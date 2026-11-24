# knobdeck-themes

Themes for KnobDeck, all original. A theme styles the dial overlay on the PC and the deck of every
phone connected to that PC: the PC picks the theme (Themes in the config window) and tells its phones
the id; each phone downloads the theme's phone counterpart from the registry itself. The app ships
three built-ins (**Auto**, **Midnight** and **Daylight**, in `Knobdeck/app/public/dial-themes/`; the phone
app has its own copies); everything here is downloaded from the Themes page.

| Theme | Look | Presets |
|---|---|---|
| `analog` | Hardware synth knob: knurled metal, tick marks, an LED arc that follows the pointer | Red, Green, Blue, White |
| `graphite` | Machined aluminium: spun-metal center, brushed buttons, engraved icons | Space Gray, Gold, Navy |
| `frost` | Frosted glass discs with a sheen | Smoke, Ice, Rose |
| `ember` | Amber on black with a segmented meter | Nixie, Ice, Lime |
| `phosphor` | Green-screen terminal: square tiles, scanlines, monospace | Amber, White, Cyan |
| `neon-grid` | Synthwave sunset over a neon grid | Miami, Laser, Toxic |
| `paper` | Ink on paper, hand-drawn outlines, highlighter hover | Blueprint, Kraft, Chalk |
| `bloom` | Pastel petals coloured by their direction | Vivid, Mint, Dusk |
| `aurora` | Dark glass with a turning aurora glow | Solar, Ocean, Rose |
| `studio` | Creator console with an on-air light | Violet, Teal, Gold |
| `contrast` | Accessibility: bold outlines, large targets, almost no motion | Black on White, White on Blue |
| `lagoon` | Navy items floating over the desktop, a dark glass hub, an aqua light on the picked item | Ice, Amber, Rose, Violet |
| `halo` | A quiet dark platter with a watch-face scale: gray slices, crisp edges, a blue bead beside the item you point at (engine 2) | Graphite, Orange, Pink, Green |
| `lucid` | Liquid glass: clear panels with bright rims on a faint smoked disc, the hovered one filling with light (engine 2) | Clear, Dusk, Deep |
| `pane` | A layered dark surface with small-radius tiles and hairline strokes; the hovered item gets an accent pill (engine 2) | Orange, Purple, Green |
| `void` | Pure black, drawn only in hairlines and light; every move on a spring, folders pour out of the centre (engine 2) | Ice, Ember, Violet |

- `themes/<id>/`: `theme.json`, `theme.css`, optional `presets/<Name>.json` and assets the CSS links
  relatively (`url("plate.webp")`), plus the phone counterpart `phone.json` and its `phone-bg*.jpg` art
  (see "Phone themes"; both stay out of the dial zip).
- Whole-menu art is a layer on the open center sized past the ring, with `drawChildrenBelow: false` so
  the items sit on top of it.
- `previews/<id>.gif`: the preview shown in the app before download. It isn't a release asset: the
  registry links it by raw GitHub URL, so a new GIF shows up without a release.

Pushing to `master` runs the **release** workflow: it zips every theme and publishes a GitHub Release
with `<id>.zip`, `<id>.phone.json`, its images (`<id>.phone-bg[-<preset>].jpg`) and a `registry.json`
(id, name, author, version, zipUrl, sha256, preview, phone: { url, sha256 }). Once the release
exists it sends a `theme-released` dispatch to the `knobdeck-registry` catalog, which rebuilds and serves it (skipped
until the catalog GitHub App is configured: `CATALOG_APP_ID` variable, `CATALOG_APP_PRIVATE_KEY` secret).

## Writing a theme

The dial engine is `Knobdeck/app/src/dial/overlay/` (Kando's theme format, engine version 1).

**theme.json**

| Field | |
|---|---|
| `name`, `author`, `license`, `version`, `description` | Shown in the app. `version` is semver (see CLAUDE.md). |
| `layers` | One div per layer inside every node, **first = frontmost**. `content`: `"icon"`, `"name"` or `"none"`. |
| `colors` | Set as `--<name>` custom properties; the CSS reads them. A preset overrides any of them. |
| `presets` | Names of `presets/<Name>.json` files (`{"colors": {...}}`). The app offers them as chips. |
| `centerTextWrapWidth` | Diameter the hovered item's name wraps into. |
| `drawChildrenBelow`, `drawCenterText`, `drawSelectionWedges`, `drawWedgeSeparators` | Engine switches. |
| `sliderStyle` | `"track"` (every theme here): a slider opens as a dial scale. Each value stop is a tick: every step of the slider, or every 2nd / 5th / 10th… when that is more than 61, spread over 300°. See the slider hooks below. `"steps"` (default when absent): 16 value items on the ring. |
| `dynamicCenter` | Optional `{ childDistance, itemSpacing, childSize, gap, growth, minSize, maxSize, textRatio }` in px, mirroring the theme CSS. When set, a dynamic ring's center starts at `minSize` and grows `growth` px for each px the ring widens past `childDistance` (staying `gap` clear of the items, up to `maxSize`), the engine sets `--dynamic-center-size` on it, and the hovered item's text wraps into `size × textRatio`. |
| `previewBackground` | CSS background for the preview tool only; the app ignores it. |
| `slices` | Engine 2 (`engineVersion: 2`): the items are drawn as pieces of one object, cut live to each item's wedge by the dial's slice renderer (`Knobdeck/app/src/dial/overlay/slices.js`, which documents every field). Either material maps (`maps`: albedo / normal / roughness, lit per pixel with a bevel, a sunken field and joint shadows; `halo`) or painted art (`tile` / `tileHover`: one slice for a ring of `tileSpan` degrees, warped to fit). The open center gets `kd-sliced` while it's drawn, so the CSS can fall back to its own item look without it. |

**What the CSS can use**

- Node classes: `active` (the center), `child` (its ring), `parent` (the menu you came from),
  `grandchild` (items of a closed submenu: the engine hides them, so don't draw them as dots),
  `hovered`, `clicked`, `dragged`, `level-<n>`, `type-<root|submenu|button|…>`,
  `left/right/top/bottom`, `dynamic-menu` (a plugin-filled ring). The layer holding the icon also
  gets `kd-icon-layer`.
- Sliders: `slider-menu` (the slider; `kd-scale` too on a `"track"` theme), `slider-previewing`
  (while a value is hovered), and on its stops `slider-step`, `current` (nearest the live value),
  `filled` (up to the hovered or live value), `major` with `data-tick="<number>"` (a round value
  the scale should number). On a `"track"` theme the slider node also holds a `.kd-scale-plate`
  div (behind everything) for the theme to size and paint.
- Set on an open slider's node: `--slider-start-angle`, `--slider-end-angle`, `--slider-span`,
  `--slider-fill` (from the start to the hovered or current value; registered as an inherited
  `<angle>`, so it animates and a layer's `::before` can use it), `--slider-value` (the live
  value as a CSS string, for `content`) and `--slider-readout` (the hovered value, else the live
  one; the engine prints no center text for a scale's stops).
- The themes here share one "Sliders: a dial scale" block at the end of `theme.css`: ticks are the
  stops' `::before`, numbers their `::after`, the pointer and the readout the slider's `::after` /
  `::before`. A theme only sets the `--scale-*` sizes and colours above it and paints the plate.
  `filled`, `major`, the plate and `--slider-readout` need an app newer than 0.3.2; older ones show plain ticks.
- Set on an open dynamic ring's node (with `dynamicCenter`): `--dynamic-center-size`.
- Set on each node: `--dir-x`, `--dir-y` (unit direction), `--angle` (0deg = up, clockwise),
  `--sibling-count`, `--start-angle` / `--end-angle` (its wedge), `--parent-angle`.
- Set on layer divs of the center (animatable): `--pointer-angle`, `--hover-angle`,
  `--hovered-child-angle`. They're registered as non-inherited, so use them on the layer itself, not
  on a `::before`.
- Also styled: `.connector`, `.center-text`, `.selection-wedges`, `.wedge-separators .separator`.
- The dial window is transparent and `backdrop-filter` can't see the desktop behind it, so glass
  looks need enough tint to read on a busy wallpaper. Respect `prefers-reduced-motion`.

## Phone themes

The phone app has no CSS: its theme is colours, a cell look and a backdrop. Every theme here has
`themes/<id>/phone.json` and its art: `phone-bg.jpg`, plus `phone-bg-<preset>.jpg` for each preset
that changes the colours (the release adds `id`, `name`, `description`, `version` and turns every image
into a release URL with `imageSha256`; the phone downloads only the one it shows). Every theme has
background art; only the app's built-ins (Midnight, Daylight) are plain. The art is drawn by
`knobdeck-theme-tools/phone/theme-backgrounds.py`. Colours that get an opacity applied must be `#rrggbb`
(`colors.bg`, `text`, `accent`, `onBackground`, `cell.icon`); the others may be any CSS colour.

```json
{
  "format": 1,
  "mode": "dark",
  "colors": { "bg", "panel", "panelAlt", "text", "subtext", "faint", "accent", "onAccent",
              "onBackground?", "line?", "danger?" },
  "cell": { "fill", "emptyFill", "border", "emptyBorder", "borderWidth", "icon",
            "label?", "pressed?", "sliderFill?", "sliderThumb?", "font?": "mono",
            "weight?", "uppercase?", "extra?": { "borderRightWidth": 4 }, "blur?": "light|dark|clear",
            "radius?": { "factor", "min", "max" } },
  "background": { "base": "#000000", "image": "phone-bg.jpg",
                  "layers": [{ "type": "linear", "angle": 160, "stops": [[0, "#2e3036"], [1, "#111215", 1]] },
                             { "type": "radial", "cx": 0.5, "cy": 0, "r": 0.9, "stops": [[0, "#6ce39a", 0.16]] }],
                  "pattern?": { "type": "scanlines|grid|dots", "color": "#000000", "opacity": 0.35 } },
  "presets": { "<Name>": { "mode?", "colors?": {}, "cell?": {}, "background?": {} } }
}
```

- `cell.blur`: the blur sheet behind the cells, `light` or `dark` (default: `mode`) for a solid frosted cell, `clear`
  for see-through glass (faint blur, the `fill` does the tinting).
- `onBackground`: text straight on the backdrop (header, page dots); `line`: hairlines. `cell.radius`:
  the corner is `factor × cell size`, clamped to `min`..`max` px.
- The backdrop is the base colour, then the image (cover, 1080×2340, JPEG under ~250 KB, under a light
  scrim in `colors.bg`). Without an image (still downloading) the gradient layers and the pattern show
  instead, so keep them close to the image's colours. Stops are
  `[offset 0..1, colour, opacity = 1]`, angles CSS-style (0 = up).
- `presets` has one entry for every name in theme.json's `presets` (CI checks), merged over the theme
  when the PC picks that preset. A preset that changes the colours brings its own
  `"background": { "image": "phone-bg-<preset>.jpg" }`.

**Checklist before shipping a theme**

Render it in the real dial engine and look at every state: idle and hovered, an open submenu,
4 / 8 / 12 items, long labels, an open slider (at rest, with a value hovered, and a coarse 0–10 one),
and every preset (menu and slider). Then make its preview GIF (`previews/<id>.gif`) and write its
`phone.json`, checked on a phone (or the phone app's web build) with every preset. The maintainers'
preview and art tools live outside this repo; a contributor can send the theme and we render it.

Check the registry build locally: `node scripts/build-registry.mjs test` (needs `zip`), output in `out/`.

## License

The themes are CC0-1.0 (see `LICENSE`).
