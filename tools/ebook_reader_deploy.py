#!/usr/bin/env python3
"""ebook_reader_deploy.py — publish the subdomain's standalone PDF reader from the root site build.

The root repository owns the composed ebook reader. The reader iframe runs on
ebooks.bucklerfamily.estate so its /api/free requests stay on the ebook-gate
Worker's origin. Publish that same built reader under a minimal Pages artifact;
never take the reader from the retired DATRO site.
— BucklerFamily.estate build
"""
from pathlib import Path
import shutil
import sys

VERSION = "1.0.0"
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
    target = dist / "ebooks-reader"
    reader = target / "read" / "index.html"
    reader.parent.mkdir(parents=True, exist_ok=True)
    shutil.copyfile(source, reader)
    (target / "index.html").write_text(REDIRECT, encoding="utf-8")
    print(f"ebook_reader_deploy v{VERSION}: published {reader} ({reader.stat().st_size} bytes)")
    return reader


if __name__ == "__main__":
    publish(sys.argv[1] if len(sys.argv) > 1 else "dist")
