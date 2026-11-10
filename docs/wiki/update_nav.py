# -*- coding: utf-8 -*-
"""
Writes the previous/next navigation at the end of each analysis page of the wiki.

The order comes from the analyses table in the README (one row per analysis, linking to its wiki
page), so adding a row there and running this script updates the neighbours of the new page too.
The navigation sits between <!-- nav --> and <!-- /nav --> markers and is replaced on every run;
a page without markers gets them appended.

GitHub wikis have a single _Footer for every page, which cannot know the current page, so the
per-page navigation has to live in the pages themselves.

Usage:
    git clone https://github.com/mapbiomas/platform-analysis.wiki.git
    python docs/wiki/update_nav.py path/to/platform-analysis.wiki
"""

import pathlib
import re
import sys

ROOT = pathlib.Path(__file__).resolve().parents[2]
WIKI_URL = "https://github.com/mapbiomas/platform-analysis/wiki/"
ROW = re.compile(r"^\| (\d+) \| \[([^\]]+)\]\(" + re.escape(WIKI_URL) + r"([^)]+)\) \|", re.M)
BLOCK = re.compile(r"\n*<!-- nav -->.*?<!-- /nav -->\n*", re.S)


def analyses():
    rows = ROW.findall((ROOT / "README.md").read_text())
    if not rows:
        sys.exit("no analyses found in the README table")
    nums = [int(n) for n, _, _ in rows]
    assert nums == list(range(1, len(nums) + 1)), f"README table is not numbered 1..n: {nums}"
    return [(int(n), title, page) for n, title, page in rows]


def nav(items, i):
    parts = []
    if i > 0:
        n, t, p = items[i - 1]
        parts.append(f"← [{n}. {t}]({p})")
    parts.append("[Home](Home)")
    if i < len(items) - 1:
        n, t, p = items[i + 1]
        parts.append(f"[{n}. {t}]({p}) →")
    return "<!-- nav -->\n\n---\n\n" + " · ".join(parts) + "\n\n<!-- /nav -->\n"


def main():
    if len(sys.argv) != 2:
        sys.exit(__doc__)
    wiki = pathlib.Path(sys.argv[1])
    items = analyses()
    for i, (_, _, page) in enumerate(items):
        path = wiki / f"{page}.md"
        if not path.exists():
            sys.exit(f"wiki page missing: {path.name}")
        text = BLOCK.sub("\n", path.read_text()).rstrip("\n")
        path.write_text(text + "\n\n" + nav(items, i))
        print(f"{path.name}: {nav(items, i).splitlines()[4]}")


if __name__ == "__main__":
    main()
