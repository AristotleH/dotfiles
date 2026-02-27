#!/usr/bin/env python3
"""
Tests for shell entrypoint files that load generated Bash/PowerShell config.

Run with: python3 .tests/test_shell_entrypoints.py
"""

import sys
from pathlib import Path

REPO_ROOT = Path(__file__).parent.parent

BASHRC = REPO_ROOT / "dot_bashrc"
BASH_PROFILE = REPO_ROOT / "dot_bash_profile"
PWSH_PROFILE = REPO_ROOT / "dot_config" / "powershell" / "Microsoft.PowerShell_profile.ps1"
PWSH_WINDOWS_BRIDGE = (
    REPO_ROOT
    / "private_Documents"
    / "private_PowerShell"
    / "Microsoft.PowerShell_profile.ps1"
)


def test_bashrc_exists():
    assert BASHRC.is_file(), f"{BASHRC} not found"


def test_bashrc_loads_generated_functions_and_modules():
    content = BASHRC.read_text()
    assert "XDG_CONFIG_HOME" in content or ".config" in content
    assert "functions/*.bash" in content, "dot_bashrc should source generated functions"
    assert "bashrc.d/*.bash" in content, "dot_bashrc should source generated modules"
    assert ".bashrc.local" in content, "dot_bashrc should support local overrides"


def test_bash_profile_exists():
    assert BASH_PROFILE.is_file(), f"{BASH_PROFILE} not found"


def test_bash_profile_sources_bashrc():
    content = BASH_PROFILE.read_text()
    assert ".bashrc" in content, "dot_bash_profile should source .bashrc"


def test_pwsh_profile_exists():
    assert PWSH_PROFILE.is_file(), f"{PWSH_PROFILE} not found"


def test_pwsh_profile_loads_generated_functions_and_modules():
    content = PWSH_PROFILE.read_text()
    assert "functions" in content, "PowerShell profile should source functions/*.ps1"
    assert "conf.d" in content, "PowerShell profile should source conf.d/*.ps1"
    assert "profile.local.ps1" in content, "PowerShell profile should support local overrides"


def test_pwsh_windows_bridge_exists():
    assert PWSH_WINDOWS_BRIDGE.is_file(), f"{PWSH_WINDOWS_BRIDGE} not found"


def test_pwsh_windows_bridge_targets_xdg_profile():
    content = PWSH_WINDOWS_BRIDGE.read_text()
    assert "XDG_CONFIG_HOME" in content or ".config" in content
    assert "Microsoft.PowerShell_profile.ps1" in content


def run_all_tests():
    tests = [
        test_bashrc_exists,
        test_bashrc_loads_generated_functions_and_modules,
        test_bash_profile_exists,
        test_bash_profile_sources_bashrc,
        test_pwsh_profile_exists,
        test_pwsh_profile_loads_generated_functions_and_modules,
        test_pwsh_windows_bridge_exists,
        test_pwsh_windows_bridge_targets_xdg_profile,
    ]

    passed = 0
    failed = 0
    for test in tests:
        try:
            test()
            print(f"  PASS {test.__name__}")
            passed += 1
        except AssertionError as e:
            print(f"  FAIL {test.__name__}: {e}")
            failed += 1
        except Exception as e:
            print(f"  FAIL {test.__name__}: Unexpected error: {e}")
            failed += 1

    print(f"\n{passed} passed, {failed} failed")
    return 0 if failed == 0 else 1


if __name__ == "__main__":
    sys.exit(run_all_tests())
