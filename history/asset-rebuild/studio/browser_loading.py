"""Load a large self-contained HTML artifact without a giant CDP JSON message.
The sandbox browser blocks file: and localhost navigations. Incremental
HTML parsing preserves the actual final DOM and scripts; no scene is replaced.
"""
from pathlib import Path

def load_html(page, path: Path):
    page.set_content('<!doctype html><html><head></head><body></body></html>')
    page.evaluate('document.open()')
    with path.open('r', encoding='utf-8') as source:
        while chunk := source.read(512 * 1024):
            page.evaluate('(chunk)=>document.write(chunk)', chunk)
    page.evaluate('document.close()')
