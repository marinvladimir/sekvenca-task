#!/usr/bin/env bash
# Kadar — instalacija svih preduvjeta (macOS / Linux; na Windowsu pokreni u WSL-u).
# Pokretanje:  ./setup.sh
set -euo pipefail
cd "$(dirname "$0")"

say()  { printf "\033[1;36m▸ %s\033[0m\n" "$*"; }
ok()   { printf "\033[1;32m✓ %s\033[0m\n" "$*"; }
warn() { printf "\033[1;33m! %s\033[0m\n" "$*"; }
die()  { printf "\033[1;31m✗ %s\033[0m\n" "$*"; exit 1; }

# 1) Python ≥ 3.9
say "Provjeravam Python…"
PY=""
for c in python3.13 python3.12 python3.11 python3.10 python3 python; do
  if command -v "$c" >/dev/null 2>&1 && "$c" -c 'import sys; sys.exit(0 if sys.version_info >= (3, 9) else 1)' 2>/dev/null; then
    PY="$c"; break
  fi
done
[ -n "$PY" ] || die "Treba Python 3.9 ili noviji (https://www.python.org/downloads/). Na macOS-u: xcode-select --install"
ok "Python: $($PY --version)"

# 2) virtualno okruženje + paketi
if [ ! -x .venv/bin/python ]; then
  say "Stvaram virtualno okruženje .venv…"
  "$PY" -m venv .venv
fi
say "Instaliram Python pakete…"
.venv/bin/python -m pip install --quiet --upgrade pip
.venv/bin/python -m pip install --quiet -r requirements.txt
ok "Paketi instalirani"

# 3) Chromium za render slajdova (Playwright)
say "Instaliram Chromium za render (jednom, ~150 MB)…"
.venv/bin/python -m playwright install chromium >/dev/null
ok "Chromium spreman"

# 4) .env iz predloška (bez ključeva)
if [ ! -f .env ]; then cp .env.example .env; ok "Napravljen .env iz .env.example"; fi

# 5) AI backend: Claude Code CLI (zadano) ili API ključ
BACKEND=$(grep -E '^KADAR_LLM_BACKEND=' .env | cut -d= -f2 || true)
BACKEND=${BACKEND:-claude-code}
if [ "$BACKEND" = "api" ]; then
  if grep -qE '^ANTHROPIC_API_KEY=.+' .env; then ok "Backend: Claude API (ključ u .env)"; else
    warn "Backend je 'api', ali ANTHROPIC_API_KEY u .env je prazan. Upiši ključ ili postavi KADAR_LLM_BACKEND=claude-code."; fi
else
  CLAUDE_BIN=$(command -v claude || true)
  [ -z "$CLAUDE_BIN" ] && [ -x "$HOME/.local/bin/claude" ] && CLAUDE_BIN="$HOME/.local/bin/claude"
  if [ -z "$CLAUDE_BIN" ]; then
    warn "Claude Code CLI nije pronađen."
    ans="n"
    [ -t 0 ] && read -r -p "  Instalirati ga službenim instalerom (curl -fsSL https://claude.ai/install.sh | bash)? [d/N] " ans
    if [[ "$ans" =~ ^[dDyY]$ ]]; then
      curl -fsSL https://claude.ai/install.sh | bash
      CLAUDE_BIN="$HOME/.local/bin/claude"
    else
      warn "Preskočeno. Alternativa: u .env postavi KADAR_LLM_BACKEND=api i ANTHROPIC_API_KEY."
    fi
  fi
  if [ -n "$CLAUDE_BIN" ] && [ -x "$CLAUDE_BIN" ]; then
    if "$CLAUDE_BIN" auth status 2>/dev/null | grep -q '"loggedIn": true'; then
      ok "Claude Code CLI prijavljen ($("$CLAUDE_BIN" --version))"
    else
      warn "Claude Code CLI nije prijavljen. Jedina ručna radnja:  $CLAUDE_BIN auth login"
    fi
  fi
fi

# 6) brza provjera
.venv/bin/python -m kadar --help >/dev/null && ok "Kadar je instaliran"
echo
echo "Pokretanje aplikacije:   ./run.sh        (otvara http://127.0.0.1:8770)"
echo "Naredbeni redak:         .venv/bin/python -m kadar --help"
