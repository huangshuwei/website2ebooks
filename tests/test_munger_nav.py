from pathlib import Path

import pytest

from website2ebooks.munger_nav import (
    MUNGER_INDEX_URL,
    MUNGER_READER_URL,
    is_munger_qa_index_href,
    parse_munger_chapters_from_html,
    parse_qa_chapter_refs_from_reader,
    should_skip_munger_nav_href,
)

FIXTURE_SIDEBAR = Path(__file__).parent / "fixtures" / "munger_sidebar_snippet.html"
FIXTURE_READER = Path(__file__).parent / "fixtures" / "munger_reader_two_chapters.html"


def test_should_skip_munger_qa_index() -> None:
    assert should_skip_munger_nav_href("/books/munger-qa/")
    assert not should_skip_munger_nav_href("/sources/1977年-蓝筹印花致股东信/")


def test_is_munger_qa_index_href() -> None:
    assert is_munger_qa_index_href("/books/munger-qa/")


@pytest.mark.skipif(not FIXTURE_READER.exists(), reason="reader fixture missing")
def test_parse_qa_chapter_refs_count() -> None:
    html_text = FIXTURE_READER.read_text(encoding="utf-8")
    refs = parse_qa_chapter_refs_from_reader(
        html_text,
        section_label="解读",
        group_label="其他",
    )
    assert len(refs) == 2
    assert refs[0].kind == "munger_qa"
    assert refs[0].url.startswith(MUNGER_READER_URL)
    assert "#chapter-" in refs[0].url


@pytest.mark.skipif(not FIXTURE_SIDEBAR.exists(), reason="sidebar fixture missing")
def test_parse_munger_sidebar_includes_qa_expansion() -> None:
    sidebar = FIXTURE_SIDEBAR.read_text(encoding="utf-8")
    reader = FIXTURE_READER.read_text(encoding="utf-8")
    chapters = parse_munger_chapters_from_html(
        sidebar,
        page_url=MUNGER_INDEX_URL,
        reader_html=reader,
    )
    assert len(chapters) >= 4
    assert chapters[0].title == "1977年 蓝筹印花致股东信"
    qa = [c for c in chapters if c.kind == "munger_qa"]
    assert len(qa) == 2
    assert qa[0].toc_path[0] == "解读"
    assert qa[0].toc_path[1] == "其他"
