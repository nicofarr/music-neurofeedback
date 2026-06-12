# reverb-player

Real-time audio player with a live reverb effect controllable via OSC. Feed it a WAV file or a YouTube URL; shape the reverb from a GUI in a second terminal. Volume controled by EEG signal.

## Files

| File | Purpose |
|---|---|
| `player.py` | Plays audio, listens for OSC, applies reverb |
| `main.py` | Sliders send OSC to the player, graphs of EEG signal |

## Install
With uv 

```bash
uv sync
```

with pip

```bash
pip install sounddevice soundfile pedalboard python-osc
pip install yt-dlp          # or: brew install yt-dlp
```

## Usage

**Terminal 1 — start the player:**
```bash
python player.py audio.wav
python player.py audio.wav --osc-port 9000 --osc-base /reverb
python player.py "https://youtu.be/dQw4w9WgXcQ"
```

**Terminal 2 — start the controller:**
```bash
python main.py
```

URL is opened by program (default `http://localhost:8501`), move the sliders to adjust reverb. Changes take effect within the next audio block (~23 ms).

## OSC API

All parameters accept a float in `[0.0, 1.0]`. Default base address: `/reverb`.

| Address | Default | Description |
|---|---|---|
| `/reverb/wet_level` | 0.33 | Level of the reverb signal |
| `/reverb/dry_level` | 0.40 | Level of the original dry signal |
| `/reverb/room_size` | 0.50 | Size of the virtual room — larger = longer tail |
| `/reverb/damping`   | 0.50 | High-frequency absorption — higher = darker, shorter tail |
| `/reverb/width`     | 1.00 | Stereo width of the reverb |
| `/reverb/freeze_mode` | 0.0 | Freeze the reverb tail (1.0 = infinite sustain) |

You can also drive the player from any OSC-capable tool (Max/MSP, Pure Data, TouchOSC, etc.).

## Notes

- **`reset=False`** — pedalboard resets its internal delay lines on every `board()` call by default, which makes the wet signal permanently zero in streaming mode. The `reset=False` keyword argument is what keeps the reverb tail alive across blocks.
- Audio is loaded fully into RAM before playback; very long files will use proportional memory.
- YouTube downloads are written to a temp directory and deleted after loading.
