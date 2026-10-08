from __future__ import annotations

from pathlib import Path

from website2ebooks.article import ParsedChapter
from website2ebooks.fetch_run import FetchContext
from website2ebooks.http import SiteClient
from website2ebooks.munger_article import fetch_and_parse_munger_chapter
from website2ebooks.munger_nav import (
    MUNGER_INDEX_URL,
    MUNGER_SAMPLE_PREFERRED_TITLE_BY_SECTION,
    parse_munger_chapters,
)
from website2ebooks.nav import ChapterRef
from website2ebooks.sites.profile import SiteProfile

MUNGER_BOOK_TITLE = "查理·芒格知识库"


def _parse_munger_chapter(
    client: SiteClient,
    chapter: ChapterRef,
    chapter_index: int,
    ctx: FetchContext,
) -> ParsedChapter:
    return fetch_and_parse_munger_chapter(
        client,
        chapter_url=chapter.url,
        chapter_title=chapter.title,
        chapter_index=chapter_index,
        kind=chapter.kind,
        reader_html=ctx.munger_qa_reader_html,
    )


MUNGER_PROFILE = SiteProfile(
    id="munger",
    nav_index_url=MUNGER_INDEX_URL,
    book_title=MUNGER_BOOK_TITLE,
    default_output=Path("dist/munger-knowledge-base.epub"),
    parse_chapters=parse_munger_chapters,
    parse_chapter=_parse_munger_chapter,
    sample_section_preferred_titles=MUNGER_SAMPLE_PREFERRED_TITLE_BY_SECTION,
)
