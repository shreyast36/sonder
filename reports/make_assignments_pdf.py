"""
Render the presentation-assignments markdown into a styled PDF.

Reuses the parsing + styling pipeline from make_pdf.py — same fonts,
same gold rules, same table treatment — so the output looks consistent
with the project report.

Output: reports/sonder_presentation_assignments.pdf
Run:    python reports/make_assignments_pdf.py
"""
from pathlib import Path

from reportlab.lib.pagesizes import letter
from reportlab.lib.units import inch
from reportlab.platypus import SimpleDocTemplate

# Pull every helper from the sibling generator so we don't duplicate code.
from make_pdf import build_styles, parse_markdown, header_footer

SRC  = Path(__file__).resolve().parent / "sonder_presentation_assignments.md"
DEST = Path(__file__).resolve().parent / "sonder_presentation_assignments.pdf"


def main():
    md_text = SRC.read_text(encoding="utf-8")
    styles = build_styles()
    doc = SimpleDocTemplate(
        str(DEST), pagesize=letter,
        topMargin=0.85 * inch, bottomMargin=0.75 * inch,
        leftMargin=0.85 * inch, rightMargin=0.85 * inch,
        title="Sonder — Presentation Assignments",
        author="Sonder Team",
    )
    page_width = doc.width
    flow = parse_markdown(md_text, styles, page_width)
    doc.build(flow, onFirstPage=header_footer, onLaterPages=header_footer)
    print(f"PDF generated: {DEST}")


if __name__ == "__main__":
    main()
