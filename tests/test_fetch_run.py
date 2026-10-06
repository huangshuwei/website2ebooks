from unittest.mock import MagicMock, patch

from website2ebooks.article import ParsedChapter, make_stub_chapter
from website2ebooks.fetch_run import (
    ChapterFetchOutcome,
    fetch_chapter_with_retry,
    fetch_chapters_serial,
    format_fetch_report,
)
from website2ebooks.nav import ChapterRef


def _parsed(title: str) -> ParsedChapter:
    return make_stub_chapter(title)


def test_fetch_chapter_with_retry_succeeds_on_third_attempt() -> None:
    chapter = ChapterRef("A", "https://example.com/a/", ("组", "A"))
    client = MagicMock()
    side_effects = [RuntimeError("net"), RuntimeError("net again"), _parsed("A")]

    with patch(
        "website2ebooks.fetch_run.fetch_and_parse_chapter",
        side_effect=side_effects,
    ) as mock_fetch:
        with patch("website2ebooks.fetch_run.time.sleep") as mock_sleep:
            outcome = fetch_chapter_with_retry(
                client,
                chapter,
                1,
                max_retries=3,
                retry_delay=2.0,
            )

    assert outcome.status == "ok"
    assert outcome.attempts == 3
    assert mock_fetch.call_count == 3
    assert mock_sleep.call_count == 2


def test_fetch_chapter_with_retry_fails_uses_stub() -> None:
    chapter = ChapterRef("B", "https://example.com/b/", ("组", "B"))
    client = MagicMock()

    with patch(
        "website2ebooks.fetch_run.fetch_and_parse_chapter",
        side_effect=ValueError("parse error"),
    ):
        outcome = fetch_chapter_with_retry(
            client,
            chapter,
            2,
            max_retries=2,
            retry_delay=0,
        )

    assert outcome.status == "failed"
    assert outcome.attempts == 2
    assert outcome.error == "parse error"
    assert "本章抓取失败" in outcome.parsed.xhtml_body


def test_fetch_chapters_serial_sleeps_after_success_not_after_last() -> None:
    chapters = [
        ChapterRef("A", "https://example.com/1/", ("组", "A")),
        ChapterRef("B", "https://example.com/2/", ("组", "B")),
        ChapterRef("C", "https://example.com/3/", ("组", "C")),
    ]
    client = MagicMock()

    with patch(
        "website2ebooks.fetch_run.fetch_chapter_with_retry",
        side_effect=[
            ChapterFetchOutcome(1, "A", "u1", "ok", 1, None, _parsed("A")),
            ChapterFetchOutcome(2, "B", "u2", "ok", 1, None, _parsed("B")),
        ],
    ):
        with patch("website2ebooks.fetch_run.time.sleep") as mock_sleep:
            parsed, outcomes = fetch_chapters_serial(
                client,
                chapters,
                frozenset({1, 2}),
                fetch_count=2,
                max_retries=1,
                retry_delay=0,
                chapter_success_delay=5.0,
            )

    assert len(parsed) == 3
    assert parsed[2].title == "C"
    assert len(outcomes) == 2
    mock_sleep.assert_called_once_with(5.0)


def test_format_fetch_report_lists_failures() -> None:
    outcomes = [
        ChapterFetchOutcome(1, "OK", "https://x/1/", "ok", 1, None, _parsed("OK")),
        ChapterFetchOutcome(
            2,
            "Bad",
            "https://x/2/",
            "failed",
            3,
            "timeout",
            _parsed("Bad"),
        ),
    ]
    text = format_fetch_report(
        outcomes,
        book_title="测试书",
        output_path="dist/out.epub",
    )
    assert "成功: 1" in text
    assert "失败: 1" in text
    assert "Bad" in text
    assert "timeout" in text
