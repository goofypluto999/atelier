#!/usr/bin/env python3
"""Measured facts about a slide deck, after render.mjs. Slides are read on a shared or projected screen, smaller and farther
away than a phone feed, so they get their own floors and a check that the deck holds together (references/slides.md).

  node S/scripts/render.mjs deck.html --audit --pdf --png --size 1920x1080 --out <folder>
  python S/scripts/deck_check.py <folder>

Reads <folder>/audit.json, the page PNGs and carousel.pdf. Fails on (exit 1):
  a slide the audit failed
  text under 48 px, or labelled fine print under 32 px, on a 1920 px wide slide (scaled to the slide's width): 24 pt and
    16 pt on a 13.33 in wide slide, a common floor for projected slides (a heuristic, not a study)
  a slide with no title (data-role="hook"): one claim per slide, said in its title
  a title off the deck's title line: from slide 2 on, its top-left corner more than 24 px from the median of the others
  more than 3 type families across the deck
  a PDF whose page count is not the slide count
Warns on: a slide over 40 words, more than 7 type sizes across the deck, a family used on one slide only, a marked box
within 3% of an edge, no carousel.pdf. A deck of one slide gets the floors only.
"""
import json
import pathlib
import re
import statistics
import struct
import sys

sys.stdout.reconfigure(encoding="utf-8") if hasattr(sys.stdout, "reconfigure") else None

BODY_PX, FINE_PX, WIDE = 48, 32, 1920    # 24 pt and 16 pt on a 13.33 in (960 pt) slide drawn 1920 px wide
LINE_PX, MAX_FAMILIES, MAX_SIZES, MAX_WORDS, EDGE = 24, 3, 7, 40, 0.03


def png_size(path):
    with open(path, "rb") as f:
        head = f.read(24)
    return struct.unpack(">II", head[16:24]) if head[:8] == b"\x89PNG\r\n\x1a\n" else (0, 0)


def main(argv):
    if len(argv) < 2:
        print(__doc__)
        return 2
    folder = pathlib.Path(argv[1])
    audit_file = folder / "audit.json"
    if not audit_file.exists():
        print(f"FAIL no audit.json in {folder.name}: run render.mjs --audit --out {folder.name} first")
        return 1
    pages = json.loads(audit_file.read_text(encoding="utf-8"))
    pngs = sorted(folder.glob("page-*.png"))
    w, h = png_size(pngs[0]) if pngs else (WIDE, 1080)
    k = w / WIDE
    fails, warns, facts = [], [], []
    facts.append(f"{len(pages)} slide(s) at {w}x{h}; floors {BODY_PX * k:.0f} px, fine print {FINE_PX * k:.0f} px")
    if w < h:
        warns.append(f"slides are {w}x{h}, taller than wide: references/slides.md expects 16:9 (1920x1080)")
    for p in pages:
        n = p["page"]
        if p.get("fails"):
            fails.append(f"slide {n}: the audit failed ({len(p['fails'])} hard fail(s)): {p['fails'][0][:90]}")
        if p.get("minFont") and p["minFont"] < BODY_PX * k:
            fails.append(f"slide {n}: text at {p['minFont']} px; a slide's floor is {BODY_PX * k:.0f} px at this width")
        if p.get("minAll") and p["minAll"] < FINE_PX * k:
            fails.append(f"slide {n}: fine print at {p['minAll']} px; its floor is {FINE_PX * k:.0f} px at this width")
        if p.get("words", 0) > MAX_WORDS:
            warns.append(f"slide {n}: {p['words']} words; one claim per slide reads in {MAX_WORDS} or fewer (move the rest to notes)")
        for b in p.get("boxes", []):
            if b["w"] and b["h"] and (b["x"] < EDGE * w or b["y"] < EDGE * h or b["x"] + b["w"] > (1 - EDGE) * w or b["y"] + b["h"] > (1 - EDGE) * h):
                warns.append(f"slide {n}: the {b['role']} box comes within 3% of an edge (a projector or a call window can crop it)")
    titles = {p["page"]: next((b for b in p.get("boxes", []) if b["role"] == "hook"), None) for p in pages}
    for n, t in titles.items():
        if t is None:
            fails.append(f"slide {n} has no title: mark its one claim data-role=\"hook\"")
    if len(pages) > 1:
        body = {n: t for n, t in titles.items() if t and n > 1}
        if len(body) >= 2:
            mx = statistics.median(t["x"] for t in body.values())
            my = statistics.median(t["y"] for t in body.values())
            for n, t in body.items():
                if abs(t["x"] - mx) > LINE_PX or abs(t["y"] - my) > LINE_PX:
                    fails.append(f"slide {n}: the title starts at ({t['x']}, {t['y']}); the deck's title line is at ({mx:.0f}, {my:.0f}), "
                                 f"more than {LINE_PX} px off")
            facts.append(f"title line at ({mx:.0f}, {my:.0f}) on slides 2 to {len(pages)}")
        fams = {}
        for p in pages:
            for f in p.get("families", []):
                fams.setdefault(f, []).append(p["page"])
        if len(fams) > MAX_FAMILIES:
            fails.append(f"{len(fams)} type families across the deck ({', '.join(fams)}); keep {MAX_FAMILIES} or fewer")
        for f, used in fams.items():
            if len(used) == 1 and len(pages) > 2:
                warns.append(f"the family {f} appears on slide {used[0]} only")
        sizes = sorted({s for p in pages for s in p.get("sizes", [])})
        facts.append(f"type sizes across the deck: {', '.join(str(s) for s in sizes)}")
        if len(sizes) > MAX_SIZES:
            warns.append(f"{len(sizes)} type sizes across the deck; a deck holds {MAX_SIZES} or fewer")
    pdf = folder / "carousel.pdf"
    if pdf.exists():
        count = len(re.findall(rb"/Type\s*/Page(?![s\w])", pdf.read_bytes()))
        facts.append(f"carousel.pdf has {count} page(s)")
        if count != len(pages):
            fails.append(f"carousel.pdf has {count} page(s) for {len(pages)} slide(s)")
    else:
        warns.append("no carousel.pdf: render with --pdf to share the deck as one file")
    print(f"== {folder.name}")
    for f in facts:
        print("  ", f)
    for f in fails:
        print("  FAIL", f)
    for x in warns:
        print("  warn", x)
    print("deck: PASS" if not fails else "deck: FAIL")
    return 1 if fails else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
