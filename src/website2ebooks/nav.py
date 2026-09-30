from __future__ import annotations

import logging
import re
from collections.abc import Callable
from dataclasses import dataclass, field
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


@dataclass(frozen=True)
class ChapterRef:
    title: str
    url: str
    toc_path: tuple[str, ...] = field(default_factory=tuple)


def normalize_url(url: str, base: str = BOOK_INDEX_URL) -> str:
    absolute = urljoin(base, url.strip())
    parsed = urlparse(absolute)
    path = parsed.path or "/"
    if not path.endswith("/"):
        path = f"{path}/"
    normalized = urlunparse(
        (parsed.scheme.lower(), parsed.netloc.lower(), path, "", "", "")
    )
    return normalized


def should_skip_nav_href(href: str, base: str = BOOK_INDEX_URL) -> bool:
    if not href or href.startswith(("javascript:", "mailto:", "tel:")):
        return True
    if "#" in href:
        return True
    absolute = normalize_url(href, base)
    if absolute in EXCLUDED_CHAPTER_URLS:
        return True
    parsed = urlparse(absolute)
    if not parsed.path.startswith(BOOK_PATH_PREFIX):
        return True
    return False


def _link_title(anchor: html.HtmlElement) -> str:
    text = anchor.text_content() or ""
    return _WHITESPACE.sub(" ", text).strip()


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


def _section_labels_for_anchor(anchor: html.HtmlElement) -> list[str]:
    labels: list[str] = []
    for ancestor in anchor.iterancestors():
        if ancestor.tag in ("h2", "h3", "h4"):
            label = _WHITESPACE.sub(" ", (ancestor.text_content() or "")).strip()
            if label and (not labels or labels[-1] != label):
                labels.append(label)
    labels.reverse()
    return labels


def parse_chapters_from_html(
    page_html: str, *, page_url: str = BOOK_INDEX_URL
) -> list[ChapterRef]:
    doc = html.fromstring(page_html)
    nav = _find_nav_root(doc)
    chapters: list[ChapterRef] = []
    seen_urls: set[str] = set()

    for anchor in nav.xpath(".//a[@href]"):
        href = anchor.get("href") or ""
        if should_skip_nav_href(href, page_url):
            continue
        url = normalize_url(href, page_url)
        if url in seen_urls:
            continue
        title = _link_title(anchor)
        if not title:
            continue
        section_labels = _section_labels_for_anchor(anchor)
        toc_path = tuple(section_labels + [title])
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
