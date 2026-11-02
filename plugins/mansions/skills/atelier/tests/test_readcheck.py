#!/usr/bin/env python3
"""Tests for the reading-time check (round 15, the lemo-opuscar intake). python tests/test_readcheck.py

1. read_time in scripts/video_check.py: 0.3 s a word, 4.5 characters a second in Chinese, Japanese and Korean, punctuation not
   counted (full-width marks, a lone dash, the katakana middle dot), then the pad and the floor.
2. Captions and texts.json without a render: a caption of 12 Chinese characters held 1.5 s fails (needs 2.7 s; counted as one word,
   as before this check, it passed at 1.2 s); a four-word English caption held 1.3 s still passes; a caption of 17 Chinese characters
   warns; a piece held exactly its reading time passes although texts.json rounds it to 3 decimals.
3. motion.mjs measures words on screen into texts.json (tests/fixtures/r15-read-time), 14 pieces: a block counts from the frame
   every word in it is nearly opaque and every line is inside the page, each overflow box and each clip-path inset; a hidden word,
   a line inside its mask (marked on the line or on its box), a clip-path reveal and a parent's opacity delay it; new text under the
   same id is a new piece; the longest whole stretch counts, and a one-frame cut is bridged; window.texts(t) reports words drawn on a
   canvas; a block cut by the frame is never whole; blocks with visibility hidden or display none get no entry. --sub 2 measures the
   same as --sub 1.
4. video_check.py fails the five planted pieces and nothing else, and passes the same film with FIX true.
5. A film with no data-read and no window.texts gets no texts.json (an older one in the folder is removed), and video_check.py only warns.
Checks 2 to 5 need ffmpeg, and 3 to 5 node and Playwright; without them they print SKIP and the test passes."""
import importlib.util
import json
import pathlib
import shutil
import subprocess
import sys
import tempfile

SKILL = pathlib.Path(__file__).resolve().parent.parent
FIXTURE = SKILL / "tests" / "fixtures" / "r15-read-time" / "motion.html"
VIDEO_CHECK = SKILL / "scripts" / "video_check.py"
SIZE = ("--seconds", "6", "--fps", "10", "--size", "480x900")


def video_check_module():
    spec = importlib.util.spec_from_file_location("video_check", VIDEO_CHECK)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def check(folder, seconds):
    return subprocess.run([sys.executable, str(VIDEO_CHECK), str(folder), "--seconds", str(seconds)], capture_output=True, text=True, encoding="utf-8")


def motion(html, out, *extra):
    return subprocess.run(["node", str(SKILL / "scripts" / "motion.mjs"), str(html), "--out", str(out), *extra], capture_output=True, text=True)


def lines(stdout, kind):
    """The FAIL or warn lines of a video_check.py run, without the closing summary line."""
    return [line.strip()[len(kind) + 1:] for line in stdout.splitlines() if line.strip().startswith(kind + " ")]


def pieces(folder):
    return {(w["id"], w["text"]): (w["start"], w["shown"], w["whole"]) for w in json.loads((folder / "texts.json").read_text(encoding="utf-8"))["texts"]}


def test_rule():
    vc = video_check_module()
    assert hasattr(vc, "read_time"), "scripts/video_check.py has no read_time(): there is no reading-time rule to check"
    rt = vc.read_time
    raw = [("Rows synced this week, night by night.", 7 * 0.3),        # 7 words
           ("这句话需要更长的时间", 10 / 4.5),                          # 10 Chinese characters, no spaces
           ("你好，世界。", 4 / 4.5),                                   # full-width punctuation is not read as a word
           ("カタカナとひらがな", 9 / 4.5),                             # kana
           ("カタ・カナ", 4 / 4.5),                                     # the katakana middle dot is punctuation
           ("한국어 문장", 5 / 4.5),                                    # hangul
           ("Q3 收入 4,812 - ok", 3 * 0.3 + 2 / 4.5)]                   # mixed: Q3, 4,812 and ok are words; a lone dash is not
    bad = [(text, round(rt(text, floor=0), 3), round(want, 3)) for text, want in raw if abs(rt(text, floor=0) - want) > 1e-9]
    assert not bad, f"read_time (text, got, want): {bad}"
    assert abs(rt("DONE", pad=1.5, floor=1.5) - 1.8) < 1e-9 and rt("", pad=1.5, floor=1.5) == 1.5 and rt("Hi") == 1.2, "pad and floor"
    print(f"PASS rule: read_time gives 0.3 s a word and 4.5 Chinese, Japanese or Korean characters a second, skips punctuation, adds the pad "
          f"and keeps the floor ({len(raw) + 3} cases)")


def test_captions_and_rounding(tmp):
    folder = tmp / "captions"
    folder.mkdir()
    subprocess.run(["ffmpeg", "-y", "-v", "error", "-f", "lavfi", "-i", "testsrc2=size=320x240:rate=10", "-t", "5", "-pix_fmt", "yuv420p",
                    str(folder / "video.mp4")], check=True)
    zh, long_zh = "这句话需要更长的时间啊吧", "这是一条很长很长的字幕需要更多时间"
    caps = [{"start": 0.0, "end": 1.5, "text": zh}, {"start": 0.5, "end": 1.8, "text": "Four words, read fast."}, {"start": 0.5, "end": 4.5, "text": long_zh}]
    (folder / "captions.json").write_text(json.dumps(caps, ensure_ascii=False), encoding="utf-8")
    six = "六个汉字刚好"   # needs 6 / 4.5 + 1.5 = 2.8333 s; 85 frames at 30 fps is 2.8333 s, which texts.json writes as 2.833
    (folder / "texts.json").write_text(json.dumps({"fps": 30, "seconds": 5, "texts": [{"id": "six", "text": six, "start": 0, "shown": 2.833, "whole": True}]},
                                                  ensure_ascii=False), encoding="utf-8")
    r = check(folder, 5)
    got, warned = lines(r.stdout, "FAIL"), lines(r.stdout, "warn")
    assert r.returncode == 1 and len(got) == 1 and zh in got[0] and "needs 2.7 s" in got[0], r.stdout
    assert any("17 Chinese, Japanese or Korean characters" in w for w in warned), r.stdout
    print("PASS captions: a caption of 12 Chinese characters held 1.5 s fails (needs 2.7 s; as one word it passed at 1.2 s), a four-word English "
          "caption held 1.3 s passes, one of 17 characters warns, and a piece held exactly its reading time passes after rounding")


def test_measure(tmp):
    """Renders the planted fixture, checks texts.json piece by piece, then video_check.py on it and on the fixed copy. Returns False on SKIP."""
    out = tmp / "planted"
    r = motion(FIXTURE, out, *SIZE)
    if "Playwright not found" in r.stderr:
        print("SKIP measure: Playwright is not installed")
        return False
    assert r.returncode == 0, r.stdout + r.stderr
    assert (out / "texts.json").is_file(), f"motion.mjs wrote no texts.json for a page with data-read blocks and window.texts: {sorted(p.name for p in out.iterdir())}"
    got = pieces(out)
    want = {("hook", "A page that says enough."): (0.0, 6.0, True),
            ("note", "Seven words that leave the screen too soon."): (1.0, 1.5, True),   # half opaque from 0.5 s does not count
            ("zh", "这句话需要更长的时间"): (2.0, 2.6, True),
            ("edge", "Cut off at the edge"): (0.0, 0, False),
            ("count", "Before"): (0.0, 3.0, True),
            ("count", "After"): (3.0, 3.0, True),                                         # new text under the same id
            ("mask", "Rises out of a mask"): (1.5, 4.5, True),                            # whole only once out of its clipping box
            ("box", "Inside the box"): (1.5, 4.5, True),                                  # the same, marked on the box
            ("kids", "Two halves"): (4.0, 2.0, True),                                     # its second word is transparent until 4 s
            ("clip", "Clipped reveal line"): (1.5, 4.5, True),                            # clip-path inset until 1.5 s
            ("parent", "Faded by its parent"): (1.0, 5.0, True),                          # the parent is half opaque until 1 s
            ("blink", "Here, gone, back again"): (1.0, 5.0, True),                        # 0.5 s, gone 0.5 s, then 5 s: the longest counts
            ("shake", "Held through one shake"): (1.5, 3.1, True),                        # cut for one frame at 3.0 s: bridged
            ("canvas", "Drawn on a canvas"): (0.0, 1.0, True)}                            # from window.texts
    assert set(got) == set(want), f"pieces in texts.json: missing {sorted(set(want) - set(got))}, extra {sorted(set(got) - set(want))}"
    off = {k: (got[k], v) for k, v in want.items() if abs(got[k][0] - v[0]) > 1e-6 or abs(got[k][1] - v[1]) > 1e-6 or got[k][2] != v[2]}
    assert not off, f"texts.json (got, want) as (start, shown, whole): {off}"

    r = motion(FIXTURE, tmp / "planted-sub", *SIZE, "--sub", "2")
    assert r.returncode == 0 and pieces(tmp / "planted-sub") == got, "--sub 2 measured differently from --sub 1"

    v = check(out, 6)
    failed = lines(v.stdout, "FAIL")
    named = sorted(f.split(": ", 1)[1].split(" ", 1)[0] for f in failed)
    assert v.returncode == 1 and named == ["canvas", "edge", "kids", "note", "zh"] and all(f.startswith("words ") for f in failed), v.stdout

    fixed = tmp / "fixed" / "motion.html"
    fixed.parent.mkdir()
    src = FIXTURE.read_text(encoding="utf-8")
    assert src.count("const FIX = false;") == 1
    fixed.write_text(src.replace("const FIX = false;", "const FIX = true;"), encoding="utf-8")
    r = motion(fixed, tmp / "fixed-out", *SIZE)
    assert r.returncode == 0, r.stdout + r.stderr
    v = check(tmp / "fixed-out", 6)
    assert v.returncode == 0 and f"{len(want)} piece(s) of words on screen" in v.stdout, v.stdout
    print(f"PASS measure: texts.json holds {len(want)} of {len(want)} pieces with the right start, time on screen and wholeness (a hidden word, a mask, "
          "a clip-path, a parent's opacity, a blink, a one-frame shake, new text under one id, window.texts, a block cut by the frame; two undrawn "
          "blocks left out), the same at --sub 2; video_check.py fails exactly the 5 planted pieces and passes the fixed film")
    return True


def test_undeclared(tmp):
    page = tmp / "plain" / "motion.html"
    page.parent.mkdir()
    page.write_text('<!doctype html><meta charset="utf-8"><style>body{margin:0}.page{position:relative;width:320px;height:400px;background:#eee}'
                    'h1{margin:0}i{position:absolute;top:180px;width:40px;height:40px;background:#333}</style><section class="page"><h1>Plain words</h1><i></i></section>'
                    '<script>window.seek = (t) => { document.querySelector("i").style.left = (t * 100).toFixed(1) + "px"; };</script>', encoding="utf-8")
    out = tmp / "plain-out"
    out.mkdir()
    (out / "texts.json").write_text('{"fps": 10, "seconds": 2, "texts": [{"id": "old", "text": "From another film", "start": 0, "shown": 0.1, "whole": true}]}',
                                    encoding="utf-8")
    r = motion(page, out, "--seconds", "2", "--fps", "10", "--size", "320x400")
    assert r.returncode == 0, r.stdout + r.stderr
    assert not (out / "texts.json").exists(), "motion.mjs left an older texts.json beside a film that marks no words"
    v = check(out, 2)
    assert v.returncode == 0 and "no texts.json" in v.stdout, v.stdout
    print("PASS undeclared: a film that marks no words gets no texts.json (an older one is removed), and video_check.py passes it with a warning")


def main():
    test_rule()
    if not shutil.which("ffmpeg"):
        print("SKIP captions, measure and undeclared: ffmpeg is not installed")
        print("test_readcheck: PASS")
        return 0
    with tempfile.TemporaryDirectory() as d:
        tmp = pathlib.Path(d)
        test_captions_and_rounding(tmp)
        if shutil.which("node") and test_measure(tmp):
            test_undeclared(tmp)
        else:
            print("SKIP undeclared: node or Playwright is not installed")
    print("test_readcheck: PASS")
    return 0


if __name__ == "__main__":
    sys.exit(main())
