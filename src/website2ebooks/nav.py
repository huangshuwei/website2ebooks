from __future__ import annotations

import logging
import re
from collections.abc import Callable, Mapping, Sequence
from dataclasses import dataclass, field
from typing import Literal
from urllib.parse import urljoin, urlparse, urlunparse

from lxml import html

from website2ebooks.config import (
    BOOK_INDEX_URL,
    BOOK_PATH_PREFIX,
    EXCLUDED_CHAPTER_URLS,
    NAV_XPATH,
    NAV_XPATH_FALLBACK,
)

logger = logging.getLogger(__name__)

_WHITESPACE = re.compile(r"\s+")


ChapterKind = Literal["standard", "munger_qa"]


@dataclass(frozen=True)
class ChapterRef:
    title: str
    url: str
    toc_path: tuple[str, ...] = field(default_factory=tuple)
    kind: ChapterKind = "standard"


def normalize_url(url: str, base: str = BOOK_INDEX_URL) -> str:
    href = url.strip().split("#", 1)[0]
    absolute = urljoin(base, href)
    parsed = urlparse(absolute)
    path = parsed.path or "/"
    if not path.endswith("/"):
        path = f"{path}/"
    normalized = urlunparse(
        (parsed.scheme.lower(), parsed.netloc.lower(), path, "", "", "")
    )
    return normalized


def _is_allowed_chapter_path(path: str) -> bool:
    if path.startswith("/sources/"):
        return True
    if path.startswith("/articles/"):
        return True
    if path.startswith(BOOK_PATH_PREFIX):
        rest = path[len(BOOK_PATH_PREFIX) :].strip("/")
        return bool(rest)
    return False


def should_skip_nav_href(href: str, base: str = BOOK_INDEX_URL) -> bool:
    if not href or href.startswith(("javascript:", "mailto:", "tel:")):
        return True
    if href in ("/",):
        return True

    absolute = normalize_url(href, base)
    if absolute in EXCLUDED_CHAPTER_URLS:
        return True

    index_url = normalize_url(BOOK_INDEX_URL, base)
    if absolute == index_url and "#" in href:
        return True

    parsed = urlparse(absolute)
    return not _is_allowed_chapter_path(parsed.path)


def _clean_text(el: html.HtmlElement) -> str:
    return _WHITESPACE.sub(" ", (el.text_content() or "")).strip()


def _summary_label(summary: html.HtmlElement) -> str:
    parts: list[str] = []
    if summary.text:
        parts.append(summary.text)
    for child in summary:
        if child.tag == "span" and "count" in (child.get("class") or ""):
            continue
        if child.tail:
            parts.append(child.tail)
    text = "".join(parts)
    if not text.strip():
        text = summary.text_content() or ""
    return _WHITESPACE.sub(" ", text).strip()


def _link_title(anchor: html.HtmlElement) -> str:
    visible = _clean_text(anchor)
    if visible:
        return visible
    title = (anchor.get("title") or "").strip()
    return _WHITESPACE.sub(" ", title).strip()


def _in_cat_menu(anchor: html.HtmlElement) -> bool:
    for ancestor in anchor.iterancestors():
        if ancestor.tag == "ul" and "cat-menu" in (ancestor.get("class") or ""):
            return True
        if ancestor.tag == "nav":
            break
    return False


def _find_nav_root(doc: html.HtmlElement) -> html.HtmlElement:
    nodes = doc.xpath(NAV_XPATH)
    if nodes:
        return nodes[0]
    logger.warning(
        "Primary nav XPath %r matched nothing; using fallback %r",
        NAV_XPATH,
        NAV_XPATH_FALLBACK,
    )
    nodes = doc.xpath(NAV_XPATH_FALLBACK)
    if not nodes:
        raise ValueError("Could not locate sidebar nav in page HTML")
    return nodes[0]


def parse_chapters_from_html(
    page_html: str, *, page_url: str = BOOK_INDEX_URL
) -> list[ChapterRef]:
    doc = html.fromstring(page_html)
    nav = _find_nav_root(doc)
    chapters: list[ChapterRef] = []
    seen_urls: set[str] = set()

    summary_label = ""

    for el in nav.iter():
        if el.tag == "p" and "menu-head" in (el.get("class") or ""):
            continue
        if el.tag == "summary":
            summary_label = _summary_label(el)
            continue
        if el.tag != "a" or not el.get("href"):
            continue
        if not _in_cat_menu(el):
            continue

        classes = el.get("class") or ""
        if "book-part-link" in classes:
            continue

        href = el.get("href") or ""
        if should_skip_nav_href(href, page_url):
            continue

        url = normalize_url(href, page_url)
        if url in seen_urls:
            continue

        title = _link_title(el)
        if not title:
            continue

        if summary_label:
            toc_path = (summary_label, title)
        else:
            toc_path = (title,)

        chapters.append(ChapterRef(title=title, url=url, toc_path=toc_path))
        seen_urls.add(url)

    return chapters


def parse_chapters(
    client_get_text: Callable[[str], str],
    book_index_url: str = BOOK_INDEX_URL,
) -> list[ChapterRef]:
    html_text = client_get_text(book_index_url)
    chapters = parse_chapters_from_html(html_text, page_url=book_index_url)
    if chapters:
        return chapters
    raise ValueError(f"No chapters found in nav at {book_index_url}")


def _index_for_section_sample(
    chapters: Sequence[ChapterRef],
    section: str,
    *,
    preferred_title_by_section: Mapping[str, str] | None = None,
) -> int | None:
    from website2ebooks.toc_page import chapter_toc_section

    indices_in_section = [
        i
        for i, ch in enumerate(chapters, start=1)
        if chapter_toc_section(ch) == section
    ]
    if not indices_in_section:
        return None
    pick = indices_in_section[0]
    want_title = (preferred_title_by_section or {}).get(section)
    if not want_title:
        return pick
    for i in indices_in_section:
        title = chapters[i - 1].title
        if title == want_title or want_title in title:
            return i
    return pick


def indices_for_one_per_toc_section(
    chapters: Sequence[ChapterRef],
    *,
    preferred_title_by_section: Mapping[str, str] | None = None,
) -> frozenset[int]:
    """1-based indices of chapters to fetch when sampling one body per toc section."""
    from website2ebooks.toc_page import chapter_toc_section

    section_order: list[str] = []
    for ch in chapters:
        key = chapter_toc_section(ch)
        if key and key not in section_order:
            section_order.append(key)

    out: list[int] = []
    for section in section_order:
        idx = _index_for_section_sample(
            chapters,
            section,
            preferred_title_by_section=preferred_title_by_section,
        )
        if idx is not None:
            out.append(idx)
    return frozenset(out)


def indices_for_named_sections(
    chapters: Sequence[ChapterRef],
    section_names: Sequence[str],
    *,
    preferred_title_by_section: Mapping[str, str] | None = None,
) -> frozenset[int]:
    """1-based indices of the first chapter in each named toc section (toc_path[0])."""
    out: list[int] = []
    for name in section_names:
        key = name.strip()
        if not key:
            continue
        idx = _index_for_section_sample(
            chapters,
            key,
            preferred_title_by_section=preferred_title_by_section,
        )
        if idx is not None:
            out.append(idx)
    return frozenset(out)
