# Slides: a deck for a talk, a pitch or a shared screen

A slide is read on a projector or a shared screen: smaller, farther away and for less time than a phone feed, while someone talks. So a slide carries one claim, says it in its title, and shows the proof under it. Worked example: examples/scoring-deck (5 slides, 1920x1080, every claim citing the file that proves it).

## The slide
- **Size.** 1920x1080 (16:9). Render with `--size 1920x1080`. deck_check.py scales its floors to another width.
- **One claim, in the title.** The title is a full sentence that states the claim, not a topic label ("Seven of twelve steps are copying", not "Process"). The body holds the proof: one number, one chart, one image or one sentence. This is the assertion-evidence structure; classroom studies by its authors found better comprehension than topic titles with bullets (Garner and Alley 2013, International Journal of Engineering Education 29(6); medium: one line of studies).
- **Floors.** Body text 48 px or more and labelled fine print 32 px or more on a 1920 px wide slide: 24 pt and 16 pt on a 13.33 in slide, a common rule for projected slides (a heuristic, not a study). The title is 96 px or more. render.mjs --audit keeps its own 32 px floor; deck_check.py adds the slide floors.
- **40 words or fewer.** What the speaker says goes in notes.md beside the deck, never on the slide.
- **Margins.** Keep marked boxes 3% or more inside each edge: projectors and call windows crop.

## The deck
- One title line: every slide after the cover starts its title at the same point (deck_check.py allows 24 px).
- Three type families or fewer, seven type sizes or fewer across the deck.
- One accent, on the number or the object, the same role on every slide.
- The order of claims is a story: setup, turns, payoff (references/carousel.md "Anatomy of a carousel" applies slide by slide).
- Deliver carousel.pdf (one page per slide, vector text) and the PNGs; a PDF opens the same everywhere.

## Run it
```
node S/scripts/render.mjs deck.html --audit --pdf --png --size 1920x1080 --out <folder>   # every slide audited, PDF and PNGs
python S/scripts/deck_check.py <folder>                                               # slide floors, titles, deck consistency, PDF
python S/scripts/attention.py <folder>                                                # each slide led by its title, number or object
python S/scripts/contact_sheet.py <folder> --out <folder>/preview.png                 # what the critic sees first
python S/vendor/huashu-design/scripts/design_lint.py check deck.html --viewport 1920x1080 --min-body 22 --min-label 22
```
`compose.py new <slug> --medium slide` deals a three-section format (claim, map or quote) and gives a plain 16:9 start; build each slide on the worked deck's grid.

## Checks
| Check | Fails when | Kind |
|---|---|---|
| audit (render.mjs) | a hard rule fails on any slide | measured |
| slide floors (deck_check.py) | text under 48 px, or fine print under 32 px, at 1920 px wide | measured; the floors are a common rule |
| title (deck_check.py) | a slide has no `data-role="hook"` | measured |
| title line (deck_check.py) | from slide 2, a title's top-left is more than 24 px off the deck's median | measured; 24 px is this tool's choice |
| families (deck_check.py) | more than 3 type families across the deck | measured |
| PDF (deck_check.py) | carousel.pdf's page count is not the slide count | measured |
| attention.py | slide 1 is led by a logo or an unmarked element | a model of attention, a rough guide |
deck_check.py warns on a slide over 40 words, more than 7 sizes, a family used on one slide only, a box near an edge and a missing PDF. tests/test_slides.py plants each fault.

## Critics
The art-director judges preview.png and each slide as rendered, with the script output as facts; the weakest slide decides. The story-editor judges the order of claims (the sections stage) and the copy-critic the words. Calibration covers 4:5 covers, not slides (references/critique.md): treat a slide verdict with that in mind.

## Not measured
How the deck reads in a given room (screen size and distance), the speaker's timing against the slides, and animated builds.
