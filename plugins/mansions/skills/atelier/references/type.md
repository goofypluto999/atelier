# Typography

## Roles, not fonts
At most three faces, each with one job: a display face (headlines), a text face (sentences, numbers), a monospaced face (only for real data, code, logs, timestamps). The bundled set: Instrument Sans (display, weight 400 to 700, width 75 to 100%), Archivo (text and numbers, weight 100 to 900, width 62 to 125%), JetBrains Mono (data). All SIL Open Font License.
- Never use monospace as decoration (tiny mono labels everywhere are a common AI tell).
- If the brand has one face, use its weights and widths as the roles.

## A scale, not random sizes
Pick a ratio and derive sizes from the body size (Bringhurst, "The Elements of Typographic Style"; modular scales). For a 1080 px wide social page:
| Role | Size (1.333 scale from 32) | Use |
|---|---|---|
| fine | 22 to 32 px | source lines only, labelled data-role="fine"; 32 px in the text colour for a line a reader needs (a source the claim rests on, a sample-content note) |
| label | 36 to 40 px (40 px condensed) | field names, legends, station and step labels |
| body | 32 to 38 px | sentences |
| lead | 44 to 50 px | the sentence under a headline |
| h2 | 64 to 76 px | page claims |
| h1 | 92 to 120 px | the cover hook |
| display | 180 to 760 px | one number or word, poster pages |
Two or three sizes do most of the work on any one page. More than 6 sizes on a page is noise (render.mjs --audit warns).

## Floors and legibility
A 1080 px page is shown about 360 to 400 px wide on a phone, a third of its size. So 32 px body text appears at about 11 px. Floors (render.mjs --audit fails below them, measured as drawn): 32 px for any text, 36 px for condensed faces, labelled fine print 22 px. A floor is not a target. In the 30 Oct 2026 run the art-director called a 24 px footnote 8 px on a phone, and 32 to 34 px labels and grey footers "at the floor": set labels that carry the proof at 36 to 40 px, and a footer a reader needs at 32 px or more in the text colour, not text-2. In the second run that day the critics charged a 32 px source line in fine print, 32 px sub-labels, and 36 to 40 px lines in a weight of 400 in six of seven verdicts, while the audit's page line said "min 40px" because it left fine print out. So the page line now gives the smallest size with fine print too, and the audit warns (`phone read`) on any line under 36 px, or under 40 px in a weight under 500, fine print included. A warning, not a floor: a source line can go to the post text instead. Line length 45 to 75 characters for text (Bringhurst); on social pages aim for 25 to 45 characters per line, because the viewer is scanning.

## Setting display type
- Tight leading for display: 0.85 to 1.05. Body leading 1.3 to 1.45. Leading tightens as size grows.
- Negative tracking for display: about -0.02em at 90 px, down to -0.04em or -0.05em at 200 px and above. Never track lowercase body text.
- Uppercase labels need positive tracking (+0.04em to +0.1em) and must still meet the 32 px floor (36 px when condensed). Three or more tiny tracked uppercase labels on a page is a template tell.
- On dark grounds, drop one weight step: light text on dark looks heavier than it is.
- Wide display faces take more measure: Boldonse sets the composition start's sample hook about a third wider than Instrument Sans. data/type_pairings.json gives such a pairing a `hook_scale` (Boldonse 0.76, Libre Baskerville 0.9, Young Serif 0.94, Tektur 0.96), and scaffold sets the start's hook that much smaller, so the sample fits the narrowest hook column (440 px in the map layout). The numbers come from the widest tied chunk of the sample, measured at 100 px in each face, with 4% to spare. Your own hook in such a face needs the same room.
- Headline budget (taste-skill): characters per line is roughly measure divided by (size x 0.5). At 120 px on a 952 px measure, about 16 characters per line: two lines hold about 32 characters. Write to the budget; do not shrink the type to fit the words. The whole page has a budget too: 45 words, the hook 8 of them (references/copy.md "Word budget").
- Break lines by sense, not by the box: "Twelve steps / between an order / and its invoice", never leaving "a" or "the" at the end of a line in display type. Set `text-wrap: balance` on every display heading and tie each small word (a, an, the, of, to, in, on, at, for, and, or, by, with, from, as) to the word after it with a no-break space (`&nbsp;`), and tie the last two words the same way, so no face the deal gives can strand a word. The specimens do both. render.mjs --audit warns on display type (60 px or more as drawn) that leaves one word alone on its last line, or ends a line on a small word.

## Variable fonts as a design tool
Archivo's width axis is a whole second voice: condensed (font-stretch 62 to 75%) at weight 800 to 900 for posters, split-flap boards and big numbers; wide (110 to 125%) for ledger totals. Use `font-stretch` and `font-weight` in CSS; the bundled fonts-local.css declares the full ranges.

## Numbers
- Tabular figures (`font-variant-numeric: tabular-nums`) in tables, ledgers, counters and anything that animates, so digits do not jump.
- Precise numbers carry more credibility than round ones when they are real (Jerez-Fernandez, Angulo and Oppenheimer 2014): 4,812, not "almost 5,000". Never sharpen a number beyond its source.
- Units small and close: "48,200 tokens", with the unit lighter or smaller than the number.
- A numbered column keeps one x and one baseline. Each numeral sits on the first baseline of its item's text, even when one item is taller, marked or boxed; a bar or a fill that marks an item hangs in the margin and never pushes its numeral sideways or centres it on a tall row.

## Right-to-left pages
For Arabic or Hebrew, set `dir="rtl"` and mirror the reading path: the hook starts top right, and arrows and timelines run right to left. Use logical CSS properties (`margin-inline-start`, not `margin-left`). Loosen display leading, because the tight 0.85 to 1.05 can clip the marks above and below the letters. Never synthesise an italic or a slant. The bundled fonts are Latin subsets: fetch a face that covers the script with get_font.py (render.mjs fails a fallback font).

## Rag, widows, alignment
- Flush left, ragged right for almost everything. Centred text only for one or two lines; over 72% centred text on a page reads as a template (taste-skill check).
- No single word alone on the last line of a paragraph or headline (`text-wrap: balance` for headlines, `text-wrap: pretty` for paragraphs in Chromium).
- One typeface change inside a headline (one word in a different face or colour) is a tell; do not do it.
