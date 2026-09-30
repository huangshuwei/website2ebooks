from __future__ import annotations

import logging
import mimetypes
import re
from dataclasses import dataclass, field
from urllib.parse import urljoin, urlparse

from lxml import html
from lxml.etree import tostring

from website2ebooks.config import (
    ARTICLE_BODY_SECTIONS_XPATH,
    ARTICLE_CHROME_PATTERNS,
    ARTICLE_TAIL_PATTERNS,
    ARTICLE_XPATH,
    ARTICLE_XPATH_FALLBACK,
    CHAPTER_CLOSING_ASIDE_XPATH,
    CHAPTER_NAV_IN_ARTICLE_XPATH,
    IN_CHAPTER_TOC_XPATH,
    STUB_CHAPTER_MESSAGE,
    STRIP_LINKS,
)
from website2ebooks.http import SiteClient

logger = logging.getLogger(__name__)

_UNSAFE_TAGS = frozenset({"script", "iframe", "noscript", "style"})
_CHROME_RES = tuple(re.compile(p) for p in ARTICLE_CHROME_PATTERNS)
_TAIL_RES = tuple(re.compile(p) for p in ARTICLE_TAIL_PATTERNS)
_MAX_CHROME_STRIPS = 8


@dataclass
class ImageAsset:
    epub_path: str
    media_type: str
    data: bytes


@dataclass
class ParsedChapter:
    title: str
    xhtml_body: str
    images: list[ImageAsset] = field(default_factory=list)


def _find_article(doc: html.HtmlElement) -> html.HtmlElement:
    nodes = doc.xpath(ARTICLE_XPATH)
    if nodes:
        return nodes[0]
    logger.warning(
        "Primary article XPath %r matched nothing; using fallback %r",
        ARTICLE_XPATH,
        ARTICLE_XPATH_FALLBACK,
    )
    nodes = doc.xpath(ARTICLE_XPATH_FALLBACK)
    if not nodes:
        raise ValueError("Could not locate article element in page HTML")
    return nodes[0]


def _remove_footers(article: html.HtmlElement) -> None:
    for node in article.xpath('.//*[@id="article-content"]/section/section/footer'):
        parent = node.getparent()
        if parent is not None:
            parent.remove(node)
    for node in article.xpath(".//footer"):
        parent = node.getparent()
        if parent is not None:
            parent.remove(node)


def _node_text_matches_tail(text: str) -> bool:
    normalized = re.sub(r"\s+", " ", text).strip()
    if not normalized:
        return False
    return any(rx.search(normalized) for rx in _TAIL_RES)


def _strip_article_tail(article: html.HtmlElement) -> None:
    tail_xpaths = (
        ".//nav[contains(@class,'chapter')]",
        ".//*[contains(@class,'chapter-nav')]",
        ".//*[contains(@class,'prev') or contains(@class,'next')]",
    )
    for xpath in tail_xpaths:
        for node in article.xpath(xpath):
            parent = node.getparent()
            if parent is not None:
                parent.remove(node)

    for node in list(article.xpath(".//aside")):
        text = re.sub(r"\s+", " ", (node.text_content() or "")).strip()
        if _node_text_matches_tail(text):
            parent = node.getparent()
            if parent is not None:
                parent.remove(node)

    stripped = 0
    while stripped < _MAX_CHROME_STRIPS and len(article):
        child = article[-1]
        chunk = re.sub(r"\s+", " ", (child.text_content() or "")).strip()
        if chunk and _node_text_matches_tail(chunk):
            article.remove(child)
            stripped += 1
            continue
        if child.tag in ("footer", "nav", "aside") and not chunk:
            article.remove(child)
            stripped += 1
            continue
        break


def _strip_unsafe(article: html.HtmlElement) -> None:
    for tag in _UNSAFE_TAGS:
        for node in article.xpath(f".//{tag}"):
            parent = node.getparent()
            if parent is not None:
                parent.remove(node)


def _guess_extension(url: str, content_type: str | None) -> str:
    path = urlparse(url).path
    ext = path.rsplit(".", 1)[-1].lower() if "." in path else ""
    if ext in {"jpg", "jpeg", "png", "gif", "webp", "svg"}:
        return "jpg" if ext == "jpeg" else ext
    if content_type:
        guessed = mimetypes.guess_extension(content_type.split(";")[0].strip())
        if guessed:
            return guessed.lstrip(".")
    return "png"


def _media_type_for_ext(ext: str) -> str:
    mapping = {
        "jpg": "image/jpeg",
        "jpeg": "image/jpeg",
        "png": "image/png",
        "gif": "image/gif",
        "webp": "image/webp",
        "svg": "image/svg+xml",
    }
    return mapping.get(ext, "image/png")


def _node_text_matches_chrome(text: str) -> bool:
    normalized = re.sub(r"\s+", " ", text).strip()
    if not normalized:
        return False
    return any(rx.search(normalized) for rx in _CHROME_RES)


def _normalize_title_text(text: str) -> str:
    return re.sub(r"\s+", " ", text).strip()


def merge_chapter_titles(nav_title: str, body_title: str | None) -> str:
    nav = _normalize_title_text(nav_title)
    body = _normalize_title_text(body_title or "")
    if not body:
        return nav or "章节"
    if nav == body:
        return nav
    if body.startswith(nav):
        return body
    return f"{nav}：{body}"


def _extract_body_title(article: html.HtmlElement) -> str | None:
    for xpath in (
        ".//header[contains(@class,'qa-chapter-header')]//h1",
        ".//header[contains(@class,'qa-chapter-header')]//h2",
    ):
        nodes = article.xpath(xpath)
        if nodes:
            text = _normalize_title_text(nodes[0].text_content() or "")
            if text:
                return text
    for node in article.xpath(".//h1"):
        text = _normalize_title_text(node.text_content() or "")
        if text and "本章目录" not in text:
            return text
    return None


def _strip_in_chapter_toc(article: html.HtmlElement) -> None:
    for node in article.xpath(IN_CHAPTER_TOC_XPATH):
        parent = node.getparent()
        if parent is not None:
            parent.remove(node)
    for node in article.xpath(".//details"):
        summary = node.find("summary")
        if summary is None:
            continue
        label = _normalize_title_text(summary.text_content() or "")
        if label.startswith("本章目录"):
            parent = node.getparent()
            if parent is not None:
                parent.remove(node)


def _strip_chapter_navigation(article: html.HtmlElement) -> None:
    _strip_in_chapter_toc(article)
    for xpath in (CHAPTER_NAV_IN_ARTICLE_XPATH, CHAPTER_CLOSING_ASIDE_XPATH):
        for node in article.xpath(xpath):
            parent = node.getparent()
            if parent is not None:
                parent.remove(node)


def _extract_article_body(article: html.HtmlElement) -> html.HtmlElement:
    sections = article.xpath(ARTICLE_BODY_SECTIONS_XPATH)
    if not sections:
        return article
    body = html.Element("article")
    for section in sections:
        body.append(html.fromstring(tostring(section, encoding="unicode")))
    return body


def _is_qa_movement_section(node: html.HtmlElement) -> bool:
    return node.tag == "section" and "qa-movement" in (node.get("class") or "")


def _strip_article_chrome(article: html.HtmlElement) -> None:
    for node in article.xpath("./header"):
        article.remove(node)
    for node in article.xpath(".//*[contains(@class,'qa-part-heading')]"):
        parent = node.getparent()
        if parent is not None:
            parent.remove(node)
    for node in article.xpath('.//nav[contains(@aria-label, "breadcrumb")]'):
        parent = node.getparent()
        if parent is not None:
            parent.remove(node)

    stripped = 0
    while stripped < _MAX_CHROME_STRIPS and len(article):
        child = article[0]
        if _is_qa_movement_section(child):
            break
        chunk = re.sub(r"\s+", " ", (child.text_content() or "")).strip()
        if chunk and _node_text_matches_chrome(chunk):
            article.remove(child)
            stripped += 1
            continue
        if child.tag in ("header", "nav") and not chunk:
            article.remove(child)
            stripped += 1
            continue
        break


def _unwrap_links(article: html.HtmlElement) -> None:
    for anchor in list(article.xpath(".//a")):
        anchor.tag = "span"
        for attr in list(anchor.attrib):
            del anchor.attrib[attr]


def _process_images(
    article: html.HtmlElement,
    page_url: str,
    client: SiteClient,
    chapter_index: int,
) -> list[ImageAsset]:
    assets: list[ImageAsset] = []
    img_index = 0
    for img in article.xpath(".//img"):
        src = img.get("src") or img.get("data-src") or ""
        src = src.strip()
        if not src:
            continue
        absolute = urljoin(page_url, src)
        try:
            data, content_type = client.get_bytes(absolute)
        except Exception as exc:
            logger.warning("Failed to download image %s: %s", absolute, exc)
            continue
        ext = _guess_extension(absolute, content_type)
        media_type = _media_type_for_ext(ext)
        epub_path = f"Images/ch_{chapter_index:03d}_{img_index:03d}.{ext}"
        img_index += 1
        img.set("src", f"../{epub_path}")
        for attr in ("data-src", "srcset", "loading", "decoding"):
            img.attrib.pop(attr, None)
        assets.append(ImageAsset(epub_path=epub_path, media_type=media_type, data=data))
    return assets


def _serialize_article_fragment(article: html.HtmlElement) -> str:
    parts: list[str] = []
    if article.text:
        parts.append(article.text)
    for child in article:
        parts.append(
            tostring(child, encoding="unicode", method="html", with_tail=True)
        )
    return "".join(parts)


def _wrap_xhtml(body_inner: str, title: str) -> str:
    safe_title = (
        title.replace("&", "&amp;")
        .replace("<", "&lt;")
        .replace(">", "&gt;")
        .replace('"', "&quot;")
    )
    return f"""<?xml version="1.0" encoding="utf-8"?>
<!DOCTYPE html>
<html xmlns="http://www.w3.org/1999/xhtml" xmlns:epub="http://www.idpf.org/2007/ops" lang="zh-CN" xml:lang="zh-CN">
<head>
  <title>{safe_title}</title>
  <link rel="stylesheet" type="text/css" href="../Styles/default.css"/>
</head>
<body epub:type="bodymatter">
{body_inner}
</body>
</html>
"""


def parse_chapter_html(
    page_html: str,
    *,
    page_url: str,
    chapter_title: str,
    chapter_index: int,
    client: SiteClient,
) -> ParsedChapter:
    doc = html.fromstring(page_html)
    article = _find_article(doc)
    article = html.fromstring(tostring(article, encoding="unicode"))
    body_title = _extract_body_title(article)
    _strip_chapter_navigation(article)
    article = _extract_article_body(article)
    _remove_footers(article)
    _strip_unsafe(article)
    _strip_article_chrome(article)
    _strip_article_tail(article)
    if STRIP_LINKS:
        _unwrap_links(article)
    images = _process_images(article, page_url, client, chapter_index)
    body = _serialize_article_fragment(article)
    title = merge_chapter_titles(chapter_title, body_title)
    return ParsedChapter(title=title, xhtml_body=_wrap_xhtml(body, title), images=images)


def fetch_and_parse_chapter(
    client: SiteClient,
    *,
    chapter_url: str,
    chapter_title: str,
    chapter_index: int,
) -> ParsedChapter:
    page_html = client.get_text(chapter_url)
    return parse_chapter_html(
        page_html,
        page_url=chapter_url,
        chapter_title=chapter_title,
        chapter_index=chapter_index,
        client=client,
    )


def make_stub_chapter(title: str) -> ParsedChapter:
    body = f"<p>{STUB_CHAPTER_MESSAGE}</p>"
    return ParsedChapter(title=title, xhtml_body=_wrap_xhtml(body, title), images=[])
