from __future__ import annotations

from dataclasses import dataclass

import httpx


@dataclass
class WebHit:
    title: str
    url: str
    snippet: str


_BRAVE_WEB_SEARCH_URL = "https://api.search.brave.com/res/v1/web/search"


class DuckDuckGoService:
    """Web text search: optional Brave Search API (reliable from cloud hosts), then ``ddgs`` / DuckDuckGo."""

    def __init__(
        self,
        *,
        brave_search_api_key: str | None = None,
    ) -> None:
        self._brave_key = (brave_search_api_key or "").strip() or None

    def _brave_search_sync(self, query: str, *, max_results: int) -> list[WebHit]:
        if not self._brave_key:
            return []
        n = min(max(1, max_results), 20)
        try:
            r = httpx.get(
                _BRAVE_WEB_SEARCH_URL,
                params={"q": query.strip(), "count": n},
                headers={"X-Subscription-Token": self._brave_key},
                timeout=25.0,
            )
            if not r.is_success:
                return []
            data = r.json()
        except (httpx.HTTPError, ValueError):
            return []
        web = data.get("web")
        if not isinstance(web, dict):
            return []
        results = web.get("results")
        if not isinstance(results, list):
            return []
        hits: list[WebHit] = []
        for it in results:
            if not isinstance(it, dict):
                continue
            desc = it.get("description")
            if desc is None:
                desc = ""
            hits.append(
                WebHit(
                    title=str(it.get("title", ""))[:500],
                    url=str(it.get("url", ""))[:2000],
                    snippet=str(desc)[:1500],
                )
            )
        return hits

    def _ddgs_search_sync(self, query: str, *, max_results: int) -> list[WebHit]:
        try:
            from ddgs import DDGS
        except ImportError as e:  # pragma: no cover
            raise ImportError("ddgs is required (pip install ddgs)") from e

        q = query.strip()
        if not q:
            return []
        hits: list[WebHit] = []
        try:
            from ddgs.exceptions import DDGSException
        except ImportError:  # pragma: no cover
            DDGSException = Exception  # type: ignore[misc, assignment]
        try:
            with DDGS() as ddgs:
                for r in ddgs.text(q, max_results=max_results, backend="duckduckgo"):
                    hits.append(
                        WebHit(
                            title=str(r.get("title", ""))[:500],
                            url=str(r.get("href", ""))[:2000],
                            snippet=str(r.get("body", ""))[:1500],
                        )
                    )
        except DDGSException:
            pass
        return hits

    def search_sync(self, query: str, *, max_results: int = 5) -> list[WebHit]:
        q = query.strip()
        if not q:
            return []
        if self._brave_key:
            b = self._brave_search_sync(q, max_results=max_results)
            if b:
                return b
        return self._ddgs_search_sync(q, max_results=max_results)

    async def search(self, query: str, *, max_results: int = 5) -> list[WebHit]:
        import asyncio

        return await asyncio.to_thread(self.search_sync, query, max_results=max_results)
