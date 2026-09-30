from lxml import html

from website2ebooks.config import DEFAULT_CSS
from website2ebooks.epub_export import _prepare_chapter_xhtml


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
    assert ".text-muted" in DEFAULT_CSS
