from __future__ import annotations

import base64
import re
from io import BytesIO
from typing import Any
from xml.sax.saxutils import escape

from reportlab.lib import colors
from reportlab.lib.enums import TA_LEFT
from reportlab.lib.pagesizes import letter
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import inch
from reportlab.platypus import Image, Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle

from search_agent.graph.trace_figure import trace_figure_png
from search_agent.models.trace import trace_steps_from_state

PAGE_W, PAGE_H = letter
_MARGIN = 0.75 * inch
_CONTENT_W = PAGE_W - 2 * _MARGIN


def _slug_xml(s: str, *, max_len: int | None = None) -> str:
    """Plain text → XML-safe fragment for Paragraph (no outer tags)."""
    t = str(s or "")
    if max_len is not None:
        t = t[:max_len]
    return escape(t, entities={'"': "&quot;", "'": "&apos;"}).replace("\n", "<br/>")


def _section_title(text: str, style: ParagraphStyle) -> Paragraph:
    """Bold section label using real markup (content is escaped)."""
    return Paragraph(f"<b>{_slug_xml(text)}</b>", style)


def _body_para(text: str, style: ParagraphStyle) -> Paragraph:
    return Paragraph(_slug_xml(text, max_len=None), style)


def _plain_answer(text: str, style: ParagraphStyle) -> Paragraph:
    """Answer text: strip common markdown noise, then escape."""
    t = str(text or "")
    t = re.sub(r"\*\*([^*]+)\*\*", r"\1", t)
    t = re.sub(r"`([^`]+)`", r"\1", t)
    return Paragraph(_slug_xml(t, max_len=12000), style)


class PdfReportService:
    def build(
        self,
        *,
        query: str,
        answer: str,
        citations: list[str],
        web_snippets: list[str],
        wiki_snippet: str,
        run_trace: list[dict[str, Any]],
        trace_diagram_png: bytes | None,
        answer_chart_png: bytes | None = None,
    ) -> bytes:
        buffer = BytesIO()
        base = getSampleStyleSheet()

        title = ParagraphStyle(
            "rep_title",
            parent=base["Heading1"],
            fontSize=18,
            leading=22,
            spaceAfter=14,
            textColor=colors.HexColor("#111827"),
        )
        h2 = ParagraphStyle(
            "rep_h2",
            parent=base["Heading2"],
            fontSize=12,
            leading=15,
            spaceBefore=12,
            spaceAfter=8,
            textColor=colors.HexColor("#111827"),
            fontName="Helvetica-Bold",
        )
        body = ParagraphStyle(
            "rep_body",
            parent=base["Normal"],
            fontName="Helvetica",
            fontSize=10,
            leading=14,
            spaceAfter=8,
            alignment=TA_LEFT,
            textColor=colors.HexColor("#374151"),
        )
        label = ParagraphStyle(
            "rep_label",
            parent=base["Normal"],
            fontName="Helvetica-Bold",
            fontSize=10,
            leading=13,
            spaceAfter=4,
            textColor=colors.HexColor("#111827"),
        )
        table_cell = ParagraphStyle(
            "rep_tbl",
            parent=base["Normal"],
            fontSize=7,
            leading=9,
            textColor=colors.HexColor("#374151"),
        )

        doc = SimpleDocTemplate(
            buffer,
            pagesize=letter,
            title="Search Agent Report",
            leftMargin=_MARGIN,
            rightMargin=_MARGIN,
            topMargin=_MARGIN,
            bottomMargin=_MARGIN,
        )

        story: list[Any] = []
        story.append(Paragraph("Search agent report", title))
        story.append(Spacer(1, 0.08 * inch))

        story.append(_section_title("Query", label))
        story.append(_body_para(query, body))
        story.append(Spacer(1, 0.12 * inch))

        story.append(Paragraph("Answer", h2))
        story.append(_plain_answer(answer, body))
        story.append(Spacer(1, 0.08 * inch))

        if citations:
            story.append(Paragraph("Citations", h2))
            for c in citations[:30]:
                story.append(Paragraph(f"• {_slug_xml(c[:500])}", body))
            story.append(Spacer(1, 0.08 * inch))

        if web_snippets:
            story.append(Paragraph("Web snippets (trimmed)", h2))
            for s in web_snippets[:12]:
                story.append(_body_para(s[:800], body))
                story.append(Spacer(1, 0.04 * inch))

        if wiki_snippet:
            story.append(Paragraph("Wikipedia (trimmed)", h2))
            story.append(_body_para(wiki_snippet[:4000], body))
            story.append(Spacer(1, 0.08 * inch))

        if trace_diagram_png:
            story.append(Paragraph("Run trace (diagram)", h2))
            img = Image(BytesIO(trace_diagram_png))
            max_w = _CONTENT_W
            img.drawWidth = min(max_w, float(img.imageWidth) * 72 / 96 * 0.65)
            if img.drawWidth <= 0:
                img.drawWidth = max_w
            img.drawHeight = float(img.imageHeight) * (img.drawWidth / float(img.imageWidth))
            story.append(img)
            story.append(Spacer(1, 0.1 * inch))

        if answer_chart_png:
            story.append(Paragraph("Answer chart", h2))
            cimg = Image(BytesIO(answer_chart_png))
            cimg.drawWidth = min(_CONTENT_W, float(cimg.imageWidth) * 72 / 96 * 0.65)
            if cimg.drawWidth <= 0:
                cimg.drawWidth = _CONTENT_W
            cimg.drawHeight = float(cimg.imageHeight) * (cimg.drawWidth / float(cimg.imageWidth))
            story.append(cimg)
            story.append(Spacer(1, 0.1 * inch))

        steps = trace_steps_from_state(run_trace)
        if steps:
            story.append(Paragraph("Trace steps", h2))
            w_time = 0.62 * inch
            w_node = 0.95 * inch
            w_title = 1.05 * inch
            w_detail = max(1.2 * inch, _CONTENT_W - w_time - w_node - w_title)
            col_widths = [w_time, w_node, w_title, w_detail]

            data: list[list[Any]] = [[
                Paragraph("<b>Time (UTC)</b>", table_cell),
                Paragraph("<b>Node</b>", table_cell),
                Paragraph("<b>Title</b>", table_cell),
                Paragraph("<b>Detail</b>", table_cell),
            ]]
            for s in steps:
                dtext = (s.detail or "")[:450]
                data.append(
                    [
                        Paragraph(_slug_xml(s.ts.strftime("%H:%M:%S")), table_cell),
                        Paragraph(_slug_xml(s.node[:44]), table_cell),
                        Paragraph(_slug_xml(s.title[:70]), table_cell),
                        Paragraph(_slug_xml(dtext), table_cell),
                    ]
                )

            t = Table(data, colWidths=col_widths, repeatRows=1)
            t.setStyle(
                TableStyle(
                    [
                        ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#e5e7eb")),
                        ("GRID", (0, 0), (-1, -1), 0.4, colors.HexColor("#d1d5db")),
                        ("VALIGN", (0, 0), (-1, -1), "TOP"),
                        ("LEFTPADDING", (0, 0), (-1, -1), 4),
                        ("RIGHTPADDING", (0, 0), (-1, -1), 4),
                        ("TOPPADDING", (0, 0), (-1, -1), 4),
                        ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
                    ]
                )
            )
            story.append(t)

        doc.build(story)
        return buffer.getvalue()

    def build_from_run_state(self, state: dict[str, Any]) -> bytes:
        web = state.get("web_results") or []
        web_snippets: list[str] = []
        for h in web[:12]:
            if isinstance(h, dict):
                line = f"{h.get('title','')}\n{h.get('url','')}\n{h.get('snippet','')}"
            else:
                line = str(h)
            web_snippets.append(line[:900])
        trace_png = trace_figure_png(list(state.get("run_trace") or []))
        chart_b64 = state.get("chart_png_base64")
        chart_bytes: bytes | None
        try:
            chart_bytes = base64.b64decode(chart_b64) if chart_b64 else None
        except Exception:
            chart_bytes = None
        return self.build(
            query=str(state.get("query", "")),
            answer=str(state.get("final_answer", "")),
            citations=list(state.get("citations") or []),
            web_snippets=web_snippets,
            wiki_snippet=str(state.get("wiki_summary") or ""),
            run_trace=list(state.get("run_trace") or []),
            trace_diagram_png=trace_png,
            answer_chart_png=chart_bytes,
        )
