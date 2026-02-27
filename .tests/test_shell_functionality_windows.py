#!/usr/bin/env python3
"""
Functionality tests for generated shell configuration files on Windows.

Tests PowerShell (pwsh) and Bash (Git Bash) generated configs.
Runs on Windows CI (GitHub Actions windows-latest) or any system
with pwsh and/or bash available.

Usage:
  python3 .tests/test_shell_functionality_windows.py <config_dir>

  config_dir: directory containing the generated shell configs
              (e.g. the --target passed to generate_shell.py)
"""

import os
import subprocess
import sys
from pathlib import Path


if len(sys.argv) < 2:
    print("Usage: test_shell_functionality_windows.py <config_dir>")
    sys.exit(1)

CONFIG_DIR = Path(sys.argv[1])

# Shell config directories
PWSH_FUNCS = CONFIG_DIR / "powershell" / "functions"
PWSH_CONFD = CONFIG_DIR / "powershell" / "conf.d"
BASH_FUNCS = CONFIG_DIR / "bash" / "functions"
BASH_CONFD = CONFIG_DIR / "bash" / "bashrc.d"


def shell_available(shell):
    """Check if a shell binary is available."""
    try:
        result = subprocess.run(
            [shell, "--version"], capture_output=True, text=True, timeout=10
        )
        return result.returncode == 0
    except (FileNotFoundError, subprocess.TimeoutExpired):
        return False


def run_pwsh(command, timeout=15):
    """Run a PowerShell command, return (returncode, stdout, stderr)."""
    result = subprocess.run(
        ["pwsh", "-NoProfile", "-NonInteractive", "-Command", command],
        capture_output=True, text=True, timeout=timeout,
    )
    return result.returncode, result.stdout.strip(), result.stderr.strip()


def run_bash(command, timeout=10):
    """Run a Bash command, return (returncode, stdout, stderr)."""
    result = subprocess.run(
        ["bash", "-c", command],
        capture_output=True, text=True, timeout=timeout,
    )
    return result.returncode, result.stdout.strip(), result.stderr.strip()


# ---------------------------------------------------------------------------
# PowerShell tests
# ---------------------------------------------------------------------------

def test_pwsh_syntax():
    """All generated .ps1 files must parse without errors."""
    errors = []
    for d in [PWSH_FUNCS, PWSH_CONFD]:
        if not d.exists():
            continue
        for f in sorted(d.glob("*.ps1")):
            # Use ParseFile with pre-declared variables to avoid [ref] errors
            rc, out, err = run_pwsh(
                f"$tokens = $null; $errs = $null; "
                f"[System.Management.Automation.Language.Parser]"
                f"::ParseFile('{f}', [ref]$tokens, [ref]$errs) | Out-Null; "
                f"if ($errs.Count -gt 0) {{ $errs | ForEach-Object {{ $_.Message }}; exit 1 }}"
            )
            if rc != 0:
                errors.append(f"{f.name}: {err or out}")
    assert not errors, "PowerShell syntax errors:\n" + "\n".join(errors)


def test_pwsh_is_linux():
    """PowerShell is-linux should return falsy on Windows."""
    func = PWSH_FUNCS / "is-linux.ps1"
    if not func.exists():
        return
    rc, out, err = run_pwsh(
        f". '{func}'; if (is-linux) {{ echo 'true' }} else {{ echo 'false' }}"
    )
    # On Windows, is-linux should return false
    # On Linux CI with pwsh, it would return true — adapt assertion
    if sys.platform == "win32":
        assert out == "false", f"is-linux should be false on Windows, got: {out}"
    else:
        assert out == "true", f"is-linux should be true on Linux, got: {out}"


def test_pwsh_is_darwin():
    """PowerShell is-darwin should return falsy on Windows/Linux."""
    func = PWSH_FUNCS / "is-darwin.ps1"
    if not func.exists():
        return
    rc, out, err = run_pwsh(
        f". '{func}'; if (is-darwin) {{ echo 'true' }} else {{ echo 'false' }}"
    )
    # On both Windows and Linux CI, is-darwin should be false
    assert out == "false", f"is-darwin should be false, got: {out}"


def test_pwsh_in_dir():
    """PowerShell in_dir should run a command in a different directory."""
    func = PWSH_FUNCS / "in_dir.ps1"
    if not func.exists():
        return
    # Use a temp dir that exists on all platforms
    if sys.platform == "win32":
        test_dir = os.environ.get("TEMP", "C:\\Windows\\Temp")
    else:
        test_dir = "/tmp"
    rc, out, err = run_pwsh(
        f". '{func}'; in_dir '{test_dir}' 'Get-Location' | "
        f"ForEach-Object {{ $_.Path }}"
    )
    assert rc == 0, f"in_dir failed with rc={rc}, stderr: {err}"
    # Normalize path comparison
    assert Path(out).resolve() == Path(test_dir).resolve(), (
        f"Expected {test_dir}, got: {out}"
    )


def test_pwsh_path_module():
    """PowerShell path module should modify PATH."""
    mod = PWSH_CONFD / "00-path.ps1"
    if not mod.exists():
        return
    rc, out, err = run_pwsh(f". '{mod}'; echo $env:PATH")
    assert rc == 0, f"path module failed: {err}"
    assert ".local/bin" in out or ".local\\bin" in out, (
        f"PATH should contain .local/bin after sourcing path module, got: {out[:200]}"
    )


# ---------------------------------------------------------------------------
# Bash (Git Bash) tests
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
    """Bash is-linux on Windows (Git Bash) should return non-0."""
    func = BASH_FUNCS / "is-linux.bash"
    if not func.exists():
        return
    # Convert Windows path to Unix-style for Git Bash
    func_path = str(func).replace("\\", "/")
    rc, out, err = run_bash(
        f'source "{func_path}"; is-linux && echo 0 || echo 1'
    )
    if sys.platform == "win32":
        # Git Bash on Windows: OSTYPE is msys*, so is-linux returns false
        assert out == "1", f"is-linux should return 1 on Windows/Git Bash, got: {out}"
    else:
        assert out == "0", f"is-linux should return 0 on Linux, got: {out}"


def test_bash_is_darwin():
    """Bash is-darwin should return non-0 on Windows and Linux."""
    func = BASH_FUNCS / "is-darwin.bash"
    if not func.exists():
        return
    func_path = str(func).replace("\\", "/")
    rc, out, err = run_bash(
        f'source "{func_path}"; is-darwin && echo 0 || echo 1'
    )
    assert out == "1", f"is-darwin should return 1 on non-macOS, got: {out}"


def test_bash_in_dir():
    """Bash in_dir should run a command in a different directory."""
    func = BASH_FUNCS / "in_dir.bash"
    if not func.exists():
        return
    func_path = str(func).replace("\\", "/")
    rc, out, err = run_bash(
        f'source "{func_path}"; in_dir /tmp pwd'
    )
    assert rc == 0, f"in_dir failed with rc={rc}, stderr: {err}"
    assert "/tmp" in out, f"Expected /tmp in output, got: {out}"


def test_bash_path_module():
    """Bash path module should add ~/.local/bin to PATH."""
    mod = BASH_CONFD / "00-path.bash"
    if not mod.exists():
        return
    mod_path = str(mod).replace("\\", "/")
    rc, out, err = run_bash(f'source "{mod_path}"; echo $PATH')
    assert rc == 0, f"path module failed: {err}"
    assert ".local/bin" in out, f"PATH should contain .local/bin, got: {out[:200]}"


# ---------------------------------------------------------------------------
# Runner
# ---------------------------------------------------------------------------

def run_all_tests():
    """Run all tests, grouping by shell. Skip shells not available."""
    shell_tests = {
        "pwsh": [
            test_pwsh_syntax,
            test_pwsh_is_linux,
            test_pwsh_is_darwin,
            test_pwsh_in_dir,
            test_pwsh_path_module,
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
                print(f"  PASS {test.__name__}")
                passed += 1
            except AssertionError as e:
                print(f"  FAIL {test.__name__}: {e}")
                failed += 1
            except Exception as e:
                print(f"  FAIL {test.__name__}: Unexpected error: {e}")
                failed += 1

    print(f"\n{passed} passed, {failed} failed, {skipped} skipped")
    return 0 if failed == 0 else 1


if __name__ == "__main__":
    sys.exit(run_all_tests())
