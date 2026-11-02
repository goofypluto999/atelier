#!/usr/bin/env python3
"""Tests for slides (1.4.0): scripts/deck_check.py. python tests/test_slides.py

1. Floors scale with the slide's width, without a render: on a 1280 px wide slide the floors are 32 px and 21 px, so
   text at 34 px passes there and fails at 1920 px; a slide over 40 words only warns.
2. The worked deck examples/scoring-deck renders (render.mjs --audit --pdf --png --size 1920x1080) and passes deck_check.py.
3. The planted deck tests/fixtures/d1-deck fails exactly its five faults: a title off the title line (slide 2), body text
   under the floor (slide 3), a slide without a title (slide 4), a fourth type family (slide 5), and a PDF with the wrong
   page count; its clean cover raises none.
Steps 2 and 3 need node and Playwright; without them they print SKIP and the test passes."""
import json
import pathlib
import re
import shutil
import struct
import subprocess
import sys
import tempfile
import zlib

SKILL = pathlib.Path(__file__).resolve().parent.parent
DECK = SKILL / "scripts" / "deck_check.py"
RENDER = SKILL / "scripts" / "render.mjs"
problems = []


def expect(cond, msg):
    print(("ok    " if cond else "FAIL  ") + msg)
    if not cond:
        problems.append(msg)


def check(folder):
    r = subprocess.run([sys.executable, str(DECK), str(folder)], capture_output=True, text=True, encoding="utf-8")
    return r.returncode, [l.strip()[5:] for l in r.stdout.splitlines() if l.strip().startswith("FAIL ")], r.stdout


def tiny_png(path, w, h):
    raw = b"".join(b"\x00" + b"\xff" * (w * 3) for _ in range(h))
    def chunk(t, d):
        return struct.pack(">I", len(d)) + t + d + struct.pack(">I", zlib.crc32(t + d) & 0xFFFFFFFF)
    path.write_bytes(b"\x89PNG\r\n\x1a\n" + chunk(b"IHDR", struct.pack(">IIBBBBB", w, h, 8, 2, 0, 0, 0))
                     + chunk(b"IDAT", zlib.compress(raw)) + chunk(b"IEND", b""))


def render(src, out):
    return subprocess.run(["node", str(RENDER), str(src), "--audit", "--pdf", "--png", "--size", "1920x1080", "--out", str(out)],
                          capture_output=True, text=True, encoding="utf-8")


def main():
    with tempfile.TemporaryDirectory() as t:
        tmp = pathlib.Path(t)
        page = {"page": 1, "words": 44, "minFont": 34, "minAll": 34, "sizes": [34, 90], "families": ["Archivo"], "fails": [],
                "boxes": [{"role": "hook", "x": 80, "y": 80, "w": 600, "h": 100}]}
        for w, h, want in ((1280, 720, 0), (1920, 1080, 1)):
            d = tmp / f"unit-{w}"
            d.mkdir()
            (d / "audit.json").write_text(json.dumps([page]), encoding="utf-8")
            tiny_png(d / "page-01.png", w, h)
            code, fails, out = check(d)
            expect(code == want and ("warn slide 1: 44 words" in out), f"1. text at 34 px on a {w} px slide: exit {code}, want {want}; 44 words warn")

    if not shutil.which("node"):
        print("SKIP  2 and 3: node not found")
    else:
        with tempfile.TemporaryDirectory() as t:
            tmp = pathlib.Path(t)
            r = render(SKILL / "examples" / "scoring-deck" / "visual.html", tmp / "good")
            if r.returncode == 2 and "Playwright" in (r.stdout + r.stderr):
                print("SKIP  2 and 3: Playwright not found")
            else:
                code, fails, out = check(tmp / "good")
                expect(r.returncode == 0 and code == 0, f"2. the worked deck passes the audit and deck_check.py (render {r.returncode}, deck {code}) {fails}")
                r = render(SKILL / "tests" / "fixtures" / "d1-deck" / "visual.html", tmp / "bad")
                shutil.copy(tmp / "good" / "carousel.pdf", tmp / "bad" / "carousel.pdf")   # 5 pages: the right count, so the slide faults stand alone
                code, fails, out = check(tmp / "bad")
                want = {"slide 2: the title starts": 1, "slide 3: text at 40 px": 1, "slide 4 has no title": 1, "4 type families": 1}
                got = {k: sum(1 for f in fails if k in f) for k in want}
                expect(code == 1 and got == want and len(fails) == len(want), f"3. the planted deck fails its four slide faults and nothing else: {fails}")
                # a PDF with the wrong page count: drop one page's object marker
                pdf = (tmp / "bad" / "carousel.pdf").read_bytes()
                m = list(re.finditer(rb"/Type\s*/Page(?![s\w])", pdf))
                (tmp / "bad" / "carousel.pdf").write_bytes(pdf[:m[-1].start()] + b"/Type /Pagx" + pdf[m[-1].end():])
                code, fails, out = check(tmp / "bad")
                expect(code == 1 and any("carousel.pdf has 4 page(s) for 5 slide(s)" in f for f in fails), "3. a PDF with the wrong page count fails")
    print("PASS" if not problems else f"FAIL {len(problems)} problem(s)")
    return 1 if problems else 0


if __name__ == "__main__":
    sys.exit(main())
