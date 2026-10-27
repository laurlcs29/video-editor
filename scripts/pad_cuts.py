"""Pad kept pieces with a little air, without reaching into cut words or overlapping.

Usage: python scripts/pad_cuts.py transcript/keep.json
keep.json is {"segments": [{"start", "end", "text"}]} with tight word times.
Writes transcript/cuts.json with padded times.
"""
import json
import sys

from media import ROOT

PRE, POST = 0.08, 0.12

keep = json.loads(open(sys.argv[1]).read())["segments"]
words = json.loads((ROOT / "transcript" / "words.json").read_text())["words"]
timed = [w for w in words if "start" in w and "end" in w]


def inside(w):
    return any(s["start"] - 1e-3 <= w["start"] and w["end"] <= s["end"] + 1e-3 for s in keep)


cut_words = [w for w in timed if not inside(w)]

padded = []
for s in keep:
    lo = max([w["end"] for w in cut_words if w["end"] <= s["start"]], default=0.0)
    hi = min([w["start"] for w in cut_words if w["start"] >= s["end"]], default=float("inf"))
    padded.append({"start": max(s["start"] - PRE, lo, 0.0), "end": min(s["end"] + POST, hi), "text": s["text"]})

# Where two pieces now overlap, split the gap between their tight times.
for a, b, ka, kb in zip(padded, padded[1:], keep, keep[1:]):
    if b["start"] < a["end"]:
        mid = (ka["end"] + kb["start"]) / 2
        a["end"], b["start"] = mid, mid

for p in padded:
    p["start"], p["end"] = round(p["start"], 3), round(p["end"], 3)

(ROOT / "transcript" / "cuts.json").write_text(json.dumps({"segments": padded}, indent=2))
print(f"wrote transcript/cuts.json: {len(padded)} pieces, {sum(p['end'] - p['start'] for p in padded):.2f} s")
