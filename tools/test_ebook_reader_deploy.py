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
        assert out.read_text(encoding="utf-8") == source.read_text(encoding="utf-8")
        assert (dist / "ebooks-reader" / "index.html").is_file()
        assert "bucklerfamily.estate/ebooks/" in (dist / "ebooks-reader" / "index.html").read_text(encoding="utf-8")
    print("ebook_reader_deploy tests passed")


if __name__ == "__main__":
    main()
