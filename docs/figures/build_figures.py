# -*- coding: utf-8 -*-
"""
Builds the README figures of the on-the-fly analyses, in a light and a dark version:

  overview-{theme}.png         the four example pixels, 40 years each
  analysis_N_<name>-{theme}.png  one figure per script in codes/, on the same four pixels

The values are not drawn by hand: the pixels are run through the scripts in codes/, unchanged,
by run_scripts.js (Node, a one-pixel stand-in for `ee` and `Map`), and each figure shows the
layer the script adds to the map. EXPECTED in each analysis pins the story its figure tells, so
if a script changes the figure changes with it or the build stops.

To add an analysis: add its entry to ANALYSES (layer name, expected values, highlight, captions,
steps). The overview only changes if the example pixels change.

Style: docs/figure-style.md of mapbiomas-pipeline (same tokens and pieces as the deforestation
and secondary vegetation method figure).

Usage (from the repository root):
    python docs/figures/build_figures.py               # all figures
    python docs/figures/build_figures.py overview analysis_1_age
    python docs/figures/build_figures.py --html-only

Needs Node on the PATH, and Google Chrome (or Chromium) to render; set CHROME to override.
"""

import argparse
import html
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile

HERE = os.path.dirname(os.path.abspath(__file__))
RUNNER = os.path.join(HERE, "run_scripts.js")

YEARS = list(range(1985, 2025))
TARGET = 15
T_START, T_END = 2008, 2024  # analysis_10_transitions.js
TRANSITIONS = "analysis_10_transitions"

# ---------------------------------------------------------------------------
# Colors
# ---------------------------------------------------------------------------

# Official Collection 10.1 legend colors. Data colors do not change with the theme.
LULC = {
    3: ("#1f8d49", "Forest Formation"),
    15: ("#edde8e", "Pasture"),
    21: ("#ffefc3", "Mosaic of Uses"),
    39: ("#f5b3c8", "Soybean"),
}
DARK_CELLS = ("#1f8d49",)
TARGET_DOT = "#8a7a2e"

THEMES = {
    "light": {
        "bg": "#ffffff", "surface": "#f6f8fa", "card": "#ffffff", "border": "#d8dee4",
        "line": "#c6ced6", "text": "#1f2328", "muted": "#59636e", "faint": "#818b98",
        "accent": "#43798a", "accent_soft": "#e7f2f5", "accent_line": "#9cc9d6",
        "shadow": "0 10px 28px -16px rgba(16,40,50,.30)", "cell_stroke": "rgba(31,35,40,.18)",
        "warm": "rgba(31,35,40,.06)",
    },
    "dark": {
        "bg": "#0d1117", "surface": "#141a22", "card": "#171e27", "border": "#2c343e",
        "line": "#3a444f", "text": "#e6edf3", "muted": "#9aa4af", "faint": "#6e7781",
        "accent": "#75c7e0", "accent_soft": "#15292f", "accent_line": "#2c515d",
        "shadow": "0 10px 28px -16px rgba(0,0,0,.8)", "cell_stroke": "rgba(255,255,255,.16)",
        "warm": "rgba(255,255,255,.05)",
    },
}

# ---------------------------------------------------------------------------
# Example pixels
# ---------------------------------------------------------------------------


def series(*runs):
    out = []
    for cls, n in runs:
        out += [cls] * n
    assert len(out) == len(YEARS), len(out)
    return dict(zip(YEARS, out))


PIXELS = {
    "A": ("Rotation, back to pasture", series((3, 8), (15, 8), (21, 4), (15, 4), (39, 5), (15, 11))),
    "B": ("Forest that never changed", series((3, 40))),
    "C": ("Pasture abandoned to forest", series((3, 6), (15, 20), (3, 14))),
    "D": ("Forest cleared for soy", series((3, 32), (15, 2), (39, 6))),
}


def run_starts(px):
    """Indexes where a new run (block of equal consecutive classes) begins, after the first."""
    vals = [px[y] for y in YEARS]
    return [i for i in range(1, len(vals)) if vals[i] != vals[i - 1]]


def name(cls):
    return LULC[cls][1]


def target_years(px):
    return [y for y in YEARS if px[y] == TARGET]


def last_run(px):
    """Years of the run that ends in the last year."""
    out = []
    for y in reversed(YEARS):
        if px[y] != px[YEARS[-1]]:
            break
        out.append(y)
    return sorted(out)


def tcode(px):
    return px[T_START] * 100 + px[T_END]


# ---------------------------------------------------------------------------
# Analyses: one entry per script in codes/
# ---------------------------------------------------------------------------
# layers:   {key: layer name passed to Map.addLayer}; the first one is the figure's value
#           unless `value` overrides it
# expected: {pixel: value}, None = masked by selfMask (transparent on the map)
# keep:     (pixel, year) -> cell drawn at full opacity; marks: pixel -> years outlined
# caption:  (pixel, value) -> line under the value
# steps:    (title, code, text) in the order the script runs them


def _cap_age(p, v):
    px = PIXELS[p][1]
    return f"since {YEARS[-1] - v + 1}" if v else f"{name(px[YEARS[-1]])} in {YEARS[-1]}"


def _cap_freq(p, v):
    px = PIXELS[p][1]
    if not v:
        return "never pasture"
    blocks = sum(1 for i in run_starts(px) if px[YEARS[i]] == TARGET) + (px[YEARS[0]] == TARGET)
    return f"years in {blocks} blocks" if blocks > 1 else "years in one block"


def _cap_last(p, v):
    px = PIXELS[p][1]
    if not v:
        return "never pasture"
    if v == YEARS[-1]:
        return "still pasture"
    return f"{name(px[v + 1])} from {v + 1}"


def _cap_first(p, v):
    px = PIXELS[p][1]
    if not v:
        return "never pasture"
    if v == YEARS[0]:
        return "pasture from the start"
    return f"{name(px[v - 1])} until {v - 1}"


def _cap_since(p, v):
    # 0 is a real value here (still in the class), so test for None, not falsiness
    if v is None:
        return "never pasture"
    if v == 0:
        return f"still pasture in {YEARS[-1]}"
    return f"last pasture in {YEARS[-1] - v}"


def _since_years(p):
    """The last target year and the years after it: the span the analysis measures."""
    ty = target_years(PIXELS[p][1])
    return [y for y in YEARS if ty and y >= ty[-1]]


ANALYSES = [
    {
        "id": "analysis_1_age", "num": 1, "title": "Class <em>age</em>", "fn": "getClassAge",
        "layers": {"v": f"Class {TARGET} Age"},
        "lead": f"Consecutive years in the target class, counted back from {YEARS[-1]}. Any other class resets the "
                f"count, so only pixels that are still in the class in {YEARS[-1]} have an age.",
        "unit": "years",
        "expected": {"A": 11, "B": None, "C": None, "D": None},
        "keep": lambda p, y: PIXELS[p][1][YEARS[-1]] == TARGET and y in last_run(PIXELS[p][1]),
        "marks": lambda p: [last_run(PIXELS[p][1])[0]] if PIXELS[p][1][YEARS[-1]] == TARGET else [],
        "caption": _cap_age,
        "steps": [
            ("Mask the target class", f"image.eq({TARGET})", "1 in pasture years, 0 in the others"),
            ("Walk the years", "age = (age + 1) × mask", "<code>ee.List(years).iterate</code>: grows by one each pasture year, back to 0 otherwise"),
            ("Keep the last year", "selfMask()", f"the result is the age in {YEARS[-1]}; age 0 is transparent"),
        ],
        "note": "Pixel A was pasture for 23 years, but only the 11 since 2014 count: the soybean years broke the run.",
    },
    {
        "id": "analysis_2_frequency", "num": 2, "title": "Class <em>frequency</em>", "fn": "getClassFrequency",
        "layers": {"v": f"Class {TARGET} Frequency"},
        "lead": f"Number of years the pixel was in the target class between {YEARS[0]} and {YEARS[-1]}, consecutive or not.",
        "unit": "years",
        "expected": {"A": 23, "B": None, "C": 20, "D": 2},
        "keep": lambda p, y: PIXELS[p][1][y] == TARGET,
        "marks": lambda p: [],
        "caption": _cap_freq,
        "steps": [
            ("Mask the target class", f"image.eq({TARGET})", "1 in pasture years, 0 in the others"),
            ("Sum over the years", "reduce(ee.Reducer.sum())", "counts pasture years in any order"),
            ("Hide zero", "selfMask()", "pixels never in the class are transparent"),
        ],
        "note": "Pixel A has the highest frequency (23) but an age of 11: the class left and came back. "
                "Comparing frequency and age separates recurrent from consolidated use.",
    },
    {
        "id": "analysis_3_number_of_classes", "num": 3, "title": "Number of <em>classes</em>",
        "fn": "getNumberOfClasses",
        "layers": {"v": "Number of Classes"},
        "lead": f"How many different classes the pixel has had in {len(YEARS)} years. Repeated classes count once.",
        "unit": "classes",
        "expected": {"A": 4, "B": 1, "C": 2, "D": 3},
        "keep": lambda p, y: True,
        "marks": lambda p: sorted({min(y for y in YEARS if PIXELS[p][1][y] == c) for c in set(PIXELS[p][1].values())}),
        "caption": lambda p, v: " · ".join(str(c) for c in sorted(set(PIXELS[p][1].values()), key=lambda c: min(
            y for y in YEARS if PIXELS[p][1][y] == c))),
        "steps": [
            ("Select the annual bands", "image.select(bands)", f"<code>classification_{YEARS[0]}</code> … <code>{YEARS[-1]}</code>"),
            ("Count distinct values", "reduce(ee.Reducer.countDistinctNonNull())", "each class counts once, however many years it lasted"),
        ],
        "note": "Outlined: the first year of each class. Returning to a class does not add one: pixel C has "
                "2 classes, Forest and Pasture, and 2 changes (analysis 4).",
    },
    {
        "id": "analysis_4_number_of_changes", "num": 4, "title": "Number of <em>changes</em>",
        "fn": "getNumberOfChanges",
        "layers": {"v": "Number of Changes"},
        "lead": "Times the class changed from one year to the next. Leaving a class and returning to it counts twice.",
        "unit": "changes",
        "expected": {"A": 5, "B": None, "C": 2, "D": 2},
        "keep": lambda p, y: True,
        "marks": lambda p: [],
        "boundaries": True,
        "caption": lambda p, v: f"{(v or 0) + 1} runs − 1" if v else "1 run − 1 = 0",
        "steps": [
            ("Select the annual bands", "image.select(bands)", f"<code>classification_{YEARS[0]}</code> … <code>{YEARS[-1]}</code>"),
            ("Count runs", "reduce(ee.Reducer.countRuns())", "a run is a block of consecutive years with the same class"),
            ("Runs minus one", "subtract(1).selfMask()", "changes = runs − 1; pixels that never changed are transparent"),
        ],
        "note": "Each line marks a change. Pixel C (Forest → Pasture → Forest) has 2 changes and 2 classes; "
                "pixel A has 5 changes among 4 classes.",
    },
    {
        "id": "analysis_5_stable", "num": 5, "title": "<em>Stable</em> classes", "fn": "getStableClasses",
        "layers": {"v": "Stable Classes"},
        "lead": f"Pixels that kept the same class in every year from {YEARS[0]} to {YEARS[-1]}. They keep that class "
                "as value, drawn with the land cover palette; every other pixel is transparent.",
        "unit": "class",
        "expected": {"A": None, "B": 3, "C": None, "D": None},
        "keep": lambda p, y: len(set(PIXELS[p][1].values())) == 1,
        "marks": lambda p: [],
        "caption": lambda p, v: name(v) if v else f"{len(set(PIXELS[p][1].values()))} classes",
        "steps": [
            ("Count distinct classes", "getNumberOfClasses(…)", "as in analysis 3"),
            ("Keep where it is 1", "mask(numberOfClasses.eq(1))", "any change in any year removes the pixel"),
            ("Value of the last year", f"select('classification_{YEARS[-1]}')", "the class the pixel always had"),
        ],
        "note": "Only pixel B is stable. Pixel D was forest for 32 years, but two pasture years are enough to leave it out.",
    },
    {
        "id": "analysis_6_first_year", "num": 6, "title": "Class <em>first year</em>", "fn": "getClassFirstYear",
        "layers": {"v": f"Class {TARGET} First Year"},
        "lead": "The earliest year in which the pixel was in the target class. With the last year (analysis 7), it "
                "frames the period in which the class was present.",
        "unit": "",
        "expected": {"A": 1993, "B": None, "C": 1991, "D": 2017},
        "keep": lambda p, y: PIXELS[p][1][y] == TARGET,
        "marks": lambda p: target_years(PIXELS[p][1])[:1],
        "caption": _cap_first,
        "steps": [
            ("Year where in class", f"eq({TARGET}).multiply(year).selfMask()",
             "each band becomes its year in pasture years; the other years are masked, so their 0 cannot be the minimum"),
            ("Take the minimum", "reduce(ee.Reducer.min())", "the earliest pasture year; pixels never in the class stay masked"),
        ],
        "note": "Pixel C entered pasture in 1991 and pixel D only in 2017. With the last year (analysis 7), pixel C "
                "was pasture from 1991 to 2010; pixel A, from 1993 to 2024 with breaks.",
    },
    {
        "id": "analysis_7_last_year", "num": 7, "title": "Class <em>last year</em>", "fn": "getClassLastYear",
        "layers": {"v": f"Class {TARGET} Last Year"},
        "lead": "The most recent year in which the pixel was in the target class. It shows when a class was last "
                "seen where it no longer is.",
        "unit": "",
        "expected": {"A": 2024, "B": None, "C": 2010, "D": 2018},
        "keep": lambda p, y: PIXELS[p][1][y] == TARGET,
        "marks": lambda p: target_years(PIXELS[p][1])[-1:],
        "caption": _cap_last,
        "steps": [
            ("Year where in class", f"eq({TARGET}).multiply(year)", "each band becomes its year in pasture years, 0 in the others"),
            ("Take the maximum", "reduce(ee.Reducer.max())", "the latest pasture year"),
            ("Hide zero", "selfMask()", "pixels never in the class are transparent"),
        ],
        "note": "Pixel C left pasture in 2010 and pixel D in 2018. Pixel A is still pasture, so its last year is the "
                "last year of the series.",
    },
    {
        "id": "analysis_8_time_since_last", "num": 8, "title": "Time since the <em>last occurrence</em>",
        "fn": "getTimeSinceLastOccurrence",
        "layers": {"v": f"Class {TARGET} Years Since Last"},
        "lead": f"Years between the last year in the target class and {YEARS[-1]}: the last year (analysis 7) as "
                "elapsed time. 0 means the pixel is still in the class; pixels never in the class are transparent.",
        "unit": "years",
        "expected": {"A": 0, "B": None, "C": 14, "D": 6},
        "keep": lambda p, y: y in _since_years(p),
        "marks": lambda p: target_years(PIXELS[p][1])[-1:],
        "caption": _cap_since,
        "steps": [
            ("Last year in class", "getClassLastYear(…)", "as in analysis 7: the latest pasture year, masked where never pasture"),
            ("Subtract from the series end", "ee.Image(years[years.length - 1])<br>.subtract(lastYear)",
             f"0 if still in the class in {YEARS[-1]}. No <code>selfMask()</code>, so 0 stays visible; the mask of "
             "the last year carries over"),
        ],
        "note": "Pixel C left pasture 14 years ago and pixel D 6. Pixel A is still pasture: 0, shown on the map, "
                "unlike pixel B, which was never pasture and is transparent.",
    },
    {
        "id": "analysis_9_accumulated", "num": 9, "title": "<em>Accumulated</em> class", "fn": "getAccumulatedClass",
        "layers": {"v": f"Class {TARGET} Accumulated"},
        "lead": "Every pixel that was in the target class in at least one year: the total footprint of the class over "
                "the series, including areas that have since changed.",
        "unit": "class",
        "expected": {"A": TARGET, "B": None, "C": TARGET, "D": TARGET},
        "keep": lambda p, y: PIXELS[p][1][y] == TARGET,
        "marks": lambda p: [],
        "caption": lambda p, v: f"pasture in {len(target_years(PIXELS[p][1]))} years" if v else "never pasture",
        "steps": [
            ("Keep years in class", f"select(bands).mask(image.eq({TARGET}))", "only pasture years stay unmasked"),
            ("First value left", "reduce(ee.Reducer.firstNonNull())", f"the class itself, {TARGET}"),
        ],
        "note": "Pixel D enters the footprint with two pasture years; in the last year it is soybean.",
    },
    {
        "id": "analysis_10_transitions", "num": 10, "title": "<em>Transitions</em>",
        "fn": f"{T_START} × 100 + {T_END}",
        "layers": {"soy": f"forest_{T_START} to soy_{T_END}",
                   "regen": f"pasture_or_mosaic_{T_START} to forest_{T_END}"},
        # the script's layer names, without the years (the columns already show them), to fit one line
        "layer_labels": {"soy": "forest → soy", "regen": "pasture or mosaic → forest"},
        "value": lambda p: tcode(PIXELS[p][1]),
        "lead": f"The class in {T_START} and the class in {T_END} combined in one code: the first digits are the "
                f"{T_START} class, the last two the {T_END} class. Each layer selects the codes of one transition.",
        "unit": "code",
        "expected": {"A": 1515, "B": 303, "C": 1503, "D": 339},
        "expected_layers": {"soy": {"D"}, "regen": {"C"}},
        "keep": lambda p, y: y in (T_START, T_END),
        "marks": lambda p: [T_START, T_END],
        "columns": (T_START, T_END),
        "caption": None,  # filled from the layers, below
        "steps": [
            ("Two years", f"select('classification_{T_START}')<br>select('classification_{T_END}')", "one band each"),
            ("One code", "img0.multiply(100).add(img1)", f"3 → 39 gives 339; 15 → 3 gives 1503"),
            ("One layer per transition", "eq(339)<br>remap([1503, 2103], [1, 1])",
             "339: forest → soy. 1503 or 2103: pasture or mosaic → forest"),
        ],
        "note": "Only the two years matter: pixel D's pasture years (2017–2018) do not change its code. Pixel A "
                "(1515) and B (303) are in no layer.",
    }
]


def run_scripts():
    node = shutil.which("node")
    if not node:
        sys.exit("node not found: it runs the scripts on the example pixels")
    with tempfile.NamedTemporaryFile("w", suffix=".json", delete=False) as fh:
        json.dump({k: {str(y): c for y, c in px.items()} for k, (_, px) in PIXELS.items()}, fh)
        tmp = fh.name
    try:
        out = subprocess.run([node, RUNNER, tmp], capture_output=True, text=True, check=True).stdout
    finally:
        os.unlink(tmp)
    return json.loads(out)


def evaluate():
    raw = run_scripts()
    for a in ANALYSES:
        layers = {k: {p: raw[a["id"] + ".js"][p][n] for p in PIXELS} for k, n in a["layers"].items()}
        a["layer_values"] = layers
        if "value" in a:
            a["values"] = {p: a["value"](p) for p in PIXELS}
        else:
            a["values"] = layers["v"]
        assert a["values"] == a["expected"], f"{a['id']}: scripts give {a['values']}, the figure says {a['expected']}"
        for k, on in a.get("expected_layers", {}).items():
            got = {p for p, v in layers[k].items() if v}
            assert got == on, f"{a['id']} layer {k}: {got} != {on}"
    missing = {f[:-3] for f in raw} - {a["id"] for a in ANALYSES}
    assert not missing, f"scripts without a figure entry: {sorted(missing)}"

    tr = next(a for a in ANALYSES if a["id"] == TRANSITIONS)
    def cap_tr(p, v):
        for k in tr["layers"]:
            if tr["layer_values"][k][p]:
                return tr["layer_labels"][k]
        return "in no layer"
    tr["caption"] = cap_tr
    ch = next(a for a in ANALYSES if a["id"] == "analysis_4_number_of_changes")
    for p, (_, px) in PIXELS.items():
        assert len(run_starts(px)) == (ch["values"][p] or 0)


# ---------------------------------------------------------------------------
# Drawing
# ---------------------------------------------------------------------------


def esc(s):
    return html.escape(str(s), quote=True)


def fg(color):
    return "#ffffff" if color in DARK_CELLS else "#1f2328"


def series_svg(size, gap, row_h, keep=None, marks=None, boundaries=False, columns=(), dots=True):
    """All example pixels as rows of cells, with a year axis on top."""
    step = size + gap
    top = 34
    w = len(YEARS) * step - gap
    h = top + len(PIXELS) * row_h - (row_h - size) + 6
    pad = 4  # room for the outline of the first and last cells
    out = [f'<svg width="{w + 2 * pad}" height="{h}" viewBox="{-pad} 0 {w + 2 * pad} {h}" class="story" '
           f'style="margin-left:{-pad}px;margin-right:{-pad}px">']
    for y in columns:
        i = YEARS.index(y)
        out.append(
            f'<rect x="{i * step - 3}" y="{top - 8}" width="{size + 6}" height="{h - top + 6}" rx="7" fill="var(--warm)"/>'
        )
    for i, y in enumerate(YEARS):
        if y % 5 == 0 or y in columns or y == YEARS[-1]:
            bold = y in columns
            anchor = "start" if i == 0 else "end" if i == len(YEARS) - 1 else "middle"
            tx = 0 if i == 0 else w if i == len(YEARS) - 1 else i * step + size / 2
            out.append(
                f'<text x="{tx}" y="16" text-anchor="{anchor}" font-size="12" '
                f'font-weight="{700 if bold else 600}" fill="var({"--accent" if bold else "--muted"})">{y}</text>'
            )
            out.append(f'<path d="M{i * step + size / 2} 22 V27" stroke="var(--line)" stroke-width="1.4"/>')
    for r, (p, (_, px)) in enumerate(PIXELS.items()):
        y0 = top + r * row_h
        for i, y in enumerate(YEARS):
            c = LULC[px[y]][0]
            op = 1 if keep is None or keep(p, y) else 0.25
            out.append(
                f'<rect x="{i * step}" y="{y0}" width="{size}" height="{size}" rx="{max(2, size * .15):.1f}" '
                f'fill="{c}" stroke="var(--cell-stroke)" stroke-width="1" opacity="{op}"/>'
            )
            if dots and px[y] == TARGET:
                out.append(
                    f'<circle cx="{i * step + size / 2}" cy="{y0 + size / 2}" r="{size * .12:.1f}" '
                    f'fill="{TARGET_DOT}" opacity="{.55 * op:.2f}"/>'
                )
        if boundaries:
            for i in run_starts(px):
                x = i * step - gap / 2
                out.append(f'<path d="M{x} {y0 - 4} V{y0 + size + 4}" stroke="var(--accent)" stroke-width="2.4" stroke-linecap="round"/>')
        for y in (marks(p) if marks else []):
            i = YEARS.index(y)
            out.append(
                f'<rect x="{i * step - 2}" y="{y0 - 2}" width="{size + 4}" height="{size + 4}" rx="{max(3, size * .2):.1f}" '
                f'fill="none" stroke="var(--accent)" stroke-width="2.2"/>'
            )
    out.append("</svg>")
    return "".join(out)


def row_labels(row_h, top=34, size=None):
    return "".join(
        f'<div class="row-label" style="top:{top + r * row_h + (size - 27) / 2 if size else top + r * row_h}px">'
        f'<b>{k}</b><span>{esc(desc)}</span></div>'
        for r, (k, (desc, _)) in enumerate(PIXELS.items())
    )


def lulc_legend():
    return "".join(
        f'<span class="lg"><i style="background:{c}"></i>{esc(n)} ({k})</span>' for k, (c, n) in LULC.items()
    )


CSS = """
*{box-sizing:border-box;margin:0;padding:0}
html,body{background:var(--bg)}
body{font-family:'Open Sans',sans-serif;color:var(--text)}
#wrap{padding:44px 44px 36px;background:var(--bg)}
code{font-family:'SFMono-Regular',Menlo,Consolas,monospace;font-size:.88em;background:var(--accent-soft);color:var(--accent);padding:1px 5px;border-radius:4px}
.over{font-size:13px;font-weight:700;letter-spacing:.22em;text-transform:uppercase;color:var(--accent)}
h1{font-family:'Montserrat','Open Sans',sans-serif;font-size:34px;font-weight:700;line-height:1.2;margin-top:8px;letter-spacing:-.01em}
h1 em{font-style:normal;color:var(--accent)}
.lead{font-size:16px;line-height:1.55;color:var(--muted);margin-top:10px;max-width:1120px}
.section{margin-top:30px}
.shdr{display:flex;align-items:baseline;gap:14px;margin-bottom:14px}
.shdr h2{font-family:'Montserrat','Open Sans',sans-serif;font-size:19px;font-weight:700}
.shdr span{font-size:13.5px;color:var(--muted)}
.panel{background:var(--surface);border:1px solid var(--border);border-radius:18px;padding:22px 24px 18px}
.story-row{display:flex;align-items:flex-start;gap:20px}
.story-wrap{position:relative;padding-left:258px}
.row-labels{position:absolute;left:0;top:0}
.row-label{position:absolute;left:0;width:250px;display:flex;align-items:center;gap:10px;height:27px;font-size:13px;color:var(--muted);white-space:nowrap}
.row-label b{width:27px;height:27px;border-radius:8px;background:var(--accent-soft);color:var(--accent);display:grid;place-items:center;font-size:13px}
.story text{font-family:'Open Sans',sans-serif}
.results{position:relative;flex:none;width:236px}
.res{position:absolute;left:0;right:0;border:1px solid var(--accent-line);background:var(--card);border-radius:10px;padding:5px 12px;display:flex;align-items:center;justify-content:space-between;gap:10px}
.res .val{display:flex;align-items:baseline;gap:6px}
.res b{font-size:18px;font-variant-numeric:tabular-nums;color:var(--text)}
.res u{text-decoration:none;font-size:11.5px;color:var(--muted)}
.res span{font-size:11.5px;color:var(--muted);white-space:nowrap;text-align:right}
.res.off{border-color:var(--border);background:transparent}
.res.off b{color:var(--faint);font-weight:600}
.res-head{position:absolute;top:4px;left:0;font-size:12px;font-weight:700;color:var(--accent)}
.story-foot{display:flex;justify-content:space-between;align-items:center;margin-top:10px;gap:20px}
.note{font-size:12.5px;color:var(--muted)}
.note b{color:var(--text)}
.note i{display:inline-block;width:14px;height:14px;border-radius:4px;background:var(--warm);border:1px solid var(--line);vertical-align:-2px;margin-right:6px}
.dot{display:inline-block;width:7px;height:7px;border-radius:50%;background:#8a7a2e;opacity:.55;margin:0 6px 1px 0}
.callout{margin-top:14px;font-size:13.5px;line-height:1.5;color:var(--text);border-left:3px solid var(--accent);padding:2px 0 2px 12px}
.flow{display:grid;gap:30px}
.stage{background:var(--card);border:1px solid var(--border);border-radius:16px;box-shadow:var(--shadow);padding:16px 18px;position:relative}
.stage .bar{position:absolute;left:16px;right:16px;top:-1px;height:4px;border-radius:0 0 4px 4px;background:linear-gradient(90deg,var(--accent),#5bcf20)}
.stage:not(:last-child)::after{content:'→';position:absolute;right:-24px;top:50%;transform:translateY(-50%);color:var(--accent);font-weight:700;font-size:20px}
.shead{display:flex;gap:11px;align-items:center}
.num{flex:none;width:32px;height:32px;border-radius:10px;background:var(--accent-soft);color:var(--accent);font-weight:700;font-size:13.5px;display:grid;place-items:center}
.stitle{font-size:15px;font-weight:700}
.scode{margin-top:12px;font-family:'SFMono-Regular',Menlo,Consolas,monospace;font-size:12.5px;line-height:1.5;color:var(--accent);background:var(--accent-soft);border:1px solid var(--accent-line);border-radius:8px;padding:6px 10px}
.stext{margin-top:9px;font-size:12.8px;line-height:1.45;color:var(--muted)}
.lg{display:inline-flex;align-items:center;gap:7px;font-size:12.5px;color:var(--muted);margin-left:16px}
.lg i{width:14px;height:14px;border-radius:4px;border:1px solid var(--cell-stroke);display:inline-block}
.foot{margin-top:24px;padding-top:14px;border-top:1px solid var(--border);display:flex;justify-content:space-between;align-items:center;gap:24px}
.src{font-size:12px;color:var(--faint);line-height:1.5}
"""


def page(theme, width, body):
    t = THEMES[theme]
    css_vars = "".join(f"--{k.replace('_', '-')}:{v};" for k, v in t.items())
    return f'''<!doctype html>
<html lang="en"><head><meta charset="utf-8"><title>figure ({theme})</title>
<link rel="preconnect" href="https://fonts.googleapis.com">
<link href="https://fonts.googleapis.com/css2?family=Montserrat:wght@600;700&family=Open+Sans:wght@400;600;700&display=block" rel="stylesheet">
<style>:root{{{css_vars}}}{CSS}body,#wrap{{width:{width}px}}</style></head>
<body><div id="wrap">{body}</div>
<script>
document.fonts.ready.then(() => {{
  document.title = 'H=' + Math.ceil(document.getElementById('wrap').getBoundingClientRect().height);
}});
</script>
</body></html>'''


SOURCE_NOTE = ("run unchanged on the example pixels by <code>docs/figures/run_scripts.js</code>, a one-pixel "
               "stand-in for <code>ee</code> and <code>Map</code>")

# --- overview -------------------------------------------------------------------------------

OVERVIEW_WIDTH = 1600


def build_overview(theme):
    size, gap, row_h = 27, 3, 46
    body = f'''
  <div class="over">MapBiomas Brazil · Collection 10.1 · {YEARS[0]}–{YEARS[-1]}</div>
  <h1>Four pixels, <em>{len(YEARS)} years</em> of land cover</h1>
  <p class="lead">Each pixel of the coverage asset holds one class per year, in bands <code>classification_{YEARS[0]}</code> to
  <code>classification_{YEARS[-1]}</code>. The analyses in this repository read that series pixel by pixel. The figure of each
  analysis runs its script on these four pixels, with Pasture ({TARGET}) as the target class.</p>
  <div class="section panel">
    <div class="story-wrap"><div class="row-labels">{row_labels(row_h)}</div>{series_svg(size, gap, row_h)}</div>
    <div class="story-foot">
      <div class="note"><span class="dot"></span>target class (Pasture, {TARGET})</div>
      <div>{lulc_legend()}</div>
    </div>
  </div>
  <div class="src" style="margin-top:14px">Example series: <code>PIXELS</code> in <code>docs/figures/build_figures.py</code>.</div>'''
    return page(theme, OVERVIEW_WIDTH, body)


# --- one analysis -----------------------------------------------------------------------------

ANALYSIS_WIDTH = 1600


def build_analysis(a, theme):
    size, gap, row_h = 21, 2.3, 50
    top = 34
    res = []
    for r, p in enumerate(PIXELS):
        v = a["values"][p]
        masked = v is None or (a["id"] == TRANSITIONS and a["caption"](p, v) == "in no layer")
        shown = "—" if v is None else v
        unit = "" if v is None or not a["unit"] or a["unit"] in ("class", "code") else a["unit"]
        if v == 1:
            unit = {"years": "year", "classes": "class", "changes": "change"}.get(unit, unit)
        res.append(
            f'<div class="res{" off" if masked else ""}" style="top:{top + r * row_h - 6}px;height:{size + 12}px">'
            f'<div class="val"><b>{esc(shown)}</b><u>{esc(unit)}</u></div><span>{esc(a["caption"](p, v))}</span></div>'
        )
    svg = series_svg(size, gap, row_h, keep=a["keep"], marks=a["marks"], boundaries=a.get("boundaries", False),
                     columns=a.get("columns", ()))
    steps = "".join(
        f'<div class="stage"><div class="bar"></div><div class="shead"><span class="num">{i:02d}</span>'
        f'<div class="stitle">{t}</div></div><div class="scode">{code}</div><div class="stext">{text}</div></div>'
        for i, (t, code, text) in enumerate(a["steps"], 1)
    )
    n = len(a["steps"])
    body = f'''
  <div class="over">On-the-fly analysis {a["num"]} · codes/{a["id"]}.js</div>
  <h1>{a["title"]}</h1>
  <p class="lead">{a["lead"]}</p>
  <div class="section panel">
    <div class="shdr"><h2>The four example pixels</h2><span>target class Pasture ({TARGET}) · highlighted: the years the
    analysis uses</span></div>
    <div class="story-row">
      <div class="story-wrap"><div class="row-labels">{row_labels(row_h, top, size)}</div>{svg}</div>
      <div class="results" style="height:{top + len(PIXELS) * row_h}px"><div class="res-head">layer value</div>{"".join(res)}</div>
    </div>
    <div class="callout">{a["note"]}</div>
  </div>
  <div class="section">
    <div class="shdr"><h2>How the script computes it</h2><span><code>{esc(a["fn"])}</code> in <code>codes/{a["id"]}.js</code></span></div>
    <div class="flow" style="grid-template-columns:repeat({n},minmax(0,1fr))">{steps}</div>
  </div>
  <div class="foot">
    <div class="note"><b>—</b> masked by <code>selfMask()</code>: transparent on the map</div>
    <div>{lulc_legend()}</div>
  </div>
  <div class="src" style="margin-top:10px">Source: <code>codes/{a["id"]}.js</code>, {SOURCE_NOTE}; each value is the layer the
  script adds to the map.</div>'''
    return page(theme, ANALYSIS_WIDTH, body)


# ---------------------------------------------------------------------------
# Rendering
# ---------------------------------------------------------------------------


def find_chrome():
    mac = "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome"
    for c in [os.environ.get("CHROME"), "google-chrome", "chromium", "chromium-browser", "google-chrome-stable", mac]:
        if c and (shutil.which(c) or os.path.exists(c)):
            return shutil.which(c) or c
    sys.exit("Chrome/Chromium not found; set CHROME")


def render(html_path, png_path, chrome, width):
    url = "file://" + html_path
    common = [chrome, "--headless=new", "--disable-gpu", "--hide-scrollbars",
              "--virtual-time-budget=8000", f"--window-size={width},4000"]
    dom = subprocess.run(common + ["--dump-dom", url], capture_output=True, text=True, check=True).stdout
    m = re.search(r"<title>H=(\d+)</title>", dom)
    if not m:
        sys.exit("could not measure the page height (fonts did not load?)")
    height = int(m.group(1))
    subprocess.run(
        [chrome, "--headless=new", "--disable-gpu", "--hide-scrollbars", "--virtual-time-budget=8000",
         "--force-device-scale-factor=2", f"--window-size={width},{height}",
         f"--screenshot={png_path}", url],
        check=True, capture_output=True,
    )
    return height


def main():
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    ap.add_argument("figures", nargs="*", help="overview and/or analysis ids (default: all)")
    ap.add_argument("--html-only", action="store_true")
    ap.add_argument("--out", default=HERE)
    args = ap.parse_args()

    evaluate()
    figures = {"overview": (build_overview, OVERVIEW_WIDTH)}
    for a in ANALYSES:
        figures[a["id"]] = ((lambda th, a=a: build_analysis(a, th)), ANALYSIS_WIDTH)
    wanted = args.figures or list(figures)
    unknown = set(wanted) - set(figures)
    if unknown:
        sys.exit(f"unknown figures: {sorted(unknown)}; choose from {list(figures)}")

    chrome = None if args.html_only else find_chrome()
    with tempfile.TemporaryDirectory() as tmp:
        for fig in wanted:
            build, width = figures[fig]
            for theme in THEMES:
                html_path = os.path.join(args.out if args.html_only else tmp, f"{fig}-{theme}.html")
                with open(html_path, "w", encoding="utf-8") as fh:
                    fh.write(build(theme))
                if chrome:
                    png = os.path.join(args.out, f"{fig}-{theme}.png")
                    h = render(os.path.abspath(html_path), png, chrome, width)
                    print(f"{fig}-{theme}.png ({width * 2}×{h * 2})")
                else:
                    print(html_path)


if __name__ == "__main__":
    main()
