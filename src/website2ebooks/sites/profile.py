from __future__ import annotations

from collections.abc import Callable, Mapping
from dataclasses import dataclass, field
from pathlib import Path
from typing import TYPE_CHECKING, Literal

from website2ebooks.nav import ChapterRef

if TYPE_CHECKING:
    from website2ebooks.article import ParsedChapter
    from website2ebooks.fetch_run import FetchContext
    from website2ebooks.http import SiteClient

SiteId = Literal["buffett", "munger"]


@dataclass(frozen=True)
class SiteProfile:
    id: SiteId
    nav_index_url: str
    book_title: str
    default_output: Path
    parse_chapters: Callable[[Callable[[str], str], str], list[ChapterRef]]
    parse_chapter: Callable[
        ["SiteClient", ChapterRef, int, "FetchContext"],
        "ParsedChapter",
    ]
    sample_section_preferred_titles: Mapping[str, str] = field(default_factory=dict)


def get_site_profile(site_id: str) -> SiteProfile:
    from website2ebooks.sites.buffett import BUFFETT_PROFILE
    from website2ebooks.sites.munger import MUNGER_PROFILE

    key = site_id.strip().lower()
    registry: dict[str, SiteProfile] = {
        "buffett": BUFFETT_PROFILE,
        "munger": MUNGER_PROFILE,
    }
    if key not in registry:
        raise ValueError(
            f"Unknown site {site_id!r}; choose from: {', '.join(registry)}"
        )
    return registry[key]
