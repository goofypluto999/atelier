#!/usr/bin/env python3
"""Tests for drawn films (huashu-art-motion folded into Atelier's video path, round 13). python tests/test_motion.py

1. For every tool section in vendor/MANIFEST.md (its Folder, Commit and Licence line and its file table), the files in that folder match
   the recorded git blob hashes, each copied file names the commit and licence, and the folder holds no unlisted file.
2. No code in the skill spawns uv, uvx, npx or pip, or carries an inline dependency block (PEP 723), and the scan covers every code
   file a MANIFEST table lists and assets/lib/art-motion.js. The pattern is first shown to catch planted examples.
   A fake second tool, registered in a temp copy as docs/INTAKE.md says, passes checks 1 and 2 with no edit here, and they still
   catch a changed byte, an unlisted file and a spawned installer in it.
3. A fixed-seed film (tests/fixtures/r13-art-motion) rendered twice by motion.mjs gives the same frames, and at fixed times
   the page's colours and the camera are where they should be.
4. Under a film finish, whose grain changes every frame, video_check.py still fails a still stretch as a dead beat.
5. motion.mjs refuses a page that asks for a file that is not local.
6. render.mjs --audit checks a film past its first frame: the hard rules again every half second and at the poster time
   (tests/fixtures/r14-late-fault breaks two rules after 2 s), with the length from --seconds or from ART.film.
7. A drawn object marked with an element that follows it leads the film's poster in attention.py; unmarked, it fails as decoration.
8. A page box that starts between two pixel rows (tests/fixtures/r16-odd-offset) renders at the box's own size, 360x450.
Rendering needs node, Playwright and ffmpeg; without them checks 3 to 8 print SKIP and the test passes."""
import hashlib
import json
import pathlib
import re
import shutil
import subprocess
import sys
import tempfile

SKILL = pathlib.Path(__file__).resolve().parent.parent
VENDOR = SKILL / "vendor" / "huashu-art-motion"
LIBS = ["util", "motion", "camera", "palettes", "finish"]


def blob(path):
    """git's blob hash of a file's bytes (what `git hash-object` prints)."""
    data = path.read_bytes()
    return hashlib.sha1(b"blob %d\0" % len(data) + data).hexdigest()


# A tool that joins by docs/INTAKE.md has its own section in vendor/MANIFEST.md: a "## <tool>" heading, one line naming its folder,
# commit and licence, and a table with one row per copied file. These checks read every such section, so a new tool needs no test edit.
TOOL_LINE = re.compile(r"^Folder: `([^`]+?)/`\. Commit: ([0-9a-f]{7,40}) \(([0-9a-f]{40})\)\. Licence: ([A-Za-z0-9.+-]+), `([^`]+)`\.\s*$", re.M)
FILE_ROW = re.compile(r"^\| `([^`]+)` \| `[^`]+` \| ([0-9a-f]{40}) \| ([0-9a-f]{40}) \| ([^|\n]+) \|\s*$", re.M)
NO_HEADER = "none (no header)"


def manifest_tools(vendor):
    """Every per-tool section of <vendor>/MANIFEST.md as {tool, folder, short, commit, licence, licence_file, rows}; rows are
    (file, upstream blob, vendored blob, lines changed). A section with a file table and no Folder line (or the reverse) fails."""
    tools = []
    for sec in re.split(r"(?m)^## ", (vendor / "MANIFEST.md").read_text(encoding="utf-8"))[1:]:
        name, head, rows = sec.split("\n", 1)[0].strip(), TOOL_LINE.search(sec), FILE_ROW.findall(sec)
        if not head and not rows:
            continue
        assert head, f"vendor/MANIFEST.md, section {name}: a file table without the line 'Folder: `<folder>/`. Commit: <short> (<full sha>). Licence: <id>, `<licence file>`.'"
        assert rows, f"vendor/MANIFEST.md, section {name}: no file rows with blob hashes under its Folder line"
        folder, short, commit, licence, lic_file = head.groups()
        assert commit.startswith(short), f"vendor/MANIFEST.md, section {name}: commit {short} is not the start of {commit}"
        tools.append({"tool": name, "folder": folder, "short": short, "commit": commit, "licence": licence, "licence_file": lic_file,
                      "rows": [(f, up, want, changed.strip()) for f, up, want, changed in rows]})
    return tools


def files_in(folder):
    """The files a vendor folder holds: .gitattributes and Python's __pycache__ aside."""
    return {p.relative_to(folder).as_posix() for p in folder.rglob("*") if p.is_file() and p.name != ".gitattributes" and "__pycache__" not in p.parts}


def credited(credits, name, short):
    """INTAKE step 6 item 3: CREDITS.md has a table row whose first cell names the tool and which carries a credit line in the form
    "<what> adapted from <repo> by <author>, commit <short sha>", and the "Vendored files" sentence names the tool."""
    word = re.compile(rf"(?<![\w-]){re.escape(name)}(?![\w-])")
    form = re.compile(rf"adapted from [^|;]+? by [^|;,]+, commit {re.escape(short)}\b")
    rows = [l for l in credits.splitlines() if l.startswith("| ") and word.search(l.split("|")[1])]
    return any(form.search(l) for l in rows) and any(l.startswith("Vendored files") and word.search(l) for l in credits.splitlines())


def check_vendor(vendor):
    """For each tool in <vendor>/MANIFEST.md, in its own folder: every listed file exists and has the recorded blob hash, its licence file is
    listed, every copied file (all but those marked "(no header)") starts with a header line naming the tool's commit and licence, the folder
    holds no unlisted file, a .gitattributes keeps its bytes (* -text), and the skill's CREDITS.md credits the tool. Every file under vendor/
    belongs to a tool. Returns the tools."""
    vendor = vendor.resolve()
    tools = manifest_tools(vendor)
    assert tools, f"{vendor / 'MANIFEST.md'} has no per-tool section"
    credits = (vendor.parent / "CREDITS.md").read_text(encoding="utf-8")
    for t in tools:
        folder = (vendor / t["folder"]).resolve()   # a section may name a folder outside vendor/, such as ../../humanizer
        listed = {name for name, *_ in t["rows"]}
        assert t["licence_file"] in listed, f"{t['tool']}: the licence file {t['licence_file']} is not listed in its table"
        for name, _, want, changed in t["rows"]:
            f = folder / name
            assert f.is_file(), f"{t['tool']}: {f} is listed in MANIFEST.md and missing"
            assert blob(f) == want, f"{t['tool']}: {name}: blob {blob(f)}, MANIFEST.md records {want}"
            if "(no header)" not in changed:
                head = f.read_bytes().split(b"\n", 1)[0].decode("utf-8", "replace")
                assert f"commit {t['short']}" in head and t["licence"] in head, f"{t['tool']}: {name}: the header line does not name commit {t['short']} and {t['licence']}: {head[:90]}"
        assert files_in(folder) == listed, f"{t['tool']}: files in {t['folder']}/ not listed in MANIFEST.md: {sorted(files_in(folder) - listed)}"
        keeps = [folder / ".gitattributes"] + [d / ".gitattributes" for d in folder.parents if d == vendor or vendor in d.parents]
        assert any(a.is_file() and "* -text" in a.read_text(encoding="utf-8") for a in keeps), f"{t['tool']}: no .gitattributes with '* -text' keeps {t['folder']}/ byte for byte"
        assert credited(credits, t["folder"].split("/")[-1], t["short"]), (f"{t['tool']}: CREDITS.md has no row for it with a credit line '<what> adapted from <repo> by "
                                                                         f"<author>, commit {t['short']}', or the 'Vendored files' sentence does not name it (INTAKE step 6, item 3)")
    owned = {f"{t['folder']}/{name}" for t in tools for name, *_ in t["rows"]}
    stray = sorted(files_in(vendor) - owned - {"MANIFEST.md"})
    assert not stray, f"files under vendor/ that no MANIFEST section lists: {stray}"
    return tools


def test_hashes():
    tools = check_vendor(SKILL / "vendor")
    each = ", ".join("%s at %s, %d files" % (t["tool"], t["short"], len(t["rows"])) for t in tools)
    print(f"PASS hashes: {len(tools)} tool(s) in vendor/MANIFEST.md ({each}); each file matches its recorded blob hash in the tool's own folder, "
          "each copied file names the commit and licence, and no folder holds an unlisted file")


CALL = re.compile(r"\b(spawn|spawnSync|exec|execSync|execFile|execFileSync|fork|Popen|subprocess\.\w+|os\.system|os\.popen)\s*\(")
TOOL = re.compile(r"""(["'`]\s*|\[\s*["'])(uv|uvx|npx|pip|pip3)\b|["']-m["']\s*,\s*["']pip["']""")
PEP723 = re.compile(r"(?m)^#\s*///\s*script\b")


def spawns(text):
    """Lines that start uv, uvx, npx or pip as a process, and inline dependency blocks."""
    hits = [line.strip()[:90] for line in text.splitlines() if CALL.search(line) and TOOL.search(line[CALL.search(line).start():])]
    return hits + (["# /// script (inline dependency block)"] if PEP723.search(text) else [])


CODE = {".py", ".mjs", ".js", ".cjs", ".sh"}


def scan_spawns(root):
    """The code files under root (fixtures and this file aside) and the ones that spawn an installer. Every code file a tool's MANIFEST table
    lists must be among those scanned, so a new tool's code is covered with no edit here. Returns (files, needed, hits)."""
    files = [p for p in root.rglob("*") if p.suffix in CODE and "fixtures" not in p.parts and p.name != "test_motion.py"]
    need = [root / "vendor" / t["folder"] / name for t in manifest_tools(root / "vendor") for name, *_ in t["rows"] if pathlib.PurePath(name).suffix in CODE]
    need += [p for p in [root / "assets" / "lib" / "art-motion.js"] if p.exists()]
    missing = [p.relative_to(root).as_posix() for p in need if p not in files]
    assert not missing, f"the scan does not cover {missing}"
    return files, need, {p.relative_to(root).as_posix(): h for p in files if (h := spawns(p.read_text(encoding="utf-8", errors="replace")))}


def test_no_spawn():
    planted = ['subprocess.run(["uv", "run", "qa.py"])', 'spawn("npx", ["hyperframes", "render"])', "execFileSync('pip', ['install', 'x'])",
               'subprocess.check_call([sys.executable, "-m", "pip", "install", "pillow"])', "# /// script\n# dependencies = []\n# ///"]
    assert all(spawns(p) for p in planted), [p for p in planted if not spawns(p)]
    clean = ['spawn("ffmpeg", ["-y"])', 'console.error("In your project run: npm i -D playwright && npx playwright install")', "subprocess.run([sys.executable, str(script)])"]
    assert not any(spawns(c) for c in clean), [c for c in clean if spawns(c)]
    files, need, hits = scan_spawns(SKILL)
    assert not hits, f"code that starts uv, npx or pip, or carries an inline dependency block: {hits}"
    print(f"PASS no spawn: {len(files)} code files in the skill (the {len(need) - 1} vendored code files MANIFEST.md lists and art-motion.js among them) start no uv, uvx, npx or pip and carry no PEP 723 block; the pattern catches 5 of 5 planted examples")


def test_second_tool(tmp):
    """docs/INTAKE.md step 6: a second tool registered as documented (its folder with a licence file and a copied file with a header line, and a
    MANIFEST section) passes the vendor checks and the spawn scan with no edit to this file or any script; a changed byte, an unlisted file
    and a spawned installer in it still fail."""
    root = tmp / "second-tool"
    shutil.copytree(SKILL / "vendor", root / "vendor")
    shutil.copytree(SKILL.parent / "humanizer", root.parent / "humanizer")   # MANIFEST's humanizer section names ../../humanizer from vendor/
    fake = root / "vendor" / "fake-tool"
    (fake / "lib").mkdir(parents=True)
    lic, code = fake / "LICENSE-fake-tool.txt", fake / "lib" / "ease.js"
    lic.write_bytes(b"MIT License\n\nCopyright (c) 2026 Example Author\n")
    body = b"const ease = (t) => t * t;\n"
    code.write_bytes(b"// Copied from fake-tool src/ease.js at commit 1234567. MIT, Copyright (c) 2026 Example Author. Licence: ../LICENSE-fake-tool.txt.\n" + body)
    hb = lambda b: hashlib.sha1(b"blob %d\0" % len(b) + b).hexdigest()
    m = root / "vendor" / "MANIFEST.md"
    m.write_text(m.read_text(encoding="utf-8") + "\n## fake-tool\nFolder: `fake-tool/`. Commit: 1234567 (1234567890abcdef1234567890abcdef12345678). Licence: MIT, `LICENSE-fake-tool.txt`.\n\n"
                 "| File | Upstream path | Upstream blob | Vendored blob | Lines changed besides the header |\n|---|---|---|---|---|\n"
                 f"| `LICENSE-fake-tool.txt` | `LICENSE` | {blob(lic)} | {blob(lic)} | {NO_HEADER} |\n"
                 f"| `lib/ease.js` | `src/ease.js` | {hb(body)} | {blob(code)} | 0 |\n", encoding="utf-8")
    (fake / ".gitattributes").write_text("* -text\n", encoding="utf-8")
    credits = root / "CREDITS.md"   # the skill's copy: a row for the tool, and its name in the "Vendored files" sentence
    plain = (SKILL / "CREDITS.md").read_text(encoding="utf-8")
    assert plain.count("| Archivo |") == 1 and plain.count("Vendored files (not just ideas) from ") == 1
    credit = "lib/ease.js adapted from example/fake-tool by Example Author, commit 1234567"
    row = f"| [fake-tool](https://example.invalid/fake-tool) | Example Author | MIT | an easing curve. Vendored: {credit} |\n"
    credits.write_text(plain.replace("| Archivo |", row + "| Archivo |")
                       .replace("Vendored files (not just ideas) from ", "Vendored files (not just ideas) from fake-tool, "), encoding="utf-8")
    tools = check_vendor(root / "vendor")
    assert [t["folder"] for t in tools][-1] == "fake-tool" and len(tools) == len(manifest_tools(SKILL / "vendor")) + 1, [t["tool"] for t in tools]
    files, need, hits = scan_spawns(root)
    assert code in need and code in files and not hits, (need, hits)
    caught, full = [], credits.read_text(encoding="utf-8")
    for label, change, undo in (("a changed byte", lambda: code.write_bytes(code.read_bytes() + b"\n"), lambda: code.write_bytes(code.read_bytes()[:-1])),
                                ("an unlisted file", lambda: (fake / "extra.js").write_text("x\n"), lambda: (fake / "extra.js").unlink()),
                                ("no CREDITS row", lambda: credits.write_text(full.replace(row, ""), encoding="utf-8"),
                                 lambda: credits.write_text(full, encoding="utf-8")),
                                ("a credit line in another form", lambda: credits.write_text(full.replace(credit, "lib/ease.js vendored at commit 1234567"), encoding="utf-8"),
                                 lambda: credits.write_text(full, encoding="utf-8")),
                                ("no .gitattributes", lambda: (fake / ".gitattributes").unlink(), lambda: (fake / ".gitattributes").write_text("* -text\n", encoding="utf-8")),
                                ("a folder with no section", lambda: (root / "vendor" / "stray-tool").mkdir() or (root / "vendor" / "stray-tool" / "x.js").write_text("x\n"),
                                 lambda: shutil.rmtree(root / "vendor" / "stray-tool"))):
        change()
        try:
            check_vendor(root / "vendor")
        except AssertionError as e:
            caught.append(label if ("fake-tool" in str(e) or "stray-tool" in str(e)) else f"{label} (wrong message: {e})")
        undo()
    check_vendor(root / "vendor")
    code.write_bytes(code.read_bytes() + b'spawn("npx", ["fake"]);\n')
    if "vendor/fake-tool/lib/ease.js" in scan_spawns(root)[2]:
        caught.append("a spawned installer")
    want = ["a changed byte", "an unlisted file", "no CREDITS row", "a credit line in another form", "no .gitattributes", "a folder with no section", "a spawned installer"]
    assert caught == want, caught
    print(f"PASS second tool: a fake tool registered as docs/INTAKE.md says (folder, licence, .gitattributes, MANIFEST section, CREDITS row) passes the vendor "
          f"checks for {len(tools)} tools and is covered by the spawn scan, with no test or script edit; {len(want)} of {len(want)} faults are caught: {', '.join(want)}")


def motion(html, out, *extra):
    return subprocess.run(["node", str(SKILL / "scripts" / "motion.mjs"), str(html), "--out", str(out), *extra], capture_output=True, text=True)


def missing(r, name):
    """True, after printing SKIP, when node could not load Playwright (motion.mjs and render.mjs then exit 2 and say so)."""
    if "Playwright not found" in r.stderr:
        print(f"SKIP {name}: Playwright is not installed")
        return True
    return False


def test_render(tmp):
    from PIL import Image
    fx = SKILL / "tests" / "fixtures" / "r13-art-motion" / "motion.html"
    runs = []
    for k in ("a", "b"):
        r = motion(fx, tmp / k, "--seconds", "2", "--fps", "10", "--size", "360x450", "--poster", "1.2")
        if missing(r, "render"):
            return
        assert r.returncode == 0, r.stdout + r.stderr
        files = [tmp / k / n for n in ("frame0.png", "poster.png", "video.mp4")]
        assert all(f.is_file() for f in files), f"motion.mjs --out {tmp / k} wrote {sorted(p.name for p in (tmp / k).glob('*'))}"
        runs.append({f.name: hashlib.sha256(f.read_bytes()).hexdigest() for f in files[:2]})
    assert runs[0] == runs[1], f"the same film rendered twice gave different frames: {runs}"
    probe = subprocess.run(["ffprobe", "-v", "error", "-count_frames", "-select_streams", "v:0", "-show_entries", "stream=nb_read_frames,width,height",
                            "-of", "csv=p=0", str(tmp / "a" / "video.mp4")], capture_output=True, text=True).stdout.strip()
    assert probe == "360,450,20", f"video.mp4 is {probe} (width, height, frames), not 360,450,20"
    ground, ink, accent = (0xE3, 0xD8, 0xD1), (0x32, 0x26, 0x1D), (0x86, 0x44, 0x48)
    near = lambda p, c: sum((a - b) ** 2 for a, b in zip(p, c)) ** 0.5
    nearest = lambda p: min((("ground", ground), ("ink", ink), ("accent", accent)), key=lambda kc: near(p, kc[1]))[0]
    f0 = Image.open(tmp / "a" / "frame0.png").convert("RGB")
    f12 = Image.open(tmp / "a" / "poster.png").convert("RGB")
    want = [(f0, (180, 225), "accent", "t=0: the middle mark is drawn in the page's --accent"),
            (f0, (205, 225), "ground", "t=0: beside the middle mark is the page's --ground"),
            (f0, (120, 225), "ink", "t=0: a side mark is drawn in the page's --text"),
            (f12, (205, 225), "accent", "t=1.2: the camera has pushed in, so the middle mark covers that point"),
            (f0, (40, 40), "ink", "t=0: the HTML square sits above the canvas")]
    got = [(why, nearest(im.getpixel(xy)), im.getpixel(xy)) for im, xy, _, why in want]
    bad = [(why, g, px) for (why, g, px), (_, _, w, _) in zip(got, want) if g != w]
    assert not bad, f"pixels not where the film puts them: {bad}"
    assert f0.getpixel((40, 40)) == ink, f"the HTML square is {f0.getpixel((40, 40))}, not the page's --text {ink}: the canvas or its finish covers the words"
    print(f"PASS render: the fixed-seed film rendered twice gives identical frame0.png and poster.png (sha256 {runs[0]['frame0.png'][:12]}, {runs[0]['poster.png'][:12]}); "
          f"video.mp4 is 360x450 with 20 frames; {len(want)} of {len(want)} pixel checks at t=0 and t=1.2 hold (page colours, camera push, words above the canvas)")


def test_dead_beat(tmp):
    """A film whose mark stops at 1 s and stays still to 5 s under the "film" finish: the grain changes every frame, and video_check.py
    must still name the still stretch a dead beat."""
    from PIL import Image, ImageChops, ImageStat
    libs = "".join(f'<script src="{(VENDOR / "lib" / f"{n}.js").as_uri()}"></script>' for n in LIBS)
    page = tmp / "still" / "motion.html"
    page.parent.mkdir(parents=True)
    page.write_text('<!doctype html><meta charset="utf-8"><style>body{margin:0}.page{position:relative;width:432px;height:540px;overflow:hidden;'
                    '--ground:#e3d8d1;--text:#32261d;--accent:#864448}</style><section class="page"></section>' + libs
                    + f'<script src="{(SKILL / "assets" / "lib" / "art-motion.js").as_uri()}"></script><script>ART.film({{ duration: 5, finish: "film", '
                    'draw(c, t, pal) { c.fillStyle = pal.bg; c.fillRect(0, 0, 432, 540); c.fillStyle = pal.accent; '
                    'c.fillRect(60 + 240 * MO.smooth(MO.seg(t, 0, 1)), 230, 80, 80); } });</script>', encoding="utf-8")
    out = tmp / "still-out"
    r = motion(page, out, "--seconds", "5", "--fps", "15", "--size", "432x540")
    if missing(r, "dead beat"):
        return
    assert r.returncode == 0, r.stdout + r.stderr
    for s in ("2.0", "3.5"):
        subprocess.run(["ffmpeg", "-y", "-v", "error", "-ss", s, "-i", str(out / "video.mp4"), "-frames:v", "1", str(out / f"at-{s}.png")], check=True)
    diff = ImageStat.Stat(ImageChops.difference(Image.open(out / "at-2.0.png").convert("L"), Image.open(out / "at-3.5.png").convert("L"))).mean[0]
    assert diff > 1, f"frames at 2.0 s and 3.5 s differ by {diff:.2f} levels on average: the film finish's grain is not drawn"
    vc = subprocess.run([sys.executable, str(SKILL / "scripts" / "video_check.py"), str(out), "--seconds", "5"], capture_output=True, text=True, encoding="utf-8")
    assert vc.returncode == 1 and "a dead beat" in vc.stdout, vc.stdout
    print(f"PASS dead beat: under the film finish the still stretch changes by {diff:.1f} levels a pixel (grain), and video_check.py still fails it as a dead beat")


def test_blocked(tmp):
    page = tmp / "remote" / "motion.html"
    page.parent.mkdir(parents=True)
    page.write_text('<!doctype html><meta charset="utf-8"><section class="page" style="width:200px;height:200px">'
                    '<img src="https://example.invalid/remote.png" alt=""></section>', encoding="utf-8")
    r = motion(page, tmp / "remote-out", "--seconds", "1", "--fps", "5", "--size", "200x200")
    if missing(r, "blocked"):
        return
    assert r.returncode == 1 and "blocked 1 request" in r.stderr and "example.invalid" in r.stderr, r.stdout + r.stderr
    assert not (tmp / "remote-out" / "video.mp4").exists(), "a blocked film still wrote video.mp4"
    print("PASS blocked: motion.mjs refuses a page that asks for https://example.invalid/remote.png (exit 1, no video.mp4)")


def test_audit_times(tmp):
    """render.mjs --audit checks a motion page past its first frame: every hard rule again every half second and at the poster time. The
    fixture is clean at 0 s, loses its note's contrast from 2.0 to 2.9 s, runs a ticket over the hook from 3.1 to 3.4 s (between two
    half-second checks), and loses its hook's contrast for 0.7 s from 21.2 s (the round 14 score hid such a fault between samples
    taken every ceil(length / 20) seconds)."""
    fx = SKILL / "tests" / "fixtures" / "r14-late-fault" / "motion.html"
    audit = lambda page, out, *extra: subprocess.run(["node", str(SKILL / "scripts" / "render.mjs"), str(page), "--audit", "--no-png", "--out", str(out), *extra],
                                                     capture_output=True, text=True)
    times = lambda out: json.loads((out / "audit.json").read_text(encoding="utf-8"))[0]["times"]
    r = audit(fx, tmp / "late-a")
    if missing(r, "audit times"):
        return
    assert r.returncode == 0 and "unknown length, checked at its first frame only" in r.stdout and times(tmp / "late-a") == [], r.stdout + r.stderr
    r = audit(fx, tmp / "late-b", "--seconds", "4")
    assert r.returncode == 1 and 'FAIL at 2 s: contrast under 3:1: "The other jobs' in r.stdout and "overlaps" not in r.stdout, r.stdout + r.stderr
    assert times(tmp / "late-b") == [0.5, 1, 1.5, 2, 2.5, 3, 3.5], times(tmp / "late-b")   # the poster defaults to 2 s, half of 4, already checked
    r = audit(fx, tmp / "late-c", "--seconds", "4", "--poster", "3.25")
    late = [x for x in r.stdout.splitlines() if x.strip().startswith("FAIL at 3.25 s: text overlaps text") and "Ticket 1038" in x]
    assert r.returncode == 1 and late and 3.25 in times(tmp / "late-c"), r.stdout + r.stderr
    r = audit(fx, tmp / "late-d", "--seconds", "30")
    assert r.returncode == 1 and 'FAIL at 21.5 s: contrast under 3:1: "One job waits' in r.stdout and len(times(tmp / "late-d")) == 59, r.stdout + r.stderr
    art = SKILL / "tests" / "fixtures" / "r13-art-motion" / "motion.html"   # a drawn film: its length comes from ART.film (2 s)
    audit(art, tmp / "late-art", "--size", "360x450")
    assert times(tmp / "late-art") == [0.5, 1, 1.5], times(tmp / "late-art")
    # a page whose seek throws at 1 s: one FAIL line with the time and the message, not a stack trace
    broken = tmp / "throws" / "motion.html"
    broken.parent.mkdir()
    broken.write_text(f'<!doctype html><meta charset="utf-8"><link rel="stylesheet" href="{(SKILL / "assets" / "tokens.css").as_uri()}">'
                      '<section class="page" style="background:var(--paper);color:var(--ink)"><h1 data-role="hook" style="margin:80px;font:700 96px/1 var(--disp)">'
                      'A film that&nbsp;breaks.</h1></section><script>window.seek = (t) => { if (t >= 1) throw new Error("seek broke at " + t + " s"); };</script>', encoding="utf-8")
    r = audit(broken, tmp / "throws-out", "--seconds", "2")
    threw = [x for x in r.stdout.splitlines() if "the page threw" in x]
    assert r.returncode == 1 and threw == ["  FAIL at 1 s: the page threw an error here: Error: seek broke at 1 s (later times not checked: fix it and audit again)"], r.stdout + r.stderr
    assert "    at " not in r.stdout + r.stderr, "a stack trace reached the output: " + r.stderr
    print("PASS audit times: a film clean at 0 s passes when its length is unknown (and the audit says so); with --seconds 4 it is checked every "
          "half second and fails at 2 s, with --poster 3.25 also at 3.25 s, where the ticket covers the hook; a 30 s film fails at 21.5 s on a "
          "0.7 s fault (59 checks); a drawn film's length comes from ART.film; a page that throws at 1 s gets one FAIL line, not a stack trace")


MARKED_FILM = """<!doctype html><meta charset="utf-8"><link rel="stylesheet" href="@TOKENS@">
<style>.page { --ground: #e3d8d1; --text: #32261d; --text-2: #52463d; --accent: #864448; }
.page h1 { position: absolute; left: 80px; right: 80px; top: 80px; font: 650 96px/1.05 var(--disp); color: var(--text); }
.page .mark { position: absolute; }</style>
<section class="page"><h1 data-role="hook">One ticket&nbsp;waits.</h1><div class="mark"@ROLE@></div></section>
@LIBS@<script>
const mark = document.querySelector(".mark"), keys = [{ t: 0, x: 900, y: 400, z: 1 }, { t: 3, x: 540, y: 900, z: 2.5 }];
ART.film({ duration: 4, theme: "page", draw(c, t, pal) {
  const cam = CAM.at(keys, t);
  c.fillStyle = pal.bg; c.fillRect(0, 0, 1080, 1350);
  CAM.with(c, cam, (g) => { g.fillStyle = pal.accent; g.fillRect(440, 800, 200, 200); });
  const [x0, y0] = CAM.toScreen(cam, 440, 800), [x1, y1] = CAM.toScreen(cam, 640, 1000);   // the drawn object's box, where it is this frame
  Object.assign(mark.style, { left: x0 + "px", top: y0 + "px", width: x1 - x0 + "px", height: y1 - y0 + "px" });
} });
</script>"""


def test_poster_object(tmp):
    """references/art-motion.md: a drawn object has no data-role, so mark it with an empty element that follows it (data-role="object",
    placed each frame from CAM.toScreen). The camera ends close on a drawn square; the audit records the boxes at the poster time, and
    attention.py passes the marked film's poster and fails the same film unmarked ("decoration")."""
    libs = "".join(f'<script src="{(VENDOR / "lib" / f"{n}.js").as_uri()}"></script>' for n in LIBS) + f'<script src="{(SKILL / "assets" / "lib" / "art-motion.js").as_uri()}"></script>'
    got = {}
    for name, role in (("marked", ' data-role="object"'), ("unmarked", "")):
        out = tmp / f"poster-{name}"
        out.mkdir()
        page = out / "motion.html"
        page.write_text(MARKED_FILM.replace("@TOKENS@", (SKILL / "assets" / "tokens.css").as_uri()).replace("@LIBS@", libs).replace("@ROLE@", role), encoding="utf-8")
        m = motion(page, out, "--seconds", "4", "--fps", "10", "--poster", "3.5")
        if missing(m, "poster object"):
            return
        assert m.returncode == 0 and (out / "poster.png").is_file(), m.stdout + m.stderr
        a = subprocess.run(["node", str(SKILL / "scripts" / "render.mjs"), str(page), "--audit", "--out", str(out), "--seconds", "4", "--poster", "3.5"], capture_output=True, text=True)
        assert a.returncode == 0, a.stdout + a.stderr
        boxes = {str(p["page"]): p["boxes"] for p in json.loads((out / "boxes.json").read_text(encoding="utf-8"))}
        att = subprocess.run([sys.executable, str(SKILL / "scripts" / "attention.py"), str(out)], capture_output=True, text=True, encoding="utf-8")
        assert "== poster.png" in att.stdout, att.stdout
        got[name] = (boxes, att, att.stdout.split("== poster.png", 1)[1])
    boxes, att, poster = got["marked"]
    first, late = (next(b for b in boxes[k] if b["role"] == "object") for k in ("1", "poster"))
    moved = first["x"] + first["w"] < late["x"] or first["y"] > late["y"] + late["h"]   # the box at 0 s does not touch the box at the poster
    assert moved and late["w"] > 2 * first["w"] and att.returncode == 0 and "FAIL" not in poster, (first, late, att.stdout)
    boxes, att, poster = got["unmarked"]
    assert att.returncode == 1 and "is decoration, not a labelled element" in poster, att.stdout
    print(f"PASS poster object: the drawn square, marked by an element that follows it, is {first['w']} px wide at 0 s and {late['w']} px at the poster (3.5 s), "
          "where the audit records its box; attention.py passes the marked poster and fails the unmarked one as decoration")


def test_odd_offset(tmp):
    """The fixture's page box starts 26.8 px down. An element screenshot rounds it out to 451 rows, which H.264 in yuv420p
    refuses ("ffmpeg 187"); motion.mjs must clip each frame to the box's own 360x450, with the page's ground at every corner."""
    from PIL import Image
    fx = SKILL / "tests" / "fixtures" / "r16-odd-offset" / "motion.html"
    r = motion(fx, tmp / "odd", "--seconds", "1", "--fps", "10", "--size", "360x450")
    if missing(r, "odd offset"):
        return
    err = next((ln.strip() for ln in r.stderr.splitlines() if ln.startswith("Error")), r.stderr.strip()[-300:])
    assert r.returncode == 0, f"a page box at a fractional offset did not render (exit {r.returncode}): {err}"
    probe = subprocess.run(["ffprobe", "-v", "error", "-count_frames", "-select_streams", "v:0", "-show_entries", "stream=nb_read_frames,width,height",
                            "-of", "csv=p=0", str(tmp / "odd" / "video.mp4")], capture_output=True, text=True).stdout.strip()
    assert probe == "360,450,10", f"video.mp4 is {probe} (width, height, frames), not 360,450,10"
    ground = (0xE3, 0xD8, 0xD1)
    for name in ("frame0.png", "poster.png"):
        im = Image.open(tmp / "odd" / name).convert("RGB")
        assert im.size == (360, 450), f"{name} is {im.size[0]}x{im.size[1]}, not the page box's 360x450"
        corners = [im.getpixel(xy) for xy in ((0, 0), (359, 0), (0, 449), (359, 449))]
        assert all(c == ground for c in corners), f"{name} corners are {corners}, not the page's ground {ground}: the frame is not the page box"
    print("PASS odd offset: a page box 26.8 px down renders at its own 360x450 (10 frames, the page's ground at every corner of frame0.png "
          "and poster.png); an element screenshot gave 451 rows and ffmpeg refused them")


def main():
    test_hashes()
    test_no_spawn()
    with tempfile.TemporaryDirectory() as d:
        test_second_tool(pathlib.Path(d))
    if not shutil.which("node") or not shutil.which("ffmpeg"):
        print("SKIP render and blocked: node or ffmpeg is not installed")
        return 0
    with tempfile.TemporaryDirectory() as d:
        tmp = pathlib.Path(d)
        test_render(tmp)
        test_dead_beat(tmp)
        test_blocked(tmp)
        test_audit_times(tmp)
        test_poster_object(tmp)
        test_odd_offset(tmp)
    print("test_motion: PASS")
    return 0


if __name__ == "__main__":
    sys.exit(main())
