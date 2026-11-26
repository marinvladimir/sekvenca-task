"""Stanje pokretanja: svaka faza (kadar) sprema svoj izlaz na disk.

runs/<brend>/
  run.json                 — brend, datum, postavke (bez ključeva)
  sources.json             — registar izvora (S1, S2, …) s URL-om i vremenom dohvata
  01_brif/output.json      — izlaz faze
  01_brif/meta.json        — status, vrijeme, model, trajanje
  ...

Ako se rad prekine, `next_phase()` vraća prvi kadar koji nije odobren,
pa se nastavlja od zadnjeg spremljenog stanja.
"""

from __future__ import annotations

import json
import re
import time
import unicodedata
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional

from .config import settings

PHASES: List[str] = [
    "01_brif",       # brifing i ulazi (brief, proizvodi, IG screenshotovi)
    "02_analiza",    # analiza brenda: ton, boje, publika; provjereno vs pretpostavka
    "03_plan",       # tri objave: cilj, format, koncept, obrazloženje
    "04_izrada",     # tekstovi + vizuali + render u PNG
    "05_provjera",   # QA: vjernost proizvoda, tvrdnje vs izvori, jezik, dimenzije
    "06_isporuka",   # pakiranje predaje
]

STATUSES = ("pending", "running", "needs_review", "approved", "failed")


def now_iso() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


def slugify(text: str) -> str:
    text = text.lower().strip().replace("đ", "d")
    text = unicodedata.normalize("NFKD", text).encode("ascii", "ignore").decode()
    return re.sub(r"[^a-z0-9]+", "-", text).strip("-")


def _read(path: Path, default: Any = None) -> Any:
    if not path.exists():
        return default
    return json.loads(path.read_text(encoding="utf-8"))


def _write(path: Path, data: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(path.suffix + ".tmp")
    tmp.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
    tmp.replace(path)  # atomarno: prekid usred pisanja ne kvari stanje


@dataclass
class Run:
    slug: str

    @property
    def dir(self) -> Path:
        return settings.runs_dir / self.slug

    # ---- run ---------------------------------------------------------------

    @classmethod
    def create(cls, brand: str, instagram: str = "", website: str = "") -> "Run":
        run = cls(slugify(brand))
        if (run.dir / "run.json").exists():
            return run
        _write(
            run.dir / "run.json",
            {
                "brand": brand,
                "instagram": instagram,
                "website": website,
                "created_at": now_iso(),
                "settings": settings.public(),
            },
        )
        _write(run.dir / "sources.json", [])
        return run

    def info(self) -> Dict[str, Any]:
        data = _read(self.dir / "run.json")
        if data is None:
            raise SystemExit(f"Ne postoji run '{self.slug}'. Pokreni `init` prvo.")
        return data

    # ---- faze --------------------------------------------------------------

    def phase_dir(self, phase: str) -> Path:
        if phase not in PHASES:
            raise ValueError(f"Nepoznata faza {phase}; dostupne: {PHASES}")
        return self.dir / phase

    def meta(self, phase: str) -> Dict[str, Any]:
        return _read(self.phase_dir(phase) / "meta.json", {"status": "pending"})

    def set_meta(self, phase: str, **fields: Any) -> Dict[str, Any]:
        meta = self.meta(phase)
        meta.update(fields)
        if "status" in fields and fields["status"] not in STATUSES:
            raise ValueError(fields["status"])
        _write(self.phase_dir(phase) / "meta.json", meta)
        return meta

    def output(self, phase: str) -> Any:
        return _read(self.phase_dir(phase) / "output.json")

    def save_output(self, phase: str, data: Any, status: str = "needs_review") -> None:
        _write(self.phase_dir(phase) / "output.json", data)
        self.set_meta(phase, status=status, finished_at=now_iso())

    def approve(self, phase: str, note: str = "") -> None:
        self.set_meta(phase, status="approved", approved_at=now_iso(), review_note=note)

    def next_phase(self) -> Optional[str]:
        for phase in PHASES:
            if self.meta(phase).get("status") != "approved":
                return phase
        return None

    def status_table(self) -> List[Dict[str, Any]]:
        return [{"phase": p, **self.meta(p)} for p in PHASES]

    # ---- izvori ------------------------------------------------------------

    def sources(self) -> List[Dict[str, Any]]:
        return _read(self.dir / "sources.json", [])

    def add_source(self, url: str, kind: str, title: str = "", note: str = "") -> str:
        """Registrira izvor i vraća njegov ID (S1, S2, …). Isti URL se ne duplicira."""
        sources = self.sources()
        for s in sources:
            if s["url"] == url:
                s["retrieved_at"] = now_iso()
                _write(self.dir / "sources.json", sources)
                return s["id"]
        sid = f"S{len(sources) + 1}"
        sources.append(
            {
                "id": sid,
                "url": url,
                "kind": kind,  # webshop | instagram | faq | other
                "title": title,
                "note": note,
                "retrieved_at": now_iso(),
            }
        )
        _write(self.dir / "sources.json", sources)
        return sid


class Timer:
    """Mjeri trajanje koraka (zapisuje se kao 'waiting' vrijeme u meta.json)."""

    def __enter__(self) -> "Timer":
        self.t0 = time.monotonic()
        return self

    def __exit__(self, *exc: Any) -> None:
        self.seconds = round(time.monotonic() - self.t0, 1)
