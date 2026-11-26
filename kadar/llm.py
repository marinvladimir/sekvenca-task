"""Sloj za pozive modela, s dva interchangeable backenda.

KADAR_LLM_BACKEND=claude-code  (zadano)
    Poziva Claude Code CLI u neinteraktivnom načinu (`claude -p`). Koristi
    prijavu iz `claude auth login`, dakle postojeću Claude pretplatu, bez
    API ključa i bez dodatnog plaćanja. Strukturirani izlaz validira CLI
    (`--json-schema`), a slike model čita alatom Read (jedini dopušteni alat).

KADAR_LLM_BACKEND=api
    Izravno Claude API (anthropic SDK). Treba ANTHROPIC_API_KEY. Koristi
    structured outputs (`messages.parse`) i server-side fallback ako
    sigurnosni klasifikator odbije zahtjev.

Oba backenda primaju iste promptove (prompts/*.md) i istu Pydantic shemu,
pa je izlaz istog oblika. Svaki poziv se zapisuje u calls.jsonl faze
(model, tokeni, trajanje), da se vrijeme čekanja može odvojiti od rada.
"""

from __future__ import annotations

import json
import os
import shutil
import subprocess
import time
from pathlib import Path
from typing import Any, Dict, List, Optional, Type, TypeVar

from pydantic import BaseModel

from .config import settings
from .images import image_block, save_preview
from .state import now_iso

T = TypeVar("T", bound=BaseModel)

BACKEND = os.getenv("KADAR_LLM_BACKEND", "claude-code")
FALLBACK_BETA = "server-side-fallback-2026-07-01"


class RefusedError(RuntimeError):
    pass


def load_prompt(name: str, **vars: Any) -> str:
    """Učita prompt iz prompts/<name>.md i zamijeni {{varijable}}."""
    text = (settings.prompts_dir / f"{name}.md").read_text(encoding="utf-8")
    for key, value in vars.items():
        if not isinstance(value, str):
            value = json.dumps(value, ensure_ascii=False, indent=2)
        text = text.replace("{{" + key + "}}", value)
    return text


def _log(log_path: Optional[Path], entry: Dict[str, Any]) -> None:
    if log_path is None:
        return
    log_path.parent.mkdir(parents=True, exist_ok=True)
    with log_path.open("a", encoding="utf-8") as f:
        f.write(json.dumps({"at": now_iso(), **entry}, ensure_ascii=False) + "\n")


def ask_structured(
    *,
    schema: Type[T],
    system: str,
    text: str,
    images: Optional[List[Path]] = None,
    image_labels: Optional[List[str]] = None,
    effort: str = "high",
    log_path: Optional[Path] = None,
    label: str = "",
) -> T:
    images = images or []
    labels = image_labels or [p.name for p in images]
    if BACKEND == "api":
        return _ask_api(schema, system, text, images, labels, effort, log_path, label)
    return _ask_claude_code(schema, system, text, images, labels, effort, log_path, label)


# ---- backend: Claude Code CLI ---------------------------------------------------

def _claude_bin() -> str:
    found = os.getenv("KADAR_CLAUDE_BIN") or shutil.which("claude")
    if not found:
        candidate = Path.home() / ".local/bin/claude"
        found = str(candidate) if candidate.exists() else None
    if not found:
        raise SystemExit(
            "Claude Code CLI nije pronađen. Instaliraj ga (curl -fsSL https://claude.ai/install.sh | bash) "
            "i prijavi se (claude auth login), ili postavi KADAR_LLM_BACKEND=api."
        )
    return found


def _ask_claude_code(schema, system, text, images, labels, effort, log_path, label):
    # Slike se smanje na ≤1568 px JPEG u cache, da model ne čita 4 MB PNG-ove.
    cache = (log_path.parent if log_path else settings.runs_dir) / ".img_cache"
    previews = [save_preview(p, cache) for p in images]
    if previews:
        listing = "\n".join(f"- [SLIKA {lab}] {pv}" for lab, pv in zip(labels, previews))
        text = (
            "Prije odgovora pročitaj alatom Read SVAKU od ovih slika (redom). "
            "Oznaka u uglatim zagradama je ime kojim se na sliku pozivaš u odgovoru.\n"
            f"{listing}\n\n{text}"
        )

    cmd = [
        _claude_bin(), "-p", text,
        "--output-format", "json",
        "--json-schema", json.dumps(schema.model_json_schema(), ensure_ascii=False),
        "--model", settings.text_model,
        "--system-prompt", system,
        "--tools", "Read" if previews else "",
        "--allowedTools", "Read",
        "--strict-mcp-config",
        "--disable-slash-commands",
        "--no-session-persistence",
        "--effort", effort,
        "--max-turns", str(len(previews) + 4),
    ]
    t0 = time.monotonic()
    proc = subprocess.run(cmd, capture_output=True, text=True, cwd=str(settings.root), timeout=1800)
    seconds = round(time.monotonic() - t0, 1)
    try:
        data = json.loads(proc.stdout)
    except json.JSONDecodeError:
        raise RuntimeError(f"{label}: CLI nije vratio JSON (kod {proc.returncode}): {proc.stderr[-800:]}")

    usage = data.get("usage", {})
    _log(log_path, {
        "label": label, "backend": "claude-code", "model": settings.text_model, "effort": effort,
        "images": len(previews), "turns": data.get("num_turns"),
        "input_tokens": usage.get("input_tokens", 0) + usage.get("cache_creation_input_tokens", 0)
        + usage.get("cache_read_input_tokens", 0),
        "output_tokens": usage.get("output_tokens"), "seconds": seconds,
        "notional_cost_usd": data.get("total_cost_usd"), "subtype": data.get("subtype"),
    })
    if data.get("is_error") or data.get("structured_output") is None:
        raise RuntimeError(f"{label}: {data.get('subtype')} — {str(data.get('result'))[:800]}")
    return schema.model_validate(data["structured_output"])


# ---- backend: Claude API ----------------------------------------------------------

def _ask_api(schema, system, text, images, labels, effort, log_path, label):
    import anthropic

    content: List[Dict[str, Any]] = []
    for lab, path in zip(labels, images):
        content.append({"type": "text", "text": f"[SLIKA {lab}]"})
        content.append(image_block(path))
    content.append({"type": "text", "text": text})

    client = anthropic.Anthropic(max_retries=4, timeout=600)
    t0 = time.monotonic()
    response = client.beta.messages.parse(
        model=settings.text_model,
        max_tokens=32000,
        betas=[FALLBACK_BETA],
        fallbacks="default",
        system=system,
        output_config={"effort": effort},
        output_format=schema,
        messages=[{"role": "user", "content": content}],
    )
    _log(log_path, {
        "label": label, "backend": "api", "model": response.model, "effort": effort,
        "images": len(images), "input_tokens": response.usage.input_tokens,
        "output_tokens": response.usage.output_tokens, "seconds": round(time.monotonic() - t0, 1),
        "stop_reason": response.stop_reason, "request_id": getattr(response, "_request_id", None),
    })
    if response.stop_reason == "refusal":
        raise RefusedError(f"{label}: model je odbio zahtjev ({getattr(response, 'stop_details', None)})")
    if response.stop_reason == "max_tokens":
        raise RuntimeError(f"{label}: izlaz je odrezan")
    if response.parsed_output is None:
        raise RuntimeError(f"{label}: odgovor nije prošao shemu")
    return response.parsed_output
