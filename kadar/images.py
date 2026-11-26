"""Priprema slika za model i mjerenje boja.

Paleta se računa kodom (kvantizacija piksela), ne procjenjuje je model,
pa su hex vrijednosti izmjerene, a ne izmišljene.
"""

from __future__ import annotations

import base64
import io
from collections import Counter
from pathlib import Path
from typing import Any, Dict, List

from PIL import Image

MAX_SIDE = 1568  # iznad toga API ionako smanjuje sliku


def load_rgb(path: Path) -> Image.Image:
    img = Image.open(path)
    if img.mode in ("RGBA", "LA", "P"):
        img = img.convert("RGBA")
        bg = Image.new("RGBA", img.size, (255, 255, 255, 255))
        img = Image.alpha_composite(bg, img)
    return img.convert("RGB")


def image_block(path: Path) -> Dict[str, Any]:
    img = load_rgb(path)
    img.thumbnail((MAX_SIDE, MAX_SIDE), Image.LANCZOS)
    buf = io.BytesIO()
    img.save(buf, format="JPEG", quality=88)
    return {
        "type": "image",
        "source": {
            "type": "base64",
            "media_type": "image/jpeg",
            "data": base64.standard_b64encode(buf.getvalue()).decode("ascii"),
        },
    }


def save_preview(path: Path, cache_dir: Path) -> Path:
    """Smanjena JPEG kopija (≤ MAX_SIDE) za model; originali ostaju netaknuti."""
    cache_dir.mkdir(parents=True, exist_ok=True)
    out = cache_dir / f"{path.parent.name}__{path.stem}.jpg"
    if not out.exists() or out.stat().st_mtime < path.stat().st_mtime:
        img = load_rgb(path)
        img.thumbnail((MAX_SIDE, MAX_SIDE), Image.LANCZOS)
        img.save(out, format="JPEG", quality=88)
    return out.resolve()


def _hex(rgb) -> str:
    return "#{:02X}{:02X}{:02X}".format(*rgb[:3])


def measure_palette(paths: List[Path], colors: int = 12, top: int = 10) -> List[Dict[str, Any]]:
    """Zajednička paleta za skup slika: hex + udio piksela.

    Gotovo bijele i gotovo crne boje se označe (pozadine i tekst), ali se ne
    izbacuju — i one su dio identiteta (npr. bijeli packshotovi).
    """
    counter: Counter = Counter()
    sums: Dict[tuple, List[int]] = {}
    for path in paths:
        img = load_rgb(path)
        img.thumbnail((256, 256))
        q = img.quantize(colors=colors, method=Image.MEDIANCUT)
        pal = q.getpalette()
        for count, idx in q.getcolors():
            rgb = tuple(pal[idx * 3 : idx * 3 + 3])
            # slične boje iz različitih slika grupiraju se u isti "spremnik",
            # a vraća se ponderirani prosjek stvarnih boja (ne zaokružena vrijednost)
            key = tuple(round(c / 24) for c in rgb)
            counter[key] += count
            acc = sums.setdefault(key, [0, 0, 0])
            for i in range(3):
                acc[i] += rgb[i] * count
    total = sum(counter.values()) or 1
    out = []
    for key, count in counter.most_common(top):
        rgb = tuple(round(s / count) for s in sums[key])
        lum = 0.2126 * rgb[0] + 0.7152 * rgb[1] + 0.0722 * rgb[2]
        out.append(
            {
                "hex": _hex(rgb),
                "share": round(count / total, 3),
                "kind": "svijetla/pozadina" if lum > 235 else "tamna/tekst" if lum < 30 else "boja",
            }
        )
    return out
