# Package Management Quick Reference

## Adding a New Package

### 1. Edit the Manifest

```bash
cd ~/.local/share/chezmoi
$EDITOR packages.yaml
```

Add to `cli_tools` section:

```yaml
- name: tool-name
  desc: Brief description
  macos: brew-package-name
  msys2: mingw-w64-x86_64-package-name
  apt: debian-package-name
  pacman: arch-package-name
  dnf: fedora-package-name
```

### 2. Generate Platform Files

```bash
./generate-packages.py
```

### 3. Review Changes

```bash
git diff
```

### 4. Apply to System

```bash
chezmoi apply
```

### 5. Install New Package

```bash
install-packages
```

## Common Tasks

### Add macOS-only GUI app

In `packages.yaml` under `macos_apps`:

```yaml
- name: app-name
  type: gui
  cask: cask-name
```

### Add Mac App Store app

Use the proper display name (with correct capitalization):

```yaml
- name: Proper App Name
  type: gui
  mas_id: 123456789
```

### Skip a platform

```yaml
- name: tool-name
  macos: tool
  apt: tool
  skip: [msys2, dnf]  # Not available here
```

### Platform not available

Use `null`:

```yaml
- name: tool-name
  macos: tool
  msys2: null  # Not available
```

## Platform-Specific Package Names

### MSYS2

UCRT packages (modern standard): `mingw-w64-ucrt-x86_64-PACKAGE`

### Debian/Ubuntu (APT)

- `bat` package → `batcat` command
- Modern tools may need extra repos

### Package Lookup

- **Homebrew**: <https://formulae.brew.sh>
- **MSYS2**: <https://packages.msys2.org>
- **Debian**: <https://packages.debian.org>
- **Ubuntu**: <https://packages.ubuntu.com>
- **Arch**: <https://archlinux.org/packages>
- **Fedora**: <https://packages.fedoraproject.org>

## Files

| File                                             | Purpose                           |
| ------------------------------------------------ | --------------------------------- |
| `packages.yaml`                                  | Single source of truth            |
| `generate-packages.py`                           | Generator script                  |
| `dot_Brewfile_darwin`                            | Generated: macOS Brewfile         |
| `dot_config/private_packages-*.txt.tmpl`         | Generated: Linux/Windows packages |
| `dot_local/bin/executable_install-packages.tmpl` | Universal installer               |

## Workflow

```text
Edit packages.yaml
     ↓
./generate-packages.py
     ↓
Review with git diff
     ↓
Commit changes
     ↓
chezmoi apply
     ↓
install-packages
```

## Remember

- **Always regenerate** after editing `packages.yaml`
- **Commit both** manifest and generated files
- **Test** on each platform you use
- See [PACKAGES.md](PACKAGES.md) for full documentation
