from pathlib import Path

import pytest

from website2ebooks.http import SiteClient
from website2ebooks.munger_article import (
    parse_munger_qa_chapter_html,
    parse_munger_reader_page_html,
)

FIXTURE_READER = Path(__file__).parent / "fixtures" / "munger_reader_two_chapters.html"
FIXTURE_SOURCE = Path(__file__).parent / "fixtures" / "munger_source_snippet.html"


@pytest.mark.skipif(not FIXTURE_READER.exists(), reason="reader fixture missing")
def test_parse_munger_qa_chapter() -> None:
    html_text = FIXTURE_READER.read_text(encoding="utf-8")
    client = SiteClient(delay=0)
    parsed = parse_munger_qa_chapter_html(
        html_text,
        fragment="chapter-before-investing",
        chapter_title="投资之前，你得先知道什么？",
        chapter_index=1,
        client=client,
        page_url="https://munger.ayaseeri.com/books/munger-qa/reader",
    )
    assert "测试答案一" in parsed.xhtml_body
    assert "测试问题一" in parsed.xhtml_body or "投资之前" in parsed.title


@pytest.mark.skipif(not FIXTURE_SOURCE.exists(), reason="source fixture missing")
def test_parse_munger_reader_page() -> None:
    html_text = FIXTURE_SOURCE.read_text(encoding="utf-8")
    client = SiteClient(delay=0)
    parsed = parse_munger_reader_page_html(
        html_text,
        page_url="https://munger.ayaseeri.com/sources/example/",
        chapter_title="示例原文",
        chapter_index=1,
        client=client,
    )
    assert "股东会正文段落" in parsed.xhtml_body
