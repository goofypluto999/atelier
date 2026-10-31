#!/usr/bin/env python3
"""End-to-end tests for compose.py: runs in a temporary project folder, no network. python tests/test_composer.py"""
import base64
import contextlib
import hashlib
import importlib.util
import json
import os
import pathlib
import re
import shutil
import subprocess
import sys
import tempfile
import time
import urllib.parse
import urllib.request

SKILL = pathlib.Path(__file__).resolve().parent.parent
C = [sys.executable, str(SKILL / "scripts" / "compose.py")]
sys.path.insert(0, str(SKILL / "scripts"))
import compose  # noqa: E402  (only its pure parsing and data functions are called here; every command runs as a subprocess)
CRIT = {"atoms": "coverage specificity sourced surprise", "lenses": "distinctness insight", "angles": "novelty truth relevance intrigue tone",
        "genome": "coherence feasibility", "sections": "one-job proof momentum arc", "copy": "clarity voice sins",
        "visual": "idea hook hierarchy craft colour distinct", "final": "depth intrigue distinct craft"}
INDEP = {"angles", "sections", "copy", "visual", "final"}


# R14: each test deals and delivers in a project of its own. A deal weighs the project's memory (.atelier/history.jsonl), and the unseeded
# pieces another test delivered there moved seeded deals from run to run (r9b, r9 render and r11 each failed that way). run() refuses
# a deal, a delivery or a coverage read in a project that the running test does not own.
PROJECTS = {}         # project folder -> the test that owns it
CURRENT = ["main"]    # the test running now
MEMORY = {"deal", "deliver", "coverage"}


def fresh_project():
    """An empty project folder for the running test (own_project removes it when the test ends)."""
    p = pathlib.Path(tempfile.mkdtemp(prefix=f"atelier-{CURRENT[0]}-")).resolve()
    PROJECTS[p] = CURRENT[0]
    return p


@contextlib.contextmanager
def own_project(name):
    """Run a block as test `name` in a fresh project it owns; that project and every fresh_project() the block made are removed after."""
    prev, CURRENT[0] = CURRENT[0], name
    try:
        yield fresh_project()
    finally:
        CURRENT[0] = prev
        for p in [p for p, who in PROJECTS.items() if who == name]:
            shutil.rmtree(p, ignore_errors=True)
            del PROJECTS[p]


def owner(cwd):
    """The test that owns the project a folder is in, or None."""
    c = pathlib.Path(cwd).resolve()
    return next((PROJECTS[p] for p in (c, *c.parents) if p in PROJECTS), None)


def run(cwd, *args, ok=True):
    if args and args[0] in MEMORY:
        who = owner(cwd)
        assert who == CURRENT[0], (f"{CURRENT[0]} ran '{args[0]}' in {'the project of ' + who if who else 'a folder no test owns'}: a deal weighs "
                                   "the project's memory, so each test deals in its own (own_project, fresh_project)")
    r = subprocess.run(C + list(args), cwd=cwd, capture_output=True, text=True)
    if ok and r.returncode != 0:
        raise AssertionError(f"{args}: {r.stdout}{r.stderr}")
    return r


def verdict(path, stage, score, word=None, scores=None, slug=None):
    """What a critic agent hands back: a verdict line and one scored line per criterion (scores: a dict that overrides score for some or all).
    slug: the piece it judges, as the art-director heads its entry; every piece needs its own file, so two pieces never share the same bytes."""
    s = {c: score for c in CRIT[stage].split()}
    s.update(scores or {})
    path.write_text((f"## {slug}\n" if slug else "") + f"verdict: {word or ('PASS' if score >= 7 else 'FAIL')}\n" + "\n".join(f"{c}: {s[c]}/10 because the critic read the worksheet and traced the claim to a source" for c in CRIT[stage].split()) + "\n")
    return path


def fresh_render(folder, html="visual.html", fails=(), pages=1, slug=None):
    """What render.mjs --audit leaves next to a page: audit.json and page-NN.png, newer than the page. fails: hard fails on page 1.
    slug: a page built by hand for that piece (no scaffold); its page and renders differ from every other piece's, as real ones do."""
    folder.mkdir(parents=True, exist_ok=True)
    page = folder / html
    if slug or not page.exists():
        page.write_text(f'<section class="page"><!-- built by hand for {slug} --></section>')
    now = time.time()
    os.utime(page, (now - 60, now - 60))
    files = [folder / "audit.json"] + [folder / f"page-{i:02d}.png" for i in range(1, pages + 1)]
    files[0].write_text(json.dumps([{"page": i, "fails": list(fails) if i == 1 else [], "warns": []} for i in range(1, pages + 1)]))
    for f in files[1:]:
        f.write_bytes(f"png {slug}".encode())
    for f in files:
        os.utime(f, (now, now))


def grade(cwd, slug, stage, score, notes_dir, folder=None):
    n = notes_dir / f"{stage}.md"
    n.write_text("\n".join(f"{c}: because the worksheet shows a specific, sourced example on line 3" for c in CRIT[stage].split()))
    scores = ",".join(f"{c}={score}" for c in CRIT[stage].split())
    args = ["grade", slug, stage, "--scores", scores, "--notes", str(n), "--by", "critic" if stage in INDEP else "self"]
    if stage in INDEP:
        args += ["--evidence", str(verdict(notes_dir / f"{slug}-{stage}-critic.md", stage, score, slug=slug))]
    if stage == "visual":   # the visual grade needs a fresh render next to the page
        fresh_render(folder or cwd, slug=slug)
    return run(cwd, *args, ok=False)


def full_piece(cwd, slug, topic, notes):
    run(cwd, "new", slug, "--topic", topic)
    for s in ["atoms", "lenses", "angles", "genome", "sections", "copy", "visual", "final"]:
        if s in {"lenses", "angles", "genome"}:
            run(cwd, "deal", slug, s)
        r = grade(cwd, slug, s, 9, notes)
        assert "PASSED" in r.stdout, r.stdout + r.stderr
        if s == "angles":
            run(cwd, "choose", slug, "angle", "1", "--text", f"{topic} seen through one invoice line")
    run(cwd, "deliver", slug)
    return json.loads((cwd / ".atelier" / "pieces" / slug / "piece.json").read_text())


def piece_json(cwd, slug):
    return json.loads((cwd / ".atelier" / "pieces" / slug / "piece.json").read_text())


def design_piece(cwd, slug, angle, pin, notes, medium="carousel", new_args=(), deal=True):
    """A design-scope piece with its genome dealt and graded: what a host system does before it builds. The host's record has a score line and the angle's own words, no PASS."""
    ops = [o["id"] for o in json.loads((SKILL / "data" / "operators.json").read_text())]
    ev = notes / f"{slug}-record.md"
    ev.write_text(f"score: 8/10\nThe judge kept this angle: {angle}, because it names one object and one gate.\n" * 3)
    run(cwd, "new", slug, "--topic", f"design test {slug}", "--scope", "design", "--medium", medium, *new_args)
    run(cwd, "adopt", slug, "--angle", angle, "--operator", ops[0], "--evidence", str(ev), "--pin", pin)
    if deal:
        run(cwd, "deal", slug, "genome")
        assert "PASSED" in grade(cwd, slug, "genome", 9, notes).stdout
    return piece_json(cwd, slug).get("genome")


def quick_to_visual(cwd, slug, topic, notes, page):
    """A quick piece taken through atoms, angles and genome, with its page scaffolded to `page` (page None: no page is built): it now waits for the visual grade."""
    run(cwd, "new", slug, "--topic", topic, "--scope", "quick", "--medium", "image")
    assert "PASSED" in grade(cwd, slug, "atoms", 9, notes).stdout
    run(cwd, "deal", slug, "angles")
    qa = notes / f"{slug}-angles.md"
    qa.write_text("\n".join(f"{c}: because the candidate quotes a sourced number on line 2" for c in CRIT["angles"].split()))
    r = run(cwd, "grade", slug, "angles", "--scores", "novelty=9,truth=9,relevance=9,intrigue=9,tone=9", "--notes", str(qa), "--by", "self")
    assert "PASSED" in r.stdout, r.stdout
    run(cwd, "choose", slug, "angle", "1", "--text", f"{topic} as one number")
    run(cwd, "deal", slug, "genome")
    assert "PASSED" in grade(cwd, slug, "genome", 9, notes).stdout
    if page:
        run(cwd, "scaffold", slug, "--out", str(page))
    n = notes / f"{slug}-visual.md"
    n.write_text("\n".join(f"{c}: because the page shows one number as the largest type on the cover" for c in CRIT["visual"].split()))
    return n


def vgrade(cwd, slug, n, ev, scores=None, folder=None):
    """compose.py grade <slug> visual with the given notes and critic file; scores default to 9 for every criterion."""
    scores = scores or ",".join(f"{c}=9" for c in CRIT["visual"].split())
    return run(cwd, "grade", slug, "visual", "--scores", scores, "--notes", str(n), "--by", "critic", "--evidence", str(ev), *(["--folder", str(folder)] if folder else []), ok=False)


def render(html, *extra):
    """node render.mjs <html> --audit, or None when node or Playwright is not installed (those checks are then skipped)."""
    if not shutil.which("node"):
        return None
    r = subprocess.run(["node", str(SKILL / "scripts" / "render.mjs"), str(html), "--audit", *extra], capture_output=True, text=True)
    return None if "Playwright not found" in r.stderr else r


def links(html):
    return re.findall(r'(?:href|src)="([^"]+)"', html) + re.findall(r"""url\(["']?([^)"']+)""", html)


def assert_links_work(html):
    urls = links(html)
    assert urls, "the page has no links at all"
    for u in urls:
        assert u.startswith("file:///"), f"a relative link was left in the page: {u}"
        assert pathlib.Path(urllib.request.url2pathname(urllib.parse.urlparse(u).path)).exists(), f"a link points nowhere: {u}"


def parser_tests():
    """What counts as a verdict and as the critic's own numbers (pure functions of compose.py)."""
    v, ids = compose.verdicts, CRIT["visual"].split()
    assert v("verdict: PASS") == ["PASS"] and v("Verdict: fail") == ["FAIL"] and v("**verdict:** REVISE") == ["REVISE"] and v("visual verdict: FAILED\nnovelty 8 because") == ["FAIL"]
    assert v("verdict: FAIL / score: 3/10") == ["FAIL"] and v("verdict: PASSED (7.9)") == ["PASS"]
    # R3a-2: only a line labelled "verdict" (or "<stage> verdict") states one; the art-director's seen: line quotes the page, whatever it says
    seen = 'page-01.png seen: "FAILED: 3 of 12 nightly jobs"\nseen: "REJECTED"\nquote: "Result: FAIL"\nverdict: PASS\n'
    assert v(seen) == ["PASS"] and compose.critic_read(seen, ids)["verdict"] == "PASS", "a status in capitals on the page was read as the verdict"
    assert v("angle-judge: PASS") == [] and v("status: FAILED") == [] and v("result: FAIL\noverall: REJECT") == [] and v('seen: "verdict: FAIL"') == [], "only a verdict label counts"
    assert v("PASS\n" + "filler " * 40) == [] and v("the design should PASS the swap test") == [] and v("strongest case to reject: Fail fast, then ship") == [], "a bare PASS or FAIL is not a verdict"
    assert v("verdict: PASS | FAIL") == [] and v("verdict: PASS or FAIL") == [] and v("verdict: <one word, PASS or FAIL>") == [] and v("action: proceed | revise | recreate") == [], "a template that offers a choice states none"
    r = compose.critic_read("## 1\nverdict: FAIL / score: 3/10\nfiller", ids)
    assert r["verdict"] == "FAIL" and r["total"] == 3 and r["scores"] == {}, r
    r = compose.critic_read("seen: x\nverdict: PASS\nscores: idea 8, hook 8, hierarchy 8, craft 8, colour 7, distinct 7  total 7.7 (capped: no)", ids)
    assert r["verdict"] == "PASS" and r["total"] == 7.7 and r["scores"] == {"idea": 8, "hook": 8, "hierarchy": 8, "craft": 8, "colour": 7, "distinct": 7}, r
    r = compose.critic_read("- idea: 9/10 because the object is only this subject's\nhook=6 because\nscores: craft=4\ndistinct: no earlier pieces given", ids)
    assert r["scores"] == {"idea": 9, "hook": 6, "craft": 4} and r["verdict"] is None and r["total"] is None, r
    r = compose.critic_read("scores: idea 8, hook 8\nscores: idea 5, hook 9\nverdict: PASS\nverdict: FAIL", ids)
    assert r["scores"]["idea"] == 5 and r["scores"]["hook"] == 8 and r["verdict"] == "FAIL", "the weakest page and the worst verdict decide: " + str(r)
    angles = CRIT["angles"].split()
    two = "## 1\nverdict: FAIL\nscores: novelty 5, truth 9, relevance 8, intrigue 5, tone 8  total 6.5\n## 2\nverdict: PASS\nscores: novelty 9, truth 9, relevance 8, intrigue 8, tone 8  total 8.5\n"
    b = compose.best_entry(two, angles)
    assert b["verdict"] == "PASS" and b["total"] == 8.5 and b["scores"]["novelty"] == 9, "the best candidate stands for the stage: " + str(b)
    assert compose.best_entry("verdict: FAIL\n" + two, angles)["verdict"] == "FAIL", "an overall FAIL above the entries stands"
    print("PASS verdict parsing: bare PASS or FAIL and offered choices state nothing; the worst verdict and the lowest score decide; the best candidate stands for angles")


def evidence_tests(cwd, notes):
    """G1-1: a critic's file cannot be graded upward, and the visual stage needs a fresh render that passed its audit."""
    page = cwd / "pages" / "q2" / "visual.html"
    n = quick_to_visual(cwd, "q2", "a shipping delay seen as one parcel", notes, page)
    folder = page.parent
    filler = "The critic found the hook buried under three competing labels and the colour off its plan. " * 3

    def state():
        return piece_json(cwd, "q2")["stages"]["visual"]

    def refused(r, *words):
        out = r.stdout + r.stderr
        assert r.returncode != 0 and "PASSED" not in r.stdout, "a refused grade passed: " + out
        assert all(w in out for w in words), f"expected {words} in: {out}"
        assert "Traceback" not in out, out
        assert "grades" not in state(), "a refused grade was recorded"
    good = verdict(notes / "q2-good.md", "visual", 9)
    refused(vgrade(cwd, "q2", n, good), "audit.json")                                  # no render at all
    fresh_render(folder, fails=["text overlaps text"])
    refused(vgrade(cwd, "q2", n, good), "does not say PASS")                           # the audit failed
    fresh_render(folder, pages=2)
    (folder / "page-02.png").unlink()
    refused(vgrade(cwd, "q2", n, good), "page-02.png")                                 # a page was not rendered
    fresh_render(folder)
    now = time.time()
    os.utime(page, (now + 30, now + 30))
    refused(vgrade(cwd, "q2", n, good), "older than")                                  # the page was edited after the render
    fresh_render(folder)
    # the shown defect: "verdict: FAIL / score: 3/10" and typed 9s
    f3 = notes / "q2-fail3.md"
    f3.write_text("verdict: FAIL\nscore: 3/10\n" + filler)
    refused(vgrade(cwd, "q2", n, f3), "states a total of 3")
    assert run(cwd, "deliver", "q2", ok=False).returncode != 0, "a piece with a FAIL critic was delivered"
    bare_fail = notes / "q2-barefail.md"
    bare_fail.write_text("verdict: FAIL\n" + filler)
    refused(vgrade(cwd, "q2", n, bare_fail), "verdict is FAIL")                        # a FAIL with no numbers cannot be graded up either
    only_pass = notes / "q2-onlypass.md"
    only_pass.write_text("PASS\n" + filler + " PASS " + filler)
    refused(vgrade(cwd, "q2", n, only_pass), "verdict or score")                      # PASS plus filler
    off = verdict(notes / "q2-off.md", "visual", 9, scores={"idea": 5, "colour": 6})
    refused(vgrade(cwd, "q2", n, off), "idea: the file says 5, --scores says 9", "colour: the file says 6")   # typed numbers differ from the critic's
    # an honest FAIL (a FAIL-level flaw with high scores) is recorded as a failed attempt, never as a pass
    fl = verdict(notes / "q2-flaw.md", "visual", 9, word="FAIL")
    r = vgrade(cwd, "q2", n, fl)
    assert r.returncode == 1 and "PASSED" not in r.stdout and "REVISE" in r.stdout and "verdict is FAIL" in r.stdout, r.stdout + r.stderr
    assert state()["status"] == "revise" and state()["grades"][-1]["passed"] is False and state()["attempts"] == 1
    assert run(cwd, "deliver", "q2", ok=False).returncode != 0
    # the total-only file: the typed scores must reach the file's total
    tot = notes / "q2-total.md"
    tot.write_text("verdict: PASS\nscore: 8.9/10\n" + filler)
    r = vgrade(cwd, "q2", n, tot, scores=",".join(f"{c}=6" for c in CRIT["visual"].split()))
    assert r.returncode != 0 and "states a total of 8.9" in r.stderr and state()["attempts"] == 1, r.stdout + r.stderr
    # the art-director's own line, with the rubric's weights: 7.7, not the plain mean
    ad = notes / "q2-ad.md"
    ad.write_text('## q2\npage-01.png seen: "FAILED: 3 of 12 nightly jobs"\nflaws: []\nverdict: PASS\nscores: idea 8, hook 8, hierarchy 8, craft 8, colour 7, distinct 7  total 7.7 (capped: no)\n' + filler)
    fresh_render(folder)
    r = vgrade(cwd, "q2", n, ad, scores="idea=8,hook=8,hierarchy=8,craft=8,colour=7,distinct=7")
    assert "PASSED" in r.stdout and "visual: 7.7" in r.stdout, "R3a-2: a seen: line of capitals was read as the verdict: " + r.stdout + r.stderr
    assert state()["grades"][-1]["evidence"]["total"] == 7.7 and state()["grades"][-1]["evidence"]["verdict"] == "PASS"
    # R3a-1: the grade stores the sha256 of the page and of every rendered page
    sha = lambda f: hashlib.sha256(f.read_bytes()).hexdigest()
    assert state()["grades"][-1]["evidence"]["render"] == {"html": str(page.resolve()), "html_sha256": sha(page), "pages": {"page-01.png": sha(folder / "page-01.png")}}, state()["grades"][-1]["evidence"]
    # R3a-1: the evidence is bound to the piece. --folder names only the folder scaffold wrote this piece's page into
    page3 = cwd / "pages" / "q3" / "visual.html"
    n3 = quick_to_visual(cwd, "q3", "a parcel that waited at a depot", notes, page3)
    elsewhere = cwd / "elsewhere"
    fresh_render(elsewhere, slug="q3")
    shared = verdict(notes / "shared.md", "visual", 9)   # a verdict with no heading: it carries no slug, so only its bytes bind it
    out = lambda r: r.stdout + r.stderr

    def refused3(slug, r, *words):
        assert r.returncode != 0 and "PASSED" not in r.stdout and "Traceback" not in out(r), "a refused grade passed: " + out(r)
        assert all(w in out(r) for w in words), f"expected {words} in: {out(r)}"
        assert "grades" not in piece_json(cwd, slug)["stages"]["visual"], f"a refused grade was recorded for {slug}"
    refused3("q3", vgrade(cwd, "q3", n3, shared), "audit.json")                         # no render in the scaffolded folder
    refused3("q3", vgrade(cwd, "q3", n3, shared, folder=elsewhere), "is not the folder scaffold wrote")   # a render elsewhere does not count
    refused3("q3", vgrade(cwd, "q3", n3, shared, folder=folder), "is not the folder scaffold wrote", "q3")   # another piece's folder (q2's, with a PASS render)
    fresh_render(page3.parent)
    r = vgrade(cwd, "q3", n3, shared, folder=page3.parent)
    assert "PASSED" in r.stdout, out(r)
    # a verdict file another piece already used (here a copy of q3's): refused, whatever the folder
    page6 = cwd / "pages" / "q6" / "visual.html"
    n6 = quick_to_visual(cwd, "q6", "a pallet counted twice at a gate", notes, page6)
    fresh_render(page6.parent)
    copy = notes / "shared-copy.md"
    shutil.copy(shared, copy)
    refused3("q6", vgrade(cwd, "q6", n6, copy), "q3", "already used")
    # a verdict headed with another piece's slug: refused. Headed with its own, or with a name that is no piece, it is read
    refused3("q6", vgrade(cwd, "q6", n6, ad), "headed '## q2'", "q6")
    refused3("q6", vgrade(cwd, "q6", n6, verdict(notes / "q6-q3.md", "visual", 9, slug="q3")), "headed '## q3'")
    r = vgrade(cwd, "q6", n6, verdict(notes / "q6-own.md", "visual", 9, slug="q6"))
    assert "PASSED" in r.stdout, out(r)
    # a second piece with no page built, pointed at another piece's folder and given its own verdict: refused, because that page was graded for q2
    n7 = quick_to_visual(cwd, "q7", "a crate that never left the dock", notes, None)
    assert "visual_html" not in piece_json(cwd, "q7")
    own7 = verdict(notes / "q7-own.md", "visual", 9, slug="q7")
    refused3("q7", vgrade(cwd, "q7", n7, own7, folder=folder), "q2", "already graded")
    # the same piece with a page of its own (built by hand, no scaffold) passes, and the grade then names the page in piece.json
    fresh_render(cwd / "pages" / "q7", slug="q7")
    r = vgrade(cwd, "q7", n7, own7, folder=cwd / "pages" / "q7")
    assert "PASSED" in r.stdout, out(r)
    assert piece_json(cwd, "q7")["visual_html"] == str((cwd / "pages" / "q7" / "visual.html").resolve())
    print("PASS evidence: FAIL, REVISE-level and bare-PASS files cannot pass; typed scores must equal the critic's; the visual needs a fresh render with a PASS audit and every page-NN.png, each newer than the page; the grade stores the sha256 of the verdict, the page and every render; --folder is only the folder scaffold wrote; another piece's folder, a reused verdict and a verdict headed with another slug are refused; a seen: line of capitals is not a verdict")


def slug_tests(cwd):
    """G1-2: a slug is a folder name, so only [a-z0-9][a-z0-9._-]{0,63} is accepted."""
    for bad in ["../../../escaped", "a:b", "a/b", "a\\b", "A1", "", " x", ".hidden", "a b", "a" * 65, "x.", "con", "nul.txt"]:
        r = run(cwd, "new", bad, "--topic", "slug test", ok=False)
        assert r.returncode != 0 and "slug" in r.stderr and "Traceback" not in r.stderr, f"{bad!r}: {r.stdout}{r.stderr}"
    r = run(cwd, "next", "../x", ok=False)
    assert r.returncode != 0 and "slug" in r.stderr, "next accepted a path as a slug"
    assert not (cwd.parent / "escaped").exists() and not (cwd / "escaped").exists(), "a slug wrote outside the pieces folder"
    for good in ["a1", "approval-pages_v2.1", "a" * 64]:
        run(cwd, "new", good, "--topic", "slug test", "--scope", "quick")
        assert (cwd / ".atelier" / "pieces" / good / "piece.json").is_file()
    r = run(cwd, "grade", "a1", "atoms", "--scores", "coverage=9,specificity=9,sourced=9,surprise=9", "--notes", str(cwd / "no-such-notes.md"), ok=False)
    assert r.returncode != 0 and "no such file" in r.stderr and "Traceback" not in r.stderr, "a missing notes file must be a clear error: " + r.stderr
    print("PASS slugs: paths, colons, capitals, spaces, reserved names and 65 characters are refused with a clear message; plain slugs work")


def genome_tests(cwd, notes):
    """G1-6 and G1-9: type from the local font library by default, ground and type follow the register, the user's brand reaches the palette line."""
    local = {p["id"] for p in json.loads((SKILL / "data" / "type_pairings.json").read_text(encoding="utf-8")) if p["source"] == "local"}
    regs = json.loads((SKILL / "data" / "registers.json").read_text(encoding="utf-8"))
    recipes = json.loads((SKILL / "data" / "colour.json").read_text(encoding="utf-8"))["recipes"]
    dirs = {d["id"]: d["ground"] for d in json.loads((SKILL / "data" / "directions.json").read_text(encoding="utf-8"))}
    assert compose.local_types() == local and len(local) == 14, "every shipped pairing must load from the local fonts: " + str(local ^ compose.local_types())
    for name, reg in regs.items():
        assert reg["pairings"] and set(reg["pairings"]) <= local, f"register {name} lists a pairing that is not local"
    brand = cwd / "brand-tokens.css"
    brand.write_text(":root { --accent: #c2410c; --dark: #101820; }\n")
    r = run(cwd, "new", "gbad", "--topic", "brand test", "--scope", "design", "--brand", str(cwd / "no-such.css"), ok=False)
    assert r.returncode != 0 and "--brand" in r.stderr, "a missing brand file was accepted"
    design_piece(cwd, "gen", "a customs form read as a bill of materials", "", notes, new_args=("--brand", str(brand)), deal=False)
    design_piece(cwd, "gen0", "a returns label read as a bill of materials", "", notes, deal=False)
    assert piece_json(cwd, "gen")["brand"] == str(brand.resolve()) and "brand" not in piece_json(cwd, "gen0")
    saw_taste = False
    for seed in range(1, 31):
        run(cwd, "deal", "gen", "genome", "--seed", str(seed))
        g = piece_json(cwd, "gen")["genome"]
        if g["direction"] == "type-only":
            assert g["type"] == "house", "type-only is built on the house type's width axis"
        ws = (cwd / ".atelier" / "pieces" / "gen" / "04-genome.md").read_text(encoding="utf-8")
        assert g["type"] in local, f"seed {seed}: type {g['type']} is outside the local font library"
        assert g["type"] in regs[g["register"]]["pairings"] or g["type"] == "house", f"seed {seed}: register {g['register']} got the unsuited face {g['type']}"
        assert compose.register_grounds(g["register"]) >= {dirs[g["direction"]]}, f"seed {seed}: register {g['register']} (recipe {regs[g['register']]['colour']['recipe']}) got a {dirs[g['direction']]} ground"
        assert g["ground"] == dirs[g["direction"]]
        assert f"--brand {compose.q(brand.resolve())}" in ws, "the palette line does not carry --brand"
        run(cwd, "deal", "gen0", "genome", "--seed", str(seed))
        assert "--brand" not in (cwd / ".atelier" / "pieces" / "gen0" / "04-genome.md").read_text(encoding="utf-8").split("palette.py")[1].split("\n")[0], "a piece without --brand got one"
    for seed in range(1, 41):
        run(cwd, "deal", "gen0", "genome", "--seed", str(seed), "--any-type")
        t = piece_json(cwd, "gen0")["genome"]["type"]
        saw_taste = saw_taste or t.startswith("taste:")
        assert t in local or t.startswith("taste:")
    assert saw_taste, "--any-type never dealt a taste-skill pairing in 40 deals"
    assert run(cwd, "deal", "gen0", "angles", "--any-type", ok=False).returncode != 0
    # a pin from the host overrides the filters: dry (a paper recipe) pinned to a dark direction, and a pinned face
    design_piece(cwd, "genp", "a packing list read as a recipe card", "direction=receipt,register=dry,type=bookish", notes)
    g = piece_json(cwd, "genp")["genome"]
    assert (g["direction"], g["register"], g["type"], g["ground"]) == ("receipt", "dry", "bookish", "dark"), g
    print("PASS genome: 30 deals of type from the 14 local pairings only, each suited to its register and on a ground its colour recipe allows; --any-type adds taste-skill's; --brand reaches the palette line; host pins still win")


def rules_tests(cwd, notes):
    """R3a-3 and R3a-5: no serif display on the unbranded paper ground; a quick image is only dealt a direction that has a specimen."""
    fresh = cwd / "fresh"   # an empty memory, so the same seeds deal the same genomes every run
    (fresh / ".atelier").mkdir(parents=True)   # its own project: compose.py uses the nearest .atelier at or above the folder it runs in
    brand = cwd / "brand-tokens.css"
    brand.write_text(":root { --accent: #c2410c; --dark: #101820; }\n")   # the brand file genome_tests writes; each test runs in its own project
    pairs = json.loads((SKILL / "data" / "type_pairings.json").read_text(encoding="utf-8"))
    serif = {p["id"] for p in pairs if p.get("serif")}
    assert {"editorial-serif", "bookish", "crisp-serif", "italic-voice", "classic-serif"} <= serif and not serif & {"house", "technical", "art-deco", "outdoors", "handnote"}, serif
    assert compose.serif_display("bookish") and not compose.serif_display("house") and compose.serif_display("taste:eb-garamond-quiet") and not compose.serif_display("taste:switzer-semibold")
    design_piece(fresh, "plain", "a customs form read as a bill of materials", "", notes, deal=False)
    design_piece(fresh, "branded", "a returns label read as a bill of materials", "", notes, new_args=("--brand", str(brand)), deal=False)
    paper = serif_on_paper = 0
    for seed in range(1, 51):   # every other deal also draws from taste-skill's types (--any-type), which have serif faces of their own
        run(fresh, "deal", "plain", "genome", "--seed", str(seed), *(["--any-type"] if seed % 2 == 0 else []))
        g = piece_json(fresh, "plain")["genome"]
        paper += g["ground"] == "paper"
        assert not (g["ground"] == "paper" and compose.serif_display(g["type"])), f"seed {seed}: a paper ground without --brand was dealt the serif display {g['type']} (palette.py: cream plus a serif is cluster 1)"
        run(fresh, "deal", "branded", "genome", "--seed", str(seed))
        g = piece_json(fresh, "branded")["genome"]
        serif_on_paper += g["ground"] == "paper" and compose.serif_display(g["type"])
    assert paper >= 8, f"only {paper} of 50 deals had a paper ground: the check has no power"
    assert serif_on_paper >= 1, "with --brand, a serif display on paper is no longer dealt in 50 deals: --brand must keep today's behaviour"
    # a pin from the host still wins over the filter
    g = design_piece(fresh, "pinned", "a glossary read as a ledger of terms", "direction=ledger,type=bookish", notes)
    assert (g["ground"], g["type"]) == ("paper", "bookish"), g
    # R3a-5: a direction counts as having a specimen when its page is on disk, and the flag in directions.json says the same
    specs = SKILL / "assets" / "directions"
    for d in json.loads((SKILL / "data" / "directions.json").read_text(encoding="utf-8")):
        on_disk = (specs / f"{d['id']}.html").is_file() or (specs / f"{d['id']}.motion.html").is_file()
        assert bool(d.get("specimen")) == on_disk, f"{d['id']}: directions.json says specimen={d.get('specimen')}, the files say {on_disk}"
    assert compose.specimen("ledger", "image") and not compose.specimen("field-guide", "image") and not compose.specimen("ledger", "slide")
    assert compose.specimen("departure-board", "video").name == "departure-board.motion.html" and not compose.specimen("the-dot", "video")
    quick_to_visual(fresh, "quicker", "a pallet counted twice at a gate", notes, None)
    for seed in range(1, 51):
        run(fresh, "deal", "quicker", "genome", "--seed", str(seed))
        d = piece_json(fresh, "quicker")["genome"]["direction"]
        assert compose.specimen(d, "image"), f"seed {seed}: a quick image was dealt the direction {d}, which has no specimen"
    print(f"PASS rules: no serif display on an unbranded paper ground in 50 deals ({paper} on paper), serif kept with --brand and with a host pin; a quick image is dealt only directions with a specimen file in 50 deals; the specimen flags match the files")


PALETTE = ".pg-1 { --ground: #101820; --text: #f4f4f0; --text-2: #cfd2d6; --accent: #36dce8; }\n"   # an accent tokens.css does not have (its teal-lit is #75a3f9)


def pixels_near(png, rgb, tol=6):
    """How many pixels of a render are within tol of rgb on every channel; None when Pillow is not installed."""
    try:
        from PIL import Image
    except ImportError:
        return None
    im = Image.open(png).convert("RGB")
    flat = getattr(im, "get_flattened_data", None) or im.getdata   # get_flattened_data where Pillow has it (Pillow 14 removes getdata), getdata on older Pillow: the pin pillow>=10.3 holds
    return sum(1 for px in flat() if all(abs(a - b) <= tol for a, b in zip(px, rgb)))


def r4_tests(cwd, notes):
    """R4-1 to R4-5: a scaffolded specimen follows palette.css and the user's brand and carries no trademark logo; next says the palette line first; deliver remembers the cover."""
    # R4-1 data: every colour token a specimen reads is mapped to a palette.css role, and only to roles palette.py writes
    roles_ok = re.compile(r"var\(--(?:ground|text-2|text|accent-2|accent)\b")
    for d in json.loads((SKILL / "data" / "directions.json").read_text(encoding="utf-8")):
        if not d.get("specimen"):
            assert "roles" not in d, f"{d['id']}: a role map without a specimen"
            continue
        spec = SKILL / "assets" / "directions" / f"{d['id']}.html"
        used = set(re.findall(r"var\(--([a-z0-9-]+)\)", spec.read_text(encoding="utf-8"))) - {"disp", "body", "mono"}
        assert used <= set(d.get("roles", {})), f"{d['id']}: the specimen reads {sorted(used - set(d.get('roles', {})))} and the role map does not map it"
        assert all(roles_ok.search(v) for v in d["roles"].values()) and all(roles_ok.search(r) for r in d.get("rules", [])), f"{d['id']}: a role or rule that does not use the palette.css roles"
    # R4-1: with a palette next to the page, the specimen's tokens become the palette roles, after palette.css, which is after tokens.css
    out = cwd / "r4" / "a" / "visual.html"
    out.parent.mkdir(parents=True)
    (out.parent / "palette.css").write_text(PALETTE)
    design_piece(cwd, "r4a", "a till roll that itemises one retry loop", "direction=receipt", notes, medium="image")
    r = run(cwd, "scaffold", "r4a", "--out", str(out))
    html = out.read_text(encoding="utf-8")
    assert_links_work(html)
    tok, pal, roles = html.index("tokens.css"), html.index("palette.css"), html.index(".page { --night: var(--ground)")
    assert tok < pal < roles, "the roles must come after tokens.css and palette.css"
    assert "--cream: var(--text)" in html and "--cream-2: var(--text-2)" in html and "--house: var(--accent)" in html and ".roll .tot span:last-child { color: var(--ground); }" in html, "the receipt's tokens are not mapped to the palette roles"
    assert "follow its --ground, --text, --text-2 and --accent" in r.stdout, r.stdout
    # R4-3: no brand, so no logo, and the line says there is no brand file (it used to say "the brand file declares no --logo")
    assert 'data-role="logo"' not in html and "logo-lockup" not in html and 'logo removed: no --brand file, so no logo; add your own with data-role="logo"' in r.stdout, r.stdout
    rr = render(out)
    if rr is None:
        print("SKIP render of the palette-driven receipt: node or Playwright is not installed")
    else:
        assert rr.returncode == 0, "the receipt with a palette and no logo fails its own audit: " + rr.stdout
        ground, night = pixels_near(out.parent / "page-01.png", (0x10, 0x18, 0x20)), pixels_near(out.parent / "page-01.png", (0x18, 0x1B, 0x20))
        if ground is not None:   # R10: the page is a composition start, so the plan shows in its ground; the default night must not
            assert ground > 500000 and night < 5000, f"the render does not show the plan's ground #101820 ({ground} px) or still shows the default night as its ground ({night} px)"   # a night ground would be over a million px; edge pixels of the text pass near it
            at = subprocess.run([sys.executable, str(SKILL / "scripts" / "attention.py"), str(out.parent)], capture_output=True, text=True)
            assert at.returncode == 0, "attention.py fails a page with no logo: " + at.stdout
    # R4-2 and R4-3: --brand is linked right after tokens.css, before palette.css; a logo stays only when the brand declares --logo
    logo = cwd / "r4" / "logo.png"
    logo.write_bytes(bytes.fromhex("89504e470d0a1a0a0000000d49484452000000010000000108060000001f15c4890000000d4944415478da63fcffff3f0300050001a5f645400000000049454e44ae426082"))
    plain, with_logo = cwd / "r4" / "plain.css", cwd / "r4" / "with-logo.css"
    plain.write_text(":root { --house: #6b2fd6; --night: #14101f; }\n")
    with_logo.write_text(":root { --house: #6b2fd6; --logo: url(logo.png); }\n")
    for slug, direction, brand in (("r4b", "task-card", plain), ("r4c", "ledger", with_logo)):
        design_piece(cwd, slug, f"a {direction} that records the {slug} change", f"direction={direction}", notes, medium="image", new_args=("--brand", str(brand)))
        page = cwd / "r4" / slug / "visual.html"
        page.parent.mkdir()
        (page.parent / "palette.css").write_text(PALETTE)
        r = run(cwd, "scaffold", slug, "--out", str(page))
        html = page.read_text(encoding="utf-8")
        assert_links_work(html)
        uri = brand.resolve().as_uri()
        assert html.count(uri) == 1 and html.index("tokens.css") < html.index(uri) < html.index("palette.css"), f"{slug}: --brand is not linked between tokens.css and palette.css"
        assert "linked after tokens.css" in r.stdout and "logo-lockup" not in html, r.stdout
        if brand is plain:
            assert 'data-role="logo"' not in html and "logo removed: the brand file declares no --logo" in r.stdout, "a brand with no --logo kept a logo: " + r.stdout
        else:
            assert re.search(r'<img[^>]*data-role="logo"[^>]*src="' + re.escape(logo.resolve().as_uri()) + '"', html) and "logo removed" not in r.stdout, "the brand's --logo is not on the page: " + r.stdout
    # a brand that declares --logo-on-dark gets it on a dark ground or a colour field and --logo on paper; one that declares only --logo uses it everywhere
    dark_logo = cwd / "r4" / "logo-dark.png"
    dark_logo.write_bytes(logo.read_bytes())
    both = cwd / "r4" / "both.css"
    both.write_text(":root { --house: #6b2fd6; --logo: url(logo.png); --logo-on-dark: url(logo-dark.png); }\n")
    for slug, direction, brand, want in (("r4e", "receipt", both, dark_logo), ("r4f", "ledger", both, logo), ("r4g", "receipt", with_logo, logo)):
        design_piece(cwd, slug, f"a {direction} that records the {slug} change", f"direction={direction}", notes, medium="image", new_args=("--brand", str(brand)))
        page = cwd / "r4" / slug / "visual.html"
        page.parent.mkdir()
        (page.parent / "palette.css").write_text(PALETTE)
        run(cwd, "scaffold", slug, "--out", str(page))
        assert re.search(r'<img[^>]*data-role="logo"[^>]*src="' + re.escape(want.resolve().as_uri()) + '"', page.read_text(encoding="utf-8")), f"{slug}: a {direction} page does not carry {want.name}"
    # R4-4: next says to make the colour before the page when palette.css is missing, and not when it is there
    assert not (cwd / "palette.css").exists()
    quick_to_visual(cwd, "r4q", "a pallet counted twice at one gate", notes, None)
    nx = run(cwd, "next", "r4q").stdout
    assert nx.startswith("visual: colour first") and "palette.py" in nx and nx.index("palette.py") < nx.index("scaffold r4q"), nx
    design_piece(cwd, "r4d", "a stock count that is read back as a till roll", "direction=receipt", notes, medium="image")   # not scaffolded yet, no palette.css anywhere
    nd = run(cwd, "next", "r4d").stdout
    assert "palette.py" in nd and nd.index("palette.py") < nd.index("Start the page"), "design scope: the palette line must come before the scaffold line: " + nd
    (cwd / "palette.css").write_text(PALETTE)
    nx = run(cwd, "next", "r4q").stdout
    assert "palette.py" not in nx and nx.startswith("visual: start the page"), nx
    (cwd / "palette.css").unlink()
    # R4-5: deliver adds the cover to the layout memory
    page = cwd / "r4" / "q" / "visual.html"
    run(cwd, "scaffold", "r4q", "--out", str(page))
    fresh_render(page.parent)
    qn = notes / "r4q-visual.md"
    qn.write_text("\n".join(f"{c}: because the page shows one number as the largest type on the cover" for c in CRIT["visual"].split()))
    assert "PASSED" in vgrade(cwd, "r4q", qn, verdict(notes / "r4q-critic.md", "visual", 9, slug="r4q")).stdout
    r = run(cwd, "deliver", "r4q")
    if importlib.util.find_spec("PIL") is None:
        print("SKIP cover memory: Pillow is not installed")
    else:
        remembered = cwd / ".atelier" / "covers" / "r4q.png"
        assert remembered.is_file() and remembered.read_bytes() == (page.parent / "page-01.png").read_bytes() and "cover remembered r4q" in r.stdout, "deliver did not add the cover to the layout memory: " + r.stdout
    print("PASS r4: every specimen colour token has a palette role; a scaffolded page follows palette.css (the receipt's start shows the plan's ground, not the default night) and carries no trademark logo; --brand is linked after tokens.css and before palette.css; --logo is the only logo kept; next says the palette line first; deliver remembers the cover")


def after_label(text, label):
    """The command printed on the line after a label line (compose.py puts every label and its command on lines of their own)."""
    lines = text.splitlines()
    i = next(k for k, l in enumerate(lines) if l.strip().startswith(label))
    assert lines[i].strip().endswith(":") and i + 1 < len(lines), f"'{label}' is not a label line of its own: {lines[i]}"
    return lines[i + 1].strip()


def find_bash():
    """Git Bash on Windows (WSL's bash.exe cannot read C:/ paths), else bash on the PATH; None when there is none."""
    found = [shutil.which("bash"), *(os.path.join(os.environ[v], "Git", "bin", "bash.exe") for v in ("ProgramFiles", "ProgramW6432") if v in os.environ)]
    return next((b for b in found if b and os.path.isfile(b) and "system32" not in b.lower()), None)


def r7_tests(cwd, notes):
    """R7-C1 and R7-C2: a brand file's own faces are kept; every path compose.py prints is quoted with forward slashes and runs from bash."""
    r7 = cwd / "r7"
    r7.mkdir()
    disp, text, mono, local = compose.type_families("technical")
    assert local
    faces = {"r7a": ':root { --house: #6b2fd6; --disp: "Fraunces", serif; --body: "Lora", serif; }\n/* --mono: "Courier Prime", monospace; */\n',   # two faces; the mono line is a comment and declares nothing
             "r7b": ':root { --house: #6b2fd6; --disp: "Fraunces", serif; --body: "Lora", serif; --mono: "Courier Prime", monospace; }\n',
             "r7c": '/* --disp: "Fraunces", serif; --body: "Lora", serif; --mono: "Courier Prime", monospace; */\n:root { --house: #6b2fd6; }\n'}   # all three commented out, as in TEMPLATE.css
    out = {}
    for slug, css in faces.items():
        brand = r7 / f"{slug}.css"
        brand.write_text(css)
        design_piece(cwd, slug, f"a {slug} label that is read back as a bill of materials", "direction=task-card,type=technical", notes, medium="image", new_args=("--brand", str(brand)))
        page = r7 / slug / "visual.html"
        r = run(cwd, "scaffold", slug, "--out", str(page))
        out[slug] = (page.read_text(encoding="utf-8"), r.stdout)
    override = lambda html, k, v: f'--{k}: "{v}"' in html   # the :root line scaffold writes for the dealt pairing
    html, said = out["r7a"]
    assert override(html, "mono", mono) and not override(html, "disp", disp) and not override(html, "body", text) and "library.css" in html, "only the face the brand file leaves out is set from the dealt pairing"
    assert "type: the brand file's faces are kept" in said and "--mono set on :root" in said, said
    html, said = out["r7b"]
    assert not any(override(html, k, v) for k, v in (("disp", disp), ("body", text), ("mono", mono))) and "library.css" not in html, "a brand file with all three faces gets no type override and no library link"
    assert "type: the brand file's faces are kept" in said and "set on :root" not in said, said
    html, said = out["r7c"]
    assert all(override(html, k, v) for k, v in (("disp", disp), ("body", text), ("mono", mono))) and "faces are kept" not in said and "--disp, --body, --mono set on :root" in said, "commented-out faces declare nothing, so the dealt pairing is set"
    tpl = SKILL / "assets" / "brands" / "TEMPLATE.css"   # a copy of the template with its colours filled pins no face and no logo until a line is uncommented
    assert compose.brand_sets(tpl, ("disp", "body", "mono")) == [] and compose.brand_logo(tpl, True) == (None, False), "TEMPLATE.css declares a face or a logo before the person uncomments it"
    # R7-C2: always quoted, forward slashes, in every printed command
    assert compose.q(pathlib.Path("a") / "d.py") == '"a/d.py"' and compose.q(pathlib.Path("a") / "b c" / "d.py") == '"a/b c/d.py"'
    if os.name == "nt":
        assert compose.q(r"D:\work\x y\v.html") == '"D:/work/x y/v.html"' and compose.q(r"D:\work\xy\v.html") == '"D:/work/xy/v.html"'
    nxt = after_label(out["r7a"][1], "next")
    assert nxt.startswith("node ") and "\\" not in nxt and nxt.count('"') >= 4, "scaffold's next line: " + nxt
    nx = run(cwd, "next", "r7a").stdout
    assert re.search(re.escape(compose.PY) + r' "[^"\\]+compose\.py" ', nx) and "\\" not in nx, nx   # the Python that runs compose.py, not a bare "python"
    # R14: PowerShell reads a line that starts with a quoted path as an expression (5.1: "Unexpected token"), so on Windows compose.py starts
    # every printed command with the call operator "& ", unless the shell is Git Bash or MSYS2 (MSYSTEM is set): there, as on macOS and
    # Linux, it prints the quoted path alone. Each shell gets the line printed in its own environment and runs it exactly as printed.
    assert compose.PY == ("& " if sys.platform == "win32" and not os.environ.get("MSYSTEM") else "") + compose.q(sys.executable), compose.PY
    lost = lambda env, slug: after_label(subprocess.run(C + ["new", slug, "--topic", "a pallet label read twice"], cwd=cwd, capture_output=True, text=True,
                                                        env=env).stdout, "Lost? Run:")
    py = compose.q(sys.executable)
    ps = shutil.which("powershell") if sys.platform == "win32" else None
    if ps:
        no_msys = {k: v for k, v in os.environ.items() if k != "MSYSTEM"}   # PowerShell started from the Start menu has no MSYSTEM
        line = lost(no_msys, "r7d")
        assert line.startswith("& " + py + ' "'), line
        enc = base64.b64encode(line.encode("utf-16-le")).decode()   # the line exactly as printed, with no second layer of quoting
        p = subprocess.run([ps, "-NoProfile", "-NonInteractive", "-EncodedCommand", enc], cwd=cwd, capture_output=True, text=True, env=no_msys)
        assert p.returncode == 0 and "atoms: fill" in p.stdout, f"a printed command does not run in Windows PowerShell: {line}\n{p.stdout}{p.stderr}"
    bash = find_bash()
    if not bash or not shutil.which("python"):
        print("SKIP bash run of a printed command: no Git Bash (or no python on the PATH)")
    else:
        line = lost({**os.environ, "MSYSTEM": "MINGW64"} if sys.platform == "win32" else dict(os.environ), "r7e")   # Git Bash sets MSYSTEM=MINGW64
        assert line.startswith(py + ' "'), line
        b = subprocess.run([bash, "-c", line], cwd=cwd, capture_output=True, text=True)
        assert b.returncode == 0 and "atoms: fill" in b.stdout, f"a printed command does not run from bash: {line}\n{b.stdout}{b.stderr}"
        tiny = r7 / "ran.py"   # the temp folder has no space in its name, the case where bash used to eat the backslashes of an unquoted path
        tiny.write_text('print("ran")\n')
        b = subprocess.run([bash, "-c", "python " + compose.q(tiny)], cwd=cwd, capture_output=True, text=True)
        assert b.returncode == 0 and "ran" in b.stdout, f"a quoted path does not run from bash: {b.stdout}{b.stderr}"
    print("PASS r7: a brand file's --disp, --body and --mono are kept (commented lines do not count) and scaffold says so; every printed path is quoted with forward slashes"
          + (", a command printed for PowerShell (it starts with '& ') runs there as printed" if ps else "")
          + (", and a command printed for Git Bash (MSYSTEM set, no '& ') runs there as printed" if bash and sys.platform == "win32" else ", and a printed command runs from bash" if bash else ""))


ATOMS_R8 = [   # the atoms of the 30 Oct 2026 run: four published sources and one made-up object
    "| 1 | number | About 70% of outages come from changes to a live system | https://sre.google/sre-book/introduction/ | the change is the risk |",
    "| 2 | limit | A good checklist holds 5 to 9 items | Atul Gawande, The Checklist Manifesto (2009), ch. 6 | more lines and people skip it |",
    "| 3 | mechanism | A pause point is where the team stops to confirm | Gawande, The Checklist Manifesto, ch. 6 | the list needs one stop |",
    "| 4 | number | The 19-item WHO checklist went with a fall in deaths from 1.5% to 0.8% | Haynes et al., NEJM 2009 | short lists change outcomes |",
    "| 5 | object | a rollback command, written out and tried before the deploy | no source: an object made up for the example | the one line that decides the weekend |",
]


def fill_atoms(cwd, slug, rows):
    """Write atom rows into a piece's 01-atoms.md in place of the empty template row."""
    f = cwd / ".atelier" / "pieces" / slug / "01-atoms.md"
    text = f.read_text(encoding="utf-8")
    row = next(l for l in text.splitlines() if l.startswith("| 1 | fact / number"))
    f.write_text(text.replace(row, "\n".join(rows)), encoding="utf-8")


def r9_tests(cwd, notes):
    """R9 (the 30 Oct 2026 run of the README example): a hook or close the atoms cannot carry honestly is never dealt; compose.py finds the
    project's .atelier from a page's folder; the quick visual stage asks for the post text the critic checks the page against."""
    st = json.loads((SKILL / "data" / "structures.json").read_text(encoding="utf-8"))
    needy = {x["id"]: x["needs"] for k in ("hooks", "closes") for x in st[k] if x.get("needs")}
    assert needy["confession"] == {"first_party": True} and needy["moment"] == {"types": ["time"]} and needy["changed"] == {"first_party": True}, needy
    # pure: the atoms table is read, a made-up object counts as unsourced, a first-party record as first-party
    run(cwd, "new", "r9a", "--topic", "what a Friday release checklist really needs", "--scope", "quick", "--medium", "image")
    fill_atoms(cwd, "r9a", ATOMS_R8)
    piece = json.loads((cwd / ".atelier" / "pieces" / "r9a" / "piece.json").read_text(encoding="utf-8"))
    old = compose.PIECES
    compose.PIECES = cwd / ".atelier" / "pieces"
    try:
        atoms = compose.atoms_of(piece)
    finally:
        compose.PIECES = old
    assert len(atoms) == 5 and [a["sourced"] for a in atoms] == [True, True, True, True, False] and not any(a["first_party"] for a in atoms), atoms
    hooks = {x["id"]: x for x in st["hooks"]}
    assert not compose.supported(hooks["confession"], atoms) and not compose.supported(hooks["moment"], atoms) and not compose.supported(hooks["artefact"], atoms), "the made-up object or a missing record carried a hook"
    assert compose.supported(hooks["number"], atoms) and compose.supported(hooks["object"], atoms), "a sourced number does not carry the number hook"
    # end to end: forty deals on those atoms never give a hook or close that would have to be invented
    assert "PASSED" in grade(cwd, "r9a", "atoms", 9, notes).stdout
    run(cwd, "deal", "r9a", "angles")
    qa = notes / "r9a-angles.md"
    qa.write_text("\n".join(f"{c}: because the candidate quotes a sourced number on line 2" for c in CRIT["angles"].split()))
    assert "PASSED" in run(cwd, "grade", "r9a", "angles", "--scores", "novelty=9,truth=9,relevance=9,intrigue=9,tone=9", "--notes", str(qa), "--by", "self").stdout
    run(cwd, "choose", "r9a", "angle", "1", "--text", "ask what goes on the list and you are asking what to do when the deploy fails")
    banned, seen = {"confession", "moment", "quote", "artefact", "changed", "next-test"}, set()
    for seed in range(40):
        run(cwd, "deal", "r9a", "genome", "--seed", str(seed))
        g = json.loads((cwd / ".atelier" / "pieces" / "r9a" / "piece.json").read_text(encoding="utf-8"))["genome"]
        assert g["hook"] not in banned and g["close"] not in banned, f"seed {seed} dealt hook {g['hook']} close {g['close']} with no atom to carry it"
        seen |= {g["hook"], g["close"]}
    ws = (cwd / ".atelier" / "pieces" / "r9a" / "04-genome.md").read_text(encoding="utf-8")
    assert "Left out of this deal" in ws and "hook confession (needs a first-party atom" in ws and "hook moment (needs a sourced time atom)" in ws and "re-deal instead" in ws, ws
    # with a first-party record and a dated instant, the same deal may give a confession or a moment. It runs in a fresh project:
    # the deal weighs .atelier/history.jsonl, which the unseeded pieces above fill at random, so --seed alone did not fix the outcome
    solo = fresh_project()
    try:
        run(solo, "new", "r9b", "--topic", "the night our Friday release went wrong", "--scope", "quick", "--medium", "image")
        fill_atoms(solo, "r9b", ATOMS_R8[:4] + ["| 5 | time | Fri 17:40: the deploy that took the site down for 40 minutes | first-party: incidents/2026-05-22.md | our own outage |"])
        assert "PASSED" in grade(solo, "r9b", "atoms", 9, notes).stdout
        run(solo, "deal", "r9b", "angles", "--seed", "1")
        assert "PASSED" in run(solo, "grade", "r9b", "angles", "--scores", "novelty=9,truth=9,relevance=9,intrigue=9,tone=9", "--notes", str(qa), "--by", "self").stdout
        run(solo, "choose", "r9b", "angle", "1", "--text", "the deploy at 17:40 that we never rolled back")
        assert not (solo / ".atelier" / "history.jsonl").exists(), "the fresh project already has a memory"
        got = set()
        for seed in range(40):
            run(solo, "deal", "r9b", "genome", "--seed", str(seed))
            g = json.loads((solo / ".atelier" / "pieces" / "r9b" / "piece.json").read_text(encoding="utf-8"))["genome"]
            got |= {g["hook"], g["close"]}
        assert got & {"confession", "moment", "changed", "next-test"}, f"a first-party dated atom never unlocked those hooks or closes: {got}"
        wb = (solo / ".atelier" / "pieces" / "r9b" / "04-genome.md").read_text(encoding="utf-8")
        assert "hook confession" not in wb and "hook moment" not in wb and "hook quote (needs a sourced quote atom)" in wb, wb
    finally:
        shutil.rmtree(solo, ignore_errors=True)
    # (c) every command finds the project's .atelier from a page's folder, as git finds .git; new there keeps the one project memory
    deep = cwd / "r9" / "friday-plain" / "renders"
    deep.mkdir(parents=True)
    r = run(deep, "next", "r9a")
    assert "no piece" not in r.stdout + r.stderr and r.stdout.startswith("genome:"), r.stdout + r.stderr
    assert run(deep, "status", "r9a").stdout.startswith("r9a (image)")
    run(deep, "new", "r9c", "--topic", "a release note nobody reads", "--scope", "quick", "--medium", "image")
    assert (cwd / ".atelier" / "pieces" / "r9c" / "piece.json").is_file() and not (deep / ".atelier").exists(), "new in a page folder made a second memory"
    outside = pathlib.Path(tempfile.mkdtemp())
    try:
        r = run(outside, "next", "r9a", ok=False)
        assert r.returncode != 0 and "no piece 'r9a'" in r.stderr, "a folder outside the project found its pieces"
    finally:
        shutil.rmtree(outside, ignore_errors=True)
    # S9: the quick visual stage asks for the post text, and next says to give it to the critic
    vws = (cwd / ".atelier" / "pieces" / "r9a" / "07-visual.md").read_text(encoding="utf-8")
    assert "Write the post text" in vws and "the renders, the post text and all script output" in vws, vws
    print(f"PASS r9: 40 deals on atoms with no first-party record, no dated instant, no quote and a made-up object never gave {', '.join(sorted(banned))}, and the worksheet says why; a first-party dated atom unlocks them; next, status and new work from a page's folder; the quick visual worksheet asks for the post text")


def specimen_on_palette(did, palette_css, out, page=1):
    """The direction's specimen page with its colour tokens pointed at a palette.css, as the builder sees it when reading the grammar
    (R10: scaffold no longer copies it into the piece's page). page: which page of the plan (.pg-N) it takes. Writes out and returns it."""
    html, _ = compose.absolute_links((compose.SPECS / f"{did}.html").read_text(encoding="utf-8"), compose.SPECS)
    html, _ = compose.fit_logo(html, None)
    first = compose.SECTION.search(html)
    sec = re.sub(r'(<section\b[^>]*\bclass=")([^"]*)"', lambda m: f'{m.group(1)}{m.group(2)} pg-{page}"', first.group(0), count=1)
    lead = f'<link rel="stylesheet" href="{palette_css.resolve().as_uri()}">\n' + (compose.palette_roles(did, palette_css) or "") + "\n"
    out.write_text(html[:first.start()] + lead + sec + html[first.end():], encoding="utf-8")
    return out


def r9_render_tests(cwd, notes):
    """R9 (d): the audit measures what the 30 Oct 2026 critics charged by eye (accent paint over 5%, a display word alone on its last line,
    a display line ending on a small word), and every specimen a quick image is dealt, on its palette, is clear of all three."""
    fx = SKILL / "tests" / "fixtures"
    first = render(fx / "r9-accent-fill" / "visual.html", "--out", str(cwd / "r9fx" / "a"))
    if first is None:
        print("SKIP r9 render checks: node or Playwright is not installed")
        return
    audit = lambda folder: json.loads((folder / "audit.json").read_text(encoding="utf-8"))[0]
    a = audit(cwd / "r9fx" / "a")
    assert first.returncode == 0 and a["accent"] >= 10 and any(w.startswith("accent paint covers") for w in a["warns"]), first.stdout
    r = render(fx / "r9-display-breaks" / "visual.html", "--out", str(cwd / "r9fx" / "b"))
    w = "\n".join(audit(cwd / "r9fx" / "b")["warns"])
    assert r.returncode == 0 and 'one word alone on its last line: "undo."' in w and 'a display line ends on "of"' in w, r.stdout
    r = render(fx / "r9-clean" / "visual.html", "--out", str(cwd / "r9fx" / "c"))
    c = audit(cwd / "r9fx" / "c")
    assert r.returncode == 0 and c["accent"] < 1 and not any("accent paint" in x or "display" in x for x in c["warns"]), r.stdout
    checked = []
    # R14: the deals run in a project of their own with no memory. In cwd, the unseeded deals made before this point are in memory and
    # move what seed 9 deals, so the register, harmony and palette changed from run to run.
    fresh = fresh_project()
    try:
        for d in json.loads((SKILL / "data" / "directions.json").read_text(encoding="utf-8")):
            if not d.get("specimen") or "image" not in d["media"]:
                continue
            slug = f"r9s-{d['id']}"
            design_piece(fresh, slug, f"a {d['id']} page that holds the {d['id']} record for r9", f"direction={d['id']}", notes, medium="image", deal=False)
            run(fresh, "deal", slug, "genome", "--seed", "9")   # a fixed seed, so the dealt type face (which sets the line breaks) is the same every run
            g = piece_json(fresh, slug)["genome"]
            page = fresh / "r9s" / d["id"] / "visual.html"
            page.parent.mkdir(parents=True)
            subprocess.run([sys.executable, str(SKILL / "scripts" / "palette.py"), "--register", g["register"], "--harmony", g["harmony"], "--arc", "steady",
                            "--pages", "1", "--ground", g["ground"], "--out", str(page.parent)], capture_output=True, text=True)
            r = render(specimen_on_palette(d["id"], page.parent / "palette.css", page))
            p = audit(page.parent)
            bad = [x for x in p["warns"] if x.startswith(("accent paint", "display type", "a display line"))]
            assert r.returncode == 0 and not bad, f"{d['id']}: the specimen a quick image reads its grammar from breaks a rule the critic charges: {bad}\n{r.stdout}"
            checked.append(f"{d['id']} {g['register']} {g['harmony']} {p.get('accent', '-')}%")
    finally:
        shutil.rmtree(fresh, ignore_errors=True)
    print(f"PASS r9 render: the audit warns on accent paint over 5% (11% on the fixture), a lone last word and a line ending on 'of'; a clean page has neither; {len(checked)} specimens on their palettes are clear ({', '.join(checked)})")


ROLE_KEYS = {"ground": "g", "text": "text", "text-2": "text2", "accent": "acc", "accent-2": "acc2"}   # palette.css role: palette.py's row key


def own_palette_pages(ground):
    """Every page an own palette (no --brand) can give a direction on this ground: each register whose colour recipe allows the ground, by
    every harmony and every arc, over 6 pages, from palette.py's own plan. Returns [((register, harmony, arc, page), {role: rgb})], colours
    rounded to the hex palette.css writes."""
    import palette
    colour = json.loads((SKILL / "data" / "colour.json").read_text(encoding="utf-8"))
    out = []
    for reg in json.loads((SKILL / "data" / "registers.json").read_text(encoding="utf-8")):
        if ground not in compose.register_grounds(reg):
            continue
        for h in (x["id"] for x in colour["harmonies"]):
            for arc in (x["id"] for x in colour["arcs"]):
                for row in palette.plan(palette.own_brand(reg, h, arc), reg, h, arc, 6, ground, (), False)[3]:
                    out.append(((reg, h, arc, row["page"]), {k: palette.hex_to_rgb(palette.rgb_to_hex(row[v])) for k, v in ROLE_KEYS.items() if row[v] is not None}))
    return out


def palette_sweep_tests(cwd):
    """R14: no direction fails the audit on a palette it can be dealt (the round 13 score: field-notebook's 32 px accent timestamps fell
    to 4.0:1 over its grid on 14 of 40 own palettes). For each direction with a specimen, every page of every own palette on its ground is
    swept for each role its specimen maps (data/directions.json roles and rules); the specimen is rendered and audited on the page where
    that role is darkest, where it is lightest and, for a text role, where it is least readable on the ground. Any hard fail fails."""
    from concurrent.futures import ThreadPoolExecutor
    import palette
    # the audit must see every colour form, or the sweep passes text it cannot read: Chromium computes color-mix() and relative colours
    # as oklab(...) and oklch(...), which the audit used to skip
    r = render(SKILL / "tests" / "fixtures" / "r14-mixed-colour" / "visual.html", "--no-png", "--out", str(cwd / "r14mixed"))
    if r is None:
        print("SKIP palette sweep: node or Playwright is not installed")
        return
    assert r.returncode == 1 and all(f'FAIL contrast under 3:1: "{t}' in r.stdout for t in ("Mixed toward black", "Eight points darker")), r.stdout
    dirs = [d for d in json.loads((SKILL / "data" / "directions.json").read_text(encoding="utf-8")) if d.get("specimen") and d.get("roles")]
    pages = {g: own_palette_pages(g) for g in sorted({d["ground"] for d in dirs})}
    jobs = []
    for d in dirs:
        maps = " ".join([*d["roles"].values(), *d.get("rules", [])])
        pick = set()
        for role in (r for r in ROLE_KEYS if f"var(--{r})" in maps):
            have = [(k, c) for k, c in pages[d["ground"]] if role in c]
            pick |= {min(have, key=lambda kc: palette.luminance(kc[1][role]))[0], max(have, key=lambda kc: palette.luminance(kc[1][role]))[0]}
            if role != "ground":
                pick.add(min(have, key=lambda kc: palette.contrast(kc[1][role], kc[1]["ground"]))[0])
        jobs += [(d, k) for k in sorted(pick)]

    def one(job):
        d, (reg, h, arc, pg) = job
        f = cwd / "r14sweep" / f"{d['id']}-{reg}-{h}-{arc}-{pg}"
        f.mkdir(parents=True)
        p = subprocess.run([sys.executable, str(SKILL / "scripts" / "palette.py"), "--register", reg, "--harmony", h, "--arc", arc, "--pages", "6",
                            "--ground", d["ground"], "--out", str(f)], capture_output=True, text=True)
        return job, p, render(specimen_on_palette(d["id"], f / "palette.css", f / "visual.html", pg), "--no-png", "--out", str(f / "audit"))

    with ThreadPoolExecutor(max_workers=min(6, os.cpu_count() or 2)) as ex:
        done = list(ex.map(one, jobs))
    bad_plan = [f"{d['id']} {k}: {p.stdout[-200:]}" for (d, k), p, _ in done if p.returncode != 0]
    assert not bad_plan, f"palette.py could not plan an own palette: {bad_plan}"
    first = lambda out: [x.strip() for x in out.splitlines() if x.strip().startswith("FAIL")]
    fails = [f"{d['id']} on {' '.join(map(str, k))}: {len(first(r.stdout))} fail(s), " + "; ".join(first(r.stdout)[:3])
             for (d, k), _, r in done if r.returncode != 0]
    assert not fails, "a direction fails the audit on a palette it can be dealt:\n" + "\n".join(fails)
    swept = ", ".join(f"{len(v)} on {g}" for g, v in pages.items())
    print(f"PASS r14 palette sweep: every own-palette page swept ({swept}); {len(dirs)} directions rendered on {len(jobs)} of those pages "
          "(each mapped role at its darkest, its lightest and, for text, its least readable on the ground): no hard fail")


ATOMS_R10 = ATOMS_R8[:4] + ["| 5 | object | The WHO Surgical Safety Checklist: 19 items in three pauses (sign in, time out, sign out) | WHO Surgical Safety Checklist (2009) | a real list built around three stops |"]


def r10_tests(cwd, notes):
    """R10 (the round 9 run: distinct 6 in 5 of 6 verdicts, because both pages kept the frame of the specimen they started from; 71 to 87 words
    a page): scaffold no longer starts a page from the specimen the critic judges distinct against; page 1 is never dealt the specimen's own
    layout; the worksheets say what to compose and the word budget; the audit fails a rule through text and names the budget; --pin fixes an
    axis of a quick deal; the kitchen-rail specimen keeps the margins and sets its words in the text face."""
    import random
    st = json.loads((SKILL / "data" / "structures.json").read_text(encoding="utf-8"))
    dirs = json.loads((SKILL / "data" / "directions.json").read_text(encoding="utf-8"))
    layouts, words = st["layouts"], st["layout_words"]
    # data: every layout word is defined in one sentence; every specimen names its own layout word and its frame, and no other direction does
    assert list(layouts) == words and all(re.fullmatch(r"[a-z][^\n]{40,220}\.", v) for v in layouts.values()), layouts
    specd = [d for d in dirs if d.get("specimen")]
    assert all(d.get("layout") in words and len(d.get("frame", "")) >= 40 for d in specd), [d["id"] for d in specd if d.get("layout") not in words]
    assert not any("layout" in d or "frame" in d for d in dirs if not d.get("specimen"))
    # the deal: page 1 never gets the avoided layout, unless the format pins it there (the pin wins)
    for seed in range(200):
        assert compose.layout_rhythm(random.Random(seed), words, 1, None, "stack") != ["stack"]
        assert compose.layout_rhythm(random.Random(seed), words, 5, None, "table")[0] != "table"
    assert compose.layout_rhythm(random.Random(1), words, 5, {"layout": "number", "page": 1}, "number")[0] == "number"
    fmts = {f["id"]: f for f in json.loads((SKILL / "data" / "formats.json").read_text(encoding="utf-8"))}
    dealt = 0
    for did in ("kitchen-rail", "timetable", "receipt", "editorial-poster"):
        d = next(x for x in dirs if x["id"] == did)
        design_piece(cwd, f"r10d-{did}", f"a {did} page that shows one record for the r10 deal", f"direction={did}", notes, medium="image", deal=False)
        for seed in range(6):
            run(cwd, "deal", f"r10d-{did}", "genome", "--seed", str(seed))
            g = piece_json(cwd, f"r10d-{did}")["genome"]
            lead = fmts[g["format"]].get("lead") or {}
            assert g["layout_rhythm"][0] != d["layout"] or (lead.get("page") == 1 and lead.get("layout") == d["layout"]), f"{did} seed {seed}: page 1 was dealt the specimen's own layout {d['layout']}"
            dealt += 1
    # the worksheets and scaffold: the run's two directions get a composition start with no sample words and no specimen markup
    samples = {"kitchen-rail": ("Four tickets", "#1041", 'class="t', "class=\"rail\""), "timetable": ("Same report", "Mon 10:00", "<table", "Two&nbsp;timetables")}
    for did, sample in samples.items():
        slug = f"r10s-{did}"
        run(cwd, "new", slug, "--topic", f"what a Friday release checklist really needs {did}", "--scope", "quick", "--medium", "image")
        fill_atoms(cwd, slug, ATOMS_R10)
        assert "PASSED" in grade(cwd, slug, "atoms", 9, notes).stdout
        run(cwd, "deal", slug, "angles")
        qa = notes / f"{slug}-angles.md"
        qa.write_text("\n".join(f"{c}: because the candidate quotes a sourced number on line 2" for c in CRIT["angles"].split()))
        assert "PASSED" in run(cwd, "grade", slug, "angles", "--scores", "novelty=9,truth=9,relevance=9,intrigue=9,tone=9", "--notes", str(qa), "--by", "self").stdout
        run(cwd, "choose", slug, "angle", "1", "--text", f"surgery stops three times and a release can too, {did}")
        run(cwd, "deal", slug, "genome", "--pin", f"direction={did}", "--seed", "4")
        g = piece_json(cwd, slug)["genome"]
        d = next(x for x in dirs if x["id"] == did)
        w = g["layout_rhythm"][0]
        assert g["direction"] == did and w != d["layout"], g
        for ws in ("04-genome.md", "07-visual.md"):
            t = (cwd / ".atelier" / "pieces" / slug / ws).read_text(encoding="utf-8")
            for want in (f'Direction "{did}": ', f"Its frame is: {d['frame']}", "Do not compose the page in that frame", f'Page 1 layout "{w}": {layouts[w]}',
                         "atom 5 (typed object)", "Word budget: 45 words or fewer on each page", "the hook 8 words or fewer"):
                assert want in t, f"{ws} for {did} does not say: {want}"
        page = cwd / "r10" / did / "visual.html"
        page.parent.mkdir(parents=True)
        subprocess.run([sys.executable, str(SKILL / "scripts" / "palette.py"), "--register", g["register"], "--harmony", g["harmony"], "--arc", "steady",
                        "--pages", "1", "--ground", g["ground"], "--out", str(page.parent)], capture_output=True, text=True)
        r = run(cwd, "scaffold", slug, "--out", str(page))
        html = page.read_text(encoding="utf-8")
        assert not [x for x in sample if x in html], f"{did}: the scaffolded page still carries the specimen's {[x for x in sample if x in html]}"
        assert f'class="page st {w} pg-1"' in html and 'data-role="hook"' in html and "a composition start, not the specimen" in r.stdout and d["frame"] in r.stdout, r.stdout
        assert_links_work(html)
        rr = render(page)
        if rr is not None:
            p = json.loads((page.parent / "audit.json").read_text(encoding="utf-8"))[0]
            bad = [x for x in p["warns"] if x.startswith(("accent paint", "display type", "a display line"))]
            assert rr.returncode == 0 and not bad, f"{did}: the composition start fails its own audit: {bad}\n{rr.stdout}"
    # every layout word on the grid: a 12-page start, one page per word, passes the audit; only the stack puts the hook in a band at the top
    twelve = cwd / "r10" / "layouts" / "visual.html"
    twelve.parent.mkdir(parents=True)
    html = (compose.START.replace("@DIR@", "kitchen-rail").replace("@GROUND@", "paper").replace("@BG@", "paper").replace("@FG@", "ink").replace("@SPEC@", "the specimen")
            .replace("@FRAME@", "the frame").replace("@BUDGET@", "45").replace("@HOOK@", "8").replace("@PAGES@", compose.start_pages("kitchen-rail", words, [])))
    html, _ = compose.absolute_links(html, compose.SPECS)
    html = re.sub(r"<h2>[^<]*</h2>", f'<h2 data-role="hook">{compose.HOOK_SAMPLE}</h2>', compose.fit_logo(html, None)[0])   # every page carries the cover's hook, measured as a hook
    twelve.write_text(html, encoding="utf-8")
    rr = render(twelve)
    if rr is None:
        print("SKIP r10 render checks: node or Playwright is not installed")
    else:
        pages = json.loads((twelve.parent / "audit.json").read_text(encoding="utf-8"))
        assert rr.returncode == 0 and len(pages) == 12, rr.stdout
        for word, p in zip(words, pages):
            hook = next(b for b in p["boxes"] if b["role"] == "hook")
            top_band = hook["y"] < 200 and hook["w"] > 600
            assert top_band == (word == "stack"), f"layout {word}: hook at {hook}; only the stack sets the hook as a band at the top"
            assert not [x for x in p["fails"] + p["warns"] if "rule runs" in x or x.startswith(("accent paint", "a display line", "display type"))], f"layout {word}: {p['warns']}"
        # the audit: a rule or border through text fails, rules beside text pass, and the word budget names the number to cut
        fx = SKILL / "tests" / "fixtures"
        r = render(fx / "r10-rule-through" / "visual.html", "--out", str(cwd / "r10fx" / "through"))
        hits = [x for x in r.stdout.splitlines() if "a rule runs through text" in x]
        assert r.returncode == 1 and len(hits) == 2 and any("border of td" in x for x in hits) and any("bar div.bar" in x for x in hits), r.stdout
        r = render(fx / "r10-rule-clear" / "visual.html", "--out", str(cwd / "r10fx" / "clear"))
        assert r.returncode == 0 and "rule runs" not in r.stdout, r.stdout
        wordy = cwd / "r10" / "wordy.html"
        wordy.write_text('<!doctype html><meta charset="utf-8"><link rel="stylesheet" href="' + (SKILL / "assets" / "tokens.css").resolve().as_uri() + '">'
                         '<section class="page" style="background: var(--paper); color: var(--ink); padding: 90px 80px"><h1 data-role="hook" style="font: 650 100px/1 var(--disp)">Sixty&nbsp;words.</h1>'
                         '<p style="font: 450 36px/1.3 var(--body); margin-top: 40px">' + " ".join(["word"] * 58) + "</p></section>", encoding="utf-8")
        r = render(wordy, "--out", str(cwd / "r10fx" / "wordy"))
        assert "60 words on one page, 15 over the budget of 45" in r.stdout and "Cut 15 words" in r.stdout and 'references/copy.md "Word budget"' in r.stdout, r.stdout
    # --pin on a quick deal: the register is fixed for every seed and kept on a later deal; it is refused off the genome and for a value the axis lacks
    quick_to_visual(cwd, "r10p", "a quiet handover at the end of a shift", notes, None)
    for seed in range(8):
        run(cwd, "deal", "r10p", "genome", "--seed", str(seed), *(["--pin", "register=warmth"] if seed == 0 else []))
        g = piece_json(cwd, "r10p")["genome"]
        assert g["register"] == "warmth" and g["ground"] in compose.register_grounds("warmth"), g
    t = (cwd / ".atelier" / "pieces" / "r10p" / "04-genome.md").read_text(encoding="utf-8")
    assert "Pinned with --pin: register=warmth." in t and "--register warmth" in t, t
    r = run(cwd, "deal", "r10p", "angles", "--pin", "register=warmth", ok=False)
    assert r.returncode != 0 and "--pin is for the genome" in r.stderr, r.stderr
    r = run(cwd, "deal", "r10p", "genome", "--pin", "register=lukewarm", ok=False)
    assert r.returncode != 0 and "--pin register=lukewarm" in r.stderr, r.stderr
    # the kitchen-rail specimen: four tickets inside the 80 px margins, its words in the text face
    kr = (compose.SPECS / "kitchen-rail.html").read_text(encoding="utf-8")
    lefts, width = [int(x) for x in re.findall(r'class="t[^"]*" style="left:(\d+)px', kr)], int(re.search(r"\.t \{[^}]*width: (\d+)px", kr).group(1))
    t_rule = re.search(r"\.t \{[^}]*\}", kr).group(0)
    assert len(lefts) == 4 and min(lefts) == 80 and max(lefts) + width == 1000 and "var(--body)" in t_rule and "var(--mono)" not in kr, (lefts, width, t_rule)
    print(f"PASS r10: 12 layout words defined and 17 specimens name their layout and frame; page 1 never got the specimen's layout in 400 pure and {dealt} dealt rhythms (a format's pin wins); "
          "kitchen-rail and timetable get a composition start with none of the specimen's words or markup, and both worksheets name the frame to leave, the layout, the object atom and the 45-word budget; "
          + ("the 12 layouts render, only the stack sets the hook as a top band; a rule through text fails, rules beside it pass, the budget warning names the cut; " if rr is not None else "")
          + "--pin register=warmth holds over 8 deals; kitchen-rail tickets sit at 80 to 1000 px in the text face")


def r11_tests(cwd, notes):
    """R11 (the second 30 Oct 2026 run: distinct 6 in 4 of 6 verdicts): with no --brand, every dealt palette is the piece's own, kept off the specimen
    palette by a stated OKLab distance; the worksheets list the dealt direction's stock parts and say to build the device from the object."""
    import shlex
    sys.dont_write_bytecode = True   # importing palette must not leave a __pycache__ in the repo
    sys.path.insert(0, str(SKILL / "scripts"))
    import palette as pal
    spec = pal.specimen_colours()
    far = lambda hex_, role: min(pal.delta_e(pal.hex_to_rgb(hex_), s) for s in spec[role])
    # (a) 20 dealt genomes with no --brand, each run through the palette line its worksheet prints
    quick_to_visual(cwd, "r11p", "what a Friday release checklist really needs, r11", notes, None)
    seen, accents, worst = [], set(), [1, 1, 1]
    for seed in range(20):
        run(cwd, "deal", "r11p", "genome", "--seed", str(seed))
        g = piece_json(cwd, "r11p")["genome"]
        ws = (cwd / ".atelier" / "pieces" / "r11p" / "04-genome.md").read_text(encoding="utf-8")
        line = next(x.strip() for x in ws.splitlines() if "palette.py" in x and x.strip().startswith(compose.PY + " "))
        assert "--brand" not in line and "this piece's own palette" in ws, line
        out = cwd / "r11pal" / str(seed)
        bash_form = line[2:] if line.startswith("& ") else line   # on Windows the printed line starts with PowerShell's "& "
        r = subprocess.run([sys.executable] + shlex.split(bash_form)[1:] + ["--out", str(out)], capture_output=True, text=True, encoding="utf-8")
        assert r.returncode == 0 and "NOTE no --brand: this piece's own palette" in r.stdout and "in cluster" not in r.stdout, r.stdout + r.stderr
        css = (out / "palette.css").read_text(encoding="utf-8")
        for body in re.findall(r"\.pg-\d+ \{([^}]*)\}", css):
            v = dict(re.findall(r"--([\w-]+):\s*(#[0-9a-f]{6})", body))
            field = v["accent"] == v["text"]
            checks = [("ground", v["ground"], pal.SPEC_MIN, 0), ("text", v["text"], pal.SPEC_MIN, 1)]
            checks += [("accent", v[k], pal.ACC_MIN, 2) for k in ("accent", "accent-2") if k in v and not (field and k == "accent")]
            for role, hex_, need, i in checks:
                d = far(hex_, role)
                worst[i] = min(worst[i], d)
                assert d >= need, f"seed {seed} ({g['register']} {g['harmony']} {g['arc']} {g['ground']}): {role} {hex_} is {d:.3f} from the specimen's, under {need}"
            accents.add(v["accent"])
        seen.append(f"{g['register']}/{g['harmony']}/{g['arc']}")
    assert len(set(seen)) >= 10 and len(accents) >= 10, f"20 deals gave {len(set(seen))} register/harmony/arc sets and {len(accents)} accents"
    # (b) the stock parts: every specimen direction names its own in 04-genome.md, and a quick piece in both worksheets
    dirs = json.loads((SKILL / "data" / "directions.json").read_text(encoding="utf-8"))
    ref = (SKILL / "references" / "directions.md").read_text(encoding="utf-8")
    named = 0
    for d in dirs:
        if not d.get("specimen"):
            assert "stock" not in d, d["id"]
            continue
        assert len(d["stock"]) >= 2 and all(len(x) >= 8 for x in d["stock"]), d["id"]
        assert f"| {d['id']} | {'; '.join(d['stock'])} |" in ref, f"references/directions.md does not list the stock parts of {d['id']}"
        slug = f"r11s-{d['id']}"
        design_piece(cwd, slug, f"a {d['id']} page built from one real record, r11", f"direction={d['id']}", notes,
                     medium="image" if "image" in d["media"] else "carousel", deal=False)
        run(cwd, "deal", slug, "genome", "--seed", "11")
        t = (cwd / ".atelier" / "pieces" / slug / "04-genome.md").read_text(encoding="utf-8")
        assert "Stock parts of the specimen, which must not appear unchanged on the page: " + "; ".join(d["stock"]) + "." in t, f"04-genome.md for {d['id']} does not list its stock parts"
        assert "Build the direction's device out of it" in t and "not as <the stock part it replaces>" in t, t
        named += 1
    for did in ("editorial-poster", "transit-map", "manual-page"):   # the three directions whose parts that run's critics named
        run(cwd, "deal", "r11p", "genome", "--pin", f"direction={did}", "--seed", "3")
        stock = next(x["stock"] for x in dirs if x["id"] == did)
        for ws in ("04-genome.md", "07-visual.md"):
            t = (cwd / ".atelier" / "pieces" / "r11p" / ws).read_text(encoding="utf-8")
            assert all(s in t for s in stock) and "Build the direction's device out of it" in t, f"{ws} for {did} does not name its stock parts"
    # (c) the composition start fits every local display face in all 12 layouts: a wide face (Boldonse) once ran the sample hook into the
    # object column in the split, map and sequence layouts (1 run of 20 failed r4 on it); data/type_pairings.json "hook_scale" sets it smaller
    words = json.loads((SKILL / "data" / "structures.json").read_text(encoding="utf-8"))["layout_words"]
    faces = [x for x in json.loads((SKILL / "data" / "type_pairings.json").read_text(encoding="utf-8")) if x["id"] in compose.local_types()]
    base = (compose.START.replace("@DIR@", "kitchen-rail").replace("@GROUND@", "paper").replace("@BG@", "paper").replace("@FG@", "ink").replace("@SPEC@", "the specimen")
            .replace("@FRAME@", "the frame").replace("@BUDGET@", "45").replace("@HOOK@", "8"))
    def face_pages(x):   # the 12 layouts, every page carrying the sample hook, set in this pairing's display face and hook scale
        style = f"--disp: \"{x['display']}\"; --hook-scale: {x.get('hook_scale', 1)}"
        twelve = re.sub(r"<h2>[^<]*</h2>", f'<h2 data-role="hook">{compose.HOOK_SAMPLE}</h2>', compose.start_pages("kitchen-rail", words, []))
        return re.sub(r'<section class="(page st [a-z]+ pg-\d+)"', lambda m: f"<section class=\"{m.group(1)}\" style='{style}'", twelve)
    pages = "".join(face_pages(x) for x in faces)
    html, _ = compose.absolute_links(base.replace("@PAGES@", pages), compose.SPECS)
    html = compose.fit_logo(html, None)[0].replace("</style>", "</style>" + f'<link rel="stylesheet" href="{(compose.FONTS / "library" / "library.css").as_uri()}">', 1)
    allf = cwd / "r11" / "faces" / "visual.html"
    allf.parent.mkdir(parents=True)
    allf.write_text(html, encoding="utf-8")
    rr = render(allf)
    fits = "skipped (no node or Playwright)"
    if rr is not None:
        audit = json.loads((allf.parent / "audit.json").read_text(encoding="utf-8"))
        assert len(audit) == len(faces) * len(words), (len(audit), rr.stdout[-500:])
        bad = [(faces[i // len(words)]["display"], words[i % len(words)], p["fails"]) for i, p in enumerate(audit) if p["fails"]]
        assert rr.returncode == 0 and not bad, f"a composition start fails its own audit: {bad[:4]}"
        fits = f"all {len(audit)} pages ({len(faces)} local pairings x {len(words)} layouts) pass the audit"
    # (d) the later pages too: their heading carried the format's job at display size ("Page 4: the consequence."), and in the map layout's half-width
    # hook column a long job word crossed the object's border and ran off the page (1 run of 3 failed the core scaffold test on it). These seeded
    # index-card deals put the map layout on page 4 under "the consequence" or "the mechanism"; each is scaffolded and audited.
    design_piece(cwd, "r11m", "a glossary entry filed as a library card, r11", "direction=index-card,type=house", notes, deal=False)
    jobs = {f["id"]: f["sections"] for f in json.loads((SKILL / "data" / "formats.json").read_text(encoding="utf-8"))}
    for seed in (40, 55, 56):
        run(cwd, "deal", "r11m", "genome", "--seed", str(seed))
        g = piece_json(cwd, "r11m")["genome"]
        job = jobs[g["format"]][3]
        assert g["layout_rhythm"][3] == "map" and job in ("the consequence", "the mechanism"), f"seed {seed} no longer deals the map layout under a long job on page 4 ({g['format']}: {g['layout_rhythm']}): pick seeds that do"
        page = cwd / "r11" / f"map-{seed}" / "visual.html"
        run(cwd, "scaffold", "r11m", "--out", str(page))
        rr = render(page)
        if rr is not None:
            assert rr.returncode == 0, f"seed {seed}: the scaffolded {g['format']} carousel fails its own audit on page 4 (map, {job}): {rr.stdout[-700:]}"
    print(f"PASS r11: 20 dealt genomes with no --brand ({len(set(seen))} register/harmony/arc sets, {len(accents)} accents) each got their own palette: grounds and text "
          f"{pal.SPEC_MIN} or more OKLab from the specimens' (closest {worst[0]:.3f} and {worst[1]:.3f}), accents {pal.ACC_MIN} or more (closest {worst[2]:.3f}), no cluster; "
          f"{named} specimen directions list their stock parts in 04-genome.md and references/directions.md; editorial-poster, transit-map and manual-page name theirs in 04-genome.md and 07-visual.md; the composition start in every local face: {fits}; "
          + ("3 seeded index-card carousels with the map layout under a long job on page 4 scaffold and pass their audit" if rr is not None else "the 3 seeded map carousels scaffold (render skipped)"))


R12_FIVE = ("phone read:", "claim twice:", "wrapped run:", "hairline accent:", "empty cell:")


def r12_verdict(path, slug, scores, fix, keep):
    """An art-director entry as the agent writes it: findings with '-> fix', a keep line, the verdict and the scores line."""
    s = ", ".join(f"{k} {v}" for k, v in scores.items())
    path.write_text(f"## {slug}\nreads as: checklist form\npage-01.png seen: \"Nine fit one pause.\"\nflaws: [craft, hierarchy]\n"
                    f"1. page-01, top band: the bracket is the lightest mark on the page -> {fix}\n"
                    "2. page-01, foot: the source line is set at the floor in a light weight -> set it at 36 px in weight 500\n"
                    f"keep: {keep}\nstrongest case to reject: the page states its claim twice.\nverdict: FAIL\nscores: {s}  total 7.0 (capped: no)\n", encoding="utf-8")
    return path


def r12_tests(cwd, notes):
    """R12 (the 30 Oct 2026 run: no piece passed, the critics charged five faults no check named, and a revision fell from 7.3 to 7.2): the audit
    names the five before a critic sees the page, and the revise step starts again from the best attempt with that verdict's fixes and keep line."""
    fx = SKILL / "tests" / "fixtures"
    r = render(fx / "r12-flawed" / "visual.html", "--out", str(cwd / "r12fx" / "flawed"))
    if r is None:
        print("SKIP r12 render checks: node or Playwright is not installed")
        said = "skipped (no node or Playwright)"
    else:
        a = json.loads((cwd / "r12fx" / "flawed" / "audit.json").read_text(encoding="utf-8"))[0]
        assert r.returncode == 0 and not a["fails"], r.stdout
        for w in R12_FIVE:
            assert any(x.startswith(w) for x in a["warns"]), f"the audit does not name '{w}' on the flawed page: {a['warns']}"
        assert a["minAll"] == 32 and "(32px with fine print)" in r.stdout, r.stdout
        hits = {w: next(x for x in a["warns"] if x.startswith(w)) for w in R12_FIVE}
        assert '"9 fit one pause"' in hits["claim twice:"] and "7 as 5 + 2" in hits["wrapped run:"] and "6 px thick" in hits["hairline accent:"] and '"Before the change"' in hits["empty cell:"], hits
        r = render(fx / "r12-clean" / "visual.html", "--out", str(cwd / "r12fx" / "clean"))
        c = json.loads((cwd / "r12fx" / "clean" / "audit.json").read_text(encoding="utf-8"))[0]
        assert r.returncode == 0 and not [x for x in c["warns"] if x.startswith(R12_FIVE)] and "with fine print" not in r.stdout, r.stdout
        said = "the flawed page gets all five warnings and its 32 px fine print in the page line; the clean page gets none"
    # the revise step: attempt 1 scores 7.3, attempt 2 falls to 7.2; next starts from attempt 1, kept with its page and verdict, and prints its fixes and keep line
    page = cwd / "r12" / "rv" / "visual.html"
    n = quick_to_visual(cwd, "r12v", "a release list in three pauses, r12", notes, page)
    start = render(page)   # the composition start's own lines (the object box, the source line) are not under the phone-read line
    if start is not None:
        sw = json.loads((page.parent / "audit.json").read_text(encoding="utf-8"))[0]["warns"]
        assert start.returncode == 0 and not [x for x in sw if x.startswith("phone read:")], sw
    ok = {"idea": 8, "hook": 7, "hierarchy": 7, "craft": 7, "colour": 7, "distinct": 8}
    low = dict(ok, distinct=7)
    for i, (sc, fix, keep) in enumerate(((ok, "draw the bracket 8 px thick", "the 19 boxes in one frame"), (low, "move the label above the run", "the seams at the gap centres")), 1):
        page.write_text(page.read_text(encoding="utf-8").replace("</section>", f"<!-- attempt {i} --></section>", 1), encoding="utf-8")
        fresh_render(page.parent, page.name)
        v = r12_verdict(notes / f"r12v-{i}.md", "r12v", sc, fix, keep)
        g = vgrade(cwd, "r12v", n, v, ",".join(f"{k}={x}" for k, x in sc.items()))
        assert g.returncode == 1 and "REVISE" in g.stdout, g.stdout + g.stderr
    kept = cwd / ".atelier" / "pieces" / "r12v" / "attempts" / "visual-1"
    assert "<!-- attempt 1 -->" in (kept / "visual.html").read_text(encoding="utf-8") and (kept / "verdict.md").is_file() and (kept / "page-01.png").is_file(), sorted(p.name for p in kept.iterdir())
    nx = run(cwd, "next", "r12v").stdout
    assert "Start from attempt 1, the best so far (7.3)" in nx and kept.as_posix() in nx, nx
    assert "fix 1: draw the bracket 8 px thick" in nx and "keep: the 19 boxes in one frame" in nx and "move the label above the run" not in nx, nx
    assert piece_json(cwd, "r12v")["stages"]["visual"]["grades"][0]["attempt"] == str(kept.resolve()) or piece_json(cwd, "r12v")["stages"]["visual"]["grades"][0]["attempt"] == str(kept), "the grade does not name its kept attempt"
    # the r5 fixtures (design-doctrine warnings) had no runner: each one's planted warning is asserted here, and r5-allowed's data-allow silences them
    doctrine = ("fake product chrome", "pill-shaped", "corner radii", "nested panels", "raw colours")
    if r is not None:
        def warns(name):
            out = cwd / "r12fx" / name
            rr = render(fx / name / "visual.html", "--out", str(out))
            assert rr.returncode == 0, rr.stdout
            return [p["warns"] for p in json.loads((out / "audit.json").read_text(encoding="utf-8"))]
        ch = warns("r5-chrome")[0]
        assert [any(w.startswith(x) for w in ch) for x in ("fake product chrome: 1 row(s) of red, amber and green dots", "fake product chrome: a status dot beside", 'fake product chrome: "NEW" in a pill or box')] == [True] * 3, ch
        assert any(w.startswith("nested panels: 1 box(es) sit three deep") for w in warns("r5-nested")[0])
        p1, p2 = warns("r5-pills")
        assert any(w.startswith("4 pill-shaped tags") for w in p1) and any(w.startswith("3 different corner radii (28px, 14px, 6px)") for w in p2), (p1, p2)
        p1, p2 = warns("r5-rawcolour")
        assert any(w.startswith("9 raw colours") for w in p1) and not any("raw colours" in w for w in p2), (p1, p2)
        al = warns("r5-allowed")[0]
        assert not [w for w in al if any(d in w for d in doctrine)], al
    cl = subprocess.run([sys.executable, str(SKILL / "scripts" / "copy_lint.py"), str(fx / "r5-repeat" / "visual.html")], capture_output=True, text=True, encoding="utf-8")
    assert cl.returncode == 0 and "repeated words: quiet x3 (pages 2, 3, 4), list x2 (twice on page 2)" in cl.stdout, cl.stdout
    # layout memory from a page's own folder (the quick path runs the checks there): it finds the project's covers, and a check makes no folder
    from PIL import Image
    proj = cwd / "r12lm"
    (proj / ".atelier" / "covers").mkdir(parents=True)
    (proj / "page").mkdir()
    Image.new("L", (108, 135), 255).save(proj / ".atelier" / "covers" / "old.png")
    im = Image.new("L", (108, 135), 255)
    im.paste(0, (10, 10, 98, 60))
    im.save(proj / "page" / "page-01.png")
    lm = subprocess.run([sys.executable, str(SKILL / "scripts" / "layout_memory.py"), "check", "page-01.png"], cwd=proj / "page", capture_output=True, text=True)
    assert "against 1 remembered cover(s)" in lm.stdout and not (proj / "page" / ".atelier").exists(), lm.stdout + lm.stderr
    print(f"PASS r12: {said}; a failed visual grade keeps its page, render and verdict, and next starts from the best attempt (7.3, not the later 7.2) with its fixes and keep line; "
          "layout_memory.py check from a page's folder compares with the project's covers and makes no .atelier there; the six r5 fixtures each raise their planted warning, and r5-allowed raises none")


def r13_tests(cwd):
    """R13 (the 30 Oct 2026 round 12 run: two faults cost a point each and no check named them): the audit warns on a mark with no text
    under 3:1 against its ground (WCAG 1.4.11; piece 1's empty slots) and on display type drawn in a thin stroke (piece 3's script hook)."""
    fx = SKILL / "tests" / "fixtures"
    pages = {}
    for name in ("r13-faint-mark", "r13-thin-script", "r12-clean"):
        r = render(fx / name / "visual.html", "--out", str(cwd / "r13fx" / name))
        if r is None:
            print("SKIP r13: node or Playwright is not installed")
            return
        assert r.returncode == 0, r.stdout
        pages[name] = [p["warns"] for p in json.loads((cwd / "r13fx" / name / "audit.json").read_text(encoding="utf-8"))]
    hit = lambda warns, w: next((x for x in warns if x.startswith(w)), None)
    faint, firm = pages["r13-faint-mark"]
    m = re.search(r"8 x i\.e (\d\.\d):1", hit(faint, "faint mark:") or "")
    assert m and float(m.group(1)) < 3, f"the empty slots under 3:1 got no faint-mark warning naming all 8: {faint}"
    assert not hit(firm, "faint mark:"), f"the empty slots at 3:1 or more were called faint: {firm}"
    script, bold, plain = pages["r13-thin-script"]
    t = hit(script, "thin stroke:")
    assert t and "Nothing You Could Do" in t, f"the script hook got no thin-stroke warning: {script}"
    assert not hit(bold, "thin stroke:") and not hit(plain, "thin stroke:"), f"a heavy or regular text face was called thin: {bold} {plain}"
    assert not [x for x in pages["r12-clean"][0] if x.startswith(("faint mark:", "thin stroke:"))], pages["r12-clean"]
    phone = re.search(r"about ([\d.]+) px on a phone", t).group(1)
    print(f"PASS r13: the empty slots at {m.group(1)}:1 get 'faint mark' and at 3:1 or more do not; the 84 px script hook gets 'thin stroke' "
          f"({phone} px on a phone) and the same hook in Work Sans 700, or Work Sans 400 at 64 px, does not; r12-clean gets neither")


def faint_twin_tests(cwd):
    """R14: a faint mark is measured against the ground behind its own drawn shape. Dots on a line of their own colour are one shape and do
    not warn (the round 14 score found them at 1.0:1 on 5 of 8 run pages); grey empty slots and a dot lost on a panel of its colour do."""
    r = render(SKILL / "tests" / "fixtures" / "r14-faint-twin" / "visual.html", "--no-png", "--out", str(cwd / "twin"))
    if r is None:
        print("SKIP faint twin: node or Playwright is not installed")
        return
    w = next((x for x in json.loads((cwd / "twin" / "audit.json").read_text(encoding="utf-8"))[0]["warns"] if x.startswith("faint mark:")), "")
    assert r.returncode == 0 and "i.lost 1.0:1" in w and re.search(r"2 x i\.slot 2\.\d:1", w) and "i.stop" not in w, r.stdout
    print("PASS r14 faint twin: four dots on a line of their own colour do not warn; two grey empty slots and a dot on a panel of its own colour do")


def r13_next_tests(cwd, notes):
    """After scaffold wrote the page, `next` names that page and no longer says to scaffold (a second scaffold refuses with exit 1)."""
    quick_to_visual(cwd, "r13n", "a release list in three pauses, r13 next", notes, None)
    before = run(cwd, "next", "r13n").stdout
    assert "start the page:" in before and " scaffold r13n" in before, before
    page = cwd / "r13n" / "visual.html"
    run(cwd, "scaffold", "r13n", "--out", str(page))
    after = run(cwd, "next", "r13n").stdout
    assert "start the page" not in after and " scaffold r13n" not in after and page.as_posix() in after and "build the page scaffold wrote" in after, after
    again = run(cwd, "scaffold", "r13n", "--out", str(page), ok=False)
    assert again.returncode == 1 and "exists" in (again.stdout + again.stderr), again.stdout + again.stderr
    print("PASS r13 next: before scaffold, next says to scaffold; after it, next names the page scaffold wrote and does not say to scaffold again (which refuses)")


def next_lines_tests(cwd, notes):
    """R14: (a) after a RECREATE grade, choose prints what next prints (deal the angles again), not a genome deal that refuses; (b) next
    prints every command on a line of its own, and each whole line runs as printed: in PowerShell, and in Git Bash with MSYSTEM set."""
    import shlex
    run(cwd, "new", "cr", "--topic", "a pallet label dealt twice", "--scope", "quick", "--medium", "image")
    assert "PASSED" in grade(cwd, "cr", "atoms", 9, notes).stdout
    run(cwd, "deal", "cr", "angles")
    # the worksheet's grade line leaves no bare | for bash to run as a pipe, and its choose line is a whole line
    ws = next(cwd.rglob("cr/03-angles.md")).read_text(encoding="utf-8")
    assert "pass|fail" not in ws and "--swap <pass-or-fail>" in ws, "the grade line carries a bare | that bash runs as a pipe"
    pick = after_label(ws, "Then record the operator")
    assert " choose cr angle " in pick and re.fullmatch(r'(& )?"[^"]+" "[^"]+\.py"( .*)?', pick), pick
    qa = notes / "cr-angles.md"
    qa.write_text("\n".join(f"{c}: because the candidate repeats a stock phrase and names no sourced number" for c in CRIT["angles"].split()))
    assert "RECREATE" in run(cwd, "grade", "cr", "angles", "--scores", "novelty=4,truth=4,relevance=4,intrigue=4,tone=4", "--notes", str(qa), "--by", "self", ok=False).stdout
    said = run(cwd, "choose", "cr", "angle", "1", "--text", "a pallet label read as a ledger").stdout.split("Next:", 1)[1]
    assert said.strip() == run(cwd, "next", "cr").stdout.strip() and " genome" not in said, said
    line = next(l.strip() for l in said.splitlines() if " deal cr " in l)
    assert run(cwd, *shlex.split(line[2:] if line.startswith("& ") else line)[2:]).returncode == 0, line   # the printed deal runs
    # (b) one project, two shells; each runs the palette and scaffold lines next printed for it, in a folder of its own
    shells = []
    ps = shutil.which("powershell") if sys.platform == "win32" else None
    if ps:
        enc = lambda line: base64.b64encode(line.encode("utf-16-le")).decode()
        shells.append(("ps", {k: v for k, v in os.environ.items() if k != "MSYSTEM"},
                       lambda line, where, env: subprocess.run([ps, "-NoProfile", "-NonInteractive", "-EncodedCommand", enc(line)], cwd=where, env=env, capture_output=True, text=True)))
    bash = find_bash()
    if bash:
        shells.append(("gb", {**os.environ, "MSYSTEM": "MINGW64"} if sys.platform == "win32" else dict(os.environ),
                       lambda line, where, env: subprocess.run([bash, "-c", line], cwd=where, env=env, capture_output=True, text=True)))
    whole = re.compile(r'(& )?"[^"]+" "[^"]+\.py"( .*)?')
    for name, env, sh in shells:
        slug = f"nl-{name}"
        quick_to_visual(cwd, slug, f"a crate counted at one gate, {name}", notes, None)
        where = cwd / name
        where.mkdir()
        out = subprocess.run(C + ["next", slug], cwd=where, env=env, capture_output=True, text=True).stdout
        cmds = [l.strip() for l in out.splitlines() if '.py" ' in l]
        assert len(cmds) == 3 and all(whole.fullmatch(c) for c in cmds), f"next printed a command inside a sentence:\n{out}"
        for c in (next(c for c in cmds if "palette.py" in c), next(c for c in cmds if f" scaffold {slug}" in c)):
            r = sh(c, where, env)
            assert r.returncode == 0, f"{name}: a printed line did not run as printed: {c}\n{r.stdout}{r.stderr}"
        assert (where / "palette.css").is_file() and (where / "visual.html").is_file(), sorted(p.name for p in where.iterdir())
        # scaffold's own "next" and new's "Lost? Run:" also print the label and the command on lines of their own
        render_line = after_label(r.stdout, "next")
        a = sh(render_line, where, env)
        assert render_line.startswith("node ") and "audit: " in a.stdout, f"{name}: scaffold's audit line did not run as printed: {render_line}\n{a.stdout}{a.stderr}"
        lost = after_label(subprocess.run(C + ["new", f"{slug}-new", "--topic", f"a crate label read twice, {name}"], cwd=where, env=env, capture_output=True, text=True).stdout, "Lost? Run:")
        b = sh(lost, where, env)
        assert b.returncode == 0 and "atoms: fill" in b.stdout, f"{name}: new's 'Lost? Run:' line did not run as printed: {lost}\n{b.stdout}{b.stderr}"
    print("PASS r14 next lines: after a RECREATE, choose prints next's own step and its deal runs; next, scaffold and new print each command on a line of "
          f"its own, and the palette, scaffold, audit and next lines run as printed in {' and '.join({'ps': 'PowerShell', 'gb': 'Git Bash'}[n] for n, *_ in shells) or 'no shell found'}")


def attention_role_tests(cwd):
    """R14: a page the audit rendered with no data-role at all (it fails the missing hook) also fails attention.py, which used to pass it
    with a note; with no boxes.json at all, attention.py still only notes that the audit has not run."""
    page = cwd / "norole" / "visual.html"
    page.parent.mkdir()
    page.write_text(f'<!doctype html><meta charset="utf-8"><link rel="stylesheet" href="{(SKILL / "assets" / "tokens.css").as_uri()}">'
                    '<section class="page" style="background:var(--paper);color:var(--ink)"><h1 style="margin:80px;font:700 96px/1 var(--disp)">'
                    'Nothing here says what&nbsp;leads.</h1></section>', encoding="utf-8")
    r = render(page)
    if r is None:
        print("SKIP attention roles: node or Playwright is not installed")
        return
    assert r.returncode == 1 and 'no data-role="hook"' in r.stdout, r.stdout
    at = lambda: subprocess.run([sys.executable, str(SKILL / "scripts" / "attention.py"), str(page.parent)], capture_output=True, text=True, encoding="utf-8")
    a = at()
    assert a.returncode == 1 and "FAIL no data-role on this page" in a.stdout, a.stdout
    (page.parent / "boxes.json").unlink()
    b = at()
    assert b.returncode == 0 and "no boxes.json" in b.stdout, b.stdout
    print("PASS r14 attention roles: a rendered page with no data-role fails attention.py (exit 1) as it fails the audit; with no boxes.json it only notes it")


def guard_tests(cwd):
    """R14: the guard itself. A deal, a delivery or a coverage read in a project another test owns is refused before it runs."""
    run(cwd, "new", "gd", "--topic", "a guard that keeps each test's memory its own")
    with own_project("intruder"):
        for cmd in (["deal", "gd", "lenses"], ["deliver", "gd"], ["coverage"]):
            try:
                run(cwd, *cmd)
            except AssertionError as e:
                assert str(e).startswith(f"intruder ran '{cmd[0]}' in the project of guard_tests"), e
            else:
                raise AssertionError(f"the guard let another test run {cmd[0]} in guard_tests' project")
    try:
        run(pathlib.Path(tempfile.gettempdir()), "coverage")
    except AssertionError as e:
        assert "a folder no test owns" in str(e), e
    else:
        raise AssertionError("the guard let a test read the memory of a folder no test owns")
    assert run(cwd, "coverage").returncode == 0, "the owner may read its own memory"
    print("PASS r14 guard: a deal, a delivery or a coverage read in another test's project, or in a folder no test owns, is refused; the owner's runs")


def main():
    parser_tests()
    with own_project("core") as d:
        cwd = pathlib.Path(d)
        notes = cwd / "notes"
        notes.mkdir()
        a = full_piece(cwd, "a", "monthly reporting automation for agencies", notes)
        b = full_piece(cwd, "b", "monthly reporting automation for agencies", notes)
        ops_a, ops_b = a["stages"]["angles"]["deals"][-1], b["stages"]["angles"]["deals"][-1]
        lens_a, lens_b = a["stages"]["lenses"]["deals"][-1], b["stages"]["lenses"]["deals"][-1]
        assert not set(ops_a) & set(ops_b), f"same topic reused operators: {set(ops_a) & set(ops_b)}"
        assert not set(lens_a) & set(lens_b), f"same topic reused lenses: {set(lens_a) & set(lens_b)}"
        ga, gb = a["genome"], b["genome"]
        diff = sum(1 for k in ("format", "direction", "register", "hook", "close", "harmony", "arc", "type") if ga[k] != gb[k])
        assert diff >= 3, f"same topic produced near-identical genomes ({diff} axes differ)"
        assert ga["format"] != gb["format"] and ga["direction"] != gb["direction"], "same topic reused format or direction"
        ra, rb = (x["stages"]["visual"]["grades"][-1]["evidence"]["render"] for x in (a, b))   # R3a-1: the visual grade stores the sha256 of the page and of each render
        assert all(re.fullmatch(r"[0-9a-f]{64}", s) for s in (ra["html_sha256"], *ra["pages"].values())) and set(ra["pages"]) == {"page-01.png"}, ra
        assert ra["html_sha256"] != rb["html_sha256"] and a["visual_html"] == ra["html"], "each piece is graded on its own page, and the grade names it in piece.json"
        print(f"PASS same topic twice: operators, lenses, format and direction all differ; {diff} of 8 genome axes differ")
        # every worksheet prints commands that work from any folder (the absolute path) and a notes template with the exact criterion names
        for f in sorted((cwd / ".atelier" / "pieces" / "a").glob("*.md")):
            t, stage = f.read_text(encoding="utf-8"), f.stem.split("-", 1)[1]
            assert "python compose.py" not in t and (SKILL / "scripts" / "compose.py").as_posix() in t, f"{f.name} prints a bare compose.py"
            assert all(f"\n{c}: \n" in t for c in CRIT[stage].split()), f"{f.name} has no notes template with {CRIT[stage]}"
            assert ("--evidence" in t) == (stage in INDEP), f"{f.name}: --evidence must be named exactly for the critic stages"
        gws = (cwd / ".atelier" / "pieces" / "a" / "04-genome.md").read_text(encoding="utf-8")
        assert (SKILL / "scripts" / "palette.py").as_posix() in gws and (SKILL / "scripts" / "render.mjs").as_posix() in (cwd / ".atelier" / "pieces" / "a" / "07-visual.md").read_text(encoding="utf-8")
        st = json.loads((SKILL / "data" / "structures.json").read_text(encoding="utf-8"))   # R3a-4: the dealt hook and close are defined in the worksheet
        for key, rows in (("hook", st["hooks"]), ("close", st["closes"])):
            assert all(re.fullmatch(r"[A-Z][^\n]{15,150}\.", x["definition"]) for x in rows), f"every {key} has a one-line definition"
            assert f'{key.capitalize()} "{ga[key]}": ' + next(x["definition"] for x in rows if x["id"] == ga[key]) in gws, f"04-genome.md does not define the dealt {key} {ga[key]}"
        assert "- lens: " + ga["lens"] in gws and "(host angle)" not in gws and "none (quick scope)" not in gws, "a full piece names its lens"
        print("PASS worksheets: absolute paths for compose.py, palette.py and render.mjs; a notes template per stage; --evidence named for critic stages")
        # a weak grade forces a recreate, then an escalation after max attempts
        run(cwd, "new", "c", "--topic", "a completely different subject about invoices")
        grade(cwd, "c", "atoms", 9, notes)
        run(cwd, "deal", "c", "lenses")
        r = grade(cwd, "c", "lenses", 4, notes)
        assert "RECREATE" in r.stdout, r.stdout
        nxt = run(cwd, "next", "c").stdout
        assert "RECREATE" in nxt and "deal" in nxt, nxt
        run(cwd, "deal", "c", "lenses")
        p = piece_json(cwd, "c")
        d1, d2 = p["stages"]["lenses"]["deals"][0], p["stages"]["lenses"]["deals"][1]
        assert not set(d1) & set(d2), "a recreate repeated lenses from the failed deal"
        grade(cwd, "c", "lenses", 4, notes)
        r = grade(cwd, "c", "lenses", 4, notes)
        assert "ESCALATED" in r.stdout, r.stdout
        print("PASS low grade -> recreate with a fresh deal -> escalate after 3 attempts")
        # independent stages refuse self-grading; thin notes are refused
        run(cwd, "new", "e", "--topic", "colour arcs in a six page carousel")
        n = notes / "thin.md"
        n.write_text("coverage: ok\nspecificity: ok\nsourced: ok\nsurprise: ok")
        r = run(cwd, "grade", "e", "atoms", "--scores", "coverage=9,specificity=9,sourced=9,surprise=9", "--notes", str(n), ok=False)
        assert r.returncode != 0 and "because" in (r.stdout + r.stderr), r.stdout + r.stderr
        grade(cwd, "e", "atoms", 9, notes)
        run(cwd, "deal", "e", "lenses"); grade(cwd, "e", "lenses", 9, notes); run(cwd, "deal", "e", "angles")
        n2 = notes / "angles-self.md"
        n2.write_text("\n".join(f"{c}: because the candidate quotes a sourced number on line 2" for c in CRIT["angles"].split()))
        r = run(cwd, "grade", "e", "angles", "--scores", "novelty=9,truth=9,relevance=9,intrigue=9,tone=9", "--notes", str(n2), "--by", "self", ok=False)
        assert r.returncode != 0 and "independent" in (r.stdout + r.stderr), r.stdout + r.stderr
        print("PASS thin notes refused; independent stages refuse self-grading")
        # a critic's grade carries the critic's file: none, the author's own notes, a short file and a file with no verdict are all refused
        crit = ["grade", "e", "angles", "--scores", "novelty=10,truth=4,relevance=10,intrigue=10,tone=10", "--notes", str(n2), "--by", "critic"]
        r = run(cwd, *crit, ok=False)
        assert r.returncode != 0 and "--evidence" in (r.stdout + r.stderr), "a critic grade passed with no evidence file: " + r.stdout + r.stderr
        r = run(cwd, *crit, "--evidence", str(n2), ok=False)
        assert r.returncode != 0 and "differ" in (r.stdout + r.stderr), "the author's own notes were taken as the critic's evidence"
        short = cwd / "short.md"; short.write_text("verdict: PASS")
        r = run(cwd, *crit, "--evidence", str(short), ok=False)
        assert r.returncode != 0 and "200 characters" in (r.stdout + r.stderr), "a short evidence file was accepted"
        bare = cwd / "bare.md"; bare.write_text("The candidates were read against the worksheet and the sources, and every claim was traced back to an atom in the table. " * 3)
        r = run(cwd, *crit, "--evidence", str(bare), ok=False)
        assert r.returncode != 0 and "verdict or score" in (r.stdout + r.stderr), "an evidence file with no verdict or score line was accepted"
        assert "grades" not in piece_json(cwd, "e")["stages"]["angles"], "a refused grade was recorded"
        # the critic's FAIL for an untrue angle (truth 4) is recorded as a failed attempt; the typed scores are the critic's own
        cv = verdict(notes / "e-angles-critic.md", "angles", 8, word="FAIL", scores={"novelty": 10, "truth": 4, "relevance": 10, "intrigue": 10, "tone": 10})
        # caps: untrue angle capped, and the evidence path and sha256 are stored with the grade
        r = run(cwd, *crit, "--evidence", str(cv), ok=False)
        assert "capped" in r.stdout and "RECREATE" in r.stdout, r.stdout
        rec = piece_json(cwd, "e")["stages"]["angles"]["grades"][-1]["evidence"]
        assert rec["sha256"] == hashlib.sha256(cv.read_bytes()).hexdigest() and pathlib.Path(rec["path"]) == cv.resolve(), rec
        print("PASS a critic grade needs the critic's file (not the notes, not a stub, not a file with no verdict); path and sha256 stored; a brilliant but untrue angle is capped at 5 and recreated")
        cov = run(cwd, "coverage").stdout
        assert "cells used" in cov
        print("PASS coverage report:", cov.splitlines()[0])
        # design scope: a host system's graded angle feeds the genome and the memory, never an ungraded one
        run(cwd, "new", "h1", "--topic", "approval pages for social posts", "--scope", "design")
        thin = cwd / "thin.md"; thin.write_text("PASS")
        r = run(cwd, "adopt", "h1", "--angle", "the approval page as a boarding pass", "--operator", "invert-order", "--evidence", str(thin), ok=False)
        assert r.returncode != 0 and "grading record" in (r.stdout + r.stderr), r.stdout + r.stderr
        ev = cwd / "angle-judge.md"; ev.write_text("verdict: PASS\n" + "novelty 8 because no earlier post treats approval as a ticket; truth 9 because the page does gate every post\n" * 3)
        ops = [o["id"] for o in json.loads((SKILL / "data" / "operators.json").read_text())]
        unrel = cwd / "unrelated.md"; unrel.write_text("score: 8/10\n" + "The quarterly offsite covers catering, travel and room bookings for the whole team, and the budget is agreed. " * 3)
        r = run(cwd, "adopt", "h1", "--angle", "the approval page as a boarding pass", "--operator", ops[0], "--evidence", str(unrel), ok=False)
        assert r.returncode != 0 and "angle" in (r.stdout + r.stderr), "evidence about another subject was accepted for this angle: " + r.stdout + r.stderr
        r = run(cwd, "adopt", "h1", "--angle", "the approval page as a boarding pass", "--operator", ops[0], "--evidence", str(bare), ok=False)
        assert r.returncode != 0 and "verdict or score" in (r.stdout + r.stderr), "a record with no verdict or score line was accepted"
        r = run(cwd, "adopt", "h1", "--angle", "the approval page as a boarding pass", "--operator", "not-an-operator", "--evidence", str(ev), ok=False)
        assert r.returncode != 0, "an unknown operator was accepted"
        r = run(cwd, "adopt", "h1", "--angle", "the approval page as a boarding pass", "--operator", ops[0], "--evidence", str(ev), "--pin", "direction=night-blueprint", ok=False)
        assert r.returncode != 0 and "--pin" in (r.stdout + r.stderr), "a direction outside data/directions.json was pinned"
        run(cwd, "adopt", "h1", "--angle", "the approval page as a boarding pass", "--operator", ops[0], "--evidence", str(ev), "--pin", "direction=receipt,register=dry")
        run(cwd, "deal", "h1", "genome")
        g = piece_json(cwd, "h1")["genome"]
        assert g["direction"] == "receipt" and g["register"] == "dry" and g["ground"] == "dark", g
        assert "PASSED" in grade(cwd, "h1", "genome", 8, notes).stdout
        nx = run(cwd, "next", "h1").stdout
        assert "Design stages passed. Build and render the piece. Deliver only after the host approves it:" in nx and "every stage passed" not in nx, nx
        assert (SKILL / "scripts" / "compose.py").as_posix() in nx and "deliver h1" in nx, nx
        hws = (cwd / ".atelier" / "pieces" / "h1" / "04-genome.md").read_text(encoding="utf-8")
        assert "- lens: (host angle)" in hws and "- field_page: " in hws, hws
        print("PASS design scope: the next step says to build and render, and to deliver only after the host approves; the genome shows lens (host angle)")
        run(cwd, "deliver", "h1")
        last = json.loads((cwd / ".atelier" / "history.jsonl").read_text().splitlines()[-1])
        assert last["scope"] == "design" and last["genome"].get("operator") == ops[0] and last["genome"].get("format"), last
        assert last["evidence"]["angles"]["sha256"] == hashlib.sha256(ev.read_bytes()).hexdigest(), last["evidence"]
        first = json.loads((cwd / ".atelier" / "history.jsonl").read_text().splitlines()[0])
        assert set(first["evidence"]) == INDEP and all(re.fullmatch(r"[0-9a-f]{64}", v["sha256"]) and pathlib.Path(v["path"]).is_file() for v in first["evidence"].values()), first["evidence"]
        assert not (cwd / ".atelier" / "history.json").exists(), "memory must be the one file history.jsonl"
        r = run(cwd, "new", "h2", "--topic", "approval pages for social posts", "--scope", "design")
        r = run(cwd, "adopt", "h2", "--angle", "the approval page as a boarding pass", "--operator", ops[1], "--evidence", str(ev), ok=False)
        assert r.returncode != 0 and "overlaps" in (r.stdout + r.stderr), "a remembered angle was adopted again"
        print("PASS design scope: graded angles only, evidence on the angle and with a verdict, unknown operators and pins refused, host pins kept, genome dealt and remembered with the evidence hashes, a repeated angle refused")
        # a record with a score line is enough when it carries the angle's own words (6 or more in a row)
        g1 = design_piece(cwd, "s1", "a release checklist printed like a maintenance task card", "direction=task-card", notes)
        # K1: scaffold writes a page that loads: absolute links that exist, one section per page, the hook marked, palette.css linked when it exists
        out1 = cwd / "pages" / "s1" / "visual.html"
        r = run(cwd, "scaffold", "s1", "--out", str(out1))
        html = out1.read_text(encoding="utf-8")
        assert_links_work(html)
        assert any(u.endswith("tokens.css") for u in links(html)) and "palette.css" in r.stdout and "not found" in r.stdout, r.stdout
        assert len(re.findall(r'<section class="page[^"]*"', html)) == len(g1["layout_rhythm"]) and 'data-role="hook"' in html and "pg-1" in html, "pages, hook or palette class missing"
        assert out1.resolve().as_posix() in r.stdout and "render.mjs" in r.stdout and "--audit" in r.stdout, r.stdout
        r = run(cwd, "scaffold", "s1", "--out", str(out1), ok=False)
        assert r.returncode != 0 and "--force" in (r.stdout + r.stderr), "scaffold overwrote an existing page without --force"
        (out1.parent / "palette.css").write_text(".pg-1 { --ground: #111111; }\n")
        run(cwd, "scaffold", "s1", "--out", str(out1), "--force")
        html = out1.read_text(encoding="utf-8")
        assert_links_work(html)
        assert any(u.endswith("palette.css") for u in links(html)), "palette.css exists next to the page but is not linked"
        # a direction with no specimen gets a minimal page; the default page is ./visual.html. The widest face is pinned to stress the layout.
        g2 = design_piece(cwd, "s2", "the invoice read aloud by a field guide to its own errors", "direction=field-guide,type=heavy-display", notes)
        for left in ("visual.html", "audit.json", "page-01.png"):   # the full pieces' fixture render, in the project folder
            (cwd / left).unlink(missing_ok=True)
        r = run(cwd, "scaffold", "s2")
        html = (cwd / "visual.html").read_text(encoding="utf-8")
        assert_links_work(html)
        assert len(re.findall(r'<section class="page[^"]*"', html)) == len(g2["layout_rhythm"]) and 'data-role="hook"' in html, "minimal page: pages or hook missing"
        # G1-4: the minimal page takes colour from the palette.css roles and type from the dealt pairing, not from --night, --cream and the house faces
        mn = re.search(r"\.mn \{([^}]*)\}", html).group(1)
        assert "background: var(--ground," in mn and "color: var(--text," in mn and "var(--accent," in html and "var(--text-2," in html, "the minimal page ignores the palette.css roles: " + mn
        assert "background: var(--night)" not in html and "color: var(--cream)" not in html, "the minimal page still hard-codes tokens.css colours"
        assert 'Boldonse' in html and '--disp: "Boldonse"' in html and '--body: "Work Sans"' in html and '--mono: "Geist Mono"' in html, "the dealt pairing's families are not set"
        assert any(u.endswith("library.css") for u in links(html)) and "library.css linked" in r.stdout, "the font library is not linked"
        assert "NOT" not in r.stdout.split("type heavy-display")[1].split("\n")[0], r.stdout
        # R3a-5: scaffold says, in one line, that a direction with no specimen gets a plain start; one with a specimen does not say it
        assert "field-guide: no specimen, so this page is a plain start" in r.stdout and "plain start" not in run(cwd, "scaffold", "s1", "--out", str(out1), "--force").stdout, r.stdout
        # R3a-6: only the placeholder line is placed at a fixed spot; a paragraph the author adds flows under the bar and never lands on another
        assert 'class="claim"' in html and not re.search(r"\.mn p \{[^}]*position", html) and re.search(r"\.mn \.claim \{[^}]*position: absolute", html) and re.search(r"\.mn \.fine \{[^}]*position: absolute", html), "the minimal page places every paragraph at one spot"
        extra = cwd / "pages" / "s2-captions.html"
        extra.write_text(html.replace('<p class="claim">Replace this with the claim and its proof.</p>', "".join(f"<p>Caption {n} for the chart.</p>" for n in (1, 2, 3))), encoding="utf-8")
        rr = render(extra, "--out", str(cwd / "pages" / "s2-captions"))
        if rr is not None:
            assert rr.returncode == 0 and "text overlaps text" not in rr.stdout, "three added paragraphs stack on the minimal page: " + rr.stdout
        # with a real palette.css next to the page the page renders and loads every file it asks for
        pal = [sys.executable, str(SKILL / "scripts" / "palette.py"), "--register", g2["register"], "--harmony", g2["harmony"], "--arc", g2["arc"], "--pages", str(len(g2["layout_rhythm"])), "--ground", g2["ground"], "--out", str(cwd)]
        if isinstance(g2.get("field_page"), int):
            pal += ["--field-page", str(g2["field_page"])]
        subprocess.run(pal, capture_output=True, text=True)
        assert (cwd / "palette.css").is_file()
        run(cwd, "scaffold", "s2", "--force")
        html = (cwd / "visual.html").read_text(encoding="utf-8")
        assert any(u.endswith("palette.css") for u in links(html)), "palette.css was not linked"
        rr = render(cwd / "visual.html")
        if rr is None:
            print("SKIP render of the scaffolded minimal page: node or Playwright is not installed")
        else:
            assert "did not load" not in rr.stdout and "not loaded or installed" not in rr.stdout, "the minimal page asks for a file or font it does not get: " + rr.stdout
            assert (cwd / "page-01.png").is_file() and (cwd / "audit.json").is_file(), "render --audit must write page-NN.png and audit.json"
        (cwd / "palette.css").unlink()
        # G1-5: a slide is 1920x1080 and never starts from a 1080x1350 specimen (ledger has one): it gets the minimal 16:9 page
        design_piece(cwd, "s3", "the month end close drawn as a relay race baton", "direction=ledger,type=heavy-display", notes, medium="slide")
        r = run(cwd, "scaffold", "s3", "--out", str(cwd / "pages" / "s3.html"))
        html = (cwd / "pages" / "s3.html").read_text(encoding="utf-8")
        assert "1920px" in html and "1080px" in html and "section.page" in html, "slide size missing"
        assert 'class="page mn wide pg-1"' in html and "slide-16x9" in html and "1920x1080" in r.stdout and "16:9" in r.stdout, "the slide is not the minimal 16:9 page, or the output does not say so: " + r.stdout
        assert "specimen ledger" not in r.stdout and ".lg h1" not in html and "1350" not in html, "a portrait specimen leaked into the slide"
        assert "--size 1920x1080" in r.stdout, r.stdout
        assert_links_work(html)
        rr = render(cwd / "pages" / "s3.html", "--size", "1920x1080")
        if rr is None:
            print("SKIP render of the scaffolded slide: node or Playwright is not installed")
        else:
            assert rr.returncode == 0, "the scaffolded 16:9 slide fails its own audit: " + rr.stdout
        assert "without --audit" not in r.stdout and "page-NN.png" in r.stdout, "the scaffold's next line is stale: " + r.stdout
        # a direction whose idea is the house type's width axis keeps it; a specimen that sets only a background still has readable placeholder pages
        design_piece(cwd, "s5", "a launch note as one oversize word", "direction=type-only,type=bookish", notes)
        r = run(cwd, "scaffold", "s5", "--out", str(cwd / "pages" / "s5.html"))
        html = (cwd / "pages" / "s5.html").read_text(encoding="utf-8")
        assert "keeps it" in r.stdout and "Libre Baskerville" not in html and "library.css" not in html, "type-only must keep the house type: " + r.stdout
        design_piece(cwd, "s4", "a glossary entry as a library card", "direction=index-card,type=house", notes)
        run(cwd, "scaffold", "s4", "--out", str(cwd / "pages" / "s4.html"))
        rr = render(cwd / "pages" / "s4.html")
        if rr is not None:
            assert rr.returncode == 0, "the scaffolded index-card carousel fails its own audit: " + rr.stdout
        print("PASS scaffold: absolute links that exist (specimen and minimal page), one section per page, hook marked, palette.css roles and the dealt type used by the minimal page, library linked, no overwrite without --force, slide = minimal 16:9 page that renders")
        # K7: a format that names a lead layout keeps it on its page; field_page says where the colour field comes
        design_piece(cwd, "k7", "one number carried through a whole week of approvals", "format=c-one-number", notes)
        seen = set()
        for seed in range(1, 25):
            run(cwd, "deal", "k7", "genome", "--seed", str(seed))
            g = piece_json(cwd, "k7")["genome"]
            lay = g["layout_rhythm"]
            assert g["format"] == "c-one-number" and lay[0] == "number" and lay.count("number") == 1, f"the number layout is not pinned to page 1: {lay}"
            assert lay.count("field") <= 1 and all(x != y for x, y in zip(lay, lay[1:])), lay
            assert g["field_page"] == (lay.index("field") + 1 if "field" in lay else "none"), g
            ws = (cwd / ".atelier" / "pieces" / "k7" / "04-genome.md").read_text(encoding="utf-8")
            assert f"- field_page: {g['field_page']}" in ws, "field_page is not printed in the genome"
            assert ("--field-page" in ws) == isinstance(g["field_page"], int) and (not isinstance(g["field_page"], int) or f"--field-page {g['field_page']}" in ws), "the palette line disagrees with field_page"
            seen.add(type(g["field_page"]).__name__)
        assert seen == {"int", "str"}, f"expected both a field page and none across 24 deals: {seen}"
        print("PASS c-one-number pins the number layout to page 1; field_page printed in the genome and passed to the palette line")
        # K8: the quick scope is four stages and one critic file
        run(cwd, "new", "q1", "--topic", "one invoice line that costs a day", "--scope", "quick", "--medium", "image")
        qdir = cwd / ".atelier" / "pieces" / "q1"
        assert [s for s, v in piece_json(cwd, "q1")["stages"].items() if v["status"] == "skipped"] == ["lenses", "sections", "copy", "final"]
        assert sorted(f.name for f in qdir.glob("*.md")) == ["01-atoms.md", "07-visual.md"] and "3 to 5 atoms" in (qdir / "01-atoms.md").read_text(encoding="utf-8")
        r = run(cwd, "deal", "q1", "lenses", ok=False)
        assert r.returncode != 0 and "not part of" in (r.stdout + r.stderr), "a skipped stage was dealt"
        # G1-7: a quick piece is graded against quick anchors (3 to 5 atoms), a full piece against the full ones
        qat = (qdir / "01-atoms.md").read_text(encoding="utf-8")
        fat = (cwd / ".atelier" / "pieces" / "a" / "01-atoms.md").read_text(encoding="utf-8")
        assert "5 atoms across 4 types" in qat and "10 to 12" not in qat and "8 to 12" not in qat, "the quick atoms worksheet does not use the quick coverage anchors: " + qat
        assert "10 to 12 specific atoms across all types" in fat and "5 atoms across 4 types" not in fat, "the full atoms worksheet lost its anchors"
        # G1-10: next prints the fill instruction and the exact grade command, not "grade it"
        nx = run(cwd, "next", "q1").stdout
        assert nx.startswith("atoms: fill ") and 'grade q1 atoms --scores "coverage=,specificity=,sourced=,surprise=" --notes <notes.md> --by self' in nx, nx
        assert 'grade q1b atoms --scores "coverage=,specificity=,sourced=,surprise="' in run(cwd, "new", "q1b", "--topic", "one invoice line that costs a day", "--scope", "quick", "--medium", "image").stdout, "new does not print the grade command"
        assert "PASSED" in grade(cwd, "q1", "atoms", 9, notes).stdout
        assert "angles: deal it" in run(cwd, "next", "q1").stdout
        run(cwd, "deal", "q1", "angles")
        assert len(piece_json(cwd, "q1")["stages"]["angles"]["deals"][-1]) <= 3, "quick scope deals three operators at most"
        # G1-3: quick scope picks ONE dealt operator and writes ONE angle; full scope writes one angle for EACH dealt operator
        qaw = (qdir / "03-angles.md").read_text(encoding="utf-8")
        faw = (cwd / ".atelier" / "pieces" / "a" / "03-angles.md").read_text(encoding="utf-8")
        for text, words in ((qaw, "operators are dealt below. Pick the ONE"), (faw, "operators are dealt below. Write ONE candidate angle for EACH")):
            n_rows = len(re.findall(r"^\d+\. \*\*", text, re.M))
            assert re.search(rf"(Quick|Full) scope: {n_rows} {words}", text), f"the angles worksheet count disagrees with its rows ({n_rows}): {text}"
        assert "lens to use" not in qaw and "lens to use" in faw and "for EACH" not in qaw and "Pick the ONE" not in faw, "quick and full angle instructions are mixed up"
        qa = notes / "q-angles.md"
        qa.write_text("\n".join(f"{c}: because the candidate quotes a sourced number on line 2" for c in CRIT["angles"].split()))
        r = run(cwd, "grade", "q1", "angles", "--scores", "novelty=9,truth=9,relevance=9,intrigue=9,tone=9", "--notes", str(qa), "--by", "self")
        assert "PASSED" in r.stdout, "quick scope must let the author grade the angle: " + r.stdout + r.stderr
        run(cwd, "choose", "q1", "angle", "1", "--text", "four euros held up a whole day")
        run(cwd, "deal", "q1", "genome")
        assert "- lens: none (quick scope)" in (qdir / "04-genome.md").read_text(encoding="utf-8") and "(host angle)" not in (qdir / "04-genome.md").read_text(encoding="utf-8"), "R3a-7: quick scope has no lens"
        assert "PASSED" in grade(cwd, "q1", "genome", 9, notes).stdout
        nx = run(cwd, "next", "q1").stdout
        assert nx.startswith("visual:") and (SKILL / "scripts" / "compose.py").as_posix() in nx and "scaffold q1" in nx, nx
        vws = (qdir / "07-visual.md").read_text(encoding="utf-8")
        assert "--by critic --evidence" in vws and (SKILL / "scripts" / "render.mjs").as_posix() in vws, vws
        run(cwd, "scaffold", "q1", "--out", str(cwd / "pages" / "q1.html"))
        vn = notes / "q-visual.md"
        vn.write_text("\n".join(f"{c}: because the page shows one number as the largest type on the cover" for c in CRIT["visual"].split()))
        vscores = ",".join(f"{c}=9" for c in CRIT["visual"].split())
        r = run(cwd, "grade", "q1", "visual", "--scores", vscores, "--notes", str(vn), "--by", "critic", ok=False)
        assert r.returncode != 0 and "--evidence" in (r.stdout + r.stderr), "the quick visual passed without the critic's file: " + r.stdout + r.stderr
        r = run(cwd, "deliver", "q1", ok=False)
        assert r.returncode != 0 and "visual" in (r.stdout + r.stderr), "a quick piece was delivered before its visual passed"
        qv = verdict(notes / "q1-visual-critic.md", "visual", 9, slug="q1")
        fresh_render(cwd / "pages", "q1.html")
        r = run(cwd, "grade", "q1", "visual", "--scores", vscores, "--notes", str(vn), "--by", "critic", "--evidence", str(qv))
        assert "PASSED" in r.stdout, r.stdout
        nx = run(cwd, "next", "q1").stdout
        assert "Quick stages passed" in nx and "deliver q1" in nx and (SKILL / "scripts" / "compose.py").as_posix() in nx, nx
        run(cwd, "deliver", "q1")
        last = json.loads((cwd / ".atelier" / "history.jsonl").read_text().splitlines()[-1])
        assert last["scope"] == "quick" and last["slug"] == "q1" and set(last["scores"]) == {"atoms", "angles", "genome", "visual"}, last
        assert set(last["evidence"]) == {"visual"} and last["evidence"]["visual"]["sha256"] == hashlib.sha256(qv.read_bytes()).hexdigest(), last["evidence"]
        assert run(cwd, "coverage").stdout.startswith("4 pieces in memory"), "the quick piece is not counted in the diversity memory"
        assert last["genome"].get("format") and last["genome"].get("direction"), "a quick piece must enter the diversity memory with its genome"
        print("PASS quick scope: four stages, the angle graded by its author, the visual refused without the critic's file, delivered with one evidence file and scope=quick in memory")
    # every other test in a project of its own (own_project): no test deals into a memory another test filled
    for test in (guard_tests, evidence_tests, slug_tests, genome_tests, rules_tests, r4_tests, r7_tests, r9_tests, r9_render_tests,
                 palette_sweep_tests, r10_tests, r11_tests, r12_tests, r13_tests, faint_twin_tests, r13_next_tests, next_lines_tests, attention_role_tests):
        with own_project(test.__name__) as cwd:
            notes = cwd / "notes"
            notes.mkdir()
            test(cwd, notes) if test.__code__.co_argcount == 2 else test(cwd)
    return 0


if __name__ == "__main__":
    sys.exit(main())
