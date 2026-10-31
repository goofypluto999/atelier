#!/usr/bin/env python3
"""Tests for palette.py: the colour planner. Runs the real CLI into temporary folders, no network. python tests/test_palette.py

P1 a warmer start never crosses the green band, P2 every hue is the brand's, P3 a register that overrides the harmony says so,
P4 --field-page, P5 common-cluster warning, P6 an arc step too small to see, P7 a brand file with no --house keeps its own hues,
P8 a brand of greys gets a grey accent and a NOTE, P9 an input that cannot be planned exits 2 with one line, P10 warmth warms the neutrals,
P11 with no --brand the piece gets its own palette, kept off the specimen palette and the clusters, P12 warmth's own accent is warm,
P13 an own ground keeps clear of a cluster's edge, P14 an own accent keeps clear of its text (both judged on the palette.css palette.py writes).
Exit 1 on the first failure."""
import pathlib
import re
import subprocess
import sys
import tempfile

SKILL = pathlib.Path(__file__).resolve().parent.parent
sys.dont_write_bytecode = True   # importing palette must not leave a __pycache__ in the repo
sys.path.insert(0, str(SKILL / "scripts"))
import palette as pal  # noqa: E402  (colour maths only; the plans below run through the CLI)

PAL = [sys.executable, str(SKILL / "scripts" / "palette.py")]
BRAND = SKILL / "tests" / "fixtures" / "b-brand" / "tokens.css"   # a teal brand with an amber and a glow
TOKENS = pal.read_tokens(BRAND.read_text(encoding="utf-8"))
GREEN = pal.GREEN
FAMILY_TOL = 12   # degrees past a brand colour's own hue that still counts as the same family (rounding to 8 bits moves a pale hue)


def hue_of(hex_):
    return pal.to_lch(pal.hex_to_rgb(hex_))


def run(tmp, *args, ok=True):
    out = pathlib.Path(tmp) / f"out{len(list(pathlib.Path(tmp).glob('out*')))}"
    r = subprocess.run(PAL + list(args) + ["--out", str(out)], capture_output=True, text=True, encoding="utf-8")
    if ok and r.returncode != 0:
        raise AssertionError(f"{args}: {r.stdout}{r.stderr}")
    return r, out


def pages(out):
    """palette.css as {page: {property: value}}"""
    css = (out / "palette.css").read_text(encoding="utf-8")
    return {int(n): dict(re.findall(r"--([\w-]+):\s*(#[0-9a-f]{6})", body)) for n, body in re.findall(r"\.pg-(\d+) \{([^}]*)\}", css)}


def chromatic(page):
    """accent colours of a page worth a hue test: (name, hex, hue) for chroma 0.03 or more"""
    return [(k, v, hue_of(v)[2]) for k, v in page.items() if k.startswith("accent") and hue_of(v)[1] >= 0.03]


def near_family(h, tokens):
    return any(pal.gap(h, hue_of(TOKENS[t])[2]) <= FAMILY_TOL for t in tokens)


TEAL, AMBER = ("house", "teal", "teal-lit"), ("amber", "glow")
RED = SKILL / "tests" / "fixtures" / "g4-red-brand" / "tokens.css"     # --primary red and --secondary orange, no --house
GREY = SKILL / "tests" / "fixtures" / "g4-grey-brand" / "tokens.css"   # greys only, no --house


def near_hex(h, hexes):
    return any(pal.gap(h, hue_of(x)[2]) <= FAMILY_TOL for x in hexes)


def test_p1_warm_start_stays_off_the_greens(tmp):
    # the defect: a teal brand turned toward amber the short way went through mint (#9ed4aa, hue 151) and never looked warm
    r, out = run(tmp, "--register", "dry", "--harmony", "complementary", "--arc", "cooldown", "--pages", "5", "--ground", "dark", "--brand", str(BRAND))
    p = pages(out)
    assert "#9ed4aa" not in (out / "palette.css").read_text(), "the mint accent is back"
    for n, page in p.items():
        for k, v, h in chromatic(page):
            assert not GREEN[0] <= h <= GREEN[1], f"page {n} {k} {v} has hue {h:.0f}, inside the green band {GREEN}"
    first, last = hue_of(p[1]["accent"])[2], hue_of(p[5]["accent"])[2]
    assert near_family(first, AMBER) and near_family(last, TEAL), f"warm start {first:.0f} should be the brand's amber, the end {last:.0f} its teal"
    assert pal.delta_e(pal.hex_to_rgb(p[1]["accent"]), pal.hex_to_rgb(p[5]["accent"])) > 0.1, "the warm start is not visibly warmer than the end"
    # a brand with no warm colour: a small nudge inside its own family, lighter, still off the greens
    teal_only = pathlib.Path(tmp) / "teal-only.css"
    teal_only.write_text(":root { --house: #075055; --teal: #206b6f; --teal-lit: #5fb3b6; --night: #0d0e10; --paper: #f4f1ea; --ink: #2e2c28; --cream: #f7f4ee; }")
    r, out = run(tmp, "--register", "unease-to-control", "--harmony", "complementary", "--arc", "cooldown", "--pages", "5", "--ground", "dark", "--brand", str(teal_only))
    p = pages(out)
    hs = [hue_of(p[n]["accent"])[2] for n in sorted(p)]
    assert all(not GREEN[0] <= h <= GREEN[1] for h in hs), f"nudge crossed the green band: {hs}"
    assert all(near_family(h, TEAL) for h in hs), f"nudge left the teal family: {hs}"
    assert hs[0] < hs[-1] and hue_of(p[1]["accent"])[0] > hue_of(p[5]["accent"])[0], f"the start is not warmer (hue {hs[0]:.0f}) and lighter than the end"
    print("PASS P1 cooldown: amber start then teal for a brand with amber, a nudge inside the teal family without; no hue in the green band")


def test_p2_every_hue_is_the_brands(tmp):
    n = 0
    for register in ("unease-to-control", "curiosity", "play", "relief", "warmth"):
        for harmony in ("analogous", "complementary", "split", "triadic"):
            for arc in ("steady", "cooldown", "single-flash", "chapters"):
                r, out = run(tmp, "--register", register, "--harmony", harmony, "--arc", arc, "--pages", "6", "--ground", "dark", "--brand", str(BRAND))
                for num, page in pages(out).items():
                    for k, v, h in chromatic(page):
                        assert near_family(h, TEAL) or near_family(h, AMBER), f"{register} {harmony} {arc} page {num} {k} {v} hue {h:.0f} is in no brand family"
                        n += 1
                    gl = hue_of(page["ground"])
                    assert gl[1] < 0.03 or near_family(gl[2], TEAL), f"{register} {harmony} {arc} page {num} ground {page['ground']} hue {gl[2]:.0f} is no brand hue"
    # complementary with an amber in the brand gives the amber, not a plum or pink
    r, out = run(tmp, "--register", "curiosity", "--harmony", "complementary", "--pages", "2", "--brand", str(BRAND))
    assert near_family(hue_of(pages(out)[1]["accent-2"])[2], AMBER), "the complement of teal should be the brand's amber"
    # --taste may add a hue, and the output says so
    r, out = run(tmp, "--taste", "white-link-blue", "--register", "curiosity", "--harmony", "complementary", "--pages", "2")
    assert "taste palette" in r.stdout and "is new" in r.stdout, r.stdout
    print(f"PASS P2 {n} accent colours over 80 plans: all in a brand family; the complement is the brand's amber; --taste says when it adds a hue")


def test_p3_register_overrides_harmony(tmp):
    r, out = run(tmp, "--register", "dry", "--harmony", "complementary", "--arc", "steady", "--pages", "3", "--brand", str(BRAND))
    line = next((x for x in r.stdout.splitlines() if x.startswith("harmony complementary overridden by register dry:")), None)
    assert line, "no override line on stdout:\n" + r.stdout
    assert line in (out / "colour-plan.md").read_text(encoding="utf-8"), "the override line is not in colour-plan.md"
    assert not any("accent-2" in p for p in pages(out).values()), "an accent-2 was written for a monochrome register"
    assert all("accent-2" not in v for v in (out / "palette.css").read_text().splitlines()[1:]), "palette.css still names accent-2"
    # the other monochrome registers, and a register that keeps the dealt harmony
    for reg in ("wonder", "craft-pride", "rigour"):
        r, out = run(tmp, "--register", reg, "--harmony", "split", "--brand", str(BRAND))
        assert f"harmony split overridden by register {reg}" in r.stdout, reg
    r, out = run(tmp, "--register", "unease-to-control", "--harmony", "complementary", "--arc", "cooldown", "--pages", "4", "--brand", str(BRAND))
    assert "overridden" not in r.stdout and all("accent-2" in p for p in pages(out).values()), "a register that allows the harmony was overridden"
    r, out = run(tmp, "--register", "dry", "--harmony", "monochrome", "--brand", str(BRAND))
    assert "overridden" not in r.stdout, "monochrome overridden by monochrome"
    print("PASS P3 monochrome registers print and record 'harmony <h> overridden by register <r>' and write no accent-2; other registers keep the harmony")


def test_p4_field_page(tmp):
    base = ("--register", "unease-to-control", "--harmony", "complementary", "--arc", "cooldown", "--pages", "5", "--ground", "dark", "--brand", str(BRAND))
    r, out = run(tmp, *base)
    assert {p["ground"] for p in pages(out).values()} == {TOKENS["night"]}, "cooldown gave a field page without --field-page"
    r, out = run(tmp, *base, "--field-page", "3")
    p = pages(out)
    assert p[3]["ground"] != TOKENS["night"] and p[3]["accent"] == TOKENS["cream"], f"page 3 is not the field page: {p[3]}"
    assert [n for n in p if p[n]["ground"] != TOKENS["night"]] == [3], "more than page 3 changed ground"
    assert "Field page(s) 3" in (out / "colour-plan.md").read_text(encoding="utf-8")
    r, out = run(tmp, *base, "--field-page", "2", "5")
    assert [n for n, x in pages(out).items() if x["ground"] != TOKENS["night"]] == [2, 5], "a list of field pages was not honoured"
    # any arc: single-flash moves its one field page to the chosen one; steady gets one
    r, out = run(tmp, "--register", "wonder", "--arc", "single-flash", "--pages", "5", "--ground", "dark", "--field-page", "1", "--brand", str(BRAND))
    assert [n for n, x in pages(out).items() if x["ground"] != TOKENS["night"]] == [1], "single-flash kept its own field page beside the chosen one"
    r, out = run(tmp, "--register", "wonder", "--arc", "steady", "--pages", "4", "--ground", "paper", "--field-page", "4", "--brand", str(BRAND))
    assert [n for n, x in pages(out).items() if x["ground"] != TOKENS["paper"]] == [4], "steady did not give page 4 the field"
    r, out = run(tmp, "--register", "wonder", "--pages", "3", "--field-page", "4", "--brand", str(BRAND), ok=False)
    assert r.returncode != 0 and "--field-page" in (r.stdout + r.stderr), "a page outside the set was accepted"
    print("PASS P4 --field-page N gives page N the field colour on cooldown, steady and single-flash; lists work; out of range refused; default unchanged")


def test_p5_common_cluster(tmp):
    # a piece with no --brand gets its own palette, made to stay out of the clusters: no cluster line on any ground
    for g in ("dark", "paper", "field"):
        r, out = run(tmp, "--register", "craft-pride", "--ground", g)
        assert "in cluster" not in r.stdout, f"the own palette on a {g} ground sits in a common cluster:\n" + r.stdout
    # a cream paper (the fixture brand) warns when the axes are free, and is only noted when it is the user's --brand
    lines = pal.plan(pal.brand_from_tokens(BRAND), "craft-pride", "monochrome", "steady", 1)[-1]["lines"]
    assert any(x.startswith("WARN") and "cluster 1" in x for x in lines), "a cream paper raised no cluster warning: " + str(lines)
    r, out = run(tmp, "--register", "craft-pride", "--brand", str(BRAND))
    assert "WARN" not in r.stdout and "fine if it is your brand" in r.stdout, "a user's own brand was warned instead of noted:\n" + r.stdout
    assert "cluster 1" in (out / "colour-plan.md").read_text(encoding="utf-8"), "the cluster line is not in colour-plan.md"
    # a dark ground by itself is not a cluster; near-black with acid green or vermilion is (checked on the matcher)
    r, out = run(tmp, "--register", "wonder", "--arc", "steady", "--pages", "2")
    assert "in cluster" not in r.stdout, "a plain dark plan was flagged:\n" + r.stdout
    data = pal.json.loads((pal.DATA / "colour.json").read_text(encoding="utf-8"))["clusters"]

    def row(g, a):
        return {"page": 1, "g": pal.hex_to_rgb(g), "acc": pal.hex_to_rgb(a)}

    assert pal.cluster_notes([row("#0c0c0d", "#b6ff00")], data, False)[0].startswith("WARN") and "cluster 2" in pal.cluster_notes([row("#0c0c0d", "#b6ff00")], data, False)[0]
    assert pal.cluster_notes([row("#0c0c0d", "#e34234")], data, False), "near-black with vermilion was not flagged"
    assert not pal.cluster_notes([row("#0c0c0d", "#5fb3b6")], data, False), "near-black with teal was flagged"
    assert pal.cluster_notes([row("#f5f0e6", "#13575c")], data, False), "a warm cream was not flagged"
    assert not pal.cluster_notes([row("#e8eef3", "#13575c")], data, False) and not pal.cluster_notes([row("#f0f4f8", "#13575c")], data, False), "a cool paper was flagged"
    assert not pal.cluster_notes([row("#fafafa", "#13575c")], data, False), "a neutral white was flagged"
    print("PASS P5 the own palette (no --brand) is in no cluster on any ground; a cream paper warns (cluster 1), and with --brand it is a note; near-black with acid green or vermilion is cluster 2; a plain dark plan is clean")


def test_p6_arc_step(tmp):
    r, out = run(tmp, "--register", "unease-to-control", "--harmony", "complementary", "--arc", "cooldown", "--pages", "9", "--ground", "dark", "--brand", str(BRAND))
    assert "arc steps" not in r.stdout, "a visible arc was warned:\n" + r.stdout
    brand = pal.brand_from_tokens(BRAND)
    brand["families"] = [f for f in brand["families"] if f["mid"] > 150]   # no warm colour: the step then rests on a nudge, lightness and chroma
    old = pal.LIFT
    pal.LIFT = 0
    try:
        lines = pal.plan(brand, "dry", "monochrome", "cooldown", 5, "dark", (), True)[6]["lines"]
    finally:
        pal.LIFT = old
    assert any(x.startswith("WARN arc steps too small to see") and str(pal.STEP_MIN) in x for x in lines), lines
    rows = pal.plan(brand, "unease-to-control", "monochrome", "cooldown", 5, "dark", (), True)[3]
    steps = [pal.delta_e(a["acc"], b["acc"]) for a, b in zip(rows, rows[1:]) if a["act"] != b["act"]]
    assert steps and min(steps) >= pal.STEP_MIN, f"the planned steps {steps} are under {pal.STEP_MIN}"
    print(f"PASS P6 arc steps are at least {pal.STEP_MIN} OKLab apart (planned: {', '.join(f'{s:.3f}' for s in steps)}); a flat step prints WARN")


def test_p7_no_house_keeps_the_brands_hues(tmp):
    # the defect: a red and orange brand without --house got the default blue accent on every page
    t = pal.read_tokens(RED.read_text(encoding="utf-8"))
    hexes = [t["primary"], t["secondary"]]
    n = 0
    for register in ("unease-to-control", "curiosity", "relief"):
        for harmony in ("analogous", "complementary", "split", "triadic"):
            for arc in ("steady", "cooldown", "single-flash"):
                r, out = run(tmp, "--register", register, "--harmony", harmony, "--arc", arc, "--pages", "5", "--brand", str(RED))
                for num, page in pages(out).items():
                    for k, v, h in chromatic(page):
                        assert near_hex(h, hexes), f"{register} {harmony} {arc} page {num} {k} {v} hue {h:.0f} is neither the red nor the orange"
                        n += 1
                    gl = hue_of(page["ground"])
                    assert gl[1] < 0.03 or near_hex(gl[2], hexes), f"{register} {harmony} {arc} page {num} ground {page['ground']} hue {gl[2]:.0f} is no brand hue"
    # the colour the file names for the brand wins over a more chromatic one; the line says so, on stdout and in colour-plan.md
    r, out = run(tmp, "--register", "craft-pride", "--brand", str(RED))
    assert near_hex(chromatic(pages(out)[1])[0][2], [t["primary"]]), "the accent is not the --primary red"
    assert "NOTE no --house" in r.stdout and "--primary" in r.stdout, r.stdout
    assert "NOTE no --house" in (out / "colour-plan.md").read_text(encoding="utf-8"), "the line is not in colour-plan.md"
    swapped = pathlib.Path(tmp) / "swapped.css"   # the primary is the less chromatic of the two: the name still decides
    swapped.write_text(f":root {{ --primary: {t['secondary']}; --secondary: {t['primary']}; --night: #15110f; --paper: #f6f1ea; --ink: #2b2522; --cream: #fbf7f1; }}")
    r, out = run(tmp, "--register", "craft-pride", "--brand", str(swapped))
    assert near_hex(chromatic(pages(out)[1])[0][2], [t["secondary"]]), "the accent is not the file's --primary orange"
    # with no such name, the most chromatic colour wins
    anon = pathlib.Path(tmp) / "anon.css"
    anon.write_text(f":root {{ --rust: {t['secondary']}; --flame: {t['primary']}; --night: #15110f; --paper: #f6f1ea; --ink: #2b2522; --cream: #fbf7f1; }}")
    assert pal.to_lch(pal.hex_to_rgb(t["primary"]))[1] > pal.to_lch(pal.hex_to_rgb(t["secondary"]))[1], "fixture changed: the red is no longer the more chromatic"
    r, out = run(tmp, "--register", "craft-pride", "--brand", str(anon))
    assert near_hex(chromatic(pages(out)[1])[0][2], [t["primary"]]) and "--flame" in r.stdout and "most chromatic" in r.stdout, r.stdout
    # a tinted ground is the accent only when nothing else has a hue
    navy = pathlib.Path(tmp) / "navy.css"
    navy.write_text(":root { --night: #0b1d3a; --paper: #f2f2f0; --ink: #262626; --cream: #fafafa; --steel: #8a8a8a; }")
    r, out = run(tmp, "--register", "craft-pride", "--brand", str(navy))
    assert near_hex(chromatic(pages(out)[1])[0][2], ["#0b1d3a"]) and "--night" in r.stdout, r.stdout
    # a brand that names its --house, and the bundled one, are not told anything
    for args in (("--brand", str(BRAND)), ()):
        r, out = run(tmp, "--register", "craft-pride", *args)
        assert "no --house" not in r.stdout, r.stdout
    print(f"PASS P7 no --house: {n} accent colours over 36 plans stay red or orange; the named primary beats a more chromatic colour, else the most chromatic wins; one NOTE line says which")


def test_p8_grey_brand_gets_a_grey_accent(tmp):
    # the defect: a brand of greys got the default blue, or an invented mustard
    n = 0
    for register in ("wonder", "dry", "craft-pride", "relief", "unease-to-control", "curiosity", "warmth", "rigour", "play"):
        for arc in ("steady", "dawn", "cooldown", "single-flash", "chapters"):
            r, out = run(tmp, "--register", register, "--harmony", "complementary", "--arc", arc, "--pages", "5", "--brand", str(GREY))
            assert r.stdout.count("NOTE no --house") == 1 and "neutral grey" in r.stdout, f"{register} {arc}:\n{r.stdout}"
            for num, page in pages(out).items():
                for k, v in page.items():
                    assert hue_of(v)[1] < 0.01, f"{register} {arc} page {num} {k} {v} has chroma {hue_of(v)[1]:.3f}: a hue was invented"
                    n += 1
    plan = (out / "colour-plan.md").read_text(encoding="utf-8")
    assert "NOTE no --house" in plan and "Hues: none" in plan, "colour-plan.md does not say the plan has no hue"
    print(f"PASS P8 grey-only brand: {n} colours over 45 plans are all grey, exit 0, one NOTE (add --house to give it a hue)")


def test_p9_bad_input_exits_2(tmp):
    cases = [("--register", "nope"), ("--harmony", "nope"), ("--arc", "nope"), ("--brand", str(pathlib.Path(tmp) / "missing.css")),
             ("--pages", "0"), ("--pages", "-3")]
    for args in cases:
        r, out = run(tmp, *args, ok=False)
        err = r.stderr.strip().splitlines()
        assert r.returncode == 2, f"{args}: exit {r.returncode}, want 2:\n{r.stdout}{r.stderr}"
        assert "Traceback" not in r.stderr and len(err) == 1 and args[0] in err[0], f"{args}: want one line naming the flag:\n{r.stderr}"
        assert not (out / "palette.css").exists(), f"{args}: a plan was written for a bad input"
    print(f"PASS P9 {len(cases)} bad inputs (register, harmony, arc, missing brand file, pages 0 and below): exit 2, one line, no traceback, nothing written")


def test_p10_warmth_warms_the_neutrals(tmp):
    # the defect (30 Oct 2026 run, friday-plain): register warmth, recipe warm-neutrals ("paper, warmed", temperature warm),
    # and the plan still put the page on the cool #f1f2f4 with cool ink; two critics marked the colour down for it
    cool = pal.read_tokens((SKILL / "assets" / "tokens.css").read_text(encoding="utf-8"))
    warm = lambda hex_: hue_of(hex_)[1] >= 0.008 and pal.gap(hue_of(hex_)[2], pal.WARM) <= 45
    data = pal.json.loads((pal.DATA / "colour.json").read_text(encoding="utf-8"))["clusters"]
    n = 0
    for g, ground_token in (("paper", "paper"), ("dark", "night")):
        for arc in ("steady", "single-flash", "chapters"):
            r, out = run(tmp, "--register", "warmth", "--harmony", "split", "--arc", arc, "--pages", "3", "--ground", g)
            assert "NOTE warm neutrals" in r.stdout and "WARN" not in r.stdout, r.stdout
            for num, page in pages(out).items():
                if hue_of(page["ground"])[1] >= 0.03:
                    continue   # a colour-field page keeps its own colour
                assert page["ground"] not in (cool["paper"], cool["night"]) and warm(page["ground"]) and warm(page["text"]), f"{g} {arc} page {num}: {page} is not warm"
                assert not any(pal.in_ground(pal.hex_to_rgb(page["ground"]), c["ground"]) for c in data if c["ground_alone"]), f"{g} {arc} page {num}: {page['ground']} is the warm cream of cluster 1"
                assert pal.contrast(pal.hex_to_rgb(page["text"]), pal.hex_to_rgb(page["ground"])) >= 7, f"{g} {arc} page {num}: text contrast fell"
                n += 1
    # another register gets its own neutrals, not warm ones; a brand keeps its own and is told so
    r, out = run(tmp, "--register", "craft-pride", "--ground", "paper")
    assert pages(out)[1]["ground"] != cool["paper"] and not warm(pages(out)[1]["ground"]) and "warm neutrals" not in r.stdout, r.stdout
    r, out = run(tmp, "--register", "warmth", "--ground", "paper", "--brand", str(BRAND))
    assert pages(out)[1]["ground"] == TOKENS["paper"] and "the brand's own paper, ink and night are kept" in r.stdout, r.stdout
    assert "warm neutrals" in (out / "colour-plan.md").read_text(encoding="utf-8"), "the line is not in colour-plan.md"
    print(f"PASS P10 register warmth: {n} paper and dark grounds over 6 plans and their text are warm (hue near amber), out of cluster 1, text at 7:1 or more; craft-pride's own neutrals are not warm; a brand keeps its own and a NOTE says so")


SPECIMEN = pal.specimen_colours()   # assets/tokens.css by role: the colours every specimen page is drawn in


def own_rows(register, harmony, arc, pages_, ground):
    return pal.plan(pal.own_brand(register, harmony, arc), register, harmony, arc, pages_, ground)[3]


def far(colour, role):
    return min(pal.delta_e(colour, s) for s in SPECIMEN[role])


def test_p11_own_palette_leaves_the_specimens(tmp):
    # the defect (30 Oct 2026 run of the README example): with no --brand the plan's paper and ink were the specimens' own #f1f2f4 and #1c1e23 and its accent
    # a blue 0.05 from their #143ca1, so the critics read every unbranded page as the specimen
    colour = pal.json.loads((pal.DATA / "colour.json").read_text(encoding="utf-8"))
    regs = pal.json.loads((pal.DATA / "registers.json").read_text(encoding="utf-8"))
    assert set(colour["own"]["registers"]) == set(regs), "every register needs its own palette in data/colour.json \"own\""
    n, worst = 0, {"ground": 1, "text": 1, "accent": 1}
    for register in regs:
        for harmony in (h["id"] for h in colour["harmonies"]):
            for arc in (a["id"] for a in colour["arcs"]):
                for ground in ("paper", "dark", "field"):
                    rows = own_rows(register, harmony, arc, 4, ground)
                    lines = pal.cluster_notes(rows, colour["clusters"], False)
                    assert not lines, f"{register} {harmony} {arc} {ground}: {lines}"
                    for r in rows:
                        where = f"{register} {harmony} {arc} {ground} page {r['page']}"
                        accents = [r["acc"]] + ([r["acc2"]] if r["acc2"] else []) if r["ground"] != "field" else [r["acc2"]] if r["acc2"] else []
                        for role, c, need in [("ground", r["g"], pal.SPEC_MIN), ("text", r["text"], pal.SPEC_MIN)] + [("accent", a, pal.ACC_MIN) for a in accents]:
                            d = far(c, role)
                            worst[role] = min(worst[role], d)
                            assert d >= need, f"{where}: {role} {pal.rgb_to_hex(c)} is {d:.3f} from the specimen's, under {need}"
                        assert pal.contrast(r["text"], r["g"]) >= 4.5, f"{where}: text contrast {pal.contrast(r['text'], r['g']):.1f}"
                        n += 1
    # the colours differ from one register to the next, and from one harmony or arc to the next inside a register
    accents = {pal.own_brand(r, "complementary", "steady")["accent"] for r in regs}
    assert len(accents) == len(regs), f"two registers share an accent: {accents}"
    assert len({pal.own_brand("curiosity", h["id"], "steady")["accent"] for h in colour["harmonies"]}) >= 4, "the harmony does not move the accent"
    # the CLI says what it did, and a brand file still decides everything
    r, out = run(tmp, "--register", "dry", "--harmony", "split", "--arc", "steady", "--pages", "2")
    assert "NOTE no --brand: this piece's own palette" in r.stdout and "own palette" in (out / "colour-plan.md").read_text(encoding="utf-8"), r.stdout
    r, out = run(tmp, "--register", "dry", "--harmony", "split", "--arc", "steady", "--pages", "2", "--brand", str(BRAND))
    assert "own palette" not in r.stdout and pages(out)[1]["ground"] == TOKENS["paper"], r.stdout
    print(f"PASS P11 own palette (no --brand), {n} pages over 9 registers x 5 harmonies x 5 arcs x 3 grounds: no cluster; every ground and text "
          f"colour {pal.SPEC_MIN} or more OKLab from the specimens' (closest {worst['ground']:.3f} and {worst['text']:.3f}), every accent {pal.ACC_MIN} "
          f"or more from theirs (closest {worst['accent']:.3f}); 9 registers, 9 accents; the harmony moves the accent; --brand still wins")


def test_p12_warmth_accent_is_warm(tmp):
    # the defect (30 Oct 2026 run, friday-warm): the warm register warmed the paper and ink, but its accent stayed a cool navy (#214e82, hue 255)
    rec = pal.json.loads((pal.DATA / "colour.json").read_text(encoding="utf-8"))["recipes"]["warm-neutrals"]
    lo, hi = rec["accent_C"]
    warm_hue = lambda h: pal.gap(h, pal.WARM) <= 60   # reds, oranges and yellows: 10 to 130 deg in OKLCH
    n = 0
    for harmony in ("analogous", "complementary", "split", "monochrome"):
        for arc in ("steady", "single-flash", "chapters", "dawn"):
            for ground in ("paper", "dark"):
                r, out = run(tmp, "--register", "warmth", "--harmony", harmony, "--arc", arc, "--pages", "3", "--ground", ground)
                assert "a warm accent" in r.stdout, r.stdout
                for num, page in pages(out).items():
                    if pal.contrast(pal.hex_to_rgb(page["accent"]), pal.hex_to_rgb(page["text"])) < 1.1:
                        continue   # a field page: its accent is the text colour
                    L, C, h = hue_of(page["accent"])
                    assert warm_hue(h) and pal.gap(h, 255) > 90, f"{harmony} {arc} {ground} page {num}: accent {page['accent']} hue {h:.0f} is not warm"
                    if arc == "steady":
                        assert lo - 0.005 <= C <= hi + 0.005, f"{harmony} {ground} page {num}: accent chroma {C:.3f} is outside the recipe's {rec['accent_C']}"
                    if harmony == "analogous":
                        assert warm_hue(hue_of(page["accent-2"])[2]), f"{arc} {ground} page {num}: accent-2 {page['accent-2']} is not warm"
                    n += 1
    # a brand keeps its own hues under warmth (palette.py's brand rules): the teal fixture's accent stays teal or amber
    r, out = run(tmp, "--register", "warmth", "--harmony", "analogous", "--pages", "2", "--brand", str(BRAND))
    for num, page in pages(out).items():
        for k, v, h in chromatic(page):
            assert near_family(h, TEAL) or near_family(h, AMBER), f"brand page {num} {k} {v} hue {h:.0f} left the brand's families"
    print(f"PASS P12 register warmth with no --brand: {n} accents over 32 plans are warm (hue within 60 deg of amber), chroma inside the recipe's {rec['accent_C']} on a steady arc, "
          "accent-2 warm under the recipe's analogous harmony; a brand keeps its own hues")


# The rules P13 and P14 hold palette.py to, as numbers (README "What the scripts check", CHANGELOG): an own palette's ground keeps 0.04 OKLab past
# a cluster's edge and 15 degrees past its hue range, and its accent 0.20 OKLab from the page's text at 4.5:1 or more on the ground.
CLUSTER_PAD, HUE_PAD, ACC_FROM_TEXT = 0.04, 15, 0.20


def own_pages(tmp, register, harmony, arc, n, ground):
    """palette.py's own palette for one plan, read back from the palette.css it writes: [(page, ground, text, accent)], field pages left out
    (a field page's ground is the colour field, mid lightness, between the dark and paper grounds)."""
    r, out = run(tmp, "--register", register, "--harmony", harmony, "--arc", arc, "--pages", str(n), "--ground", ground)
    rows = [(k, v["ground"], v["text"], v["accent"]) for k, v in sorted(pages(out).items())]
    return r, [x for x in rows if not 0.35 < hue_of(x[1])[0] < 0.8]


def in_cluster(hex_, gd):
    """A ground inside a cluster's ground, widened by the pads: within its OKLab distance, and in its hue range when it has one."""
    rgb, (_, c, h) = pal.hex_to_rgb(hex_), hue_of(hex_)
    near = pal.delta_e(rgb, pal.hex_to_rgb(gd["hex"])) <= gd["de"] + CLUSTER_PAD
    return near and ("hue" not in gd or (gd["hue"][0] - HUE_PAD <= h <= gd["hue"][1] + HUE_PAD and c >= gd["min_c"]))


def test_p13_own_ground_keeps_clear_of_a_cluster(tmp):
    # the defect (30 Oct 2026 run, friday-warm): the own warm paper #efe4dc sat 0.034 OKLab from cluster 1's cream #f4f1ea (radius 0.03) at hue 59,
    # one degree under the cluster's hue range, so no check fired; the critic read it as the warm-cream cluster
    clusters = pal.json.loads((pal.DATA / "colour.json").read_text(encoding="utf-8"))["clusters"]
    regs = list(pal.json.loads((pal.DATA / "registers.json").read_text(encoding="utf-8")))
    n = 0
    for register in regs:
        for harmony in ("analogous", "complementary"):
            for arc in ("steady", "chapters"):
                for ground in ("paper", "dark"):
                    _, rows = own_pages(tmp, register, harmony, arc, 3, ground)
                    for page, g, _, _ in rows:
                        for c in clusters:
                            gd = c["ground"]
                            assert not in_cluster(g, gd), (f"{register} {harmony} {arc} {ground} page {page}: palette.py wrote ground {g}, "
                                                           f"{pal.delta_e(pal.hex_to_rgb(g), pal.hex_to_rgb(gd['hex'])):.3f} from cluster {c['id']}'s {gd['hex']}, under {gd['de']} + {CLUSTER_PAD}")
                        n += 1
    _, rows = own_pages(tmp, "warmth", "analogous", "steady", 1, "paper")
    paper = rows[0][1]
    d = pal.delta_e(pal.hex_to_rgb(paper), pal.hex_to_rgb("#f4f1ea"))
    assert d >= 0.03 + CLUSTER_PAD, f"palette.py wrote the warm paper {paper}, {d:.3f} from the cream"
    print(f"PASS P13 own palette: {n} paper and dark grounds palette.py wrote over {len(regs)} registers keep {CLUSTER_PAD} OKLab past each cluster's edge and {HUE_PAD} deg past its hue range; the warm paper is {paper}, {d:.3f} from the cream")


def test_p14_own_accent_is_not_ink(tmp):
    # the defect (30 Oct 2026 run, friday-warm): the own accent #77363b sat 0.160 OKLab from its ink #32261d (chroma 0.09), and the critic read the
    # underline as a dark brown line; accents 0.221 and 0.239 from their ink read as accents
    regs = list(pal.json.loads((pal.DATA / "registers.json").read_text(encoding="utf-8")))
    n, worst = 0, 1
    for register in regs:
        for harmony in ("analogous", "monochrome", "split"):
            for ground in ("paper", "dark"):
                _, rows = own_pages(tmp, register, harmony, "steady", 2, ground)
                for page, g, text, acc in rows:
                    d, cr = pal.delta_e(pal.hex_to_rgb(acc), pal.hex_to_rgb(text)), pal.contrast(pal.hex_to_rgb(acc), pal.hex_to_rgb(g))
                    worst = min(worst, d)
                    assert d >= ACC_FROM_TEXT and cr >= 4.5, f"{register} {harmony} {ground} page {page}: palette.py wrote accent {acc}, {d:.3f} from the text {text}, contrast {cr:.1f}:1 on {g}"
                    n += 1
    r, rows = own_pages(tmp, "warmth", "analogous", "steady", 1, "paper")
    _, _, text, acc = rows[0]
    d = pal.delta_e(pal.hex_to_rgb(acc), pal.hex_to_rgb(text))
    assert d >= ACC_FROM_TEXT and "WARN" not in r.stdout, r.stdout
    print(f"PASS P14 own palette: {n} accents palette.py wrote over {len(regs)} registers sit {ACC_FROM_TEXT} OKLab or more from their text (closest {worst:.3f}) at 4.5:1 or more on the ground; the warm accent is {acc}, {d:.3f} from its ink {text}")


def main():
    with tempfile.TemporaryDirectory() as tmp:
        for t in (test_p1_warm_start_stays_off_the_greens, test_p2_every_hue_is_the_brands, test_p3_register_overrides_harmony,
                  test_p4_field_page, test_p5_common_cluster, test_p6_arc_step, test_p7_no_house_keeps_the_brands_hues,
                  test_p8_grey_brand_gets_a_grey_accent, test_p9_bad_input_exits_2, test_p10_warmth_warms_the_neutrals,
                  test_p11_own_palette_leaves_the_specimens, test_p12_warmth_accent_is_warm,
                  test_p13_own_ground_keeps_clear_of_a_cluster, test_p14_own_accent_is_not_ink):
            try:
                t(tmp)
            except AssertionError as e:
                print(f"FAIL {t.__name__}: {e}")
                return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
