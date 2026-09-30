from website2ebooks.nav import normalize_url, should_skip_nav_href


def test_normalize_url_trailing_slash() -> None:
    assert (
        normalize_url("https://buffett.ayaseeri.com/books/buffett-wenda-lu/neng-li-quan")
        == "https://buffett.ayaseeri.com/books/buffett-wenda-lu/neng-li-quan/"
    )


def test_skip_index_url() -> None:
    assert should_skip_nav_href("https://buffett.ayaseeri.com/books/buffett-wenda-lu/")
    assert should_skip_nav_href("/books/buffett-wenda-lu/")


def test_skip_fragment_links() -> None:
    assert should_skip_nav_href(
        "https://buffett.ayaseeri.com/books/buffett-wenda-lu/#kan-dong-zai-xia-zhu"
    )
    assert should_skip_nav_href("/books/buffett-wenda-lu/foo/#bar")


def test_allow_chapter_url() -> None:
    assert not should_skip_nav_href(
        "https://buffett.ayaseeri.com/books/buffett-wenda-lu/neng-li-quan/"
    )


def test_skip_external_url() -> None:
    assert should_skip_nav_href("https://example.com/other/")
