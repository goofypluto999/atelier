# Composition: grids, hierarchy and one path for the eye

## The page has one job
One subject, one claim, one path for the eye. Before placing anything, decide the order in which the viewer should see three things (usually: the hook, the proof, the source or logo). Then make each one visibly less important than the one before.

## Grids (after Josef Müller-Brockmann, "Grid Systems in Graphic Design", 1981)
- Choose margins first. On a 1080 x 1350 page: outer margins 70 to 90 px; bottom margin larger than top (platform UI and the eye's settling point). Keep 60 to 80 px clear of edges where feeds overlay buttons (references/carousel.md, safe areas).
- A 6- or 12-column grid with 24 to 32 px gutters covers almost every layout; a 4 x 5 modular grid suits posters and data pages.
- Align to the grid, then break it once, on purpose, for the element that matters (an oversized number bleeding off the edge; mark it `data-allow="bleed"` so the audit knows it is deliberate). One deliberate break reads as design; several read as error.
- Fewer left edges are calmer: more than 5 or 6 different left alignments on a page reads as clutter (taste-skill check). Every block outside a container (the headline, a diagram's first station and its label, a list's numerals, a note, the source line) starts on the page's one left margin; a block set in 10 to 40 px from it reads as a slip, not a choice. Inside a box, every block starts on one inner edge. A drawing keeps the right margin too: no ring, label or line end past it.
- Write positions in percentages or grid units, not one-off pixel nudges, so pages in a set stay consistent.
- Take every gap from one spacing scale (for example multiples of 8 px on a 1080 px canvas). A gap off the scale is a nudge, and the eye reads it as a mistake.
- A rule, a border or a table line never runs through text: a row too short for its text lets the next rule strike it. render.mjs --audit fails it (data-allow="over" marks a deliberate strike).

## Hierarchy: how importance is made
In order of strength: size, then contrast (light against dark), then weight, then colour, then position (top and left read first in left-to-right languages), then isolation (space around it). Use two or three of these for the top element; use one at most for the rest.
- Scale contrast: the display element should be at least 4 times the body size. Timid ratios (1.5x) look like a document; bold ratios look like a design.
- Weight and colour can do the work of size: a smaller label can still be secondary by being lighter and greyer (Refactoring UI, Wathan and Schoger).
- Do not make everything bold. If two things shout, neither is heard.

## Gestalt (Wertheimer and colleagues, 1920s) as working rules
- Proximity: things that belong together sit closer to each other than to anything else. Spacing inside a group must be visibly smaller than spacing between groups (at least 1:2).
- Similarity: same role, same treatment. A label is always the same size, weight and colour.
- Common region: a panel or a field groups things more strongly than lines do; prefer a 2 to 6 point lightness step between surfaces over a 1 px border (taste-skill). Use one container level per page: group by space first, a field second, never a box inside a box inside a box.
- Continuity and closure: a line, a curve or an implied edge leads the eye; use it to lead to the claim.
- Figure and ground: the subject must separate from the ground at a glance; test by blurring the page (attention.py's overlay is a quick proxy).

## Focal point and pop-out
Bottom-up attention is pulled by contrast in colour, intensity and orientation before reading starts (Itti, Koch and Niebur 1998). People also fixate text and faces whatever their contrast (Cerf, Frady and Koch 2009), and look at the centre of a frame first (Judd et al. 2009).
- Make the one thing that pops out the thing you want remembered. If a decorative shape pops out more than the hook, tone the shape down.
- An isolated item is remembered (von Restorff effect): the single accent works because it is single.
- `python scripts/attention.py <folder>` shows the pop-out map; the audit checks the hook is the biggest type.

## Reading patterns
- Text-heavy pages are scanned in an F shape: the first line and the left edge get the most attention (Nielsen Norman Group eye-tracking). Put the claim in the first line and start lines with the meaningful word.
- Sparse pages are read in a Z: top left, top right, diagonal, bottom left, bottom right. The hook top left, the proof on the diagonal, the source and logo bottom right.
- The "Gutenberg diagram" is folklore with weak evidence; do not cite it as a rule.

## Space
Empty space is active only when it frames something. A large blank area with no tension (nothing near its edge, nothing pointing into it) is not minimalism, it is a hole. Either give it a job (a number bleeding into it, a line crossing it) or fill it with real material. In a row of cells (a form, a table, a split) the same holds per cell: render.mjs --audit warns (`empty cell`) when one cell's content spans under 40% of its height beside a cell filled to 75% or more, the lopsided row the 30 Oct 2026 critics charged. A run of identical marks (boxes, dots, ticks) that wraps and leaves a short last row (7 as 5 + 2) warns too (`wrapped run`): set a count on one line, or break it where the count breaks.

## Sets of pages
- Keep the grid, margins and type scale identical across a carousel; change the layout inside the grid page by page (huashu-design: fixed style, varied layout).
- Alternate densities: a dense proof page after a sparse claim page.
- Name the layout of each page in one word (stack, split, bleed, grid, table, map). The same word twice in a row, or three times in a set, is samey.
