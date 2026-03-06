#!/usr/bin/env bash
# scripts/demo.sh - Run the full ctrlmap pipeline end-to-end
#
# Demonstrates:  parse → index → map (with LLM rationale) → harmonize
#
# Prerequisites:
#   - uv sync (Python deps installed)
#   - Ollama running with llama3 model pulled
#
# Usage:  ./scripts/demo.sh
set -euo pipefail

BOLD='\033[1m'
GREEN='\033[0;32m'
BLUE='\033[0;34m'
YELLOW='\033[0;33m'
CYAN='\033[0;36m'
DIM='\033[2m'
NC='\033[0m'

DEMO_DIR="$(cd "$(dirname "$0")/.." && pwd)"
OUTPUT_DIR="$DEMO_DIR/demo/output"
POLICIES_DIR="$DEMO_DIR/demo/policies"
FRAMEWORKS_DIR="$DEMO_DIR/demo/frameworks"

step()   { echo -e "\n${BOLD}${BLUE}━━━ $1 ━━━${NC}"; }
info()   { echo -e "${GREEN}[+]${NC} $1"; }
detail() { echo -e "${DIM}    $1${NC}"; }

elapsed() {
    local start=$1
    local end
    end=$(date +%s)
    echo "$((end - start))s"
}

# ── Preflight ────────────────────────────────────────────────────────
echo -e "${BOLD}${CYAN}"
echo "  ┌─────────────────────────────────────────────────────┐"
echo "  │           ctrlmap — End-to-End Demo                 │"
echo "  │   PDF Policy → Parse → Index → Map → Harmonize     │"
echo "  └─────────────────────────────────────────────────────┘"
echo -e "${NC}"

# Verify prerequisites
if ! command -v ollama &> /dev/null; then
    echo -e "${YELLOW}[!] Ollama not found. Run 'make setup' first.${NC}"
    exit 1
fi

if ! pgrep -x "ollama" > /dev/null 2>&1; then
    echo -e "${YELLOW}[!] Ollama not running. Starting...${NC}"
    ollama serve &
    sleep 3
fi

if ! ollama list 2>/dev/null | grep -q "llama3"; then
    echo -e "${YELLOW}[!] llama3 model not found. Pulling (this may take a few minutes)...${NC}"
    ollama pull llama3
fi

# Clean previous output
rm -rf "$OUTPUT_DIR"
mkdir -p "$OUTPUT_DIR"

DEMO_START=$(date +%s)

# ── Step 1: Parse PDFs ───────────────────────────────────────────────
step "Step 1/5: Parsing Policy PDFs"
T=$(date +%s)

for pdf in "$POLICIES_DIR"/*.pdf; do
    name=$(basename "$pdf" .pdf)
    info "Parsing: $(basename "$pdf")"
    uv run ctrlmap parse \
        --input "$pdf" \
        --output "$OUTPUT_DIR/${name}_chunks.jsonl"
done

# Merge all chunks into a single file for indexing
cat "$OUTPUT_DIR"/*_chunks.jsonl > "$OUTPUT_DIR/all_chunks.jsonl"
TOTAL_CHUNKS=$(wc -l < "$OUTPUT_DIR/all_chunks.jsonl" | tr -d ' ')
info "Merged: $TOTAL_CHUNKS total chunks ($(elapsed $T))"

# ── Step 2: Index with NIST 800-53 ──────────────────────────────────
step "Step 2/5: Indexing with NIST 800-53 Framework"
T=$(date +%s)

uv run ctrlmap index \
    --chunks "$OUTPUT_DIR/all_chunks.jsonl" \
    --framework "$FRAMEWORKS_DIR/nist_800_53_subset.json" \
    --db-path "$OUTPUT_DIR/demo_db"

info "NIST 800-53 indexed ($(elapsed $T))"

# ── Step 3: Index with PCI DSS ──────────────────────────────────────
step "Step 3/5: Indexing with PCI DSS v4.0.1 Framework"
T=$(date +%s)

uv run ctrlmap index \
    --chunks "$OUTPUT_DIR/all_chunks.jsonl" \
    --framework "$FRAMEWORKS_DIR/pci_dss_v4_oscal.json" \
    --db-path "$OUTPUT_DIR/demo_db"

info "PCI DSS v4.0.1 indexed ($(elapsed $T))"

# ── Step 4: Map controls ────────────────────────────────────────────
step "Step 4/5: Mapping Controls (with LLM Rationale)"

T=$(date +%s)
info "Mapping against NIST 800-53..."
uv run ctrlmap map \
    --framework "$FRAMEWORKS_DIR/nist_800_53_subset.json" \
    --db-path "$OUTPUT_DIR/demo_db" \
    --rationale \
    --output-format markdown \
    --output "$OUTPUT_DIR/nist_mapping.md"
info "NIST mapping complete"

info "Mapping against PCI DSS v4.0.1..."
uv run ctrlmap map \
    --framework "$FRAMEWORKS_DIR/pci_dss_v4_oscal.json" \
    --db-path "$OUTPUT_DIR/demo_db" \
    --rationale \
    --output-format markdown \
    --output "$OUTPUT_DIR/pci_mapping.md"
info "PCI DSS mapping complete ($(elapsed $T))"

# Also export as JSON for programmatic consumption
uv run ctrlmap map \
    --framework "$FRAMEWORKS_DIR/pci_dss_v4_oscal.json" \
    --db-path "$OUTPUT_DIR/demo_db" \
    --output-format json \
    --output "$OUTPUT_DIR/pci_mapping.json"

# Generate interactive HTML reports
info "Generating interactive HTML reports..."
uv run ctrlmap map \
    --framework "$FRAMEWORKS_DIR/nist_800_53_subset.json" \
    --db-path "$OUTPUT_DIR/demo_db" \
    --rationale \
    --output-format html \
    --output "$OUTPUT_DIR/nist_report.html"

uv run ctrlmap map \
    --framework "$FRAMEWORKS_DIR/pci_dss_v4_oscal.json" \
    --db-path "$OUTPUT_DIR/demo_db" \
    --rationale \
    --output-format html \
    --output "$OUTPUT_DIR/pci_report.html"

info "HTML reports generated"

# ── Step 5: Harmonize ───────────────────────────────────────────────
step "Step 5/5: Harmonizing Controls Across Frameworks"
T=$(date +%s)

uv run ctrlmap harmonize \
    --inputs "$FRAMEWORKS_DIR" \
    1> "$OUTPUT_DIR/harmonized_controls.json"

COMMON=$(python3 -c "import json; d=json.load(open('$OUTPUT_DIR/harmonized_controls.json')); print(len(d))")
info "Harmonized into $COMMON common controls ($(elapsed $T))"

# ── Summary ──────────────────────────────────────────────────────────
echo ""
echo -e "${BOLD}${GREEN}━━━ Demo Complete ━━━${NC}"
echo ""
echo -e "  Total time: ${BOLD}$(elapsed $DEMO_START)${NC}"
echo ""
echo -e "  ${CYAN}Output files:${NC}"
echo -e "    demo/output/all_chunks.jsonl          ${DIM}— merged parsed chunks${NC}"
echo -e "    demo/output/demo_db/                  ${DIM}— ChromaDB vector store${NC}"
echo -e "    demo/output/nist_mapping.md           ${DIM}— NIST 800-53 mappings (markdown)${NC}"
echo -e "    demo/output/pci_mapping.md            ${DIM}— PCI DSS v4.0.1 mappings (markdown)${NC}"
echo -e "    demo/output/pci_mapping.json          ${DIM}— PCI DSS mappings (JSON)${NC}"
echo -e "    demo/output/harmonized_controls.json  ${DIM}— deduplicated common controls${NC}"
echo -e ""
echo -e "  ${CYAN}★ Interactive HTML Reports:${NC}"
echo -e "    demo/output/nist_report.html          ${DIM}— NIST 800-53 (open in browser)${NC}"
echo -e "    demo/output/pci_report.html           ${DIM}— PCI DSS v4.0.1 (open in browser)${NC}"
echo ""
echo -e "  ${CYAN}Quick peek:${NC}"
echo -e "    open demo/output/pci_report.html"
echo ""
