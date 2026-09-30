from __future__ import annotations

import argparse
import logging
import sys
from pathlib import Path

from website2ebooks.article import fetch_and_parse_chapter, make_stub_chapter
from website2ebooks.config import BOOK_INDEX_URL, BOOK_TITLE
from website2ebooks.epub_export import build_epub
from website2ebooks.http import SiteClient
from website2ebooks.nav import parse_chapters


def _configure_logging(verbose: bool) -> None:
    level = logging.DEBUG if verbose else logging.INFO
    logging.basicConfig(
        level=level,
        format="%(levelname)s %(message)s",
    )


def run(
    *,
    output: Path,
    book_url: str,
    content_limit: int | None,
    delay: float,
    book_title: str,
) -> None:
    with SiteClient(delay=delay) as client:
        all_chapters = parse_chapters(client.get_text, book_url)
        if not all_chapters:
            raise SystemExit("No chapters found in nav.")

        unlimited = content_limit is None or content_limit <= 0
        fetch_count = len(all_chapters) if unlimited else min(content_limit, len(all_chapters))

        parsed = []
        for index, chapter in enumerate(all_chapters, start=1):
            if index <= fetch_count:
                logging.info(
                    "[fetch %s/%s] %s — %s",
                    index,
                    fetch_count,
                    chapter.title,
                    chapter.url,
                )
                parsed.append(
                    fetch_and_parse_chapter(
                        client,
                        chapter_url=chapter.url,
                        chapter_title=chapter.title,
                        chapter_index=index,
                    )
                )
            else:
                if index == fetch_count + 1:
                    logging.info(
                        "Skipping fetch for remaining %s chapters (stub pages only)",
                        len(all_chapters) - fetch_count,
                    )
                parsed.append(make_stub_chapter(chapter.title))

        build_epub(all_chapters, parsed, output, book_title=book_title)
        logging.info(
            "Wrote %s (%s toc entries, %s with full content)",
            output,
            len(all_chapters),
            fetch_count,
        )


def main(argv: list[str] | None = None) -> None:
    parser = argparse.ArgumentParser(
        description="Generate EPUB from buffett.ayaseeri.com sidebar navigation.",
    )
    parser.add_argument(
        "--output",
        "-o",
        type=Path,
        default=Path("dist/buffett-wenda-lu.epub"),
        help="Output EPUB path",
    )
    parser.add_argument(
        "--book-url",
        default=BOOK_INDEX_URL,
        help="Book index URL used to parse sidebar nav",
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
        "--title",
        default=BOOK_TITLE,
        help="EPUB metadata title",
    )
    parser.add_argument("--verbose", "-v", action="store_true")
    args = parser.parse_args(argv)
    _configure_logging(args.verbose)

    content_limit: int | None = args.content_limit
    if args.all:
        content_limit = 0
    if args.limit is not None:
        content_limit = args.limit

    try:
        run(
            output=args.output,
            book_url=args.book_url,
            content_limit=content_limit,
            delay=args.delay,
            book_title=args.title,
        )
    except KeyboardInterrupt:
        raise SystemExit(130) from None
    except Exception as exc:
        logging.error("%s", exc)
        raise SystemExit(1) from exc


if __name__ == "__main__":
    main(sys.argv[1:])
