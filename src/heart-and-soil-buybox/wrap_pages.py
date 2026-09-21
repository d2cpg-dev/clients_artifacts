# -*- coding: utf-8 -*-
"""Wrap the built artifact body into a standalone page for GitHub Pages.

The Artifact platform supplies <!DOCTYPE>, <html> and <head>, so build_v18.py emits a
fragment that starts at <title>. GitHub Pages does not, so this adds the document shell,
the crawler directives and the social description, and changes nothing else.

    python wrap_pages.py            # build_v18.py must have been run first
"""
import io, os, re, sys

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.abspath(os.path.join(HERE, "..", ".."))
SRC = os.path.join(HERE, "page_v18.html")
OUT = os.path.join(REPO, "heart-and-soil-buybox-review.html")

DESCRIPTION = ("Subscription take rate, plan mix and order value for Heart &amp; Soil since the "
               "Sep 3 2026 buy-box change. Prepared by DTCPG.")

frag = io.open(SRC, encoding="utf-8").read()

# the body begins at the first element after the stylesheets
marker = '<a class="skip"'
assert marker in frag, "body marker not found; did build_v18.py change the page shell?"
split = frag.index(marker)
head, body = frag[:split].rstrip(), frag[split:].rstrip()

assert "<title>" in head, "title missing from the head fragment"
assert head.count("<style>") == head.count("</style>"), "unbalanced style blocks"
assert "prefers-color-scheme" not in frag, "this page is light only; a dark block crept back in"

doc = (
    "<!DOCTYPE html>\n"
    '<html lang="en">\n'
    "<head>\n"
    '<meta charset="UTF-8">\n'
    '<meta name="viewport" content="width=device-width, initial-scale=1.0">\n'
    '<meta name="robots" content="noindex, nofollow, noarchive">\n'
    '<meta name="description" content="%s">\n'
    "%s\n"
    "</head>\n"
    "<body>\n"
    "%s\n"
    "</body>\n"
    "</html>\n" % (DESCRIPTION, head, body)
)

# the page must stay ASCII so it survives any transport
non_ascii = [c for c in doc if ord(c) > 127]
assert not non_ascii, "non-ascii characters present: %r" % sorted(set(non_ascii))[:8]

io.open(OUT, "w", encoding="utf-8", newline="\n").write(doc)
print("wrote %s (%d bytes)" % (os.path.relpath(OUT, REPO), len(doc)))
print("  head %d bytes, body %d bytes" % (len(head), len(body)))
for probe in ("Nothing was removed", "Let people pick one bottle", "noindex"):
    print("  contains %-32s %s" % (repr(probe), probe in doc))
