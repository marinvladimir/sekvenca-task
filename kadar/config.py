"""Postavke iz .env-a. Ključevi se nikad ne ispisuju ni ne spremaju u run direktorij."""

from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path

from dotenv import load_dotenv

ROOT = Path(__file__).resolve().parent.parent
load_dotenv(ROOT / ".env")


@dataclass(frozen=True)
class Settings:
    root: Path = ROOT
    runs_dir: Path = ROOT / "runs"
    prompts_dir: Path = ROOT / "prompts"
    inputs_dir: Path = ROOT / "inputs"
    text_model: str = os.getenv("KADAR_TEXT_MODEL", "claude-opus-5-5")
    user_agent: str = os.getenv(
        "KADAR_USER_AGENT", "Mozilla/5.0 (compatible; KadarRecipe/0.1)"
    )
    request_delay_s: float = float(os.getenv("KADAR_REQUEST_DELAY_S", "1.0"))

    def public(self) -> dict:
        """Postavke koje se smiju zapisati u meta.json (bez tajni)."""
        return {
            "text_model": self.text_model,
            "user_agent": self.user_agent,
            "request_delay_s": self.request_delay_s,
        }


settings = Settings()


def require_key(name: str) -> str:
    value = os.getenv(name, "").strip()
    if not value:
        raise SystemExit(
            f"Nedostaje {name}. Kopiraj .env.example u .env i upiši ključ."
        )
    return value
