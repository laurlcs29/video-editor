# video-editor

Claude Code cuts raw talking-head footage and lays the cut in Premiere, Resolve Studio, Final Cut, or a rendered MP4. Adapted from Jason Cooperson's free "Claude Video Editor" starter prompt.

## Run it
Runs on your own machine (macOS Apple Silicon or Windows), because the editing app and footage live there.

```
git clone https://github.com/laurlcs29/video-editor.git
cd video-editor
# put one raw clip in raw/
claude
```
Then say: **"edit the clip in raw/"**. Claude follows `CLAUDE.md`: checks your machine, asks which app you use, connects, transcribes, proposes a cut for your approval, and builds it.

## Scripts
| Script | Does |
|---|---|
| `scripts/check_env.sh` | Reports missing tools. Installs nothing. |
| `scripts/transcribe.py` | WhisperX large-v3 with word timings → `transcript/words.json`. Run with the WhisperX venv's python. |
| `scripts/pad_cuts.py` | Pads kept pieces without reaching into cut words → `transcript/cuts.json`. |
| `scripts/frames.py` | Footage specs and the cut as frame ranges, for Resolve and Premiere. |
| `scripts/render_cut.py` | Frame-exact ffmpeg render → `cut.mp4`, verified by frame count. |
| `scripts/fcpxml.py` | FCPXML for Final Cut, timecode-aware → `cut.fcpxml`. |
