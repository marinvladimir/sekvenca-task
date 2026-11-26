"""KADAR 01 · BRIF I ULAZI

Ulaz:   brif (JSON datoteka ili interaktivna pitanja), URL-ovi proizvoda,
        IG screenshotovi u mapi + index.csv, opcionalno ručni logo.
Radi:   sprema brif, dohvaća činjenice i slike proizvoda, logo, indeksira
        screenshotove i upozorava na nedostatke.
Izlaz:  01_brif/output.json → ulaz za analizu.
"""

from __future__ import annotations

import csv
import json
import shutil
from pathlib import Path
from typing import Any, Dict, List

from ..config import settings
from ..scrape.brand import scrape_logo
from ..scrape.instagram import scrape_posts, shortcode
from ..scrape.product import scrape_product
from ..state import Run, now_iso

PHASE = "01_brif"
IMAGE_EXT = {".png", ".jpg", ".jpeg", ".webp"}

QUESTIONS = [
    ("brand", "Naziv brenda", ""),
    ("brand_choice", "Zašto ovaj brend (kratko)", ""),
    ("instagram", "Instagram profil (URL)", ""),
    ("website", "Službena web-stranica / webshop", ""),
    ("products", "URL-ovi proizvoda za promociju (odvojeni zarezom)", ""),
    ("audience", "Ciljana publika", ""),
    ("goals", "Ciljevi objava (npr. spremanja, komentari, prodaja)", ""),
    ("inspiration", "Uzori i inspiracija (brendovi, profili, stil)", ""),
    ("tone_notes", "Napomene o tonu i stilu", ""),
    ("constraints", "Ograničenja (što se ne smije)", ""),
    ("language", "Jezik objava", "hrvatski"),
    ("instagram_screenshots_dir", "Mapa s IG screenshotovima", "inputs/instagram"),
    ("brand_dir", "Mapa s ručnim ulazima brenda (logo, brand.json)", "inputs/brand"),
]


def ask_brief() -> Dict[str, Any]:
    print("KADAR 01 · BRIF — Enter prihvaća zadanu vrijednost.\n")
    brief: Dict[str, Any] = {}
    for key, question, default in QUESTIONS:
        hint = f" [{default}]" if default else ""
        answer = input(f"{question}{hint}: ").strip() or default
        brief[key] = answer
    brief["products"] = [u.strip() for u in brief["products"].split(",") if u.strip()]
    return brief


def _index_instagram(folder: Path) -> Dict[str, Any]:
    rows: Dict[str, Dict[str, str]] = {}
    index = folder / "index.csv"
    if index.exists():
        with index.open(encoding="utf-8") as f:
            for row in csv.DictReader(f):
                if row.get("file"):
                    rows[row["file"].strip()] = {k: (v or "").strip() for k, v in row.items()}
    files = sorted(p for p in folder.glob("*") if p.suffix.lower() in IMAGE_EXT) if folder.exists() else []
    items = []
    for p in files:
        meta = rows.get(p.name, {})
        items.append(
            {
                "file": str(p.relative_to(settings.root)),
                "label": f"IG:{p.name}",
                "post_url": meta.get("post_url", ""),
                "post_type": meta.get("post_type", ""),
                "date_posted": meta.get("date_posted", ""),
                "note": meta.get("note", ""),
            }
        )
    missing_meta = [i["file"] for i in items if not i["post_url"]]
    return {"items": items, "missing_url": missing_meta}


def run_brief(run: Run, brief: Dict[str, Any]) -> Dict[str, Any]:
    run.set_meta(PHASE, status="running", started_at=now_iso())
    warnings: List[str] = []

    # 1) proizvodi
    products = []
    for url in brief.get("products", []):
        try:
            rec = scrape_product(url, run)
            products.append(rec["_path"])
        except Exception as exc:
            warnings.append(f"Proizvod nije dohvaćen: {url} ({exc})")

    # 2) logo: ručni ulaz ima prednost pred automatskim dohvatom
    brand_dir = run.phase_dir(PHASE) / "brand"
    manual = next((p for p in (settings.root / brief.get("brand_dir", "inputs/brand")).glob("logo.*")), None)
    if manual:
        brand_dir.mkdir(parents=True, exist_ok=True)
        shutil.copy(manual, brand_dir / manual.name)
        logo = {"file": str((brand_dir / manual.name).relative_to(run.dir)), "method": "ručni ulaz"}
    else:
        try:
            logo = scrape_logo(brief["website"], run, brand_dir)
        except Exception as exc:
            logo = None
            warnings.append(f"Logo nije dohvaćen ({exc})")
        if not logo:
            warnings.append("Nema loga: stavi službeni logo u inputs/brand/logo.svg ili .png.")

    # 3) Instagram screenshotovi (ručni korak — IG ne dopušta dohvat bez prijave)
    ig = _index_instagram(settings.root / brief.get("instagram_screenshots_dir", "inputs/instagram"))
    for item in ig["items"]:
        if item["post_url"]:
            run.add_source(item["post_url"], kind="instagram", title=item["label"], note=item["note"])
    n = len(ig["items"])
    if n == 0:
        warnings.append("Nema IG screenshotova: analiza Instagrama bit će označena kao NEDOSTUPNO.")
    elif n < 8:
        warnings.append(f"Samo {n} IG screenshotova; preporuka je 12–15 za pouzdanu analizu.")
    if ig["missing_url"]:
        warnings.append(f"{len(ig['missing_url'])} screenshotova nema URL u index.csv (slabiji dokaz).")
    if brief.get("instagram"):
        run.add_source(brief["instagram"], kind="instagram", title="Instagram profil",
                       note="Feed profila nije dostupan bez prijave; korišteni screenshotovi i poveznice objava.")

    # 4) javni podaci objava iz poveznica (posts.txt + poveznice iz index.csv)
    ig_dir = settings.root / brief.get("instagram_screenshots_dir", "inputs/instagram")
    urls: List[str] = []
    if (ig_dir / "posts.txt").exists():
        urls += [l.strip() for l in (ig_dir / "posts.txt").read_text(encoding="utf-8").splitlines()
                 if l.strip() and not l.startswith("#")]
    urls += [i["post_url"] for i in ig["items"] if "/p/" in i["post_url"] or "/reel" in i["post_url"]]
    seen, unique = set(), []
    for u in urls:
        code = shortcode(u)
        if code and code not in seen:
            seen.add(code)
            unique.append(u)
    posts = scrape_posts(unique, run, run.phase_dir(PHASE) / "instagram") if unique else []
    shot_by_code = {shortcode(i["post_url"]): i["label"] for i in ig["items"] if shortcode(i["post_url"] or "")}
    for p in posts:
        p["screenshot"] = shot_by_code.get(p["code"])
    failed = [p["url"] for p in posts if p["status"] != "ok"]
    if failed:
        warnings.append(f"{len(failed)} objava bez javnog opisa: {', '.join(failed)}")

    output = {
        "brief": brief,
        "products": products,
        "logo": logo,
        "instagram": ig["items"],
        "instagram_posts": posts,
        "warnings": warnings,
        "human_steps": [
            "Ispunjavanje brifa (odgovori u brief JSON-u ili interaktivno).",
            "Poveznice Instagram objava u posts.txt (feed profila nije dostupan bez prijave).",
            "Opcionalno: screenshotovi objava + index.csv (vide se raspored, komentari, slajdovi).",
            "Odobrenje faze nakon pregleda upozorenja.",
        ],
    }
    run.save_output(PHASE, output)
    return output


def load_brief_file(path: Path) -> Dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))
