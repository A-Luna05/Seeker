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
