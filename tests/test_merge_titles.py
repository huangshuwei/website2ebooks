from website2ebooks.article import merge_chapter_titles


def test_merge_titles_identical() -> None:
    assert merge_chapter_titles("企业价值", "企业价值") == "企业价值"


def test_merge_titles_different_uses_colon() -> None:
    nav = "企业价值"
    body = "好生意为什么能持续赚钱 30 问"
    assert merge_chapter_titles(nav, body) == f"{nav}：{body}"


def test_merge_titles_body_starts_with_nav() -> None:
    body = "企业价值：深入理解估值"
    assert merge_chapter_titles("企业价值", body) == body


def test_merge_titles_empty_body() -> None:
    assert merge_chapter_titles("能力圈", None) == "能力圈"
    assert merge_chapter_titles("能力圈", "") == "能力圈"
