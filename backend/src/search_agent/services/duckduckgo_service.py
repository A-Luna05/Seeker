from __future__ import annotations

from dataclasses import dataclass


@dataclass
class WebHit:
    title: str
    url: str
    snippet: str


class DuckDuckGoService:
    """Web text search via the ``ddgs`` package (DuckDuckGo backend). Blocking work runs in a thread."""

    def search_sync(self, query: str, *, max_results: int = 5) -> list[WebHit]:
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
            # "No results", rate limits, or transient DDG errors — degrade gracefully
            pass
        return hits

    async def search(self, query: str, *, max_results: int = 5) -> list[WebHit]:
        import asyncio

        return await asyncio.to_thread(self.search_sync, query, max_results=max_results)
