#!/usr/bin/env python3
"""Measured facts about a rendered video, for the art-director agent and for you. Run after motion.mjs.

  python video_check.py posts/<date>/<id> [--seconds 20]

Writes, next to video.mp4:
  contact.png  one frame per second, 5 across (the critic looks at this, not at the code)
  phone.png    the same frames at 360 px wide, as a phone shows them
Checks (ffmpeg, local):
  duration within 2% of --seconds (or of the last caption's end)
  still stretches of 3 s or more (freezedetect): nothing new on screen = a dead beat. The final hold may be up to 3 s.
    It looks at a quarter-size, blurred copy, so the grain of a film finish (assets/lib/art-motion.js) does not count as change.
  black frames (blackdetect)
  frame 0 must carry the hook: frame0.png (from motion.mjs) is checked by attention.py; captions must start by 0.5 s
  captions of 7 words or fewer, each on screen long enough to read (0.3 s per word, 1.2 s minimum)
Exit 1 on a FAIL.
"""
import json
import pathlib
import re
import subprocess
import sys

sys.stdout.reconfigure(encoding="utf-8") if hasattr(sys.stdout, "reconfigure") else None


def ff(args):
    return subprocess.run(["ffmpeg", "-hide_banner", "-nostats"] + args, capture_output=True, text=True).stderr


def duration(video):
    r = subprocess.run(["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "csv=p=0", str(video)],
                       capture_output=True, text=True)
    return float(r.stdout.strip() or 0)


def main(argv):
    if len(argv) < 2:
        print(__doc__)
        return 2
    folder = pathlib.Path(argv[1])
    video = folder / "video.mp4"
    if not video.exists():
        print(f"FAIL no video.mp4 in {folder}")
        return 1
    fails, warns, facts = [], [], []
    dur = duration(video)
    caps = json.loads((folder / "captions.json").read_text(encoding="utf-8")) if (folder / "captions.json").exists() else []
    want = float(argv[argv.index("--seconds") + 1]) if "--seconds" in argv else (caps[-1]["end"] if caps else dur)
    facts.append(f"duration {dur:.2f} s (expected {want:.2f})")
    if want and abs(dur - want) / want > 0.02:
        fails.append(f"duration {dur:.2f} s is more than 2% off {want:.2f} s")

    # grain changes every frame and would hide a still stretch: average it out first (tested on the soft and film finishes, 30 Oct 2026)
    err = ff(["-i", str(video), "-vf", "scale=iw/4:-2,gblur=sigma=2,freezedetect=n=-55dB:d=3", "-map", "0:v", "-f", "null", "-"])
    starts = [float(x) for x in re.findall(r"freeze_start: ([\d.]+)", err)]
    lens = [float(x) for x in re.findall(r"freeze_duration: ([\d.]+)", err)]
    if len(starts) > len(lens):  # a freeze running to the end has no duration line
        lens.append(dur - starts[-1])
    for s, d in zip(starts, lens):
        end = s + d
        if end >= dur - 0.1 and d <= 3.05:
            facts.append(f"final hold {d:.1f} s from {s:.1f} s")
        else:
            fails.append(f"nothing changes from {s:.1f} s to {end:.1f} s ({d:.1f} s): a dead beat")

    err = ff(["-i", str(video), "-vf", "blackdetect=d=0.2:pix_th=0.05", "-an", "-f", "null", "-"])
    for s, e in re.findall(r"black_start:([\d.]+) black_end:([\d.]+)", err):
        warns.append(f"black frames from {float(s):.1f} s to {float(e):.1f} s")

    if caps:
        if caps[0]["start"] > 0.5:
            fails.append(f"first caption starts at {caps[0]['start']} s; LinkedIn autoplays muted, frame 0 must say something")
        for c in caps:
            n = len(c["text"].split())
            shown = c["end"] - c["start"]
            if n > 7:
                warns.append(f"caption of {n} words: \"{c['text'][:50]}\" (7 or fewer reads at a glance)")
            if shown < max(1.2, 0.3 * n):
                fails.append(f"caption \"{c['text'][:40]}\" is on screen {shown:.1f} s; needs {max(1.2, 0.3 * n):.1f} s")
    else:
        warns.append("no captions.json")

    secs = max(1, int(dur))
    rows = (secs + 4) // 5
    ff(["-y", "-i", str(video), "-vf", f"fps=1,scale=216:-1,tile=5x{rows}", "-frames:v", "1", str(folder / "contact.png")])
    ff(["-y", "-i", str(video), "-vf", f"fps=1,scale=360:-1,tile=5x{rows}", "-frames:v", "1", str(folder / "phone.png")])
    facts.append("contact.png and phone.png written; frame0.png comes from motion.mjs")

    print(f"== {video}")
    for f in facts:
        print("  ", f)
    for f in fails:
        print("  FAIL", f)
    for w in warns:
        print("  warn", w)
    print("  PASS" if not fails else "  FAIL")
    return 1 if fails else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
