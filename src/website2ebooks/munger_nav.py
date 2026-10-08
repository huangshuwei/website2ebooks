from __future__ import annotations

import logging
import re
from collections.abc import Callable
from urllib.parse import urljoin, urlparse

from lxml import html

from website2ebooks.nav import ChapterRef, normalize_url

logger = logging.getLogger(__name__)

MUNGER_INDEX_URL = "https://munger.ayaseeri.com/"
MUNGER_READER_URL = "https://munger.ayaseeri.com/books/munger-qa/reader"
MUNGER_QA_INDEX_PATH = "/books/munger-qa/"

_WHITESPACE = re.compile(r"\s+")

MUNGER_ALLOWED_PREFIXES = (
    "/sources/",
    "/articles/",
    "/thinking-grids/",
    "/stop-doing/",
    "/book-list/",
)


def _clean_text(text: str) -> str:
    return _WHITESPACE.sub(" ", text).strip()


def _link_title(anchor: html.HtmlElement) -> str:
    parts: list[str] = []
    if anchor.text:
        parts.append(anchor.text)
    for child in anchor:
        classes = child.get("class") or ""
        if child.tag == "span" and ("count" in classes or child.get("class") == "chevron"):
            continue
        if child.tag == "small":
            continue
        if child.tag == "span" and child.text:
            parts.append(child.text)
        if child.tail:
            parts.append(child.tail)
    text = "".join(parts)
    if not text.strip():
        text = anchor.text_content() or ""
    return _clean_text(text)


def _path_only(url: str, base: str) -> str:
    return normalize_url(url, base)


def is_munger_qa_index_href(href: str, base: str = MUNGER_INDEX_URL) -> bool:
    if not href:
        return False
    absolute = urljoin(base, href.split("#", 1)[0])
    parsed = urlparse(absolute)
    path = parsed.path.rstrip("/") + "/"
    return path.endswith(MUNGER_QA_INDEX_PATH) or path == MUNGER_QA_INDEX_PATH.rstrip("/") + "/"


def should_skip_munger_nav_href(href: str, base: str = MUNGER_INDEX_URL) -> bool:
    if not href or href.startswith(("javascript:", "mailto:", "tel:")):
        return True
    if href in ("/",):
        return True
    if is_munger_qa_index_href(href, base):
        return True
    path = urlparse(urljoin(base, href.split("#", 1)[0])).path or "/"
    if path == "/search" or path.startswith("/search/"):
        return True
    return not any(path.startswith(prefix) for prefix in MUNGER_ALLOWED_PREFIXES)


def parse_qa_chapter_refs_from_reader(
    reader_html: str,
    *,
    section_label: str,
    group_label: str,
    reader_url: str = MUNGER_READER_URL,
) -> list[ChapterRef]:
    doc = html.fromstring(reader_html)
    refs: list[ChapterRef] = []
    for anchor in doc.xpath(
        '//nav[contains(@class,"rail")]//ol[contains(@class,"toc")]//a[@href]'
    ):
        href = (anchor.get("href") or "").strip()
        if not href.startswith("#"):
            continue
        fragment = href[1:]
        title = _link_title(anchor)
        if not title:
            continue
        url = f"{reader_url.rstrip('/')}#{fragment}"
        refs.append(
            ChapterRef(
                title=title,
                url=url,
                toc_path=(section_label, group_label, title),
                kind="munger_qa",
            )
        )
    return refs


def parse_munger_chapters_from_html(
    page_html: str,
    *,
    page_url: str = MUNGER_INDEX_URL,
    reader_html: str | None = None,
) -> list[ChapterRef]:
    doc = html.fromstring(page_html)
    nav_nodes = doc.xpath("//nav[contains(@class,'sidebar-nav')]")
    if not nav_nodes:
        raise ValueError("Could not locate munger sidebar-nav in page HTML")
    nav = nav_nodes[0]

    chapters: list[ChapterRef] = []
    seen_urls: set[str] = set()

    for section in nav.xpath(".//section[contains(@class,'sidebar-section')]"):
        h2_nodes = section.xpath(".//h2")
        section_label = _clean_text(
            h2_nodes[0].text_content() if h2_nodes else ""
        )
        if not section_label:
            continue

        for details in section.xpath(".//details"):
            summary = details.find("summary")
            if summary is None:
                continue
            group_nodes = summary.xpath(
                ".//span[contains(@class,'sidebar-group-label')]"
            )
            group_label = _clean_text(
                group_nodes[0].text_content() if group_nodes else summary.text_content()
            )

            for anchor in details.xpath(".//ul[contains(@class,'sidebar-leaves')]//a[@href]"):
                href = anchor.get("href") or ""
                if is_munger_qa_index_href(href, page_url):
                    if reader_html:
                        qa_refs = parse_qa_chapter_refs_from_reader(
                            reader_html,
                            section_label=section_label,
                            group_label=group_label,
                        )
                        for ref in qa_refs:
                            if ref.url in seen_urls:
                                continue
                            chapters.append(ref)
                            seen_urls.add(ref.url)
                    else:
                        logger.warning(
                            "Munger QA index link found but no reader HTML was provided"
                        )
                    continue

                if should_skip_munger_nav_href(href, page_url):
                    continue

                title = _link_title(anchor)
                if not title:
                    continue

                url = _path_only(href, page_url)
                if url in seen_urls:
                    continue

                chapters.append(
                    ChapterRef(
                        title=title,
                        url=url,
                        toc_path=(section_label, group_label, title),
                        kind="standard",
                    )
                )
                seen_urls.add(url)

    return chapters


def parse_munger_chapters(
    client_get_text: Callable[[str], str],
    nav_index_url: str = MUNGER_INDEX_URL,
) -> list[ChapterRef]:
    html_text = client_get_text(nav_index_url)
    reader_html = client_get_text(MUNGER_READER_URL)
    chapters = parse_munger_chapters_from_html(
        html_text,
        page_url=nav_index_url,
        reader_html=reader_html,
    )
    if chapters:
        return chapters
    raise ValueError(f"No chapters found in munger nav at {nav_index_url}")
