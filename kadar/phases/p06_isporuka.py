"""KADAR 06 · ISPORUKA

Ulaz:   odobreni kadrovi 01–05.
Radi:   slaže paket za predaju u isporuka/<run>/: tri objave (slajdovi redom,
        opis, format, cilj, obrazloženje, KPI, upute za objavu), izvori i
        ulazne reference, analiza, plan, izvještaji provjere, sažetak potrošnje.
Izlaz:  isporuka/<run>/README.md (pregled sa slikama, čita se i na GitHubu).
"""

from __future__ import annotations

import csv
import json
import shutil
from pathlib import Path
from typing import Any, Dict, List

from ..config import settings
from ..state import PHASES, Run, now_iso

PHASE = "06_isporuka"
GOALS = {"edukacija_spremanja": "Edukacija — spremanja", "predstavljanje_proizvoda": "Predstavljanje proizvoda",
         "interes_za_kupnju": "Interes za kupnju", "reakcije_komentari": "Reakcije i komentari"}
FORMATS = {"karusel": "Karusel (feed, 1080×1350)", "slika": "Jedna slika (feed, 1080×1350)",
           "story_niz": "Niz storyja (1080×1920)"}


def _usage(run: Run) -> Dict[str, Any]:
    calls, seconds, tin, tout = 0, 0.0, 0, 0
    for p in PHASES:
        f = run.phase_dir(p) / "calls.jsonl"
        if f.exists():
            for line in f.read_text(encoding="utf-8").splitlines():
                if line.strip():
                    d = json.loads(line)
                    calls += 1
                    seconds += d.get("seconds") or 0
                    tin += d.get("input_tokens") or 0
                    tout += d.get("output_tokens") or 0
    return {"llm_calls": calls, "llm_minutes": round(seconds / 60, 1), "input_tokens": tin, "output_tokens": tout}


def _posting_notes(post: Dict[str, Any]) -> List[str]:
    notes = ["Slajdove objavi redom (slajd_01 … slajd_NN).", "Opis kopiraj iz `opis.txt` bez izmjena."]
    if post["format"] == "story_niz":
        notes = ["Kadrove objavi redom kao story (kadar_01 … kadar_NN).",
                 "Preko grafike ankete/kviza postavi nativne Instagram stikere (Poll / Quiz) s istim pitanjem i opcijama; "
                 "grafika pokazuje njihov položaj.",
                 "Na zadnji kadar postavi Link stiker s tekstom „Pogledaj D3” i poveznicom na stranicu proizvoda.",
                 "Nakon 24 h spremi niz u highlight (npr. „Članci”)."]
    return notes


def run_delivery(run: Run) -> Dict[str, Any]:
    create, plan, qa = run.output("04_izrada"), run.output("03_plan"), run.output("05_provjera")
    brif, analysis = run.output("01_brif"), run.output("02_analiza")
    if not (create and plan and brif and analysis):
        raise SystemExit("Isporuka traži izlaze kadrova 01–04.")
    run.set_meta(PHASE, status="running", started_at=now_iso())
    out = settings.root / "isporuka" / run.slug
    if out.exists():
        shutil.rmtree(out)
    out.mkdir(parents=True)

    # objave
    posts_md = []
    for post in create["posts"]:
        n = post["objava"]
        d = out / f"objava_{n}"
        d.mkdir()
        prefix = "kadar" if post["format"] == "story_niz" else "slajd"
        files = []
        for i, rel in enumerate(post["slajdovi"], 1):
            name = f"{prefix}_{i:02d}.png"
            shutil.copy(run.dir / rel, d / name)
            files.append(name)
        (d / "opis.txt").write_text(post["opis"].strip() + "\n", encoding="utf-8")
        info = [f"# Objava {n}: {post['naslov']}", "",
                f"- **Format:** {FORMATS.get(post['format'], post['format'])}, {len(files)} {'kadrova' if prefix == 'kadar' else 'slajdova'}",
                f"- **Cilj:** {GOALS.get(post['cilj'], post['cilj'])}", f"- **Proizvod:** {post['proizvod']}",
                f"- **KPI:** {post['kpi']}", "", "## Koncept", "", post["koncept"], "",
                "## Zašto odgovara brendu", "", post["obrazlozenje"], "", "## Opis objave", "", "```", post["opis"].strip(), "```", "",
                "## Alternativni tekst", "", post["alt_text"], "", "## Upute za objavu", ""] + \
               [f"- {x}" for x in _posting_notes(post)] + ["", "## Slajdovi", ""] + [f"![{f}]({f})" for f in files]
        (d / "README.md").write_text("\n".join(info) + "\n", encoding="utf-8")
        posts_md.append((n, post, files))

    # dokumenti faza
    docs = {"analiza.md": run.phase_dir("02_analiza") / "analiza.md", "plan.md": run.phase_dir("03_plan") / "plan.md",
            "provjera.md": run.phase_dir("05_provjera") / "provjera.md",
            "provjera_krug1.md": run.phase_dir("05_provjera") / "krug1_provjera.md",
            "provjera_krug2.md": run.phase_dir("05_provjera") / "krug2_provjera.md"}
    (out / "dokumenti").mkdir()
    for name, src in docs.items():
        if src.exists():
            shutil.copy(src, out / "dokumenti" / name)

    # izvori i ulazi
    info = run.info()
    src = ["# Izvori i ulazne reference", "", f"- **Instagram profil:** {info.get('instagram')}",
           f"- **Web-stranica:** {info.get('website')}", f"- **Run započet:** {info.get('created_at', '')[:10]}", "",
           "## Registar izvora (ID-evi se koriste u analizi i planu)", "", "| ID | Vrsta | Naslov | Poveznica | Dohvaćeno |", "|---|---|---|---|---|"]
    src += [f"| {s['id']} | {s['kind']} | {s['title']} | {s['url']} | {s['retrieved_at'][:16]} |" for s in run.sources()]
    src += ["", "## Brif (ulazi za demonstraciju)", "", "```json", json.dumps(brif["brief"], ensure_ascii=False, indent=2), "```", "",
            "## Instagram screenshotovi (ručni ulaz)", ""]
    shots = out / "ulazi" / "instagram"
    shots.mkdir(parents=True)
    for item in brif["instagram"]:
        p = settings.root / item["file"]
        if p.exists():
            # smanjena JPG kopija (original ostaje u inputs/)
            from PIL import Image
            img = Image.open(p).convert("RGB")
            img.thumbnail((1600, 1600))
            name = p.stem + ".jpg"
            img.save(shots / name, quality=82)
            src.append(f"- `ulazi/instagram/{name}` — {item['post_url'] or '(bez poveznice)'} {item['note'][:80]}")
    src += ["", "## Reference proizvoda (izabrani packshotovi)", ""]
    refs = out / "ulazi" / "proizvodi"
    refs.mkdir(parents=True)
    for name, img in analysis["product_images"].items():
        if img.get("best_reference_path"):
            p = run.dir / img["best_reference_path"]
            shutil.copy(p, refs / p.name)
            src.append(f"- **{name}:** `ulazi/proizvodi/{p.name}`")
    if brif.get("logo"):
        shutil.copy(run.dir / brif["logo"]["file"], out / "ulazi" / Path(brif["logo"]["file"]).name)
        src.append(f"- **Logo:** `ulazi/{Path(brif['logo']['file']).name}` (dohvaćen sa službene stranice)")
    (out / "izvori.md").write_text("\n".join(src) + "\n", encoding="utf-8")

    usage = _usage(run)
    s = (qa or {}).get("summary", {})
    readme = [f"# {info['brand']} — tri gotove objave", "",
              f"Izrađeno receptom **Kadar** · Instagram: {info.get('instagram')} · {now_iso()[:10]}", "",
              "| # | Objava | Format | Cilj |", "|---|---|---|---|"]
    readme += [f"| {n} | [{p['naslov']}](objava_{n}/README.md) | {FORMATS.get(p['format'], p['format'])} | {GOALS.get(p['cilj'], p['cilj'])} |"
               for n, p, _ in posts_md]
    if qa:
        rounds = []
        for label, f in (("krug 1", "krug1_output.json"), ("krug 2", "krug2_output.json")):
            path = run.phase_dir("05_provjera") / f
            if path.exists():
                r = json.loads(path.read_text(encoding="utf-8"))
                rs = r["summary"]
                rounds.append(f"{label} (kod + AI vizija): {r['total']} provjera — ✅ {rs.get('pass', 0)} · ⚠️ {rs.get('warn', 0)} · ❌ {rs.get('fail', 0)}")
        rounds.append(f"završno nakon ispravaka: {qa['total']} provjera — ✅ {s.get('pass', 0)} · ⚠️ {s.get('warn', 0)} · ❌ {s.get('fail', 0)}")
        readme += ["", "**Provjera kvalitete** ([završni izvještaj](dokumenti/provjera.md) · [krug 1](dokumenti/provjera_krug1.md) · "
                   "[krug 2](dokumenti/provjera_krug2.md)):", ""] + [f"- {x}" for x in rounds]
    readme += ["", f"**AI pozivi:** {usage['llm_calls']} · ukupno {usage['llm_minutes']} min generiranja", "",
               "Dokumenti: [analiza brenda](dokumenti/analiza.md) · [plan](dokumenti/plan.md) · [izvori i ulazi](izvori.md)", ""]
    for n, p, files in posts_md:
        readme += [f"## Objava {n}: {p['naslov']}", "", f"*{FORMATS.get(p['format'])} · {GOALS.get(p['cilj'])}*", "",
                   " ".join(f'<img src="objava_{n}/{f}" width="{150 if p["format"] == "story_niz" else 190}">' for f in files), "",
                   "**Opis:**", "", "> " + p["opis"].strip().replace("\n", "\n> "), ""]
    (out / "README.md").write_text("\n".join(readme) + "\n", encoding="utf-8")

    output = {"folder": str(out.relative_to(settings.root)), "posts": len(posts_md), "usage": usage,
              "qa_summary": s, "files": sorted(str(p.relative_to(out)) for p in out.rglob("*") if p.is_file())}
    run.save_output(PHASE, output)
    return output
