"""Parallel HTTP fetch + HTML → text (tables flattened to lines) for synthesis context."""

from __future__ import annotations

import asyncio
from typing import Any

import httpx
from bs4 import BeautifulSoup, NavigableString

_DEFAULT_UA = (
    "Mozilla/5.0 (compatible; SearchAgent/1.0; +https://github.com/) "
    "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
)


def _html_to_text(html: str, max_chars: int) -> str:
    soup = BeautifulSoup(html, "html.parser")
    for tag in soup(["script", "style", "noscript", "svg", "template"]):
        tag.decompose()
    for table in soup.find_all("table"):
        rows: list[str] = []
        for tr in table.find_all("tr"):
            cells = [
                c.get_text(separator=" ", strip=True)
                for c in tr.find_all(["th", "td"])
            ]
            if cells:
                rows.append(" | ".join(cells))
        if rows:
            table.replace_with(NavigableString("\n[TABLE]\n" + "\n".join(rows) + "\n[/TABLE]\n"))
    text = soup.get_text(separator="\n", strip=True)
    lines = [ln.strip() for ln in text.splitlines() if ln.strip()]
    out = "\n".join(lines)
    if len(out) > max_chars:
        out = out[: max_chars - 20] + "\n…(truncated)"
    return out


class PageFetchService:
    """Fetch several URLs concurrently (bounded concurrency); extract readable text."""

    def __init__(
        self,
        *,
        max_concurrent: int = 4,
        timeout_s: float = 18.0,
        max_response_bytes: int = 800_000,
        max_chars_per_page: int = 14_000,
    ) -> None:
        self._max_concurrent = max(1, max_concurrent)
        self._timeout = timeout_s
        self._max_response_bytes = max_response_bytes
        self._max_chars = max_chars_per_page

    @staticmethod
    def _safe_http_url(url: str) -> bool:
        u = url.strip().lower()
        return u.startswith("http://") or u.startswith("https://")

    async def fetch_many(self, urls: list[str]) -> list[dict[str, Any]]:
        if not urls:
            return []
        sem = asyncio.Semaphore(self._max_concurrent)
        limits = httpx.Limits(max_keepalive_connections=5, max_connections=10)
        headers = {"User-Agent": str(_DEFAULT_UA)}
        timeout = httpx.Timeout(self._timeout, connect=10.0)

        async def one(client: httpx.AsyncClient, url: str) -> dict[str, Any]:
            base = {"url": url, "ok": False, "text": "", "error": None}
            if not self._safe_http_url(url):
                base["error"] = "unsupported_url"
                return base
            async with sem:
                try:
                    r = await client.get(url, headers=headers, follow_redirects=True)
                    r.raise_for_status()
                    ct = (r.headers.get("content-type") or "").lower()
                    if "text/html" not in ct and "application/xhtml" not in ct:
                        if "text/" not in ct and ct:
                            base["error"] = f"non_html:{ct.split(';')[0].strip()}"
                            return base
                    body = r.content
                    if len(body) > self._max_response_bytes:
                        body = body[: self._max_response_bytes]
                    html = body.decode("utf-8", errors="replace")
                    text = _html_to_text(html, self._max_chars)
                    if not text.strip():
                        base["error"] = "empty_extract"
                        return base
                    base["ok"] = True
                    base["text"] = text
                except httpx.HTTPStatusError as e:
                    base["error"] = f"http_{e.response.status_code}"
                except httpx.RequestError as e:
                    base["error"] = str(e)[:200]
                except Exception as e:  # pragma: no cover
                    base["error"] = str(e)[:200]
            return base

        async with httpx.AsyncClient(timeout=timeout, limits=limits) as client:
            return await asyncio.gather(*[one(client, u) for u in urls])
