#!/usr/bin/env python3
"""
WAV/YouTube player with OSC-controlled reverb.

Deps: pip install sounddevice soundfile pedalboard python-osc
      pip install yt-dlp   # or: brew/apt install yt-dlp

Usage:
  python player.py audio.wav
  python player.py audio.wav --osc-port 9000 --osc-base /reverb
  python player.py "https://youtu.be/..."

OSC addresses (all expect a float 0.0 – 1.0):
  /reverb/room_size
  /reverb/damping
  /reverb/wet_level
  /reverb/dry_level
  /reverb/width
  /reverb/freeze_mode
"""

import argparse, os, sys, threading, tempfile
import numpy as np
import sounddevice as sd
import soundfile as sf
from pedalboard import Pedalboard, Reverb

# ── Shared reverb state (GIL-safe float reads/writes) ────────────────────────
params = {
    "room_size":   0.5,
    "damping":     0.5,
    "wet_level":   0.33,
    "dry_level":   0.4,
    "width":       1.0,
    "freeze_mode": 0.0,
    "crossfade":      1.0,
    "paused":          0.0,
}

# ── Audio loading ─────────────────────────────────────────────────────────────
def load_audio(source):
    if source.startswith("http://") or source.startswith("https://"):
        import subprocess
        with tempfile.TemporaryDirectory() as d:
            tpl = os.path.join(d, "audio.%(ext)s")
            subprocess.run(
                ["yt-dlp", "-x", "--audio-format", "wav", "-o", tpl, source],
                check=True,
            )
            data, sr = sf.read(os.path.join(d, "audio.wav"), dtype="float32")
    else:
        data, sr = sf.read(source, dtype="float32")

    if data.ndim == 1:
        data = data[:, np.newaxis]          # mono → (N, 1)
    return data, sr

# ── Playback ──────────────────────────────────────────────────────────────────
def play(data_a, data_b, sr):
    channels  = data_a.shape[1]
    blocksize = 1024
    board     = Pedalboard([Reverb()])
    pos       = [0]
    tick      = [0]
    done      = threading.Event()

    def callback(outdata, frames, _time, _status):
        # Snapshot params for this block (consistent read)
        p = params.copy()

        # Apply all reverb parameters
        board[0].room_size   = p["room_size"]
        board[0].damping     = p["damping"]
        board[0].wet_level   = p["wet_level"]
        board[0].dry_level   = p["dry_level"]
        board[0].width       = p["width"]
        board[0].freeze_mode = p["freeze_mode"]

        #chunk = data[pos[0] : pos[0] + frames]
        #pad   = frames - len(chunk)
        #if pad:
        #    chunk = np.pad(chunk, ((0, pad), (0, 0)))
        
        if params["paused"] > 0.5:
            outdata[:] = np.zeros_like(outdata)
            return
        
        ratio = params["crossfade"]

        pos_a = pos[0] % len(data_a)
        chunk_a = data_a[pos_a : pos_a + frames]

        chunk_b = data_b[pos[0] : pos[0] + frames]
        pad_b = frames - len(chunk_b)

        if len(chunk_a) < frames:
            chunk_a = np.concatenate([chunk_a, data_a[:frames - len(chunk_a)]])
        if pad_b:
            chunk_b = np.pad(chunk_b, ((0, pad_b), (0, 0)))

        chunk = (1 - ratio) * chunk_a + ratio * chunk_b
        pad = pad_a


        # KEY FIX: reset=False keeps the reverb tail alive across blocks.
        # Without it pedalboard resets its internal delay lines every call
        # and the wet signal is always zero.
        processed = board(chunk.T, sr, reset=False).T[:frames]
        outdata[:] = processed
        pos[0] += frames

        # Diagnostic: print input vs output RMS every ~2 s
        tick[0] += 1
        if tick[0] % max(1, (sr // blocksize * 2)) == 0:
            in_rms  = float(np.sqrt(np.mean(chunk**2)))
            out_rms = float(np.sqrt(np.mean(processed**2)))
            print(
                f"\r  in={in_rms:.3f}  out={out_rms:.3f} │ "
                f"wet={p['wet_level']:.2f}  dry={p['dry_level']:.2f}  "
                f"room={p['room_size']:.2f}  damp={p['damping']:.2f}  "
                f"width={p['width']:.2f}  freeze={p['freeze_mode']:.2f}  ",
                end="", flush=True,
            )

        if pad:
            raise sd.CallbackStop()

    with sd.OutputStream(
        samplerate=sr,
        channels=channels,
        blocksize=blocksize,
        dtype="float32",
        callback=callback,
        finished_callback=done.set,
    ):
        done.wait()

# ── OSC listener ──────────────────────────────────────────────────────────────
def start_osc(port, base):
    try:
        from pythonosc import dispatcher, osc_server
    except ImportError:
        sys.exit("Missing dep: pip install python-osc")

    def make_handler(key):
        def handler(_addr, value, *_):
            params[key] = float(np.clip(value, 0.0, 1.0))
        return handler

    d = dispatcher.Dispatcher()
    for key in params:
        d.map(f"{base}/{key}", make_handler(key))

    server = osc_server.ThreadingOSCUDPServer(("0.0.0.0", port), d)
    print(f"[OSC] port {port} — listening on:")
    for key in params:
        print(f"  {base}/{key}  (float 0–1)")

    threading.Thread(target=server.serve_forever, daemon=True).start()
    return server

# ── CLI ───────────────────────────────────────────────────────────────────────
def main():
    ap = argparse.ArgumentParser(
        description="WAV/YouTube player with OSC-controlled reverb"
    )
    #ap.add_argument("source",      help="WAV file path or YouTube URL")
    ap.add_argument("source_a",      help="Background WAV file path or YouTube URL")
    ap.add_argument("source_b",      help="Music WAV file path or YouTube URL")

    ap.add_argument("--osc-port",  type=int, default=9000, metavar="PORT")
    ap.add_argument("--osc-base",  default="/reverb",      metavar="ADDR",
                    help="OSC base address (default: /reverb)")
    args = ap.parse_args()

    #print(f"Loading {args.source} …")
    #data, sr = load_audio(args.source)
    #print(f"  {data.shape[0] / sr:.1f}s | {sr} Hz | {data.shape[1]}ch")

    print(f"Loading {args.source_a} …")
    data_a, sr_a = load_audio(args.source_a)
    print(f"  {data_a.shape[0] / sr_a:.1f}s | {sr_a} Hz | {data_a.shape[1]}ch")
    print(f"RMS source_a: {np.sqrt(np.mean(data_a**2)):.4f}")

    print(f"Loading {args.source_b} …")
    data_b, sr_b = load_audio(args.source_b)
    print(f"  {data_b.shape[0] / sr_b:.1f}s | {sr_b} Hz | {data_b.shape[1]}ch")
    print(f"RMS source_b: {np.sqrt(np.mean(data_b**2)):.4f}")

    osc = start_osc(args.osc_port, args.osc_base)

    print("\nPlaying — move sliders in control.py to shape the reverb (Ctrl+C to quit)")
    try:
        play(data_a, data_b, sr_a)
    except KeyboardInterrupt:
        pass
    print("\nDone.")

if __name__ == "__main__":
    main()
