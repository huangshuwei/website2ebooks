from pathlib import Path

import pytest

from website2ebooks.munger_nav import MUNGER_INDEX_URL, parse_munger_chapters_from_html
from website2ebooks.nav import (
    ChapterRef,
    indices_for_named_sections,
    indices_for_one_per_toc_section,
    parse_chapters_from_html,
)
from website2ebooks.toc_page import chapter_toc_section

FIXTURE = Path(__file__).parent / "fixtures" / "nav_index.html"
MUNGER_SIDEBAR = Path(__file__).parent / "fixtures" / "munger_sidebar_snippet.html"
MUNGER_READER = Path(__file__).parent / "fixtures" / "munger_reader_two_chapters.html"


def test_chapter_toc_section_matches_toc_path() -> None:
    ch = ChapterRef("A", "https://example.com/1/", ("组一", "A"))
    assert chapter_toc_section(ch) == "组一"
    flat = ChapterRef("B", "https://example.com/2/", ("B",))
    assert chapter_toc_section(flat) == ""


def test_indices_preferred_title_in_section() -> None:
    chapters = [
        ChapterRef("思维格栅", "https://example.com/grids/", ("其他", "思维格栅")),
        ChapterRef("不可为清单", "https://example.com/stop/", ("其他", "不可为清单")),
        ChapterRef("探索智慧", "https://example.com/wisdom/", ("其他", "探索智慧")),
    ]
    assert indices_for_one_per_toc_section(
        chapters, preferred_title_by_section={"其他": "探索智慧"}
    ) == frozenset({3})


def test_indices_for_named_sections() -> None:
    chapters = [
        ChapterRef("A", "https://example.com/1/", ("组一", "A")),
        ChapterRef("B", "https://example.com/2/", ("组一", "B")),
        ChapterRef("C", "https://example.com/3/", ("组二", "C")),
    ]
    assert indices_for_named_sections(chapters, ["组二", "组一"]) == frozenset({3, 1})
    assert indices_for_named_sections(chapters, ["missing"]) == frozenset()


@pytest.mark.skipif(
    not MUNGER_SIDEBAR.exists() or not MUNGER_READER.exists(),
    reason="munger fixtures missing",
)
def test_indices_for_named_sections_munger_fixture() -> None:
    chapters = parse_munger_chapters_from_html(
        MUNGER_SIDEBAR.read_text(encoding="utf-8"),
        page_url=MUNGER_INDEX_URL,
        reader_html=MUNGER_READER.read_text(encoding="utf-8"),
    )
    indices = indices_for_named_sections(
        chapters, ["股东会与股东信", "投资原则"]
    )
    assert len(indices) == 2
    for i in indices:
        ch = chapters[i - 1]
        assert chapter_toc_section(ch) in ("股东会与股东信", "投资原则")
    assert chapters[min(indices) - 1].toc_path[0] == "股东会与股东信"


def test_indices_one_per_toc_section() -> None:
    chapters = [
        ChapterRef("A", "https://example.com/1/", ("组一", "A")),
        ChapterRef("B", "https://example.com/2/", ("组一", "B")),
        ChapterRef("C", "https://example.com/3/", ("组二", "C")),
    ]
    assert indices_for_one_per_toc_section(chapters) == frozenset({1, 3})


@pytest.mark.skipif(not FIXTURE.exists(), reason="nav fixture not present")
def test_nav_fixture_section_sample_count() -> None:
    chapters = parse_chapters_from_html(FIXTURE.read_text(encoding="utf-8"))
    indices = indices_for_one_per_toc_section(chapters)
    sections = {chapter_toc_section(ch) for ch in chapters}
    assert len(indices) == len(sections)
