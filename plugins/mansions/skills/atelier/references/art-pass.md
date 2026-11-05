# Art pass: an image people stop for

Use this when a piece must stop a stranger in a feed: a single image, a carousel cover or the first frame of a film. It comes from a real run (Nov 2026): a post about one week of UK public tenders went through four rounds. A code card, a default chart and a brand-correct line drawing were each judged lifeless by the owner. Three scenes in three art styles, made in parallel, were judged "THIS is what we want". The difference was never polish. It was a story.

## The recipe
1. **Load the bar.** Put the owner's rejections, in their exact words, into the brief, with the images they rejected. Add what they want, in their words. Critics advise; the owner's taste decides.
2. **Stay in the brand family.** Ground, light and one accent from the brand (references/brand.md). Name and address small, in the brand's type. Label an illustration as one.
3. **Turn the data into a world.** The big number becomes the place: a pile of 2,413 notices became a mountain, a sea, an archive hall. The small number becomes the one lit thing in that world, in the accent: 7 flags on a summit, 7 notices in a net, 7 folders in a beam of light.
4. **Put someone in it, doing something.** A climber on a trail, a fisherman hauling a net, a clerk who just stood up. A scene is a story; an object is a diagram.
5. **Add one quiet joke.** The boat is folded from a notice. The fisherman smokes a pipe. Notices blow off the summit like snow. One notice became a paper plane.
6. **Hide the true count in the art, and log it.** For example, 2,403 sheets in the sea, 3 falling, 7 in the net: 2,413. It keeps the picture honest and rewards whoever checks.
7. **Hook on the image, 7 words or fewer, playful and true.** "2,413 at sea. 7 in the net." / "2,413 notices. 7 made the desk." It must read at 360 px wide.
8. **A real art style with a physical process.** Silkscreen poster: opaque flat inks, 4 to 6 per print, stepped bands, registration slips, paper as the brightest colour. Woodcut print: carved lines, gouge texture, ink pulled through a print model, one accent only where the wood is cut. 3D cinematic still: real path-traced light, haze and dust in a beam, a low camera, then grain. (Silkscreen and woodcut grammar rewritten from lemo-opuscar by LemoLab, MIT, commit bebbbe1; see vendor/MANIFEST.md.)
9. **Type that belongs to the style.** Poster: a national-park display face and a condensed numeral face. Woodcut: a carved serif with lining figures and a book serif. 3D: the brand sans. Open-licence faces only, with the licence file beside each (scripts/get_font.py).
10. **Make three in parallel, then let the owner pick.** One maker per style, each in its own folder, one shared brief. Each renders, looks at its own render, judges it against the owner's bar, and improves: at most 4 rounds. Then the owner sees the three side by side. The two not picked become style references for later pieces.

## When to use it
- A new story or a new style: the full three-sample pass.
- A normal piece in a style the owner already approved: one maker, the same recipe, one style by rotation.
- Never skip steps 3 to 7. A brand-correct object on a plain ground is the most common failure.

## What it costs (the measured run)
Three samples took 11 to 26 minutes each. A 3D still rendered in 53 s at 256 samples on an 8 GB laptop GPU. The makers' tokens were the largest cost; plan for three times one image.
