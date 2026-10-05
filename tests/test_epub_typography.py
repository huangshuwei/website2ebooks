import re
import tempfile
import zipfile
from pathlib import Path

from lxml import html

from website2ebooks.article import make_stub_chapter, parse_chapter_html
from website2ebooks.config import DEFAULT_CSS
from website2ebooks.epub_export import (
    STYLE_FILE_NAME,
    _prepare_chapter_xhtml,
    _stylesheet_href_for_chapter,
    build_epub,
)
from website2ebooks.http import SiteClient
from website2ebooks.nav import ChapterRef


def test_prepare_chapter_xhtml_single_h1() -> None:
    inner = """<?xml version="1.0" encoding="utf-8"?>
<html xmlns="http://www.w3.org/1999/xhtml" lang="zh-CN">
<body epub:type="bodymatter">
<p class="text-muted">副标题</p>
<h3>第一条</h3>
</body>
</html>"""
    out = _prepare_chapter_xhtml(inner, "1956 有限合伙协议")
    doc = html.fromstring(out.encode("utf-8"))
    h1_nodes = doc.xpath("//h1")
    assert len(h1_nodes) == 1
    assert h1_nodes[0].get("class") == "chapter-title"
    assert (h1_nodes[0].text or "").startswith("1956")


def test_default_css_left_align_and_heading_scale() -> None:
    assert "text-align: left" in DEFAULT_CSS
    assert ".chapter-title" in DEFAULT_CSS
    assert ".w2e-heading" in DEFAULT_CSS
    assert ".text-muted" in DEFAULT_CSS
    assert "font-size: 1em !important" in DEFAULT_CSS
    assert "font-size: 1.25em !important" in DEFAULT_CSS


def test_stylesheet_href_from_text_chapter() -> None:
    href = _stylesheet_href_for_chapter("Text/chapter_001.xhtml", STYLE_FILE_NAME)
    assert href == "../Styles/default.css"


def test_epub_chapter_links_stylesheet_with_correct_relative_path() -> None:
    chapters = [ChapterRef("能力圈", "https://example.com/a/", ("巴菲特问答录", "能力圈"))]
    parsed = [make_stub_chapter("能力圈")]
    with tempfile.TemporaryDirectory() as tmp:
        out = Path(tmp) / "test.epub"
        build_epub(chapters, parsed, out)
        with zipfile.ZipFile(out) as zf:
            names = [n for n in zf.namelist() if "chapter_001" in n and n.endswith(".xhtml")]
            assert len(names) == 1
            body = zf.read(names[0]).decode("utf-8")
            match = re.search(r'<link[^>]+href="([^"]+)"[^>]*rel="stylesheet"', body)
            assert match is not None
            assert match.group(1) == "../Styles/default.css"


def test_parse_chapter_replaces_body_headings_with_w2e_heading() -> None:
    page = """
    <html><body><main><article>
      <section class="qa-movement">
        <header class="qa-movement-header"><h2>小节</h2></header>
        <section class="qa-question">
          <h3><span>第 1 问</span><span>问题标题</span></h3>
          <div class="qa-answer"><p>答案正文</p></div>
        </section>
      </section>
    </article></main></body></html>
    """
    with SiteClient(delay=0) as client:
        parsed = parse_chapter_html(
            page,
            page_url="https://example.com/x/",
            chapter_title="测试章",
            chapter_index=1,
            client=client,
        )
    fragment = parsed.xhtml_body.split("</head>")[-1]
    assert "<h2" not in fragment
    assert "<h3" not in fragment
    assert "w2e-heading" in fragment
    assert parsed.xhtml_body.count("<h1") == 0
