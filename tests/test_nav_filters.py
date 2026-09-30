from pathlib import Path

import pytest

from website2ebooks.nav import normalize_url, parse_chapters_from_html, should_skip_nav_href

FIXTURE = Path(__file__).parent / "fixtures" / "nav_index.html"


def test_normalize_url_trailing_slash() -> None:
    assert (
        normalize_url("https://buffett.ayaseeri.com/books/buffett-wenda-lu/neng-li-quan")
        == "https://buffett.ayaseeri.com/books/buffett-wenda-lu/neng-li-quan/"
    )


def test_skip_index_url() -> None:
    assert should_skip_nav_href("https://buffett.ayaseeri.com/books/buffett-wenda-lu/")
    assert should_skip_nav_href("/books/buffett-wenda-lu/")


def test_skip_index_fragment_only() -> None:
    assert should_skip_nav_href(
        "https://buffett.ayaseeri.com/books/buffett-wenda-lu/#kan-dong-zai-xia-zhu"
    )
    assert should_skip_nav_href("/books/buffett-wenda-lu/#kan-dong-zai-xia-zhu")


def test_allow_chapter_with_fragment() -> None:
    assert not should_skip_nav_href(
        "/books/buffett-wenda-lu/neng-li-quan/#section-1"
    )


def test_allow_chapter_url() -> None:
    assert not should_skip_nav_href(
        "https://buffett.ayaseeri.com/books/buffett-wenda-lu/neng-li-quan/"
    )


def test_allow_sources_and_articles() -> None:
    assert not should_skip_nav_href("/sources/interviews/ba-fei-te-1985nian-tan-tou-zi/")
    assert not should_skip_nav_href("/articles/question/wei-shen-me-bu-yu-ce-shi-chang")


def test_skip_external_url() -> None:
    assert should_skip_nav_href("https://example.com/other/")


@pytest.mark.skipif(not FIXTURE.exists(), reason="nav fixture not present")
def test_parse_nav_fixture_count_and_sources() -> None:
    html_text = FIXTURE.read_text(encoding="utf-8")
    chapters = parse_chapters_from_html(html_text)
    assert len(chapters) >= 350
    assert any("/sources/" in ch.url for ch in chapters)
    assert any("neng-li-quan" in ch.url for ch in chapters)
    first = chapters[0]
    assert "能力圈" in first.title or "neng-li-quan" in first.url
