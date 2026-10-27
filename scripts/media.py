"""Shared helpers: ffprobe the raw clip and snap seconds to its frame grid."""
import json
import subprocess
from fractions import Fraction
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent


def probe(path):
    out = subprocess.run(
        ["ffprobe", "-v", "error", "-print_format", "json", "-show_streams", "-show_format", str(path)],
        check=True, capture_output=True, text=True,
    ).stdout
    data = json.loads(out)
    video = next(s for s in data["streams"] if s["codec_type"] == "video")
    audio = next((s for s in data["streams"] if s["codec_type"] == "audio"), None)
    fps = Fraction(video["r_frame_rate"])
    width, height = int(video["width"]), int(video["height"])
    rotation = 0
    for sd in video.get("side_data_list", []):
        if "rotation" in sd:
            rotation = int(sd["rotation"])
    if abs(rotation) in (90, 270):
        width, height = height, width
    timecode = video.get("tags", {}).get("timecode") or data["format"].get("tags", {}).get("timecode")
    return {
        "fps": fps,
        "width": width,
        "height": height,
        "vertical": height > width,
        "duration": float(data["format"]["duration"]),
        "frames": int(video["nb_frames"]) if video.get("nb_frames") else None,
        "timecode": timecode,
        "audio_rate": int(audio["sample_rate"]) if audio else 48000,
        "audio_channels": int(audio["channels"]) if audio else 2,
    }


def to_frame(seconds, fps):
    """Nearest whole frame for a time in seconds."""
    return round(Fraction(seconds).limit_denominator(1_000_000) * fps)


def timecode_frames(tc, fps):
    """Frame count of an SMPTE timecode; ';' marks drop-frame."""
    drop = ";" in tc
    h, m, s, f = (int(x) for x in tc.replace(";", ":").split(":"))
    nominal = round(fps)
    frames = ((h * 60 + m) * 60 + s) * nominal + f
    if drop:
        dropped = 2 if nominal == 30 else 4
        total_min = h * 60 + m
        frames -= dropped * (total_min - total_min // 10)
    return frames


def load_cuts(path=ROOT / "transcript" / "cuts.json"):
    segs = json.loads(Path(path).read_text())["segments"]
    for a, b in zip(segs, segs[1:]):
        if b["start"] < a["end"]:
            raise SystemExit(f"cuts.json: overlapping pieces at {a['end']} / {b['start']}")
    return segs


def frame_ranges(segs, fps):
    """[(in_frame, out_frame_exclusive)] for each kept piece, snapped to the grid."""
    ranges = []
    for s in segs:
        a, b = to_frame(s["start"], fps), to_frame(s["end"], fps)
        if b <= a:
            raise SystemExit(f"cuts.json: piece {s} is shorter than one frame")
        ranges.append((a, b))
    return ranges


def find_raw():
    clips = [p for p in (ROOT / "raw").iterdir() if p.is_file() and not p.name.startswith(".")]
    if len(clips) != 1:
        raise SystemExit(f"expected exactly one clip in raw/, found {len(clips)}")
    return clips[0]
