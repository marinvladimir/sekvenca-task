"""Javni podaci Instagram objava iz poveznica.

Instagram bez prijave ne daje feed profila, ali stranica pojedine objave
sadrži Open Graph oznake: datum, broj lajkova i komentara, opis (caption)
i naslovnu sliku. Dovoljno je dati poveznice objava; screenshotovi ostaju
koristan dodatak (vide se raspored, komentari i ostali slajdovi karusela).

Datum objave se dodatno izračuna iz koda objave (shortcode → media ID →
vrijeme), pa se poveznica može upariti sa screenshotom bez nagađanja.
"""

from __future__ import annotations

import html as html_lib
import re
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional

from ..config import settings
from ..state import Run, now_iso
from .product import _client

ALPHABET = "ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789-_"
IG_EPOCH_MS = 1314220021721


def shortcode(url: str) -> Optional[str]:
    m = re.search(r"instagram\.com/(?:p|reel|reels|tv)/([A-Za-z0-9_-]+)", url)
    return m.group(1) if m else None


def shortcode_date(code: str) -> str:
    n = 0
    for ch in code:
        n = n * 64 + ALPHABET.index(ch)
    ms = (n >> 23) + IG_EPOCH_MS
    return datetime.fromtimestamp(ms / 1000, tz=timezone.utc).strftime("%Y-%m-%d")


def _meta(page: str, key: str) -> str:
    m = re.search(rf'<meta (?:property|name)="{re.escape(key)}" content="([^"]*)"', page)
    return html_lib.unescape(m.group(1)) if m else ""


def _parse_description(desc: str) -> Dict[str, Any]:
    # "76 likes, 2 comments - gymbeamhr on September 29, 2026: "caption…""
    m = re.match(r'\s*([\d,.KkMm]+) likes?, ([\d,.KkMm]+) comments? - (\S+) on ([^:]+):\s*"?(.*?)"?\.?\s*$', desc, re.S)
    if not m:
        return {"caption": desc}
    return {"likes": m.group(1), "comments": m.group(2), "account": m.group(3),
            "date_text": m.group(4), "caption": m.group(5).strip()}


def scrape_posts(urls: List[str], run: Run, out_dir: Path) -> List[Dict[str, Any]]:
    out_dir.mkdir(parents=True, exist_ok=True)
    posts = []
    with _client() as client:
        for url in urls:
            code = shortcode(url)
            if not code:
                continue
            clean = f"https://www.instagram.com/{'reel' if '/reel' in url else 'p'}/{code}/"
            item: Dict[str, Any] = {"url": clean, "code": code, "kind": "reel" if "/reel" in url else "objava",
                                    "date": shortcode_date(code), "retrieved_at": now_iso()}
            try:
                time.sleep(settings.request_delay_s)
                page = client.get(clean).text
                item.update(_parse_description(_meta(page, "og:description")))
                img_url = _meta(page, "og:image")
                if img_url:
                    r = client.get(img_url)
                    if r.status_code == 200 and r.headers.get("content-type", "").startswith("image/"):
                        path = out_dir / f"{code}.jpg"
                        path.write_bytes(r.content)
                        item["image"] = str(path.relative_to(run.dir))
                item["status"] = "ok" if item.get("caption") else "bez_opisa"
            except Exception as exc:  # jedna nedostupna objava ne ruši ostale
                item["status"] = f"greška: {exc}"
            item["source_id"] = run.add_source(clean, kind="instagram", title=f"IG {item['kind']} {item['date']}",
                                               note=(item.get("caption") or "")[:120])
            posts.append(item)
    return posts
