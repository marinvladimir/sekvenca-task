"""Dohvat činjenica o proizvodu sa službene stranice.

Generički dio čita schema.org JSON-LD (Product, FAQPage, BreadcrumbList), koji
koristi većina webshopova (Magento, Shopify, WooCommerce). GymBeam-specifični
dio dodaje kratki/dugi opis i tablicu specifikacija iz `data-test` atributa.

Svaka činjenica nosi ID izvora (S1, S2…) iz `sources.json`, da analiza i QA
mogu dokazati odakle tvrdnja dolazi. Cijene su označene kao promjenjive
(akcije, Black Friday) i ne smiju se koristiti u objavama bez ponovne provjere.

Napomena: prva slika u galeriji često je promo kompozicija (npr. poklon uz
proizvod), a ne čisti packshot. Zato se skidaju sve slike; izbor reference
radi se u analizi (vizijski model) ili ga potvrđuje čovjek.
"""

from __future__ import annotations

import html as html_lib
import json
import re
import time
from pathlib import Path
from typing import Any, Dict, List, Optional
from urllib.parse import urlparse

import httpx
from bs4 import BeautifulSoup

from ..config import settings
from ..state import Run, now_iso, slugify

ALLOWED_IMAGE_TYPES = {"image/jpeg": ".jpg", "image/png": ".png", "image/webp": ".webp"}


def _client() -> httpx.Client:
    return httpx.Client(
        headers={"User-Agent": settings.user_agent, "Accept-Language": "hr,en;q=0.8"},
        follow_redirects=True,
        timeout=30,
    )


def _clean(text: Optional[str]) -> str:
    if not text:
        return ""
    text = html_lib.unescape(text)
    return re.sub(r"\s+", " ", text).strip()


def _json_ld(soup: BeautifulSoup) -> List[Dict[str, Any]]:
    """Vrati sve JSON-LD čvorove (uključujući one unutar @graph) kao ravnu listu."""
    nodes: List[Dict[str, Any]] = []
    for tag in soup.find_all("script", type="application/ld+json"):
        try:
            data = json.loads(tag.string or "")
        except json.JSONDecodeError:
            continue
        stack = data if isinstance(data, list) else [data]
        while stack:
            node = stack.pop()
            if isinstance(node, dict):
                nodes.append(node)
                stack.extend(node.get("@graph", []))
    return nodes


def _of_type(nodes: List[Dict[str, Any]], t: str) -> List[Dict[str, Any]]:
    out = []
    for n in nodes:
        types = n.get("@type")
        types = types if isinstance(types, list) else [types]
        if t in types:
            out.append(n)
    return out


def _offers(product: Dict[str, Any]) -> List[Dict[str, Any]]:
    offers = product.get("offers") or {}
    if isinstance(offers, dict) and "offers" in offers:  # AggregateOffer
        offers = offers["offers"]
    if isinstance(offers, dict):
        offers = [offers]
    return [
        {
            "name": _clean(o.get("name")),
            "price": o.get("price"),
            "currency": o.get("priceCurrency"),
            "gtin13": o.get("gtin13"),
            "sku": o.get("sku"),
            "available": str(o.get("availability", "")).endswith("InStock"),
            "url": o.get("url"),
        }
        for o in offers
        if isinstance(o, dict)
    ]


def _properties(product: Dict[str, Any]) -> Dict[str, str]:
    props = {}
    for p in product.get("additionalProperty", []) or []:
        if isinstance(p, dict) and p.get("name"):
            props[_clean(p["name"])] = _clean(str(p.get("value", "")))
    return props


def _spec_table(soup: BeautifulSoup) -> Dict[str, str]:
    table = soup.find(attrs={"data-test": "pdp-product-description-table"})
    specs: Dict[str, str] = {}
    if not table:
        return specs
    for td in table.find_all("td", attrs={"data-th": True}):
        key = _clean(td["data-th"]).rstrip(":").strip()
        value_el = td.find("div") or td
        value = _clean(value_el.get_text(" "))
        if key and value and key not in specs:
            specs[key] = value
    return specs


def _text_by_test(soup: BeautifulSoup, test_id: str) -> str:
    el = soup.find(attrs={"data-test": test_id})
    if not el:
        return ""
    for junk in el.find_all(["script", "style", "button"]):
        junk.decompose()
    return _clean(el.get_text(" "))


def _short_description(soup: BeautifulSoup) -> str:
    """Kratki opis bez varijanti/cijena koje su u istom bloku."""
    text = _text_by_test(soup, "pdp-product-description-short")
    return text.split(" Pročitaj više")[0].strip()


GENERIC_TOKENS = {"gymbeam", "gym", "beam", "protein", "proteinska", "html", "www"}
PROMO_HINTS = ("t-shirt", "tshirt", "shirt", "shower", "gel", "creatine", "shots", "caps", "mikina", "gift",
               "socks", "carape", "_1x_", "1x_", "2x_", "bundle", "set_", "box_", "copy")


def _variant_images(page: str, url: str, known: List[str], limit: int = 6) -> List[str]:
    """Slike varijanti istog proizvoda iz podataka stranice (bez promo kompleta)."""
    slug = Path(urlparse(url).path).stem.lower()
    tokens = [t for t in re.split(r"[-_]", slug) if t and t not in GENERIC_TOKENS]
    seen = {re.sub(r"/cache/[0-9a-f]+", "", k) for k in known}
    found: List[str] = []
    for m in re.finditer(r"https?://[^\"'\s\\&]+/media/catalog/product/(?:cache/[0-9a-f]+/)?[a-z0-9]/[a-z0-9]/([^\"'\s\\&/]+\.(?:png|jpg|jpeg|webp))", page, re.I):
        full = re.sub(r"/cache/[0-9a-f]+", "", m.group(0))
        name = m.group(1).lower()
        flat = re.sub(r"[-_.]", "", name)
        if full in seen or re.match(r"^[a-z]{2}_", name) or any(h in name for h in PROMO_HINTS):
            continue
        if all(t.replace("-", "") in flat for t in tokens):
            seen.add(full)
            found.append(full)
    # PNG i "mockup" su najčešće čisti packshotovi — stavi ih naprijed
    found.sort(key=lambda u: (not u.lower().endswith(".png"), "mockup" not in u.lower()))
    return found[:limit]


def scrape_product(url: str, run: Run, download_images: bool = True) -> Dict[str, Any]:
    with _client() as client:
        resp = client.get(url)
        resp.raise_for_status()
        soup = BeautifulSoup(resp.text, "html.parser")
        nodes = _json_ld(soup)

        products = _of_type(nodes, "Product")
        if not products:
            raise RuntimeError(f"Na {url} nema schema.org Product podataka.")
        product = products[0]
        title = _clean(product.get("name"))
        source_id = run.add_source(url, kind="webshop", title=title)

        faq = []
        for page in _of_type(nodes, "FAQPage"):
            for q in page.get("mainEntity", []):
                answer = (q.get("acceptedAnswer") or {}).get("text")
                faq.append({"q": _clean(q.get("name")), "a": _clean(answer)})

        rating = product.get("aggregateRating") or {}
        images = product.get("image") or []
        images = [images] if isinstance(images, str) else images
        # Glavna galerija (JSON-LD) je često puna promo kompozicija; slike
        # pojedinih okusa/varijanti su u podacima stranice i obično su čisti packshotovi.
        variants = _variant_images(resp.text, url, images)

        record: Dict[str, Any] = {
            "source_id": source_id,
            "url": url,
            "retrieved_at": now_iso(),
            "name": title,
            "brand": _clean((product.get("brand") or {}).get("name")),
            "sku": product.get("sku"),
            "category": _clean(product.get("category")),
            "description_schema": _clean(product.get("description")),
            "description_short": _short_description(soup),
            "description_long": _text_by_test(soup, "pdp-product-description-long"),
            "properties": _properties(product),
            "spec_table": _spec_table(soup),
            "faq": faq,
            "rating": {
                "value": rating.get("ratingValue"),
                "count": rating.get("reviewCount") or rating.get("ratingCount"),
            },
            "offers": _offers(product),
            "offers_note": "Cijene su promjenjive (akcije). Ne koristiti u objavama bez ponovne provjere.",
            "images": [{"url": u, "file": None, "origin": "galerija"} for u in images]
            + [{"url": u, "file": None, "origin": "varijanta"} for u in variants],
        }

        out_dir = run.phase_dir("01_brif") / "products" / slugify(title)[:60]
        if download_images:
            img_dir = out_dir / "images"
            img_dir.mkdir(parents=True, exist_ok=True)
            for i, img in enumerate(record["images"], start=1):
                time.sleep(settings.request_delay_s)
                r = client.get(img["url"])
                ctype = r.headers.get("content-type", "").split(";")[0]
                if r.status_code != 200 or ctype not in ALLOWED_IMAGE_TYPES:
                    img["error"] = f"{r.status_code} {ctype}"
                    continue
                name = f"{i:02d}_{Path(urlparse(img['url']).path).stem}{ALLOWED_IMAGE_TYPES[ctype]}"
                (img_dir / name).write_bytes(r.content)
                img["file"] = str((img_dir / name).relative_to(run.dir))

        out_dir.mkdir(parents=True, exist_ok=True)
        (out_dir / "product.json").write_text(
            json.dumps(record, ensure_ascii=False, indent=2), encoding="utf-8"
        )
        record["_path"] = str((out_dir / "product.json").relative_to(run.dir))
        return record
