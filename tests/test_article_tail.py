from lxml import html

from website2ebooks.article import _serialize_article_fragment, _strip_article_tail


def test_strip_article_tail_removes_prev_next_and_bridge() -> None:
    fragment = """
    <article>
      <p>正文段落</p>
      <footer><a href="#">下一章：企业价值</a></footer>
      <p>编者过桥</p>
    </article>
    """
    article = html.fromstring(fragment)
    _strip_article_tail(article)
    out = _serialize_article_fragment(article)
    assert "下一章" not in out
    assert "编者过桥" not in out
    assert "正文段落" in out
