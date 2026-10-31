# Photographs

Most directions run on type, drawing and real artefacts. When a piece uses photographs, two rules hold.

- **Type on the quiet area.** Place text where the photograph is calm (sky, a wall, a floor, an empty table) before anything else. If contrast still fails, put a flat neutral scrim (black at 40 to 55%) under the text block only; never a colour wash or a gradient fog. `render.mjs --audit` samples the rendered pixels under text when the photograph is a CSS `background-image`; over an `<img>` element it judges the colour behind the image instead, so set a photograph that carries text as a background.
- **One treatment, one grade.** Every photograph in a set shares one treatment (untouched, greyscale, or darkened for a dark page) and one grade: the same light, the same saturation, the same few crop ratios. Mixed grades read as a stock dump.

Deeper, in the vendored taste-skill (MIT): vendor/taste-skill/references/imagery.md, section 5 (cropping and placing) and section 6 (treatment). Section 6 also allows a scrim that fades from black to transparent; this skill keeps to the flat one.

Not used here: stacked text shadows to lift type off a photograph. `render.mjs --audit` counts a text shadow as a glow and warns. Use the quiet area or the scrim.
