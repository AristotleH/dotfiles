# AGENTS.md

This file provides guidance to coding agents when working with this repository.

## Overview

Chezmoi-managed dotfiles for macOS, Linux (Debian/Ubuntu, Arch, Fedora),
and Windows (MSYS2). Four shells (Fish, Zsh, Bash, PowerShell) are generated
from a base YAML manifest plus optional external manifests. Optional package management installs
platform-specific packages from an external `packages.yaml` during
`chezmoi apply`. A `bootstrap.sh` script provides a no-chezmoi fallback.

## Common Commands

### Shell Generation

```bash
# Generate shell configs (to chezmoi source dir)
cd .shellgen && make generate

# Run all shell generator tests
cd .shellgen && make test
```

### Tests

```bash
# Shell generator (unit + sync)
python3 .shellgen/tests/test_shell_generator.py
python3 .shellgen/tests/test_shell_sync.py

# Shell config validation
python3 .tests/test_zsh.py
python3 .tests/test_fish.py

# Package generator
python3 .pkgmgmt/tests/test_generator.py

# Bootstrap script
python3 .tests/test_bootstrap.py
```

### Testing in Containers

```bash
# Test on Debian (primary CI environment)
.pkgmgmt/test-environments/test-chezmoi.sh debian

# Other platforms: ubuntu, arch, fedora
.pkgmgmt/test-environments/test-chezmoi.sh <platform>
```

### Chezmoi Operations

```bash
chezmoi diff      # Preview changes
chezmoi apply     # Apply dotfiles
chezmoi update    # Pull and apply latest
```

## Architecture

### Shell Config Generator (.shellgen/)

`shell.yaml` + optional extra manifest files/directories → `generate_shell.py` →
Fish, Zsh, Bash, and PowerShell configs.

The generator is idempotent and produces matching configurations for all
four shells. It writes to the chezmoi source dir by default, or directly
to `~/.config` with `--target`. Directory sources expand to compatible
`.yaml`/`.yml` files in alphabetical order, and later manifests override
earlier ones when names collide.

### Package Management (.pkgmgmt/)

External `packages.yaml` (not in repo) → `generate_packages.py` →
platform-specific files written to a temp dir → installed immediately.

Set `packages.manifestPath` in chezmoi config to enable. If unset or
the file doesn't exist, package installation is skipped.

### Bootstrap (bootstrap.sh)

For machines where chezmoi can't be installed. Translates chezmoi naming
conventions (`dot_`, `private_`), renders `dot_gitconfig.tmpl`, runs the
shell generator in `--target` mode, and copies all config directories.
Requires Python 3 + PyYAML.

### Chezmoi Template Conventions

- `dot_` prefix → dotfile (e.g., `dot_config` → `.config`)
- `.tmpl` suffix → Go template processed by chezmoi
- `private_` prefix → 0600 permissions
- `_darwin`/`_linux` suffix → platform-specific files

### Shell Configuration Structure

**Fish** (`dot_config/fish/`): `config.fish` sources `conf.d/*.fish`, functions in `functions/`

**Zsh** (`dot_config/zsh/`): `.zshrc` sources `.zshrc.d/*.zsh`,
functions in `.zfunctions/`, plugins via Antidote (`.zsh_plugins.txt`)

**Bash** (`dot_config/bash/`): `dot_bashrc` sources `bashrc.d/*.bash`, functions in `functions/`

**PowerShell** (`dot_config/powershell/`): Profile sources `conf.d/*.ps1`, functions in `functions/`

All shells support local overrides not managed by chezmoi
(e.g., `.zshrc.local`, `config.local.fish`, `.bashrc.local`).

### Test Organization

- `.tests/` — Dotfiles validation (zsh/fish config, bootstrap)
- `.shellgen/tests/` — Shell generator unit + sync tests
- `.pkgmgmt/tests/` — Package generator unit tests

## CI/CD

Two GitHub Actions workflows:

**Dotfiles & Shell Tests** (`test-dotfiles.yml`): Runs on changes to
`.tests/`, `.shellgen/`, or shell config files.

**Package Management Tests** (`test-packages.yml`): Runs on changes to
`.pkgmgmt/` or `.chezmoiscripts/`. Includes generator unit tests and a
Debian Docker integration test for chezmoi initialization.

## Notes

This file is excluded from `chezmoi apply` via `.chezmoiignore.tmpl`.
