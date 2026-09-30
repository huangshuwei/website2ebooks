from __future__ import annotations

import argparse
import logging
import sys
from pathlib import Path

from website2ebooks.article import fetch_and_parse_chapter
from website2ebooks.config import BOOK_INDEX_URL, BOOK_TITLE
from website2ebooks.epub_export import build_epub, build_url_to_epub_map
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
    limit: int | None,
    delay: float,
    book_title: str,
) -> None:
    with SiteClient(delay=delay) as client:
        all_chapters = parse_chapters(client.get_text, book_url)
        chapters = all_chapters if limit is None else all_chapters[:limit]
        if not chapters:
            raise SystemExit("No chapters to export after applying filters/limit.")

        url_map = build_url_to_epub_map(chapters)
        parsed = []
        for index, chapter in enumerate(chapters, start=1):
            logging.info(
                "[%s/%s] %s — %s",
                index,
                len(chapters),
                chapter.title,
                chapter.url,
            )
            parsed.append(
                fetch_and_parse_chapter(
                    client,
                    chapter_url=chapter.url,
                    chapter_title=chapter.title,
                    chapter_index=index,
                    url_to_epub=url_map,
                )
            )

        build_epub(chapters, parsed, output, book_title=book_title)
        logging.info("Wrote %s (%s chapters)", output, len(chapters))


def main(argv: list[str] | None = None) -> None:
    parser = argparse.ArgumentParser(
        description="Generate EPUB from buffett.ayaseeri.com book navigation.",
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
        "--limit",
        type=int,
        default=None,
        help="Export only the first N chapters (for testing, e.g. 2)",
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
    try:
        run(
            output=args.output,
            book_url=args.book_url,
            limit=args.limit,
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
