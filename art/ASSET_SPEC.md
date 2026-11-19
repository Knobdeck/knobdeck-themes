# Theme asset spec: painting a sliced dial theme

A sliced theme (engine 2, like Forge) is five painted parts. The dial cuts and moves them live:
each item gets its own slice, warped to its wedge whatever the item count, and the hovered slice
fades to its lit version. Everything is painted on **one blueprint sheet**.

**The sheet:** `art/templates/blueprint.png` (2832 × 1962 px, magenta with white wireframes).

**To make a theme:** paint every part inside its wireframe, keep everything else flat magenta, and
send the sheet back as a PNG at the same size. Then `python3 art/cut.py <sheet.png> <theme-id>`
writes the theme's images, and the CSS (motion, glow colours, presets) is written around them.

## Rules for every part

1. **Straight top-down view**, as if looking at a flat object lying on a table. No perspective,
   no tilt, no camera angle.
2. **Light from the top left**, soft, the same on every part.
3. **Fill the wireframe exactly.** The white line is the part's outer edge. Paint up to it; nothing
   may stick out past it (a soft shadow may fall a few px outside, onto the magenta).
4. **Background stays pure magenta `#FF00FF`.** It is keyed out. Don't use magenta or pink inside
   the art, don't add a floor or table, and don't leave the guide lines or any text.
5. **No icons, letters or symbols where the app draws its own.** Item icons sit on each slice's
   circle; the item's name is written on the centre piece.
6. **Same size back.** If the generator changes the size, keep the aspect ratio; the cutter scales
   it back.

## The parts

Sizes are in dial px (the sheet draws them at 4 sheet px per dial px).

| # | Part | Shape and size | What it is | Notes |
|---|---|---|---|---|
| 1 | **Backplate** | disc, r = 196 | Everything behind the items: the base the theme is built on (wheel, frame, shield, panel) | Decorate freely **outside** the outer dashed ring (rim, sockets, notches, runes, vines). Between the two middle dashed rings (r = 58…134) paint a **plain recessed channel**: the slices sit in it, and it shows in a submenu's gap. Inside r = 60: plain (the centre piece covers it). It never moves. |
| 2 | **Centre piece** | disc, r = 56 | The emblem in the middle | Must be **your own design**: no logos or game emblems. Keep the inner dashed disc (r < 40) **calm and dark enough for light text**, since the hovered item's name is written there. |
| 3 | **Back item** | disc, r = 22 | The small button for "the menu you came from", shown beside a submenu | A small stone, coin or orb in the theme's material. The app puts an icon on it. |
| 4 | **Item slice, idle** | one wedge of a ring of 8 (45°, r = 64…128, with the joint to its neighbours already left out) | One item's piece of the object: a stone slab, glass segment, leaf, panel… | The item's icon sits on the small circle: keep that spot plain (a recess or flat field is ideal). Its edges should read as an edge (bevel, rim, outline), because the dial repeats this piece round the ring. The dial warps it for 3 to 16 items, so avoid details that only look right at exactly 45° (perfect circles, text). |
| 5 | **Item slice, hovered** | the same wedge | The same piece, "lit": glowing, raised, energised | **Same shape and position as 4.** Only the light changes (glowing edges or runes, brighter surface). The dial crossfades 4 → 5 as the pointer arrives, and adds its own lift and glow. |

## Prompting an image generator

Attach the blueprint as the layout image and describe the style, e.g.:

> Using this blueprint as an exact layout guide, paint a game UI radial menu kit in the style of
> *[theme: e.g. "ancient rusted iron and carved granite", "neon cyberpunk glass", "living wood and
> leaves"]*. Replace each white wireframe with the finished part, filling it exactly, seen straight
> from above, lit softly from the top left. Part 1 is the backplate disc with a plain recessed
> channel ring for the items; part 2 is a centre emblem with a calm dark middle; part 3 is a
> small round back button; parts 4 and 5 are the same single item segment, 5 glowing as if
> hovered. Keep the background pure flat magenta #FF00FF. No text, no guide lines, no icons,
> no logos.

Generate a few, pick the sheet whose parts fit their outlines best, and send it back. Small fixes
(a part a little off its outline) are fine; the cutter trims to the outline.

## What comes back to you

The theme folder (`themes/<id>/`) with `plate.webp`, `center.webp`, `back.webp`, `slice.webp` and
`slice-hover.webp`, plus `theme.json` (`slices` with `tile` / `tileHover`) and `theme.css`: the
open animation, the hover glow colour, icon colours and presets. Check it with
`node scripts/preview/preview.mjs check <id>`.
