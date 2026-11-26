"""Logo brenda sa službene stranice.

Redoslijed: inline SVG u poveznici s aria-label/title "Logo" → <img> s "logo"
u nazivu → schema.org Organization.logo. Ako ništa ne uspije, logo je ručni
ulaz (inputs/brand/logo.svg|png) i to se navodi u brifu.
"""

from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Optional
from urllib.parse import urljoin

from bs4 import BeautifulSoup

from ..state import Run
from .product import _client, _json_ld, _of_type


def scrape_logo(website: str, run: Run, out_dir: Path) -> Optional[dict]:
    out_dir.mkdir(parents=True, exist_ok=True)
    with _client() as client:
        resp = client.get(website)
        resp.raise_for_status()
        soup = BeautifulSoup(resp.text, "html.parser")
        sid = run.add_source(website, kind="webshop", title="Naslovnica (logo)")

        # SVG se vadi iz sirovog HTML-a: html.parser pretvara atribute u mala
        # slova (viewBox → viewbox, clipPath → clippath), što kvari SVG.
        m = re.search(r'<a[^>]*aria-label="[^"]*logo[^"]*"[^>]*>\s*(<svg.*?</svg>)', resp.text, re.I | re.S)
        svg = m.group(1) if m else None
        if svg:
            svg = re.sub(r'\s(class|aria-hidden)="[^"]*"', "", svg, count=2)
            path = out_dir / "logo.svg"
            path.write_text(svg, encoding="utf-8")
            # bijela varijanta za tamne pozadine (zamjena crne ispune)
            white = re.sub(r'fill="#0{3}(0{3})?"', 'fill="#FFFFFF"', svg)
            (out_dir / "logo-white.svg").write_text(white, encoding="utf-8")
            return {"file": str(path.relative_to(run.dir)), "variant_white": str((out_dir / "logo-white.svg").relative_to(run.dir)),
                    "method": "inline_svg", "source_id": sid}

        img = soup.find("img", attrs={"src": re.compile("logo", re.I)})
        url = urljoin(website, img["src"]) if img else None
        if not url:
            orgs = _of_type(_json_ld(soup), "Organization")
            url = orgs[0].get("logo") if orgs else None
            url = url.get("url") if isinstance(url, dict) else url
        if not url:
            return None
        r = client.get(url)
        ext = ".svg" if "svg" in r.headers.get("content-type", "") else ".png"
        path = out_dir / f"logo{ext}"
        path.write_bytes(r.content)
        return {"file": str(path.relative_to(run.dir)), "method": "img_or_schema", "url": url, "source_id": sid}
