from __future__ import annotations

from collections.abc import Sequence

from ebooklib import epub

from website2ebooks.nav import ChapterRef


def _group_name(chapter: ChapterRef) -> str:
    if len(chapter.toc_path) >= 2:
        return chapter.toc_path[0]
    return ""


def build_nested_book_toc(
    chapters: Sequence[ChapterRef],
    epub_chapters: Sequence[epub.EpubHtml],
) -> list:
    items: list = []
    i = 0
    n = len(chapters)
    while i < n:
        group = _group_name(chapters[i])
        batch: list[epub.EpubHtml] = []
        while i < n and _group_name(chapters[i]) == group:
            batch.append(epub_chapters[i])
            i += 1
        if group:
            items.append((epub.Section(group), batch))
        else:
            items.extend(batch)
    return items
