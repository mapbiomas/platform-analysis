# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## What this repo is

Google Earth Engine (GEE) JavaScript scripts that reproduce the on-the-fly temporal LULC analyses offered by the MapBiomas Platform. There is no build system, package manager, linter or test suite: scripts are run by pasting them into the GEE Code Editor (code.earthengine.google.com), which provides the globals `ee` and `Map` and resolves `require('users/mapbiomas/modules:Palettes.js')`. Scripts cannot be executed locally with Node.

Documentation lives in the GitHub wiki (https://github.com/mapbiomas/platform-analysis/wiki, a separate git repo: `platform-analysis.wiki.git`): Home, one page per analysis (description, worked example with its figure, parameters, map layers), Figures and `_Sidebar`. The README stays short: repository description, a prominent wiki link, a table of analyses linking to the wiki pages and scripts, usage and layout. When adding, renaming or changing an analysis, update its wiki page, the sidebar and the README table.

## Structure

- `codes/analysis.js` — the original combined script with all seven pixel-history functions (age, frequency, number of classes, number of changes, stable, last year, accumulated) and their visualization layers. Comments here are in Portuguese.
- `codes/analysis_N_<name>.js` — standalone, self-contained versions of each analysis (English comments). Each one is meant to be copy-pasted alone, so shared setup (asset, `years`, `bandPrefix`, palettes) is intentionally duplicated in every file rather than imported.
- `codes/analysis_8_transitions.js` — different pattern: compares two years via map algebra (`start * 100 + end`, e.g. 3→39 = `339`) and selects transitions with `eq` / `remap`.

## Shared conventions

- Input: MapBiomas Brazil Collection 10.1 coverage asset (`projects/mapbiomas-public/assets/brazil/lulc/collection10_1/mapbiomas_brazil_collection10_1_coverage_v1`), one band per year named `classification_<YYYY>` for 1985–2024.
- Function signature pattern: `getX(image, targetClass, years, bandPrefix)`; band names are built server-side with `ee.String(bandPrefix).cat(ee.Number(year).format('%.0f'))`.
- `targetClass` uses MapBiomas legend codes (e.g. 3 Forest, 15 Pasture, 21 Mosaic of Uses, 39 Soybean). LULC layers use `Palettes.get('classification9')` with `min: 0, max: 69`; continuous metrics use a hand-defined palette.
- Outputs are masked with `.selfMask()` so zero/no-data pixels render transparent.
- When updating to a new collection or year range, change the asset path, the `years` array and any hard-coded band names / `max` values (e.g. `classification_2023` reference layer, last-year `max`) in every script, since nothing is shared.

## Figures

`docs/figures/*.png` (shown in the wiki through raw.githubusercontent.com URLs on `main`) are generated, not drawn: `python docs/figures/build_figures.py [overview|analysis_N_name ...]` runs every `codes/analysis_*.js` unchanged on four example pixels through `docs/figures/run_scripts.js` (Node `vm` with a one-pixel mock of `ee`/`Map`/`require`), then renders HTML to light/dark PNGs with headless Chrome. There is one overview figure (the example pixels) plus one figure per analysis, driven by the `ANALYSES` registry in `build_figures.py`.

- Adding a script: add its `ANALYSES` entry (the build fails if a script in `codes/` has none), a wiki page with the figure, a row in the README table, and keep the overview untouched unless the example pixels change.
- Each entry's `expected` pins the values its figure and the wiki page describe; if a script's output changes the build stops — update the story, the asserts and the wiki page together.
- If a script starts using an `ee` operation the mock doesn't implement, add it to `run_scripts.js` (unknown operations throw on purpose).
- Visual style follows `docs/figure-style.md` in the sibling `mapbiomas-pipeline` repo (origin/main).
