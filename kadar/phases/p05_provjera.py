"""KADAR 05 · PROVJERA

Ulaz:   04_izrada (slajdovi, opisi, render.json mjerenja), plan, analiza
        (dopuštene tvrdnje, reference proizvoda), izvori.
Radi:   (A) automatske provjere u kodu — dimenzije, preljev teksta, sigurna
            zona storyja, logo/packshot učitani, broj slajdova, duljina opisa,
            emoji i hashtagovi, zabranjene riječi, obraćanje "ti", brojke
            prisutne u izvoru, obavezna upozorenja, zaostale oznake;
        (B) AI provjera s vizijom po objavi — proizvod vs referenca, logo,
            čitljivost, hijerarhija, jezik, prirodnost, ton, identitet,
            tvrdnje, CTA — uz konkretne jezične ispravke.
Izlaz:  05_provjera/output.json + provjera.md (tablica svih rezultata + sažetak).
"""

from __future__ import annotations

import json
import re
from collections import Counter
from pathlib import Path
from typing import Any, Dict, List

from ..llm import ask_structured, load_prompt
from ..schemas import VisionReview
from ..state import Run, now_iso

PHASE = "05_provjera"

FORBIDDEN = [
    r"\bnajbolj\w*", r"\bbr\.?\s*1\b", r"#1\b", r"\bjača\w*\s+imunitet", r"\bliječi\w*", r"\bsprječava\w*",
    r"\bgarantira\w*", r"\bzajamčen\w*", r"\bbez šećera\b", r"\bbez dodanog šećera\b", r"\bčudesn\w*",
    r"\b100\s?% prirodn\w*", r"\btopi masti\b", r"\bbrže gradi\b", r"\bdetoks\w*", r"€", r"\bEUR\b",
    r"\bpopust\w*", r"\bkod\s+[A-Z0-9]{3,}\b", r"\bakcij\w*",
]
VI_FORMS = r"\b(Vi|Vas|Vam|Vama|Vaš\w*|vaš\w*)\b"
VI_IMPERATIVE = r"\b(Listajte|Pošaljite|Spremite|Napišite|Pogledajte|Uzmite|Probajte|Kliknite|Glasajte|Pronađite|Otkrijte|Uvedite|Pripremite|Javite|Recite|Odaberite|Izaberite)\b"
EMOJI = re.compile("[\U0001F300-\U0001FAFF☀-➿]")
STORY_SAFE_TOP, STORY_SAFE_BOTTOM = 250, 1920 - 340


def _norm_num(x: str) -> str:
    return x.replace(",", ".").replace(" ", "")


def _numbers(text: str) -> List[str]:
    """Brojke vrijedne provjere: decimalne, ≥ 11 ili s mjernom jedinicom."""
    out = []
    for m in re.finditer(r"(\d+(?:[.,]\d+)?)\s*(g|mg|μg|µg|ml|kcal|kJ|IU|%|kapsul\w*)?", text):
        num, unit = m.group(1), m.group(2)
        if unit or "," in num or "." in num or float(num.replace(",", ".")) >= 11:
            out.append(_norm_num(num))
    return out


def _r(results: List[Dict[str, Any]], post: int, slide: int, group: str, check: str, status: str, detail: str = "") -> None:
    results.append({"post": post, "slide": slide, "group": group, "check": check, "status": status, "detail": detail})


def code_checks(run: Run) -> List[Dict[str, Any]]:
    create, plan, analysis = run.output("04_izrada"), run.output("03_plan")["plan"], run.output("02_analiza")
    res: List[Dict[str, Any]] = []
    source_text = ""
    for rel in analysis["product_files"]:
        source_text += json.dumps(json.loads((run.dir / rel).read_text(encoding="utf-8")), ensure_ascii=False)
    source_nums = {_norm_num(n) for n in re.findall(r"\d+(?:[.,]\d+)?", source_text)}
    usable = {Path(i["file"]).name for pi in analysis["product_images"].values() for i in pi["images"] if i["usable_as_reference"]}

    for post, planned in zip(create["posts"], plan["posts"]):
        n = post["objava"]
        out_dir = run.phase_dir("04_izrada") / f"objava_{n}"
        metrics = json.loads((out_dir / "render.json").read_text(encoding="utf-8"))
        story = post["format"] == "story_niz"
        W, H = (1080, 1920) if story else (1080, 1350)

        # ---- po slajdu
        for m in metrics:
            from PIL import Image
            size = Image.open(out_dir / m["png"]).size
            _r(res, n, m["slide"], "slajd", "Dimenzije", "pass" if size == (W, H) else "fail", f"{size[0]}×{size[1]} (očekivano {W}×{H})")
            ov = m.get("overflow_v") or m.get("overflow_h")
            _r(res, n, m["slide"], "slajd", "Tekst stane (bez preljeva)", "fail" if ov else "pass",
               f"naslov {m.get('headline_px')} px" + (" · preljev!" if ov else ""))
            hp = m.get("headline_px") or 0
            _r(res, n, m["slide"], "slajd", "Čitljiva veličina naslova (≥ 56 px)", "pass" if hp >= 56 or not hp else "warn", f"{hp} px")
            assets_ok = m.get("logo_ok") and m.get("product_ok") is not False
            _r(res, n, m["slide"], "slajd", "Logo i packshot učitani", "pass" if assets_ok else "fail",
               f"logo={m.get('logo_ok')} packshot={m.get('product_ok')}")
            if story:
                ok = (m.get("text_top") or 999) >= STORY_SAFE_TOP and (m.get("text_bottom") or 0) <= STORY_SAFE_BOTTOM
                _r(res, n, m["slide"], "slajd", "Sigurna zona storyja (250 px gore, 340 px dolje)", "pass" if ok else "warn",
                   f"tekst od {m.get('text_top')} do {m.get('text_bottom')} px")

        # ---- po objavi
        texts = " ".join(" ".join([s["kicker"], s["headline"], s["body"], s["stat"], " ".join(s["options"]), s.get("footnote", "")])
                         for s in post["tekst_slajdova"])
        layouts = [ps["layout"] for ps in planned["slides"]]
        # činjenične brojke: bez kickera (npr. "WHEY 101") i bez opcija kviza (namjerno netočni ometači)
        fact_text = " ".join(" ".join([s["headline"], s["body"], s["stat"], s.get("footnote", "")]
                                      + ([] if lay == "story_kviz" else s["options"]))
                             for s, lay in zip(post["tekst_slajdova"], layouts))
        # oznake: naslovi smiju imati *naglasak* (prikazuje se narančasto), ostala polja ne
        plain_text = " ".join(" ".join([s["kicker"], s["body"], " ".join(s["options"]), s.get("footnote", "")])
                              for s in post["tekst_slajdova"])
        caption = post["opis"]
        allt = texts + " " + caption
        _r(res, n, 0, "objava", "Broj slajdova = plan", "pass" if len(post["slajdovi"]) == len(planned["slides"]) else "fail",
           f"{len(post['slajdovi'])} / plan {len(planned['slides'])}")
        _r(res, n, 0, "objava", "Format odgovara planu", "pass" if post["format"] == planned["format"] else "fail", post["format"])
        clen = len(caption)
        _r(res, n, 0, "opis", "Duljina opisa (40–2200 znakova)", "pass" if 40 <= clen <= 2200 else "warn", f"{clen} znakova")
        emo = len(EMOJI.findall(caption))
        _r(res, n, 0, "opis", "Najviše 3 emojija u opisu", "pass" if emo <= 3 else "warn", f"{emo} emojija")
        tags = re.findall(r"#\w+", caption)
        tag_ok = 2 <= len(tags) <= 6 and "#gymbeamhr" in [t.lower() for t in tags]
        _r(res, n, 0, "opis", "Hashtagovi (2–6, uključuje #gymbeamhr)", "pass" if tag_ok or story else "warn",
           " ".join(tags) or "—")
        hits = [m.group(0) for p in FORBIDDEN for m in re.finditer(p, allt, re.I)]
        _r(res, n, 0, "usklađenost", "Bez zabranjenih tvrdnji, cijena i kodova", "fail" if hits else "pass", ", ".join(hits) or "nema")
        vi = re.findall(VI_FORMS, allt) + re.findall(VI_IMPERATIVE, allt)
        _r(res, n, 0, "jezik", "Dosljedno obraćanje „ti”", "warn" if vi else "pass", ", ".join(vi) or "nema oblika s „vi”")
        missing = sorted({x for x in _numbers(fact_text) if x not in source_nums})
        _r(res, n, 0, "usklađenost", "Sve brojke na slajdovima postoje u izvoru", "fail" if missing else "pass",
           ("nema u izvoru: " + ", ".join(missing)) if missing else f"{len(_numbers(fact_text))} brojki provjereno")
        leftovers = re.findall(r"\*\w|\bListaj\b\s*→|\{\{|\}\}", plain_text + " " + caption)
        _r(res, n, 0, "jezik", "Bez zaostalih oznaka (*, {{ }}, dupli „Listaj”)", "fail" if leftovers else "pass", ", ".join(leftovers) or "čisto")
        prod = planned["product"].lower()
        need = []
        if "d3" in prod or "vitamin" in prod:
            need = [("djec", "nije za djecu"), ("prekorač", "ne prekoračiti dozu")]
        elif "pločica" in prod or "moimüv" in prod:
            need = [("zaslađivač", "sadrži zaslađivače")]
        elif "whey" in prod:
            need = [("laktoz", "nije bez laktoze")]
        lack = [label for key, label in need if key not in allt.lower()]
        _r(res, n, 0, "usklađenost", "Obavezna upozorenja prisutna", "fail" if lack else "pass", ", ".join(lack) or ", ".join(l for _, l in need))
        _r(res, n, 0, "proizvod", "Packshot je odobrena referenca (bez promo kompozicija)", "pass" if usable else "fail",
           f"{len(usable)} odobrenih referenci u analizi")
        dup = [w for w, c in Counter(re.findall(r"\b\w{5,}\b", texts.lower())).items() if c >= 5]
        _r(res, n, 0, "jezik", "Bez pretjeranog ponavljanja riječi", "warn" if dup else "pass", ", ".join(dup) or "ok")
    return res


def _decisions(run: Run) -> str:
    from ..config import settings
    from ..render.renderer import brand_config
    notes = settings.inputs_dir / f"plan_notes_{run.slug}.md"
    cfg = brand_config(run.dir)
    return (f"Boje: {cfg['colors']} (odluka čovjeka). Obraćanje: {cfg.get('address', 'ti')}.\n"
            + (notes.read_text(encoding="utf-8") if notes.exists() else "")
            + "\nAnkete, kvizovi i poveznice u storyju su grafički prikaz; pri objavi se preko njih postavljaju "
              "nativni Instagram stikeri (Poll, Quiz, Link) — to nije greška grafike.")


def vision_checks(run: Run) -> List[Dict[str, Any]]:
    create, analysis, plan = run.output("04_izrada"), run.output("02_analiza"), run.output("03_plan")["plan"]
    out = []
    log = run.phase_dir(PHASE) / "calls.jsonl"
    cache_dir = run.phase_dir(PHASE) / "steps"
    cache_dir.mkdir(parents=True, exist_ok=True)
    for post, planned in zip(create["posts"], plan["posts"]):
        n = post["objava"]
        cache = cache_dir / f"vision_{n}.json"
        if cache.exists():
            out.append(json.loads(cache.read_text(encoding="utf-8")))
            continue
        product = next((k for k in analysis["product_images"] if planned["product"].lower()[:12] in k.lower()), None)
        ref = run.dir / analysis["product_images"][product]["best_reference_path"] if product else None
        slides = [run.dir / s for s in post["slajdovi"]]
        claims = [c["text"] for c in analysis["claims"].get(product, {}).get("claims", []) if c["safe_for_post"]] if product else []
        texts = [{"slajd": i + 1, **s} for i, s in enumerate(post["tekst_slajdova"])]
        review = ask_structured(
            schema=VisionReview,
            system=load_prompt("05_provjera_system"),
            text=load_prompt("05_provjera_user", number=str(n), title=post["naslov"], goal=post["cilj"], format=post["format"],
                             slides=texts, caption=post["opis"], claims=claims, voice=analysis["brand"]["voice"],
                             decisions=_decisions(run)),
            images=([ref] if ref else []) + slides,
            image_labels=(["REFERENCA"] if ref else []) + [f"S{i + 1}" for i in range(len(slides))],
            effort="medium",
            log_path=log,
            label=f"provjera:{n}",
        ).model_dump()
        review["post"] = n
        cache.write_text(json.dumps(review, ensure_ascii=False, indent=2), encoding="utf-8")
        out.append(review)
    return out


LABELS = {"proizvod_tocan": "Proizvod odgovara referenci", "logo_tocan": "Logo točan", "citljivost": "Čitljivost",
          "hijerarhija": "Hijerarhija poruke", "jezik_pravopis": "Pravopis i gramatika", "prirodnost_hr": "Prirodan hrvatski, „ti”",
          "ton_brenda": "Ton brenda", "vizualni_identitet": "Vizualni identitet", "tvrdnje_dopustene": "Samo dopuštene tvrdnje",
          "cta_jasan": "Jasan poziv na akciju"}


def run_qa(run: Run, with_vision: bool = True) -> Dict[str, Any]:
    if not run.output("04_izrada"):
        raise SystemExit("Nema izlaza kadra 04.")
    run.set_meta(PHASE, status="running", started_at=now_iso())
    results = code_checks(run)
    reviews = vision_checks(run) if with_vision else []
    fixes = []
    for rv in reviews:
        for f in rv["findings"]:
            _r(results, rv["post"], f["slide"], "AI vizija", LABELS.get(f["check"], f["check"]), f["status"], f["detail"])
        fixes += [{"post": rv["post"], **x} for x in rv["language_fixes"]]
    count = Counter(r["status"] for r in results)
    output = {"results": results, "summary": dict(count), "total": len(results), "language_fixes": fixes,
              "overall": {rv["post"]: rv["overall"] for rv in reviews}}
    run.save_output(PHASE, output)
    (run.phase_dir(PHASE) / "provjera.md").write_text(render_markdown(output), encoding="utf-8")
    return output


ICON = {"pass": "✅", "warn": "⚠️", "fail": "❌"}


def render_markdown(o: Dict[str, Any]) -> str:
    s = o["summary"]
    L = ["# Provjera kvalitete", "",
         f"**{o['total']} provjera:** ✅ {s.get('pass', 0)} prolazi · ⚠️ {s.get('warn', 0)} upozorenja · ❌ {s.get('fail', 0)} grešaka", ""]
    bad = [r for r in o["results"] if r["status"] != "pass"]
    if bad:
        L += ["## Što treba pogledati", "", "| Objava | Slajd | Provjera | Status | Detalj |", "|---|---|---|---|---|"]
        for r in sorted(bad, key=lambda r: (r["status"] != "fail", r["post"], r["slide"])):
            L.append(f"| {r['post']} | {r['slide'] or '—'} | {r['check']} | {ICON[r['status']]} | {r['detail']} |")
        L.append("")
    if o["language_fixes"]:
        L += ["## Jezične ispravke (prijedlog AI lektora)", "", "| Objava | Slajd | Izvorno | Prijedlog | Zašto |", "|---|---|---|---|---|"]
        for f in o["language_fixes"]:
            L.append(f"| {f['post']} | {f['slide'] or 'opis'} | {f['original']} | {f['suggestion']} | {f['reason']} |")
        L.append("")
    if o["overall"]:
        L += ["## Ukupna ocjena po objavi", ""] + [f"- **Objava {k}:** {v}" for k, v in o["overall"].items()] + [""]
    L += ["## Svi rezultati", ""]
    by_group = Counter((r["group"], r["status"]) for r in o["results"])
    groups = sorted({r["group"] for r in o["results"]})
    L += ["| Skupina | ✅ | ⚠️ | ❌ |", "|---|---|---|---|"] + [
        f"| {g} | {by_group[(g, 'pass')]} | {by_group[(g, 'warn')]} | {by_group[(g, 'fail')]} |" for g in groups] + [""]
    L += ["| Objava | Slajd | Skupina | Provjera | Status | Detalj |", "|---|---|---|---|---|---|"]
    for r in o["results"]:
        L.append(f"| {r['post']} | {r['slide'] or '—'} | {r['group']} | {r['check']} | {ICON[r['status']]} | {r['detail']} |")
    L += ["", "## Ljudska provjera (checklist, ~10 min)", "",
          "1. Otvori sve slajdove na **mobitelu** (pošalji si ih ili otvori galeriju) i listaj kao na Instagramu.",
          "2. Za svaki slajd: čitaš li naslov u 1 sekundi s udaljenosti ruke?",
          "3. Proizvod: je li pakiranje isto kao na webshopu (okus, boja, natpis)? Nema poklona ni promo oznaka?",
          "4. Tekst naglas: zvuči li kao da ga je napisao GymBeam, a ne prijevod? Ima li tipfelera?",
          "5. Brojke: usporedi 2–3 brojke sa stranicom proizvoda (poveznica u izvorima).",
          "6. Upozorenja: vidljiva su (laktoza / zaslađivači / djeca i trudnice)?",
          "7. Usporedi naslovnicu s pravim GymBeam profilom: bi li se uklopila u feed?",
          "8. Story: je li tekst izvan gornjeg i donjeg ruba gdje Instagram stavlja svoje elemente?",
          "9. Opis: poziv na akciju je jasan, hashtagovi na kraju, bez cijena i kodova?",
          "10. Što bi promijenio? Zapiši i ispravi prije odobravanja kadra 05."]
    return "\n".join(L) + "\n"


# ---- petlja dorade: primjena ispravaka iz provjere -----------------------------

def apply_fixes(run: Run) -> Dict[str, Any]:
    """Primijeni jezične ispravke iz provjere (+ ručne iz inputs/fixes_<run>.json) na tekstove
    kadra 04, doslovnom zamjenom. Nakon toga treba ponovno renderirati (kadar 04) i provjeriti."""
    from ..config import settings

    qa = run.output(PHASE) or {}
    fixes = [dict(f, source="AI lektor") for f in qa.get("language_fixes", [])]
    manual = settings.inputs_dir / f"fixes_{run.slug}.json"
    if manual.exists():
        fixes += [dict(f, source="čovjek") for f in json.loads(manual.read_text(encoding="utf-8")) if f.get("phase") != "03_plan"]
    copy_path = run.phase_dir("04_izrada") / "copy.json"
    copy = json.loads(copy_path.read_text(encoding="utf-8"))
    log = []
    for f in fixes:
        post = next((p for p in copy["posts"] if p["number"] == f["post"]), None)
        hit = False
        if post:
            if f["original"] in post["caption"]:
                post["caption"] = post["caption"].replace(f["original"], f["suggestion"]); hit = True
            for sl in post["slides"]:
                for key in ("kicker", "headline", "body", "footnote"):
                    if f["original"] in sl.get(key, ""):
                        sl[key] = sl[key].replace(f["original"], f["suggestion"]); hit = True
                sl["options"] = [o.replace(f["original"], f["suggestion"]) for o in sl["options"]]
        if not hit and post and f["original"] not in json.dumps(post, ensure_ascii=False):
            hit = "već primijenjeno"
        log.append({**f, "applied": hit})
    copy_path.write_text(json.dumps(copy, ensure_ascii=False, indent=2), encoding="utf-8")
    (run.phase_dir(PHASE) / "fixes_applied.json").write_text(json.dumps(log, ensure_ascii=False, indent=2), encoding="utf-8")
    # nova provjera s vizijom mora vidjeti nove slajdove
    for c in (run.phase_dir(PHASE) / "steps").glob("vision_*.json"):
        c.unlink()
    return {"applied": sum(1 for l in log if l["applied"]), "total": len(log), "log": log}
