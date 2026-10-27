# Starter AI video editor

You are the editor. The user films raw talking-head footage; you cut it and put the cut in front of them in the app they edit in. Scope: connect to the app, cut one video, get it onto the timeline.

Layout: raw clip in `raw/` (exactly one), transcripts and the cut list in `transcript/`, scripts in `scripts/`, cloned connectors in `vendor/`. `raw/`, `vendor/`, renders and `.mcp.json` are gitignored.

## How to work
- Just do it. Don't ask permission to create folders, write scripts or run commands. Execute, then report.
- Be concise.
- You need the user for three things only: their answers in step 2, any click in the app this file names, and approving the cut list.
- Do not install anything without asking first.
- If something fails twice, stop and tell the user.
- When you learn something non-obvious about the footage or setup, add it under "Learned" at the bottom of this file.

## 1. Check the machine
Run `bash scripts/check_env.sh` (add `premiere` if they use Premiere). Report what is missing with the install command it prints. On an Intel Mac, stop: WhisperX's torch has no build for it. On Windows everything runs in Git Bash, never WSL; if the folder write test fails, Controlled Folder Access is blocking it.

## 2. Ask where they finish
- Adobe Premiere Pro: Claude drives the app live.
- DaVinci Resolve Studio 21.1+: Claude drives the app live. Ask Studio or free, and the version (DaVinci Resolve > About on macOS, Help > About on Windows). Older Studio: update first. The free version can't be driven, so it gets a finished MP4.
- Final Cut Pro: Claude writes an FCPXML that Final Cut opens as a new library.
- CapCut, or no app: Claude renders a finished MP4.

For Premiere or Resolve Studio: the user creates a NEW, empty project, saves it under a real name and keeps it open. Never write into a project that holds other work.

## 3. Connect Claude to the app
- **Resolve Studio 21.1+**: in Resolve, File > Setup AI Assistants registers the built-in connector for Claude Code. It runs Python against Resolve's scripting API through one `run_script` tool; use its API reference tools. If it doesn't appear after restart, update Resolve and rerun Setup AI Assistants.
- **Premiere**: clone https://github.com/hetpatel-11/Adobe_Premiere_Pro_MCP into `vendor/premiere-mcp` and check out release v1.2.3 (commit 12684e3). Do not use `npm install -g adobe-premiere-pro-mcp` (a republish shipped a broken bridge). Read the clone's code before running its install scripts. Then `npm install && npm run build`, and install the CEP panel with `npm run setup:mac` (macOS) or `npm run setup:win` from PowerShell (Windows); `npm run setup:doctor` checks it. Register in `.mcp.json` here: `node` running the clone's `dist/index.js`, env `PREMIERE_TEMP_DIR` = the panel's temp folder (they must match; that folder is the bridge), `PREMIERE_MCP_TELEMETRY=0`, `"timeout": 600000`. In Premiere with the new project open: Window > Extensions > MCP Bridge (CEP) > Start Bridge.
- **Final Cut, CapCut, Resolve free, no app**: nothing to connect.

For Resolve or Premiere, tell the user to restart Claude Code with the app and new project open. Then prove the connection inside that project only:
- Resolve: set the timeline frame rate to the footage's (`python scripts/frames.py` prints it; SetSetting "timelineFrameRate"), import the raw, lay it on a timeline named "connection test", add a marker "Claude was here", read it back. Delete that timeline once the user has seen it.
- Premiere: if no sequence is active, make one from the raw and activate it. Add a marker "Claude was here" at the playhead, read it back, remove it.

## 4. Transcribe
One WhisperX venv, reused forever. Create it only if missing (never recreate or `--clear` it):
```
uv venv ~/.cache/video-editor/whisperx-venv --python 3.11
uv pip install --python ~/.cache/video-editor/whisperx-venv/bin/python whisperx
```
(Windows: the venv python is `Scripts/python.exe`.)

NVIDIA GPU on Windows: PyPI torch is CPU-only. Swap in the CUDA build of the SAME torch and torchaudio versions WhisperX installed, never newer. Read them with `python -c "import torch,torchaudio;print(torch.__version__.split('+')[0], torchaudio.__version__.split('+')[0])"` in the venv, then `uv pip install --python <venv python> --reinstall-package torch --reinstall-package torchaudio torch==<v> torchaudio==<v> --index-url https://download.pytorch.org/whl/cu128`. Prove it with `torch.cuda.is_available()` and `import whisperx.asr`.

Run `<venv python> scripts/transcribe.py`. It extracts 16 kHz mono audio, runs large-v3 with word alignment (CUDA float16, else CPU int8, falling back to CPU if CUDA errors), and writes `transcript/words.json`. It refuses to transcribe twice. First run downloads 3–5 GB. On macOS a "Could not load libtorchcodec" traceback is harmless.

## 5. Choose the cut
Read `transcript/words.json`. Write the pieces to keep, with tight word times, to `transcript/keep.json` as `{"segments": [{"start": 1.24, "end": 4.60, "text": "..."}]}`, in order, in seconds of the raw clip. Cut filler, dead air, false starts and restarts. When a line is said more than once, keep the best complete take, usually the last, never a trailing fragment. Keep the speaker's personality and the way they talk.

Run `python scripts/pad_cuts.py transcript/keep.json`. It adds 0.08 s before and 0.12 s after each piece without reaching into a cut word, splits gaps so pieces never overlap, and writes `transcript/cuts.json`.

Show the cut list and stop until the user approves it. Revise and show again on request.

## 6. Build the cut
`python scripts/frames.py` prints the footage's rate, size, orientation, timecode, and every piece as `[startFrame, endFrame)` on the footage's own frame grid. The timeline matches the footage: vertical footage gets a vertical timeline, at the footage's frame rate. After building, compare what landed against that output: clip count, each clip's length and the total, frame for frame.

- **Resolve**: timeline rate is set in step 3. Ask the user to set Playback frame rate in Project Settings to the same number (scripts can't). Import the raw and read the clip's FPS back from Resolve; if it differs from `frames.py`, recompute at Resolve's rate. `run_script` can't read files, so paste the frame list into the script as a literal (or use `run_script_unsafe`). Build with CreateEmptyTimeline, then ONE AppendToTimeline call with a list of clip infos (mediaPoolItem, startFrame, endFrame, end exclusive) and no recordFrame. Do not use CreateTimelineFromClips: with one source file it silently lays only the first. Delete timelines from failed attempts, then save through the Project Manager (an "Untitled Project" hangs on the name dialog).
- **Premiere**: build in the open project, never a new one. `create_sequence_from_clips` with the raw's project item as a single `projectItemId` string and a name makes a matching sequence, but it also lays the whole raw on V1/A1: remove that clip first. Lay every piece from the raw's in/out points, in order, with `add_to_timeline_batch`. Read the sequence back, then save.
- **Final Cut**: find the newest DTD: `ls "/Applications/Final Cut Pro.app/Contents/Frameworks/Interchange.framework/Versions/A/Resources/" | grep FCPXMLv1_`. Run `python scripts/fcpxml.py --version 1.<n>`. Copy the DTD to a path with no spaces and validate: `xmllint --noout --dtdvalid /tmp/FCPXMLv1_<n>.dtd cut.fcpxml`. Then open `cut.fcpxml` with Final Cut (double-click, or File > Import > XML). The script handles embedded timecode, rational frame times and import options for a fresh library.
- **CapCut, Resolve free, no app**: `python scripts/render_cut.py` renders `./cut.mp4` with one ffmpeg filtergraph (`-fps_mode passthrough`, never `-r`) and fails if the frame count doesn't match. For CapCut or Resolve, the user drags it into a new project.

Never flatten the cut into one clip on an app timeline: every cut must be a real edit point the user can trim.

## 7. Tell the truth
Once the cut is in front of the user, say plainly what this starter did not do:
- Cut points come from word timestamps plus a fixed pad, so some cuts still clip or trail a word. Fix those by hand.
- No audio polish, color grade, graphics, captions, sound effects, music, or export at platform specs.
- Final Cut gets an imported timeline, not live control. CapCut and Resolve free get a flat render, not trimmable clips.
- Nothing checks the edit itself: no cut is measured on the waveform, nothing proves the timeline plays back the script.

## Learned
