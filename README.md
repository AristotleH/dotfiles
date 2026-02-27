# Dotfiles

Personal dotfiles managed with [chezmoi](https://www.chezmoi.io/).

## Features

- **Cross-platform**: Works on macOS, Linux (Debian/Ubuntu, Arch, Fedora), and Windows (MSYS2)
- **Unified package management**: Define packages once in YAML, install everywhere
- **Dual shell support**: Fish (with Tide prompt) and Zsh (with Powerlevel10k)
- **Modern CLI tools**: bat, eza, fd, fzf, ripgrep, zoxide, git-delta, and more
- **Tmux integration**: Mouse support, OSC passthrough for modern terminals

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

### If You Cannot Install Chezmoi

You can still use the shell setup directly from a clone of this repo:

```bash
git clone <this-repo-url> dotfiles
cd dotfiles

# Generate cross-shell config directly into ~/.config
python3 .shellgen/generate_shell.py --target "$HOME/.config" .shellgen/shell.yaml "$HOME/.config/shell.d"

# Bash entrypoints
cp dot_bashrc "$HOME/.bashrc"
cp dot_bash_profile "$HOME/.bash_profile"

# PowerShell profile (pwsh)
mkdir -p "$HOME/.config/powershell"
cp dot_config/powershell/Microsoft.PowerShell_profile.ps1 "$HOME/.config/powershell/Microsoft.PowerShell_profile.ps1"
```

On Windows PowerShell, use the profile bridge path:

```powershell
New-Item -ItemType Directory -Force -Path "$HOME\\Documents\\PowerShell" | Out-Null
Copy-Item private_Documents/private_PowerShell/Microsoft.PowerShell_profile.ps1 `
  "$HOME\\Documents\\PowerShell\\Microsoft.PowerShell_profile.ps1" -Force
```

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
├── .pkgmgmt/                           # Package management system
│   ├── packages.yaml                   # Central package manifest
│   ├── generate_packages.py            # Package list generator
│   └── test-environments/              # Container-based testing
├── dot_config/
│   ├── fish/                           # Fish shell configuration
│   │   ├── config.fish                 # Main config (sources conf.d/)
│   │   ├── conf.d/                     # Modular config files
│   │   └── functions/                  # Custom functions
│   ├── zsh/                            # Zsh shell configuration
│   │   ├── dot_zshrc                   # Main config (sources .zshrc.d/)
│   │   ├── dot_zshenv                  # Environment variables
│   │   ├── dot_zsh_plugins.txt         # Antidote plugin list
│   │   ├── dot_zshrc.d/                # Modular config files
│   │   └── dot_zfunctions/             # Custom functions
│   ├── tmux/                           # Tmux configuration
│   └── packages-*.txt.tmpl             # Generated: Platform package lists
├── dot_local/bin/
│   └── install-packages.tmpl           # Universal package installer
└── dot_gitconfig.tmpl                  # Git configuration
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
- Syntax highlighting (built-in)
- Modern CLI tool aliases (eza, bat, etc.)
- Custom functions in `~/.config/fish/functions/`

#### External Fish Config

Add machine-specific settings in `~/.config/fish/config.local.fish` (not managed by chezmoi).

### Zsh Shell

The Zsh shell configuration includes:

- [Powerlevel10k](https://github.com/romkatv/powerlevel10k) prompt (run `p10k configure` to customize)
- [Antidote](https://github.com/mattmc3/antidote) plugin manager
- [fzf-tab](https://github.com/Aloxaf/fzf-tab) for fuzzy completion
- Syntax highlighting and autosuggestions
- Native git completions (full subcommand support)
- Custom functions in `~/.config/zsh/.zfunctions/`

#### Zsh Plugins

Plugins are defined in `~/.config/zsh/.zsh_plugins.txt`:

- `mattmc3/ez-compinit` - Lazy completion initialization
- `zsh-users/zsh-completions` - Additional completions
- `Aloxaf/fzf-tab` - Fuzzy tab completion with fzf
- `romkatv/powerlevel10k` - Fast, customizable prompt
- `zdharma-continuum/fast-syntax-highlighting` - Command highlighting
- `zsh-users/zsh-autosuggestions` - Fish-like history suggestions

#### External Zsh Config

Add machine-specific settings in `~/.config/zsh/.zshrc.local` (not managed by chezmoi).

### Tmux

Tmux configuration includes:

- Mouse support
- OSC passthrough for modern terminals (Ghostty, iTerm2, etc.)
- 256-color and RGB support
- 1-indexed windows and panes

To enable auto-attach on shell startup, set `TMUX_AUTO_ATTACH=1` in your environment (e.g., in `~/.config/zsh/.zshrc.local`).

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
- [Zsh documentation](https://zsh.sourceforge.io/Doc/)
- [Powerlevel10k](https://github.com/romkatv/powerlevel10k)
- [fzf](https://github.com/junegunn/fzf)
- [Package management documentation](.pkgmgmt/PACKAGES.md)
