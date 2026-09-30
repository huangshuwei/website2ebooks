from pathlib import Path

import pytest
from ebooklib import epub

from website2ebooks.nav import parse_chapters_from_html
from website2ebooks.toc_page import build_nested_book_toc

FIXTURE = Path(__file__).parent / "fixtures" / "nav_index.html"


@pytest.mark.skipif(not FIXTURE.exists(), reason="nav fixture not present")
def test_toc_path_two_levels_without_menu_head() -> None:
    chapters = parse_chapters_from_html(FIXTURE.read_text(encoding="utf-8"))
    assert chapters
    first = chapters[0]
    assert "专题" not in first.toc_path
    assert "原文" not in first.toc_path
    assert "解读" not in first.toc_path
    assert len(first.toc_path) == 2
    assert first.toc_path[0] == "巴菲特问答录"
    assert first.title == "能力圈"


def test_nested_book_toc_groups_in_order_without_toc_page() -> None:
    from website2ebooks.nav import ChapterRef

    chapters = [
        ChapterRef("A", "https://example.com/1/", ("组一", "A")),
        ChapterRef("B", "https://example.com/2/", ("组一", "B")),
        ChapterRef("C", "https://example.com/3/", ("组二", "C")),
    ]
    chs = [
        epub.EpubHtml(title=c.title, file_name=f"Text/chapter_{i:03d}.xhtml", lang="zh-CN")
        for i, c in enumerate(chapters, start=1)
    ]
    nested = build_nested_book_toc(chapters, chs)
    assert len(nested) == 2
    assert nested[0][0].title == "组一"
    assert len(nested[0][1]) == 2
    assert nested[1][0].title == "组二"
