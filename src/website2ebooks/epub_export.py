from __future__ import annotations

import uuid
from pathlib import Path

from ebooklib import epub

from website2ebooks.article import ParsedChapter
from website2ebooks.config import BOOK_TITLE, DEFAULT_CSS
from website2ebooks.nav import ChapterRef


def _chapter_file_name(index: int) -> str:
    return f"Text/chapter_{index:03d}.xhtml"


def build_url_to_epub_map(chapters: list[ChapterRef]) -> dict[str, str]:
    return {ch.url: _chapter_href(i) for i, ch in enumerate(chapters, start=1)}


def _chapter_href(index: int) -> str:
    return f"chapter_{index:03d}.xhtml"


def _flat_toc_title(chapter_ref: ChapterRef) -> str:
    if chapter_ref.toc_path:
        return " › ".join(chapter_ref.toc_path)
    return chapter_ref.title


def build_epub(
    chapters: list[ChapterRef],
    parsed: list[ParsedChapter],
    output_path: Path,
    *,
    book_title: str = BOOK_TITLE,
) -> None:
    if len(chapters) != len(parsed):
        raise ValueError("chapters and parsed content length mismatch")

    book = epub.EpubBook()
    book.set_identifier(f"urn:uuid:{uuid.uuid4()}")
    book.set_title(book_title)
    book.set_language("zh-CN")

    style = epub.EpubItem(
        uid="style_default",
        file_name="Styles/default.css",
        media_type="text/css",
        content=DEFAULT_CSS.encode("utf-8"),
    )
    book.add_item(style)

    epub_chapters: list[epub.EpubHtml] = []
    spine: list[str] = ["nav"]

    for index, (chapter_ref, content) in enumerate(zip(chapters, parsed, strict=True), start=1):
        file_name = _chapter_file_name(index)
        display_title = _flat_toc_title(chapter_ref)
        ch = epub.EpubHtml(
            title=display_title,
            file_name=file_name,
            lang="zh-CN",
        )
        ch.content = content.xhtml_body.encode("utf-8")
        ch.add_item(style)
        book.add_item(ch)
        epub_chapters.append(ch)
        spine.append(ch.get_id())

        for img in content.images:
            item = epub.EpubItem(
                uid=f"img_{index}_{img.epub_path.replace('/', '_')}",
                file_name=img.epub_path,
                media_type=img.media_type,
                content=img.data,
            )
            book.add_item(item)

    book.toc = epub_chapters
    book.add_item(epub.EpubNav())
    book.add_item(epub.EpubNcx())
    book.spine = spine

    output_path.parent.mkdir(parents=True, exist_ok=True)
    epub.write_epub(str(output_path), book, {})
