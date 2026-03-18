# AGENTS.md

This file provides guidance to coding agents when working with this repository.

## Overview

This is a chezmoi-managed dotfiles repository supporting macOS, Linux (Debian/Ubuntu, Arch, Fedora), and Windows (MSYS2). It features dual shell support (Fish with Tide, Zsh with Powerlevel10k), a shell config generator, and an optional package management system.

## Common Commands

### Shell Generation

```bash
# Edit the shell config manifest
vim .shellgen/shell.yaml

# Generate shell configs (to chezmoi source dir)
cd .shellgen && make generate

# Run shell generator tests
cd .shellgen && make test
```

### Shell Config Validation

```bash
# Run zsh config tests
python3 .tests/test_zsh.py

# Run fish config tests
python3 .tests/test_fish.py
```

### Package Management (optional)

Package installation runs during `chezmoi apply` when `packages.manifestPath` is set in
chezmoi config to a local `packages.yaml` (not stored in this repo).

```bash
# Run generator unit tests
cd .pkgmgmt && make test
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

Central manifest (`shell.yaml`) → Generator (`generate_shell.py`) → Shell-specific files for both Fish and Zsh.

The generator is idempotent and produces matching configurations for both shells from a single YAML source.

### Package Management System (.pkgmgmt/)

External `packages.yaml` (provided by user, not in repo) → `generate_packages.py --manifest <path> --output-dir <tmpdir>` → platform-specific files written to a temp directory → installed immediately.

Set `packages.manifestPath` in chezmoi config to enable. If unset or the file doesn't exist, package installation is skipped.

### Chezmoi Template Conventions

- `dot_` prefix → dotfile (e.g., `dot_config` → `.config`)
- `.tmpl` suffix → Go template processed by chezmoi
- `private_` prefix → 0600 permissions
- `_darwin`/`_linux` suffix → platform-specific files

### Shell Configuration Structure

**Fish** (`dot_config/fish/`): `config.fish` sources `conf.d/*.fish`, functions in `functions/`

**Zsh** (`dot_config/zsh/`): `.zshrc` sources `.zshrc.d/*.zsh`, functions in `.zfunctions/`, plugins via Antidote (`.zsh_plugins.txt`)

Both shells support local overrides: `config.local.fish` or `.zshrc.local` (not managed by chezmoi).

### Test Organization

- `.tests/` — Dotfiles validation (zsh/fish config structure, conventions)
- `.shellgen/tests/` — Shell generator unit + sync tests
- `.pkgmgmt/tests/` — Package generator unit tests

## CI/CD

Two GitHub Actions workflows:

**Dotfiles & Shell Tests** (`test-dotfiles.yml`): Runs on changes to `.tests/`, `.shellgen/`, or shell config files.

**Package Management Tests** (`test-packages.yml`): Runs on changes to `.pkgmgmt/` or `.chezmoiscripts/`. Includes generator unit tests and a Debian Docker integration test for chezmoi initialization.

## Notes

This file is excluded from `chezmoi apply` via `.chezmoiignore.tmpl`.
