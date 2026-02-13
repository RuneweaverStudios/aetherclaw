#!/bin/bash
#
# Aether-Claw Installer
# Secure, swarm-based AI assistant with cryptographic skill signing
#
# Usage: curl -sSL https://raw.githubusercontent.com/RuneweaverStudios/aetherclaw/main/install.sh | bash -s -- [OPTIONS]
#

set -e

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
CYAN='\033[0;36m'
NC='\033[0m'

# Defaults
INSTALL_DIR="${HOME}/.aether-claw"
REPO_URL="https://github.com/RuneweaverStudios/aetherclaw.git"
BRANCH="main"
FORCE=false

# Parse arguments FIRST before anything else
while [[ $# -gt 0 ]]; do
    case $1 in
        --force|-f)
            FORCE=true
            shift
            ;;
        --branch|-b)
            BRANCH="$2"
            shift 2
            ;;
        --dir|-d)
            INSTALL_DIR="$2"
            shift 2
            ;;
        --help|-h)
            echo "Usage: curl -sSL <url> | bash -s -- [OPTIONS]"
            echo ""
            echo "Options:"
            echo "  --force, -f           Force reinstall if already exists"
            echo "  --branch, -b BRANCH   Git branch to install (default: main)"
            echo "  --dir, -d DIR         Installation directory (default: ~/.aether-claw)"
            echo "  --help, -h            Show this help message"
            exit 0
            ;;
        *)
            shift
            ;;
    esac
done

# Banner (no ANSI in middle of lines)
echo ""
printf "${BLUE}╔════════════════════════════════════════════════════╗${NC}\n"
printf "${BLUE}║${NC} ${CYAN}                A E T H E R C L A W                 ${NC} ${BLUE}║${NC}\n"
printf "${BLUE}║${NC}   ───────────────────────────────────────────────  ${BLUE}║${NC}\n"
printf "${BLUE}║${NC}      Secure Swarm-Based Second Brain / Agent      ${NC} ${BLUE}║${NC}\n"
printf "${BLUE}║${NC}   Local • Cryptographically Signed Skills • Memory${NC} ${BLUE}║${NC}\n"
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

# Create installation directory
printf "\n${BLUE}Installing Aether-Claw...${NC}\n"

if [ -d "$INSTALL_DIR" ]; then
    if [ "$FORCE" = true ]; then
        printf "${YELLOW}Removing existing installation...${NC}\n"
        rm -rf "$INSTALL_DIR"
    else
        printf "${YELLOW}Existing installation found at $INSTALL_DIR${NC}\n"
        printf "Use ${CYAN}--force${NC} to reinstall\n"
        printf "\nQuick start:\n"
        printf "  ${CYAN}source ~/.zshrc${NC}\n"
        printf "  ${CYAN}aetherclaw onboard${NC}\n"
        exit 0
    fi
fi

# Clone repository
if command -v git &> /dev/null; then
    printf "${GREEN}✓${NC} Cloning repository...\n"
    git clone --depth 1 --branch "$BRANCH" "$REPO_URL" "$INSTALL_DIR" 2>/dev/null || {
        printf "${YELLOW}!${NC} Downloading archive...\n"
        TEMP_DIR=$(mktemp -d)
        curl -sSL "https://github.com/RuneweaverStudios/aetherclaw/archive/refs/heads/$BRANCH.tar.gz" | tar -xzf - -C "$TEMP_DIR"
        mv "$TEMP_DIR/aetherclaw-$BRANCH" "$INSTALL_DIR"
        rm -rf "$TEMP_DIR"
    }
else
    printf "${YELLOW}!${NC} Downloading archive...\n"
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

cat > "$BIN_DIR/aetherclaw" << 'CMD_EOF'
#!/bin/bash
cd "$HOME/.aether-claw" 2>/dev/null || cd "$(dirname "$0")/../.aether-claw"
python3 aether_claw.py "$@"
CMD_EOF
chmod +x "$BIN_DIR/aetherclaw"

# Add to PATH
NEED_RELOAD=false
if [[ ":$PATH:" != *":$BIN_DIR:"* ]]; then
    SHELL_RC=""
    if [ -n "$ZSH_VERSION" ]; then
        SHELL_RC="$HOME/.zshrc"
    elif [ -n "$BASH_VERSION" ]; then
        SHELL_RC="$HOME/.bashrc"
    fi

    if [ -n "$SHELL_RC" ]; then
        # Check if already in shell rc
        if ! grep -q '.local/bin' "$SHELL_RC" 2>/dev/null; then
            echo "" >> "$SHELL_RC"
            echo "# Aether-Claw" >> "$SHELL_RC"
            echo 'export PATH="$HOME/.local/bin:$PATH"' >> "$SHELL_RC"
        fi
        printf "${GREEN}✓${NC} Added to PATH\n"
        NEED_RELOAD=true
    fi
fi

# Create .env template
if [ ! -f "$INSTALL_DIR/.env" ]; then
    cat > "$INSTALL_DIR/.env" << 'ENV_EOF'
# Aether-Claw Environment Configuration

# OpenRouter API Key (recommended)
OPENROUTER_API_KEY=

# Alternative: Z.ai GLM API Key
GLM_API_KEY=

# Telegram Integration (optional)
TELEGRAM_BOT_TOKEN=
TELEGRAM_CHAT_ID=
ENV_EOF
    printf "${GREEN}✓${NC} Created .env template\n"
fi

printf "\n${GREEN}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}\n"
printf "${GREEN}✓ Aether-Claw installed!${NC}\n"
printf "${GREEN}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}\n"
printf "\n${BLUE}Location:${NC} $INSTALL_DIR\n"
printf "\n${YELLOW}Next:${NC}\n"
printf "  ${CYAN}export OPENROUTER_API_KEY=your-key${NC}\n"
printf "  ${CYAN}aetherclaw onboard${NC}\n"
printf "\n"

# Auto-reload shell if needed
if [ "$NEED_RELOAD" = true ]; then
    printf "${DIM}Reloading shell...${NC}\n"
    if [ -n "$ZSH_VERSION" ]; then
        exec zsh -l
    elif [ -n "$BASH_VERSION" ]; then
        exec bash -l
    fi
fi
