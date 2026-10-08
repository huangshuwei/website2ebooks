from __future__ import annotations

from pathlib import Path

from website2ebooks.article import ParsedChapter, fetch_and_parse_chapter
from website2ebooks.config import BOOK_INDEX_URL, BOOK_TITLE
from website2ebooks.fetch_run import FetchContext
from website2ebooks.http import SiteClient
from website2ebooks.nav import ChapterRef, parse_chapters
from website2ebooks.sites.profile import SiteProfile


def _parse_buffett_chapter(
    client: SiteClient,
    chapter: ChapterRef,
    chapter_index: int,
    _ctx: FetchContext,
) -> ParsedChapter:
    return fetch_and_parse_chapter(
        client,
        chapter_url=chapter.url,
        chapter_title=chapter.title,
        chapter_index=chapter_index,
    )


BUFFETT_PROFILE = SiteProfile(
    id="buffett",
    nav_index_url=BOOK_INDEX_URL,
    book_title=BOOK_TITLE,
    default_output=Path("dist/buffett-wenda-lu.epub"),
    parse_chapters=parse_chapters,
    parse_chapter=_parse_buffett_chapter,
)
