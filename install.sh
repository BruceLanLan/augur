#!/usr/bin/env bash
# Augur Next — One-line installer
# Usage: curl -fsSL https://raw.githubusercontent.com/BruceLanLan/augur-next/main/install.sh | bash

set -e

REPO="https://github.com/BruceLanLan/augur-next.git"
INSTALL_DIR="${AUGUR_DIR:-$HOME/augur-next}"
PYTHON="${PYTHON:-python3}"
MIN_PYTHON="3.8"

# ── Colors ──────────────────────────────────────────────────────────────────
RED='\033[0;31m'; GREEN='\033[0;32m'; YELLOW='\033[1;33m'
CYAN='\033[0;36m'; BOLD='\033[1m'; NC='\033[0m'

info()    { echo -e "${CYAN}[augur]${NC} $1"; }
success() { echo -e "${GREEN}[augur]${NC} $1"; }
warn()    { echo -e "${YELLOW}[augur]${NC} $1"; }
error()   { echo -e "${RED}[augur] ERROR${NC} $1"; exit 1; }

# ── Check dependencies ───────────────────────────────────────────────────────
info "Checking dependencies..."

if ! command -v "$PYTHON" &>/dev/null; then
    error "Python not found. Install Python 3.8+ from https://python.org"
fi

PYTHON_VER=$("$PYTHON" -c "import sys; print(f'{sys.version_info.major}.{sys.version_info.minor}')")
if ! "$PYTHON" -c "import sys; assert sys.version_info >= (3,8)" 2>/dev/null; then
    error "Python $MIN_PYTHON+ required. Found: $PYTHON_VER"
fi
success "Python $PYTHON_VER ✓"

if ! command -v git &>/dev/null; then
    error "Git not found. Install git first."
fi
success "Git ✓"

# ── Clone or update ──────────────────────────────────────────────────────────
if [ -d "$INSTALL_DIR/.git" ]; then
    info "Updating existing installation at $INSTALL_DIR..."
    cd "$INSTALL_DIR"
    git pull --ff-only origin main 2>/dev/null || git pull origin main
else
    info "Cloning to $INSTALL_DIR..."
    git clone "$REPO" "$INSTALL_DIR"
    cd "$INSTALL_DIR"
fi

# ── Install ───────────────────────────────────────────────────────────────────
info "Installing Augur Next..."

# Try full install (data + mcp), fall back to minimal
if "$PYTHON" -c "import sys; assert sys.version_info >= (3,10)" 2>/dev/null; then
    "$PYTHON" -m pip install -e ".[data,mcp]" --quiet && success "Installed with MCP support ✓" \
    || "$PYTHON" -m pip install -e ".[data]" --quiet && warn "MCP install failed; installed data-only"
else
    "$PYTHON" -m pip install -e ".[data]" --quiet
    warn "MCP requires Python 3.10+. Installed data-only (no augur-mcp command)."
fi

# ── Verify ────────────────────────────────────────────────────────────────────
if command -v augur &>/dev/null; then
    success "augur CLI installed ✓"
else
    warn "'augur' not in PATH. Add to ~/.bashrc: export PATH=\"\$PATH:\$(python3 -m site --user-base)/bin\""
fi

# ── Done ─────────────────────────────────────────────────────────────────────
echo ""
echo -e "${BOLD}${GREEN}🦉 Augur Next installed at: $INSTALL_DIR${NC}"
echo ""
echo "  ${BOLD}Quick start:${NC}"
echo "    augur analyze AAPL                 # 18-master consensus"
echo "    augur serve                        # launch dashboard → http://localhost:8000"
echo "    augur-mcp                          # start MCP server for Hermes/Claude"
echo "    augur committee AAPL               # investment committee (coming soon)"
echo ""
echo "  ${BOLD}Connect to Hermes Studio:${NC}"
echo "    echo 'mcp_servers:\\n  augur:\\n    command: augur-mcp' >> ~/.hermes/config.yaml"
echo ""
echo "  ${BOLD}Docs:${NC} https://github.com/BruceLanLan/augur-next"
echo ""
