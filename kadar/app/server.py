"""Kadar web aplikacija (lokalna): sučelje nad istim fazama koje koristi CLI.

Pokretanje:  python -m kadar app        → http://127.0.0.1:8770

Svaki kadar se pokreće gumbom, radi u pozadinskoj niti, a sučelje prati
stanje. Izlazi su iste datoteke u runs/<brend>/ kao kod CLI-ja, pa se rad
može nastaviti bilo gdje (aplikacija, CLI ili Claude Code).
"""

from __future__ import annotations

import json
import re
import threading
import time
import traceback
from pathlib import Path
from typing import Any, Callable, Dict, Optional

import markdown as md
from flask import Flask, abort, jsonify, render_template, request, send_from_directory

from ..config import settings
from ..state import PHASES, Run, now_iso, slugify

HERE = Path(__file__).resolve().parent
app = Flask(__name__, template_folder=str(HERE / "templates"), static_folder=None)
app.config["TEMPLATES_AUTO_RELOAD"] = True
app.config["SEND_FILE_MAX_AGE_DEFAULT"] = 0

JOBS: Dict[str, Dict[str, Any]] = {}
LOCK = threading.Lock()
SERVE_ROOTS = ("runs/", "app/assets/", "inputs/", "isporuka/")
IMAGE_EXT = {".png", ".jpg", ".jpeg", ".webp"}

PHASE_INFO = {
    "01_brif": ("Brif i ulazi", "Brif, poveznice proizvoda i IG objava, logo i screenshotovi.",
                "Dohvaća činjenice i slike proizvoda, logo i javne podatke IG objava.", "Ulazi za analizu"),
    "02_analiza": ("Analiza brenda", "Ulazi iz kadra 01.",
                   "Bira čisti packshot, izvlači dopuštene tvrdnje s citatima, mjeri paletu, analizira ton i stil "
                   "(PROVJERENO / PRETPOSTAVKA / NEDOSTUPNO).", "analiza.md"),
    "03_plan": ("Plan objava", "Odobrena analiza + ljudske smjernice.",
                "Predlaže tri objave (cilj, format, koncept, slajdovi) i provjerava da su sve tvrdnje dopuštene.", "plan.md"),
    "04_izrada": ("Izrada", "Odobreni plan.", "Završni tekstovi i opisi (lektura), render slajdova u PNG.",
                  "3 gotove objave"),
    "05_provjera": ("Provjera", "Gotove objave.", "Automatska provjera proizvoda, tvrdnji, jezika i dimenzija.",
                    "Izvještaj provjere"),
    "06_isporuka": ("Isporuka", "Provjerene objave.", "Pakiranje objava, izvora i recepta za predaju.", "Paket za predaju"),
}


# ---- pozadinski poslovi ------------------------------------------------------------

def _job(slug: str) -> Optional[Dict[str, Any]]:
    with LOCK:
        return dict(JOBS[slug]) if slug in JOBS else None


def _start(slug: str, phase: str, fn: Callable[[], Any]):
    with LOCK:
        j = JOBS.get(slug)
        if j and j["state"] == "running":
            return jsonify(error=f"Već radi kadar {j['phase']}."), 409
        JOBS[slug] = {"phase": phase, "state": "running", "started": time.time(), "error": None}

    def work():
        try:
            fn()
            state, err = "done", None
        except BaseException as exc:  # SystemExit iz faza nosi poruku za korisnika
            state, err = "error", str(exc) or exc.__class__.__name__
            traceback.print_exc()
            try:
                Run(slug).set_meta(phase, status="failed", error=err, finished_at=now_iso())
            except Exception:
                pass
        with LOCK:
            JOBS[slug].update(state=state, error=err, finished=time.time())

    threading.Thread(target=work, daemon=True).start()
    return jsonify(ok=True)


# ---- pomoćne ----------------------------------------------------------------------

def _read_json(path: Path, default: Any = None) -> Any:
    return json.loads(path.read_text(encoding="utf-8")) if path.exists() else default


def _md(path: Path) -> str:
    return md.markdown(path.read_text(encoding="utf-8"), extensions=["tables"]) if path.exists() else ""


def _brief_path(slug: str) -> Path:
    return settings.inputs_dir / f"brief_{slug}.json"


def _brand_dir(run: Run) -> Path:
    brif = run.output("01_brif") or {}
    brief = brif.get("brief") or _read_json(_brief_path(run.slug), {}) or {}
    return settings.root / brief.get("brand_dir", f"inputs/{run.slug}/brand")


def _rel(p: Path) -> str:
    return "/files/" + str(p.resolve().relative_to(settings.root))


def _calls_seconds(run: Run) -> float:
    total = 0.0
    for phase in PHASES:
        f = run.phase_dir(phase) / "calls.jsonl"
        if f.exists():
            total += sum(json.loads(l).get("seconds", 0) for l in f.read_text(encoding="utf-8").splitlines() if l.strip())
    return round(total)


# ---- stranice i datoteke ---------------------------------------------------------

@app.get("/")
def index():
    return render_template("index.html")


@app.get("/files/<path:rel>")
def files(rel: str):
    if not rel.startswith(SERVE_ROOTS) or ".." in rel:
        abort(404)
    return send_from_directory(settings.root, rel)


# ---- API ---------------------------------------------------------------------------

@app.get("/api/runs")
def api_runs():
    runs = []
    if settings.runs_dir.exists():
        for d in sorted(settings.runs_dir.iterdir()):
            info = _read_json(d / "run.json")
            if info:
                runs.append({"slug": d.name, "brand": info.get("brand", d.name)})
    return jsonify(runs=runs, phases=PHASES,
                   info={p: dict(zip(("title", "input", "does", "output"), v)) for p, v in PHASE_INFO.items()})


@app.get("/api/run/<slug>")
def api_run(slug: str):
    run = Run(slug)
    if not (run.dir / "run.json").exists():
        abort(404)
    data: Dict[str, Any] = {"info": run.info(), "phases": {p: run.meta(p) for p in PHASES}, "job": _job(slug),
                            "next": run.next_phase(), "ai_seconds": _calls_seconds(run), "sources": run.sources()}
    brif = run.output("01_brif")
    if brif:
        products = []
        for rel in brif["products"]:
            pr = _read_json(run.dir / rel)
            imgs = [_rel(run.dir / i["file"]) for i in pr["images"] if i.get("file")][:6]
            products.append({"name": pr["name"], "url": pr["url"], "images": imgs, "faq": len(pr["faq"]),
                             "properties": len(pr["properties"])})
        data["brif"] = {"brief": brif["brief"], "warnings": brif["warnings"], "products": products,
                        "logo": _rel(run.dir / brif["logo"]["file"]) if brif.get("logo") else None,
                        "instagram": [{"label": i["label"], "img": "/files/" + i["file"], "url": i["post_url"]}
                                      for i in brif["instagram"]],
                        "posts": [{"url": p["url"], "date": p["date"], "kind": p["kind"], "likes": p.get("likes"),
                                   "caption": (p.get("caption") or "")[:160],
                                   "img": _rel(run.dir / p["image"]) if p.get("image") else None}
                                  for p in brif.get("instagram_posts", [])]}
    data["analysis_html"] = _md(run.phase_dir("02_analiza") / "analiza.md")
    data["plan_html"] = _md(run.phase_dir("03_plan") / "plan.md")
    notes = settings.inputs_dir / f"plan_notes_{slug}.md"
    data["plan_notes"] = notes.read_text(encoding="utf-8") if notes.exists() else ""
    data["brand"] = _read_json(_brand_dir(run) / "brand.json", {})
    data["scenes_html"] = _md(run.phase_dir("04_izrada") / "scene_prompts.md")
    create = run.output("04_izrada")
    if create:
        data["posts"] = [{**p, "slajdovi": ["/files/" + str((run.dir / s).relative_to(settings.root)) for s in p["slajdovi"]]}
                         for p in create["posts"]]
    qa = run.output("05_provjera")
    if qa:
        data["qa"] = qa
        data["qa_html"] = _md(run.phase_dir("05_provjera") / "provjera.md")
    delivery = run.output("06_isporuka")
    if delivery:
        data["delivery"] = delivery
        readme = settings.root / delivery["folder"] / "README.md"
        html = _md(readme)
        base = "/files/" + delivery["folder"] + "/"
        data["delivery_html"] = re.sub(r'(src|href)="(?!https?:|/)([^"]+)"', lambda m: f'{m.group(1)}="{base}{m.group(2)}"', html)
    return jsonify(data)


@app.post("/api/brief")
def api_brief():
    f = request.form
    brand = f.get("brand", "").strip()
    if not brand:
        return jsonify(error="Naziv brenda je obavezan."), 400
    slug = slugify(brand)
    base = f"inputs/{slug}"
    ig_dir, brand_dir = settings.root / base / "instagram", settings.root / base / "brand"
    ig_dir.mkdir(parents=True, exist_ok=True)
    brand_dir.mkdir(parents=True, exist_ok=True)

    lines = lambda key: [l.strip() for l in f.get(key, "").splitlines() if l.strip()]
    (ig_dir / "posts.txt").write_text("\n".join(lines("instagram_posts")) + "\n", encoding="utf-8")
    logo = request.files.get("logo")
    if logo and logo.filename:
        ext = Path(logo.filename).suffix.lower()
        if ext in {".svg", ".png", ".jpg", ".jpeg", ".webp"}:
            logo.save(brand_dir / f"logo{ext}")
    shots = [s for s in request.files.getlist("screenshots") if s.filename]
    for i, s in enumerate(shots, 1):
        ext = Path(s.filename).suffix.lower()
        if ext in IMAGE_EXT:
            s.save(ig_dir / f"upload_{i:02d}{ext}")

    brief = {
        "brand": brand, "brand_choice": f.get("brand_choice", "").strip(),
        "instagram": f.get("instagram", "").strip(), "website": f.get("website", "").strip(),
        "products": lines("products"), "audience": f.get("audience", ""), "goals": f.get("goals", ""),
        "inspiration": f.get("inspiration", ""), "tone_notes": f.get("tone_notes", ""),
        "constraints": f.get("constraints", ""), "language": f.get("language", "hrvatski") or "hrvatski",
        "instagram_screenshots_dir": f"{base}/instagram", "brand_dir": f"{base}/brand",
    }
    _brief_path(slug).write_text(json.dumps(brief, ensure_ascii=False, indent=2), encoding="utf-8")
    return _start_brief(slug, brief)


def _start_brief(slug: str, brief: Dict[str, Any]):
    from ..phases.p01_brif import run_brief

    run = Run.create(brief["brand"], instagram=brief.get("instagram", ""), website=brief.get("website", ""))
    return _start(run.slug, "01_brif", lambda: run_brief(run, brief))


@app.post("/api/run/<slug>/<phase>")
def api_run_phase(slug: str, phase: str):
    run = Run(slug)
    if phase not in PHASES:
        abort(404)
    idx = PHASES.index(phase)
    if idx > 0 and run.meta(PHASES[idx - 1]).get("status") != "approved":
        return jsonify(error=f"Prvo odobri kadar {PHASES[idx - 1]}."), 409
    if phase == "01_brif":
        brief = _read_json(_brief_path(slug))
        if not brief:
            return jsonify(error="Nema spremljenog brifa."), 400
        return _start_brief(slug, brief)
    if phase == "02_analiza":
        from ..phases.p02_analiza import run_analysis
        return _start(slug, phase, lambda: run_analysis(run))
    if phase == "03_plan":
        from ..phases.p03_plan import run_plan
        return _start(slug, phase, lambda: run_plan(run))
    if phase == "04_izrada":
        from ..phases.p04_izrada import run_create
        from ..render.gallery import build_gallery

        # "rewrite" = novi tekstovi (novi poziv modela); inače samo ponovni render postojećih tekstova
        rewrite = bool((request.get_json(silent=True) or {}).get("rewrite"))

        def create():
            copy_file = run.phase_dir(phase) / "copy.json"
            if rewrite and copy_file.exists():
                copy_file.unlink()
            run_create(run)
            build_gallery(run)
        return _start(slug, phase, create)
    if phase == "05_provjera":
        from ..phases.p05_provjera import run_qa
        vision = not (request.get_json(silent=True) or {}).get("code_only")
        return _start(slug, phase, lambda: run_qa(run, with_vision=vision))
    if phase == "06_isporuka":
        from ..phases.p06_isporuka import run_delivery
        return _start(slug, phase, lambda: run_delivery(run))
    abort(404)


@app.post("/api/fix/<slug>")
def api_fix(slug: str):
    """Petlja dorade: ispravci iz provjere → novi render → provjera u kodu."""
    from ..phases.p04_izrada import run_create
    from ..phases.p05_provjera import apply_fixes, run_qa
    from ..render.gallery import build_gallery

    run = Run(slug)

    def work():
        apply_fixes(run)
        run_create(run)
        build_gallery(run)
        run_qa(run, with_vision=False)
    return _start(slug, "05_provjera", work)


@app.post("/api/scenes/<slug>")
def api_scenes(slug: str):
    from ..phases.p04_izrada import run_creative
    run = Run(slug)
    return _start(slug, "04_izrada", lambda: run_creative(run))


@app.post("/api/approve/<slug>/<phase>")
def api_approve(slug: str, phase: str):
    run = Run(slug)
    if phase not in PHASES or run.output(phase) is None:
        return jsonify(error="Kadar još nema izlaz."), 400
    run.approve(phase, note=(request.get_json(silent=True) or {}).get("note", ""))
    return jsonify(ok=True, next=run.next_phase())


@app.post("/api/notes/<slug>")
def api_notes(slug: str):
    text = (request.get_json(silent=True) or {}).get("text", "")
    (settings.inputs_dir / f"plan_notes_{slug}.md").write_text(text, encoding="utf-8")
    return jsonify(ok=True)


@app.post("/api/brand/<slug>")
def api_brand(slug: str):
    body = request.get_json(silent=True) or {}
    hexre = re.compile(r"^#[0-9A-Fa-f]{6}$")
    colors = {k: v for k, v in (body.get("colors") or {}).items() if k in ("brand", "dark", "light") and hexre.match(v or "")}
    path = _brand_dir(Run(slug)) / "brand.json"
    path.parent.mkdir(parents=True, exist_ok=True)
    data = _read_json(path, {}) or {}
    data.setdefault("colors", {}).update(colors)
    for k in ("address", "handle", "link_label"):
        if k in body:
            data[k] = body[k]
    data["_note"] = f"Ljudska odluka iz aplikacije ({now_iso()[:10]}); nadjačava boje iz analize."
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
    return jsonify(ok=True, brand=data)


def serve(port: int = 8770, open_browser: bool = True) -> None:
    url = f"http://127.0.0.1:{port}"
    print(f"Kadar radi na {url}  (Ctrl+C za izlaz)")
    if open_browser:
        import webbrowser
        threading.Timer(1.0, lambda: webbrowser.open(url)).start()
    app.run(host="127.0.0.1", port=port, debug=False, threaded=True)
