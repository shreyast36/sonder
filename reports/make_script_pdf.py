"""
Render Shreyas's speaking-script markdown into a styled PDF.

Reuses the parsing + styling pipeline from make_pdf.py — same fonts,
same gold rules, same headings — so the output looks consistent with
the rest of the Sonder presentation assets.

Output: reports/shreyas_speaking_script.pdf
Run:    python reports/make_script_pdf.py
"""
from pathlib import Path

from reportlab.lib.pagesizes import letter
from reportlab.lib.units import inch
from reportlab.platypus import SimpleDocTemplate

from make_pdf import build_styles, parse_markdown, header_footer

SRC  = Path(__file__).resolve().parent / "shreyas_speaking_script.md"
DEST = Path(__file__).resolve().parent / "shreyas_speaking_script.pdf"


def main():
    md_text = SRC.read_text(encoding="utf-8")
    styles = build_styles()
    doc = SimpleDocTemplate(
        str(DEST), pagesize=letter,
        topMargin=0.85 * inch, bottomMargin=0.75 * inch,
        leftMargin=0.85 * inch, rightMargin=0.85 * inch,
        title="Sonder — Speaking Script (Shreyas)",
        author="Sonder Team",
    )
    page_width = doc.width
    flow = parse_markdown(md_text, styles, page_width)
    doc.build(flow, onFirstPage=header_footer, onLaterPages=header_footer)
    print(f"PDF generated: {DEST}")


if __name__ == "__main__":
    main()
