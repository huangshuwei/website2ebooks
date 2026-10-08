from __future__ import annotations

import logging
import time
from dataclasses import dataclass, field
from typing import Literal

from website2ebooks.article import (
    ParsedChapter,
    make_stub_chapter,
    make_stub_fetch_failed_chapter,
)
from website2ebooks.http import SiteClient
from website2ebooks.munger_nav import MUNGER_READER_URL
from website2ebooks.nav import ChapterRef
from website2ebooks.sites.profile import SiteProfile
from website2ebooks.toc_page import chapter_toc_section

logger = logging.getLogger(__name__)


@dataclass
class FetchContext:
    munger_qa_reader_html: str | None = field(default=None)
    _munger_reader_loaded: bool = field(default=False, repr=False)


@dataclass(frozen=True)
class ChapterFetchOutcome:
    index: int
    title: str
    url: str
    status: Literal["ok", "failed"]
    attempts: int
    error: str | None
    parsed: ParsedChapter


def _ensure_munger_reader_cache(
    client: SiteClient,
    ctx: FetchContext,
    chapter: ChapterRef,
) -> None:
    if chapter.kind != "munger_qa" or ctx._munger_reader_loaded:
        return
    ctx.munger_qa_reader_html = client.get_text(MUNGER_READER_URL)
    ctx._munger_reader_loaded = True


def fetch_chapter_with_retry(
    client: SiteClient,
    chapter: ChapterRef,
    chapter_index: int,
    *,
    profile: SiteProfile,
    fetch_ctx: FetchContext,
    max_retries: int,
    retry_delay: float,
) -> ChapterFetchOutcome:
    last_error: str | None = None
    attempts = max(1, max_retries)
    for attempt in range(1, attempts + 1):
        try:
            _ensure_munger_reader_cache(client, fetch_ctx, chapter)
            parsed = profile.parse_chapter(
                client, chapter, chapter_index, fetch_ctx
            )
            return ChapterFetchOutcome(
                index=chapter_index,
                title=chapter.title,
                url=chapter.url,
                status="ok",
                attempts=attempt,
                error=None,
                parsed=parsed,
            )
        except Exception as exc:
            last_error = str(exc)
            logger.warning(
                "Chapter fetch failed (attempt %s/%s) [%s] %s: %s",
                attempt,
                attempts,
                chapter_index,
                chapter.title,
                last_error,
            )
            if attempt < attempts and retry_delay > 0:
                time.sleep(retry_delay)
    assert last_error is not None
    stub = make_stub_fetch_failed_chapter(
        chapter.title,
        attempts=attempts,
        error=last_error,
    )
    return ChapterFetchOutcome(
        index=chapter_index,
        title=chapter.title,
        url=chapter.url,
        status="failed",
        attempts=attempts,
        error=last_error,
        parsed=stub,
    )


def fetch_chapters_serial(
    client: SiteClient,
    all_chapters: list[ChapterRef],
    fetch_indices: frozenset[int],
    *,
    profile: SiteProfile,
    fetch_count: int,
    max_retries: int,
    retry_delay: float,
    chapter_success_delay: float,
) -> tuple[list[ParsedChapter], list[ChapterFetchOutcome]]:
    parsed: list[ParsedChapter] = []
    outcomes: list[ChapterFetchOutcome] = []
    fetched_so_far = 0
    logged_stub = False
    sorted_fetch = sorted(fetch_indices)
    fetch_ctx = FetchContext()

    for index, chapter in enumerate(all_chapters, start=1):
        if index in fetch_indices:
            fetched_so_far += 1
            section = chapter_toc_section(chapter) or "(flat)"
            logger.info(
                "[fetch %s/%s] [组: %s] %s — %s",
                fetched_so_far,
                fetch_count,
                section,
                chapter.title,
                chapter.url,
            )
            outcome = fetch_chapter_with_retry(
                client,
                chapter,
                index,
                profile=profile,
                fetch_ctx=fetch_ctx,
                max_retries=max_retries,
                retry_delay=retry_delay,
            )
            outcomes.append(outcome)
            parsed.append(outcome.parsed)
            if (
                outcome.status == "ok"
                and chapter_success_delay > 0
                and index != sorted_fetch[-1]
            ):
                time.sleep(chapter_success_delay)
        else:
            if not logged_stub:
                logger.info(
                    "Skipping fetch for remaining %s chapters (stub pages only)",
                    len(all_chapters) - fetch_count,
                )
                logged_stub = True
            parsed.append(make_stub_chapter(chapter.title))

    return parsed, outcomes


def format_fetch_report(
    outcomes: list[ChapterFetchOutcome],
    *,
    book_title: str,
    output_path: str,
) -> str:
    ok = [o for o in outcomes if o.status == "ok"]
    failed = [o for o in outcomes if o.status == "failed"]
    lines = [
        f"书名: {book_title}",
        f"输出: {output_path}",
        f"抓取合计: {len(outcomes)} 章",
        f"成功: {len(ok)}",
        f"失败: {len(failed)}",
        "",
    ]
    if ok:
        lines.append("=== 成功章节 ===")
        for o in ok:
            lines.append(f"  [{o.index}] {o.title} ({o.attempts} 次尝试)")
            lines.append(f"      {o.url}")
        lines.append("")
    if failed:
        lines.append("=== 失败章节 ===")
        for o in failed:
            lines.append(f"  [{o.index}] {o.title} ({o.attempts} 次尝试)")
            lines.append(f"      {o.url}")
            lines.append(f"      错误: {o.error}")
        lines.append("")
    return "\n".join(lines).rstrip() + "\n"
