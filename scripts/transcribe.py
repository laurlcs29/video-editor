"""Transcribe the raw clip once with WhisperX large-v3 and word-level alignment.

Run with the shared venv's python:
  ~/.cache/video-editor/whisperx-venv/bin/python scripts/transcribe.py [raw_clip]
  (Windows: ~/.cache/video-editor/whisperx-venv/Scripts/python.exe)
Writes transcript/words.json. Does nothing if it already exists.
"""
import json
import os
import subprocess
import sys
from pathlib import Path

os.environ.setdefault("PYTHONUTF8", "1")
os.environ.setdefault("HF_HUB_DISABLE_SYMLINKS", "1")

ROOT = Path(__file__).resolve().parent.parent
OUT = ROOT / "transcript" / "words.json"
WAV = ROOT / "transcript" / "audio16k.wav"

if OUT.exists():
    print(f"{OUT} exists; not transcribing the same footage twice")
    sys.exit(0)

if len(sys.argv) > 1:
    raw = Path(sys.argv[1])
else:
    clips = [p for p in (ROOT / "raw").iterdir() if p.is_file() and not p.name.startswith(".")]
    if len(clips) != 1:
        sys.exit(f"expected exactly one clip in raw/, found {len(clips)}")
    raw = clips[0]

subprocess.run(["ffmpeg", "-y", "-v", "error", "-i", str(raw), "-vn", "-ac", "1", "-ar", "16000", str(WAV)], check=True)

import torch  # noqa: E402
import whisperx  # noqa: E402

device, compute = "cpu", "int8"
if torch.cuda.is_available():
    device, compute = "cuda", "float16"


def run(device, compute):
    audio = whisperx.load_audio(str(WAV))
    model = whisperx.load_model("large-v3", device, compute_type=compute)
    result = model.transcribe(audio, batch_size=16 if device == "cuda" else 4)
    align_model, meta = whisperx.load_align_model(language_code=result["language"], device=device)
    aligned = whisperx.align(result["segments"], align_model, meta, audio, device, return_char_alignments=False)
    return result["language"], aligned


try:
    language, aligned = run(device, compute)
except RuntimeError as e:
    if device != "cuda":
        raise
    print(f"CUDA failed ({e}); falling back to CPU int8")
    language, aligned = run("cpu", "int8")

OUT.write_text(json.dumps({
    "source": str(raw),
    "language": language,
    "segments": [{"start": s["start"], "end": s["end"], "text": s["text"].strip()} for s in aligned["segments"]],
    "words": aligned["word_segments"],
}, indent=2, ensure_ascii=False))
print(f"wrote {OUT}: {len(aligned['word_segments'])} words")
