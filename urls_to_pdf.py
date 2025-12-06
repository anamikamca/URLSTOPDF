#!/usr/bin/env python3
"""Combine multiple web pages (URLs) into a single PDF using Playwright.

Usage examples:
  python urls_to_pdf.py https://example.com https://example.org -o combined.pdf
  python urls_to_pdf.py -f urls.txt -o combined.pdf

Notes:
  - Install dependencies: `python -m pip install -r requirements.txt`
  - Install Playwright browsers: `python -m playwright install`
  - If `pip` is not available, use `python -m ensurepip` or run pip via `python -m pip`.
"""
import argparse
import io
import sys
import time

from playwright.sync_api import sync_playwright
from pypdf import PdfReader

# pypdf changed APIs across versions. Prefer PdfMerger if available,
# otherwise fall back to PdfWriter and merge pages manually.
try:
    from pypdf import PdfMerger  # type: ignore
    _HAVE_PDFMERGER = True
except Exception:
    from pypdf import PdfWriter  # type: ignore
    _HAVE_PDFMERGER = False


def urls_from_file(path: str):
    with open(path, "r", encoding="utf-8") as f:
        lines = [ln.strip() for ln in f]
    return [ln for ln in lines if ln and not ln.startswith("#")]


def render_urls_to_pdf(urls, output_path, wait_after_load=1.0, viewport=None, pdf_format="A4"):
    if _HAVE_PDFMERGER:
        merger = PdfMerger()
    else:
        writer = PdfWriter()
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        context = browser.new_context(viewport=viewport)

        for idx, url in enumerate(urls, start=1):
            print(f"[{idx}/{len(urls)}] Loading: {url}")
            page = context.new_page()
            try:
                page.goto(url, wait_until="networkidle", timeout=60000)
                if wait_after_load and wait_after_load > 0:
                    time.sleep(wait_after_load)
                pdf_bytes = page.pdf(format=pdf_format, print_background=True)
                reader = PdfReader(io.BytesIO(pdf_bytes))
                if _HAVE_PDFMERGER:
                    merger.append(reader)
                else:
                    for p in reader.pages:
                        writer.add_page(p)
            except Exception as exc:
                print(f"Warning: failed to render {url}: {exc}", file=sys.stderr)
            finally:
                try:
                    page.close()
                except Exception:
                    pass

        try:
            browser.close()
        except Exception:
            pass

    print(f"Writing combined PDF to: {output_path}")
    if _HAVE_PDFMERGER:
        merger.write(output_path)
        merger.close()
    else:
        with open(output_path, "wb") as out_f:
            writer.write(out_f)


def main():
    parser = argparse.ArgumentParser(description="Combine multiple URLs into a single PDF file")
    parser.add_argument("urls", nargs="*", help="One or more URLs to render")
    parser.add_argument("-f", "--file", help="Text file with one URL per line (can include # comments)")
    parser.add_argument("-o", "--output", default="combined.pdf", help="Output PDF filename")
    parser.add_argument("--wait", type=float, default=1.0, help="Seconds to wait after page load before printing")
    parser.add_argument("--format", default="A4", help="PDF page size format (A4, Letter, etc.)")
    args = parser.parse_args()

    urls = list(args.urls or [])
    if args.file:
        urls.extend(urls_from_file(args.file))

    if not urls:
        parser.error("No URLs provided. Use positional URLs or -f/--file to supply them.")

    render_urls_to_pdf(urls, args.output, wait_after_load=args.wait, pdf_format=args.format)
    print("Done.")


if __name__ == "__main__":
    main()
