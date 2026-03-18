# Package Management

This directory contains the cross-platform package installer for the dotfiles repository.

Packages are defined in an external `packages.yaml` on each machine (not stored in this repo)
and installed automatically during `chezmoi apply` when `packages.manifestPath` is configured.

## Files

- **generate_packages.py** - Generates platform-specific package lists from a `packages.yaml`
- **tests/** - Unit tests for the generator
- **test-environments/** - Docker environments for integration testing
- **Makefile** - Convenient commands

## Usage

Set `packages.manifestPath` in your chezmoi config, then run `chezmoi apply`:

```toml
# ~/.config/chezmoi/chezmoi.toml
[data.packages]
  manifestPath = "/path/to/your/packages.yaml"
```

The generator is invoked automatically by the chezmoi install script. You can also run it
manually:

```bash
python3 generate_packages.py --manifest /path/to/packages.yaml --output-dir /tmp/pkgs
```

## Testing

```bash
make test
```
