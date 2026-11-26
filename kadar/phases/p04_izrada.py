"""KADAR 04 · IZRADA

Ulaz:   03_plan/output.json (odobren, s ljudskim doradama), reference
        proizvoda i logo iz faza 01–02, boje iz inputs/brand/brand.json.
Radi:   (a) završni tekstovi i opisi (jedan poziv modela, lektura, "ti"),
        (b) render svakog slajda u PNG (HTML predložak → Playwright).
        Raspored, pozadina i proizvod dolaze iz plana; model mijenja samo tekst.
Izlaz:  04_izrada/objava_N/slajd_XX.png + opis.txt + objava.json → ulaz za provjeru.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict, List, Optional

from ..config import settings
from ..llm import ask_structured, load_prompt
from ..render.renderer import render_post
from ..schemas import FinalCopy
from ..state import Run, now_iso

PHASE = "04_izrada"

# riječ u tekstu slajda → dio naziva datoteke packshota te varijante
FLAVOR_HINTS = {"bez okusa": "unflavored", "cookies": "cookie", "krokant": "caramel", "karamel": "caramel",
                "vanilij": "vanilla", "120 kaps": "120", "60 kaps": "60"}


def _match_product(name: str, refs: Dict[str, Dict[str, Any]]) -> Optional[str]:
    if not name:
        return None
    import re as _re
    words = lambda t: {w for w in _re.findall(r"\w+", t.lower()) if len(w) > 2}
    n = words(name)
    best, score = None, 0.0
    for key in refs:
        k = words(key)
        sc = len(n & k) / max(1, len(n))  # udio riječi iz plana koje postoje u nazivu proizvoda
        if sc > score:
            best, score = key, sc
    return best if score >= 0.34 else None


def _image_for(slide_text: str, product: str, analysis: Dict[str, Any], run: Run) -> Optional[Path]:
    info = analysis["product_images"][product]
    usable = [i["file"] for i in info["images"] if i["usable_as_reference"]]
    text = slide_text.lower()
    for hint, token in FLAVOR_HINTS.items():
        if hint in text:
            hit = next((f for f in usable if token in f.lower()), None)
            if hit:
                return run.dir / Path(info["best_reference_path"]).parent / hit
    return run.dir / info["best_reference_path"] if info.get("best_reference_path") else None


def run_create(run: Run, copy_only: bool = False) -> Dict[str, Any]:
    plan_out = run.output("03_plan")
    analysis = run.output("02_analiza")
    if not plan_out or not analysis:
        raise SystemExit("Nedostaje odobreni plan ili analiza.")
    phase_dir = run.phase_dir(PHASE)
    run.set_meta(PHASE, status="running", started_at=now_iso())
    plan = plan_out["plan"]

    # (a) završni tekstovi — spremaju se, pa ponovni render ne troši novi poziv
    copy_path = phase_dir / "copy.json"
    if copy_path.exists():
        copy = json.loads(copy_path.read_text(encoding="utf-8"))
    else:
        notes_path = settings.inputs_dir / f"plan_notes_{run.slug}.md"
        copy = ask_structured(
            schema=FinalCopy,
            system=load_prompt("04_tekst_system"),
            text=load_prompt("04_tekst_user", plan=plan,
                             human_notes=notes_path.read_text(encoding="utf-8") if notes_path.exists() else "(nema)"),
            effort="high",
            log_path=phase_dir / "calls.jsonl",
            label="tekstovi",
        ).model_dump()
        copy_path.write_text(json.dumps(copy, ensure_ascii=False, indent=2), encoding="utf-8")
    if copy_only:
        return copy

    # (b) render
    logo_dark = run.dir / analysis["logo"]["file"]
    logo_white = run.dir / analysis["logo"].get("variant_white", analysis["logo"]["file"])
    posts_out: List[Dict[str, Any]] = []
    for planned, final in zip(plan["posts"], copy["posts"]):
        product = _match_product(planned["product"], analysis["product_images"])
        slides, images = [], {}
        for ps, fs in zip(planned["slides"], final["slides"]):
            s = {"layout": ps["layout"], "background": ps["background"], **fs}
            s["product"] = ""
            # proizvod po slajdu (karusel s više proizvoda), inače proizvod objave
            slide_product = _match_product(ps.get("product", ""), analysis["product_images"]) or product
            if slide_product and (ps.get("product") or ps["layout"] in ("proizvod", "story_otkrivanje", "story_poveznica")):
                img = _image_for(" ".join([fs["headline"], fs["body"]]), slide_product, analysis, run)
                product_key = slide_product
                if img:
                    key = f"{product_key}::{img.name}"
                    images[key] = img
                    s["product"] = key
            s["source"] = fs.get("footnote", "")
            slides.append(s)
        story = planned["format"] == "story_niz"
        out_dir = phase_dir / f"objava_{planned['number']}"
        sd = scene_dir(run)
        scenes = {}
        for i in range(1, len(slides) + 1):
            for ext in (".jpg", ".jpeg", ".png", ".webp"):
                f = sd / f"objava_{planned['number']}_slajd_{i:02d}{ext}"
                if f.exists():
                    scenes[i] = f
                    break
        pngs = render_post(slides, story, out_dir, run.dir, images, logo_dark, logo_white, scenes)
        (out_dir / "opis.txt").write_text(final["caption"] + "\n", encoding="utf-8")
        meta = {
            "objava": planned["number"], "naslov": planned["title"], "cilj": planned["goal"],
            "format": planned["format"], "proizvod": planned["product"], "koncept": planned["concept"],
            "obrazlozenje": planned["why_it_fits"], "kpi": planned["kpi"], "opis": final["caption"],
            "alt_text": final["alt_text"], "slajdovi": [str(p.relative_to(run.dir)) for p in pngs],
            "tekst_slajdova": final["slides"],
        }
        (out_dir / "objava.json").write_text(json.dumps(meta, ensure_ascii=False, indent=2), encoding="utf-8")
        posts_out.append(meta)

    output = {"posts": posts_out, "editor_notes": copy.get("editor_notes", [])}
    run.save_output(PHASE, output)
    return output


# ---- kreativni sloj: scene za naslovnice + razigraniji naslovi -------------------

def scene_dir(run: Run) -> Path:
    brif = run.output("01_brif") or {}
    base = (brif.get("brief") or {}).get("brand_dir", "inputs/brand")  # isti default kao renderer
    return settings.root / Path(base).parent / "scenes"


def run_creative(run: Run) -> Dict[str, Any]:
    """Jedan AI poziv: prompti za scene naslovnica (čovjek ih generira u alatu po izboru) i 3 naslova po naslovnici."""
    from ..schemas import CreativePack

    plan = run.output("03_plan")["plan"]
    analysis = run.output("02_analiza")["brand"]
    covers = []
    for p in plan["posts"]:
        s = p["slides"][0]
        covers.append({"post": p["number"], "slide": 1, "format": p["format"], "concept": p["concept"],
                       "headline": s["headline"], "product": p["product"]})
    pack = ask_structured(
        schema=CreativePack,
        system=load_prompt("04b_scene_system"),
        text=load_prompt("04b_scene_user", style={"photo_style": analysis["visual"]["photo_style"],
                                                  "pillars": analysis["content_pillars"], "voice": analysis["voice"]},
                         brief=run.output("01_brif")["brief"], covers=covers),
        effort="low",
        log_path=run.phase_dir(PHASE) / "calls.jsonl",
        label="scene",
    ).model_dump()
    out = run.phase_dir(PHASE) / "scene.json"
    out.write_text(json.dumps(pack, ensure_ascii=False, indent=2), encoding="utf-8")
    sd = scene_dir(run)
    sd.mkdir(parents=True, exist_ok=True)
    md = ["# Scene za naslovnice (ljudski korak)", "",
          "Svaki prompt zalijepi u generator slika po izboru (omjer 4:5 za feed, 9:16 za story) i spremi sliku pod navedenim imenom.",
          f"Mapa: `{sd.relative_to(settings.root)}/`. Zatim pokreni `create` — slajd dobiva scenu, a proizvod ostaje prava fotografija.", ""]
    for sc in pack["scenes"]:
        md += [f"## Objava {sc['post']}, slajd {sc['slide']} → `objava_{sc['post']}_slajd_{sc['slide']:02d}.jpg`", "",
               "```", sc["prompt"], "```", f"*{sc['why']}*", ""]
    md += ["# Prijedlozi naslova (izbor je ljudska odluka → inputs/fixes_<brend>.json)", ""]
    for h in pack["headlines"]:
        md += [f"- **Objava {h['post']}:** " + " · ".join(h["options"]) + f"  \n  *{h['why']}*"]
    (run.phase_dir(PHASE) / "scene_prompts.md").write_text("\n".join(md) + "\n", encoding="utf-8")
    return pack
