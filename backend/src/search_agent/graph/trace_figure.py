from __future__ import annotations

import io
import math
from typing import Any

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402

# Max nodes per row before wrapping (PDF stays letter-width friendly).
_TRACE_COLS = 5
_SPACING_X = 10.0
_ROW_STEP_Y = 7.8


def trace_figure_png(run_trace: list[dict[str, Any]], *, figscale: float = 1.0) -> bytes | None:
    if not run_trace:
        return None
    labels: list[str] = []
    for i, step in enumerate(run_trace):
        node = str(step.get("node", f"step_{i}"))
        title = str(step.get("title", ""))[:40]
        labels.append(f"{node}\n{title}" if title else node)
    n = len(labels)
    cols = min(_TRACE_COLS, n)
    rows = max(1, math.ceil(n / cols))

    def center(i: int) -> tuple[float, float]:
        r, c = divmod(i, cols)
        x = c * _SPACING_X + 2.0
        y = (rows - 1 - r) * _ROW_STEP_Y + 5.6
        return x, y

    fig_w = min(14.0, max(6.5, cols * 2.15 + 1.5)) * figscale
    fig_h = max(2.8, 1.2 + rows * 2.25) * figscale
    fig, ax = plt.subplots(figsize=(fig_w, fig_h))
    ax.set_xlim(-1.5, cols * _SPACING_X + 3.5)
    ax.set_ylim(1.0, rows * _ROW_STEP_Y + 5.0)
    ax.axis("off")

    for i, lab in enumerate(labels):
        cx, cy = center(i)
        box = plt.Rectangle(
            (cx - 1.6, cy - 1.6),
            3.2,
            3.2,
            fill=True,
            facecolor="#ecfeff",
            edgecolor="#06b6d4",
        )
        ax.add_patch(box)
        ax.text(cx, cy, lab, ha="center", va="center", fontsize=7, linespacing=1.15)
        if i == 0:
            continue
        px, py = center(i - 1)
        x0, y0 = px + 1.55, py
        x1, y1 = cx - 1.55, cy
        same_row = abs(py - cy) < 0.01
        if same_row:
            style: dict[str, Any] = dict(arrowstyle="->", color="#333", lw=1.15)
        else:
            # Visual “wrap” to the next row (bend so the arrow does not slice through boxes).
            style = dict(
                arrowstyle="->",
                color="#333",
                lw=1.15,
                connectionstyle="arc3,rad=-0.35",
            )
        ax.annotate("", xy=(x1, y1), xytext=(x0, y0), arrowprops=style)

    ax.set_title("Agent run trace (rows: top → bottom, within a row: left → right)")
    buf = io.BytesIO()
    fig.savefig(buf, format="png", dpi=140, bbox_inches="tight")
    plt.close(fig)
    return buf.getvalue()
