"""Render transcript/cuts.json to ./cut.mp4 with one ffmpeg filtergraph, then verify it.

Usage: python scripts/render_cut.py [raw_clip]
For CapCut, Resolve's free version or no app.
"""
import subprocess
import sys

from media import ROOT, find_raw, frame_ranges, load_cuts, probe

raw = sys.argv[1] if len(sys.argv) > 1 else find_raw()
info = probe(raw)
fps = info["fps"]
ranges = frame_ranges(load_cuts(), fps)

parts, labels = [], []
for i, (a, b) in enumerate(ranges):
    t0, t1 = float(a / fps), float(b / fps)
    parts.append(f"[0:v]trim=start_frame={a}:end_frame={b},setpts=PTS-STARTPTS[v{i}]")
    parts.append(f"[0:a]atrim=start={t0:.6f}:end={t1:.6f},asetpts=PTS-STARTPTS[a{i}]")
    labels.append(f"[v{i}][a{i}]")
graph = ";".join(parts) + f";{''.join(labels)}concat=n={len(ranges)}:v=1:a=1[v][a]"

out = ROOT / "cut.mp4"
subprocess.run([
    "ffmpeg", "-y", "-v", "error", "-i", str(raw), "-filter_complex", graph,
    "-map", "[v]", "-map", "[a]", "-fps_mode", "passthrough",
    "-c:v", "libx264", "-crf", "16", "-preset", "medium", "-pix_fmt", "yuv420p",
    "-c:a", "aac", "-b:a", "320k", "-movflags", "+faststart", str(out),
], check=True)

expected = sum(b - a for a, b in ranges)
got = int(subprocess.run(
    ["ffprobe", "-v", "error", "-count_frames", "-select_streams", "v:0",
     "-show_entries", "stream=nb_read_frames", "-of", "csv=p=0", str(out)],
    check=True, capture_output=True, text=True,
).stdout.strip())
dur = probe(out)["duration"]
print(f"cut.mp4: {len(ranges)} pieces, {got} frames (expected {expected}), {dur:.3f} s (expected {float(expected / fps):.3f} s)")
if got != expected:
    sys.exit("frame count mismatch")
