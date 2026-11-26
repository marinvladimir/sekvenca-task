"""KADAR 03 · PLAN SADRŽAJA

Ulaz:   02_analiza/output.json (analiza, dopuštene tvrdnje, reference pakiranja)
        + opcionalne ljudske smjernice u inputs/plan_notes_<run>.md.
Radi:   predlaže tri objave (cilj, format, koncept, obrazloženje, slajdovi
        s rasporedima iz skupa predložaka), uz odbačene ideje i rizike.
        Automatski provjerava da su sve korištene tvrdnje s popisa dopuštenih.
Izlaz:  03_plan/output.json + plan.md → ulaz za izradu.
"""

from __future__ import annotations

from typing import Any, Dict, List

from ..config import settings
from ..llm import ask_structured, load_prompt
from ..schemas import ContentPlan
from ..state import Run, now_iso

PHASE = "03_plan"


def _allowed_claims(analysis: Dict[str, Any]) -> List[str]:
    return [c["text"] for pc in analysis["claims"].values() for c in pc["claims"] if c["safe_for_post"]]


def check_claims(plan: Dict[str, Any], allowed: List[str]) -> List[str]:
    """Svaka tvrdnja u planu mora doslovno postojati na popisu dopuštenih."""
    allowed_set = {a.strip() for a in allowed}
    problems = []
    for post in plan["posts"]:
        for i, slide in enumerate(post["slides"], 1):
            for c in slide["claims_used"]:
                if c.strip() not in allowed_set:
                    problems.append(f"Objava {post['number']}, slajd {i}: tvrdnja nije s popisa — «{c}»")
    return problems


def run_plan(run: Run) -> Dict[str, Any]:
    analysis = run.output("02_analiza")
    if not analysis:
        raise SystemExit("Faza 02_analiza nema izlaz.")
    run.set_meta(PHASE, status="running", started_at=now_iso())
    notes_path = settings.inputs_dir / f"plan_notes_{run.slug}.md"
    notes = notes_path.read_text(encoding="utf-8") if notes_path.exists() else "(nema)"

    claims = {name: {k: pc[k] for k in ("claims", "inconsistencies", "forbidden")}
              for name, pc in analysis["claims"].items()}
    packaging = {name: {"referenca": img.get("best_reference_path"), "pakiranje": img["packaging_description"]}
                 for name, img in analysis["product_images"].items()}

    plan = ask_structured(
        schema=ContentPlan,
        system=load_prompt("03_plan_system"),
        text=load_prompt("03_plan_user", brief=run.output("01_brif")["brief"], analysis=analysis["brand"],
                         claims=claims, packaging=packaging, human_notes=notes),
        effort="high",
        log_path=run.phase_dir(PHASE) / "calls.jsonl",
        label="plan",
    ).model_dump()

    # ljudske dorade plana (inputs/fixes_<run>.json, "phase": "03_plan") — dio recepta, ne ručna izmjena
    fixes_path = settings.inputs_dir / f"fixes_{run.slug}.json"
    applied = []
    if fixes_path.exists():
        import json as _json
        text = _json.dumps(plan, ensure_ascii=False)
        for fx in _json.loads(fixes_path.read_text(encoding="utf-8")):
            if fx.get("phase") == "03_plan" and fx["original"] in text:
                text = text.replace(fx["original"], fx["suggestion"])
                applied.append(f'{fx["original"]} → {fx["suggestion"]}')
        plan = _json.loads(text)

    problems = check_claims(plan, _allowed_claims(analysis))
    output = {"plan": plan, "claim_check": problems, "human_notes": notes, "human_edits": applied}
    run.save_output(PHASE, output)
    (run.phase_dir(PHASE) / "plan.md").write_text(render_markdown(output), encoding="utf-8")
    return output


def render_markdown(o: Dict[str, Any]) -> str:
    p = o["plan"]
    L = ["# Plan sadržaja", "", p["strategy_summary"], ""]
    for post in p["posts"]:
        L += [f"## Objava {post['number']}: {post['title']}", "",
              f"- **Cilj:** {post['goal']}  ·  **Format:** {post['format']}  ·  **Proizvod:** {post['product']}",
              f"- **Koncept:** {post['concept']}", f"- **Zašto odgovara brendu:** {post['why_it_fits']} ({', '.join(post['evidence'])})",
              f"- **KPI:** {post['kpi']}", f"- **CTA:** {post['cta']}", f"- **Hashtagovi:** {' '.join(post['hashtags'])}",
              f"- **Opis objave:** {post['caption_brief']}", "", "| # | Raspored | Naslov | Tekst | Tvrdnje |", "|---|---|---|---|---|"]
        for i, s in enumerate(post["slides"], 1):
            extra = f" [{s['stat']}]" if s["stat"] else ""
            opts = f" Opcije: {' / '.join(s['options'])}" if s["options"] else ""
            L.append(f"| {i} | {s['layout']} ({s['background']}) | {s['headline']}{extra} | {s['body']}{opts} | {'; '.join(s['claims_used']) or '—'} |")
        L += ["", "**Rizici:** " + "; ".join(post["risks"]), ""]
    L += ["## Odbačene ideje", ""] + [f"- {r['idea']} — {r['reason']}" for r in p["rejected_ideas"]]
    L += ["", "## Provjera tvrdnji", ""] + ([f"- ⚠ {x}" for x in o["claim_check"]] or ["- Sve tvrdnje su s popisa dopuštenih."])
    return "\n".join(L) + "\n"
