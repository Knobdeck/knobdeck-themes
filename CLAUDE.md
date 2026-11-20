# KnobDeck themes — working rules

Dial themes served to the KnobDeck app through GitHub Releases and the app site's registry (see README.md).

## Rule 1: a change to a theme bumps its version

Any change to `themes/<id>/` needs a new `version` in `themes/<id>/theme.json`
(semver; absent means `1.0.0`). The app compares versions to offer an Update, so an unbumped change never reaches users.
Preview GIFs are the exception: the registry links `previews/<id>.gif` by raw GitHub URL, so a new GIF is live as soon as it is on master.

## Rule 2: update `index.json` with the new version

Put the same version in `index.json`. CI fails if `index.json` and `theme.json` disagree. The release workflow
rebuilds a theme only when its `index.json` version differs from the previous release's `registry.json`; any other
theme's zip is copied over from that release unchanged. So without the bump, your change is not published.

New theme: add `themes/<id>/`, `previews/<id>.gif` and an `index.json` entry. The release workflow then tells
the `knobdeck-registry` catalog (a `theme-released` dispatch) to rebuild, so the app sees it without a manual step.

## Rule 3: every theme is original and checked

Ship only KnobDeck's own themes (CC0-1.0, `"author": "KnobDeck"` unless a contributor made it). Before
shipping, render it with `node preview/preview.mjs check <id>` and `presets <id>` (run from
`../knobdeck-theme-tools`) and look at every state; regenerate the GIF with `gif <id>`. README.md lists what the theme CSS can use.

## Rule 4: this repo holds themes only

Only what ships or what CI needs lives here: `themes/`, `previews/`, `index.json`, `scripts/build-registry.mjs`,
the workflow and the docs. Making-of tools (preview renderer, blueprint and cutter, Blender scripts, reference
images) live in the local workspace folder `../knobdeck-theme-tools`, never in this repo.
