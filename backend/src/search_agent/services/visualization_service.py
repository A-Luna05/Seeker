from __future__ import annotations

import base64
import io
from typing import Any

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402


class VisualizationService:
    """Matplotlib charts as PNG base64."""

    def chart_result_counts(self, labels: list[str], values: list[int]) -> str:
        fig, ax = plt.subplots(figsize=(6, 3.5))
        ax.bar(labels, values, color="#4C72B0")
        ax.set_ylabel("Count")
        ax.set_title("Sources used")
        plt.tight_layout()
        buf = io.BytesIO()
        fig.savefig(buf, format="png", dpi=120)
        plt.close(fig)
        return base64.b64encode(buf.getvalue()).decode("ascii")

    def chart_from_state_context(self, state: dict[str, Any]) -> str | None:
        web = state.get("web_results") or []
        wiki_summary = (state.get("wiki_summary") or "").strip()
        labels: list[str] = []
        values: list[int] = []
        if web:
            labels.append("web_hits")
            values.append(len(web))
        if wiki_summary:
            labels.append("wiki")
            values.append(max(1, len(wiki_summary.split())))
        if not labels:
            return None
        return self.chart_result_counts(labels, values)

    def chart_stock_daily_closes_png(
        self,
        *,
        symbol: str,
        name: str | None,
        points: list[dict[str, Any]],
    ) -> bytes | None:
        """PNG bytes for PDF embedding (mirrors UI stock series, not the React canvas)."""
        dates: list[str] = []
        closes: list[float] = []
        for p in points:
            if not isinstance(p, dict):
                continue
            d_raw = p.get("date")
            c_raw = p.get("close")
            if d_raw is None or c_raw is None:
                continue
            try:
                closes.append(float(c_raw))
                dates.append(str(d_raw))
            except (TypeError, ValueError):
                continue
        if len(dates) < 2:
            return None
        fig, ax = plt.subplots(figsize=(7, 3.4))
        x = range(len(closes))
        ax.plot(x, closes, color="#0891b2", linewidth=1.8)
        n = len(dates)
        max_ticks = 6
        step = max(1, (n - 1) // max(1, max_ticks - 1))
        tick_idx = list(range(0, n, step))
        if tick_idx[-1] != n - 1:
            tick_idx.append(n - 1)
        ax.set_xticks(tick_idx)
        ax.set_xticklabels([dates[i] for i in tick_idx], rotation=22, ha="right", fontsize=8)
        ax.set_ylabel("Close (USD)")
        lbl = (name or "").strip() or symbol
        ax.set_title(f"{lbl} ({symbol}) — daily close", fontsize=11)
        ax.grid(True, alpha=0.35)
        plt.tight_layout()
        buf = io.BytesIO()
        fig.savefig(buf, format="png", dpi=120)
        plt.close(fig)
        return buf.getvalue()
