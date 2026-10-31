# The composer: making every piece different on purpose, and good on evidence

Creative work goes flat over time for a mechanical reason: the same mind, given the same kind of topic, reaches for the same angle, structure, layout and colour. Telling it to "be creative" does not fix that. The composer fixes it with four mechanisms that run as code (`scripts/compose.py`):

1. **Decomposition.** The topic is broken into atoms (facts, numbers, objects, roles, tensions, limits) and each is digested on its own before any idea is formed. Ideas come from atoms, not from the topic's headline.
2. **Dealt play.** Perspectives (24 lenses) and play operators (44, from lateral thinking, TRIZ, SCAMPER, bisociation and constrained writing) are dealt at random, weighted against what has been used, so the starting points differ every time.
3. **Memory with rising pressure.** Every delivered piece is remembered. The more there are, the harder the dealer pushes away from them (diversity scaling), and a topic made before can never get the same operators, lenses, format or direction again.
4. **Grades at every stage.** Eight stages, each graded against a rubric with a threshold. Below it, the stage is recreated with a fresh deal or revised; after 3 graded attempts (2 for the final stage) it escalates to a person. Key stages must be graded by an independent critic, and a critic's FAIL verdict never passes and counts as an attempt.

## The stages
| # | Stage | You produce | Graded by | Below threshold |
|---|---|---|---|---|
| 1 | atoms | 8 to 12 typed, sourced atoms (01-atoms.md) | self | revise |
| 2 | lenses | 3 dealt perspectives, 2 lines each | self | recreate (new lenses) |
| 3 | angles | 6 candidate angles, one per dealt operator (quick scope: one angle, from one operator the author picks) | story-editor (quick scope: self) | recreate (new operators) |
| 4 | genome | the dealt design: format, direction, register, hook, close, harmony, arc, type, motion, layout rhythm | self + script rules | recreate |
| 5 | sections | each section with one job, its atom, words and visual | story-editor | revise |
| 6 | copy | the final words | copy-critic (+ copy_lint.py) | revise |
| 7 | visual | the rendered pages or film | art-director (+ the audit scripts) | revise |
| 8 | final | the whole piece, as a stranger on a phone | art-director + story-editor | revise |

Thresholds, criteria, weights, anchors and caps: data/rubrics.json. A grade needs a score per criterion AND a "because" line per criterion that quotes or locates evidence. compose.py checks only that each line is 25 characters or more, not that it quotes or locates evidence; it also refuses notes that use vague words ("pop", "clean", "modern") 3 or more times, and refuses `--by self` on a critic stage.

## Running it
S is this skill's folder. Run compose.py by its full path from your project folder; it keeps its memory in `.atelier/` there. From a folder inside the project (a page's own folder) it finds the nearest `.atelier/` above, as git finds `.git`, so `next` works there too. To start a separate project inside another project's folder, make an empty `.atelier` folder in it first.
```
python S/scripts/compose.py new q4-report --topic "monthly client reporting at agencies" --medium carousel --brand <your tokens.css>
python S/scripts/compose.py next q4-report        # always tells you the one next action
```
Then follow `next`: fill the worksheet it names, deal when told, grade, choose the winning angle, and at the end `deliver` (which writes the memory and adds the cover to the layout memory). `status` shows the ledger; `coverage` shows how much of the creative space has been used. A slug uses lower case letters, digits, dots, dashes and underscores. `--brand` is optional: it passes the user's brand file to the palette line in the genome worksheet, so the colour plan keeps the brand's hues.

## Quick scope: one image
`new <slug> --scope quick --medium image` walks four stages: atoms (3 to 5), angles, genome and visual. The visual stage also asks for the post text (post.md next to the page): the art-director checks every claim on the page against it. At the angles stage the author picks ONE of the dealt operators and writes ONE angle with it, grades it (`--by self`), and records it with `choose <slug> angle <n>`, where n is that operator's number. In full scope there is one angle per dealt operator, and the story-editor grades them. Only the visual stage needs a critic's verdict file. `deliver` records `scope: quick`, so the piece still counts for diversity.

## Evidence for a critic-graded stage
A critic-graded stage takes the critic's verdict file with `--evidence`. compose.py checks it before it records the grade: the file exists, holds 200 characters or more, carries a verdict line (labelled `verdict` or `<stage> verdict`; the art-director's `seen:` line and labels such as `status:` or `result:` are not read as a verdict), and is not the notes file. Type the critic's scores into `--scores`; compose.py refuses numbers that differ from the verdict file and recomputes the total with the rubric's weights, so the scores are the critic's. A verdict that says FAIL or REVISE never passes, and a FAIL counts as an attempt. The art-director scores exactly the rubric's visual criteria (idea, hook, hierarchy, craft, colour, distinct; idea and hook weigh 1.5) and ends with the grade line. Each grade stores the evidence path and its sha256. compose.py checks the verdict's form, scores and binding, not who wrote it.

The visual grade is bound to its own piece:
- The render must be in the folder scaffold wrote the page in. `--folder` is only for a page built without scaffold; to grade a scaffolded piece elsewhere, run `scaffold <slug> --out <folder>/visual.html --force` first. A page another piece was graded on is refused.
- That folder needs page-NN.png and a PASS audit.json, each newer than visual.html, so a grade cannot rest on an old render.
- The verdict's `## <slug>` heading must be this piece's slug, so give the critic the slug.
- A verdict file already used by another piece is refused.
- The grade records the sha256 of visual.html and of every page.

The visual stage is measured before the critic sees it. `render.mjs --audit` fails on hard rules (type floors of 32 px, 36 px for condensed faces and 22 px for fine print, measured as drawn; overlap; text off the page; contrast; broken links; missing images; fallback fonts) and only warns on AI-look tells and shapes painted over text. `attention.py` checks the first glance: page 1 is led by the hook, the number or the object; a logo or an element without a `data-role` never leads (FAIL); an accent may lead by under 1.5 times the best hook, number or object (a note) and fails above that; body and fine text are left out of the lead race.

## Inside another system (design scope)
When a host system already finds and grades angles and runs its own critics and approval (a content engine, an editorial calendar), do not pay for the same work twice. `new <slug> --topic "..." --medium carousel --scope design` gives the piece four stages fewer: the host owns sections, copy, visual and final. `adopt <slug> --angle "<one line>" --operator <closest id> --evidence <the host's grading record>` brings in the host's approved angle. Add `--pin direction=receipt,register=dry` for axes the host has already decided (its own direction rotation per person, the post's register, so the colour carries the same feeling as the words); the rest of the genome is dealt around the pins. Adopt refuses an angle with no grading record (under 200 characters), a record without a verdict or score line, a record that neither names the angle (6 or more of its words in a row) nor carries a winner line, an operator that is not in data/operators.json, a pin that is not a value of its axis, and an angle that overlaps a remembered one by 0.25 or more. Then `deal genome`, grade it, build with the host's tools and palette.py, and `deliver` only after the host's approval, so memory holds only what was published. The dealt design, the colour plan and the memory stay the composer's; the grading of words and pages stays the host's. Tested in tests/test_composer.py.

## Intelligent play (data/operators.json)
Families and what they do:
- **invert**: reverse the order, turn over a real belief, failure first, the cost of not acting.
- **scale**: zoom in to one atom, zoom out to the system, ten times, a tenth.
- **time**: then and now, slow motion, timelapse.
- **transfer**: borrow a genre, an old idea from another field, a mechanism from nature (Koestler's bisociation: two frames of reference meeting).
- **artefact**: let the real document speak, the anatomy plate, before and after.
- **measure**: the one number, the ratio, the price tag, counting what nobody counts.
- **stakeholder**: somebody else's chair, the object's point of view, the sceptic, the specialist's eye.
- **constrain**: one word per page, no adjectives, numbers only, one shape that never cuts (Oulipo: constraint produces invention).
- **decompose**: define the word, sort into kinds, find the threshold, the question behind the question, the hidden constraint, the second-order effect.
- **combine**: combine two atoms, take one away, put it to another use (SCAMPER).
- **provoke**: a labelled provocation, a random entry word (de Bono).
- **narrative**: two voices, a real scene, the puzzle, a note to the next person.
Each operator states its risk (the sin it can drift into). Play is a method for finding true angles, not a licence for gimmicks: an angle that is clever but untrue is capped at 5 and recreated.

## Perspective lenses (data/lenses.json)
Three are dealt per piece from 24 (the newcomer, the maintainer at 3 am, the auditor, the finance lead, the customer's customer, the historian, the archaeologist in 2040, the sceptic, the object itself, the ten-year-old, the minimalist...). Each angle candidate is written through one lens, so the six candidates do not converge.

## The genome and diversity scaling
The genome is every design decision for the piece, dealt together so they fit: format (30 communication formats with an overuse score; overused ones are dealt less), art direction (28), register (9: wonder, dry, craft-pride, relief, unease-to-control, curiosity, warmth, rigour, play), hook, close, colour harmony and arc, type pairing (the 14 local pairings by default; `deal <slug> genome --any-type` adds taste-skill's 44, which may need a font download), motion recipe (taste-skill's 18, for video), and a layout rhythm (one layout word per section, never the same twice in a row). 04-genome.md prints the definitions of the dealt hook and close (data/structures.json). A hook or close that needs material is dealt only when an atom in 01-atoms.md carries it with a real source: a confession and the closes "changed" and "next-test" need a first-party atom (`first-party: <file>` in the source column), a moment a time atom, a quote a quote atom, an artefact an object atom, a number or price hook a number atom. A made-up object ("no source") carries nothing. The worksheet lists what was left out and why, so nobody invents an admission, a date or a quote to fit a dealt hook. Design scope has no atoms table, so its worksheet says to re-deal when the material cannot carry the hook. Tested in tests/test_composer.py (`r9_tests`). `deal <slug> genome --pin axis=value` fixes an axis before the deal in any scope (for example `--pin register=warmth`), and later deals of the piece keep it. Without `--brand`, a paper ground is never dealt a serif display face, the cream-and-serif look generated design falls into (references/tells.md).

`scaffold` does not copy the dealt direction's specimen. With nothing in memory the art-director judges distinct against the specimen a page started from, so a page started as the specimen keeps its frame and scores "related" (6 in 5 of 6 verdicts in the 30 Oct 2026 run). For an image or a carousel, scaffold writes a composition start instead: the grid (one left margin at 80 px), the dealt type and the palette.css roles, each page set up for its dealt layout word (data/structures.json "layouts" defines all twelve), with no sample words and no part of the specimen's arrangement. The deal never gives page 1 the specimen's own layout (data/directions.json "layout"; most specimens are a stack), unless the format pins that layout to page 1. 04-genome.md and 07-visual.md then say what to compose: the direction's grammar, the specimen's frame in one line (data/directions.json "frame") to leave, each page's layout word, the object atom, and the word budget (references/copy.md). The specimen stays the picture of the grammar's rules. Its stock parts (data/directions.json "stock": the poster's huge numeral and hairline, the map's ring stations, the manual's rhombi) are listed in both worksheets as parts that must not appear unchanged, because once the frame was gone, the critics of the 30 Oct 2026 runs still read them as the specimen; the builder makes the direction's device out of the topic's own object instead. A film still starts from its motion specimen. Quick scope deals only directions that have a specimen, so there is always a picture to read. In full and design scope a direction without a specimen gives a plain start, and scaffold says so; build that direction from references/directions.md. Scaffold points the direction's colour tokens at the palette.css roles, so the colour plan colours the page and any part borrowed from the specimen, links the `new --brand` file after tokens.css, and fills the page's empty logo slot from the brand file's `--logo` (`--logo-on-dark` on a dark or colour-field ground) or removes the slot, printing why. Where the brand file declares `--disp`, `--body` or `--mono`, scaffold keeps those faces; the dealt type pairing sets only the ones it leaves out. `next` prints the palette.py line before scaffold while palette.css is missing.

Rules, with n pieces in memory:
- each value is weighted by 1 / (1 + its recent uses) to the power alpha, alpha = 1 + log2(1 + n/10), so the pull away from the familiar grows as the archive grows;
- the genome must differ from each of the last 10 on at least d_min axes, d_min = 2 + floor(log2(1 + n/4)), so near-duplicates are impossible;
- empty cells of register x operator family x ground are preferred: a quality-diversity archive in the spirit of MAP-Elites (Mouret and Clune 2015), which fills a space of different good solutions instead of polishing one.
Measured (tests/test_diversity.py, 30 simulated pieces): every axis near its maximum entropy (register 3.16 of a possible 3.17 bits), 30 pieces in 30 different cells, and the most similar pair within any 10 still differing on 5 of 8 axes.

## Same prompt twice
A topic that shares half its key words with a delivered piece counts as the same topic. Its deals exclude every operator, lens, format and direction used before for it; `similar` flags any angle whose phrasing overlaps earlier angles (0.25 or more: recreate). Tested in tests/test_composer.py: the same topic twice shares no operators, no lenses, no format and no direction.

## Bite-sized sections
Stage 5 turns the angle into sections, one job each (claim, proof, turn, payoff), each tied to one atom, each graded for its job, its proof and whether it makes the next section necessary. The arc is graded too: the peak and the end must carry the takeaway (peak-end rule). A section that does two jobs is split; a section with no job is cut.

## Colour in the genome
The register chooses a colour recipe; the harmony and the arc are dealt; `palette.py` turns them into per-page colours on the direction's ground (`--ground`) and inside the brand's hues and checks contrast and colour vision (references/colour.md, "Connotation by system").

## What the grades are for
Grades are not a ceremony. Each stage's lowest criteria are the revision brief; a recreate means the idea was wrong, not the wording; an escalation means the material or the topic is too thin, which is a decision for a person. Never lower a threshold to make a piece pass.
