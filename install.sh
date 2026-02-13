#!/bin/bash
#
# Aether-Claw Installer
# Secure, swarm-based AI assistant with cryptographic skill signing
#
# Usage: curl -sSL https://raw.githubusercontent.com/RuneweaverStudios/aetherclaw/main/install.sh | bash
#

set -e

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
CYAN='\033[0;36m'
NC='\033[0m'

# Default install location
INSTALL_DIR="${HOME}/.aether-claw"
REPO_URL="https://github.com/RuneweaverStudios/aetherclaw.git"
FORCE_INSTALL=false

# Banner
echo ""
printf "${BLUE}╔════════════════════════════════════════════════════╗${NC}\n"
printf "${BLUE}║${NC} ${CYAN}                A E T H E R C L A W                 ${NC} ${BLUE}║${NC}\n"
printf "${BLUE}║${NC} ${DIM}  ───────────────────────────────────────────────  ${NC}${BLUE}║${NC}\n"
printf "${BLUE}║${NC} ${WHITE}     Secure Swarm-Based Second Brain / Agent        ${NC} ${BLUE}║${NC}\n"
printf "${BLUE}║${NC} ${DIM}  Local • Cryptographically Signed Skills • Memory  ${NC} ${BLUE}║${NC}\n"
printf "${BLUE}╚════════════════════════════════════════════════════╝${NC}\n"
echo ""
printf "${CYAN}   █████╗ ███████╗████████╗██╗  ██╗███████╗██████╗${NC}\n"
printf "${CYAN}  ██╔══██╗██╔════╝╚══██╔══╝██║  ██║██╔════╝██╔══██╗${NC}\n"
printf "${CYAN}  ███████║█████╗     ██║   ███████║█████╗  ██████╔╝${NC}\n"
printf "${CYAN}  ██╔══██║██╔══╝     ██║   ██╔══██║██╔══╝  ██╔══██╗${NC}\n"
printf "${CYAN}  ██║  ██║███████╗   ██║   ██║  ██║███████╗██║  ██║${NC}\n"
printf "${CYAN}  ╚═╝  ╚═╝╚══════╝   ╚═╝   ╚═╝  ╚═╝╚══════╝╚═╝  ╚═╝${NC}\n"
echo ""

# Check Python
if ! command -v python3 &> /dev/null; then
    printf "${RED}Error: Python 3 is required but not installed.${NC}\n"
    echo "Please install Python 3.8+ and try again."
    exit 1
fi

PYTHON_VERSION=$(python3 -c 'import sys; print(f"{sys.version_info.major}.{sys.version_info.minor}")')
printf "${GREEN}✓${NC} Python $PYTHON_VERSION found\n"

# Check pip
if ! command -v pip3 &> /dev/null; then
    printf "${RED}Error: pip3 is required but not installed.${NC}\n"
    exit 1
fi
printf "${GREEN}✓${NC} pip found\n"

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
        --force|-f)
            FORCE_INSTALL=true
            shift
            ;;
        --help|-h)
            echo "Usage: curl -sSL <url> | bash -s -- [OPTIONS]"
            echo ""
            echo "Options:"
            echo "  --branch, -b BRANCH   Git branch to install (default: main)"
            echo "  --dir, -d DIR         Installation directory (default: ~/.aether-claw)"
            echo "  --force, -f           Force reinstall if already exists"
            echo "  --help, -h            Show this help message"
            exit 0
            ;;
        *)
            printf "${RED}Unknown option: $1${NC}\n"
            exit 1
            ;;
    esac
done

# Create installation directory
printf "\n${BLUE}Installing Aether-Claw...${NC}\n"

if [ -d "$INSTALL_DIR" ]; then
    if [ "$FORCE_INSTALL" = true ]; then
        printf "${YELLOW}Removing existing installation...${NC}\n"
        rm -rf "$INSTALL_DIR"
    else
        printf "${YELLOW}Existing installation found at $INSTALL_DIR${NC}\n"
        printf "Use --force to reinstall, or run: ${CYAN}aetherclaw onboard${NC}\n"
        printf "If aetherclaw command not found, run: ${CYAN}source ~/.zshrc${NC} (or ~/.bashrc)\n"
        exit 0
    fi
fi

# Clone repository
if command -v git &> /dev/null; then
    printf "${GREEN}✓${NC} Cloning repository...\n"
    git clone --depth 1 --branch "$BRANCH" "$REPO_URL" "$INSTALL_DIR" 2>/dev/null || {
        printf "${YELLOW}!${NC} Could not clone from git, downloading archive...\n"
        TEMP_DIR=$(mktemp -d)
        curl -sSL "https://github.com/RuneweaverStudios/aetherclaw/archive/refs/heads/$BRANCH.tar.gz" | tar -xzf - -C "$TEMP_DIR"
        mv "$TEMP_DIR/aetherclaw-$BRANCH" "$INSTALL_DIR"
        rm -rf "$TEMP_DIR"
    }
else
    printf "${YELLOW}!${NC} Git not found, downloading archive...\n"
    TEMP_DIR=$(mktemp -d)
    curl -sSL "https://github.com/RuneweaverStudios/aetherclaw/archive/refs/heads/$BRANCH.tar.gz" | tar -xzf - -C "$TEMP_DIR"
    mv "$TEMP_DIR/aetherclaw-$BRANCH" "$INSTALL_DIR"
    rm -rf "$TEMP_DIR"
fi

# Install dependencies
printf "${GREEN}✓${NC} Installing dependencies...\n"
cd "$INSTALL_DIR"
pip3 install -q cryptography bandit plyer streamlit pyyaml psutil rich python-dotenv 2>/dev/null || {
    printf "${RED}Error installing dependencies.${NC}\n"
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
        printf "${GREEN}✓${NC} Added to PATH in $SHELL_RC\n"
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

# Telegram Integration (optional)
TELEGRAM_BOT_TOKEN=
TELEGRAM_CHAT_ID=
EOF
    printf "${GREEN}✓${NC} Created .env template\n"
fi

printf "\n${GREEN}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}\n"
printf "${GREEN}✓ Aether-Claw installed successfully!${NC}\n"
printf "${GREEN}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}\n"
printf "\nInstallation directory: ${BLUE}$INSTALL_DIR${NC}\n"
printf "\n${YELLOW}Next steps:${NC}\n"
printf "\n  1. Add your API key:\n"
printf "     ${CYAN}export OPENROUTER_API_KEY=your-key${NC}\n"
printf "     Or edit: ${BLUE}$INSTALL_DIR/.env${NC}\n"
printf "\n  2. Reload your shell:\n"
printf "     ${CYAN}source ~/.zshrc${NC}  (or ~/.bashrc)\n"
printf "\n  3. Run onboarding:\n"
printf "     ${CYAN}aetherclaw onboard${NC}\n"
printf "\n  4. Launch interfaces:\n"
printf "     ${CYAN}aetherclaw tui${NC}        # Terminal UI\n"
printf "     ${CYAN}aetherclaw dashboard${NC}  # Web dashboard\n"
printf "\n"
