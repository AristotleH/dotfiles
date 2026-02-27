#!/usr/bin/env bash
# Test chezmoi dotfiles in a containerized environment
#
# Usage:
#   ./test-chezmoi.sh <distro> [repo-url]
#
# Examples:
#   ./test-chezmoi.sh debian
#   ./test-chezmoi.sh arch https://github.com/yourusername/dotfiles.git
#   ./test-chezmoi.sh fedora /path/to/local/repo

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "$SCRIPT_DIR/../.." && pwd)"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

usage() {
    echo "Usage: $0 <distro> [repo-url]"
    echo ""
    echo "Available distros:"
    echo "  debian  - Debian Bookworm (APT)"
    echo "  ubuntu  - Ubuntu Latest (APT)"
    echo "  arch    - Arch Linux (Pacman)"
    echo "  fedora  - Fedora (DNF)"
    echo ""
    echo "Options:"
    echo "  repo-url  - Git repository URL or local path (default: local repo)"
    echo ""
    echo "Examples:"
    echo "  $0 debian"
    echo "  $0 ubuntu"
    echo "  $0 arch https://github.com/yourusername/dotfiles.git"
    exit 1
}

if [ $# -lt 1 ]; then
    usage
fi

DISTRO="$1"
REPO_SOURCE="${2:-local}"

# Validate distro
if [ ! -f "$SCRIPT_DIR/Dockerfile.$DISTRO" ]; then
    echo -e "${RED}Error: Dockerfile.$DISTRO not found${NC}"
    echo "Available distros: debian, ubuntu, arch, fedora"
    exit 1
fi

IMAGE_NAME="chezmoi-test-$DISTRO"
CONTAINER_NAME="chezmoi-test-$DISTRO-$(date +%s)"

echo -e "${BLUE}Building Docker image for $DISTRO...${NC}"
docker build -t "$IMAGE_NAME" -f "$SCRIPT_DIR/Dockerfile.$DISTRO" "$SCRIPT_DIR"

echo ""
echo -e "${BLUE}Starting container...${NC}"

if [ "$REPO_SOURCE" = "local" ]; then
    echo -e "${YELLOW}Using local repository${NC}"
    # Mount the repo as read-only and copy it inside the container
    docker run -it --rm \
        --name "$CONTAINER_NAME" \
        -v "$REPO_ROOT:/dotfiles-src:ro" \
        "$IMAGE_NAME" \
        bash -c '
            set -e
            echo "📦 Copying dotfiles repository..."
            cp -r /dotfiles-src /tmp/dotfiles

            echo ""
            echo "🔧 Pre-configuring chezmoi to avoid prompts..."
            mkdir -p ~/.config/chezmoi
            cat > ~/.config/chezmoi/chezmoi.toml << "CFGEOF"
[data.git]
  email = "test@example.com"
  name = "Test User"

[data.packages]
  runInstalls = false

[data.shell]
  extraManifests = ""
CFGEOF

            echo ""
            echo "🔧 Initializing chezmoi from local directory..."
            chezmoi init --source=/tmp/dotfiles --apply --force

            echo ""
            echo "📋 Verifying dotfiles structure..."
            chezmoi --source=/tmp/dotfiles status || true

            echo ""
            echo "✅ Chezmoi initialized successfully!"
            echo ""
            echo "Available commands in this test environment:"
            echo "  chezmoi diff                  # Show differences"
            echo "  chezmoi apply                 # Apply any remaining changes"
            echo "  cat ~/.config/packages-apt.txt  # View generated package list"
            echo "  ls -la ~/.config/fish/        # View fish configuration"
            echo "  exit                          # Exit container"
            echo ""
            exec bash
        '
else
    echo -e "${YELLOW}Using remote repository: $REPO_SOURCE${NC}"
    docker run -it --rm \
        --name "$CONTAINER_NAME" \
        "$IMAGE_NAME" \
        bash -c "
            set -e
            echo '🔧 Pre-configuring chezmoi to avoid prompts...'
            mkdir -p ~/.config/chezmoi
            cat > ~/.config/chezmoi/chezmoi.toml << 'CFGEOF'
[data.git]
  email = \"test@example.com\"
  name = \"Test User\"

[data.packages]
  runInstalls = false

[data.shell]
  extraManifests = \"\"
CFGEOF

            echo ''
            echo '🔧 Initializing chezmoi from remote repository...'
            chezmoi init '$REPO_SOURCE' --apply --force

            echo ''
            echo '📋 Verifying dotfiles structure...'
            chezmoi status || true

            echo ''
            echo '✅ Chezmoi initialized successfully!'
            echo ''
            echo 'Available commands in this test environment:'
            echo '  chezmoi diff                  # Show differences'
            echo '  chezmoi apply                 # Apply any remaining changes'
            echo '  cat ~/.config/packages-*.txt  # View generated package lists'
            echo '  ls -la ~/.config/fish/        # View fish configuration'
            echo '  exit                          # Exit container'
            echo ''
            exec bash
        "
fi

echo -e "${GREEN}Test completed!${NC}"
