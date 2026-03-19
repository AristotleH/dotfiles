#!/usr/bin/env python3
"""Prompt behavior regression tests for truncation and performance."""

from __future__ import annotations

import os
import re
import shutil
import subprocess
import sys
import tempfile
import textwrap
import time
from pathlib import Path


ANSI_RE = re.compile(r"\x1b\[[0-9;]*m")
REPO_ROOT = Path(__file__).resolve().parent.parent
DEFAULT_CONFIG_DIR = Path.home() / ".config"
CONFIG_DIR = Path(sys.argv[1]) if len(sys.argv) > 1 else DEFAULT_CONFIG_DIR
FISH_PROMPT = CONFIG_DIR / "fish" / "functions" / "fish_prompt.fish"
BASH_PROMPT = CONFIG_DIR / "bash" / "bashrc.d" / "80-prompt.bash"
ZSH_PROMPT = REPO_ROOT / "dot_config" / "zsh" / "dot_zshrc.d" / "80-prompt.zsh"


def shell_available(shell: str) -> bool:
    try:
        result = subprocess.run(
            [shell, "--version"], capture_output=True, text=True, timeout=5
        )
    except (FileNotFoundError, subprocess.TimeoutExpired):
        return False
    return result.returncode == 0


def strip_ansi(text: str) -> str:
    return ANSI_RE.sub("", text)


def run_shell(args: list[str], script: str, timeout: int = 15) -> subprocess.CompletedProcess:
    return subprocess.run(
        args + [script],
        capture_output=True,
        text=True,
        timeout=timeout,
        check=False,
    )


def make_slow_git_dir() -> Path:
    real_git = shutil.which("git")
    if not real_git:
        raise RuntimeError("git is required for prompt tests")

    tempdir = Path(tempfile.mkdtemp(prefix="slow-git-"))
    wrapper = tempdir / "git"
    wrapper.write_text(
        "#!/usr/bin/env bash\n"
        "sleep 0.2\n"
        f'exec "{real_git}" "$@"\n'
    )
    wrapper.chmod(0o755)
    return tempdir


def make_repo() -> Path:
    repo = Path(tempfile.mkdtemp(prefix="prompt-repo-")) / "a" / "verylongsegment" / "b" / "repository"
    repo.mkdir(parents=True)
    subprocess.run(["git", "init", str(repo)], check=True, capture_output=True, text=True)
    subprocess.run(["git", "-C", str(repo), "config", "user.name", "Prompt Test"], check=True)
    subprocess.run(["git", "-C", str(repo), "config", "user.email", "prompt@example.com"], check=True)
    (repo / "tracked.txt").write_text("hello\n")
    subprocess.run(["git", "-C", str(repo), "add", "tracked.txt"], check=True)
    subprocess.run(["git", "-C", str(repo), "commit", "-m", "init"], check=True, capture_output=True)
    return repo


def test_fish_prompt_truncates_paths():
    if not shell_available("fish") or not FISH_PROMPT.exists():
        return

    long_dir = Path(tempfile.mkdtemp(prefix="fish-prompt-")) / "alpha" / "beta" / "gamma" / "delta"
    long_dir.mkdir(parents=True)
    script = textwrap.dedent(
        f"""
        source {FISH_PROMPT}
        set -gx COLUMNS 18
        cd {long_dir}
        _prompt_pwd
        """
    )
    result = run_shell(["fish", "-c"], script)
    assert result.returncode == 0, result.stderr
    rendered = strip_ansi(result.stdout.strip())
    assert len(rendered) <= 10, rendered
    assert rendered.endswith("delta"), rendered


def test_bash_prompt_truncates_paths():
    if not shell_available("bash") or not BASH_PROMPT.exists():
        return

    long_dir = Path(tempfile.mkdtemp(prefix="bash-prompt-")) / "alpha" / "beta" / "gamma" / "delta"
    long_dir.mkdir(parents=True)
    script = textwrap.dedent(
        f"""
        source "{BASH_PROMPT}"
        COLUMNS=18
        cd "{long_dir}"
        __dot_prompt_pwd
        """
    )
    result = run_shell(["bash", "-c"], script)
    assert result.returncode == 0, result.stderr
    rendered = strip_ansi(result.stdout.strip())
    assert len(rendered) <= 10, rendered
    assert rendered.endswith("delta"), rendered


def test_zsh_prompt_truncates_paths():
    if not shell_available("zsh") or not ZSH_PROMPT.exists():
        return

    long_dir = Path(tempfile.mkdtemp(prefix="zsh-prompt-")) / "alpha" / "beta" / "gamma" / "delta"
    long_dir.mkdir(parents=True)
    script = textwrap.dedent(
        f"""
        source {ZSH_PROMPT}
        COLUMNS=18
        cd {long_dir}
        _prompt_pwd
        """
    )
    result = run_shell(["zsh", "-i", "-c"], script)
    assert result.returncode == 0, result.stderr
    rendered = strip_ansi(result.stdout.strip().splitlines()[-1])
    assert len(rendered) <= 10, rendered
    assert rendered.endswith("delta"), rendered


def test_fish_prompt_non_repo_is_fast():
    if not shell_available("fish") or not FISH_PROMPT.exists():
        return

    long_dir = Path(tempfile.mkdtemp(prefix="fish-fast-")) / "outside" / "repo"
    long_dir.mkdir(parents=True)
    start = time.perf_counter()
    result = run_shell(
        ["fish", "-c"],
        textwrap.dedent(
            f"""
            source {FISH_PROMPT}
            set -gx COLUMNS 120
            cd {long_dir}
            for _ in (seq 20)
                fish_prompt >/dev/null
            end
            """
        ),
    )
    elapsed = time.perf_counter() - start
    assert result.returncode == 0, result.stderr
    assert elapsed < 0.35, elapsed


def test_bash_prompt_non_repo_is_fast():
    if not shell_available("bash") or not BASH_PROMPT.exists():
        return

    long_dir = Path(tempfile.mkdtemp(prefix="bash-fast-")) / "outside" / "repo"
    long_dir.mkdir(parents=True)
    start = time.perf_counter()
    result = run_shell(
        ["bash", "-c"],
        textwrap.dedent(
            f"""
            source "{BASH_PROMPT}"
            COLUMNS=120
            cd "{long_dir}"
            for _ in $(seq 20); do
                __dot_prompt_precmd
            done
            """
        ),
    )
    elapsed = time.perf_counter() - start
    assert result.returncode == 0, result.stderr
    assert elapsed < 0.35, elapsed


def test_fish_prompt_git_refresh_is_async():
    if not shell_available("fish") or not FISH_PROMPT.exists() or not shutil.which("git"):
        return

    repo = make_repo()
    slow_git_dir = make_slow_git_dir()
    prompt_path = os.pathsep.join([str(slow_git_dir), os.environ.get("PATH", "")])
    start = time.perf_counter()
    result = run_shell(
        ["env", f"PATH={prompt_path}", "fish", "-c"],
        textwrap.dedent(
            f"""
            source {FISH_PROMPT}
            set -gx COLUMNS 120
            cd {repo}
            fish_prompt >/dev/null
            """
        ),
        timeout=20,
    )
    elapsed = time.perf_counter() - start
    assert result.returncode == 0, result.stderr
    assert elapsed < 0.18, elapsed


def test_bash_prompt_git_refresh_is_async():
    if not shell_available("bash") or not BASH_PROMPT.exists() or not shutil.which("git"):
        return

    repo = make_repo()
    slow_git_dir = make_slow_git_dir()
    prompt_path = os.pathsep.join([str(slow_git_dir), os.environ.get("PATH", "")])
    start = time.perf_counter()
    result = run_shell(
        ["env", f"PATH={prompt_path}", "bash", "-c"],
        textwrap.dedent(
            f"""
            source "{BASH_PROMPT}"
            COLUMNS=120
            cd "{repo}"
            __dot_prompt_precmd
            """
        ),
        timeout=20,
    )
    elapsed = time.perf_counter() - start
    assert result.returncode == 0, result.stderr
    assert elapsed < 0.18, elapsed


def test_fish_prompt_eventually_renders_git_info():
    if not shell_available("fish") or not FISH_PROMPT.exists() or not shutil.which("git"):
        return

    repo = make_repo()
    result = run_shell(
        ["fish", "-c"],
        textwrap.dedent(
            f"""
            source {FISH_PROMPT}
            set -gx COLUMNS 120
            cd {repo}
            fish_prompt >/dev/null
            sleep 0.5
            fish_prompt
            """
        ),
        timeout=20,
    )
    assert result.returncode == 0, result.stderr
    rendered = strip_ansi(result.stdout.strip())
    assert repo.name in rendered or "main" in rendered or "master" in rendered, rendered


def test_bash_prompt_eventually_renders_git_info():
    if not shell_available("bash") or not BASH_PROMPT.exists() or not shutil.which("git"):
        return

    repo = make_repo()
    result = run_shell(
        ["bash", "-c"],
        textwrap.dedent(
            f"""
            source "{BASH_PROMPT}"
            COLUMNS=120
            cd "{repo}"
            __dot_prompt_precmd
            sleep 0.5
            __dot_prompt_precmd
            printf '%s\n' "$PS1"
            """
        ),
        timeout=20,
    )
    assert result.returncode == 0, result.stderr
    rendered = strip_ansi(result.stdout.strip())
    assert "main" in rendered or "master" in rendered, rendered


TESTS = [
    test_fish_prompt_truncates_paths,
    test_bash_prompt_truncates_paths,
    test_zsh_prompt_truncates_paths,
    test_fish_prompt_non_repo_is_fast,
    test_bash_prompt_non_repo_is_fast,
    test_fish_prompt_eventually_renders_git_info,
    test_bash_prompt_eventually_renders_git_info,
    test_fish_prompt_git_refresh_is_async,
    test_bash_prompt_git_refresh_is_async,
]


def run_all_tests() -> int:
    passed = 0
    failed = 0
    for test in TESTS:
        try:
            test()
            print(f"PASS {test.__name__}")
            passed += 1
        except AssertionError as exc:
            print(f"FAIL {test.__name__}: {exc}")
            failed += 1
        except Exception as exc:  # pragma: no cover - manual runner
            print(f"FAIL {test.__name__}: Unexpected error: {exc}")
            failed += 1
    print(f"\n{passed} passed, {failed} failed")
    return 0 if failed == 0 else 1


if __name__ == "__main__":
    sys.exit(run_all_tests())
