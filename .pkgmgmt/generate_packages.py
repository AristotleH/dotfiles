#!/usr/bin/env python3
"""
Generate platform-specific package files from packages.yaml

Run this script from the chezmoi source directory to regenerate
all platform-specific package lists.
"""

import yaml
from pathlib import Path
from typing import Dict, Any


def should_skip(pkg: Dict[str, Any], platform: str) -> bool:
    """Check if package should be skipped for this platform."""
    skip_list = pkg.get('skip', [])
    return platform in skip_list


def get_package_name(pkg: Dict[str, Any], platform: str) -> str:
    """Get package name for a platform, using 'pkg' as fallback."""
    # First check platform-specific field
    platform_pkg = pkg.get(platform)
    if platform_pkg and platform_pkg not in (None, 'null'):
        return platform_pkg

    # Fall back to 'pkg' shorthand
    pkg_shorthand = pkg.get('pkg')
    if pkg_shorthand and pkg_shorthand not in (None, 'null'):
        return pkg_shorthand

    return None


def generate_brewfile(manifest: Dict) -> str:
    """Generate Brewfile for macOS."""
    lines = []
    lines.append('tap "homebrew/bundle"')
    lines.append('tap "homebrew/services"')

    # CLI tools
    cli_tools = manifest.get('cli_tools', [])
    for pkg in cli_tools:
        if should_skip(pkg, 'macos'):
            continue

        macos_name = get_package_name(pkg, 'macos')
        if macos_name:
            lines.append(f'brew "{macos_name}"')

    # macOS-specific apps
    macos_apps = manifest.get('macos_apps', [])

    # Group by type
    brews = []
    casks = []
    mas_apps = []

    for app in macos_apps:
        if 'brew' in app:
            brew_line = f'brew "{app["brew"]}"'
            if 'brew_options' in app:
                brew_line += f', {app["brew_options"]}'
            brews.append(brew_line)
        elif 'cask' in app:
            casks.append(f'cask "{app["cask"]}"')
        elif 'mas_id' in app:
            # Use the name directly from YAML (already properly formatted)
            mas_apps.append(f'mas "{app["name"]}", id: {app["mas_id"]}')

    lines.extend(brews)
    lines.extend(casks)
    lines.extend(mas_apps)

    return '\n'.join(lines) + '\n'


def generate_package_list(manifest: Dict, platform: str) -> str:
    """Generate simple package list for apt, pacman, dnf, etc."""
    # Raspberry Pi uses APT packages
    platform_display = platform
    lookup_platform = 'apt' if platform == 'raspi' else platform

    lines = [f"# Generated package list for {platform_display}"]
    lines.append("# Generated from packages.yaml")
    lines.append("#")
    lines.append("# Install with:")

    if platform == 'msys2':
        lines.append("#   pacman -S --needed $(cat packages-msys2.txt | grep -v '^#')")
    elif platform in ('apt', 'raspi'):
        filename = f"packages-{platform}.txt"
        lines.append(f"#   sudo apt-get install $(cat {filename} | grep -v '^#')")
    elif platform == 'pacman':
        lines.append("#   sudo pacman -S --needed $(cat packages-pacman.txt | grep -v '^#')")
    elif platform == 'dnf':
        lines.append("#   sudo dnf install $(cat packages-dnf.txt | grep -v '^#')")

    lines.append("")

    cli_tools = manifest.get('cli_tools', [])
    packages = []

    for pkg in cli_tools:
        if should_skip(pkg, lookup_platform):
            continue

        # Raspberry Pi uses apt package names
        pkg_name = get_package_name(pkg, lookup_platform)
        if pkg_name:
            packages.append(pkg_name)

    lines.extend(packages)
    return '\n'.join(lines) + '\n'


def main():
    script_dir = Path(__file__).parent
    repo_root = script_dir.parent  # Go up from .pkgmgmt to repo root
    manifest_path = script_dir / 'packages.yaml'

    if not manifest_path.exists():
        print(f"Error: packages.yaml not found at {manifest_path}")
        return 1

    print(f"Reading manifest from {manifest_path}")
    with open(manifest_path) as f:
        manifest = yaml.safe_load(f)

    # Generate Brewfile in dot_config
    brewfile_path = repo_root / 'dot_config' / 'Brewfile_darwin'
    with open(brewfile_path, 'w') as f:
        f.write(generate_brewfile(manifest))
    print(f"✓ Generated {brewfile_path}")

    # Generate package lists for other platforms
    platforms = {
        'msys2': 'dot_config/packages-msys2.txt.tmpl',
        'apt': 'dot_config/packages-apt.txt.tmpl',
        'pacman': 'dot_config/packages-pacman.txt.tmpl',
        'dnf': 'dot_config/packages-dnf.txt.tmpl',
        'raspi': 'dot_config/packages-raspi.txt.tmpl',
    }

    for platform, template_path in platforms.items():
        output_path = repo_root / template_path
        output_path.parent.mkdir(parents=True, exist_ok=True)
        with open(output_path, 'w') as f:
            f.write(generate_package_list(manifest, platform))
        print(f"✓ Generated {output_path}")

    print("\n✅ All package lists generated successfully!")
    print("\nNext steps:")
    print("1. Review the generated files")
    print("2. Run 'chezmoi apply' to update your dotfiles")
    print("3. Use platform-specific commands to install packages")

    return 0


if __name__ == '__main__':
    exit(main())
