# Atelier

Claude designs your social images, carousels, slides and short films, renders them on your machine, and checks them before you post.

[![check](https://github.com/goofypluto999/atelier/actions/workflows/check.yml/badge.svg)](https://github.com/goofypluto999/atelier/actions/workflows/check.yml) [![Licence: MIT](https://img.shields.io/badge/licence-MIT-blue)](LICENSE)

Atelier is a Claude Code plugin. It builds each piece in HTML, renders it to PNG, PDF or MP4, and measures the result with scripts (type size, contrast, overflow, safe zones, reading time, loudness) before a critic agent that did not make it reviews it. It remembers what you made, so the next piece takes a different layout, colour plan and angle, within your brand's hues. For people who publish designed posts on LinkedIn, Instagram and similar feeds.

Made by [The Mansions Agency](https://themansions.agency). A landing page with the films playing is [docs/index.html](docs/index.html): open it in a browser after cloning (on GitHub it shows as source).

![A 12 second film: the seven stages of an Atelier run land one by one on a rail, each on a beat, and PASS lands last](docs/media/the-run.webp)

Made with Atelier: `motion.mjs` rendered the frames, `sound.py` made the sound from the same timeline, and `video_check.py` passed the picture and the sound. A README cannot play a video file, so this is a silent animated WebP; the film with its sound is [docs/media/the-run.mp4](docs/media/the-run.mp4). The bed and the effects are code-made sample sound. Source: [examples/the-run](plugins/mansions/skills/atelier/examples/the-run).

## What it makes

It picks the mode from the ask and the platform ([SKILL.md, "Pick the mode"](plugins/mansions/skills/atelier/SKILL.md)). Each mode has its own sizes, checks and critics.

| Single image | Poster | Carousel | Story |
|---|---|---|---|
| ![A 4:5 post: "Nineteen surgical checks, seven at a time." over three rows of nine slots against a raspberry wall](docs/media/single-image.webp) | ![The editorial-poster direction: one very large number on a full colour field with a short claim](docs/media/poster.webp) | ![Six carousel pages on the hours spent assembling a monthly report](docs/media/carousel.webp) | ![A 9:16 story page with its text clear of the zones where the app draws its controls](docs/media/story.webp) |
| From a real quick-path run: passed the art-director at 7.5 on its second attempt, with a made-up sample brand ([docs/run](docs/run/README.md)). | One claim with its proof: the editorial-poster specimen. Print sizes are not checked. | 6 pages as PNGs and a PDF; audited in CI ([examples/ledger-carousel](plugins/mansions/skills/atelier/examples/ledger-carousel)). | 9:16, text kept out of the platform's UI zones (`--safe reels`). |

| Slides | Motion film | Animation | Film with sound |
|---|---|---|---|
| ![Five 16:9 slides on how Atelier scores, each with a one-line claim, one large number and its source file](docs/media/slides.webp) | ![A dot traces a line chart night by night while a counter rolls, then the peak night is named](docs/media/the-dot-reel.webp) | ![A split-flap departure board settles on three DONE rows and one WAIT](docs/media/departure-board.webp) | ![Seven stages land on a rail, each on a beat, then PASS](docs/media/the-run.webp) |
| 5 slides; every claim cites the file that proves it. Passes the audit and `deck_check.py` ([examples/scoring-deck](plugins/mansions/skills/atelier/examples/scoring-deck)). | 10 s, 9:16; passes `video_check.py` ([examples/the-dot-reel](plugins/mansions/skills/atelier/examples/the-dot-reel), [MP4](docs/media/the-dot-reel.mp4)). | 8 s, drawn by `window.seek(t)` and stepped frame by frame; passes `video_check.py` ([MP4](docs/media/departure-board.mp4)). | 12 s; one `timeline.json` times the picture and the sound ([MP4 with sound](docs/media/the-run.mp4)). |

All content in the examples is sample content, except the scoring deck and the words of the film with sound, which are about Atelier itself. That film's sound is code-made sample sound.

## How it works

It runs like a small studio with a gate at every step: the maker builds, scripts measure, critics who did not build the piece judge it, and memory keeps the next piece from repeating the last. The three diagrams below are pages too: `render.mjs` drew them and its audit passed them, with a word-count warning on each, since a diagram carries more words than a post ([docs/diagrams](docs/diagrams)).

| The run | The team | The scoring |
|---|---|---|
| ![The run: brief, direction, composition, render, script checks, critic agents, revision, memory; revision loops back to render](docs/media/diagram-run.png) | ![The team: the main agent builds, scripts measure, fresh critic agents judge, compose.py gates, .atelier remembers](docs/media/diagram-team.png) | ![The scoring: measured first, six criteria, located findings, both orders, calibrated, TRIBE v2 not used](docs/media/diagram-scoring.png) |

In words:

1. **Atoms.** The topic is broken into atoms: facts, numbers, objects, roles and tensions, each with a source. Ideas start from atoms, not from the headline.
2. **Lenses and play operators.** Three points of view are dealt from 24 lenses (the auditor, the newcomer, the object itself), and up to six play operators from 44 (reverse it, zoom in on one number, borrow a genre), taken from lateral thinking, TRIZ, SCAMPER, bisociation and constrained writing. Each operator turns the atoms into one candidate angle.
3. **The genome.** Every design decision for the piece is dealt together: format (30), art direction (28), register, meaning the feeling (9), hook, close, colour harmony and arc, type pairing, motion and layout rhythm.
4. **Memory.** It is built not to repeat itself: compose.py remembers delivered pieces in your project's `.atelier/` folder and deals the next one away from them. Each value is weighted down by its recent uses, and a new genome must differ from each of the last 10 pieces on a minimum number of axes that rises as memory grows. The same topic twice gets no operator, lens, format or direction it had before ([docs/composer-demo.md](docs/composer-demo.md), [tests/test_composer.py](plugins/mansions/skills/atelier/tests/test_composer.py)). [tests/test_diversity.py](plugins/mansions/skills/atelier/tests/test_diversity.py) simulates 30 pieces by default (20 in CI) and fails if any two within a window of 10 differ on fewer than 3 axes.
5. **Grades.** Eight stages (atoms, lenses, angles, genome, sections, copy, visual, final) each have a rubric and a threshold. A grade needs a reason per criterion. compose.py checks that each reason is 25 characters or more, not that it quotes or locates evidence. Below the threshold the stage is recreated (with a fresh deal where it was dealt) or revised. After 3 graded attempts (2 for the final stage) it goes to a person. The angles, sections, copy, visual and final stages are graded by a critic agent, with its verdict file as evidence (in quick scope, only the visual stage).
6. **Checks.** The scripts measure the rendered pages, not the prompt. Then a critic agent that did not make the piece reviews the PNGs. Three ship with the plugin: `atelier:story-editor` (angles and structure), `atelier:art-director` (the rendered pages) and `atelier:copy-critic` (the words), plus the `humanizer` skill for long copy.

The full pipeline is in [SKILL.md](plugins/mansions/skills/atelier/SKILL.md). The composer is explained in [references/composer.md](plugins/mansions/skills/atelier/references/composer.md).

## Quick start (one image)

You need Claude Code, Node 20 or newer (Playwright 1.63.0 stops below 20) and Python 3.10 or newer (`python3` on macOS and Linux, where the commands below say `python`).

**1. Install the plugin.** In Claude Code:
```
/plugin marketplace add goofypluto999/atelier
/plugin install atelier@mansions
```

**2. Install the render tools** in the project folder where you want the image:
```
# bash or zsh
npm i -D playwright@1.63.0
npx playwright install chromium
# Windows PowerShell: npm and npx start .ps1 files, which its default execution policy stops; the .cmd forms run
npm.cmd i -D playwright@1.63.0
npx.cmd playwright install chromium
```
Then Pillow and the Python Playwright, in a virtual environment: Python on recent Debian, Ubuntu and Homebrew refuses a bare `pip install` into the system Python (PEP 668). The Python Playwright runs huashu-design's checker (`design_lint.py`); at the same version as the Node one, it uses the Chromium you just installed.
```
# bash or zsh
python3 -m venv .venv                  # Git Bash on Windows: python -m venv .venv
. .venv/bin/activate                   # Git Bash on Windows: . .venv/Scripts/activate
pip install -U "pillow>=10.3" playwright==1.63.0
# PowerShell (no Activate.ps1: the default execution policy blocks it)
python -m venv .venv
.venv\Scripts\python -m pip install -U "pillow>=10.3" playwright==1.63.0
```
In bash or zsh, activate it again in each new terminal before you run the scripts. In PowerShell, type `.venv\Scripts\python` where the lines below say `python`; the commands compose.py prints then use that Python too. On Linux, install Chromium's system libraries too, as CI does: `npx playwright install --with-deps chromium`.

**3. Ask Claude:** `Use Atelier to make one image about [your topic]. Use only these facts: [facts, with sources].` Or run `/atelier:atelier`. Claude runs the steps below for you.

Words used here: atoms are sourced facts; an angle is your one-line take; the genome is the dealt design (direction, colours, type, layout); lenses are points of view; play operators are ways to turn facts into an angle; dealt means picked at random, weighted away from what you made before.

**4. Or run the steps yourself.** Set `S` to the skill folder. The plugin cache keeps it under a folder named for the installed version, so these lines take the highest version number (1.10.0 after 1.9.0):
```
# bash or zsh
S=$(ls -d "${CLAUDE_CONFIG_DIR:-$HOME/.claude}"/plugins/cache/mansions/atelier/*/skills/atelier | sort -V | tail -n 1)
# PowerShell
$C = if ($env:CLAUDE_CONFIG_DIR) { $env:CLAUDE_CONFIG_DIR } else { "$HOME/.claude" }
$S = (Get-ChildItem "$C/plugins/cache/mansions/atelier" -Directory | Sort-Object { [version]$_.Name } | Select-Object -Last 1).FullName + "/skills/atelier"
```
Claude Code keeps its plugin cache in its config folder: `~/.claude`, or the folder `CLAUDE_CONFIG_DIR` names when it is set. Both lines above look there first.

If you added the marketplace from a local folder (a clone), Claude Code can load the skill from that clone instead of the cache. Then set `S` to the clone's skill folder: `S="<clone>/plugins/mansions/skills/atelier"` (PowerShell: `$S = "<clone>/plugins/mansions/skills/atelier"`). To be sure, use the folder Claude names as the skill's base directory when it loads Atelier.

Start a piece, then ask for the next step:
```
python "$S/scripts/compose.py" new first-image --topic "your topic" --scope quick --medium image
python "$S/scripts/compose.py" next first-image
```
`next` prints the one next command, with your absolute paths and the Python that ran compose.py, quoted. Each line runs as printed in the shell you ran compose.py from: in PowerShell on Windows it starts with `& `, and in Git Bash (it sets `MSYSTEM`), bash and zsh it does not. Its first answer looks like this (paths shortened to `<project>` and `<S>`, the Python to `python`):
```
atoms: fill <project>/.atelier/pieces/first-image/01-atoms.md. Then grade it (the notes template is at the end of the worksheet):
  python <S>/scripts/compose.py grade first-image atoms --scores "coverage=,specificity=,sourced=,surprise=" --notes <notes.md> --by self
```
The rest of the path, one command per step. Run `next` at any point to see where you are.

1. Write 3 to 5 facts with their sources in `01-atoms.md`, then run the grade line above with your scores and a notes file.
2. `python "$S/scripts/compose.py" deal first-image angles`: pick one of the 3 dealt operators (ways in, such as "ask the sceptic"), write one angle (your one-line take) with it, grade it, then record it with `choose`.
3. `python "$S/scripts/compose.py" deal first-image genome`: grade the dealt design. Then run `next`: it prints the `palette.py` line first. Run that line; it writes `palette.css`, your colour plan.
4. `python "$S/scripts/compose.py" scaffold first-image` (the line `next` prints after that): it writes `visual.html`, a composition start in the dealt direction, type and palette, not a copy of the direction's specimen. Build the direction's device out of your own object; the stock parts to leave out and the logo rules are in [SKILL.md](plugins/mansions/skills/atelier/SKILL.md), quick path step 5. Keep the page to 45 words and the hook to 8.
5. `node "$S/scripts/render.mjs" visual.html --audit`: fix every FAIL it prints, and cut to the word budget it states.
6. `python "$S/scripts/attention.py" .`: fix a FAIL on what the eye sees first.
7. Write the post text that goes out with the image (`post.md`, with every claim on the page in it). Give `page-01.png`, the post text and the slug `first-image` to the `atelier:art-director` agent, save its verdict to a file, and run the visual grade line `next` prints.
8. `python "$S/scripts/compose.py" deliver first-image`: Atelier remembers the piece, so the next one is dealt away from it, and adds its cover to the layout memory.

What each check refuses: [Rules the checks enforce](#rules-the-checks-enforce).


## The design system

**The core belief.** Removing the tells of AI design is not enough: a page with every cliche removed and nothing in its place is empty and polite. Every piece needs a material idea (something that belongs to this subject, made visible), a direction dealt on purpose, and proof that it works, measured on the rendered output.

- **Process.** Sourced facts first, then one angle, then a dealt design. Eight stages each have a rubric and a pass mark ([process.md](plugins/mansions/skills/atelier/references/process.md), [composer.md](plugins/mansions/skills/atelier/references/composer.md), [brief.md](plugins/mansions/skills/atelier/references/brief.md)).
- **Preferences.** One subject and one claim per page; one accent, under 5% of the page; real numbers only, with sources; replace, never just remove ([SKILL.md, "Hard rules"](plugins/mansions/skills/atelier/SKILL.md)).
- **Styles.** Art directions with specimen pages, type pairings, colour plans in OKLCH, and eight film styles ([directions.md](plugins/mansions/skills/atelier/references/directions.md), [type.md](plugins/mansions/skills/atelier/references/type.md), [colour.md](plugins/mansions/skills/atelier/references/colour.md), [film-styles.md](plugins/mansions/skills/atelier/references/film-styles.md)). Seven of the specimen covers:

![Seven of Atelier's bundled cover specimens on dark, paper and ultramarine grounds](docs/hero.png)

- **Review rules.** What the scripts refuse is under [Rules the checks enforce](#rules-the-checks-enforce); what a critic looks for is in [critique.md](plugins/mansions/skills/atelier/references/critique.md) and [tells.md](plugins/mansions/skills/atelier/references/tells.md). Films: [motion.md](plugins/mansions/skills/atelier/references/motion.md), [art-motion.md](plugins/mansions/skills/atelier/references/art-motion.md), [sound.md](plugins/mansions/skills/atelier/references/sound.md). Slides: [slides.md](plugins/mansions/skills/atelier/references/slides.md).

## The scoring, and why

A score from a model is only worth something if the model cannot be flattered and has been tested on known answers.

- **Measured first.** The scripts' results reach the critic as facts. A model that reviewed video alone found 3 of 14 dead stretches; given the measured freeze data it found all 14 (huashu-design, cited in [critique.md](plugins/mansions/skills/atelier/references/critique.md)).
- **The render, not the code.** The art-director agent has two tools, Read and Glob ([art-director.md](plugins/mansions/agents/art-director.md)). It is told to judge the PNGs only, never the HTML or the maker's notes.
- **Six criteria, 1 to 10.** Idea and hook count 1.5 times; the pass mark is 7.5 ([rubrics.json](plugins/mansions/skills/atelier/data/rubrics.json)). A FAIL never passes, and compose.py refuses scores that differ from the critic's verdict file.
- **Both orders.** Model judges favour the first option shown (Zheng et al. 2023, in [science.md](plugins/mansions/skills/atelier/references/science.md)). When a revision competes with an earlier attempt, `pairwise.py` shows the two as 1|2 and then 2|1 to fresh critics; a preference that flips with the order is no winner ([tests/test_pairwise.py](plugins/mansions/skills/atelier/tests/test_pairwise.py)).
- **Located.** Every finding names a page, a place or a quote ([critique.md](plugins/mansions/skills/atelier/references/critique.md)). `pairwise.py` refuses a preference whose reasons do neither.
- **Calibrated.** On 30 Oct 2026 the art-director judged 10 labelled covers blind: 7 of 7 planted flaws caught, 3 of 3 strong covers passed ([calibration-log.csv](plugins/mansions/skills/atelier/evals/anchors/calibration-log.csv)).

**Why not a brain-response score?** Meta's TRIBE v2 predicts brain responses to media, and it is sometimes suggested as a "neuro" score for content. Atelier does not use it. As of October 2026 its licence is non-commercial (CC BY-NC 4.0), and no published test links its predictions to social performance ([science.md, "Not used, and why"](plugins/mansions/skills/atelier/references/science.md)). Atelier uses the evidence such tools try to imitate: studies graded strong, medium or weak, rules measured on the render, a simple attention model it calls a rough guide, and critics tested on known answers.

## Built on

Atelier combines the work of others. Each is credited with its author and licence in [CREDITS.md](CREDITS.md); vendored files are pinned to a commit in [vendor/MANIFEST.md](plugins/mansions/skills/atelier/vendor/MANIFEST.md).

| Project | Author | Licence | What Atelier took |
|---|---|---|---|
| [taste-skill](https://github.com/leonxlnx/taste-skill) | Leonxlnx | MIT | Dealing a direction, the swap test, AI-look tells, critique with caps. Vendored: library data and references |
| [huashu-design](https://github.com/alchaincyf/huashu-design) | alchaincyf | MIT | Layout memory, measured facts for the reviewer, every frame a cover. Vendored: design_lint.py and references |
| [huashu-art-motion](https://github.com/alchaincyf/huashu-art-motion) | alchaincyf | MIT | Drawn films under a camera moved by time. Vendored: five drawing files |
| [lemo-opuscar](https://github.com/lemomo-ai/lemo-opuscar) | LemoLab (lemomo-ai) | MIT | The reading-time idea, rewritten. Vendored: its licence file only |
| [superpowers](https://github.com/obra/superpowers) | Jesse Vincent | MIT | Evidence before claims, independent review. Vendored: three skills |
| [humanizer](https://github.com/blader/humanizer) | blader | MIT | Signs of AI writing; ships as the humanizer skill |
| [brag](https://github.com/latent-spaces/brag) | Shunit Haviv Hakimi (latent-spaces) | MIT (its music, CC BY 4.0, is not used) | Read the real project first; video from a browser and ffmpeg. Vendored: the skill text |
| [Uncodixfy](https://github.com/cyxzdev/Uncodixfy) | cyxzdev | MIT | Fake product chrome and pill overload as tells. Ideas only |
| [awesome-opus5-5-videos](https://github.com/yihui-dev/awesome-opus5-5-videos) | yihui-dev and the creators it lists | MIT for the list | Patterns in motion briefs, paraphrased. No prompt text |
| "How to Build a Motion Design Studio With Opus 5.5" | Ray C. | not stated | The seek(t) render contract, springs, sub-frame blur. Ideas only |
| frontend-design and canvas-design | Anthropic | Apache 2.0 | The clusters generated design falls into. Vendored: the two skill texts |
| Archivo, Instrument Sans, JetBrains Mono | Omnibus-Type, Instrument, JetBrains | SIL OFL 1.1 | The bundled fonts |

The render tools are installed separately and not bundled: Playwright with Chromium, ffmpeg, Python with Pillow, and Node. A third-party tool comes in only through [docs/INTAKE.md](docs/INTAKE.md): vet it without running it, check its licence, copy only small pure code, test it, credit it.

## Limits

- The critic was calibrated on 10 cover images. There is no calibration set for slides, films or sound yet.
- No film has passed a real critic run in the kept evidence: the one drawn film in the worked run failed all three attempts.
- Sound is measured for level, peak, clipping, timing and captions. No critic listens to it. Voice and music are your own licensed files.
- The both-orders comparison is new in 1.4.0 and has no kept run yet.
- `attention.py` is a simple model of the first glance, not a measurement of eyes.
- Posters are checked as screen images; print size, bleed and resolution are not checked.
- Rendering and the checks need Node, Playwright, Python with Pillow, and ffmpeg. Without them the skill gives guidance and critique only.
- Platforms change their sizes, safe zones and loudness. Check their help pages before a launch.

## What one run looks like

One real run on 30 Oct 2026 of the quick path above, on the topic "what a Friday release checklist really needs", in an empty folder with one made-up brand file. Every verdict came from a fresh art-director agent.
Two of three pieces passed, each at exactly the bar of 7.5. With the brand file, the piece failed at 7.2 and passed at 7.5 on its second attempt. Without it, the piece failed at 6.0, 6.5 and 6.3 and went to a person: the critics read its 7-in-10 drawing as a chart any statistic could fill. A third piece, pinned to the warm register, failed at 6.7 and 6.8 and passed at 7.5 on its third attempt.
After each FAIL, `next` named the best attempt so far, its verdict's fixes and its keep line, and the next attempt started from it.
The step log, every verdict, audit, render, post text and piece.json: [docs/run](docs/run/README.md).

A fourth piece, run on 30 and 31 Oct 2026 after drawn films joined the video path, was a 10 s film on the same topic: one ticket of 19 checks on a kitchen rail, cut into tickets of 7, 7 and 5 that are ticked off and stamped. Each verdict came from a fresh Sonnet agent (the model of each call is in its evidence), and each judged the film alive. It failed all three attempts (6.0 with craft capped, 7.0 and 6.7) and went to a person: the last critic found the cut that carries the idea at the film's least readable moment, stamps over a row of checks, and placeholder lines on the tickets. Its verdicts, contact sheets, script output, pages and last video are in [docs/run](docs/run/README.md).

| Start: what scaffold wrote for piece 1 | Piece 1 (PASS 7.5) | Piece 2, best attempt (FAIL 6.5) | Piece 3, warm register (PASS 7.5) |
|---|---|---|---|
| ![The composition start for piece 1 on the brand's pale paper: a sample hook over a dashed box for the object, a line of proof and a source line](docs/run/start.png) | ![Piece 1: "Nineteen surgical checks, seven at a time." over three rows of nine slots, Sign in 7, Time out 7 and Sign out 5 filled, against a raspberry wall marked "One pause holds at most 9"](docs/run/friday-brand.png) | ![Piece 2, second attempt: a ruled table with seven green stations after a stop bar labelled "Friday list" for a change to a live system and three grey ones for everything else, over "Seven in ten outages start with a change."](docs/run/friday-plain.png) | ![Piece 3: the handwritten line "Fifteen deaths in a thousand operations became eight." over two runs of three stops, the WHO checklist's Sign in, Time out and Sign out above and a Friday release's Before the change, At go-live and Before you leave below in madder red](docs/run/friday-warm.png) |

## Rules the checks enforce

- **The audit** (`render.mjs --audit`) writes `page-NN.png` and `audit.json`. It exits 1 on a hard rule:
  - text under 32 px (36 px for condensed faces, 22 px for labelled fine print), measured as drawn after SVG and CSS transforms;
  - contrast under 4.5:1 for text under 48 px (3:1 above), in any CSS colour form (`color-mix()` and relative colours too), judged on the rendered pixels over a gradient, a picture or a drawn film;
  - text off the page or over other text;
  - a rule or border running through text;
  - text set sideways, mirrored, or turned more than 30 degrees (a warning above 10 degrees), judged on the page as loaded; `data-allow="rotate"` marks a deliberate spine label;
  - text in platform UI zones;
  - a hook that is not the biggest type;
  - a broken link, a missing image or a fallback font.

  A film is checked at more than its first frame: every hard rule but the hook rule and the turned-text rule runs again every half second of the film (at 0.5 s, 1 s, 1.5 s and on to its end) and at the poster time. The length comes from `--seconds N` (pass the same `--seconds` and `--poster` as to `motion.mjs`), else from `timeline.json` next to the page, else from `ART.film`, else from the CSS animations. With no known length, only the first frame is checked, and the audit says so.

  It warns, without failing, on:
  - AI-look tells, and shapes painted over text;
  - accent paint over 5% of the page;
  - display type that leaves one word alone on its last line or ends a line on a small word;
  - more than 45 words on a page (it says how many to cut).

  Seven more warnings name what the art-director charged in the 30 Oct 2026 runs. Fix them before a critic sees the page:
  - `phone read`: text under 36 px, or under 40 px in a weight under 500, fine print included (the page line gives the smallest size with fine print);
  - `claim twice`: a line that repeats the hook's words;
  - `wrapped run`: identical marks that wrap and leave a short last row;
  - `hairline accent`: an accent mark drawn under 8 px;
  - `empty cell`: a cell mostly empty beside a full one;
  - `faint mark`: a mark with no text (an empty slot, a dot, an outline) under 3:1 against the ground behind it (WCAG 1.4.11). A small shape in the mark's own colour, such as the line under a dot, or a shape smaller than the mark is not its ground; `data-allow="faint"` marks decoration;
  - `thin stroke`: display type, 48 px or more, whose strokes are under 6 px (2 px on a phone) and under 6.5% of its size, as script, hairline and light faces draw.
- **The first glance** (`attention.py`): page 1 must be led by the hook, the number or the object. A logo, or an element without a `data-role`, never leads (FAIL). An accent may lead by under 1.5 times the best hook, number or object, which prints a note; by more, it fails. Body and fine text are left out of this race. A logo under 3:1 against its ground fails.
- **The critic's scores.** The art-director scores six criteria (idea, hook, hierarchy, craft, colour, distinct; idea and hook weigh 1.5) and ends its verdict with a `verdict:` line and a `scores:` line. With nothing in memory, it judges distinct against the shipped specimens and the clusters in [references/tells.md](plugins/mansions/skills/atelier/references/tells.md). Type the critic's scores into `--scores`; compose.py refuses numbers that differ from the verdict file and recomputes the total. A verdict that says FAIL or REVISE never passes. compose.py checks the verdict's form, scores and binding, not who wrote it.
- **The visual grade is bound to its piece.** The render must be in the folder scaffold wrote the page in, or in a `--folder` that holds this piece's own `visual.html`, with `page-NN.png` and a PASS `audit.json` newer than `visual.html`. A film also needs `video.mp4` and a `video_check.json` from `video_check.py` with no FAIL, for that very video. The verdict's `## <slug>` heading must be this piece's slug, and a verdict file already used by another piece is refused. Every grade records the sha256 of the verdict file; a passing grade also records the sha256 of `visual.html` and every page.
- **Attempts.** A stage goes to a person after 3 graded attempts (2 for the final stage). A FAIL verdict never passes and counts as an attempt. Each visual attempt is kept with its page, renders and verdict in `.atelier/pieces/<slug>/attempts/visual-<n>`, and after a FAIL `next` names the best attempt so far, its verdict's numbered fixes and its `keep:` line: the next attempt starts from that one.
- **Films with sound** (`video_check.py`, when `timeline.json` declares sound): no sound track, a track more than 0.1 s off the picture, loudness more than 1 LU from the target (-14 LUFS, a common target, not a standard), a true peak over -1.0 dBTP, 3 samples in a row at full scale, 1.0 s or more of silence at the start, a voice line without its caption, or a caption shorter than its reading time. Each has a planted film in `tests/test_audio.py`, and the clipping rule also a near-miss (2 samples pass, 3 fail).
- **Slides** (`deck_check.py`): text under 48 px or fine print under 32 px on a 1920 px slide, a slide with no title, a title off the deck's title line, more than three type families, or a PDF whose page count is not the slide count. A planted deck in `tests/test_slides.py` holds each fault.
- **The start page.** For an image or a carousel, `scaffold` writes a composition start (the grid, the dealt type and colours, each page set up for its dealt layout word), never the direction's specimen, and the deal never gives page 1 the specimen's own layout. The genome and visual worksheets list the specimen's stock parts, which must not appear unchanged. Quick scope deals only directions that have a specimen, so there is always a picture of the grammar to read. In full and design scope, a direction without a specimen gives a plain start, and scaffold says so.

## What the scripts check

All scripts are in [plugins/mansions/skills/atelier/scripts](plugins/mansions/skills/atelier/scripts). A check that fails exits non-zero.

| Script | What it does |
|---|---|
| `compose.py new\|next\|deal\|choose\|grade\|adopt\|similar\|status\|scaffold\|deliver\|coverage` | The composer. `next` prints the one next step, with absolute script paths. `<command> --help` explains each command. A slug uses lower case letters, digits, dots, dashes and underscores. `new <slug> --brand <tokens.css>` passes your brand to the palette line. `deal <slug> genome [--pin axis=value]` deals one direction inside the genome, and its worksheet says what the dealt hook and close mean and what to compose. `scaffold <slug> [--out visual.html]` writes a composition start for it, not the direction's specimen. `grade` on a critic-graded stage needs `--evidence <critic verdict file>`: type the critic's scores into `--scores`; compose.py refuses numbers that differ from the verdict file and recomputes the total. `deliver` writes the memory, `.atelier/history.jsonl`, and adds the cover to the layout memory. In design scope (inside another system) it says to deliver only after the host approves. |
| `render.mjs <file> [--audit] [--png] [--pdf] [--video scenes.json] [--no-png] [--out <dir>] [--size WxH] [--safe reels\|story] [--raw-max N] [--seconds N] [--poster T]` | HTML pages to PNG and PDF (with no flag it writes both; `--png` or `--pdf` writes one; `--video` makes an MP4 from a scenes file; `--raw-max` sets how many raw colours a page may keep, default 6). `--audit` also writes the PNGs (`--no-png` skips them) and fails on the hard rules above. It warns, without failing, on AI-look tells, among them fake product chrome (window dots, live dots, NEW or BETA badges), pill tags and too many corner radii, panels nested three deep, and raw colour values outside the tokens. It also warns when the page's `--accent` covers 5% or more of the page (text left out), when display type leaves a word alone or ends a line on a small word, when a page carries more than 45 words, and on the seven warnings above. It fails a rule or border that runs through text. It deletes stale page PNGs above the new page count. |
| `attention.py <folder>` | A simplified Itti, Koch and Niebur saliency model: a prediction of what the eye lands on first, by each element's share of the page. Fails on the first-glance rules above. Exit 2 when the folder has no page PNGs. |
| `palette.py --register <r> --harmony <h> --arc <a> --pages <n> [--ground dark\|paper\|field] [--field-page N]` | The colour plan in OKLCH. Keeps the brand's hues; without `--brand` it makes the piece its own palette from the register, harmony and arc, kept off the specimens' colours. Says when the register overrides the harmony, warns when the colours sit near a cluster that generated design falls into, and checks contrast and colour vision on every page. Writes `palette.css`. `--taste <id>` starts from one of 56 curated palettes. |
| `cvd.py <folder>` | Protan, deutan and tritan simulation. Ends with `cvd: PASS` or `cvd: WARN` (an accent that differs from its ground by hue only). |
| `contact_sheet.py <folder> [--out <file>]` | Every page on one sheet, for the critic. |
| `layout_memory.py check\|add <cover>` | Fails a cover that copies the shape of one of the last 8 (kept in `.atelier/covers`). |
| `motion.mjs <file> --seconds 20 [--sub 2] [--out <dir>]` | Frame-exact MP4 from `window.seek(t)`, with poster, first frame and SRT captions. With a `timeline.json` beside the page, each beat becomes the CSS variable `--beat-<id>` and `window.TIMELINE`, and the film's length comes from it. A drawn film with a camera, springs and a film finish uses `ART.film` from `assets/lib/art-motion.js` ([references/art-motion.md](plugins/mansions/skills/atelier/references/art-motion.md)). The page may load local files only: any other request is blocked and the render fails. Needs ffmpeg. |
| `video_check.py <folder>` | Duration, dead beats (looked for on a quarter-size, blurred copy, so film grain does not hide one), black frames, caption timing, contact and phone sheets. When the folder's `timeline.json` declares sound: a sound track, its length, loudness within 1 LU of -14 LUFS, true peak, clipping, silence at the start, and captions for every voice line. |
| `sound.py <folder>` | The film's sound from the same `timeline.json` that timed its picture: code-made effects on beats (Python standard library) and an optional bed (ffmpeg's `aevalsrc`), your own voice and music files, ducking under the voice, two-pass loudness to -14 LUFS, and captions (JSON, SRT, VTT) from the voice lines. Local only: no network, no model, no voice bundled ([references/sound.md](plugins/mansions/skills/atelier/references/sound.md)). |
| `deck_check.py <folder>` | After `render.mjs --audit --pdf --png --size 1920x1080`: slide floors scaled to the width (48 px, fine print 32 px at 1920), a title on every slide, one title line, three type families or fewer, and the PDF's page count ([references/slides.md](plugins/mansions/skills/atelier/references/slides.md)). |
| `pairwise.py prepare\|judge` | Two renders shown in both orders to fresh critics; a preference counts only if it survives the swap, and only with reasons that quote the page or name a place. |
| `copy_lint.py <file>` | Cringe, preachy, salesy, samey and AI-sounding copy, and flat sentence rhythm. It warns on repeated words. |
| `brand_extract.mjs <url>` | A draft brand file (colours, type, logos, contrast) from a live site. |
| `get_font.py "<Family>"` | An open-licensed Google font with its licence, into your project. |
| `specimens.mjs [id ...]` | Renders page 1 of each direction specimen with the bundled `tokens.css`, and overwrites `assets/directions/specimens/*.png` and `directions.png` in the skill folder (in a plugin install, in the plugin cache). It has no brand option. |
| `calibrate.py prepare\|score` | Tests a critic blind against known answers. |
| [`vendor/huashu-design/scripts/design_lint.py`](plugins/mansions/skills/atelier/vendor/huashu-design/scripts/design_lint.py) `check\|ledger` | huashu-design's checker for template habits and repeated looks. It needs the Python Playwright at the same version as the Node one (`playwright==1.63.0`), which quick start step 2 installs. |

## Use your brand

Copy [assets/brands/TEMPLATE.css](plugins/mansions/skills/atelier/assets/brands/TEMPLATE.css), or start from `brand_extract.mjs <your site>`. Fill in the roles (grounds, text, one accent, faces). Start each piece with `compose.py new <slug> --brand <your file>.css`: the colour plan keeps your hues, and `scaffold` links your file after [tokens.css](plugins/mansions/skills/atelier/assets/tokens.css). If your file declares `--disp`, `--body` or `--mono`, scaffold keeps those faces; the dealt type pairing sets only the ones it leaves out. Without `--brand`, a paper ground is never dealt a serif display face (cream paper with a serif is a look generated design falls into).

The default look is generic: tokens.css holds a neutral palette that belongs to no brand, and the specimens are drawn in it. A piece made without `--brand` does not wear it: `palette.py` makes that piece its own paper, ink and accent from the dealt register, harmony and arc, kept at least 0.04 OKLab (grounds and text) and 0.10 (accents) from the specimens' colours and out of the generated-design colour clusters ([references/colour.md](plugins/mansions/skills/atelier/references/colour.md), "Own palette"). The Mansions Agency palette and logo are an optional theme, [assets/themes/mansions.css](plugins/mansions/skills/atelier/assets/themes/mansions.css): load it after tokens.css, or pass it with `--brand`. The specimens carry an empty logo slot: `scaffold` fills it from your brand file's `--logo` (`--logo-on-dark` on a dark or colour-field ground), or removes it and says why. The Mansions logo is a trademark and not licensed to you: use it only for work by or for The Mansions Agency. If you copy a specimen page by hand, put your own logo in its empty slot.

## Other ways to install

- **Without the plugin system:** copy [plugins/mansions/skills/atelier](plugins/mansions/skills/atelier) to `~/.claude/skills/atelier`, [plugins/mansions/skills/humanizer](plugins/mansions/skills/humanizer) to `~/.claude/skills/humanizer`, and the files in [plugins/mansions/agents](plugins/mansions/agents) to `~/.claude/agents/`. The agents are then named `art-director`, `story-editor` and `copy-critic`, and `S` is `~/.claude/skills/atelier`.
- **Claude.ai or the Claude desktop chat:** download `atelier-skill.zip` and `humanizer-skill.zip` from the [latest release](https://github.com/goofypluto999/atelier/releases/latest). In Claude, go to Customize, Skills, click the + button, then Create skill, then Upload a skill, and pick the zip ([Anthropic's steps](https://support.claude.com/en/articles/12512180-use-skills-in-claude); code execution must be on under Settings, Capabilities). The atelier zip holds the skill folder with its LICENSE and CREDITS.md. It leaves out `tests/`, `evals/` and the rendered videos, PDFs and sheets of the examples, which makes it about 7.35 MB (a zip of the whole folder is 10.73 MB; both built with `git archive` as in [CONTRIBUTING.md](CONTRIBUTING.md), measured 2 Nov 2026). It does not hold the three critic agents, and the rendering and checks need Node, Playwright and Python with Pillow 10.3 or newer on your own machine; without them the skill gives design guidance and critique only.

## What it costs

- **Always in context:** about 366 tokens, the count `claude plugin details` shows for the installed plugin (in Windows PowerShell, `claude.cmd plugin details` when Claude Code came from npm, whose `claude.ps1` the default execution policy stops) (30 Oct 2026). That count is from before 1.4.0, which added 22 characters to the skill's description. The descriptions of the 2 skills and 3 agents are 1,416 characters of the committed files.
- **When the skill loads:** SKILL.md is 20,539 characters, about 5,100 tokens at 4 characters per token, counted on the committed file (`git show HEAD:<path>`, 2 Nov 2026), not on a Windows working copy, whose line ends add a character per line. That is an estimate, not a tokenizer count. The humanizer skill's SKILL.md is 32,309 characters, about 8,100 tokens by the same estimate. References load only when a step needs them.
- **Critic calls:** each graded critic stage is one Sonnet agent call (`model: sonnet` in the three files in [plugins/mansions/agents](plugins/mansions/agents)). A quick image grades only the visual stage, so it takes 1 to 3 calls: one per attempt, and a stage goes to a person after 3. In the full pipeline the angles, sections, copy, visual and final stages each take a critic call.
- No script calls a paid service.

## Are the critics tested?

[evals/anchors](plugins/mansions/skills/atelier/evals/anchors) (10 covers: 3 strong, 7 with one planted flaw) and [evals/angles](plugins/mansions/skills/atelier/evals/angles) (8 angles: 3 strong, 5 flawed) are the calibration sets. The anchors log holds two runs, on 29 and 30 Oct 2026; the angles log holds one, on 29 Oct. The 29 Oct runs came before the art-director and [references/critique.md](plugins/mansions/skills/atelier/references/critique.md) changed on 30 Oct: every flaw caught, every strong item passed. Their verdict files were not kept. Run `calibrate.py` yourself before you trust a critic.

Calibration after the 30 Oct changes: the art-director ran again blind and shuffled on Sonnet on 30 Oct 2026, caught 7 of 7 flawed covers and passed 3 of 3 strong ones. Its verdicts and the answer map are in [evals/anchors/runs/2026-10-30](plugins/mansions/skills/atelier/evals/anchors/runs/2026-10-30).

## Layout
```
.claude-plugin/marketplace.json        the marketplace ("mansions")
plugins/mansions/.claude-plugin/       the plugin manifest ("atelier")
plugins/mansions/agents/               story-editor, art-director, copy-critic
plugins/mansions/skills/humanizer/     the humanizer skill (blader, MIT)
plugins/mansions/skills/atelier/
  SKILL.md                             the quick path, the full pipeline and the hard rules
  LICENSE, CREDITS.md                  copies of the root files, so every install carries them
  references/                          process, brief, directions, composition, type, colour, carousel,
                                       slides, motion, art-motion, film-styles, sound, dataviz, copy, imagery, tells, critique, science,
                                       brand, composer
  scripts/                             the tools above
  data/                                operators, lenses, formats, registers, colour, rubrics, directions,
                                       type pairings, structures (hooks, closes, layout words)
  vendor/                              the source projects' tools and references, pinned and licensed (MANIFEST.md),
                                       among them huashu-art-motion's five drawing files
  tests/                               composer, diversity, palette, motion, reading-time, audio, slides and pairwise tests;
                                       fixtures with planted flaws
  assets/                              tokens.css (neutral), themes/ (optional Mansions theme), brands/, fonts/ (OFL),
                                       lib/motion.js, lib/art-motion.js (drawn films), directions/ (specimens)
  examples/                            ledger-carousel (6 pages), scoring-deck (5 slides), the-dot-reel (9:16),
                                       the-run (4:5, with sound)
  evals/                               anchors and angles: calibration sets with known answers
docs/                                  the landing page (index.html), its media and fonts, the diagrams, the composer demo,
                                       the worked runs (run/) and
                                       the tool-adoption process (INTAKE.md)
.github/workflows/check.yml            CI: validates the plugin, audits every specimen, runs the tests
```
CI fails if the audit, the copy lint, the attention check or design_lint stops catching one of the original planted flaws. CI also runs `tests/test_readcheck.py`, the reading-time check's planted faults. The newer fixtures, `tests/test_palette.py`, `tests/test_motion.py`, `tests/test_audio.py`, `tests/test_slides.py` and `tests/test_pairwise.py` run from the local list in [CONTRIBUTING.md](CONTRIBUTING.md), where each line prints its exit code next to the expected one.

## Contributing and licence

How to run the checks and build the release zips: [CONTRIBUTING.md](CONTRIBUTING.md). Changes: [CHANGELOG.md](CHANGELOG.md).

MIT, see [LICENSE](LICENSE). Fonts: SIL Open Font License 1.1. Vendored files keep their own licences (MIT, Apache 2.0). The Mansions logo is a trademark of The Mansions Agency and is not covered by the MIT licence. The skill folder carries copies of LICENSE and CREDITS.md, so a plugin install and the claude.ai zip keep them.
