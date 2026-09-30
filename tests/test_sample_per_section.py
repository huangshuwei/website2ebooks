from pathlib import Path

import pytest

from website2ebooks.nav import ChapterRef, indices_for_one_per_toc_section, parse_chapters_from_html
from website2ebooks.toc_page import chapter_toc_section

FIXTURE = Path(__file__).parent / "fixtures" / "nav_index.html"


def test_chapter_toc_section_matches_toc_path() -> None:
    ch = ChapterRef("A", "https://example.com/1/", ("组一", "A"))
    assert chapter_toc_section(ch) == "组一"
    flat = ChapterRef("B", "https://example.com/2/", ("B",))
    assert chapter_toc_section(flat) == ""


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
