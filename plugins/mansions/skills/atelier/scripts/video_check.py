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
  captions of 7 words or fewer, each on screen long enough to read (read_time, 1.2 s minimum)
  words on screen (texts.json, which motion.mjs writes for blocks marked data-read and for window.texts): each piece whole
    on screen for read_time plus 1.5 s, the time the eye needs to find it (1.5 s minimum); a piece never whole on screen fails
  read_time: 0.3 s a word, and 4.5 characters a second in Chinese, Japanese and Korean
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


# One reading speed for captions and for words elsewhere on screen. Latin script: 0.3 s a word (Atelier's caption rule;
# lemo-opuscar's 15 characters a second comes to about the same in English). Chinese, Japanese and Korean put no spaces
# between words, so they count by character, 4.5 a second (the idea of lemo-opuscar's core/render/readcheck.mjs, rewritten).
# Kana punctuation (the double hyphen and the middle dot) is not a character to read.
CJK = re.compile("[\u1100-\u11ff\u3040-\u309f\u30a1-\u30fa\u30fc-\u30ff\u3130-\u318f\u31f0-\u31ff\u3400-\u4dbf\u4e00-\u9fff\uac00-\ud7af\uf900-\ufaff\uff66-\uff9f\U00020000-\U0002fa1f]")


def read_time(text, pad=0.0, floor=1.2):
    """Seconds a viewer needs to read text: 0.3 s a word, a Chinese, Japanese or Korean character 1/4.5 s, plus pad; at least floor."""
    cjk = len(CJK.findall(text))
    words = [w for w in CJK.sub(" ", text).split() if re.search(r"\w", w)]
    return max(floor, 0.3 * len(words) + cjk / 4.5 + pad)


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
            shown, need = c["end"] - c["start"], read_time(c["text"])
            cjk = len(CJK.findall(c["text"]))
            if n > 7 and not cjk:
                warns.append(f"caption of {n} words: \"{c['text'][:50]}\" (7 or fewer reads at a glance)")
            if cjk > 16:
                warns.append(f"caption of {cjk} Chinese, Japanese or Korean characters: \"{c['text'][:30]}\" (16 or fewer reads at a glance)")
            if shown < need:
                fails.append(f"caption \"{c['text'][:40]}\" is on screen {shown:.1f} s; needs {need:.1f} s")
    else:
        warns.append("no captions.json")

    words = folder / "texts.json"
    if words.exists():
        texts = json.loads(words.read_text(encoding="utf-8")).get("texts", [])
        if not texts:
            fails.append("texts.json lists no words: a block marked data-read, or window.texts(t), was never on screen")
        for w in texts:
            label = f"{w['id']} \"{w['text'][:40]}\""
            if not w["whole"]:
                fails.append(f"words never wholly visible (cut by the frame or a clip, or partly hidden): {label}")
                continue
            need = read_time(w["text"], pad=1.5, floor=1.5)
            if w["shown"] < need - 0.002:   # shown is rounded to 3 decimals in texts.json
                fails.append(f"words on screen too briefly to read: {label} is whole on screen {w['shown']:.2f} s from {w['start']:.2f} s; needs {need:.2f} s")
        facts.append(f"{len(texts)} piece(s) of words on screen measured for reading time (texts.json)")
    else:
        warns.append("no texts.json: words on screen are not checked for reading time (mark them data-read, references/motion.md)")

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
