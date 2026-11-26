"""Naredbeni redak za Kadar.

Primjeri:
  python -m kadar init "GymBeam HR" --instagram https://www.instagram.com/gymbeamhr/ --website https://gymbeam.hr
  python -m kadar scrape gymbeam-hr https://gymbeam.hr/protein-just-whey-gymbeam.html
  python -m kadar status gymbeam-hr

Tijek (svaki kadar se pregleda i odobri prije sljedećeg):
  python -m kadar brief --from inputs/brief_gymbeam-hr.json
  python -m kadar approve gymbeam-hr 01_brif
  python -m kadar analyze gymbeam-hr
  python -m kadar approve gymbeam-hr 02_analiza
"""

from __future__ import annotations

import argparse
import sys

from .state import PHASES, Run


def cmd_init(a: argparse.Namespace) -> None:
    run = Run.create(a.brand, instagram=a.instagram, website=a.website)
    print(f"Run spreman: {run.dir}")


def cmd_scrape(a: argparse.Namespace) -> None:
    from .scrape.product import scrape_product

    run = Run(a.run)
    run.info()
    for url in a.urls:
        try:
            rec = scrape_product(url, run, download_images=not a.no_images)
        except Exception as exc:  # jedan neuspjeli proizvod ne ruši ostale
            print(f"✗ {url}: {exc}", file=sys.stderr)
            continue
        ok = sum(1 for i in rec["images"] if i["file"])
        print(
            f"✓ {rec['name']} [{rec['source_id']}] — {len(rec['properties'])} svojstava, "
            f"{len(rec['faq'])} FAQ, {len(rec['offers'])} varijanti, {ok}/{len(rec['images'])} slika"
            f"\n  → {rec['_path']}"
        )


def cmd_brief(a: argparse.Namespace) -> None:
    from pathlib import Path

    from .phases.p01_brif import ask_brief, load_brief_file, run_brief

    brief = load_brief_file(Path(a.from_file)) if a.from_file else ask_brief()
    run = Run.create(brief["brand"], instagram=brief.get("instagram", ""), website=brief.get("website", ""))
    out = run_brief(run, brief)
    print(f"\nKADAR 01 · BRIF gotov → {run.phase_dir('01_brif')}/output.json")
    print(f"  proizvoda: {len(out['products'])}, IG screenshotova: {len(out['instagram'])}, logo: {bool(out['logo'])}")
    for w in out["warnings"]:
        print(f"  ⚠ {w}")
    print(f"\nPregledaj i odobri: python -m kadar approve {run.slug} 01_brif")


def cmd_analyze(a: argparse.Namespace) -> None:
    from .phases.p02_analiza import run_analysis

    run = Run(a.run)
    run.info()
    if run.meta("01_brif").get("status") != "approved" and not a.force:
        raise SystemExit("01_brif nije odobren. Odobri ga ili dodaj --force.")
    run_analysis(run, dry_run=a.dry_run)
    if not a.dry_run:
        print(f"KADAR 02 · ANALIZA gotova → {run.phase_dir('02_analiza')}/analiza.md")
        print(f"Pregledaj i odobri: python -m kadar approve {run.slug} 02_analiza")


def cmd_plan(a: argparse.Namespace) -> None:
    from .phases.p03_plan import run_plan

    run = Run(a.run)
    if run.meta("02_analiza").get("status") != "approved" and not a.force:
        raise SystemExit("02_analiza nije odobrena. Odobri je ili dodaj --force.")
    out = run_plan(run)
    print(f"KADAR 03 · PLAN gotov → {run.phase_dir('03_plan')}/plan.md")
    for p in out["claim_check"]:
        print(f"  ⚠ {p}")
    print(f"Pregledaj i odobri: python -m kadar approve {run.slug} 03_plan")


def cmd_create(a: argparse.Namespace) -> None:
    from .phases.p04_izrada import run_create

    run = Run(a.run)
    if run.meta("03_plan").get("status") != "approved" and not a.force:
        raise SystemExit("03_plan nije odobren. Odobri ga ili dodaj --force.")
    out = run_create(run)
    for p in out["posts"]:
        print(f"✓ Objava {p['objava']} ({p['format']}): {len(p['slajdovi'])} slajdova")
    print(f"KADAR 04 · IZRADA gotova → {run.phase_dir('04_izrada')}")


def cmd_gallery(a: argparse.Namespace) -> None:
    from .render.gallery import build_gallery

    print(f"Galerija → {build_gallery(Run(a.run))}")


def cmd_app(a: argparse.Namespace) -> None:
    from .app.server import serve

    serve(port=a.port, open_browser=not a.no_browser)


def cmd_qa(a: argparse.Namespace) -> None:
    from .phases.p05_provjera import run_qa

    out = run_qa(Run(a.run), with_vision=not a.no_vision)
    s = out["summary"]
    print(f"KADAR 05 · PROVJERA: {out['total']} provjera — ✅ {s.get('pass', 0)} ⚠️ {s.get('warn', 0)} ❌ {s.get('fail', 0)}")
    print(f"Izvještaj → {Run(a.run).phase_dir('05_provjera')}/provjera.md")


def cmd_fix(a: argparse.Namespace) -> None:
    from .phases.p04_izrada import run_create
    from .phases.p05_provjera import apply_fixes
    from .render.gallery import build_gallery

    run = Run(a.run)
    r = apply_fixes(run)
    print(f"Primijenjeno {r['applied']}/{r['total']} ispravaka")
    for l in r["log"]:
        print(f"  {'✓' if l['applied'] is True else ('=' if l['applied'] else '✗')} [{l['source']}] {l['original'][:50]} → {l['suggestion'][:50]}")
    run_create(run)
    build_gallery(run)
    print("Slajdovi ponovno renderirani. Pokreni `qa` za novi krug provjere.")


def cmd_deliver(a: argparse.Namespace) -> None:
    from .phases.p06_isporuka import run_delivery

    out = run_delivery(Run(a.run))
    print(f"KADAR 06 · ISPORUKA → {out['folder']}/README.md ({len(out['files'])} datoteka)")


def cmd_approve(a: argparse.Namespace) -> None:
    run = Run(a.run)
    if run.output(a.phase) is None:
        raise SystemExit(f"{a.phase} još nema izlaz.")
    run.approve(a.phase, note=a.note)
    print(f"✓ {a.phase} odobren. Sljedeći kadar: {run.next_phase() or 'sve odobreno'}")


def cmd_status(a: argparse.Namespace) -> None:
    run = Run(a.run)
    info = run.info()
    print(f"{info['brand']}  ({run.dir})")
    for row in run.status_table():
        when = row.get("approved_at") or row.get("finished_at") or row.get("started_at") or ""
        print(f"  {row['phase']:<12} {row.get('status', 'pending'):<13} {when}")
    if a.debug:
        import sys
        from .config import settings
        print(f"[debug] python={sys.executable} root={settings.root}")
        for p in PHASES:
            m = run.phase_dir(p) / "meta.json"
            print(f"[debug] {m} exists={m.exists()}")
    nxt = run.next_phase()
    print(f"Sljedeći kadar: {nxt or 'sve odobreno'}")


def main(argv=None) -> None:
    for stream in (sys.stdout, sys.stderr):  # Windows konzola (cp1252) inače puca na ✓, ⚠, →
        try:
            stream.reconfigure(encoding="utf-8", errors="replace")
        except Exception:
            pass
    p = argparse.ArgumentParser(prog="kadar", description="Od brenda do objave, kadar po kadar.")
    sub = p.add_subparsers(dest="cmd", required=True)

    s = sub.add_parser("init", help="novi run za brend")
    s.add_argument("brand")
    s.add_argument("--instagram", default="")
    s.add_argument("--website", default="")
    s.set_defaults(func=cmd_init)

    s = sub.add_parser("scrape", help="dohvati činjenice i slike proizvoda")
    s.add_argument("run", help="slug runa, npr. gymbeam-hr")
    s.add_argument("urls", nargs="+")
    s.add_argument("--no-images", action="store_true")
    s.set_defaults(func=cmd_scrape)

    s = sub.add_parser("brief", help="KADAR 01: brif i ulazi (interaktivno ili --from datoteka)")
    s.add_argument("--from", dest="from_file", default="")
    s.set_defaults(func=cmd_brief)

    s = sub.add_parser("analyze", help="KADAR 02: analiza brenda")
    s.add_argument("run")
    s.add_argument("--dry-run", action="store_true", help="bez API poziva, samo provjera ulaza")
    s.add_argument("--force", action="store_true", help="pokreni i ako 01 nije odobren")
    s.set_defaults(func=cmd_analyze)

    s = sub.add_parser("plan", help="KADAR 03: plan triju objava")
    s.add_argument("run")
    s.add_argument("--force", action="store_true")
    s.set_defaults(func=cmd_plan)

    s = sub.add_parser("create", help="KADAR 04: završni tekstovi + render slajdova")
    s.add_argument("run")
    s.add_argument("--force", action="store_true")
    s.set_defaults(func=cmd_create)

    s = sub.add_parser("gallery", help="HTML galerija runa (faze + gotove objave)")
    s.add_argument("run")
    s.set_defaults(func=cmd_gallery)

    s = sub.add_parser("app", help="pokreni web aplikaciju (http://127.0.0.1:8770)")
    s.add_argument("--port", type=int, default=8770)
    s.add_argument("--no-browser", action="store_true")
    s.set_defaults(func=cmd_app)

    s = sub.add_parser("qa", help="KADAR 05: automatska provjera (kod + AI vizija)")
    s.add_argument("run")
    s.add_argument("--no-vision", action="store_true", help="samo provjere u kodu (bez AI poziva)")
    s.set_defaults(func=cmd_qa)

    s = sub.add_parser("fix", help="primijeni ispravke iz provjere i ponovno renderiraj")
    s.add_argument("run")
    s.set_defaults(func=cmd_fix)

    s = sub.add_parser("deliver", help="KADAR 06: paket za predaju u isporuka/<run>/")
    s.add_argument("run")
    s.set_defaults(func=cmd_deliver)

    s = sub.add_parser("approve", help="odobri kadar nakon ljudskog pregleda")
    s.add_argument("run")
    s.add_argument("phase", choices=PHASES)
    s.add_argument("--note", default="", help="što je pregledano / promijenjeno")
    s.set_defaults(func=cmd_approve)

    s = sub.add_parser("status", help=f"stanje faza ({', '.join(PHASES)})")
    s.add_argument("run")
    s.add_argument("--debug", action="store_true")
    s.set_defaults(func=cmd_status)

    a = p.parse_args(argv)
    a.func(a)


if __name__ == "__main__":
    main()
