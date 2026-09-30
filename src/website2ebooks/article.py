from __future__ import annotations

import logging
import mimetypes
import re
from dataclasses import dataclass, field
from urllib.parse import urljoin, urlparse

from lxml import html
from lxml.etree import tostring

from website2ebooks.config import ARTICLE_XPATH, ARTICLE_XPATH_FALLBACK, FOOTER_XPATH
from website2ebooks.http import SiteClient
from website2ebooks.nav import normalize_url

logger = logging.getLogger(__name__)

_UNSAFE_TAGS = frozenset({"script", "iframe", "noscript", "style"})


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


def _rewrite_links(
    article: html.HtmlElement,
    page_url: str,
    url_to_epub: dict[str, str],
) -> None:
    for anchor in article.xpath(".//a[@href]"):
        href = (anchor.get("href") or "").strip()
        if not href or href.startswith("#"):
            continue
        if href.startswith(("javascript:", "mailto:", "tel:")):
            anchor.attrib.pop("href", None)
            continue
        absolute = normalize_url(href.split("#")[0], page_url)
        fragment = ""
        if "#" in href:
            fragment = href.split("#", 1)[1]
        target = url_to_epub.get(absolute)
        if target:
            anchor.set("href", f"{target}#{fragment}" if fragment else target)
        else:
            anchor.set("href", urljoin(page_url, href))


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
<html xmlns="http://www.w3.org/1999/xhtml" lang="zh-CN" xml:lang="zh-CN">
<head>
  <title>{safe_title}</title>
  <link rel="stylesheet" type="text/css" href="../Styles/default.css"/>
</head>
<body>
{body_inner}
</body>
</html>
"""


def _infer_title(article: html.HtmlElement, fallback: str) -> str:
    for xpath in (".//h1", ".//header//h1", ".//h2"):
        nodes = article.xpath(xpath)
        if nodes:
            text = re.sub(r"\s+", " ", nodes[0].text_content() or "").strip()
            if text:
                return text
    return fallback


def parse_chapter_html(
    page_html: str,
    *,
    page_url: str,
    chapter_title: str,
    chapter_index: int,
    client: SiteClient,
    url_to_epub: dict[str, str],
) -> ParsedChapter:
    doc = html.fromstring(page_html)
    article = _find_article(doc)
    article = html.fromstring(tostring(article, encoding="unicode"))
    _remove_footers(article)
    _strip_unsafe(article)
    _rewrite_links(article, page_url, url_to_epub)
    images = _process_images(article, page_url, client, chapter_index)
    body = _serialize_article_fragment(article)
    title = _infer_title(article, chapter_title)
    return ParsedChapter(title=title, xhtml_body=_wrap_xhtml(body, title), images=images)


def fetch_and_parse_chapter(
    client: SiteClient,
    *,
    chapter_url: str,
    chapter_title: str,
    chapter_index: int,
    url_to_epub: dict[str, str],
) -> ParsedChapter:
    page_html = client.get_text(chapter_url)
    return parse_chapter_html(
        page_html,
        page_url=chapter_url,
        chapter_title=chapter_title,
        chapter_index=chapter_index,
        client=client,
        url_to_epub=url_to_epub,
    )
