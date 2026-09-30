from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from pathlib import Path

from ebooklib import epub

from website2ebooks.article import ParsedChapter
from website2ebooks.config import BOOK_TITLE, DEFAULT_CSS
from website2ebooks.nav import ChapterRef


def _chapter_file_name(index: int) -> str:
    return f"Text/chapter_{index:03d}.xhtml"


def _chapter_href(index: int) -> str:
    return f"chapter_{index:03d}.xhtml"


def build_url_to_epub_map(chapters: list[ChapterRef]) -> dict[str, str]:
    return {ch.url: _chapter_href(i) for i, ch in enumerate(chapters, start=1)}


@dataclass
class _TocNode:
    children: dict[str, _TocNode] = field(default_factory=dict)
    chapters: list[epub.EpubHtml] = field(default_factory=list)


def _append_to_toc(root: _TocNode, toc_path: tuple[str, ...], epub_ch: epub.EpubHtml) -> None:
    if len(toc_path) <= 1:
        root.chapters.append(epub_ch)
        return
    node = root
    for section in toc_path[:-1]:
        if section not in node.children:
            node.children[section] = _TocNode()
        node = node.children[section]
    node.chapters.append(epub_ch)


def _toc_node_to_list(node: _TocNode) -> list:
    items: list = []
    items.extend(node.chapters)
    for name in sorted(node.children):
        child = node.children[name]
        nested = _toc_node_to_list(child)
        if nested:
            items.append((epub.Section(name), nested))
    return items


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
    toc_root = _TocNode()

    for index, (chapter_ref, content) in enumerate(zip(chapters, parsed, strict=True), start=1):
        file_name = _chapter_file_name(index)
        ch = epub.EpubHtml(
            title=content.title or chapter_ref.title,
            file_name=file_name,
            lang="zh-CN",
        )
        ch.content = content.xhtml_body.encode("utf-8")
        ch.add_item(style)
        book.add_item(ch)
        epub_chapters.append(ch)
        spine.append(ch.get_id())
        _append_to_toc(toc_root, chapter_ref.toc_path, ch)

        for img in content.images:
            item = epub.EpubItem(
                uid=f"img_{index}_{img.epub_path.replace('/', '_')}",
                file_name=img.epub_path,
                media_type=img.media_type,
                content=img.data,
            )
            book.add_item(item)

    book.toc = _toc_node_to_list(toc_root)
    book.add_item(epub.EpubNav())
    book.spine = spine

    output_path.parent.mkdir(parents=True, exist_ok=True)
    epub.write_epub(str(output_path), book, {})
