# reverb-player

Real-time audio player with a live reverb effect controllable via OSC. Feed it a WAV file or a YouTube URL; shape the reverb from a GUI in a second terminal. Volume controled by EEG signal.

## Files

| File | Purpose |
|---|---|
| `player.py` | Plays audio, listens for OSC, applies reverb |
| `main.py` | Sliders send OSC to the player, controls player and shows graphs of EEG signal |

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

**Download audio files (optional but recommended):**
```bash
yt-dlp -x --audio-format wav -o "noise.wav" "https://www.youtube.com/..."
yt-dlp -x --audio-format wav -o "music.wav" "https://www.youtube.com/..."
```

**Start the controller:**
```bash
python main.py
```

The browser opens automatically at `http://localhost:8000`. From the web interface you can:
- Enter paths to the audio files (or YouTube URLs) and click **Play** to start the player
- Use the reverb sliders to adjust the audio parameters manually
- Click **Start** to begin the EEG experiment — the system will calculate a baseline reference (calculated independently in each experiment). Crossfade between the two audio sources is controlled in real time based on the alpha/beta power ratio
- Click **Stop** to end the experiment and **Save** to export the recorded EEG data
- Click **Stop player** to stop audio playback

Changes to reverb parameters take effect within the next audio block (~23 ms).

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
