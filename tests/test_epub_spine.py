import tempfile
import zipfile
from pathlib import Path

from website2ebooks.article import make_stub_chapter
from website2ebooks.epub_export import build_epub
from website2ebooks.nav import ChapterRef


def test_epub_has_no_toc_xhtml_and_chapter_h1() -> None:
    chapters = [
        ChapterRef("能力圈", "https://example.com/a/", ("巴菲特问答录", "能力圈")),
        ChapterRef("企业价值", "https://example.com/b/", ("巴菲特问答录", "企业价值")),
    ]
    parsed = [make_stub_chapter(c.title) for c in chapters]
    with tempfile.TemporaryDirectory() as tmp:
        out = Path(tmp) / "test.epub"
        build_epub(chapters, parsed, out)
        with zipfile.ZipFile(out) as zf:
            names = zf.namelist()
            assert not any("toc.xhtml" in n for n in names)
            ch1 = next(n for n in names if "chapter_001" in n and n.endswith(".xhtml"))
            body = zf.read(ch1).decode("utf-8")
            assert 'class="chapter-title"' in body
            assert "能力圈" in body
            assert "nav.xhtml" not in body
