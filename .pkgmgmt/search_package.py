#!/usr/bin/env python3
"""
Search for a package name across different platforms.

This is a helper tool to look up package names when adding to packages.yaml.
Usage: ./search-package.py <package-name>
"""

import sys
import subprocess


def search_homebrew(query: str):
    """Search Homebrew packages."""
    print("\n🍺 Homebrew (macOS)")
    print("=" * 50)
    try:
        result = subprocess.run(
            ["brew", "search", query],
            capture_output=True,
            text=True,
            timeout=10
        )
        if result.returncode == 0:
            print(result.stdout)
        else:
            print("brew command not available or search failed")
    except (subprocess.TimeoutExpired, FileNotFoundError):
        print("brew not installed or timed out")
    print(f"🔗 https://formulae.brew.sh/formula/{query}")


def search_apt(query: str):
    """Search APT packages."""
    print("\n📦 APT (Debian/Ubuntu)")
    print("=" * 50)
    try:
        result = subprocess.run(
            ["apt-cache", "search", f"^{query}"],
            capture_output=True,
            text=True,
            timeout=10
        )
        if result.returncode == 0 and result.stdout:
            all_lines = result.stdout.strip().split('\n')
            lines = all_lines[:5]
            for line in lines:
                print(line)
            if len(all_lines) > 5:
                remaining = len(all_lines) - 5
                print(f"... and {remaining} more")
        else:
            print("apt-cache not available or no results")
    except (subprocess.TimeoutExpired, FileNotFoundError):
        print("apt-cache not installed or timed out")
    print(f"🔗 https://packages.ubuntu.com/search?keywords={query}")


def search_pacman(query: str):
    """Search Pacman packages."""
    print("\n⚙️  Pacman (Arch Linux)")
    print("=" * 50)
    try:
        result = subprocess.run(
            ["pacman", "-Ss", f"^{query}"],
            capture_output=True,
            text=True,
            timeout=10
        )
        if result.returncode == 0 and result.stdout:
            lines = result.stdout.strip().split('\n')[:10]
            for line in lines:
                print(line)
        else:
            print("pacman not available or no results")
    except (subprocess.TimeoutExpired, FileNotFoundError):
        print("pacman not installed or timed out")
    print(f"🔗 https://archlinux.org/packages/?q={query}")


def search_msys2(query: str):
    """Show MSYS2 search info."""
    print("\n🪟 MSYS2 (Windows)")
    print("=" * 50)
    print("Search manually at:")
    print(f"🔗 https://packages.msys2.org/search?q={query}")
    print("\nUCRT packages (recommended): mingw-w64-ucrt-x86_64-{package}")


def search_dnf(query: str):
    """Search DNF packages."""
    print("\n🎩 DNF (Fedora/RHEL)")
    print("=" * 50)
    try:
        result = subprocess.run(
            ["dnf", "search", query],
            capture_output=True,
            text=True,
            timeout=10
        )
        if result.returncode == 0 and result.stdout:
            lines = result.stdout.strip().split('\n')[:10]
            for line in lines:
                print(line)
        else:
            print("dnf not available or no results")
    except (subprocess.TimeoutExpired, FileNotFoundError):
        print("dnf not installed or timed out")
    print(f"🔗 https://packages.fedoraproject.org/search?query={query}")


def show_example(package_name: str):
    """Show example YAML entry."""
    print("\n📝 Example packages.yaml entry:")
    print("=" * 50)
    print(f"""cli_tools:
  - name: {package_name}
    # Add description in comment if needed
    macos: {package_name}
    msys2: mingw-w64-ucrt-x86_64-{package_name}
    apt: {package_name}
    pacman: {package_name}
    dnf: {package_name}

# If not available on some platforms, use skip:
cli_tools:
  - name: {package_name}
    # Add description in comment if needed
    macos: {package_name}
    apt: {package_name}
    skip: [msys2, pacman, dnf]  # Not available on these
""")


def main():
    if len(sys.argv) < 2:
        print("Usage: ./search-package.py <package-name>")
        print("\nExample: ./search-package.py ripgrep")
        print("\nThis tool helps you find package names across different platforms")
        print("for adding to packages.yaml")
        return 1

    query = sys.argv[1]
    print(f"🔍 Searching for package: {query}")
    print("=" * 50)

    # Search all platforms
    search_homebrew(query)
    search_apt(query)
    search_pacman(query)
    search_dnf(query)
    search_msys2(query)

    # Show example entry
    show_example(query)

    # Show next steps
    print("\n📋 Next steps:")
    print("=" * 50)
    print("1. Add the package to packages.yaml")
    print("2. Run: ./generate-packages.py")
    print("3. Run: chezmoi apply")
    print("4. Run: install-packages")

    return 0


if __name__ == '__main__':
    exit(main())
