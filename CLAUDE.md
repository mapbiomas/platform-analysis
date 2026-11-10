# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## What this repo is

Google Earth Engine (GEE) JavaScript scripts that reproduce the on-the-fly temporal LULC analyses offered by the MapBiomas Platform. There is no build system, package manager, linter or test suite: scripts are run by pasting them into the GEE Code Editor (code.earthengine.google.com), which provides the globals `ee` and `Map` and resolves `require('users/mapbiomas/modules:Palettes.js')`. The only local execution is the one-pixel mock used to build the figures (see Figures).

## Structure

- `codes/analysis_N_<name>.js` — one standalone script per analysis (English comments), numbered 1–10: age, frequency, number of classes, number of changes, stable, first year, last year, time since last occurrence, accumulated, transitions. Each is meant to be copy-pasted alone, so shared setup (asset, `years`, `bandPrefix`, palettes) is intentionally duplicated in every file rather than imported.
- `codes/analysis_10_transitions.js` — different pattern: compares two years via map algebra (`start * 100 + end`, e.g. 3→39 = `339`) and selects transitions with `eq` / `remap`.
- `codes/analysis.js` — the original combined script (Portuguese comments) with seven of the functions (age, frequency, number of classes, number of changes, stable, last year, accumulated); it has no first year or transitions and is not documented in the README/wiki.
- `docs/figures/` — figure generator and its PNG outputs. `docs/wiki/update_nav.py` — wiki navigation helper.
- README — kept short: description, prominent wiki link, a numbered table of analyses (wiki page + script), usage, layout. The table is the source of truth for the analysis order.

## Shared conventions

- Input: MapBiomas Brazil Collection 10.1 coverage asset (`projects/mapbiomas-public/assets/brazil/lulc/collection10_1/mapbiomas_brazil_collection10_1_coverage_v1`), one band per year named `classification_<YYYY>` for 1985–2024.
- Function signature pattern: `getX(image, targetClass, years, bandPrefix)`; band names are built server-side with `ee.String(bandPrefix).cat(ee.Number(year).format('%.0f'))`.
- `targetClass` uses MapBiomas legend codes (e.g. 3 Forest, 15 Pasture, 21 Mosaic of Uses, 39 Soybean). LULC layers use `Palettes.get('classification9')` with `min: 0, max: 69`; continuous metrics use a hand-defined palette.
- Outputs are masked with `.selfMask()` so zero/no-data pixels render transparent. Exception: time since last occurrence (8), where 0 means "still in the class" and must stay visible; only pixels never in the class are masked (inherited from the last-year mask). In `build_figures.py` captions for such analyses, test `v is None`, not falsiness.
- Year-valued reductions build one band per year as `eq(targetClass).multiply(year)`. `max` (last year) can ignore the zeros, but `min` (first year) cannot: there the per-year bands are `selfMask()`ed before reducing, otherwise 0 always wins.
- When updating to a new collection or year range, change the asset path, the `years` array and any hard-coded band names / `max` values (the `classification_YYYY` reference layer, the first/last-year color scale `max`) in every script, `analysis.js` included, since nothing is shared.

## Documentation (wiki)

Documentation lives in the GitHub wiki (https://github.com/mapbiomas/platform-analysis/wiki), a separate git repo (`https://github.com/mapbiomas/platform-analysis.wiki.git`) that must be cloned on its own: Home (intro, overview figure, numbered list, how to run), one page per analysis (description, worked example with its figure, parameters table, map layers table, previous/next navigation), Figures, `_Sidebar` and `_Footer`.

- Wiki pages show the figures through `raw.githubusercontent.com/.../main/docs/figures/...` URLs, so push `main` before pushing wiki changes that reference new figures.
- The previous/next links sit between `<!-- nav -->` and `<!-- /nav -->` at the end of each analysis page and are written by `python docs/wiki/update_nav.py <wiki clone>` from the README table order (it requires the table to be numbered 1..n). A wiki `_Footer` is the same on every page, so it only holds fixed links.

## Adding or renumbering an analysis

Everything keyed by number must move together:

1. Script `codes/analysis_N_<name>.js` (`git mv` when renumbering; keep related analyses adjacent, e.g. first year 6, last year 7 and time since last occurrence 8).
2. `ANALYSES` entry in `docs/figures/build_figures.py` (`id`, `num`, list order; the `TRANSITIONS` constant holds the transitions id) and any "analysis N" cross-references in entry texts and script header comments; rebuild the figures and delete the PNGs of old ids.
3. README table row.
4. Wiki: the page (its script link and figure URLs), the Home list and intro, `_Sidebar`, then run `update_nav.py`.

## Figures

`docs/figures/*.png` are generated, not drawn: `python docs/figures/build_figures.py [overview|analysis_N_name ...]` runs every `codes/analysis_*.js` unchanged on four example pixels through `docs/figures/run_scripts.js` (Node `vm` with a one-pixel mock of `ee`/`Map`/`require`), then renders HTML to light/dark PNGs with headless Chrome (needs Node and Chrome; `--html-only` skips rendering but still runs every assert). There is one overview figure (the example pixels, untouched unless the pixels change) plus one figure per analysis, driven by the `ANALYSES` registry.

- The build fails if a script in `codes/analysis_*` has no `ANALYSES` entry.
- Each entry's `expected` pins the values its figure and wiki page describe; if a script's output changes the build stops — update the story, the asserts and the wiki page together.
- If a script starts using an `ee` operation the mock doesn't implement, add it to `run_scripts.js` (unknown operations throw on purpose).
- Visual style and layout pitfalls follow `docs/figure-style.md` in the sibling `mapbiomas-pipeline` repo (origin/main); check every rendered figure in both themes before committing.
