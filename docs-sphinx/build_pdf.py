"""Build a single PDF from the Sphinx HTML output using WeasyPrint."""
import os
from pathlib import Path
from bs4 import BeautifulSoup
from weasyprint import HTML, CSS

BUILD_DIR = Path(__file__).parent / "_build" / "html"
OUTPUT_PDF = Path(__file__).parent / "_build" / "BSPQ26-E9.pdf"

PAGE_ORDER = [
    "index.html",
    "overview.html",
    "architecture.html",
    "api/index.html",
    "api/auth_api.html",
    "api/inventory_api.html",
    "api/transaction_api.html",
    "api/agentic_api.html",
    "wallabot_agent.html",
    "testing.html",
    "devops.html",
]

CSS_OVERRIDES = CSS(string="""
    @page { size: A4; margin: 2cm; }
    .wy-nav-side, .wy-nav-top, footer { display: none !important; }
    .wy-nav-content-wrap { margin-left: 0 !important; }
    .wy-nav-content { max-width: 100% !important; }
    a[href]::after { content: none !important; }
""")


def collect_html_documents():
    documents = []
    for page in PAGE_ORDER:
        path = BUILD_DIR / page
        if path.exists():
            documents.append(HTML(filename=str(path)))
    return documents


def main():
    OUTPUT_PDF.parent.mkdir(parents=True, exist_ok=True)
    docs = collect_html_documents()
    if not docs:
        raise RuntimeError(f"No HTML files found in {BUILD_DIR}")
    combined = docs[0].render(stylesheets=[CSS_OVERRIDES])
    for doc in docs[1:]:
        rendered = doc.render(stylesheets=[CSS_OVERRIDES])
        combined.pages.extend(rendered.pages)
    combined.write_pdf(str(OUTPUT_PDF))
    size_kb = OUTPUT_PDF.stat().st_size // 1024
    print(f"PDF written to {OUTPUT_PDF} ({size_kb} KB)")


if __name__ == "__main__":
    main()
