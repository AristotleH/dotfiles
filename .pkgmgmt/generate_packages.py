#!/usr/bin/env python3
"""
Generate platform-specific package files from an external packages.yaml.

Usage:
    generate_packages.py --manifest /path/to/packages.yaml --output-dir /tmp/pkgs
"""

import argparse
import yaml
from pathlib import Path
from typing import Dict, Any


def should_skip(pkg: Dict[str, Any], platform: str) -> bool:
    return platform in pkg.get('skip', [])


def get_package_name(pkg: Dict[str, Any], platform: str) -> str:
    platform_pkg = pkg.get(platform)
    if platform_pkg and platform_pkg not in (None, 'null'):
        return platform_pkg
    pkg_shorthand = pkg.get('pkg')
    if pkg_shorthand and pkg_shorthand not in (None, 'null'):
        return pkg_shorthand
    return None


def generate_brewfile(manifest: Dict) -> str:
    lines = ['tap "homebrew/bundle"', 'tap "homebrew/services"']

    for pkg in manifest.get('cli_tools', []):
        if should_skip(pkg, 'macos'):
            continue
        name = get_package_name(pkg, 'macos')
        if name:
            lines.append(f'brew "{name}"')

    for app in manifest.get('macos_apps', []):
        if 'brew' in app:
            line = f'brew "{app["brew"]}"'
            if 'brew_options' in app:
                line += f', {app["brew_options"]}'
            lines.append(line)
        elif 'cask' in app:
            lines.append(f'cask "{app["cask"]}"')
        elif 'mas_id' in app:
            lines.append(f'mas "{app["name"]}", id: {app["mas_id"]}')

    return '\n'.join(lines) + '\n'


def generate_package_list(manifest: Dict, platform: str) -> str:
    lookup = 'apt' if platform == 'raspi' else platform

    install_cmd = {
        'msys2':  "#   pacman -S --needed $(cat packages-msys2.txt | grep -v '^#')",
        'apt':    "#   sudo apt-get install $(cat packages-apt.txt | grep -v '^#')",
        'raspi':  "#   sudo apt-get install $(cat packages-raspi.txt | grep -v '^#')",
        'pacman': "#   sudo pacman -S --needed $(cat packages-pacman.txt | grep -v '^#')",
        'dnf':    "#   sudo dnf install $(cat packages-dnf.txt | grep -v '^#')",
    }

    lines = [
        f"# Generated package list for {platform}",
        "#",
        "# Install with:",
        install_cmd[platform],
        "",
    ]

    for pkg in manifest.get('cli_tools', []):
        if should_skip(pkg, lookup):
            continue
        name = get_package_name(pkg, lookup)
        if name:
            lines.append(name)

    return '\n'.join(lines) + '\n'


def main():
    parser = argparse.ArgumentParser(description="Generate platform package lists from packages.yaml")
    parser.add_argument('--manifest', required=True, help='Path to packages.yaml')
    parser.add_argument('--output-dir', required=True, help='Directory to write generated files into')
    args = parser.parse_args()

    manifest_path = Path(args.manifest)
    output_dir = Path(args.output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    with open(manifest_path) as f:
        manifest = yaml.safe_load(f)

    outputs = {
        'Brewfile':           generate_brewfile(manifest),
        'packages-apt.txt':   generate_package_list(manifest, 'apt'),
        'packages-pacman.txt': generate_package_list(manifest, 'pacman'),
        'packages-dnf.txt':   generate_package_list(manifest, 'dnf'),
        'packages-msys2.txt': generate_package_list(manifest, 'msys2'),
        'packages-raspi.txt': generate_package_list(manifest, 'raspi'),
    }

    for filename, content in outputs.items():
        path = output_dir / filename
        path.write_text(content)
        print(f"Generated {path}")


if __name__ == '__main__':
    main()
