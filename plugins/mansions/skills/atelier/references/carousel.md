# Carousels and single images

## Sizes (check the platform's current help page before a launch; these were current in late 2026)
| Platform and format | Size | Notes |
|---|---|---|
| LinkedIn document carousel | 1080 x 1350 per page (4:5), or 1080 x 1080 | upload as PDF; give the document a title; text stays vector in the PDF |
| LinkedIn image | 1080 x 1350 (4:5) | portrait takes the most feed height |
| Instagram feed | 1080 x 1350 (4:5) | the profile grid shows a taller-than-square crop of each post (check the current ratio); keep the key content away from the top and bottom edges |
| Stories, Reels, TikTok, Shorts | 1080 x 1920 (9:16) | keep text out of the top 220 px, the bottom 320 px and the right 140 px (buttons and captions overlay); `render.mjs --audit --safe reels` checks it |
| X | 1080 x 1350 or 1600 x 900 | |
| Slides (16:9) | 1920 x 1080 | references/slides.md: one claim a slide, body 48 px, fine print 32 px |
Render any size with `node scripts/render.mjs file.html --size 1080x1920`.

## Anatomy of a carousel (5 to 9 pages)
Worked example: examples/ledger-carousel (6 pages: stack, bleed, table, split with a to-scale bar, struck table, keep).
1. **Cover.** The hook in 7 words or fewer, plus the material that proves it is worth a swipe (the number, the object, the first line of the artefact). It must work alone, at 360 px wide, in under a second. No "swipe" arrows: a cut-off element at the right edge, or a line that continues, pulls the swipe without asking.
2. **Setup (1 page).** What was expected, or the situation, in one claim.
3. **Turns (2 to 5 pages).** One claim per page, each with its proof (a number, an artefact, a diagram). Alternate dense and sparse pages.
4. **Payoff (1 page).** The insight the cover promised.
5. **Last page.** The one thing to remember, or something useful to keep (a rule, a check, a number): people remember the peak and the end (Kahneman et al. 1993). Then the logo. Never a pitch, never "follow for more".

A page without a claim is deleted. If two pages make the same claim, merge them.

## Continuity
- Same grid, margins, type scale and ground logic on every page; the layout inside the grid changes.
- A thread can carry the set: a line that runs from page to page, a number that grows, a stamp that moves. Use one, not three.
- Page numbers only when the order matters ("2 of 6"), never as decoration.

## Single images
Everything the carousel does in one frame: hook, proof, source. Fewer words than you think: about 20 words is a lot for a single image.

## Covers that stop the scroll
- One element dominates (scale), one contrast decides (light against dark is the safest), one accent marks it.
- The cover must not look like the last eight covers (`python scripts/layout_memory.py check <cover>`).
- Faces raise engagement on Instagram (Bakhshi, Shamma and Gilbert 2014); test a face on the cover before assuming it works elsewhere.
- A cover that only works at full size does not work.

## Accessibility and text
- Alt text for every image post starts with the claim and its numbers, then says what the image shows; never "an image of". Captions for every video.
- The words on the pages must also be in the post text if the platform's alt text is unavailable, so screen readers and search see them.
- Run `python scripts/copy_lint.py visual.html` on the page text: the sins of copy apply on the page too.

## The checks for every page
`node scripts/render.mjs visual.html` (PNGs and PDF), then `--audit` (floors, contrast, tells, hook size), `python scripts/attention.py <folder>` (pop-out), `python scripts/contact_sheet.py <folder>` (the whole set at a glance), `python scripts/layout_memory.py check <folder>/page-01.png`.
