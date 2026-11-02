# Contributing

Atelier's rule for itself is the rule it gives designers: evidence before claims.

## What a change needs
- **A new art direction** needs a cover specimen in [plugins/mansions/skills/atelier/assets/directions/](plugins/mansions/skills/atelier/assets/directions/) built on `tokens.css`, a row in [references/directions.md](plugins/mansions/skills/atelier/references/directions.md) and in `data/directions.json`, and a clean `render.mjs --audit`. It must borrow a real form that carries information (a ledger, a board, a card), and pass the swap test.
- **A new check** needs a planted flaw it catches, added to the planted-flaw list below with the exit code it expects, and must not fail any current specimen.
- **A third-party tool** comes in only through [docs/INTAKE.md](docs/INTAKE.md): vetted before anything runs, licence checked, only small pure code copied with a header line, each file listed in the tool's own section of vendor/MANIFEST.md with its commit and git blob hash, and credited in CREDITS.md. Step 6 of docs/INTAKE.md lists every file a new tool touches; no test or script is edited, because tests/test_motion.py checks every tool section against its own folder and commit.
- **A change to a critic agent or to references/critique.md** needs a passing calibration on `evals/anchors` (`scripts/calibrate.py`), with the result appended to `evals/anchors/calibration-log.csv`. Keep the verdict file with the change. Never edit `labels.json` to make a run pass.
- **Facts and research** in `references/science.md` need a source and a strength grade; a failed replication is said plainly.
- Keep `SKILL.md` short; detail goes in references, loaded only when needed.
- No third-party prompts, code, images or music without a licence that allows it, credited in [CREDITS.md](CREDITS.md).
- **LICENSE and CREDITS.md exist twice**: at the repository root and in `plugins/mansions/skills/atelier`, so a plugin install and the claude.ai zip carry them. Change both, and keep the copies identical to the root files (step 8 below checks it).
- No em dash or en dash in any file you write. Vendored files keep their upstream text, the planted fixture `evals/anchors/src/bad-template-chrome.html` holds one on purpose, and `plugins/mansions/skills/humanizer/SKILL.md` shows both dashes as examples of what to remove.

## Run the checks locally
Run everything from the repository root in bash (Git Bash on Windows). You need Node 20 or newer (Playwright 1.63.0 stops below 20), Python 3.10 or newer, ffmpeg and Claude Code. Every render below writes to a temp folder with `--out`, never next to the file it checks, so the committed example pages stay as they are.

One-time setup:
```
npm i -D playwright@1.63.0
npx playwright install chromium
python3 -m venv .venv                  # Windows: python -m venv .venv
. .venv/bin/activate                   # Git Bash on Windows: . .venv/Scripts/activate
pip install -U "pillow>=10.3" playwright==1.63.0
```
The packages go into the virtual environment, not the system Python, which recent Debian, Ubuntu and Homebrew refuse to change (PEP 668). Activate it again in each new terminal; every `python` below is then its Python.

### The steps CI runs
These follow [.github/workflows/check.yml](.github/workflows/check.yml), without its planted-flaw lines (those are in step 7). Every line must exit 0.
```
S=plugins/mansions/skills/atelier
T=$(mktemp -d)

# 1. The plugin and the marketplace are valid
claude plugin validate .
claude plugin validate ./plugins/mansions

# 2. Every specimen and the worked carousel pass the audit
for f in $S/assets/directions/*.html; do
  case "$f" in
    *.motion.html) continue ;;
    *slide-16x9.html) X="--size 1920x1080" ;;
    *story-9x16.html) X="--size 1080x1920 --safe reels" ;;
    *) X="" ;;
  esac
  node $S/scripts/render.mjs "$f" --audit $X --out "$T/$(basename "$f" .html)"
done
node $S/scripts/render.mjs $S/examples/ledger-carousel/visual.html --audit --out $T/ledger-carousel

# 3. huashu-design's checker agrees with the audit
L="python $S/vendor/huashu-design/scripts/design_lint.py check --min-body 22 --min-label 22"
for f in $S/assets/directions/*.html $S/examples/ledger-carousel/visual.html; do
  case "$f" in
    *.motion.html) continue ;;
    *slide-16x9.html) V=1920x1080 ;;
    *story-9x16.html) V=1080x1920 ;;
    *) V=1080x1350 ;;
  esac
  $L "$f" --viewport $V
done

# 4. The composer and diversity tests
python $S/tests/test_composer.py
python $S/tests/test_diversity.py 20

# 5. Every colour register passes contrast and colour-vision checks
for r in wonder dry craft-pride relief unease-to-control curiosity warmth rigour play; do
  python $S/scripts/palette.py --register $r --harmony analogous --arc dawn --pages 6 --out $T/pal-$r
  for g in dark paper field; do
    for arc in steady cooldown single-flash chapters; do
      python $S/scripts/palette.py --register $r --harmony split --arc $arc --pages 6 --ground $g --out $T/pal-$r-$g > /dev/null
    done
  done
done
python $S/scripts/palette.py --taste white-link-blue --register curiosity --harmony complementary --pages 3 --out $T/pal-taste

# 6. The Python scripts compile
python -m py_compile $S/scripts/*.py $S/vendor/huashu-design/scripts/design_lint.py
```

### 7. The checks catch every planted flaw
CI covers the original planted flaws: in check.yml each negative check is written `if <check>; then exit 1; fi`, so the step fails when a check stops catching its flaw. (A line that starts with `!` would not do this under `bash -e`.) The newer fixtures below are not in CI yet (CI runs test_readcheck.py; test_audio.py, test_slides.py and test_pairwise.py, the last lines, are not in CI), so run this list too. Each line prints `ok` or `MISS` with the exit code it got and the one it expects, and the last line must say `PLANTED miss=0`. The fixtures in `tests/fixtures` and `evals/anchors/src` each hold one planted case.
```
S=plugins/mansions/skills/atelier
F=$S/tests/fixtures
A=$S/evals/anchors/src
T=$(mktemp -d)
miss=0
expect() { want=$1; shift; "$@" > "$T/last.txt" 2>&1; got=$?; if [ "$got" = "$want" ]; then echo "ok    exit $got  $*"; else echo "MISS  exit $got, want $want  $*"; miss=1; fi; }

# The audit (render.mjs --audit exits 1 on a hard fail)
expect 1 node $S/scripts/render.mjs $A/bad-clipped.html --audit --out $T/bad-clipped               # text off the page
expect 1 node $S/scripts/render.mjs $A/bad-overlap.html --audit --out $T/bad-overlap               # text over text
expect 1 node $S/scripts/render.mjs $A/bad-tiny-text.html --audit --out $T/bad-tiny-text           # type under the floor
expect 1 node $S/scripts/render.mjs $F/a1-broken-link/visual.html --audit --out $T/a1-broken-link  # missing stylesheet and logo
expect 1 node $S/scripts/render.mjs $F/a1-svg-scaled/visual.html --audit --out $T/a1-svg-scaled    # SVG text drawn under the floor
expect 1 node $S/scripts/render.mjs $F/g2-css-scaled/visual.html --audit --out $T/g2-css-scaled    # CSS transform draws text under the floor
expect 0 node $S/scripts/render.mjs $F/a1-ring-over-label/visual.html --audit --out $T/a1-ring    # a shape over a label only warns
expect 0 node $S/scripts/render.mjs $F/g2-bare-text/visual.html --audit --out $T/g2-bare-text      # contrast is measured where the text is drawn
expect 0 node $S/scripts/render.mjs $F/g2-local-alias/visual.html --audit --out $T/g2-local-alias  # a local() font alias is not a fallback font
expect 1 node $S/scripts/render.mjs $F/r10-rule-through/visual.html --audit --out $T/r10-rule-through  # a table border and a bar run through text
expect 0 node $S/scripts/render.mjs $F/r10-rule-clear/visual.html --audit --out $T/r10-rule-clear      # rules beside text, a label on a rule: no fail

# The words
expect 1 python $S/scripts/copy_lint.py $A/bad-salesy-copy.html                                    # salesy copy

# The first glance (attention.py exits 1 on a FAIL, 2 with no page PNGs)
for n in logo-vanish a2-big-logo a2-thin-line g3-body-block g3-object-accent; do
  expect 0 node $S/scripts/render.mjs $F/$n/visual.html --audit --out $T/$n
done
expect 1 python $S/scripts/attention.py $T/logo-vanish        # the logo's ink is under 3:1 against its ground
expect 1 python $S/scripts/attention.py $T/a2-big-logo        # the logo leads the cover
expect 0 python $S/scripts/attention.py $T/a2-thin-line       # a thin accent line does not beat a large numeral
expect 0 python $S/scripts/attention.py $T/g3-body-block      # body text is left out of the lead race
expect 0 python $S/scripts/attention.py $T/g3-object-accent   # passes with a note: the accent leads the object by under 1.5 times
mkdir -p $T/empty
expect 2 python $S/scripts/attention.py $T/empty              # no page PNGs

# huashu-design's checker (needs Python Playwright 1.63.0)
L="python $S/vendor/huashu-design/scripts/design_lint.py check --min-body 22 --min-label 22"
expect 1 $L $A/bad-tiny-text.html --viewport 1080x1350                                             # type under the floor
$L $A/bad-template-chrome.html --viewport 1080x1350 > $T/chrome.txt 2>&1
expect 0 grep -q "卡片套件" $T/chrome.txt                                                           # the card-kit template habit

# The palette tests
expect 0 python $S/tests/test_palette.py

# The two warnings from the second 30 Oct run: the audit still exits 0, and the warning is in audit.json
expect 0 node $S/scripts/render.mjs $F/r13-faint-mark/visual.html --audit --out $T/r13-faint-mark
expect 0 grep -q "faint mark:" $T/r13-faint-mark/audit.json        # empty slots under 3:1 against the paper
expect 0 node $S/scripts/render.mjs $F/r13-thin-script/visual.html --audit --out $T/r13-thin-script
expect 0 grep -q "thin stroke:" $T/r13-thin-script/audit.json      # a script hook whose strokes are 1.6 px on a phone

# Drawn films (needs ffmpeg): vendored blob hashes, no spawned installers, a fixed-seed film twice, a still stretch under grain, a blocked request, a page box at a fractional offset
expect 0 python $S/tests/test_motion.py

# The reading-time check (CI runs this too): a planted film with five faults, the rule, captions, a film with no marks
expect 0 python $S/tests/test_readcheck.py

# Films with sound (not in CI): sound.py on a planted film, thirteen planted sound faults, the clipping edge, and timeline.json timing the picture and the audit
expect 0 python $S/tests/test_audio.py

# Slides (not in CI): slide floors scaled to the width, the worked deck, a planted deck with five faults
expect 0 python $S/tests/test_slides.py

# Both orders (not in CI): a preference must survive the swap, and reasons must quote or locate
expect 0 python $S/tests/test_pairwise.py

echo "PLANTED miss=$miss"
```
Two lines expect exit 0 on purpose. `g2-local-alias` declares a page font with `@font-face` whose source is an installed system font (`local()`); the audit must not call that a fallback font. `g3-object-accent` has an accent block a hair ahead of the drawn object on the cover; attention.py compares an accent with the best hook, number or object, so it passes and prints a note instead of a FAIL.

### 8. The licence copies match the root files
```
cmp LICENSE plugins/mansions/skills/atelier/LICENSE
cmp CREDITS.md plugins/mansions/skills/atelier/CREDITS.md
```
Both lines print nothing and exit 0.

Without `--out`, the audit writes PNGs, `audit.json` and `boxes.json` next to each file it checks, and over the committed pages of the worked examples; the workflow does that on a throwaway runner. Before you commit, `git status` must show only the files you meant to change. If the workflow changes, update steps 1 to 6 to match.

## Build the release zips
The two zips for claude.ai are release assets, not files in git. Build them from committed files only, so nothing you rendered locally gets in:
```
mkdir -p dist
git archive --format=zip --prefix=atelier/ -o dist/atelier-skill.zip HEAD:plugins/mansions/skills/atelier -- . ':(exclude)tests' ':(exclude)evals' ':(exclude)examples/*/*.mp4' ':(exclude)examples/*/*.pdf' ':(exclude)examples/*/preview.png' ':(exclude)examples/*/phone.png' ':(exclude)examples/*/contact.png'
git archive --format=zip --prefix=humanizer/ -o dist/humanizer-skill.zip HEAD:plugins/mansions/skills/humanizer
ls -l dist
```
`atelier-skill.zip` holds the skill folder with its LICENSE and CREDITS.md. It leaves out what claude.ai cannot use: `tests/`, `evals/` (calibration needs the critic agents, which the zip does not hold) and the rendered videos, PDFs and contact sheets of the examples (their sources and page PNGs stay). SKILL.md and references still mention `evals/` and `tests/` in passing, as history. Built this way from the branch head on 2 Nov 2026, the zip is about 7.35 MB (the same `git archive` without the excludes gives 10.73 MB), and unpacks to about 11.8 MB. Anthropic publishes no size limit for a claude.ai skill zip that we could find: the support article "Use skills in Claude" lists "ZIP file exceeds size limits" as an upload error and gives no figure, and the Skills API guide says "Total upload size must be under 30 MB (uncompressed)" (read 30 Oct 2026). Keep the zip small. Attach both zips to the GitHub release:
```
gh release create v1.2.0 dist/atelier-skill.zip dist/humanizer-skill.zip --title "Atelier 1.2.0" --notes-file CHANGELOG.md
```
Then delete `dist/`. Never commit it.
