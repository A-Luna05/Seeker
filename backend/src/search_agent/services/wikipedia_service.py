from __future__ import annotations

import re
import warnings
from dataclasses import dataclass
from typing import Any

try:
    from bs4 import GuessedAtParserWarning
except ImportError:
    pass
else:
    # PyPI `wikipedia` uses BeautifulSoup without features=...; we don't control that package.
    warnings.filterwarnings("ignore", category=GuessedAtParserWarning)


@dataclass
class WikiResult:
    title: str
    summary: str
    url: str


# Words that should not drive “which article” disambiguation alone
_STOP = frozenset(
    """
    the a an and or for to of in is it as at be by if on so that this with from
    user seeks seek seeking tell about describe what who when where which why how
    suitable overview background achievements achievement information summary
    professional basketball player nba game games team teams year years
    his her their our your my its one two
    """.split()
)


def _distinctive_tokens(query: str) -> set[str]:
    words = re.findall(r"[A-Za-z]{3,}", query)
    return {w.lower() for w in words if w.lower() not in _STOP}


def _title_matches_query(title: str, tokens: set[str]) -> int:
    """Higher score = title is more consistent with query tokens (e.g. lebron + james)."""
    if not tokens:
        return 0
    t = title.lower()
    return sum(1 for w in tokens if w in t)


def _pick_best_title(hits: list[str], tokens: set[str]) -> str | None:
    """Return a hit only if at least one query token appears in the title — never arbitrary hits[0]."""
    best_title: str | None = None
    best_score = 0
    for title in hits:
        score = _title_matches_query(title, tokens)
        if score > best_score:
            best_score = score
            best_title = title
    return best_title if best_score > 0 else None


_BAD_LEAD = frozenset(
    {
        "User",
        "Tell",
        "Describe",
        "What",
        "Give",
        "Find",
        "Show",
        "List",
        "Explain",
        "Please",
        "The",
        "A",
        "An",
        "How",
        "Why",
        "When",
        "Where",
        "Which",
    }
)


def _entity_phrases(query: str) -> list[str]:
    """
    Pull likely article titles from the query, e.g. 'LeBron James' in a long question.
    Longer / more specific phrases first.
    """
    found = re.findall(
        r"\b[A-Z][a-zA-Z0-9]*(?:\s+[A-Z][a-zA-Z0-9]*)+\b",
        query,
    )
    seen: set[str] = set()
    out: list[str] = []
    for p in sorted(found, key=len, reverse=True):
        parts = p.split()
        if parts and parts[0] in _BAD_LEAD:
            continue
        key = p.lower()
        if key not in seen:
            seen.add(key)
            out.append(p.strip())
    return out


def _ordered_keywords(query: str, tokens: set[str]) -> str:
    """Preserve query word order for tokens (e.g. 'LeBron James'), for focused search/suggest."""
    words = re.findall(r"[A-Za-z]+", query)
    out: list[str] = []
    seen: set[str] = set()
    for w in words:
        wl = w.lower()
        if wl not in tokens or wl in seen or len(wl) < 3:
            continue
        seen.add(wl)
        out.append(w)
    return " ".join(out)


class WikipediaService:
    def summarize_sync(self, query: str, *, sentences: int = 5) -> WikiResult | None:
        try:
            import wikipedia
        except ImportError as e:  # pragma: no cover
            raise ImportError("wikipedia is required") from e

        q = query.strip()
        if not q:
            return None
        wikipedia.set_lang("en")

        import wikipedia as wiki_mod

        tokens = _distinctive_tokens(q)

        def load_page(title: str, *, suggest: bool) -> Any:
            try:
                return wiki_mod.page(title=title, auto_suggest=suggest)
            except wiki_mod.exceptions.DisambiguationError as e:
                options = list(e.options or [])
                if not options:
                    return None
                pick = _pick_best_title(options, tokens)
                if pick is None and options:
                    pick = options[0]
                if pick is None:
                    return None
                try:
                    return wiki_mod.page(pick, auto_suggest=False)
                except Exception:
                    return None
            except Exception:
                return None

        # 1) Likely person/entity phrases ("LeBron James") — not the whole question as a title
        for phrase in _entity_phrases(q):
            page = load_page(phrase, suggest=True)
            if page is not None:
                return self._result_from_page(page, sentences)

        focused = _ordered_keywords(q, tokens)

        # 2) Suggest only on focused keywords (full question suggest often returns wrong page)
        if focused:
            try:
                sug = wiki_mod.suggest(focused)
                if sug and _title_matches_query(sug, tokens) > 0:
                    page = load_page(sug, suggest=False)
                    if page is not None:
                        return self._result_from_page(page, sentences)
            except Exception:
                pass

        # 3) Search full query; only accept titles that share tokens with the question
        try:
            hits = wiki_mod.search(q, results=15)
        except Exception:
            hits = []
        pick = _pick_best_title(hits, tokens)

        # 4) Focused search (keywords in original order) when broad search matched nothing relevant
        if pick is None and focused:
            try:
                hits_f = wiki_mod.search(focused, results=15)
            except Exception:
                hits_f = []
            pick = _pick_best_title(hits_f, tokens)

        if pick:
            page = load_page(pick, suggest=False)
            if page is not None:
                return self._result_from_page(page, sentences)

        return None

    def _result_from_page(self, page: object, sentences: int) -> WikiResult:
        import wikipedia as wiki_mod

        title = getattr(page, "title", "") or ""
        url = getattr(page, "url", "") or ""
        try:
            summary = wiki_mod.summary(title, sentences=sentences)
        except Exception:
            summary = ""
        return WikiResult(title=title, summary=summary or "", url=url)

    async def summarize(self, query: str, *, sentences: int = 5) -> WikiResult | None:
        import asyncio

        first = await asyncio.to_thread(self.summarize_sync, query, sentences=sentences)
        if first is not None:
            return first
        await asyncio.sleep(0.35)
        return await asyncio.to_thread(self.summarize_sync, query, sentences=sentences)
