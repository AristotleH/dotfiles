#!/usr/bin/env python3
"""
Functionality tests for generated shell configuration files.

Tests that generated shell configs actually work when loaded and executed,
not just that the files exist.

Platform-aware assertions adapt to the host OS:
  - Linux: is-linux true, is-darwin false
  - macOS: is-linux false, is-darwin true
  - other: both false

Supports two modes:
  - With a config dir argument: test files in that directory
  - Without arguments: test files in ~/.config (post-chezmoi apply)

Run with: python3 .tests/test_shell_functionality.py [config_dir]
"""

import subprocess
import sys
from pathlib import Path


# Default to ~/.config, allow override via CLI arg
if len(sys.argv) > 1:
    CONFIG_DIR = Path(sys.argv[1])
else:
    CONFIG_DIR = Path.home() / ".config"

# Shell config directories
FISH_FUNCS = CONFIG_DIR / "fish" / "functions"
FISH_CONFD = CONFIG_DIR / "fish" / "conf.d"
ZSH_FUNCS = CONFIG_DIR / "zsh" / ".zfunctions"
ZSH_CONFD = CONFIG_DIR / "zsh" / ".zshrc.d"
BASH_FUNCS = CONFIG_DIR / "bash" / "functions"
BASH_CONFD = CONFIG_DIR / "bash" / "bashrc.d"


def shell_available(shell):
    """Check if a shell binary is available."""
    try:
        result = subprocess.run(
            [shell, "--version"], capture_output=True, text=True, timeout=5
        )
        return result.returncode == 0
    except (FileNotFoundError, subprocess.TimeoutExpired):
        return False


def run_shell(shell, command, timeout=10):
    """Run a command in a given shell, return (returncode, stdout, stderr)."""
    if shell == "fish":
        args = ["fish", "-c", command]
    elif shell == "zsh":
        args = ["zsh", "-c", command]
    elif shell == "bash":
        args = ["bash", "-c", command]
    else:
        raise ValueError(f"Unknown shell: {shell}")

    result = subprocess.run(
        args, capture_output=True, text=True, timeout=timeout
    )
    return result.returncode, result.stdout.strip(), result.stderr.strip()


def _expected_is_linux_result():
    """Return expected success marker ('0' true, '1' false) for is-linux."""
    return "0" if sys.platform.startswith("linux") else "1"


def _expected_is_darwin_result():
    """Return expected success marker ('0' true, '1' false) for is-darwin."""
    return "0" if sys.platform == "darwin" else "1"


# ---------------------------------------------------------------------------
# Fish tests
# ---------------------------------------------------------------------------

def test_fish_syntax():
    """All generated .fish files must pass fish --no-execute syntax check."""
    errors = []
    for d in [FISH_FUNCS, FISH_CONFD]:
        if not d.exists():
            continue
        for f in sorted(d.glob("*.fish")):
            result = subprocess.run(
                ["fish", "--no-execute", str(f)],
                capture_output=True, text=True, timeout=10,
            )
            if result.returncode != 0:
                errors.append(f"{f.name}: {result.stderr.strip()}")
    assert not errors, "Fish syntax errors:\n" + "\n".join(errors)


def test_fish_is_linux():
    """Fish is-linux function should match host OS."""
    func = FISH_FUNCS / "is-linux.fish"
    if not func.exists():
        return
    rc, out, err = run_shell(
        "fish", f"source {func}; is-linux; echo $status"
    )
    expected = _expected_is_linux_result()
    assert out == expected, f"is-linux expected status {expected}, got status {out}"


def test_fish_is_darwin():
    """Fish is-darwin function should match host OS."""
    func = FISH_FUNCS / "is-darwin.fish"
    if not func.exists():
        return
    rc, out, err = run_shell(
        "fish", f"source {func}; is-darwin; echo $status"
    )
    expected = _expected_is_darwin_result()
    assert out == expected, f"is-darwin expected status {expected}, got status {out}"


def test_fish_in_dir():
    """Fish in_dir should run a command in a different directory."""
    func = FISH_FUNCS / "in_dir.fish"
    if not func.exists():
        return
    rc, out, err = run_shell(
        "fish", f"source {func}; in_dir /tmp pwd"
    )
    assert rc == 0, f"in_dir failed with rc={rc}, stderr: {err}"
    assert out == "/tmp", f"Expected /tmp, got: {out}"


def test_fish_path_module():
    """Fish path module should add ~/.local/bin to PATH."""
    mod = FISH_CONFD / "00-path.fish"
    if not mod.exists():
        return
    rc, out, err = run_shell(
        "fish", f"source {mod}; echo $PATH"
    )
    assert rc == 0, f"path module failed: {err}"
    assert ".local/bin" in out, f"PATH should contain .local/bin, got: {out}"


# ---------------------------------------------------------------------------
# Zsh tests
# ---------------------------------------------------------------------------

def test_zsh_syntax():
    """All generated .zsh files must pass zsh -n syntax check."""
    errors = []
    for d in [ZSH_CONFD]:
        if not d.exists():
            continue
        for f in sorted(d.glob("*.zsh")):
            result = subprocess.run(
                ["zsh", "-n", str(f)],
                capture_output=True, text=True, timeout=10,
            )
            if result.returncode != 0:
                errors.append(f"{f.name}: {result.stderr.strip()}")
    assert not errors, "Zsh syntax errors:\n" + "\n".join(errors)


def test_zsh_is_linux():
    """Zsh is-linux function should match host OS."""
    func_dir = ZSH_FUNCS
    if not (func_dir / "is-linux").exists():
        return
    rc, out, err = run_shell(
        "zsh",
        f'fpath=({func_dir} $fpath); autoload -Uz is-linux; '
        f'is-linux && echo 0 || echo 1'
    )
    expected = _expected_is_linux_result()
    assert out == expected, f"is-linux expected {expected}, got: {out}"


def test_zsh_is_darwin():
    """Zsh is-darwin function should match host OS."""
    func_dir = ZSH_FUNCS
    if not (func_dir / "is-darwin").exists():
        return
    rc, out, err = run_shell(
        "zsh",
        f'fpath=({func_dir} $fpath); autoload -Uz is-darwin; '
        f'is-darwin && echo 0 || echo 1'
    )
    expected = _expected_is_darwin_result()
    assert out == expected, f"is-darwin expected {expected}, got: {out}"


def test_zsh_in_dir():
    """Zsh in_dir should run a command in a different directory."""
    func_dir = ZSH_FUNCS
    if not (func_dir / "in_dir").exists():
        return
    rc, out, err = run_shell(
        "zsh",
        f'fpath=({func_dir} $fpath); autoload -Uz in_dir; '
        f'in_dir /tmp pwd'
    )
    assert rc == 0, f"in_dir failed with rc={rc}, stderr: {err}"
    assert out == "/tmp", f"Expected /tmp, got: {out}"


def test_zsh_path_module():
    """Zsh path module should add ~/.local/bin to PATH."""
    mod = ZSH_CONFD / "00-path.zsh"
    if not mod.exists():
        return
    rc, out, err = run_shell(
        "zsh", f'source {mod}; echo $PATH'
    )
    assert rc == 0, f"path module failed: {err}"
    assert ".local/bin" in out, f"PATH should contain .local/bin, got: {out}"


# ---------------------------------------------------------------------------
# Bash tests
# ---------------------------------------------------------------------------

def test_bash_syntax():
    """All generated .bash files must pass bash -n syntax check."""
    errors = []
    for d in [BASH_FUNCS, BASH_CONFD]:
        if not d.exists():
            continue
        for f in sorted(d.glob("*.bash")):
            result = subprocess.run(
                ["bash", "-n", str(f)],
                capture_output=True, text=True, timeout=10,
            )
            if result.returncode != 0:
                errors.append(f"{f.name}: {result.stderr.strip()}")
    assert not errors, "Bash syntax errors:\n" + "\n".join(errors)


def test_bash_is_linux():
    """Bash is-linux function should match host OS."""
    func = BASH_FUNCS / "is-linux.bash"
    if not func.exists():
        return
    rc, out, err = run_shell(
        "bash",
        f'source {func}; is-linux && echo 0 || echo 1'
    )
    expected = _expected_is_linux_result()
    assert out == expected, f"is-linux expected {expected}, got: {out}"


def test_bash_is_darwin():
    """Bash is-darwin function should match host OS."""
    func = BASH_FUNCS / "is-darwin.bash"
    if not func.exists():
        return
    rc, out, err = run_shell(
        "bash",
        f'source {func}; is-darwin && echo 0 || echo 1'
    )
    expected = _expected_is_darwin_result()
    assert out == expected, f"is-darwin expected {expected}, got: {out}"


def test_bash_in_dir():
    """Bash in_dir should run a command in a different directory."""
    func = BASH_FUNCS / "in_dir.bash"
    if not func.exists():
        return
    rc, out, err = run_shell(
        "bash",
        f'source {func}; in_dir /tmp pwd'
    )
    assert rc == 0, f"in_dir failed with rc={rc}, stderr: {err}"
    assert out == "/tmp", f"Expected /tmp, got: {out}"


def test_bash_path_module():
    """Bash path module should add ~/.local/bin to PATH."""
    mod = BASH_CONFD / "00-path.bash"
    if not mod.exists():
        return
    rc, out, err = run_shell(
        "bash", f'source {mod}; echo $PATH'
    )
    assert rc == 0, f"path module failed: {err}"
    assert ".local/bin" in out, f"PATH should contain .local/bin, got: {out}"


# ---------------------------------------------------------------------------
# Runner
# ---------------------------------------------------------------------------

def run_all_tests():
    """Run all tests, grouping by shell. Skip shells not available."""
    shell_tests = {
        "fish": [
            test_fish_syntax,
            test_fish_is_linux,
            test_fish_is_darwin,
            test_fish_in_dir,
            test_fish_path_module,
        ],
        "zsh": [
            test_zsh_syntax,
            test_zsh_is_linux,
            test_zsh_is_darwin,
            test_zsh_in_dir,
            test_zsh_path_module,
        ],
        "bash": [
            test_bash_syntax,
            test_bash_is_linux,
            test_bash_is_darwin,
            test_bash_in_dir,
            test_bash_path_module,
        ],
    }

    passed = 0
    failed = 0
    skipped = 0

    for shell, tests in shell_tests.items():
        if not shell_available(shell):
            print(f"\nSKIP: {shell} not available")
            skipped += len(tests)
            continue

        print(f"\n--- {shell} ---")
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

    print(f"\n{passed} passed, {failed} failed, {skipped} skipped")
    return 0 if failed == 0 else 1


if __name__ == "__main__":
    sys.exit(run_all_tests())
