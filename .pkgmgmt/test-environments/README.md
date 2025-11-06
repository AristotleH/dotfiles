# Testing Chezmoi Dotfiles in Containers

This directory contains Docker-based test environments for validating your chezmoi dotfiles across different Linux distributions.

**Note:** Debian is the primary test environment used in CI/CD (GitHub Actions). Arch and Fedora Dockerfiles are available for manual local testing.

## Quick Start

```bash
# Test on Debian (APT) - Primary CI environment
./test-chezmoi.sh debian

# Test on Ubuntu (APT)
./test-chezmoi.sh ubuntu

# Test on Arch Linux (Pacman) - Local testing only
./test-chezmoi.sh arch

# Test on Fedora (DNF) - Local testing only
./test-chezmoi.sh fedora
```

## Available Test Environments

| Distro | Package Manager | Use Case | CI/CD | Notes |
|--------|----------------|----------|-------|-------|
| `debian` | APT | Debian, Raspberry Pi OS | ✅ Automated | Native ARM64 support |
| `ubuntu` | APT | Ubuntu (latest) | Manual only | Native ARM64 support |
| `arch` | Pacman | Arch Linux, Manjaro | Manual only | x86_64 only (emulated on ARM) |
| `fedora` | DNF | Fedora, RHEL, CentOS | Manual only | Native ARM64 support |

## What Gets Tested

Each test environment:

1. ✅ Installs chezmoi from official installer
2. ✅ Initializes your dotfiles repository
3. ✅ Verifies the chezmoi structure is valid
4. ✅ Provides an interactive shell to test further

## Testing Workflow

### 1. Test with Local Repository (Default)

```bash
./test-chezmoi.sh debian
```

This mounts your local dotfiles repository and lets you test changes before pushing to Git.

### 2. Test with Remote Repository

```bash
./test-chezmoi.sh arch https://github.com/yourusername/dotfiles.git
```

This tests the full workflow a new machine would use (cloning from GitHub).

### 3. Inside the Container

Once inside the test container, you can:

```bash
# See what would be applied
chezmoi diff

# Apply dotfiles (dry-run)
chezmoi apply --dry-run --verbose

# Actually apply dotfiles
chezmoi apply

# Check generated package lists
cat ~/.config/packages-apt.txt      # Debian
cat ~/.config/packages-pacman.txt   # Arch
cat ~/.config/packages-dnf.txt      # Fedora

# Test installing packages (dry-run on Debian)
apt-get install --dry-run $(cat ~/.config/packages-apt.txt | grep -v '^#')

# Exit the container
exit
```

## Testing Package Installation

To test the actual package installation:

```bash
# Debian/Ubuntu
sudo apt-get update
sudo apt-get install $(cat ~/.config/packages-apt.txt | grep -v '^#')

# Arch Linux
sudo pacman -S --needed $(cat ~/.config/packages-pacman.txt | grep -v '^#')

# Fedora
sudo dnf install $(cat ~/.config/packages-dnf.txt | grep -v '^#')
```

**Note:** Most packages won't be available in the container environment (like fish, tmux, etc.), but you can verify the package list format is correct and test with packages that are available (like `git`, `curl`).

## Advanced Usage

### Keep Container Running for Multiple Tests

```bash
# Start container and keep it running
docker run -it --name chezmoi-test \
  -v "$PWD/../..:/dotfiles-src:ro" \
  chezmoi-test-debian bash

# In the container, initialize chezmoi
chezmoi init --source=/dotfiles-src

# Make changes to your dotfiles locally, then in container:
chezmoi update
chezmoi apply
```

### Test Specific Scenarios

```bash
# Test package generation
cd /dotfiles-src/.pkgmgmt
python3 generate_packages.py

# Run tests
python3 tests/test_generator.py
python3 tests/test_sync.py
```

### Clean Up

```bash
# Remove all test images
docker rmi chezmoi-test-debian chezmoi-test-arch chezmoi-test-fedora

# Remove all stopped containers
docker container prune
```

## CI/CD Integration

The GitHub Actions workflow (`.github/workflows/test-packages.yml`) automatically runs:

1. **Unit Tests** (Python) - Fast validation of generator and sync
2. **Integration Test (Debian)** - Full Docker-based test with chezmoi initialization
3. **macOS Validation** (main branch only) - Brewfile syntax check

**Why only Debian in CI?**
- Fastest to build (~60 seconds)
- Covers APT packages (also validates Raspberry Pi)
- Docker layer caching reduces subsequent runs to ~30-45 seconds
- Keeps CI time minimal (~2-3 minutes total)

**To test other distros:**
- Run locally using the test scripts
- Debian validates the core chezmoi functionality
- Platform-specific packages are validated in unit tests

## Troubleshooting

### Docker not found
```bash
# Install Docker Desktop on macOS
brew install --cask docker

# Or use OrbStack (lighter alternative)
brew install --cask orbstack
```

### Permission denied
```bash
# Make script executable
chmod +x test-chezmoi.sh
```

### Container fails to start
```bash
# Check Docker is running
docker ps

# Rebuild the image
docker build -t chezmoi-test-debian -f Dockerfile.debian .
```

## Platform-Specific Notes

### Debian/Ubuntu (APT)
- Tests the `apt` platform in packages.yaml
- Also validates Raspberry Pi (`raspi`) since it uses APT

### Arch Linux (Pacman)
- Tests the `pacman` platform in packages.yaml
- Some AUR packages may not be available in base repos

### Fedora (DNF)
- Tests the `dnf` platform in packages.yaml
- Works for RHEL/CentOS Stream as well

## Windows (MSYS2) Testing

MSYS2 testing requires a Windows environment. Consider:

- **GitHub Actions Windows runner**: Use `windows-latest`
- **Windows VM**: Use Parallels, VMware, or VirtualBox
- **WSL2**: Not the same as MSYS2, but can test Linux workflows

## macOS Testing

For macOS (Homebrew) testing:
- Use a macOS machine (native or VM)
- Or use GitHub Actions with `macos-latest` runner
- Test Brewfile generation in containers, but install only on macOS
