#!/usr/bin/env python3
"""
Tests for fish shell configuration files.

Validates structure, conventions, and absence of common pitfalls
in the chezmoi-managed fish config.

Run with: python3 tests/test_fish.py
"""

import re
import subprocess
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).parent.parent.parent
FISH_DIR = REPO_ROOT / "dot_config" / "fish"
CONFIG_FISH = FISH_DIR / "config.fish"
CONF_D = FISH_DIR / "conf.d"
FUNCTIONS_DIR = FISH_DIR / "functions"
FISH_PLUGINS = FISH_DIR / "fish_plugins"


def test_config_fish_exists():
    """config.fish must exist."""
    assert CONFIG_FISH.is_file(), f"{CONFIG_FISH} not found"


def test_config_fish_has_interactive_guard():
    """Interactive code in config.fish must be inside 'status is-interactive'."""
    content = CONFIG_FISH.read_text()
    assert "status is-interactive" in content, (
        "config.fish should guard interactive code with 'status is-interactive'"
    )


def test_config_fish_supports_local_override():
    """config.fish must source config.local.fish if it exists."""
    content = CONFIG_FISH.read_text()
    assert "config.local.fish" in content, (
        "config.fish missing local override support (config.local.fish)"
    )


def test_conf_d_exists():
    """conf.d directory must exist."""
    assert CONF_D.is_dir(), f"{CONF_D} not found"


def test_functions_dir_exists():
    """functions directory must exist."""
    assert FUNCTIONS_DIR.is_dir(), f"{FUNCTIONS_DIR} not found"


def test_fish_plugins_exists():
    """fish_plugins must exist (fisher plugin list)."""
    assert FISH_PLUGINS.is_file(), f"{FISH_PLUGINS} not found"


def test_fish_plugins_has_fisher():
    """fish_plugins must include the fisher plugin manager."""
    content = FISH_PLUGINS.read_text()
    assert "jorgebucaran/fisher" in content, (
        "fish_plugins missing jorgebucaran/fisher (plugin manager)"
    )


def test_fish_plugins_has_tide():
    """fish_plugins must include the tide prompt."""
    content = FISH_PLUGINS.read_text()
    assert "ilancosman/tide" in content, (
        "fish_plugins missing ilancosman/tide (prompt theme)"
    )


def test_fish_plugins_no_blank_lines():
    """fish_plugins should not have blank lines (fisher convention)."""
    lines = FISH_PLUGINS.read_text().splitlines()
    blank = [i + 1 for i, l in enumerate(lines) if not l.strip()]
    assert not blank, f"fish_plugins has blank lines at: {blank}"


def test_conf_d_hand_managed_files_have_shebang():
    """Hand-managed .fish files in conf.d/ should start with a shebang."""
    gitignore = (CONF_D / ".gitignore").read_text() if (CONF_D / ".gitignore").exists() else ""
    generated = {l.strip() for l in gitignore.splitlines()
                 if l.strip() and not l.strip().startswith("#")}

    fish_files = sorted(CONF_D.glob("*.fish"))
    missing = []
    for f in fish_files:
        if f.name in generated:
            continue
        first_line = f.read_text().splitlines()[0] if f.read_text().strip() else ""
        if not first_line.startswith("#!"):
            missing.append(f.name)

    assert not missing, (
        f"conf.d files missing shebang (#!/usr/bin/env fish): {missing}"
    )


def test_env_fish_disables_greeting():
    """Fish greeting should be disabled."""
    env_file = CONF_D / "0_env.fish"
    if not env_file.exists():
        return
    content = env_file.read_text()
    assert "fish_greeting" in content, (
        "0_env.fish should disable the fish greeting (set fish_greeting)"
    )


def test_brew_fish_handles_all_platforms():
    """brew.fish should detect homebrew on Linux, macOS ARM, and macOS Intel."""
    brew_file = CONF_D / "brew.fish"
    if not brew_file.exists():
        return
    content = brew_file.read_text()
    assert "/home/linuxbrew" in content, "brew.fish missing Linux homebrew path"
    assert "/opt/homebrew" in content, "brew.fish missing macOS ARM homebrew path"
    assert "/usr/local" in content, "brew.fish missing macOS Intel homebrew path"


def test_brew_fish_has_early_return():
    """brew.fish should return early if homebrew is not installed."""
    brew_file = CONF_D / "brew.fish"
    if not brew_file.exists():
        return
    content = brew_file.read_text()
    assert "return" in content, (
        "brew.fish should 'return 0' when homebrew is not installed"
    )


def test_no_universal_vars_in_conf_d():
    """conf.d files should prefer -g (global) over -U (universal) for set commands.

    Universal vars persist across sessions and can cause surprising behavior
    when managed by config files. Use -g instead.
    """
    gitignore = (CONF_D / ".gitignore").read_text() if (CONF_D / ".gitignore").exists() else ""
    generated = {l.strip() for l in gitignore.splitlines()
                 if l.strip() and not l.strip().startswith("#")}

    violations = []
    for f in sorted(CONF_D.glob("*.fish")):
        if f.name in generated:
            continue
        for i, line in enumerate(f.read_text().splitlines(), 1):
            stripped = line.strip()
            if stripped.startswith("#"):
                continue
            # Match 'set -U' or 'set -gxU' etc. but not inside comments
            if re.search(r'\bset\b.*\s-\w*U', stripped):
                violations.append(f"{f.name}:{i}: {stripped}")

    assert not violations, (
        "conf.d files should use 'set -g' not 'set -U' (universal vars):\n"
        + "\n".join(violations)
    )


def test_fish_syntax():
    """All .fish files must pass fish --no-execute syntax check."""
    try:
        result = subprocess.run(
            ["fish", "--version"], capture_output=True, text=True
        )
    except FileNotFoundError:
        print("SKIP: fish not available")
        return
    if result.returncode != 0:
        print("SKIP: fish not available")
        return

    all_files = [CONFIG_FISH]
    all_files += sorted(CONF_D.glob("*.fish"))
    # Skip fish_prompt.fish — it relies on tide functions not available outside fish
    all_files += [
        f for f in sorted(FUNCTIONS_DIR.glob("*.fish"))
        if f.name != "fish_prompt.fish"
    ]

    errors = []
    for f in all_files:
        result = subprocess.run(
            ["fish", "--no-execute", str(f)],
            capture_output=True,
            text=True,
        )
        if result.returncode != 0:
            errors.append(f"{f.name}: {result.stderr.strip()}")

    assert not errors, "Syntax errors:\n" + "\n".join(errors)


def test_gitignore_covers_generated_files():
    """conf.d and functions .gitignore files must list generated files."""
    for subdir in [CONF_D, FUNCTIONS_DIR]:
        gi = subdir / ".gitignore"
        if not gi.exists():
            continue
        content = gi.read_text()
        assert "generate_shell.py" in content, (
            f"{gi} should have the generate_shell.py header comment"
        )


def run_all_tests():
    """Run all tests manually (for systems without pytest)."""
    tests = [
        test_config_fish_exists,
        test_config_fish_has_interactive_guard,
        test_config_fish_supports_local_override,
        test_conf_d_exists,
        test_functions_dir_exists,
        test_fish_plugins_exists,
        test_fish_plugins_has_fisher,
        test_fish_plugins_has_tide,
        test_fish_plugins_no_blank_lines,
        test_conf_d_hand_managed_files_have_shebang,
        test_env_fish_disables_greeting,
        test_brew_fish_handles_all_platforms,
        test_brew_fish_has_early_return,
        test_no_universal_vars_in_conf_d,
        test_fish_syntax,
        test_gitignore_covers_generated_files,
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
