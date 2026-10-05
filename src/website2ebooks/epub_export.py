from __future__ import annotations

import html as html_module
import os
import uuid
from pathlib import Path, PurePosixPath

from ebooklib import epub

from website2ebooks.article import ParsedChapter
from website2ebooks.config import BOOK_TITLE, DEFAULT_CSS
from website2ebooks.nav import ChapterRef
from website2ebooks.toc_page import build_nested_book_toc


STYLE_FILE_NAME = "Styles/default.css"


def _chapter_file_name(index: int) -> str:
    return f"Text/chapter_{index:03d}.xhtml"


def _stylesheet_href_for_chapter(chapter_file_name: str, stylesheet_file_name: str) -> str:
    chapter_dir = PurePosixPath(chapter_file_name).parent.as_posix()
    return os.path.relpath(stylesheet_file_name, chapter_dir).replace("\\", "/")


def build_url_to_epub_map(chapters: list[ChapterRef]) -> dict[str, str]:
    return {ch.url: f"chapter_{i:03d}.xhtml" for i, ch in enumerate(chapters, start=1)}


def _prepare_chapter_xhtml(xhtml_body: str, chapter_title: str) -> str:
    safe = html_module.escape(chapter_title)
    heading = f'<h1 class="chapter-title">{safe}</h1>\n'
    for marker in ('<body epub:type="bodymatter">', "<body>"):
        if marker in xhtml_body:
            return xhtml_body.replace(marker, f"{marker}\n{heading}", 1)
    return xhtml_body


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
        file_name=STYLE_FILE_NAME,
        media_type="text/css",
        content=DEFAULT_CSS.encode("utf-8"),
    )
    book.add_item(style)

    epub_chapters: list[epub.EpubHtml] = []
    spine: list[str] = ["nav"]

    for index, (chapter_ref, content) in enumerate(zip(chapters, parsed, strict=True), start=1):
        file_name = _chapter_file_name(index)
        ch = epub.EpubHtml(
            title=content.title,
            file_name=file_name,
            lang="zh-CN",
        )
        xhtml = _prepare_chapter_xhtml(content.xhtml_body, content.title)
        ch.content = xhtml.encode("utf-8")
        css_href = _stylesheet_href_for_chapter(file_name, STYLE_FILE_NAME)
        ch.add_link(href=css_href, rel="stylesheet", type="text/css")
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

    book.toc = build_nested_book_toc(chapters, epub_chapters)
    book.add_item(epub.EpubNav())
    book.add_item(epub.EpubNcx())
    book.spine = spine

    output_path.parent.mkdir(parents=True, exist_ok=True)
    epub.write_epub(str(output_path), book, {})
