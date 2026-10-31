# Tells: what makes a design look machine-made

Each tell is a default a generator reaches for when it has no idea. Removing a tell is half the job; the other half is putting real material in its place (taste-skill: "an empty page with good manners" is a tell too).

## The clusters generated design falls into (from Anthropic's frontend-design skill, Apache 2.0)
1. A warm cream ground (near #F4F1EA) with a high-contrast serif display and a terracotta or clay accent (near #D97757).
2. A near-black ground with one bright acid-green or vermilion accent.
3. A broadsheet layout: hairline rules, zero radius, dense newspaper columns.
4. The SaaS card kit: identical rounded cards, one radius everywhere, the same soft grey shadow, gradient washes.
5. Template chrome on any subject: tracked all-caps eyebrows, "A · B · C" meta strings, "WORD, fragment" labels, tinted near-black (#0B0B0B, #111) for black, monospace for small data labels, "→" after links.
Each is legitimate when the brief or the brand asks for it (the optional Mansions theme, assets/themes/mansions.css, is a real brand's palette, and it sits near clusters 1 and 2 for that reason). A piece with no `--brand` gets its own palette from palette.py, kept out of clusters 1 and 2 and away from the specimens' colours (references/colour.md, "Own palette"). When an axis is free, do not spend the freedom on one of these.

## Static pages
- A centred title on a gradient. Purple-to-blue gradients, neon on black, glows behind text, glassmorphism, gradient text.
- Tiny uppercase tracked labels above every heading (eyebrows); three or more on a page.
- 01 / 02 / 03 numbering on things that are not a sequence; "A · B · C" chains of keywords.
- "Swipe" arrows and "→" after every line.
- Rows of identical cards with an icon on top; icon soup; emoji as bullets.
- One word in a headline recoloured or set in another face.
- Hairline 1 px boxes around everything; resting drop shadows on flat items.
- Fake dashboards: grey bars, lorem charts, made-up UI.
- Fake product chrome: traffic-light window dots, a pulsing "live" dot, NEW, BETA or version badges, status words the product never uses.
- Rows of pill-shaped tags, and a different corner radius on every box. A piece uses one radius, two at most with a role each, set by the direction.
- Panels inside panels: a box inside a box inside a box (references/composition.md, common region).
- Stock imagery of laptops, handshakes, glowing brains, robots, circuit boards, sparkles, abstract 3D blobs.
- Everything centred; everything the same size; everything bold.
- Monospace used as decoration rather than for real data.
- A blank area with no tension, presented as minimalism.

The fake chrome, pill and nested-panel tells follow Uncodixfy (cyxzdev, MIT), rewritten for social images.

## Motion
- Everything fades in with the same timing.
- Bouncy or elastic easing on serious content; particle bursts; lens flares.
- Typewriter or scramble text on every line.
- Spinning or pulsing logos; a logo as the first frame.
- Crossfades between unrelated shots; blur wipes.
- Dead time: 3 s or more with nothing new.
- Captions too long to read in the time shown.

## Copy (on the page)
See references/copy.md: stock words, not-X-but-Y, triads, summaries, questions to the viewer, flat rhythm.

## What to put in the gap
| Removed | Replace with |
|---|---|
| gradient background | a flat brand ground, or a full accent field as a chapter |
| eyebrow labels | nothing; let the headline lead, or one real field label in a real form (task card, ledger) |
| stock image | the real artefact: a screenshot, a log line, a config line, a receipt, a map of the real flow |
| icon row | one diagram that shows how the parts connect |
| glow on the key number | scale and the single accent |
| fade-in on everything | one staged entrance per beat, springs, a held moment |
| pill tags | the words set plain, or the one real field the direction's form has |
| nested panels | one container; group the rest by space |

## Automated checks
`render.mjs --audit` warns on eyebrows, glows, gradients, too many sizes, too many faces, too many words, too much centred text, fake product chrome (window dots, live dots, NEW or BETA badges), pill tags and too many corner radii, panels nested three deep, and raw colour values outside the tokens. It fails on contrast, the type floor and a hook that is not the biggest type. `copy_lint.py` warns on repeated words. Mark a deliberate exception with `data-allow="..."` on the element or a parent, and say why in the notes: `gradient`, `shadow`, `chrome` (fake product chrome), `pill` (pill tags and corner radii), `nested` (nested panels) or `colour` (raw colours; `--raw-max N` sets how many distinct raw colours a page may keep, default 6).
