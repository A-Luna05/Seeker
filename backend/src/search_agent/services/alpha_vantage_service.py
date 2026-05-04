from __future__ import annotations

import asyncio
import time
from typing import Any

import httpx

_ALPHAVANTAGE_QUERY = "https://www.alphavantage.co/query"
# Free / standard keys: Alpha Vantage asks for ~1 request per second; back-to-back calls get throttled.
_MIN_INTERVAL_SEC = 1.08


class AlphaVantageService:
    """Stock lookup and daily time series via Alpha Vantage REST API."""

    def __init__(self, api_key: str | None) -> None:
        self._api_key = (api_key or "").strip() or None
        self._rate_lock = asyncio.Lock()
        self._next_allowed_at = 0.0

    @property
    def configured(self) -> bool:
        return self._api_key is not None

    async def _get(self, params: dict[str, str]) -> dict[str, Any]:
        if not self._api_key:
            return {}
        q = {**params, "apikey": self._api_key}
        async with self._rate_lock:
            now = time.monotonic()
            wait = self._next_allowed_at - now
            if wait > 0:
                await asyncio.sleep(wait)
            async with httpx.AsyncClient(timeout=45.0) as client:
                r = await client.get(_ALPHAVANTAGE_QUERY, params=q)
                r.raise_for_status()
                data = r.json()
            self._next_allowed_at = time.monotonic() + _MIN_INTERVAL_SEC
        return data if isinstance(data, dict) else {}

    @staticmethod
    def _api_feedback(data: dict[str, Any]) -> str | None:
        if not data:
            return "empty response"
        for key in ("Note", "Information", "Error Message"):
            msg = data.get(key)
            if isinstance(msg, str) and msg.strip():
                return msg.strip()[:800]
        return None

    async def search_symbols(
        self, keywords: str, *, max_results: int = 5
    ) -> tuple[list[dict[str, str]], str | None]:
        """Return (matches, api_error). api_error is set when the API returns a throttle/error payload."""
        kw = keywords.strip()
        if not kw or not self._api_key:
            return [], None
        raw = await self._get({"function": "SYMBOL_SEARCH", "keywords": kw[:200]})
        err = self._api_feedback(raw)
        if err:
            return [], err
        matches = raw.get("bestMatches")
        if not isinstance(matches, list):
            return [], None
        out: list[dict[str, str]] = []
        for row in matches[:max_results]:
            if not isinstance(row, dict):
                continue
            sym = row.get("1. symbol")
            name = row.get("2. name")
            region = row.get("4. region")
            if isinstance(sym, str) and sym.strip():
                out.append(
                    {
                        "symbol": sym.strip().upper(),
                        "name": str(name).strip() if name else sym.strip().upper(),
                        "region": str(region).strip() if region else "",
                    }
                )
        return out, None

    def _pick_match(self, matches: list[dict[str, str]]) -> dict[str, str] | None:
        if not matches:
            return None
        for m in matches:
            if m.get("region") == "United States":
                return m
        return matches[0]

    async def daily_closes(
        self,
        symbol: str,
        *,
        max_points: int = 120,
    ) -> tuple[list[dict[str, Any]], str | None]:
        """Return ascending [{date, close}, ...] and optional error message."""
        sym = symbol.strip().upper()
        if not sym or not self._api_key:
            return [], "not configured" if not self._api_key else "missing symbol"
        raw = await self._get(
            {
                "function": "TIME_SERIES_DAILY",
                "symbol": sym,
                "outputsize": "compact",
            }
        )
        err = self._api_feedback(raw)
        if err:
            return [], err
        series = raw.get("Time Series (Daily)")
        if not isinstance(series, dict):
            return [], "no time series in response"
        pairs: list[tuple[str, float]] = []
        for date_key, row in series.items():
            if not isinstance(row, dict):
                continue
            close_raw = row.get("4. close")
            if close_raw is None:
                continue
            try:
                close = float(close_raw)
            except (TypeError, ValueError):
                continue
            if isinstance(date_key, str) and date_key.strip():
                pairs.append((date_key.strip(), close))
        pairs.sort(key=lambda x: x[0])
        if max_points > 0 and len(pairs) > max_points:
            pairs = pairs[-max_points:]
        points = [{"date": d, "close": c} for d, c in pairs]
        return points, None

    async def lookup_equity_series(
        self,
        keywords: str,
        *,
        max_points: int = 120,
    ) -> dict[str, Any]:
        """Resolve keywords to a US-preferred symbol and fetch daily closes."""
        matches, search_err = await self.search_symbols(keywords)
        if search_err:
            return {
                "ok": False,
                "error": search_err,
                "matches": [],
            }
        pick = self._pick_match(matches)
        if not pick:
            return {
                "ok": False,
                "error": "no symbol match",
                "matches": matches,
            }
        symbol = pick["symbol"]
        points, err = await self.daily_closes(symbol, max_points=max_points)
        if err:
            return {
                "ok": False,
                "error": err,
                "symbol": symbol,
                "name": pick.get("name"),
                "matches": matches,
            }
        return {
            "ok": True,
            "symbol": symbol,
            "name": pick.get("name"),
            "interval": "daily",
            "points": points,
            "matches": matches,
        }
