#!/usr/bin/env python3
"""Contract test for the standalone ebook reader Pages artifact."""
from pathlib import Path
import tempfile

from ebook_reader_deploy import publish


def main():
    with tempfile.TemporaryDirectory() as tmp:
        dist = Path(tmp)
        source = dist / "ebooks" / "read" / "index.html"
        source.parent.mkdir(parents=True)
        source.write_text(
            "var BOOK_KEY=/^[a-z0-9-]+(?:@[0-9a-z.\\-]+)?$/; "
            "if(BOOK_KEY.test(gb))render(vb,'/api/free?book='+encodeURIComponent(gb));",
            encoding="utf-8",
        )
        out = publish(dist)
        published = out.read_text(encoding="utf-8")
        assert "BOOK_KEY.test(gb)" in published
        assert "render(vb,'https://ebooks.bucklerfamily.estate/api/free?book='+encodeURIComponent(gb))" in published
        assert "render(vb,'/api/free?book='+encodeURIComponent(gb))" not in published
        assert "PDFJS='https://cdn.jsdelivr.net/npm/pdfjs-dist@3.11.174/build/'" in published
        assert "PDFJS='https://bucklerfamily.estate/_ext/cdn.jsdelivr.net/" not in published
        assert (dist / "reader-root-v132" / "index.html").is_file()
        assert "bucklerfamily.estate/ebooks/" in (dist / "reader-root-v132" / "index.html").read_text(encoding="utf-8")
    print("ebook_reader_deploy tests passed")


if __name__ == "__main__":
    main()
