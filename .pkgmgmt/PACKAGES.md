# Cross-Platform Package Management

This chezmoi configuration includes a unified package management system that works across macOS, Windows (MSYS2), and various Linux distributions.

## Overview

Instead of maintaining separate package lists for each platform, you define packages once in `packages.yaml` and generate platform-specific files automatically.

### Supported Platforms

- **macOS**: Homebrew (formulas, casks, and Mac App Store via `mas`)
- **Windows**: MSYS2 (MinGW packages)
- **Linux**:
  - Debian/Ubuntu (APT)
  - Arch Linux (Pacman)
  - Fedora/RHEL (DNF)
  - Raspberry Pi OS (APT)

## Quick Start

### 1. Add a Package

Edit `packages.yaml` and add your package to the `cli_tools` section:

```yaml
cli_tools:
  - name: your-tool
    desc: Description of the tool
    macos: homebrew-name
    msys2: mingw-w64-x86_64-package-name
    apt: debian-package-name
    pacman: arch-package-name
    dnf: fedora-package-name
```

If a package isn't available on a platform, use `null` or add it to the `skip` list:

```yaml
cli_tools:
  - name: macos-only-tool
    desc: Only available on macOS
    macos: tool-name
    skip: [msys2, apt, pacman, dnf]
```

### 2. Generate Platform-Specific Files

From the chezmoi source directory:

```bash
cd ~/.local/share/chezmoi
./generate-packages.py
```

This creates:

- `dot_Brewfile_darwin` (macOS)
- `dot_config/private_packages-msys2.txt.tmpl` (Windows MSYS2)
- `dot_config/private_packages-apt.txt.tmpl` (Debian/Ubuntu)
- `dot_config/private_packages-pacman.txt.tmpl` (Arch Linux)
- `dot_config/private_packages-dnf.txt.tmpl` (Fedora/RHEL)
- `dot_config/private_packages-raspi.txt.tmpl` (Raspberry Pi)

### 3. Apply Changes

```bash
chezmoi apply
```

### 4. Install Packages

The universal installer automatically detects your platform:

```bash
install-packages
```

Or use platform-specific commands:

**macOS:**

```bash
brew bundle --file=~/.Brewfile
```

**MSYS2:**

```bash
pacman -S --needed $(cat ~/.config/packages-msys2.txt | grep -v '^#')
```

**Debian/Ubuntu:**

```bash
sudo apt-get install $(cat ~/.config/packages-apt.txt | grep -v '^#')
```

**Arch Linux:**

```bash
sudo pacman -S --needed $(cat ~/.config/packages-pacman.txt | grep -v '^#')
```

**Fedora/RHEL:**

```bash
sudo dnf install $(cat ~/.config/packages-dnf.txt | grep -v '^#')
```

## Package Manifest Structure

### CLI Tools

Cross-platform command-line tools that work on multiple platforms:

```yaml
cli_tools:
  - name: bat
    desc: Clone of cat with syntax highlighting
    macos: bat
    msys2: mingw-w64-x86_64-bat
    apt: bat
    pacman: bat
    dnf: bat
```

### macOS-Specific Applications

GUI apps, fonts, and services for macOS only:

```yaml
macos_apps:
  # Homebrew cask
  - name: visual-studio-code
    type: gui
    cask: visual-studio-code

  # Homebrew formula with options
  - name: ollama
    type: service
    brew: ollama
    brew_options: "restart_service: :changed"

  # Mac App Store app
  - name: xcode
    type: gui
    mas_id: 497799835

  # Font
  - name: jetbrains-mono
    type: font
    cask: font-jetbrains-mono
```

### Package Types

- `cli`: Command-line tools (default)
- `gui`: GUI applications
- `font`: Fonts
- `service`: Background services

## Platform-Specific Notes

### MSYS2 (Windows)

Most MinGW packages use the prefix `mingw-w64-x86_64-`:

```yaml
- name: ripgrep
  msys2: mingw-w64-x86_64-ripgrep
```

Some tools may need manual installation from GitHub releases.

### APT (Debian/Ubuntu)

Some modern tools need additional repositories:

```bash
# For eza (modern ls)
sudo apt install -y gpg
sudo mkdir -p /etc/apt/keyrings
wget -qO- https://raw.githubusercontent.com/eza-community/eza/main/deb.asc | sudo gpg --dearmor -o /etc/apt/keyrings/gierens.gpg
echo "deb [signed-by=/etc/apt/keyrings/gierens.gpg] http://deb.gierens.de stable main" | sudo tee /etc/apt/sources.list.d/gierens.list
sudo apt update
```

Note: On Ubuntu/Debian, `bat` is installed as `batcat` to avoid conflicts.

### Raspberry Pi OS

Use lightweight alternatives when possible. Some tools may need compilation from source.

## Workflow Examples

### Adding a New Tool Across All Platforms

1. Research package names for each platform
2. Add to `packages.yaml`:

```yaml
cli_tools:
  - name: jq
    desc: Command-line JSON processor
    macos: jq
    msys2: mingw-w64-x86_64-jq
    apt: jq
    pacman: jq
    dnf: jq
```

3. Regenerate files: `./generate-packages.py`
4. Review changes: `git diff`
5. Apply: `chezmoi apply`
6. Install: `install-packages`

### Adding a macOS-Only App

1. Add to `macos_apps` section in `packages.yaml`:

  ```yaml
  macos_apps:
    - name: my-mac-app
      type: gui
      cask: my-mac-app
  ```

2. Regenerate: `./generate-packages.py`
3. Apply: `chezmoi apply`
4. Install: `brew bundle --file=~/.Brewfile`

### Skipping a Package on Specific Platforms

Use the `skip` field:

```yaml
cli_tools:
  - name: special-tool
    desc: Not available everywhere
    macos: special-tool
    pacman: special-tool
    skip: [msys2, apt, dnf]  # Skip these platforms
```

## File Structure

```
~/.local/share/chezmoi/
├── packages.yaml                                    # Central manifest
├── generate-packages.py                                # Generator script
├── dot_Brewfile_darwin                             # Generated: macOS Brewfile
├── dot_config/
│   ├── private_packages-msys2.txt.tmpl            # Generated: MSYS2 packages
│   ├── private_packages-apt.txt.tmpl              # Generated: Debian/Ubuntu packages
│   ├── private_packages-pacman.txt.tmpl           # Generated: Arch packages
│   ├── private_packages-dnf.txt.tmpl              # Generated: Fedora packages
│   └── private_packages-raspi.txt.tmpl            # Generated: Raspberry Pi packages
└── dot_local/bin/
    └── executable_install-packages.tmpl           # Universal installer
```

## Tips

1. **Always regenerate** after editing `packages.yaml`:

   ```bash
   cd ~/.local/share/chezmoi && ./generate-packages.py
   ```

2. **Commit both** the manifest and generated files to track changes:

   ```bash
   git add packages.yaml dot_Brewfile_darwin dot_config/private_packages-*.txt.tmpl
   git commit -m "Add new package: tool-name"
   ```

3. **Platform-specific testing**: Test installation on each platform you use

4. **Manual installations**: Some tools may not be packaged everywhere. Document these in the `platform_notes` section of `packages.yaml`

5. **Keep it DRY**: Define once in `packages.yaml`, deploy everywhere

## Troubleshooting

### Generator script fails

Make sure you have Python 3 and PyYAML installed:

```bash
# macOS
brew install python3
pip3 install pyyaml

# Linux (apt)
sudo apt-get install python3 python3-pip
pip3 install pyyaml

# MSYS2
pacman -S mingw-w64-x86_64-python mingw-w64-x86_64-python-pip
pip install pyyaml
```

### Package not found on a platform

1. Check the package exists: search the platform's package repository
2. Use the correct package name (may differ from other platforms)
3. If unavailable, add to `skip` list or use `null`

### Install script doesn't detect platform

Check your platform detection in [.chezmoi.toml.tmpl](.chezmoi.toml.tmpl#L12-L25)

## Future Enhancements

Possible improvements to this system:

- [ ] Automatic package name lookup/translation
- [ ] Conflict resolution for duplicate packages
- [ ] Dependency management
- [ ] Version pinning support
- [ ] Automated testing on multiple platforms
- [ ] Integration with chezmoi's `runOnce` scripts
- [ ] Support for additional package managers (Nix, Snap, Flatpak)
