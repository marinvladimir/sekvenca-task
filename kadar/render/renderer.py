"""Render slajdova: HTML predložak (Jinja2) → PNG preko Playwrighta (Chromium).

Tekst, logo i raspored renderira preglednik, ne model za slike, pa su
hrvatski dijakritici, logo i packshot točni do piksela. Proizvod je uvijek
stvarna fotografija s webshopa (referenca iz analize) u bijeloj kartici.
"""

from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any, Dict, List, Optional

from jinja2 import Environment, FileSystemLoader, select_autoescape

from ..config import settings

HERE = Path(__file__).resolve().parent
FEED = (1080, 1350)
STORY = (1080, 1920)

_env = Environment(loader=FileSystemLoader(str(HERE / "templates")), autoescape=select_autoescape(["html"]))


def _palette_colors(run_dir: Path) -> Dict[str, str]:
    """Boje iz palete koju je kadar 02 izmjerio kodom: najzasićenija boja = brend, najtamnija i najsvjetlija = podloge."""
    import colorsys
    out = run_dir / "02_analiza" / "output.json"
    if not out.exists():
        return {}
    pal = json.loads(out.read_text(encoding="utf-8")).get("palette_measured") or []
    def hsv(h):
        r, g, b = (int(h[i:i + 2], 16) / 255 for i in (1, 3, 5))
        return colorsys.rgb_to_hsv(r, g, b)
    res: Dict[str, str] = {}
    colored = [c for c in pal if c.get("share", 0) >= 0.005 and hsv(c["hex"])[1] > 0.35 and hsv(c["hex"])[2] > 0.35]
    if colored:
        res["brand"] = max(colored, key=lambda c: hsv(c["hex"])[1] * hsv(c["hex"])[2])["hex"]
    if pal:
        res["dark"] = min(pal, key=lambda c: hsv(c["hex"])[2])["hex"]
        light = [c for c in pal if c["hex"].upper() != "#FFFFFF"] or pal
        res["light"] = max(light, key=lambda c: hsv(c["hex"])[2] - hsv(c["hex"])[1])["hex"]
    return res


def brand_config(run_dir: Path) -> Dict[str, Any]:
    """Boje i postavke brenda: ljudska odluka (inputs/brand/brand.json) ima prednost pred analizom."""
    cfg = {"colors": {"brand": "#2B2B2B", "dark": "#151515", "light": "#F4F2EE"}, "handle": "", "link_label": ""}
    brif = run_dir / "01_brif" / "output.json"
    brief = json.loads(brif.read_text(encoding="utf-8"))["brief"] if brif.exists() else {}
    brand_dir = brief.get("brand_dir", "inputs/brand")
    # zadano za bilo koji brend: @handle iz Instagram poveznice, domena weba, boje iz izmjerene palete
    m = re.search(r"instagram\.com/([A-Za-z0-9_.]+)", brief.get("instagram", ""))
    if m:
        cfg["handle"] = "@" + m.group(1)
    dom = re.sub(r"^https?://(www\.)?", "", brief.get("website", "")).strip("/")
    if dom:
        cfg["link_label"] = dom
    cfg["colors"].update(_palette_colors(run_dir))
    path = settings.root / brand_dir / "brand.json"
    if path.exists():
        data = json.loads(path.read_text(encoding="utf-8"))
        cfg["colors"].update(data.get("colors", {}))
        cfg.update({k: v for k, v in data.items() if k != "colors"})
    return cfg


def headline_html(text: str) -> str:
    """*riječ* u naslovu → <em> (naglašena riječ u boji, kao u objavama brenda)."""
    from markupsafe import escape
    safe = str(escape(text))
    safe = re.sub(r"\*(.+?)\*", r"<em>\1</em>", safe)
    # mjerne jedinice ostaju malim slovima (verzal bi μg pretvorio u grčko "ΜG")
    safe = re.sub(r"(?<=\d)(\s?)(μg|µg|mg|g|ml|kcal|kJ)\b", lambda m: ("&nbsp;" if m.group(1) else "") + f'<span class="unit">{m.group(2)}</span>', safe)
    # kratke riječi (od, u, s, za, i, ili…) i broj ostaju u istom retku kao sljedeća riječ
    return re.sub(r"(?<=\s)(\w{1,3}|\d+(?:,\d+)?)\s(?=\S)", r"\1&nbsp;", safe)


def clean_slide(s: Dict[str, Any]) -> Dict[str, Any]:
    """Zaštita predloška od tipičnih odstupanja modela (kod je dio recepta)."""
    strip_stars = lambda t: re.sub(r"\*(.+?)\*", r"\1", t or "")
    # oznaka slajda ("02 / 07 ·") već postoji u brojaču gore desno
    s["kicker"] = re.sub(r"^\s*\d+\s*/\s*\d+\s*[·|:-]?\s*", "", strip_stars(s.get("kicker", "")))
    s["kicker"] = re.sub(r"\s*[·|]?\s*\d+\s*/\s*\d+\s*$", "", s["kicker"])
    # "Listaj →" u tekstu je suvišan jer je u donjoj traci
    s["body"] = re.sub(r"\s*Listaj\s*[→>]*\s*$", "", strip_stars(s.get("body", ""))).strip()
    s["options"] = [strip_stars(o) for o in s.get("options", [])]
    if s["layout"] == "mit_cinjenica" and len(s["options"]) < 2:
        myth = re.sub(r"\s*\bMIT\b\s*", " ", strip_stars(s.get("headline", ""))).strip(" „“\"")
        s["options"] = [myth, s["body"]]
        s["headline"] = "Mit ili *činjenica*?"
    return s


def render_post(slides: List[Dict[str, Any]], story: bool, out_dir: Path, run_dir: Path,
                product_images: Dict[str, Path], logo_dark: Path, logo_white: Path,
                scenes: Optional[Dict[int, Path]] = None) -> List[Path]:
    from playwright.sync_api import sync_playwright

    cfg = brand_config(run_dir)
    logo_dark, logo_white = logo_dark.resolve(), logo_white.resolve()
    product_images = {k: v.resolve() for k, v in product_images.items()}
    W, H = STORY if story else FEED
    out_dir.mkdir(parents=True, exist_ok=True)
    tmpl = _env.get_template("slide.html")
    outputs: List[Path] = []
    metrics: List[Dict[str, Any]] = []
    with sync_playwright() as pw:
        browser = pw.chromium.launch()
        page = browser.new_page(viewport={"width": W, "height": H}, device_scale_factor=1)
        for idx, s in enumerate(slides, 1):
            s = dict(s)
            s = clean_slide(s)
            s["headline_html"] = headline_html(s.get("headline", ""))
            body = s.get("body", "")
            s["bullets"] = [b.strip(" •-") for b in re.split(r"\s*[•;]\s*|\n", body) if b.strip(" •-")] \
                if s["layout"] == "proizvod" and ("•" in body or ";" in body or "\n" in body) else []
            img = product_images.get(s.get("product") or "")
            scene = (scenes or {}).get(idx)
            if scene:
                s["background"] = "scena"
            html = tmpl.render(
                s=s, idx=idx, total=len(slides), story=story, W=W, H=H, c=cfg["colors"],
                fonts=(HERE / "fonts").as_uri(), logo_dark=logo_dark.as_uri(), logo_white=logo_white.as_uri(),
                product_img=img.as_uri() if img else None, handle=cfg.get("handle", ""),
                link_label=cfg.get("link_label", ""), source=s.get("source", ""),
                scene=scene.resolve().as_uri() if scene else None,
            )
            html_path = out_dir / f"_slajd_{idx:02d}.html"
            html_path.write_text(html, encoding="utf-8")
            page.goto(html_path.as_uri())
            page.wait_for_function("document.body.dataset.ready === '1'", timeout=15000)
            png = out_dir / f"slajd_{idx:02d}.png"
            page.screenshot(path=str(png), clip={"x": 0, "y": 0, "width": W, "height": H})
            metrics.append({"slide": idx, "layout": s["layout"], "png": png.name, "W": W, "H": H,
                            **json.loads(page.evaluate("document.body.dataset.metrics") or "{}")})
            html_path.unlink()
            outputs.append(png)
        browser.close()
    (out_dir / "render.json").write_text(json.dumps(metrics, ensure_ascii=False, indent=2), encoding="utf-8")
    return outputs
