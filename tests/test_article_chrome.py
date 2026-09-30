from lxml import html

from website2ebooks.article import _serialize_article_fragment, _strip_article_chrome


def test_strip_article_chrome_removes_book_header_noise() -> None:
    fragment = """
    <article>
      <header><p>巴菲特问答录</p><p>30 问</p></header>
      <p>编者导读</p>
      <h3>第 1 问 正文开始</h3>
    </article>
    """
    article = html.fromstring(fragment)
    _strip_article_chrome(article)
    out = _serialize_article_fragment(article)
    assert "巴菲特问答录" not in out
    assert "30 问" not in out
    assert "编者导读" in out
    assert "正文开始" in out


def test_strip_article_chrome_does_not_remove_qa_movement_sections() -> None:
    fragment = """
    <article>
      <header><p>巴菲特问答录</p></header>
      <section class="qa-movement">
        <p>第1节 看懂如何赚钱</p>
        <h3>第 31 问 正文保留</h3>
      </section>
    </article>
    """
    article = html.fromstring(fragment)
    _strip_article_chrome(article)
    out = _serialize_article_fragment(article)
    assert "qa-movement" in out
    assert "第 31 问" in out
    assert "正文保留" in out
