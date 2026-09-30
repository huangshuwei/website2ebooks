from __future__ import annotations

import time
from typing import TYPE_CHECKING

import httpx

from website2ebooks.config import DEFAULT_USER_AGENT

if TYPE_CHECKING:
    from collections.abc import Iterator


class SiteClient:
    def __init__(self, delay: float = 0.5, timeout: float = 60.0) -> None:
        self.delay = delay
        self._last_request_at = 0.0
        self._client = httpx.Client(
            headers={"User-Agent": DEFAULT_USER_AGENT},
            timeout=timeout,
            follow_redirects=True,
        )

    def close(self) -> None:
        self._client.close()

    def __enter__(self) -> SiteClient:
        return self

    def __exit__(self, *args: object) -> None:
        self.close()

    def _wait(self) -> None:
        if self.delay <= 0:
            return
        elapsed = time.monotonic() - self._last_request_at
        if elapsed < self.delay:
            time.sleep(self.delay - elapsed)

    def get_text(self, url: str) -> str:
        self._wait()
        response = self._client.get(url)
        self._last_request_at = time.monotonic()
        response.raise_for_status()
        return response.text

    def get_bytes(self, url: str) -> tuple[bytes, str | None]:
        self._wait()
        response = self._client.get(url)
        self._last_request_at = time.monotonic()
        response.raise_for_status()
        content_type = response.headers.get("content-type")
        return response.content, content_type
