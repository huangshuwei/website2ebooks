from unittest.mock import MagicMock

from lxml import html

from website2ebooks.article import (
    _serialize_article_fragment,
    _strip_leading_duplicate_title,
    parse_chapter_html,
)


def test_strip_leading_duplicate_title_removes_matching_h1() -> None:
    fragment = """
    <article>
      <h1>1956 有限合伙协议</h1>
      <p class="text-muted">致合伙人信</p>
      <h3>第一条</h3>
      <p>正文段落</p>
    </article>
    """
    article = html.fromstring(fragment)
    _strip_leading_duplicate_title(
        article,
        display_title="1956 有限合伙协议",
        nav_title="1956 有限合伙协议",
        body_title="1956 有限合伙协议",
    )
    out = _serialize_article_fragment(article)
    assert "<h1" not in out
    assert "第一条" in out
    assert "正文段落" in out


def test_parse_partner_letter_page_no_body_h1() -> None:
    page = """
    <html><body>
      <div><main><article>
        <h1>1956 有限合伙协议</h1>
        <p style="color:var(--text-muted)">致合伙人信</p>
        <h3>第一条</h3>
        <p>合伙企业名称</p>
      </article></main></div>
    </body></html>
    """
    parsed = parse_chapter_html(
        page,
        page_url="https://example.com/sources/partner-letters/1956/",
        chapter_title="1956 有限合伙协议",
        chapter_index=1,
        client=MagicMock(),
    )
    assert "<h1" not in parsed.xhtml_body.split("</head>")[-1]
    assert "text-muted" in parsed.xhtml_body
    assert "style=" not in parsed.xhtml_body
    assert "第一条" in parsed.xhtml_body
