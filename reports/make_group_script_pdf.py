"""
Render the 12-minute group speaking-script markdown into a styled PDF.

Same parsing + styling pipeline as the rest of the Sonder reports.

Output: reports/group_12min_script.pdf
Run:    python reports/make_group_script_pdf.py
"""
from pathlib import Path

from reportlab.lib.pagesizes import letter
from reportlab.lib.units import inch
from reportlab.platypus import SimpleDocTemplate

from make_pdf import build_styles, parse_markdown, header_footer

SRC  = Path(__file__).resolve().parent / "group_12min_script.md"
DEST = Path(__file__).resolve().parent / "group_12min_script.pdf"


def main():
    md_text = SRC.read_text(encoding="utf-8")
    styles = build_styles()
    doc = SimpleDocTemplate(
        str(DEST), pagesize=letter,
        topMargin=0.85 * inch, bottomMargin=0.75 * inch,
        leftMargin=0.85 * inch, rightMargin=0.85 * inch,
        title="Sonder — 12-Minute Group Script",
        author="Sonder Team",
    )
    page_width = doc.width
    flow = parse_markdown(md_text, styles, page_width)
    doc.build(flow, onFirstPage=header_footer, onLaterPages=header_footer)
    print(f"PDF generated: {DEST}")


if __name__ == "__main__":
    main()
