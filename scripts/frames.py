"""Print the raw clip's specs and the cut as frame ranges (for Resolve and Premiere).

Usage: python scripts/frames.py [raw_clip]
Frame ranges are [in, out) at the footage's own rate; paste them into the app script as a literal.
"""
import json
import sys

from media import find_raw, frame_ranges, load_cuts, probe

raw = sys.argv[1] if len(sys.argv) > 1 else find_raw()
info = probe(raw)
fps = info["fps"]
ranges = frame_ranges(load_cuts(), fps)
print(json.dumps({
    "raw": str(raw),
    "fps": f"{fps.numerator}/{fps.denominator}",
    "fps_float": float(fps),
    "size": [info["width"], info["height"]],
    "vertical": info["vertical"],
    "timecode": info["timecode"],
    "pieces": [{"startFrame": a, "endFrame": b, "seconds_in": float(a / fps), "seconds_out": float(b / fps)} for a, b in ranges],
    "total_frames": sum(b - a for a, b in ranges),
}, indent=2))
