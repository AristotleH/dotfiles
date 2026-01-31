# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Overview

This is a chezmoi-managed dotfiles repository supporting macOS, Linux (Debian/Ubuntu, Arch, Fedora), and Windows (MSYS2). It features a unified package management system and dual shell support (Fish with Tide, Zsh with Powerlevel10k).

## Common Commands

### Package Management

```bash
# Edit the central package manifest
vim .pkgmgmt/packages.yaml

# Generate platform-specific package files
cd .pkgmgmt && make generate

# Run all tests (unit + sync check)
cd .pkgmgmt && make test

# Quick sync check before commit
cd .pkgmgmt && make check

# Search for package names across platforms
.pkgmgmt/search_package.py <package-name>
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

### Package Management System (.pkgmgmt/)

Central manifest (`packages.yaml`) → Generator (`generate_packages.py`) → Platform-specific files:
- `dot_config/Brewfile_darwin` (macOS Homebrew)
- `dot_config/packages-*.txt.tmpl` (Linux/Windows)

The generator is idempotent. Always commit both `packages.yaml` and generated files together.

### Chezmoi Template Conventions

- `dot_` prefix → dotfile (e.g., `dot_config` → `.config`)
- `.tmpl` suffix → Go template processed by chezmoi
- `private_` prefix → 0600 permissions
- `_darwin`/`_linux` suffix → platform-specific files

### Shell Configuration Structure

**Fish** (`dot_config/fish/`): `config.fish` sources `conf.d/*.fish`, functions in `functions/`

**Zsh** (`dot_config/zsh/`): `.zshrc` sources `.zshrc.d/*.zsh`, functions in `.zfunctions/`, plugins via Antidote (`.zsh_plugins.txt`)

Both shells support local overrides: `config.local.fish` or `.zshrc.local` (not managed by chezmoi).

## CI/CD

GitHub Actions runs on changes to `.pkgmgmt/`, `dot_config/zsh/`, or package files:
1. Unit tests (Python)
2. Sync check (generated files match manifest)
3. Integration test (Debian Docker with chezmoi init)
4. macOS Brewfile validation (main branch only)

## Notes

This file is excluded from `chezmoi apply` via `.chezmoiignore.tmpl`.
