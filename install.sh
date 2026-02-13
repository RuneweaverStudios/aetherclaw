#!/bin/bash
#
# Aether-Claw Installer
# Secure, swarm-based AI assistant with cryptographic skill signing
#
# Usage: curl -sSL https://raw.githubusercontent.com/your-repo/aether-claw/main/install.sh | bash
#

set -e

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
CYAN='\033[0;36m'
NC='\033[0m' # No Color

# Default install location
INSTALL_DIR="${HOME}/.aether-claw"
REPO_URL="https://github.com/RuneweaverStudios/aetherclaw.git"

echo -e "${BLUE}"
echo "╔══════════════════════════════════════════════════╗"
echo "║                A E T H E R C L A W                 ║"
echo "║  ───────────────────────────────────────────────  ║"
echo "║     Secure Swarm-Based Second Brain / Agent        ║"
echo "║  Local • Cryptographically Signed Skills • Memory  ║"
echo "╚══════════════════════════════════════════════════╝"
echo -e "${NC}"
echo ""
echo -e "${CYAN}   █████╗ ███████╗████████╗██╗  ██╗███████╗██████╗ "
echo "  ██╔══██╗██╔════╝╚══██╔══╝██║  ██║██╔════╝██╔══██╗"
echo "  ███████║█████╗     ██║   ███████║█████╗  ██████╔╝"
echo "  ██╔══██║██╔══╝     ██║   ██╔══██║██╔══╝  ██╔══██╗"
echo "  ██║  ██║███████╗   ██║   ██║  ██║███████╗██║  ██║"
echo "  ╚═╝  ╚═╝╚══════╝   ╚═╝   ╚═╝  ╚═╝╚══════╝╚═╝  ╚═╝${NC}"
echo ""

# Check Python
if ! command -v python3 &> /dev/null; then
    echo -e "${RED}Error: Python 3 is required but not installed.${NC}"
    echo "Please install Python 3.8+ and try again."
    exit 1
fi

PYTHON_VERSION=$(python3 -c 'import sys; print(f"{sys.version_info.major}.{sys.version_info.minor}")')
echo -e "${GREEN}✓${NC} Python $PYTHON_VERSION found"

# Check pip
if ! command -v pip3 &> /dev/null; then
    echo -e "${RED}Error: pip3 is required but not installed.${NC}"
    exit 1
fi
echo -e "${GREEN}✓${NC} pip found"

# Parse arguments
BRANCH="main"
while [[ $# -gt 0 ]]; do
    case $1 in
        --branch|-b)
            BRANCH="$2"
            shift 2
            ;;
        --dir|-d)
            INSTALL_DIR="$2"
            shift 2
            ;;
        --help|-h)
            echo "Usage: curl -sSL <url> | bash [OPTIONS]"
            echo ""
            echo "Options:"
            echo "  --branch, -b BRANCH   Git branch to install (default: main)"
            echo "  --dir, -d DIR         Installation directory (default: ~/.aether-claw)"
            echo "  --help, -h            Show this help message"
            exit 0
            ;;
        *)
            echo -e "${RED}Unknown option: $1${NC}"
            exit 1
            ;;
    esac
done

# Create installation directory
echo ""
echo -e "${BLUE}Installing Aether-Claw...${NC}"

if [ -d "$INSTALL_DIR" ]; then
    echo -e "${YELLOW}Existing installation found at $INSTALL_DIR${NC}"
    read -p "Remove and reinstall? [y/N] " -n 1 -r
    echo
    if [[ $REPLY =~ ^[Yy]$ ]]; then
        rm -rf "$INSTALL_DIR"
    else
        echo "Aborting installation."
        exit 1
    fi
fi

# Clone repository
if command -v git &> /dev/null; then
    echo -e "${GREEN}✓${NC} Cloning repository..."
    git clone --depth 1 --branch "$BRANCH" "$REPO_URL" "$INSTALL_DIR" 2>/dev/null || {
        echo -e "${YELLOW}!${NC} Could not clone from git, downloading archive..."
        TEMP_DIR=$(mktemp -d)
        curl -sSL "https://github.com/your-repo/aether-claw/archive/refs/heads/$BRANCH.tar.gz" | tar -xzf - -C "$TEMP_DIR"
        mv "$TEMP_DIR/aether-claw-$BRANCH" "$INSTALL_DIR"
        rm -rf "$TEMP_DIR"
    }
else
    echo -e "${YELLOW}!${NC} Git not found, downloading archive..."
    TEMP_DIR=$(mktemp -d)
    curl -sSL "https://github.com/your-repo/aether-claw/archive/refs/heads/$BRANCH.tar.gz" | tar -xzf - -C "$TEMP_DIR"
    mv "$TEMP_DIR/aether-claw-$BRANCH" "$INSTALL_DIR"
    rm -rf "$TEMP_DIR"
fi

# Install dependencies
echo -e "${GREEN}✓${NC} Installing dependencies..."
cd "$INSTALL_DIR"
pip3 install -q cryptography bandit plyer streamlit pyyaml psutil 2>/dev/null || {
    echo -e "${RED}Error installing dependencies.${NC}"
    exit 1
}

# Create aetherclaw command
BIN_DIR="$HOME/.local/bin"
mkdir -p "$BIN_DIR"

cat > "$BIN_DIR/aetherclaw" << 'EOF'
#!/bin/bash
# Aether-Claw CLI wrapper
cd "$HOME/.aether-claw" 2>/dev/null || cd "$(dirname "$0")/../.aether-claw"
python3 aether_claw.py "$@"
EOF
chmod +x "$BIN_DIR/aetherclaw"

# Add to PATH if needed
if [[ ":$PATH:" != *":$BIN_DIR:"* ]]; then
    SHELL_RC=""
    if [ -n "$ZSH_VERSION" ]; then
        SHELL_RC="$HOME/.zshrc"
    elif [ -n "$BASH_VERSION" ]; then
        SHELL_RC="$HOME/.bashrc"
    fi

    if [ -n "$SHELL_RC" ]; then
        echo "" >> "$SHELL_RC"
        echo "# Aether-Claw" >> "$SHELL_RC"
        echo 'export PATH="$HOME/.local/bin:$PATH"' >> "$SHELL_RC"
        echo -e "${GREEN}✓${NC} Added to PATH in $SHELL_RC"
    fi
fi

# Create default .env template
if [ ! -f "$INSTALL_DIR/.env" ]; then
    cat > "$INSTALL_DIR/.env" << 'EOF'
# Aether-Claw Environment Configuration
# Add your API keys here (this file is gitignored)

# OpenRouter API Key (recommended)
OPENROUTER_API_KEY=

# Alternative: Z.ai GLM API Key
GLM_API_KEY=

# Notifications (optional)
TODOIST_API_KEY=
EOF
    echo -e "${GREEN}✓${NC} Created .env template"
fi

echo ""
echo -e "${GREEN}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo -e "${GREEN}✓ Aether-Claw installed successfully!${NC}"
echo -e "${GREEN}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo ""
echo -e "Installation directory: ${BLUE}$INSTALL_DIR${NC}"
echo ""
echo -e "${YELLOW}Next steps:${NC}"
echo ""
echo "  1. Add your API key to $INSTALL_DIR/.env"
echo "     Or export it: export OPENROUTER_API_KEY=your-key"
echo ""
echo "  2. Run onboarding:"
echo -e "     ${BLUE}aetherclaw onboard${NC}"
echo ""
echo "  3. Or start using immediately:"
echo -e "     ${BLUE}aetherclaw status${NC}"
echo -e "     ${BLUE}aetherclaw dashboard${NC}"
echo ""

# Check if PATH needs refresh
if [[ ":$PATH:" != *":$BIN_DIR:"* ]]; then
    echo -e "${YELLOW}Note: Restart your shell or run: source ~/.bashrc (or ~/.zshrc)${NC}"
    echo ""
fi
