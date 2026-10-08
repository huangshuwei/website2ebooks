from __future__ import annotations

import re
from urllib.parse import urljoin, urlparse

from lxml import html
from lxml.etree import tostring

from website2ebooks.article import (
    ParsedChapter,
    merge_chapter_titles,
    parse_chapter_html,
)
from website2ebooks.http import SiteClient
from website2ebooks.munger_nav import MUNGER_READER_URL

_UNSAFE_TAGS = frozenset({"script", "iframe", "noscript", "style"})


def _ensure_reader_html(ctx_html: str | None, client: SiteClient) -> str:
    if ctx_html:
        return ctx_html
    return client.get_text(MUNGER_READER_URL)


def _strip_unsafe(root: html.HtmlElement) -> None:
    for tag in _UNSAFE_TAGS:
        for node in root.xpath(f".//{tag}"):
            parent = node.getparent()
            if parent is not None:
                parent.remove(node)


def _strip_qa_chrome(section: html.HtmlElement) -> None:
    for node in section.xpath(".//article[contains(@class,'qa')]//footer"):
        parent = node.getparent()
        if parent is not None:
            parent.remove(node)
    for node in section.xpath(".//article[contains(@class,'qa')]//a"):
        anchor = node
        anchor.tag = "span"
        for attr in list(anchor.attrib):
            del anchor.attrib[attr]


def parse_munger_qa_chapter_html(
    reader_html: str,
    *,
    fragment: str,
    chapter_title: str,
    chapter_index: int,
    client: SiteClient,
    page_url: str,
) -> ParsedChapter:
    doc = html.fromstring(reader_html)
    section_nodes = doc.xpath(
        f'//section[contains(@class,"chapter")][@id="{fragment}"]'
    )
    if not section_nodes:
        raise ValueError(f"Munger QA chapter section not found: {fragment!r}")
    section = html.fromstring(tostring(section_nodes[0], encoding="unicode"))
    _strip_unsafe(section)
    _strip_qa_chrome(section)

    header_h2 = section.xpath('.//header[contains(@class,"chapter-header")]//h2')
    body_title = None
    if header_h2:
        body_title = re.sub(r"\s+", " ", header_h2[0].text_content() or "").strip()

    from website2ebooks import article as article_mod

    title = merge_chapter_titles(chapter_title, body_title)
    article_mod._normalize_epub_presentation(section)
    article_mod._normalize_typography(section)
    if article_mod.STRIP_LINKS:
        article_mod._unwrap_links(section)
    images = article_mod._process_images(section, page_url, client, chapter_index)
    body = article_mod._serialize_article_fragment(section)
    return ParsedChapter(
        title=title,
        xhtml_body=article_mod._wrap_xhtml(body, title),
        images=images,
    )


def _parse_munger_content_blocks(
    doc: html.HtmlElement,
    *,
    page_url: str,
    chapter_title: str,
    chapter_index: int,
    client: SiteClient,
) -> ParsedChapter | None:
    blocks = doc.xpath("//section[contains(@class,'content-block')]")
    if not blocks:
        return None

    from website2ebooks import article as article_mod

    wrapper = html.Element("div")
    title_nodes = doc.xpath("//header[contains(@class,'title-page')]")
    if title_nodes:
        wrapper.append(
            html.fromstring(tostring(title_nodes[0], encoding="unicode"))
        )
    for block in blocks:
        wrapper.append(html.fromstring(tostring(block, encoding="unicode")))
    _strip_unsafe(wrapper)

    body_title = None
    h1_nodes = doc.xpath("//header[contains(@class,'title-page')]//h1")
    if h1_nodes:
        body_title = re.sub(r"\s+", " ", h1_nodes[0].text_content() or "").strip()

    title = merge_chapter_titles(chapter_title, body_title)
    article_mod._normalize_epub_presentation(wrapper)
    article_mod._normalize_typography(wrapper)
    if article_mod.STRIP_LINKS:
        article_mod._unwrap_links(wrapper)
    images = article_mod._process_images(wrapper, page_url, client, chapter_index)
    body = article_mod._serialize_article_fragment(wrapper)
    return ParsedChapter(
        title=title,
        xhtml_body=article_mod._wrap_xhtml(body, title),
        images=images,
    )


def parse_munger_reader_page_html(
    page_html: str,
    *,
    page_url: str,
    chapter_title: str,
    chapter_index: int,
    client: SiteClient,
) -> ParsedChapter:
    doc = html.fromstring(page_html)
    iframe_nodes = doc.xpath(
        "//iframe[contains(@class,'standalone-reader-frame')][@src]"
    )
    if iframe_nodes:
        reader_url = urljoin(page_url, iframe_nodes[0].get("src") or "")
        reader_html = client.get_text(reader_url)
        reader_doc = html.fromstring(reader_html)
        parsed = _parse_munger_content_blocks(
            reader_doc,
            page_url=reader_url,
            chapter_title=chapter_title,
            chapter_index=chapter_index,
            client=client,
        )
        if parsed:
            return parsed

    body_nodes = doc.xpath(
        "//article[contains(@class,'reader-layout')]//div[contains(@class,'article-body')]"
    )
    if body_nodes:
        article_body = html.fromstring(tostring(body_nodes[0], encoding="unicode"))
        header_nodes = doc.xpath(
            "//article[contains(@class,'reader-layout')]"
            "//header[contains(@class,'reader-header')]//h1"
        )
        body_title = None
        if header_nodes:
            body_title = re.sub(
                r"\s+", " ", header_nodes[0].text_content() or ""
            ).strip()
        _strip_unsafe(article_body)

        from website2ebooks import article as article_mod

        title = merge_chapter_titles(chapter_title, body_title)
        article_mod._normalize_epub_presentation(article_body)
        article_mod._normalize_typography(article_body)
        if article_mod.STRIP_LINKS:
            article_mod._unwrap_links(article_body)
        images = article_mod._process_images(
            article_body, page_url, client, chapter_index
        )
        body = article_mod._serialize_article_fragment(article_body)
        return ParsedChapter(
            title=title,
            xhtml_body=article_mod._wrap_xhtml(body, title),
            images=images,
        )

    parsed_blocks = _parse_munger_content_blocks(
        doc,
        page_url=page_url,
        chapter_title=chapter_title,
        chapter_index=chapter_index,
        client=client,
    )
    if parsed_blocks:
        return parsed_blocks

    main_article = doc.xpath("//main//article")
    if main_article:
        wrapped = html.tostring(main_article[0], encoding="unicode")
        return parse_chapter_html(
            f"<html><body>{wrapped}</body></html>",
            page_url=page_url,
            chapter_title=chapter_title,
            chapter_index=chapter_index,
            client=client,
        )

    raise ValueError("Could not locate munger reader article body in page HTML")


def fetch_and_parse_munger_chapter(
    client: SiteClient,
    *,
    chapter_url: str,
    chapter_title: str,
    chapter_index: int,
    kind: str,
    reader_html: str | None,
) -> ParsedChapter:
    if kind == "munger_qa":
        parsed = urlparse(chapter_url)
        fragment = parsed.fragment
        if not fragment:
            raise ValueError(f"Munger QA chapter URL missing fragment: {chapter_url}")
        reader = _ensure_reader_html(reader_html, client)
        base = chapter_url.split("#", 1)[0]
        return parse_munger_qa_chapter_html(
            reader,
            fragment=fragment,
            chapter_title=chapter_title,
            chapter_index=chapter_index,
            client=client,
            page_url=base,
        )

    page_html = client.get_text(chapter_url)
    return parse_munger_reader_page_html(
        page_html,
        page_url=chapter_url,
        chapter_title=chapter_title,
        chapter_index=chapter_index,
        client=client,
    )
