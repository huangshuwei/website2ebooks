from pathlib import Path

import pytest
from ebooklib import epub

from website2ebooks.munger_nav import (
    MUNGER_INDEX_URL,
    MUNGER_QA_TOC_GROUP,
    MUNGER_READER_URL,
    is_munger_qa_index_href,
    parse_munger_chapters_from_html,
    parse_qa_chapter_refs_from_reader,
    should_skip_munger_nav_href,
)
from website2ebooks.toc_page import build_nested_book_toc, chapter_toc_section

FIXTURE_SIDEBAR = Path(__file__).parent / "fixtures" / "munger_sidebar_snippet.html"
FIXTURE_READER = Path(__file__).parent / "fixtures" / "munger_reader_two_chapters.html"


def test_should_skip_munger_qa_index() -> None:
    assert should_skip_munger_nav_href("/books/munger-qa/")
    assert not should_skip_munger_nav_href("/sources/1977年-蓝筹印花致股东信/")


def test_should_skip_thinking_grids() -> None:
    assert should_skip_munger_nav_href("/thinking-grids/")
    assert should_skip_munger_nav_href("https://munger.ayaseeri.com/thinking-grids/")


def test_is_munger_qa_index_href() -> None:
    assert is_munger_qa_index_href("/books/munger-qa/")


@pytest.mark.skipif(not FIXTURE_READER.exists(), reason="reader fixture missing")
def test_parse_qa_chapter_refs_count() -> None:
    html_text = FIXTURE_READER.read_text(encoding="utf-8")
    refs = parse_qa_chapter_refs_from_reader(html_text)
    assert len(refs) == 2
    assert refs[0].kind == "munger_qa"
    assert refs[0].url.startswith(MUNGER_READER_URL)
    assert "#chapter-" in refs[0].url
    assert refs[0].toc_path == (MUNGER_QA_TOC_GROUP, refs[0].title)


@pytest.mark.skipif(not FIXTURE_SIDEBAR.exists(), reason="sidebar fixture missing")
def test_parse_munger_sidebar_includes_qa_expansion() -> None:
    sidebar = FIXTURE_SIDEBAR.read_text(encoding="utf-8")
    reader = FIXTURE_READER.read_text(encoding="utf-8")
    chapters = parse_munger_chapters_from_html(
        sidebar,
        page_url=MUNGER_INDEX_URL,
        reader_html=reader,
    )
    assert len(chapters) >= 5
    assert chapters[0].title == "1977年 蓝筹印花致股东信"
    assert chapters[0].toc_path == ("股东会与股东信", "1977年 蓝筹印花致股东信")
    qa = [c for c in chapters if c.kind == "munger_qa"]
    assert len(qa) == 2
    assert qa[0].toc_path[0] == MUNGER_QA_TOC_GROUP


@pytest.mark.skipif(not FIXTURE_SIDEBAR.exists(), reason="sidebar fixture missing")
def test_munger_fixture_toc_sections_exclude_h2_labels() -> None:
    sidebar = FIXTURE_SIDEBAR.read_text(encoding="utf-8")
    reader = FIXTURE_READER.read_text(encoding="utf-8")
    chapters = parse_munger_chapters_from_html(
        sidebar,
        page_url=MUNGER_INDEX_URL,
        reader_html=reader,
    )
    sections = {chapter_toc_section(ch) for ch in chapters}
    assert "原文" not in sections
    assert "解读" not in sections
    assert "股东会与股东信" in sections
    assert "投资原则" in sections
    assert MUNGER_QA_TOC_GROUP in sections


@pytest.mark.skipif(not FIXTURE_SIDEBAR.exists(), reason="sidebar fixture missing")
def test_munger_fixture_nested_toc_top_level() -> None:
    sidebar = FIXTURE_SIDEBAR.read_text(encoding="utf-8")
    reader = FIXTURE_READER.read_text(encoding="utf-8")
    chapters = parse_munger_chapters_from_html(
        sidebar,
        page_url=MUNGER_INDEX_URL,
        reader_html=reader,
    )
    chs = [
        epub.EpubHtml(
            title=c.title, file_name=f"Text/chapter_{i:03d}.xhtml", lang="zh-CN"
        )
        for i, c in enumerate(chapters, start=1)
    ]
    toc = build_nested_book_toc(chapters, chs)
    top_titles = {item[0].title for item in toc if isinstance(item, tuple)}
    assert "原文" not in top_titles
    assert "解读" not in top_titles
