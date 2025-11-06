# Dotfiles

Personal dotfiles managed with [chezmoi](https://www.chezmoi.io/).

## Features

- **Cross-platform**: Works on macOS, Linux (Debian/Ubuntu, Arch, Fedora), Raspberry Pi, and Windows (MSYS2)
- **Unified package management**: Define packages once in YAML, install everywhere
- **Fish shell** with Tide prompt
- **Modern CLI tools**: bat, ripgrep, eza, fzf, git-delta, and more

## Quick Start

### Install chezmoi and apply dotfiles

```bash
# Install chezmoi
sh -c "$(curl -fsLS get.chezmoi.io)"

# Initialize from this repo
chezmoi init https://github.com/YOUR-USERNAME/dotfiles.git

# Review changes
chezmoi diff

# Apply dotfiles
chezmoi apply
```

### Install packages

After applying dotfiles, install packages for your platform:

```bash
install-packages
```

This automatically detects your platform and installs the appropriate packages.

## Package Management

This setup includes a unified cross-platform package management system. Edit packages once in [`.pkgmgmt/packages.yaml`](.pkgmgmt/packages.yaml), then generate platform-specific files.

### Adding a new package

1. Edit [`.pkgmgmt/packages.yaml`](.pkgmgmt/packages.yaml):

   ```yaml
   cli_tools:
     - name: tool-name
       desc: Description
       macos: brew-name
       msys2: mingw-w64-ucrt-x86_64-tool-name
       apt: apt-name
       pacman: pacman-name
       dnf: dnf-name
   ```

2. Generate platform-specific files:

   ```bash
   ./.pkgmgmt/generate_packages.py
   ```

3. Apply changes:

   ```bash
   chezmoi apply
   install-packages
   ```

See [.pkgmgmt/PACKAGES.md](.pkgmgmt/PACKAGES.md) for complete documentation or [.pkgmgmt/PACKAGES-QUICKREF.md](.pkgmgmt/PACKAGES-QUICKREF.md) for a quick reference.

## Structure

```
.
├── .pkgmgmt/packages.yaml              # Central package manifest
├── .pkgmgmt/generate_packages.py       # Package list generator
├── search-package.py          # Helper to search package names
├── dot_Brewfile_darwin        # Generated: macOS packages
├── dot_config/
│   ├── fish/                  # Fish shell configuration
│   ├── packages-*.txt.tmpl    # Generated: Platform package lists
│   └── ...
├── dot_local/bin/
│   └── install-packages.tmpl  # Universal package installer
└── dot_gitconfig.tmpl         # Git configuration

Documentation:
├── README.md                  # This file
├── .pkgmgmt/PACKAGES.md                # Complete package system documentation
└── .pkgmgmt/PACKAGES-QUICKREF.md       # Quick reference guide
```

## Configuration

### Git

On first run, chezmoi will prompt for:

- Git email
- Git name
- Whether to auto-install packages

These are stored in chezmoi's config and used in templates.

#### External Git Config

You can add machine-specific or private git settings in `~/.gitconfig.local`. This file is **not** managed by chezmoi and will be included automatically.

Example `~/.gitconfig.local`:

```ini
[user]
    signingkey = YOUR-GPG-KEY

[url "git@github.com:"]
    insteadOf = https://github.com/

[credential]
    helper = osxkeychain
```

### Fish Shell

The Fish shell configuration includes:

- [Tide prompt](https://github.com/IlanCosman/tide) (v6)
- Syntax highlighting
- Modern CLI tool aliases (eza for ls, bat for cat)
- Custom functions in `~/.config/fish/functions/`

#### External Fish Config

You can add machine-specific or private fish settings in `~/.config/fish/config.local.fish`. This file is **not** managed by chezmoi and will be sourced automatically.

Example `~/.config/fish/config.local.fish`:

```fish
# Machine-specific environment variables
set -x WORK_PROJECT_DIR ~/work/projects

# Private API keys (never commit these!)
set -x ANTHROPIC_API_KEY "sk-..."

# Machine-specific aliases
alias work="cd $WORK_PROJECT_DIR"
```

### Platform-Specific Files

Chezmoi templates automatically handle platform-specific files:

- Files ending in `_darwin` only apply to macOS
- Files ending in `_linux` only apply to Linux
- Templates can include conditional logic

## Updating

### Update dotfiles

```bash
# Pull latest changes
chezmoi update

# Or manually
chezmoi git pull
chezmoi apply
```

### Add new machines

```bash
# On new machine
chezmoi init https://github.com/YOUR-USERNAME/dotfiles.git
chezmoi apply
install-packages
```

## Development

### Testing in containers

Test your dotfiles in clean environments before deploying:

```bash
# Test on Debian (APT) - Primary CI environment
./.pkgmgmt/test-environments/test-chezmoi.sh debian

# Test on Ubuntu (APT)
./.pkgmgmt/test-environments/test-chezmoi.sh ubuntu

# Test on Arch Linux (Pacman)
./.pkgmgmt/test-environments/test-chezmoi.sh arch

# Test on Fedora (DNF)
./.pkgmgmt/test-environments/test-chezmoi.sh fedora
```

See [.pkgmgmt/test-environments/README.md](.pkgmgmt/test-environments/README.md) for detailed testing documentation.

### Testing package changes

```bash
# Edit .pkgmgmt/packages.yaml
vim .pkgmgmt/packages.yaml

# Generate and review
./.pkgmgmt/generate_packages.py
git diff

# Run tests
cd .pkgmgmt
python3 tests/test_generator.py
python3 tests/test_sync.py

# Test in a container (recommended)
./test-environments/test-chezmoi.sh debian
```

### Searching for packages

Use the helper script to find package names across platforms:

```bash
./search-package.py ripgrep
```

## Platform-Specific Notes

### macOS

- Uses Homebrew for package management
- Includes Mac App Store apps via `mas`
- GUI apps, fonts, and services configured via Brewfile

### MSYS2 (Windows)

- Uses UCRT runtime (modern standard)
- Package prefix: `mingw-w64-ucrt-x86_64-`
- Run in MSYS2 terminal, not Windows Command Prompt

### Linux

- **Debian/Ubuntu**: `bat` command is `batcat`
- **Arch Linux**: Most packages available in official repos
- **Fedora/RHEL**: Some modern tools may need COPR repos
- **Raspberry Pi**: Uses same packages as Debian/Ubuntu

## Resources

- [chezmoi documentation](https://www.chezmoi.io/)
- [Fish shell documentation](https://fishshell.com/docs/current/)
- [Package management documentation](.pkgmgmt/PACKAGES.md)
