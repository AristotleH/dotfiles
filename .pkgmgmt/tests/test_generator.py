#!/usr/bin/env python3
"""
Test suite for the package generator.

Run with: python3 -m pytest tests/
Or: python3 tests/test_generator.py
"""

import sys
import yaml
from pathlib import Path

# Add parent directory to path to import the generator
sys.path.insert(0, str(Path(__file__).parent.parent))
from generate_packages import (
    should_skip,
    generate_brewfile,
    generate_package_list
)


def test_should_skip():
    """Test the skip logic."""
    # Package with skip list
    pkg = {'name': 'test', 'skip': ['msys2', 'apt']}
    assert should_skip(pkg, 'msys2') == True
    assert should_skip(pkg, 'apt') == True
    assert should_skip(pkg, 'macos') == False

    # Package without skip list
    pkg = {'name': 'test'}
    assert should_skip(pkg, 'msys2') == False


def test_generate_brewfile_basic():
    """Test basic Brewfile generation."""
    manifest = {
        'cli_tools': [
            {
                'name': 'test-tool',
                'macos': 'test-tool'
            }
        ],
        'macos_apps': []
    }

    result = generate_brewfile(manifest)
    assert 'tap "homebrew/bundle"' in result
    assert 'brew "test-tool"' in result


def test_generate_brewfile_with_cask():
    """Test Brewfile generation with casks."""
    manifest = {
        'cli_tools': [],
        'macos_apps': [
            {
                'name': 'test-app',
                'type': 'gui',
                'cask': 'test-app'
            }
        ]
    }

    result = generate_brewfile(manifest)
    assert 'cask "test-app"' in result


def test_generate_brewfile_with_mas():
    """Test Brewfile generation with Mac App Store apps."""
    manifest = {
        'cli_tools': [],
        'macos_apps': [
            {
                'name': 'Test App',
                'type': 'gui',
                'mas_id': 123456
            }
        ]
    }

    result = generate_brewfile(manifest)
    assert 'mas "Test App", id: 123456' in result


def test_generate_brewfile_with_skip():
    """Test Brewfile generation with skipped packages."""
    manifest = {
        'cli_tools': [
            {
                'name': 'linux-only',
                'macos': 'linux-only',
                'skip': ['macos']
            }
        ],
        'macos_apps': []
    }

    result = generate_brewfile(manifest)
    assert 'linux-only' not in result


def test_generate_package_list_apt():
    """Test APT package list generation."""
    manifest = {
        'cli_tools': [
            {
                'name': 'test',
                'apt': 'test-package'
            }
        ]
    }

    result = generate_package_list(manifest, 'apt')
    assert '# Generated package list for apt' in result
    assert 'test-package' in result
    assert 'sudo apt-get install' in result


def test_generate_package_list_raspi():
    """Test Raspberry Pi package list generation (should use apt packages)."""
    manifest = {
        'cli_tools': [
            {
                'name': 'test',
                'apt': 'test-package'
            }
        ]
    }

    result = generate_package_list(manifest, 'raspi')
    assert '# Generated package list for raspi' in result
    assert 'test-package' in result
    assert 'packages-raspi.txt' in result


def test_generate_package_list_msys2():
    """Test MSYS2 package list generation."""
    manifest = {
        'cli_tools': [
            {
                'name': 'test',
                'msys2': 'mingw-w64-ucrt-x86_64-test'
            }
        ]
    }

    result = generate_package_list(manifest, 'msys2')
    assert 'mingw-w64-ucrt-x86_64-test' in result
    assert 'pacman -S --needed' in result


def test_null_package_handling():
    """Test that null packages are properly skipped."""
    manifest = {
        'cli_tools': [
            {
                'name': 'test',
                'macos': 'test',
                'apt': None
            }
        ]
    }

    result = generate_package_list(manifest, 'apt')
    assert 'test' not in result.split('\n')[5:]  # Skip header lines


def test_ucrt_packages():
    """Test that UCRT packages are correctly formatted."""
    manifest = {
        'cli_tools': [
            {
                'name': 'ripgrep',
                'msys2': 'mingw-w64-ucrt-x86_64-ripgrep'
            }
        ]
    }

    result = generate_package_list(manifest, 'msys2')
    assert 'mingw-w64-ucrt-x86_64-ripgrep' in result
    assert 'mingw-w64-x86_64-' not in result  # Old prefix shouldn't appear


def test_pkg_shorthand():
    """Test that 'pkg' shorthand works for all platforms."""
    manifest = {
        'cli_tools': [
            {
                'name': 'fish',
                'pkg': 'fish'
            }
        ]
    }

    # Test Brewfile generation
    result = generate_brewfile(manifest)
    assert 'brew "fish"' in result

    # Test all package list formats
    for platform in ['apt', 'msys2', 'pacman', 'dnf', 'raspi']:
        result = generate_package_list(manifest, platform)
        assert 'fish' in result


def test_pkg_shorthand_with_override():
    """Test that platform-specific fields override 'pkg' shorthand."""
    manifest = {
        'cli_tools': [
            {
                'name': 'neovim',
                'pkg': 'neovim',
                'msys2': 'mingw-w64-ucrt-x86_64-neovim'
            }
        ]
    }

    # Test Brewfile uses shorthand
    result = generate_brewfile(manifest)
    assert 'brew "neovim"' in result

    # Test MSYS2 uses override
    result = generate_package_list(manifest, 'msys2')
    assert 'mingw-w64-ucrt-x86_64-neovim' in result
    assert 'brew "neovim"' not in result  # Wrong format shouldn't appear

    # Test APT uses shorthand
    result = generate_package_list(manifest, 'apt')
    assert 'neovim' in result
    assert 'mingw-w64-ucrt-x86_64-neovim' not in result  # Override shouldn't appear


def run_all_tests():
    """Run all tests manually (for systems without pytest)."""
    tests = [
        test_should_skip,
        test_generate_brewfile_basic,
        test_generate_brewfile_with_cask,
        test_generate_brewfile_with_mas,
        test_generate_brewfile_with_skip,
        test_generate_package_list_apt,
        test_generate_package_list_raspi,
        test_generate_package_list_msys2,
        test_null_package_handling,
        test_ucrt_packages,
        test_pkg_shorthand,
        test_pkg_shorthand_with_override,
    ]

    passed = 0
    failed = 0

    for test in tests:
        try:
            test()
            print(f"✓ {test.__name__}")
            passed += 1
        except AssertionError as e:
            print(f"✗ {test.__name__}: {e}")
            failed += 1
        except Exception as e:
            print(f"✗ {test.__name__}: Unexpected error: {e}")
            failed += 1

    print(f"\n{passed} passed, {failed} failed")
    return 0 if failed == 0 else 1


if __name__ == '__main__':
    sys.exit(run_all_tests())
