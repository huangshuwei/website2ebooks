from unittest.mock import MagicMock

from lxml import html

from website2ebooks.article import (
    _serialize_article_fragment,
    _strip_in_chapter_toc,
    parse_chapter_html,
)


def test_strip_in_chapter_toc_removes_mobile_toc_keeps_body() -> None:
    fragment = """
    <article>
      <details class="qa-mobile-toc">
        <summary>本章目录</summary>
        <p>看懂如何赚钱</p>
        <ul><li><a href="#q1">第 1 问</a></li></ul>
      </details>
      <section class="qa-movement">
        <h3>第 1 问 正文保留</h3>
      </section>
    </article>
    """
    article = html.fromstring(fragment)
    _strip_in_chapter_toc(article)
    out = _serialize_article_fragment(article)
    assert "本章目录" not in out
    assert "看懂如何赚钱" not in out
    assert "正文保留" in out


def test_parse_chapter_strips_toc_and_merges_title() -> None:
    page = """
    <html><body>
      <div><main><article>
        <details class="qa-mobile-toc">
          <summary>本章目录</summary>
          <ul><li>分组目录项</li></ul>
        </details>
        <header class="qa-chapter-header"><h1>页头长标题示例</h1></header>
        <section class="qa-movement"><p>第 1 问 正文</p></section>
      </article></main></div>
    </body></html>
    """
    client = MagicMock()
    parsed = parse_chapter_html(
        page,
        page_url="https://example.com/ch/",
        chapter_title="企业价值",
        chapter_index=1,
        client=client,
    )
    assert parsed.title == "企业价值：页头长标题示例"
    assert "本章目录" not in parsed.xhtml_body
    assert "分组目录项" not in parsed.xhtml_body
    assert "第 1 问 正文" in parsed.xhtml_body


def test_parse_chapter_keeps_qa_movement_strips_chapter_nav() -> None:
    page = """
    <html><body>
      <div><main><article>
        <header class="qa-chapter-header"><h1>长标题</h1></header>
        <section class="qa-movement">
          <p>第1节 看懂如何赚钱</p>
          <h3>第 31 问 失去的竞争优势</h3>
          <p>沃伦·巴菲特：正文段落</p>
        </section>
        <nav class="qa-chapter-nav" aria-label="问答录章节导航">
          <a href="#q31">第 31 问</a>
          <span>看懂如何赚钱</span>
        </nav>
        <aside class="qa-chapter-closing">编者过桥</aside>
      </article></main></div>
    </body></html>
    """
    client = MagicMock()
    parsed = parse_chapter_html(
        page,
        page_url="https://example.com/ch/",
        chapter_title="企业价值",
        chapter_index=1,
        client=client,
    )
    assert "qa-chapter-nav" not in parsed.xhtml_body
    assert "第1节 看懂如何赚钱" in parsed.xhtml_body
    assert "第 31 问" in parsed.xhtml_body
    assert "沃伦" in parsed.xhtml_body
    assert "编者过桥" not in parsed.xhtml_body
