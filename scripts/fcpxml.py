"""Write transcript/cuts.json as an FCPXML that Final Cut opens as a new library.

Usage: python scripts/fcpxml.py [--version 1.11] [raw_clip]
Use the newest FCPXML version your Final Cut ships a DTD for:
  ls "/Applications/Final Cut Pro.app/Contents/Frameworks/Interchange.framework/Versions/A/Resources/" | grep FCPXMLv1_
Validate: cp that .dtd to a path with no spaces, then
  xmllint --noout --dtdvalid /tmp/FCPXMLv1_11.dtd cut.fcpxml
"""
import argparse
from pathlib import Path
from xml.sax.saxutils import quoteattr

from media import ROOT, find_raw, frame_ranges, load_cuts, probe, timecode_frames

ap = argparse.ArgumentParser()
ap.add_argument("raw", nargs="?")
ap.add_argument("--version", default="1.11")
ap.add_argument("--name", default="Claude cut")
args = ap.parse_args()

raw = Path(args.raw) if args.raw else find_raw()
raw = raw.resolve()
info = probe(raw)
fps = info["fps"]


def t(frames):
    """Rational time on the footage's frame grid, e.g. 1001/30000s."""
    num, den = frames * fps.denominator, fps.numerator
    return f"{num}/{den}s" if num % den else f"{num // den}s"


tc = info["timecode"]
tc_start = timecode_frames(tc, fps) if tc else 0
tc_format = "DF" if tc and ";" in tc else "NDF"
asset_frames = round(info["duration"] * fps)
ranges = frame_ranges(load_cuts(), fps)
total = sum(b - a for a, b in ranges)
layout = "mono" if info["audio_channels"] == 1 else "stereo"
rate = {44100: "44.1k", 48000: "48k", 96000: "96k"}.get(info["audio_rate"], "48k")

clips, offset = [], 0
for i, (a, b) in enumerate(ranges, 1):
    clips.append(
        f'          <asset-clip ref="r2" name={quoteattr(f"{raw.stem} {i}")} offset="{t(offset)}" '
        f'start="{t(tc_start + a)}" duration="{t(b - a)}" tcFormat="{tc_format}"/>'
    )
    offset += b - a

library = (ROOT / f"{args.name}.fcpbundle").resolve().as_uri()
xml = f"""<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE fcpxml>
<fcpxml version="{args.version}">
  <import-options>
    <option key="library location" value={quoteattr(library)}/>
    <option key="copy assets" value="0"/>
    <option key="suppress warnings" value="1"/>
  </import-options>
  <resources>
    <format id="r1" frameDuration="{t(1)}" width="{info['width']}" height="{info['height']}" colorSpace="1-1-1 (Rec. 709)"/>
    <asset id="r2" name={quoteattr(raw.stem)} start="{t(tc_start)}" duration="{t(asset_frames)}" hasVideo="1" format="r1" hasAudio="1" audioSources="1" audioChannels="{info['audio_channels']}" audioRate="{info['audio_rate']}">
      <media-rep kind="original-media" src={quoteattr(raw.as_uri())}/>
    </asset>
  </resources>
  <library>
    <event name={quoteattr(args.name)}>
      <project name={quoteattr(args.name)}>
        <sequence format="r1" duration="{t(total)}" tcStart="0s" tcFormat="{tc_format}" audioLayout="{layout}" audioRate="{rate}">
          <spine>
{chr(10).join(clips)}
          </spine>
        </sequence>
      </project>
    </event>
  </library>
</fcpxml>
"""
out = ROOT / "cut.fcpxml"
out.write_text(xml)
print(f"wrote {out}: {len(ranges)} clips, {total} frames at {fps}")
