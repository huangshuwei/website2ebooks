from __future__ import annotations

import argparse
import logging
import sys
from pathlib import Path

from website2ebooks.epub_export import build_epub
from website2ebooks.fetch_run import fetch_chapters_serial, format_fetch_report
from website2ebooks.http import SiteClient
from website2ebooks.nav import (
    indices_for_named_sections,
    indices_for_one_per_toc_section,
)
from website2ebooks.sites import get_site_profile
from website2ebooks.toc_page import chapter_toc_section


def _configure_logging(verbose: bool) -> None:
    level = logging.DEBUG if verbose else logging.INFO
    logging.basicConfig(
        level=level,
        format="%(levelname)s %(message)s",
    )


def _default_report_path(output: Path) -> Path:
    return output.parent / f"{output.stem}-fetch-report.txt"


def run(
    *,
    output: Path,
    book_url: str,
    content_limit: int | None,
    sample_per_section: bool,
    sample_section_names: list[str] | None,
    delay: float,
    book_title: str,
    chapter_success_delay: float | None,
    max_retries: int | None,
    retry_delay: float,
    report_path: Path | None,
    site_id: str,
) -> int:
    profile = get_site_profile(site_id)
    with SiteClient(delay=delay) as client:
        all_chapters = profile.parse_chapters(client.get_text, book_url)
        if not all_chapters:
            raise SystemExit("No chapters found in nav.")

        unlimited = (
            not sample_per_section
            and not sample_section_names
            and (content_limit is None or content_limit <= 0)
        )
        preferred_titles = profile.sample_section_preferred_titles
        if sample_section_names:
            fetch_indices = indices_for_named_sections(
                all_chapters,
                sample_section_names,
                preferred_title_by_section=preferred_titles,
            )
            matched = {
                chapter_toc_section(all_chapters[i - 1]) for i in fetch_indices
            }
            for name in sample_section_names:
                key = name.strip()
                if key and key not in matched:
                    logging.warning(
                        "No chapter in toc section %r for --sample-sections",
                        key,
                    )
            fetch_count = len(fetch_indices)
        elif sample_per_section:
            fetch_indices = indices_for_one_per_toc_section(
                all_chapters,
                preferred_title_by_section=preferred_titles,
            )
            fetch_count = len(fetch_indices)
        elif unlimited:
            fetch_indices = frozenset(range(1, len(all_chapters) + 1))
            fetch_count = len(all_chapters)
        else:
            limit = min(content_limit or 0, len(all_chapters))
            fetch_indices = frozenset(range(1, limit + 1))
            fetch_count = limit

        if unlimited:
            effective_chapter_delay = (
                5.0 if chapter_success_delay is None else chapter_success_delay
            )
            effective_max_retries = 3 if max_retries is None else max_retries
        else:
            effective_chapter_delay = chapter_success_delay or 0.0
            effective_max_retries = 1 if max_retries is None else max_retries

        parsed, outcomes = fetch_chapters_serial(
            client,
            all_chapters,
            fetch_indices,
            profile=profile,
            fetch_count=fetch_count,
            max_retries=effective_max_retries,
            retry_delay=retry_delay,
            chapter_success_delay=effective_chapter_delay,
        )

        build_epub(all_chapters, parsed, output, book_title=book_title)

        if outcomes:
            report = format_fetch_report(
                outcomes,
                book_title=book_title,
                output_path=str(output),
            )
            dest = report_path or _default_report_path(output)
            dest.parent.mkdir(parents=True, exist_ok=True)
            dest.write_text(report, encoding="utf-8")
            failed = sum(1 for o in outcomes if o.status == "failed")
            ok = len(outcomes) - failed
            logging.info(
                "Fetch summary: %s ok, %s failed (report: %s)",
                ok,
                failed,
                dest,
            )

        if sample_per_section or sample_section_names:
            logging.info(
                "Wrote %s (%s toc entries, %s with full content, %s sections sampled)",
                output,
                len(all_chapters),
                fetch_count,
                fetch_count,
            )
        else:
            logging.info(
                "Wrote %s (%s toc entries, %s with full content)",
                output,
                len(all_chapters),
                fetch_count,
            )

        if outcomes and any(o.status == "failed" for o in outcomes):
            return 1
        return 0


def main(argv: list[str] | None = None) -> None:
    parser = argparse.ArgumentParser(
        description="Generate EPUB from ayaseeri.com knowledge-base sidebar navigation.",
    )
    parser.add_argument(
        "--site",
        choices=("buffett", "munger"),
        default="buffett",
        help="Site preset (default: buffett)",
    )
    parser.add_argument(
        "--output",
        "-o",
        type=Path,
        default=None,
        help="Output EPUB path (default depends on --site)",
    )
    parser.add_argument(
        "--book-url",
        default=None,
        help="Nav index URL (default depends on --site)",
    )
    parser.add_argument(
        "--content-limit",
        type=int,
        default=2,
        help="Fetch full article HTML for first N chapters (default: 2). "
        "TOC always includes all nav entries.",
    )
    parser.add_argument(
        "--all",
        action="store_true",
        help="Fetch all chapters (same as --content-limit 0)",
    )
    parser.add_argument(
        "--sample-per-section",
        action="store_true",
        help="Fetch full content for the first chapter in each sidebar toc section "
        "(toc_path[0]); remaining entries are stub pages.",
    )
    parser.add_argument(
        "--sample-sections",
        default=None,
        metavar="NAMES",
        help="Comma-separated toc section names (toc_path[0]); fetch the first chapter "
        "in each named section. Mutually exclusive with --content-limit/--all.",
    )
    parser.add_argument(
        "--limit",
        type=int,
        default=None,
        help=argparse.SUPPRESS,
    )
    parser.add_argument(
        "--delay",
        type=float,
        default=0.5,
        help="Seconds to wait between HTTP requests",
    )
    parser.add_argument(
        "--chapter-success-delay",
        type=float,
        default=None,
        help="Seconds to wait after each chapter fetch succeeds "
        "(default: 5 for --all, 0 otherwise)",
    )
    parser.add_argument(
        "--max-retries",
        type=int,
        default=None,
        help="Max attempts per chapter (default: 3 for --all, 1 otherwise)",
    )
    parser.add_argument(
        "--retry-delay",
        type=float,
        default=2.0,
        help="Extra seconds between failed attempts for the same chapter",
    )
    parser.add_argument(
        "--report",
        type=Path,
        default=None,
        help="Write fetch summary report to this path "
        "(default: <output-stem>-fetch-report.txt next to EPUB)",
    )
    parser.add_argument(
        "--title",
        default=None,
        help="EPUB metadata title (default depends on --site)",
    )
    parser.add_argument("--verbose", "-v", action="store_true")
    args = parser.parse_args(argv)
    _configure_logging(args.verbose)

    profile = get_site_profile(args.site)
    book_url = args.book_url or profile.nav_index_url
    book_title = args.title or profile.book_title
    output = args.output or profile.default_output

    content_limit: int | None = args.content_limit
    sample_per_section = args.sample_per_section
    sample_section_names: list[str] | None = None
    if args.sample_sections:
        sample_section_names = [
            s.strip() for s in args.sample_sections.split(",") if s.strip()
        ]
    if args.all:
        content_limit = 0
        sample_per_section = False
        sample_section_names = None
    if args.limit is not None:
        content_limit = args.limit
        sample_per_section = False
        sample_section_names = None
    if sample_section_names:
        sample_per_section = False
        content_limit = None

    try:
        exit_code = run(
            output=output,
            book_url=book_url,
            content_limit=content_limit,
            sample_per_section=sample_per_section,
            sample_section_names=sample_section_names,
            delay=args.delay,
            book_title=book_title,
            chapter_success_delay=args.chapter_success_delay,
            max_retries=args.max_retries,
            retry_delay=args.retry_delay,
            report_path=args.report,
            site_id=args.site,
        )
    except KeyboardInterrupt:
        raise SystemExit(130) from None
    except Exception as exc:
        logging.error("%s", exc)
        raise SystemExit(1) from exc
    else:
        raise SystemExit(exit_code)


if __name__ == "__main__":
    main(sys.argv[1:])
