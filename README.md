# Dotfiles

Personal dotfiles managed with [chezmoi](https://www.chezmoi.io/).

## Features

- **Cross-platform**: macOS, Linux (Debian/Ubuntu, Arch, Fedora), and Windows (MSYS2)
- **Four-shell support**: Fish, Zsh, Bash, and PowerShell from a single YAML manifest
- **Optional package management**: Install from an external `packages.yaml` at apply time
- **Modern CLI tools**: bat, eza, fd, fzf, ripgrep, zoxide, git-delta, and more
- **Tmux integration**: Mouse support, OSC passthrough for modern terminals
- **No-chezmoi bootstrap**: `bootstrap.sh` for machines where chezmoi can't be installed

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

The included bootstrap script sets up everything without chezmoi — shell configs,
gitconfig, tmux, neovim, and more. It works on macOS, Linux, and MSYS2.

```bash
git clone <this-repo-url> dotfiles
dotfiles/bootstrap.sh
```

Requires Python 3 and PyYAML (`pip3 install pyyaml`).

## Package Management

Packages are installed during `chezmoi apply` from an external `packages.yaml` you maintain
outside of this repo. Set `packages.manifestPath` in your chezmoi config:

```toml
# ~/.config/chezmoi/chezmoi.toml
[data.packages]
  manifestPath = "/path/to/your/packages.yaml"
```

If unset or the file doesn't exist, package installation is silently skipped.

See the test fixtures in
[`.pkgmgmt/tests/test_generator.py`](.pkgmgmt/tests/test_generator.py) for the `packages.yaml` schema.

## Structure

```
.
├── bootstrap.sh                        # No-chezmoi installer
├── .shellgen/                          # Shell config generator
│   ├── shell.yaml                      # Central shell manifest
│   └── generate_shell.py              # YAML → Fish/Zsh/Bash/PowerShell
├── .pkgmgmt/                           # Package management
│   ├── generate_packages.py            # YAML → platform package lists
│   └── test-environments/              # Docker-based integration tests
├── dot_config/
│   ├── fish/                           # Fish (config.fish, conf.d/, functions/)
│   ├── zsh/                            # Zsh (dot_zshrc, dot_zshrc.d/, dot_zfunctions/)
│   ├── bash/                           # Bash (bashrc.d/, functions/)
│   ├── powershell/                     # PowerShell (profile, conf.d/, functions/)
│   ├── tmux/                           # Tmux configuration
│   ├── nvim/                           # Neovim configuration
│   ├── ghostty/                        # Ghostty terminal config
│   └── mise/                           # Mise (runtime manager) config
├── dot_local/bin/
│   └── install-packages.tmpl           # Standalone package installer
└── dot_gitconfig.tmpl                  # Git configuration template
```

## Configuration

### Git

On first run, chezmoi will prompt for:

- Git email and name
- Extra gitconfig paths (comma-separated, optional)
- Path to an external `packages.yaml` (optional)
- Extra shell manifest paths (optional)

These are stored in chezmoi's config and used in templates.

#### External Git Config

Add machine-specific or private git settings in `~/.gitconfig.local`.
This file is **not** managed by chezmoi and is included automatically.

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

- Custom prompt (pwd + git status + arrow, transient on submit)
- Syntax highlighting (built-in)
- Modern CLI tool aliases (eza, bat, etc.)
- Custom functions in `~/.config/fish/functions/`

#### External Fish Config

Add machine-specific settings in `~/.config/fish/config.local.fish` (not managed by chezmoi).

### Zsh Shell

The Zsh shell configuration includes:

- Custom prompt (pwd + git status + arrow, transient on submit) matching Fish
- [Antidote](https://github.com/mattmc3/antidote) plugin manager
- Syntax highlighting and autosuggestions
- Native git completions (full subcommand support)
- Custom functions in `~/.config/zsh/.zfunctions/`

#### Zsh Plugins

Plugins are defined in `~/.config/zsh/.zsh_plugins.txt`:

- `zsh-users/zsh-completions` - Additional completions
- `zdharma-continuum/fast-syntax-highlighting` - Command highlighting
- `zsh-users/zsh-autosuggestions` - Fish-like history suggestions
- `marlonrichert/zsh-autocomplete` - Fish-like live completions

#### External Zsh Config

Add machine-specific settings in `~/.config/zsh/.zshrc.local` (not managed by chezmoi).

### Tmux

Tmux configuration includes:

- Mouse support
- OSC passthrough for modern terminals (Ghostty, iTerm2, etc.)
- 256-color and RGB support
- 1-indexed windows and panes

To enable auto-attach on shell startup, set `TMUX_AUTO_ATTACH=1` in
your environment (e.g., in `~/.config/zsh/.zshrc.local`).

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

### Running tests

```bash
# Shell generator
python3 .shellgen/tests/test_shell_generator.py

# Package generator
python3 .pkgmgmt/tests/test_generator.py

# Bootstrap script
python3 .tests/test_bootstrap.py

# Shell config validation
python3 .tests/test_zsh.py
python3 .tests/test_fish.py
```

## Platform-Specific Notes

- **macOS**: Packages via Homebrew (including casks and Mac App Store via `mas`)
- **Linux**: Detected automatically — APT, Pacman, or DNF
- **Raspberry Pi**: Uses APT packages (same as Debian/Ubuntu)
- **MSYS2**: Uses UCRT runtime; run in MSYS2 terminal, not CMD
