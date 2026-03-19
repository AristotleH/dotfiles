#!/usr/bin/env python3
"""
Prompt speed and correctness regression tests for Fish and Bash.

Ensures the synchronous portion of the prompt (pwd + cached git + arrow)
renders well within the threshold.  Async git runs in the background and
is NOT included in the timing — only the instant part matters.

Also validates path truncation produces the correct output.

Run with: python3 .tests/test_prompt_speed.py
Requires: fish (for fish tests), bash (for bash tests), python3 + pyyaml
          (for bash generation).  Tests are skipped gracefully when tools
          are unavailable.
"""

import os
import re
import subprocess
import sys
import tempfile
from pathlib import Path

REPO_ROOT = Path(__file__).parent.parent
FISH_PROMPT = REPO_ROOT / "dot_config" / "fish" / "functions" / "fish_prompt.fish"
SHELLGEN_DIR = REPO_ROOT / ".shellgen"

# Synchronous prompt rendering must complete within this budget (ms).
# Generous to account for CI variability; real-world is typically <10ms.
PROMPT_SPEED_MS = 100


def _strip_ansi(s):
    """Strip ANSI escape codes and bash readline wrapping markers."""
    s = re.sub(r'\x1b\[[0-9;]*m', '', s)
    # Also strip bash \[...\] readline markers (literal backslash-bracket)
    s = s.replace('\\[', '').replace('\\]', '')
    # And raw escape sequences like \e[0m that weren't yet interpreted
    s = re.sub(r'\\e\[[0-9;]*m', '', s)
    return s


def _has_command(cmd):
    try:
        r = subprocess.run([cmd, "--version"], capture_output=True, timeout=5)
        return r.returncode == 0
    except (FileNotFoundError, subprocess.TimeoutExpired):
        return False


def _generate_bash_prompt():
    """Generate the bash prompt file via shellgen and return its contents."""
    try:
        import yaml  # noqa: F401
    except ImportError:
        return None

    with tempfile.TemporaryDirectory() as tmpdir:
        r = subprocess.run(
            [sys.executable,
             str(SHELLGEN_DIR / "generate_shell.py"),
             "--target", tmpdir,
             str(SHELLGEN_DIR / "shell.yaml")],
            capture_output=True, text=True, timeout=30,
        )
        if r.returncode != 0:
            print(f"  shellgen failed: {r.stderr[:200]}")
            return None
        prompt_file = Path(tmpdir) / "bash" / "bashrc.d" / "80-prompt.bash"
        if prompt_file.exists():
            return prompt_file.read_text()
    return None


def _git_init(path):
    """Create a minimal git repo at *path* with one commit."""
    env = {
        **os.environ,
        "GIT_AUTHOR_NAME": "test",
        "GIT_AUTHOR_EMAIL": "t@t",
        "GIT_COMMITTER_NAME": "test",
        "GIT_COMMITTER_EMAIL": "t@t",
    }
    subprocess.run(["git", "init", path], capture_output=True, check=True)
    subprocess.run(
        ["git", "-C", path, "-c", "commit.gpgsign=false",
         "commit", "--allow-empty", "-m", "init"],
        capture_output=True, check=True, env=env,
    )


# ---------------------------------------------------------------------------
# Fish tests
# ---------------------------------------------------------------------------

def test_fish_prompt_speed_no_git():
    """Fish prompt renders quickly outside a git repo."""
    if not _has_command("fish"):
        print("SKIP: fish not available")
        return

    with tempfile.TemporaryDirectory() as tmpdir:
        script = (
            f"set -g COLUMNS 120\n"
            f"source {FISH_PROMPT}\n"
            f"set -l t0 (date +%s%N)\n"
            f"fish_prompt >/dev/null\n"
            f"set -l t1 (date +%s%N)\n"
            f"echo (math \"($t1 - $t0) / 1000000\")\n"
        )
        r = subprocess.run(
            ["fish", "-c", script],
            capture_output=True, text=True,
            cwd=tmpdir, timeout=10,
        )
        assert r.returncode == 0, f"fish prompt failed: {r.stderr}"
        elapsed = float(r.stdout.strip())
        print(f"  Fish (no git): {elapsed:.1f}ms")
        assert elapsed < PROMPT_SPEED_MS, (
            f"Fish prompt too slow outside git: {elapsed:.1f}ms > {PROMPT_SPEED_MS}ms"
        )


def test_fish_prompt_speed_in_git():
    """Fish prompt renders quickly inside a git repo (sync portion only)."""
    if not _has_command("fish"):
        print("SKIP: fish not available")
        return

    with tempfile.TemporaryDirectory() as tmpdir:
        _git_init(tmpdir)
        script = (
            f"set -g COLUMNS 120\n"
            f"source {FISH_PROMPT}\n"
            f"set -l t0 (date +%s%N)\n"
            f"fish_prompt >/dev/null\n"
            f"set -l t1 (date +%s%N)\n"
            f"echo (math \"($t1 - $t0) / 1000000\")\n"
        )
        r = subprocess.run(
            ["fish", "-c", script],
            capture_output=True, text=True,
            cwd=tmpdir, timeout=10,
        )
        assert r.returncode == 0, f"fish prompt failed: {r.stderr}"
        elapsed = float(r.stdout.strip())
        print(f"  Fish (git repo, sync): {elapsed:.1f}ms")
        assert elapsed < PROMPT_SPEED_MS, (
            f"Fish prompt too slow in git: {elapsed:.1f}ms > {PROMPT_SPEED_MS}ms"
        )


def test_fish_prompt_no_subprocess_outside_git():
    """Fish prompt must not spawn any subprocess when outside a git repo."""
    if not _has_command("fish"):
        print("SKIP: fish not available")
        return

    with tempfile.TemporaryDirectory() as tmpdir:
        # Use strace to count execve calls (Linux only)
        try:
            subprocess.run(["strace", "--version"], capture_output=True, check=True)
        except (FileNotFoundError, subprocess.CalledProcessError):
            print("SKIP: strace not available")
            return

        script = (
            f"set -g COLUMNS 80\n"
            f"source {FISH_PROMPT}\n"
            f"fish_prompt >/dev/null\n"
        )
        r = subprocess.run(
            ["strace", "-f", "-e", "trace=execve", "-o", f"{tmpdir}/trace.log",
             "fish", "-c", script],
            capture_output=True, text=True,
            cwd=tmpdir, timeout=10,
        )
        trace = Path(f"{tmpdir}/trace.log").read_text()
        # Match only actual git binary executions, not paths containing "git"
        git_calls = [l for l in trace.splitlines()
                     if 'execve(' in l and ('"git"' in l or '/git"' in l)]
        assert len(git_calls) == 0, (
            f"Fish prompt spawned git outside a repo:\n"
            + "\n".join(git_calls[:5])
        )
        print(f"  Fish (no git subprocesses outside repo): OK")


def test_fish_path_truncation():
    """Fish _prompt_pwd truncates middle components when path is long."""
    if not _has_command("fish"):
        print("SKIP: fish not available")
        return

    with tempfile.TemporaryDirectory() as tmpdir:
        # Create a deep nested path
        deep = Path(tmpdir) / "very" / "deeply" / "nested" / "directory"
        deep.mkdir(parents=True)
        script = (
            f"source {FISH_PROMPT}\n"
            f"set -g COLUMNS 40\n"
            f"set -g HOME {tmpdir}\n"
            f"cd {deep}\n"
            f"echo (_prompt_pwd)\n"
        )
        r = subprocess.run(
            ["fish", "-c", script],
            capture_output=True, text=True, timeout=10,
        )
        assert r.returncode == 0, f"fish _prompt_pwd failed: {r.stderr}"
        raw = _strip_ansi(r.stdout.strip())
        # Path ~/very/deeply/nested/directory → with COLUMNS=40, cwd is ~26 chars
        # half=20, so it should truncate: ~/v/d/n/directory
        assert "directory" in raw, f"Last component missing: {raw}"
        assert raw.startswith("~"), f"Should start with ~: {raw}"
        # Middle components should be single chars
        parts = raw.split("/")
        if len(parts) > 2:
            for p in parts[1:-1]:
                assert len(p) <= 1, f"Middle component not truncated: '{p}' in {raw}"
        print(f"  Fish path truncation: OK ({raw})")


def test_fish_path_no_truncation_short():
    """Fish _prompt_pwd does NOT truncate when path fits."""
    if not _has_command("fish"):
        print("SKIP: fish not available")
        return

    with tempfile.TemporaryDirectory() as tmpdir:
        short = Path(tmpdir) / "a" / "b"
        short.mkdir(parents=True)
        script = (
            f"source {FISH_PROMPT}\n"
            f"set -g COLUMNS 200\n"
            f"set -g HOME {tmpdir}\n"
            f"cd {short}\n"
            f"echo (_prompt_pwd)\n"
        )
        r = subprocess.run(
            ["fish", "-c", script],
            capture_output=True, text=True, timeout=10,
        )
        assert r.returncode == 0, f"fish _prompt_pwd failed: {r.stderr}"
        raw = _strip_ansi(r.stdout.strip())
        assert raw == "~/a/b", f"Short path should not be truncated: {raw}"
        print(f"  Fish path (no truncation): OK ({raw})")


# ---------------------------------------------------------------------------
# Bash tests
# ---------------------------------------------------------------------------

def _bash_run(script, cwd, timeout=10, env=None):
    """Run a bash script in interactive mode (--norc --noprofile -i)."""
    return subprocess.run(
        ["bash", "--norc", "--noprofile", "-i", "-c", script],
        capture_output=True, text=True,
        cwd=cwd, timeout=timeout, env=env,
    )


def test_bash_prompt_speed_no_git():
    """Bash prompt renders quickly outside a git repo."""
    prompt_code = _generate_bash_prompt()
    if prompt_code is None:
        print("SKIP: could not generate bash prompt (pyyaml missing?)")
        return

    with tempfile.TemporaryDirectory() as tmpdir:
        pf = Path(tmpdir) / "prompt.bash"
        pf.write_text(prompt_code)
        script = (
            f'source "{pf}"\n'
            f'COLUMNS=120\n'
            f'start=$(date +%s%N)\n'
            f'__dot_prompt_precmd\n'
            f'end=$(date +%s%N)\n'
            f'echo $(( (end - start) / 1000000 ))\n'
        )
        r = _bash_run(script, cwd=tmpdir)
        assert r.returncode == 0, f"bash prompt failed: {r.stderr}"
        elapsed = int(r.stdout.strip())
        print(f"  Bash (no git): {elapsed}ms")
        assert elapsed < PROMPT_SPEED_MS, (
            f"Bash prompt too slow outside git: {elapsed}ms > {PROMPT_SPEED_MS}ms"
        )


def test_bash_prompt_speed_in_git():
    """Bash prompt renders quickly inside a git repo (sync portion only)."""
    prompt_code = _generate_bash_prompt()
    if prompt_code is None:
        print("SKIP: could not generate bash prompt (pyyaml missing?)")
        return

    with tempfile.TemporaryDirectory() as tmpdir:
        _git_init(tmpdir)
        pf = Path(tmpdir) / "prompt.bash"
        pf.write_text(prompt_code)
        script = (
            f'source "{pf}"\n'
            f'COLUMNS=120\n'
            f'start=$(date +%s%N)\n'
            f'__dot_prompt_precmd\n'
            f'end=$(date +%s%N)\n'
            f'echo $(( (end - start) / 1000000 ))\n'
        )
        r = _bash_run(script, cwd=tmpdir)
        assert r.returncode == 0, f"bash prompt failed: {r.stderr}"
        elapsed = int(r.stdout.strip())
        print(f"  Bash (git repo, sync): {elapsed}ms")
        assert elapsed < PROMPT_SPEED_MS, (
            f"Bash prompt too slow in git: {elapsed}ms > {PROMPT_SPEED_MS}ms"
        )


def test_bash_prompt_no_subprocess_outside_git():
    """Bash prompt must not spawn any subprocess when outside a git repo."""
    prompt_code = _generate_bash_prompt()
    if prompt_code is None:
        print("SKIP: could not generate bash prompt (pyyaml missing?)")
        return

    try:
        subprocess.run(["strace", "--version"], capture_output=True, check=True)
    except (FileNotFoundError, subprocess.CalledProcessError):
        print("SKIP: strace not available")
        return

    with tempfile.TemporaryDirectory() as tmpdir:
        pf = Path(tmpdir) / "prompt.bash"
        pf.write_text(prompt_code)
        script = (
            f'source "{pf}"\n'
            f'COLUMNS=120\n'
            f'__dot_prompt_precmd\n'
        )
        r = subprocess.run(
            ["strace", "-f", "-e", "trace=execve", "-o", f"{tmpdir}/trace.log",
             "bash", "--norc", "--noprofile", "-i", "-c", script],
            capture_output=True, text=True,
            cwd=tmpdir, timeout=10,
        )
        trace = Path(f"{tmpdir}/trace.log").read_text()
        # Match only actual git binary executions, not paths containing "git"
        git_calls = [l for l in trace.splitlines()
                     if 'execve(' in l and ('"git"' in l or '/git"' in l)]
        assert len(git_calls) == 0, (
            f"Bash prompt spawned git outside a repo:\n"
            + "\n".join(git_calls[:5])
        )
        print(f"  Bash (no git subprocesses outside repo): OK")


def test_bash_path_truncation():
    """Bash __dot_prompt_pwd truncates middle components correctly."""
    prompt_code = _generate_bash_prompt()
    if prompt_code is None:
        print("SKIP: could not generate bash prompt (pyyaml missing?)")
        return

    with tempfile.TemporaryDirectory() as tmpdir:
        deep = Path(tmpdir) / "very" / "deeply" / "nested" / "directory"
        deep.mkdir(parents=True)
        pf = Path(tmpdir) / "prompt.bash"
        # Strip the interactive guard so we can source without -i
        pf.write_text(prompt_code.replace(
            '[[ $- == *i* ]] || return 0', '# guard removed for test'))
        script = (
            f'export HOME="{tmpdir}"\n'
            f'source "{pf}"\n'
            f'COLUMNS=40\n'
            f'cd "{deep}"\n'
            f'__dot_prompt_pwd\n'
        )
        r = subprocess.run(
            ["bash", "--norc", "--noprofile", "-c", script],
            capture_output=True, text=True,
            cwd=tmpdir, timeout=10,
        )
        assert r.returncode == 0, f"bash __dot_prompt_pwd failed: {r.stderr}"
        raw = _strip_ansi(r.stdout.strip())
        assert "directory" in raw, f"Last component missing: {raw}"
        assert raw.startswith("~"), f"Should start with ~: {raw}"
        parts = raw.split("/")
        if len(parts) > 2:
            for p in parts[1:-1]:
                assert len(p) <= 1, f"Middle component not truncated: '{p}' in {raw}"
        print(f"  Bash path truncation: OK ({raw})")


# ---------------------------------------------------------------------------
# Runner
# ---------------------------------------------------------------------------

def run_all_tests():
    tests = [
        test_fish_prompt_speed_no_git,
        test_fish_prompt_speed_in_git,
        test_fish_prompt_no_subprocess_outside_git,
        test_fish_path_truncation,
        test_fish_path_no_truncation_short,
        test_bash_prompt_speed_no_git,
        test_bash_prompt_speed_in_git,
        test_bash_prompt_no_subprocess_outside_git,
        test_bash_path_truncation,
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
