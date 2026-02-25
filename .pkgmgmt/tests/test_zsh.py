#!/usr/bin/env python3
"""
Tests for zsh configuration files.

Validates syntax, load order, structure, and absence of dead code
in the chezmoi-managed zsh config.

Run with: python3 tests/test_zsh.py
"""

import re
import subprocess
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).parent.parent.parent
ZSH_DIR = REPO_ROOT / "dot_config" / "zsh"
ZSHRC = ZSH_DIR / "dot_zshrc"
ZSHRC_D = ZSH_DIR / "dot_zshrc.d"

# Expected numeric prefix pattern: NN-name.zsh
NUMBERED_RE = re.compile(r"^\d{2}-.+\.zsh$")


def test_zshrc_exists():
    """dot_zshrc must exist."""
    assert ZSHRC.is_file(), f"{ZSHRC} not found"


def test_zshrc_d_exists():
    """dot_zshrc.d directory must exist."""
    assert ZSHRC_D.is_dir(), f"{ZSHRC_D} not found"


def test_zshrc_d_files_are_numbered():
    """Every .zsh file in .zshrc.d/ must have a NN- numeric prefix."""
    zsh_files = sorted(ZSHRC_D.glob("*.zsh"))
    assert zsh_files, f"No .zsh files found in {ZSHRC_D}"

    unnumbered = [f.name for f in zsh_files if not NUMBERED_RE.match(f.name)]
    assert not unnumbered, (
        f"Files missing numeric prefix: {unnumbered}\n"
        f"Expected pattern: NN-name.zsh (e.g., 00-options.zsh)"
    )


def test_no_duplicate_prefixes():
    """Each numeric prefix in .zshrc.d/ must be unique."""
    zsh_files = sorted(ZSHRC_D.glob("*.zsh"))
    prefixes = {}
    for f in zsh_files:
        match = re.match(r"^(\d{2})-", f.name)
        if match:
            prefix = match.group(1)
            prefixes.setdefault(prefix, []).append(f.name)

    dupes = {k: v for k, v in prefixes.items() if len(v) > 1}
    assert not dupes, f"Duplicate load-order prefixes: {dupes}"


def test_load_order_is_monotonic():
    """Files should have strictly increasing numeric prefixes."""
    zsh_files = sorted(ZSHRC_D.glob("*.zsh"))
    numbers = []
    for f in zsh_files:
        match = re.match(r"^(\d{2})-", f.name)
        if match:
            numbers.append((int(match.group(1)), f.name))

    for i in range(1, len(numbers)):
        prev_num, prev_name = numbers[i - 1]
        curr_num, curr_name = numbers[i]
        assert curr_num > prev_num, (
            f"Load order not monotonic: {prev_name} ({prev_num}) "
            f"comes before {curr_name} ({curr_num})"
        )


def test_no_dead_files():
    """No .zsh file should be entirely commented out (dead code)."""
    for f in ZSHRC_D.glob("*.zsh"):
        lines = f.read_text().splitlines()
        code_lines = [
            l for l in lines
            if l.strip() and not l.strip().startswith("#")
        ]
        assert code_lines, (
            f"{f.name} is entirely comments/blank — dead file, should be deleted"
        )


def test_zsh_syntax():
    """All .zsh files must pass zsh -n syntax check."""
    result = subprocess.run(["zsh", "--version"], capture_output=True, text=True)
    if result.returncode != 0:
        print("SKIP: zsh not available")
        return

    all_files = [ZSHRC] + sorted(ZSHRC_D.glob("*.zsh"))
    errors = []
    for f in all_files:
        result = subprocess.run(
            ["zsh", "-n", str(f)],
            capture_output=True,
            text=True,
        )
        if result.returncode != 0:
            errors.append(f"{f.name}: {result.stderr.strip()}")

    assert not errors, "Syntax errors:\n" + "\n".join(errors)


def test_zshrc_sources_zshrc_d():
    """dot_zshrc must have the glob loop that sources .zshrc.d/*.zsh."""
    content = ZSHRC.read_text()
    assert ".zshrc.d/*.zsh" in content, (
        "dot_zshrc missing .zshrc.d/*.zsh sourcing loop"
    )


def test_zshrc_pre_plugin_zstyles():
    """Autocomplete zstyles must appear before antidote load."""
    content = ZSHRC.read_text()
    zstyle_pos = content.find("zstyle ':autocomplete:")
    load_pos = content.find("antidote load")
    assert zstyle_pos != -1, "Missing pre-plugin autocomplete zstyles"
    assert load_pos != -1, "Missing antidote load"
    assert zstyle_pos < load_pos, (
        "autocomplete zstyles must come BEFORE antidote load"
    )


def run_all_tests():
    """Run all tests manually (for systems without pytest)."""
    tests = [
        test_zshrc_exists,
        test_zshrc_d_exists,
        test_zshrc_d_files_are_numbered,
        test_no_duplicate_prefixes,
        test_load_order_is_monotonic,
        test_no_dead_files,
        test_zsh_syntax,
        test_zshrc_sources_zshrc_d,
        test_zshrc_pre_plugin_zstyles,
    ]

    passed = 0
    failed = 0

    for test in tests:
        try:
            test()
            print(f"  \u2713 {test.__name__}")
            passed += 1
        except AssertionError as e:
            print(f"  \u2717 {test.__name__}: {e}")
            failed += 1
        except Exception as e:
            print(f"  \u2717 {test.__name__}: Unexpected error: {e}")
            failed += 1

    print(f"\n{passed} passed, {failed} failed")
    return 0 if failed == 0 else 1


if __name__ == "__main__":
    sys.exit(run_all_tests())
