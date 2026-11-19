#!/usr/bin/env python3
"""ebook_reader_deploy.py — publish the subdomain's standalone PDF reader from the root site build.

The root repository owns the composed ebook reader. The reader iframe runs on
ebooks.bucklerfamily.estate so its /api/free requests stay on the ebook-gate
Worker's origin. Publish that same built reader under a neutral, non-theme Pages path;
never take the reader from the retired DATRO site.
— BucklerFamily.estate build
"""
from pathlib import Path
import shutil
import sys

VERSION = "1.0.4"
REDIRECT = """<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="robots" content="noindex">
<meta http-equiv="refresh" content="0;url=https://bucklerfamily.estate/ebooks/">
<title>E-book reader</title>
</head>
<body><p><a href="https://bucklerfamily.estate/ebooks/">Open the E-book Shelf</a></p>
<script>location.replace("https://bucklerfamily.estate/ebooks/");</script>
</body>
</html>
"""


def publish(dist):
    dist = Path(dist)
    source = dist / "ebooks" / "read" / "index.html"
    if not source.is_file():
        raise FileNotFoundError(f"assembled ebook reader is missing: {source}")
    html = source.read_text(encoding="utf-8", errors="strict")
    required = (
        "var BOOK_KEY=/",
        "BOOK_KEY.test(gb)",
        "render(vb,'/api/free?book='+encodeURIComponent(gb))",
    )
    missing = [item for item in required if item not in html]
    if missing:
        raise ValueError("assembled reader does not accept and render bare book keys: " + ", ".join(missing))
    target = dist / "reader-root-v132"
    reader = target / "read" / "index.html"
    reader.parent.mkdir(parents=True, exist_ok=True)
    # The shared runtime prefixes relative /api paths with the current theme.
    # Keep the free-PDF request explicitly same-origin with the reader iframe,
    # so it reaches the existing ebooks.bucklerfamily.estate/api/* Worker.
    relative_api = "render(vb,'/api/free?book='+encodeURIComponent(gb))"
    absolute_api = "render(vb,'https://ebooks.bucklerfamily.estate/api/free?book='+encodeURIComponent(gb))"
    vendored_pdfjs = "https://cedwyn.bucklerfamily.estate/_ext/cdn.jsdelivr.net/npm/pdfjs-dist@3.11.174/build/"
    direct_pdfjs = "https://cdn.jsdelivr.net/npm/pdfjs-dist@3.11.174/build/"
    if relative_api not in html:
        raise ValueError("assembled reader is missing its expected relative free-PDF request")
    if vendored_pdfjs not in html:
        raise ValueError("assembled reader is missing the vendored PDF.js URL")
    html = html.replace(relative_api, absolute_api).replace(vendored_pdfjs, direct_pdfjs)
    reader.write_text(html, encoding="utf-8")
    (target / "index.html").write_text(REDIRECT, encoding="utf-8")
    print(f"ebook_reader_deploy v{VERSION}: published {reader} ({reader.stat().st_size} bytes)")
    return reader


if __name__ == "__main__":
    publish(sys.argv[1] if len(sys.argv) > 1 else "dist")
