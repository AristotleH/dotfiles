# Package Management System

This directory contains the cross-platform package management system for the dotfiles repository.

## Quick Start

```bash
# Edit package manifest
vim packages.yaml

# Generate platform-specific files
make generate

# Run tests
make test

# Check if files are in sync (before committing)
make check
```

## Files

- **packages.yaml** - Central package manifest (edit this!)
- **generate_packages.py** - Generator script
- **search_package.py** - Helper to search package names
- **tests/** - Test suite
- **Makefile** - Convenient commands
- **PACKAGES.md** - Complete documentation
- **PACKAGES-QUICKREF.md** - Quick reference

## Documentation

- See [PACKAGES.md](PACKAGES.md) for complete documentation
- See [PACKAGES-QUICKREF.md](PACKAGES-QUICKREF.md) for quick reference
- Run `make workflow` to see typical workflow

## Testing

Tests automatically run in GitHub Actions on push/PR.

Run locally:

```bash
make test           # All tests
make test-unit      # Unit tests only
make test-sync      # Check files are in sync
```

## Generated Files

The generator creates these files in the parent directory:

- `../dot_Brewfile_darwin` - macOS Homebrew packages
- `../dot_config/packages-*.txt.tmpl` - Linux/Windows packages

These generated files **should be committed** to the repository.

## Workflow

1. Edit `packages.yaml`
2. Run `make generate`
3. Run `make test` to validate
4. Review with `git diff`
5. Commit both manifest and generated files
6. Apply with `chezmoi apply`
7. Install with `install-packages`

See `make help` for all available commands.
