# Process: the studio pipeline, and the discipline that keeps it honest

The pipeline in SKILL.md is short on purpose. This file is the detail behind each gate, plus the habits that stop a design agent from fooling itself. The habits are adapted from superpowers (Jesse Vincent, MIT): options before work, evidence before claims, independent review, no agreement for show.

## Why gates
Most weak design is not a lack of skill; it is skipping a step under time pressure: designing before knowing the one idea, polishing a layout that should have been thrown away, declaring it done without looking at it on a phone. Each gate below has an output you can point to. No output, no next step.

| Gate | Output you can point to | Fails when |
|---|---|---|
| 1 Brief | brief.md with the material idea and the swap test | the idea would work for a competitor unchanged |
| 2 Direction | the genome from `compose.py deal <slug> genome`, with one sentence on how the material lives in its direction | the direction was picked by hand, or the sentence would fit any subject |
| 3 Measure | script output with zero FAIL | any FAIL is open |
| 4 Critique | scores, three worst problems, fixes, one keep | quotes or locations are missing; total under the bar after the third attempt |

## Step by step

### 1. Intake (ask once, then decide)
Collect: format and size (references/carousel.md has the platform table), platform and where it will be seen (feed, story, slide deck, print), the audience in one sentence, the single thing to remember, the brand (references/brand.md), the deadline, and any must-use material. If an answer is missing and a sensible default exists, take the default and state it. Ask only what changes the design.

### 2. Material (from brag's "read the project first")
Design starts from the real thing. For a product: open the site or app with Playwright, take real screenshots at the size you need, read the real logo and colours from the page, list them before designing. For a story: collect the real numbers with their source, the real quotes, the real timeline. For a brand: its tokens file. Write `material.md`: what you have, where it came from, what you are not allowed to say.
- Never redraw a product UI from memory. Crop and animate the real one.
- Sample content is allowed only when the user asks for a template or a mock-up; label it "sample" on the design.

### 3. Brief
See references/brief.md. The brief is short and specific. If you cannot write the material idea in one sentence, you are not ready to design.

### 4. Deal the design
Directions are dealt, not defaulted to, so the work does not collapse into one house look (taste-skill's method, MIT). One command does it (S is this skill's folder):
```
python S/scripts/compose.py deal <slug> genome
```
It deals ONE direction for the piece's medium, together with the register, type pairing, colour harmony and arc, hook, close and layout rhythm. Each value is weighted away from the pieces in `.atelier/history.jsonl`, a direction already used for the same topic is excluded, and the whole genome must differ from each of the last 10 pieces on a minimum number of axes that rises as memory grows (references/composer.md). Write one sentence: "On these pages, [material] becomes [the direction's device]." If the direction fights the material, deal again; the next deal excludes this one. If no direction in references/directions.md fits the subject, say so and propose a new one, built by the rules at the end of directions.md.

`.atelier/history.jsonl` is the only piece memory. compose.py writes one line per delivered piece; do not edit it by hand.

### 5. Thumbnails before pages
Before building eight pages, build the cover three to six ways in the dealt direction: different placement of the main mass, different scale relationships, a different ground. Render them small (360 px wide) on one sheet. Choose the one that reads first and strongest. Huashu-design's blind tests found that offering more options beat adding more bans; thumbnails are the cheap way to have options.

### 6. Build and measure
- Pages: one `<section class="page">` per page, sized by CSS (default 1080 x 1350). Start from `python S/scripts/compose.py scaffold <slug> --out visual.html`, which writes the page with absolute links to the tokens, fonts, logos and palette.css: for an image or a carousel a composition start on the grid, each page set up for its dealt layout word, not the direction's specimen (references/composer.md). In full and design scope a direction without a specimen gives a plain start, and scaffold says so; build it from references/directions.md.
- Motion: one `<section class="page">`, painted by `window.seek(t)` (references/motion.md).
- Mark roles: `data-role="hook"` on the headline, `number` or `object` on the hero element, `accent` on the one accented thing, `logo`, `fine` on source lines.
- Then measure: `render.mjs --audit` (writes the PNGs and audit.json; fails on type floors measured as drawn, contrast, overlap, text off the page, the hook not being the biggest type, broken links, missing images and fallback fonts; only warns on AI-look tells and shapes painted over text), `attention.py` (page 1 is led by the hook, the number or the object; a logo or an element without a `data-role` never leads; an accent may lead by under 1.5 times the best of those three, as a note, and fails above that; body and fine text are left out of the lead race), `layout_memory.py check` (is this cover a copy of a recent one), `video_check.py` for motion, `copy_lint.py` for the words, and `cvd.py` last.

### 7. Critique
references/critique.md. The critic sees the renders and the measured facts, and nothing about what you intended or what you think you fixed. If you can run an independent subagent, do; a fresh context is the cheapest way to get an honest eye. Score as the person who did not make it.

### 8. Rounds
Fix the three worst problems only (fixing everything at once breaks what worked). Keep the critic's "keep". Re-render, re-measure, re-critique. Stop at three rounds. At the cap, every open finding gets a one-line ruling in the delivery notes: fixed, declined (with the reason) or deferred. Silently dropping a finding is not allowed.

### 9. Deliver and remember
Deliver the files and the notes (SKILL.md "Output contract"). `compose.py deliver <slug>` appends the piece to `.atelier/history.jsonl`, and `layout_memory.py add <cover> --name <slug>` remembers the cover. In design scope, deliver only after the host system has approved the piece, so memory holds only what was published. Memory is what keeps the tenth piece as fresh as the first.

## Discipline

**Evidence before claims.** "Done", "readable", "on brand", "fixed" are claims. Each needs fresh evidence: the render you looked at, the script output, the phone-size sheet. Words like "should look fine" mean you have not checked.

**Options before work.** Before a big build, offer two or three approaches with a recommendation, in a short message. Do not ask for permission on obvious defaults; state them and proceed.

**Receiving critique.** For each finding, either fix it ("Fixed: moved the number to the top third") or disagree with evidence ("Disagree: the contrast is 7.2:1, measured"). Never perform agreement ("Great catch!"), never ignore a finding, never let a stated reason downgrade a finding's severity.

**Rationalisations** (if you think the left column, do the right one):
| The thought | What to do |
|---|---|
| "It's minimal, so it's tasteful." | Empty is not minimal. What real material replaced the ornament? |
| "The client will like the gradient." | Show them two versions; let the work argue. |
| "Small text is fine, people can zoom." | Feeds do not zoom. Fix the floor. |
| "The fade-in is subtle." | If everything fades in, nothing is staged. Choose one entrance. |
| "It's on brand because it uses the colours." | Brand is proportion, type and behaviour, not hex codes. Check the accent share. |
| "One more round will fix it." | Three rounds is the cap. Change the approach or simplify the format. |
| "The script is too strict." | Scripts state facts. Change the design, or argue the rule with evidence in the notes; never edit the check to pass. |

**Red flags in your own work:** a first self-score of 9 or 10; a critique with no locations; a "fix" that adds a new effect; three pieces in a row on the same ground; a cover that only works at full size.

## Testing this skill
When you change this skill, test it like code (superpowers' writing-skills method): give a fresh agent a pressure scenario with and without the change and compare behaviour. Scenarios worth keeping: a deadline in 20 minutes and a failing contrast check; a client who insists on a centred title over a gradient; a cover that wins at full size and fails at 360 px; a third critique round that is still at 6/10.
