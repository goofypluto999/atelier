# Brand: capture it once, use it everywhere

A brand file turns "make it on brand" from a guess into a check. Every direction in this skill reads the same token names, so a new brand is one CSS file.

## The brand file (assets/brands/TEMPLATE.css)
Roles, not colours:
| Token | Role |
|---|---|
| --night, --deep | dark ground, deeper panels on dark |
| --paper, --paper-2 | light ground, panels on light |
| --cream, --cream-2, --steel | text on dark: primary, secondary (7:1 for body), labels (large only) |
| --ink, --ink-2 | text on light: primary, secondary |
| --house, --teal, --teal-lit | the accent, a lighter step, the step that works on dark |
| --glow, --amber | warm highlight and status highlight on dark |
| --disp, --body, --mono | display face, text face, data face |
Load it after tokens.css: `<link rel="stylesheet" href="../tokens.css"><link rel="stylesheet" href="../brands/yours.css">`. The bundled default is a neutral palette that belongs to no brand; the specimens are drawn in it, and a piece made without `--brand` gets its own palette from palette.py instead (references/colour.md, "Own palette"). The Mansions Agency palette and logo are an optional theme: assets/themes/mansions.css. Load a theme or your own file after tokens.css, or pass it with `compose.py new <slug> --brand`.

## Capturing a brand from its site (with permission)
`node scripts/brand_extract.mjs https://example.com --out brand` does steps 1 to 3 and drafts step 4: screenshots, the palette by area and by text, borders and drawing marks, the type of headings, body and buttons, logo files, a draft brand CSS and the contrast of each pair. It says plainly when it finds no light ground or no saturated accent instead of guessing. Then check it by eye:
1. Open the site with Playwright at 1440 px and 390 px wide; take full-page screenshots.
2. Read computed styles of the body, headings, buttons and links: background colours, text colours, font families, weights, sizes, letter-spacing, border radii.
3. Download the logo files the site serves (SVG preferred) into the project's assets, and note clear-space and minimum size if the brand guide states them.
4. Map what you found to the roles above. Check each text pairing with render.mjs --audit; if a brand colour fails contrast as text, keep it for fields and large type only, and add a lighter or darker step for text.
5. Write brand.md next to the tokens: the voice in 3 adjectives with one example sentence each, what the brand never does (banned looks and words), and any rules from the brand's own guide. Write the visual rules as numbers, counts and bans, not adjectives: "restrained" cannot be checked, "one accent per page, two faces, radius 0" can. The brand's own guide always wins over this skill.

## Fonts
`python scripts/get_font.py "Bricolage Grotesque"` fetches an open-licensed Google font with its licence file into the project.
Use the brand's fonts if they are licensed for the use (web fonts for rendering locally, OFL or a purchased licence). If unavailable, pick the closest open font for each role and say so. Never fake bold or italic by synthesis; load the real weights (variable fonts help).

## Logos
A brand file declares its logo with `--logo: url(file)` and, for dark and colour-field grounds, a light lockup with `--logo-on-dark: url(file)`; scaffold fills the specimen's empty logo slot from them (a relative path is read against the brand file) or removes the slot. The logo is the quietest element on a page: small, in a corner, never the first thing that pops out (attention.py fails a cover where it does). Never stretch, recolour outside the brand's variants, or add effects. Brand logos are trademarks of their owners and are not covered by this skill's MIT licence.

## Consistency is the brand
People learn a brand from repetition of proportions and behaviour more than from a hex code: the same type roles, the same accent discipline, the same tone of motion. The directions vary the grammar on purpose; the brand file keeps everything else constant.
