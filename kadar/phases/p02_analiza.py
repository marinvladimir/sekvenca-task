"""KADAR 02 · ANALIZA BRENDA

Ulaz:   01_brif/output.json (brif, proizvodi, IG screenshotovi, logo).
Radi:   (a) klasificira slike proizvoda i bira čisti packshot kao referencu,
        (b) izvlači dopuštene tvrdnje o proizvodu s doslovnim citatima,
        (c) mjeri paletu kodom iz screenshotova,
        (d) analizira brend (ton, publika, teme, stil, boje, prikaz proizvoda
            i osoba) uz obavezne oznake PROVJERENO / PRETPOSTAVKA / NEDOSTUPNO.
Izlaz:  02_analiza/output.json + analiza.md (za čovjeka) → ulaz za plan.

Svaki korak sprema međurezultat, pa ponovno pokretanje preskače gotove korake.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict, List

from ..config import settings
from ..images import measure_palette
from ..llm import ask_structured, load_prompt
from ..schemas import BrandAnalysis, ProductClaims, ProductImages
from ..state import Run, now_iso

PHASE = "02_analiza"


def _cached(path: Path):
    return json.loads(path.read_text(encoding="utf-8")) if path.exists() else None


def _save(path: Path, data: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")


def _product_digest(p: Dict[str, Any]) -> Dict[str, Any]:
    """Sažetak činjenica za prompt (bez HS kodova, dimenzija paketa i sl.)."""
    skip = ("HS tarifni", "Bruto", "Dužina", "Širina", "Visina", "Broj komada", "Last Redesign", "EAN")
    props = {k: v for k, v in p["properties"].items() if not k.startswith(skip)}
    return {
        "source_id": p["source_id"],
        "name": p["name"],
        "brand": p["brand"],
        "description_short": p["description_short"],
        "description_long": p["description_long"][:6000],
        "properties": props,
        "faq": p["faq"],
        "rating": p["rating"],
        "variants": sorted({o["name"] for o in p["offers"]})[:20],
    }


def run_analysis(run: Run, dry_run: bool = False) -> Dict[str, Any]:
    brif = run.output("01_brif")
    if not brif:
        raise SystemExit("Faza 01_brif nema izlaz. Pokreni `brief` prvo.")
    work = run.phase_dir(PHASE) / "steps"
    log = run.phase_dir(PHASE) / "calls.jsonl"
    if not dry_run:
        run.set_meta(PHASE, status="running", started_at=now_iso())

    products = [json.loads((run.dir / p).read_text(encoding="utf-8")) for p in brif["products"]]

    # (a) slike proizvoda → uloga + najbolja referenca
    image_roles: Dict[str, Any] = {}
    for p in products:
        out = work / f"images_{p['sku']}.json"
        files = [run.dir / i["file"] for i in p["images"] if i.get("file")]
        if dry_run:
            print(f"[dry] slike {p['name']}: {len(files)}")
            continue
        cached = _cached(out)
        if cached is None:
            res = ask_structured(
                schema=ProductImages,
                system=load_prompt("02a_slike_system"),
                text=load_prompt("02a_slike_user", product=p["name"]),
                images=files,
                image_labels=[f.name for f in files],
                effort="low",
                log_path=log,
                label=f"slike:{p['sku']}",
            )
            cached = res.model_dump()
            # Referenca smije biti samo slika označena kao upotrebljiva. Ako je model
            # vratio promo kompoziciju, uzmi prvu upotrebljivu; ako je nema, ostavi prazno.
            usable = [i["file"] for i in cached["images"] if i["usable_as_reference"]]
            pick = res.best_reference if res.best_reference in usable else (usable[0] if usable else None)
            ref = next((f for f in files if f.name == pick), None)
            cached["best_reference"] = pick
            cached["best_reference_path"] = str(ref.relative_to(run.dir)) if ref else None
            if ref is None:
                # ručna referenca: <brand_dir>/<slug-proizvoda>.png|jpg (npr. inputs/brand/just-whey.png)
                from ..state import slugify
                brand_dir = settings.root / brif["brief"].get("brand_dir", "inputs/brand")
                manual = next((m for ext in (".png", ".jpg", ".jpeg", ".webp")
                               for m in [brand_dir / f"{slugify(p['name'])[:60]}{ext}"] if m.exists()), None)
                if manual:
                    dest = files[0].parent / f"rucna_referenca{manual.suffix}"
                    dest.write_bytes(manual.read_bytes())
                    cached["best_reference"], cached["best_reference_path"] = dest.name, str(dest.relative_to(run.dir))
                    cached["images"].append({"file": dest.name, "role": "packshot", "background": "ostalo", "extra_items": [],
                                             "visible_label_text": "", "usable_as_reference": True, "reason": "ručna referenca (čovjek)"})
                else:
                    cached["warning"] = (f"Nijedna slika nije čisti packshot — dodaj ručnu referencu "
                                         f"{brand_dir.relative_to(settings.root)}/{slugify(p['name'])[:60]}.png")
            _save(out, cached)
        image_roles[p["name"]] = cached

    # (b) dopuštene tvrdnje
    claims: Dict[str, Any] = {}
    for p in products:
        out = work / f"claims_{p['sku']}.json"
        if dry_run:
            print(f"[dry] tvrdnje {p['name']}")
            continue
        cached = _cached(out)
        if cached is None:
            res = ask_structured(
                schema=ProductClaims,
                system=load_prompt("02b_tvrdnje_system"),
                text=load_prompt("02b_tvrdnje_user", product=_product_digest(p)),
                effort="medium",
                log_path=log,
                label=f"tvrdnje:{p['sku']}",
            )
            cached = {"source_id": p["source_id"], **res.model_dump()}
            _save(out, cached)
        claims[p["name"]] = cached

    # (c) izmjerena paleta (kod, ne model)
    ig = brif["instagram"]
    posts = brif.get("instagram_posts", [])
    # naslovne slike objava koje nemaju screenshot (da se ista objava ne šalje dvaput)
    extra = [p for p in posts if p.get("image") and not p.get("screenshot")]
    ig_paths = [settings.root / i["file"] for i in ig] + [run.dir / p["image"] for p in extra]
    ig_labels = [i["label"] for i in ig] + [f"IG:{p['code']}" for p in extra]
    palette = measure_palette(ig_paths) if ig_paths else []
    _save(work / "palette_measured.json", palette)

    # (d) analiza brenda
    out = work / "brand.json"
    ig_meta = [{k: i[k] for k in ("label", "post_url", "post_type", "date_posted", "note")} for i in ig]
    ig_meta += [{"label": f"IG:{p['code']}" if p in extra else p.get("screenshot"), "source_id": p["source_id"],
                 "url": p["url"], "kind": p["kind"], "date": p["date"], "likes": p.get("likes"),
                 "comments": p.get("comments"), "caption": p.get("caption")} for p in posts]
    user = load_prompt(
        "02c_brend_user",
        brief=brif["brief"],
        sources=run.sources(),
        instagram=ig_meta,
        palette=palette,
        products=[_product_digest(p) for p in products],
        warnings=brif["warnings"],
    )
    if dry_run:
        print(f"[dry] analiza brenda: {len(ig_paths)} screenshotova, prompt {len(user)} znakova")
        return {}
    brand = _cached(out)
    if brand is None:
        res = ask_structured(
            schema=BrandAnalysis,
            system=load_prompt("02c_brend_system"),
            text=user,
            images=ig_paths,
            image_labels=ig_labels,
            effort="high",
            log_path=log,
            label="analiza_brenda",
        )
        brand = res.model_dump()
        _save(out, brand)

    output = {
        "brand": brand,
        "palette_measured": palette,
        "product_images": image_roles,
        "claims": claims,
        "product_files": brif["products"],
        "logo": brif["logo"],
    }
    run.save_output(PHASE, output)
    (run.phase_dir(PHASE) / "analiza.md").write_text(render_markdown(run, output), encoding="utf-8")
    return output


def render_markdown(run: Run, o: Dict[str, Any]) -> str:
    b = o["brand"]
    src = {s["id"]: s for s in run.sources()}
    L: List[str] = [f"# Analiza brenda — {run.info()['brand']}", "", b["summary"], "",
                    f"**Publika:** {b['audience']}", "", "## Nalazi", "",
                    "| Tema | Nalaz | Status | Dokaz |", "|---|---|---|---|"]
    for f in b["findings"]:
        ev = ", ".join(f"[{e}]({src[e]['url']})" if e in src else e for e in f["evidence"]) or "—"
        L.append(f"| {f['topic']} | {f['statement']} | **{f['status']}** | {ev} |")
    v = b["voice"]
    L += ["", "## Glas brenda", "", f"- Ton: {', '.join(v['tone_words'])}", f"- Obraćanje: {v['address']}",
          f"- Emoji: {v['emoji_usage']}", f"- Hashtagovi: {' '.join(v['hashtags_seen'])}",
          f"- CTA obrasci: {'; '.join(v['cta_patterns'])}", f"- Radi: {'; '.join(v['do'])}",
          f"- Ne radi: {'; '.join(v['dont'])}", "", "## Vizualni identitet", ""]
    vis = b["visual"]
    for c in vis["palette"]:
        L.append(f"- `{c['hex']}` {c['role']} — **{c['status']}** ({c['evidence']})")
    L += ["", f"**Izmjerena paleta (kod, iz screenshotova):** " +
          ", ".join(f"`{c['hex']}` {c['share']:.0%}" for c in o["palette_measured"]) or "—",
          "", f"- Tipografija: {vis['typography']}", f"- Fotografija: {vis['photo_style']}",
          f"- Prikaz proizvoda: {vis['product_presentation']}", f"- Prikaz osoba: {vis['people_presentation']}",
          f"- Rasporedi: {'; '.join(vis['layout_patterns'])}", "", "## Stupovi sadržaja", ""]
    for p in b["content_pillars"]:
        L.append(f"- **{p['name']}** — {p['description']} ({', '.join(p['example_evidence'])})")
    L += ["", "## Prilike", ""] + [f"- {x}" for x in b["opportunities"]]
    L += ["", "## Proizvodi: reference i tvrdnje", ""]
    for name, img in o["product_images"].items():
        L.append(f"### {name}\n\nReferenca: `{img.get('best_reference')}` — {img['packaging_description']}\n")
        for i in img["images"]:
            extra = f" (+ {', '.join(i['extra_items'])})" if i["extra_items"] else ""
            L.append(f"- `{i['file']}`: {i['role']}{extra} — referenca: {'da' if i['usable_as_reference'] else 'ne'}")
        c = o["claims"].get(name, {})
        if c:
            L.append("\n| Tvrdnja | Vrsta | Smije u objavu | Napomena |\n|---|---|---|---|")
            for cl in c["claims"]:
                L.append(f"| {cl['text']} | {cl['kind']} | {'da' if cl['safe_for_post'] else 'NE'} | {cl['note']} |")
            if c["inconsistencies"]:
                L.append("\n**Nedosljednosti u izvoru:** " + "; ".join(c["inconsistencies"]))
            if c["forbidden"]:
                L.append("\n**Ne tvrditi:** " + "; ".join(c["forbidden"]))
        L.append("")
    L += ["## Nedostupni izvori", ""] + [f"- {u['source']}: {u['reason']}" for u in b["unavailable_sources"]]
    L += ["", "## Izvori", ""] + [f"- {s['id']}: [{s['title'] or s['url']}]({s['url']}) — dohvaćeno {s['retrieved_at']}"
                                  for s in run.sources()]
    return "\n".join(L) + "\n"
