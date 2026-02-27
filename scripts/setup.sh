#!/usr/bin/env bash
# scripts/setup.sh - One-command developer setup for ctrlmap
#
# Usage: ./scripts/setup.sh
#
# Installs all dependencies needed to develop and test ctrlmap:
#   1. Python dependencies via uv
#   2. Ollama (local LLM runtime)
#   3. llama3 model for rationale generation
set -euo pipefail

BOLD='\033[1m'
GREEN='\033[0;32m'
YELLOW='\033[0;33m'
RED='\033[0;31m'
NC='\033[0m'

info()  { echo -e "${BOLD}${GREEN}[+]${NC} $1"; }
warn()  { echo -e "${BOLD}${YELLOW}[!]${NC} $1"; }
error() { echo -e "${BOLD}${RED}[x]${NC} $1"; }

# ── Python dependencies ──────────────────────────────────────────────
info "Installing Python dependencies..."
if command -v uv &> /dev/null; then
    uv sync
    info "Python dependencies installed."
else
    error "uv is not installed. Install it: https://docs.astral.sh/uv/getting-started/installation/"
    exit 1
fi

# ── Ollama ────────────────────────────────────────────────────────────
info "Checking for Ollama..."
if command -v ollama &> /dev/null; then
    info "Ollama is already installed."
else
    warn "Ollama not found. Installing via Homebrew..."
    if command -v brew &> /dev/null; then
        brew install ollama
        info "Ollama installed."
    else
        error "Homebrew not found. Install Ollama manually: https://ollama.com/download"
        exit 1
    fi
fi

# ── Start Ollama service ─────────────────────────────────────────────
info "Starting Ollama service..."
if pgrep -x "ollama" > /dev/null 2>&1; then
    info "Ollama is already running."
else
    if command -v brew &> /dev/null; then
        brew services start ollama 2>/dev/null || ollama serve &
    else
        ollama serve &
    fi
    sleep 3
    info "Ollama service started."
fi

# ── Pull model ────────────────────────────────────────────────────────
MODEL="llama3"
info "Pulling $MODEL model (this may take a few minutes on first run)..."
if ollama list 2>/dev/null | grep -q "$MODEL"; then
    info "$MODEL model is already available."
else
    ollama pull "$MODEL"
    info "$MODEL model pulled."
fi

# ── Verify ────────────────────────────────────────────────────────────
echo ""
info "Setup complete. Verify with:"
echo "  uv run pytest tests/unit/ -q"
echo "  uv run pytest tests/evaluation/ -m eval -v"
echo ""
info "Quick start:"
echo "  ctrlmap parse -i policy.pdf -o chunks.jsonl"
echo "  ctrlmap index --chunks chunks.jsonl --framework nist_800_53.json"
echo "  ctrlmap map --db-path ctrlmap_db --framework nist_800_53.json"
