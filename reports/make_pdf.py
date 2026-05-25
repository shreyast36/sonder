"""
Render the Sonder project report from markdown to a styled PDF.

Uses reportlab directly (no LaTeX dependency). Hand-rolled markdown
parser tuned for the specific report shape — headings, paragraphs,
bullet lists, tables, italics, bold, inline code. Tables get column-
width auto-fit; long cells wrap.

Output:  reports/sonder_project_report.pdf
"""
from __future__ import annotations

import re
from pathlib import Path

from reportlab.lib import colors
from reportlab.lib.pagesizes import letter
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import inch
from reportlab.platypus import (
    SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle,
    PageBreak, KeepTogether,
)
from reportlab.lib.enums import TA_LEFT, TA_JUSTIFY


SRC  = Path(__file__).resolve().parent / "sonder_project_report.md"
DEST = Path(__file__).resolve().parent / "sonder_project_report.pdf"


# ── Styles ──────────────────────────────────────────────────────────────
def build_styles():
    base = getSampleStyleSheet()
    # Clear and rebuild so we control the look.
    title = ParagraphStyle(
        "Title", parent=base["Title"],
        fontName="Helvetica-Bold", fontSize=22, leading=26,
        spaceAfter=4, textColor=colors.HexColor("#1a1410"),
        alignment=TA_LEFT,
    )
    subtitle = ParagraphStyle(
        "Subtitle", parent=base["Normal"],
        fontName="Helvetica-Oblique", fontSize=14, leading=18,
        textColor=colors.HexColor("#555"), spaceAfter=18,
    )
    h1 = ParagraphStyle(
        "H1", parent=base["Heading1"],
        fontName="Helvetica-Bold", fontSize=16, leading=20,
        spaceBefore=18, spaceAfter=8,
        textColor=colors.HexColor("#1a1410"),
        borderPadding=4, borderColor=colors.HexColor("#D4B686"),
    )
    h2 = ParagraphStyle(
        "H2", parent=base["Heading2"],
        fontName="Helvetica-Bold", fontSize=13, leading=17,
        spaceBefore=14, spaceAfter=6,
        textColor=colors.HexColor("#2a1a12"),
    )
    h3 = ParagraphStyle(
        "H3", parent=base["Heading3"],
        fontName="Helvetica-Bold", fontSize=11, leading=15,
        spaceBefore=10, spaceAfter=4,
        textColor=colors.HexColor("#444"),
    )
    body = ParagraphStyle(
        "Body", parent=base["BodyText"],
        fontName="Helvetica", fontSize=10, leading=14,
        spaceAfter=8, alignment=TA_JUSTIFY,
        textColor=colors.HexColor("#1a1410"),
    )
    bullet = ParagraphStyle(
        "Bullet", parent=body,
        leftIndent=18, bulletIndent=4,
        spaceAfter=4,
    )
    table_header = ParagraphStyle(
        "TableHeader", parent=base["Normal"],
        fontName="Helvetica-Bold", fontSize=9, leading=12,
        textColor=colors.HexColor("#1a1410"),
    )
    table_cell = ParagraphStyle(
        "TableCell", parent=base["Normal"],
        fontName="Helvetica", fontSize=9, leading=12,
        textColor=colors.HexColor("#1a1410"),
    )
    rule = ParagraphStyle(
        "Rule", parent=base["Normal"],
        fontSize=8, textColor=colors.HexColor("#aaa"),
        alignment=TA_LEFT,
    )
    return dict(
        title=title, subtitle=subtitle,
        h1=h1, h2=h2, h3=h3,
        body=body, bullet=bullet,
        table_header=table_header, table_cell=table_cell,
        rule=rule,
    )


# ── Inline markdown → ReportLab "mini-HTML" ─────────────────────────────
def render_inline(text: str) -> str:
    """Convert inline markdown (`**bold**`, `*italic*`, `_italic_`, `` `code` ``)
    to the inline tag subset reportlab Paragraph understands.

    Order matters: do **bold** before *italic* so we don't eat one of
    the bold stars as an italic open.
    """
    # Escape `&` first since reportlab interprets &amp; etc.
    text = text.replace("&", "&amp;")
    text = text.replace("<", "&lt;").replace(">", "&gt;")
    # Bold: **x**
    text = re.sub(r"\*\*([^*]+?)\*\*", r"<b>\1</b>", text)
    # Italic: *x* (but not from a leftover star) or _x_
    text = re.sub(r"(?<![*\w])\*([^*]+?)\*(?!\w)", r"<i>\1</i>", text)
    text = re.sub(r"(?<![\w_])_([^_]+?)_(?!\w)", r"<i>\1</i>", text)
    # Inline code: `x`
    text = re.sub(r"`([^`]+?)`", r'<font name="Courier" size="9">\1</font>', text)
    return text


# ── Block-level parser ──────────────────────────────────────────────────
HEADING_RE  = re.compile(r"^(#{1,4})\s+(.*)$")
RULE_RE     = re.compile(r"^---+\s*$")
BULLET_RE   = re.compile(r"^([-*])\s+(.*)$")
TABLE_SEP_RE = re.compile(r"^\|[\s\-:|]+\|\s*$")
TABLE_ROW_RE = re.compile(r"^\|(.+)\|\s*$")


def split_table_row(line: str) -> list[str]:
    inner = line.strip().strip("|")
    return [c.strip() for c in inner.split("|")]


def col_widths(rows: list[list[str]], total: float) -> list[float]:
    """Width per column proportional to its longest cell, with a floor
    so single-character columns don't squish to nothing."""
    cols = max(len(r) for r in rows) if rows else 1
    max_lens = [1] * cols
    for r in rows:
        for i, cell in enumerate(r):
            max_lens[i] = max(max_lens[i], len(cell) or 1)
    total_len = sum(max_lens)
    if total_len == 0:
        return [total / cols] * cols
    floors = [0.10 * total / cols] * cols  # 10% floor of even share
    raw = [(m / total_len) * total for m in max_lens]
    out = [max(r, f) for r, f in zip(raw, floors)]
    # Renormalise so they sum to total
    s = sum(out)
    return [w * (total / s) for w in out]


def make_table(rows: list[list[str]], styles: dict, page_width: float):
    if not rows:
        return None
    header, *body = rows
    data = [
        [Paragraph(render_inline(c), styles["table_header"]) for c in header]
    ] + [
        [Paragraph(render_inline(c), styles["table_cell"]) for c in row]
        for row in body
    ]
    widths = col_widths(rows, page_width)
    t = Table(data, colWidths=widths, repeatRows=1)
    t.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#f4ede0")),
        ("TEXTCOLOR",  (0, 0), (-1, 0), colors.HexColor("#1a1410")),
        ("FONTNAME",   (0, 0), (-1, 0), "Helvetica-Bold"),
        ("GRID",       (0, 0), (-1, -1), 0.4, colors.HexColor("#bbb")),
        ("VALIGN",     (0, 0), (-1, -1), "TOP"),
        ("LEFTPADDING",  (0, 0), (-1, -1), 5),
        ("RIGHTPADDING", (0, 0), (-1, -1), 5),
        ("TOPPADDING",   (0, 0), (-1, -1), 4),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
        ("ROWBACKGROUNDS", (0, 1), (-1, -1),
         [colors.white, colors.HexColor("#fafaf7")]),
    ]))
    return t


def parse_markdown(md_text: str, styles: dict, page_width: float):
    """Walk the markdown line-by-line and emit a flowables list.
    Hand-rolled because the report's structure is narrow + predictable."""
    flow = []
    lines = md_text.splitlines()
    i = 0
    n = len(lines)
    saw_title = False

    while i < n:
        line = lines[i]
        stripped = line.strip()

        # Blank → spacer
        if not stripped:
            flow.append(Spacer(1, 4))
            i += 1
            continue

        # Horizontal rule
        if RULE_RE.match(stripped):
            flow.append(Spacer(1, 6))
            flow.append(Table(
                [[""]], colWidths=[page_width],
                rowHeights=[0.6],
                style=TableStyle([
                    ("LINEBELOW", (0, 0), (-1, -1), 0.8,
                     colors.HexColor("#D4B686")),
                ]),
            ))
            flow.append(Spacer(1, 6))
            i += 1
            continue

        # Heading
        m = HEADING_RE.match(stripped)
        if m:
            level = len(m.group(1))
            content = render_inline(m.group(2))
            if level == 1 and not saw_title:
                # First H1 is the title.
                flow.append(Paragraph(content, styles["title"]))
                saw_title = True
            elif level == 2 and not saw_title:
                # Subtitle for the cover.
                flow.append(Paragraph(content, styles["subtitle"]))
            else:
                style_key = {1: "h1", 2: "h2", 3: "h3", 4: "h3"}[level]
                flow.append(Paragraph(content, styles[style_key]))
            i += 1
            continue

        # Table — header row + separator + body rows
        if TABLE_ROW_RE.match(stripped) and i + 1 < n and TABLE_SEP_RE.match(lines[i + 1].strip()):
            rows: list[list[str]] = []
            rows.append(split_table_row(lines[i]))
            i += 2   # skip separator
            while i < n and TABLE_ROW_RE.match(lines[i].strip()):
                rows.append(split_table_row(lines[i]))
                i += 1
            tbl = make_table(rows, styles, page_width)
            if tbl is not None:
                flow.append(Spacer(1, 4))
                flow.append(tbl)
                flow.append(Spacer(1, 8))
            continue

        # Bullet list
        m = BULLET_RE.match(stripped)
        if m:
            items: list[str] = []
            while i < n:
                bm = BULLET_RE.match(lines[i].strip())
                if not bm:
                    break
                items.append(bm.group(2))
                i += 1
            for item in items:
                flow.append(Paragraph(
                    render_inline(item),
                    styles["bullet"],
                    bulletText="•",
                ))
            flow.append(Spacer(1, 4))
            continue

        # Italic-only single line ("*End of report.*")
        # Treat as paragraph; render_inline handles emphasis.
        # Regular paragraph — collect until blank line or block boundary.
        paragraph_lines = [line]
        i += 1
        while i < n:
            nxt = lines[i]
            ns = nxt.strip()
            if (not ns) or HEADING_RE.match(ns) or RULE_RE.match(ns) \
                or BULLET_RE.match(ns) or TABLE_ROW_RE.match(ns):
                break
            paragraph_lines.append(nxt)
            i += 1
        text = " ".join(s.strip() for s in paragraph_lines)
        flow.append(Paragraph(render_inline(text), styles["body"]))

    return flow


# ── Page furniture ──────────────────────────────────────────────────────
def header_footer(canvas, doc):
    canvas.saveState()
    width, height = letter
    # Footer rule + page number
    canvas.setStrokeColor(colors.HexColor("#D4B686"))
    canvas.setLineWidth(0.4)
    canvas.line(0.75 * inch, 0.55 * inch, width - 0.75 * inch, 0.55 * inch)
    canvas.setFont("Helvetica", 8)
    canvas.setFillColor(colors.HexColor("#888"))
    canvas.drawString(0.75 * inch, 0.4 * inch, "Sonder · Project Report")
    canvas.drawRightString(width - 0.75 * inch, 0.4 * inch,
                           f"Page {doc.page}")
    canvas.restoreState()


def main():
    md_text = SRC.read_text(encoding="utf-8")
    styles = build_styles()
    doc = SimpleDocTemplate(
        str(DEST), pagesize=letter,
        topMargin=0.85 * inch, bottomMargin=0.75 * inch,
        leftMargin=0.85 * inch, rightMargin=0.85 * inch,
        title="Sonder — Project Report",
        author="Sonder Team",
    )
    page_width = doc.width
    flow = parse_markdown(md_text, styles, page_width)
    doc.build(flow, onFirstPage=header_footer, onLaterPages=header_footer)
    print(f"PDF generated: {DEST}")


if __name__ == "__main__":
    main()
