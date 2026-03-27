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
BASH_PROMPT_RE = re.compile(r"\\\[|\\\]|\\e\[[0-9;]*m")
ZSH_PROMPT_RE = re.compile(r"%F\{[^}]+\}|%f")
OSC_RE = re.compile(r"\x1b\][^\x07\x1b]*(?:\x07|\x1b\\)")
REPO_ROOT = Path(__file__).resolve().parent.parent
DEFAULT_CONFIG_DIR = Path.home() / ".config"
CONFIG_DIR = Path(sys.argv[1]) if len(sys.argv) > 1 else DEFAULT_CONFIG_DIR
FISH_PROMPT = CONFIG_DIR / "fish" / "functions" / "fish_prompt.fish"
BASH_PROMPT = CONFIG_DIR / "bash" / "bashrc.d" / "80-prompt.bash"
ZSH_PROMPT = CONFIG_DIR / "zsh" / ".zshrc.d" / "80-prompt.zsh"
PWSH_PROMPT = CONFIG_DIR / "powershell" / "conf.d" / "80-prompt.ps1"
if not BASH_PROMPT.exists():
    BASH_PROMPT = REPO_ROOT / "dot_config" / "bash" / "bashrc.d" / "80-prompt.bash"
if not ZSH_PROMPT.exists():
    ZSH_PROMPT = REPO_ROOT / "dot_config" / "zsh" / "dot_zshrc.d" / "80-prompt.zsh"
if not PWSH_PROMPT.exists():
    PWSH_PROMPT = REPO_ROOT / "dot_config" / "powershell" / "conf.d" / "80-prompt.ps1"


def shell_available(shell: str) -> bool:
    try:
        result = subprocess.run(
            [shell, "--version"], capture_output=True, text=True, timeout=5
        )
    except (FileNotFoundError, subprocess.TimeoutExpired):
        return False
    return result.returncode == 0


def strip_ansi(text: str) -> str:
    text = BASH_PROMPT_RE.sub("", text)
    text = ZSH_PROMPT_RE.sub("", text)
    text = OSC_RE.sub("", text)
    return ANSI_RE.sub("", text)


def last_nonempty_line(text: str, label: str) -> str:
    lines = [line for line in text.splitlines() if line.strip()]
    assert lines, f"no output captured for {label}"
    return lines[-1]


def run_shell(args: list[str], script: str, timeout: int = 15) -> subprocess.CompletedProcess:
    return subprocess.run(
        args + [script],
        capture_output=True,
        text=True,
        timeout=timeout,
        check=False,
    )


def isolated_prompt_env() -> dict[str, str]:
    home = Path(tempfile.mkdtemp(prefix="prompt-home-"))
    cache = home / ".cache"
    cache.mkdir(parents=True, exist_ok=True)
    env = os.environ.copy()
    env["HOME"] = str(home)
    env["XDG_CACHE_HOME"] = str(cache)
    return env


def prompt_cache_paths(repo: Path, env: dict[str, str], shell_suffix: str) -> tuple[Path, Path]:
    key = re.sub(r"[^A-Za-z0-9_.-]", "_", str(repo))
    cache_dir = Path(env["HOME"]) / ".cache" / "dot_prompt"
    return cache_dir / f"{key}.{shell_suffix}.git", cache_dir / f"{key}.{shell_suffix}.head"


def wait_for_prompt_cache(cache: Path, head_cache: Path, timeout: float = 2.0) -> str:
    deadline = time.perf_counter() + timeout
    last_cache = ""
    while time.perf_counter() < deadline:
        if cache.exists():
            last_cache = cache.read_text()
        if last_cache and head_cache.exists():
            return last_cache
        time.sleep(0.05)
    raise AssertionError(
        f"prompt cache did not settle: cache={cache.exists()} head_cache={head_cache.exists()}"
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


def _git_config_repo(repo: Path) -> None:
    """Apply minimal git config needed for test repos."""
    subprocess.run(["git", "-C", str(repo), "config", "user.name", "Prompt Test"], check=True)
    subprocess.run(["git", "-C", str(repo), "config", "user.email", "prompt@example.com"], check=True)
    subprocess.run(["git", "-C", str(repo), "config", "commit.gpgsign", "false"], check=True)


def make_repo() -> Path:
    repo = Path(tempfile.mkdtemp(prefix="prompt-repo-")) / "a" / "verylongsegment" / "b" / "repository"
    repo.mkdir(parents=True)
    subprocess.run(["git", "init", str(repo)], check=True, capture_output=True, text=True)
    _git_config_repo(repo)
    (repo / "tracked.txt").write_text("hello\n")
    subprocess.run(["git", "-C", str(repo), "add", "tracked.txt"], check=True)
    subprocess.run(["git", "-C", str(repo), "commit", "-m", "init"], check=True, capture_output=True)
    return repo


def make_branch_repo(prefix: str, branch: str) -> Path:
    repo = Path(tempfile.mkdtemp(prefix=prefix)) / "verylongsegment" / "repo"
    repo.mkdir(parents=True)
    subprocess.run(["git", "init", str(repo)], check=True, capture_output=True, text=True)
    _git_config_repo(repo)
    (repo / "tracked.txt").write_text("hello\n")
    subprocess.run(["git", "-C", str(repo), "add", "tracked.txt"], check=True)
    subprocess.run(["git", "-C", str(repo), "commit", "-m", "init"], check=True, capture_output=True)
    subprocess.run(
        ["git", "-C", str(repo), "checkout", "-b", branch],
        check=True,
        capture_output=True,
        text=True,
    )
    return repo


def make_dirty_branch_repo(prefix: str, branch: str) -> Path:
    """Create a repo with many git status indicators: staged, dirty, untracked, stash."""
    repo = make_branch_repo(prefix, branch)
    # Staged change
    (repo / "staged.txt").write_text("staged\n")
    subprocess.run(["git", "-C", str(repo), "add", "staged.txt"], check=True)
    # Dirty tracked file
    (repo / "tracked.txt").write_text("modified\n")
    # Untracked files
    (repo / "untracked1.txt").write_text("u1\n")
    (repo / "untracked2.txt").write_text("u2\n")
    # Stash
    (repo / "stashme.txt").write_text("stash\n")
    subprocess.run(["git", "-C", str(repo), "add", "stashme.txt"], check=True)
    subprocess.run(
        ["git", "-C", str(repo), "stash", "push", "-m", "test-stash"],
        check=True,
        capture_output=True,
    )
    # Re-stage staged.txt (stash pop may have cleared it)
    (repo / "staged.txt").write_text("staged\n")
    subprocess.run(["git", "-C", str(repo), "add", "staged.txt"], check=True)
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
    result = run_shell(["bash", "--noprofile", "--norc", "-ic"], script)
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
    result = run_shell(["zsh", "-f", "-i", "-c"], script)
    assert result.returncode == 0, result.stderr
    rendered = strip_ansi(last_nonempty_line(result.stdout, "zsh truncation"))
    assert len(rendered) <= 10, rendered
    assert rendered.endswith("delta"), rendered


def test_zsh_prompt_preserves_non_prompt_width():
    if not shell_available("zsh") or not ZSH_PROMPT.exists() or not shutil.which("git"):
        return

    repo = make_branch_repo(
        "zsh-width-",
        "feature/super-long-branch-name-for-prompt-width-testing",
    )
    env = isolated_prompt_env()
    script = textwrap.dedent(
        f"""
        source {ZSH_PROMPT}
        COLUMNS=80
        cd {repo}
        _prompt_build 0
        print -P -- "$PROMPT"
        """
    )
    result = subprocess.run(
        ["zsh", "-f", "-i", "-c", script],
        capture_output=True,
        text=True,
        timeout=15,
        check=False,
        env=env,
    )
    assert result.returncode == 0, result.stderr
    rendered = strip_ansi(last_nonempty_line(result.stdout, "zsh prompt width"))
    assert len(rendered) <= 32, rendered
    assert "prompt-width-testing" not in rendered, rendered
    assert "…" in rendered, rendered


def test_fish_prompt_preserves_non_prompt_width():
    if not shell_available("fish") or not FISH_PROMPT.exists() or not shutil.which("git"):
        return

    repo = make_branch_repo(
        "fish-width-",
        "feature/super-long-branch-name-for-prompt-width-testing",
    )
    env = isolated_prompt_env()
    warm = subprocess.run(
        ["fish", "-c", textwrap.dedent(
            f"""
            source {FISH_PROMPT}
            set -gx COLUMNS 80
            cd {repo}
            fish_prompt >/dev/null
            sleep 0.5
            """
        )],
        capture_output=True,
        text=True,
        timeout=15,
        check=False,
        env=env,
    )
    assert warm.returncode == 0, warm.stderr
    cache, head_cache = prompt_cache_paths(repo, env, "fish")
    cache_text = wait_for_prompt_cache(cache, head_cache)
    # Cache stores raw data (branch\tcounts); verify branch is present
    assert "prompt-width-testing" in cache_text, cache_text

    script = textwrap.dedent(
        f"""
        source {FISH_PROMPT}
        set -gx COLUMNS 80
        cd {repo}
        fish_prompt
        """
    )
    result = subprocess.run(
        ["fish", "-c", script],
        capture_output=True,
        text=True,
        timeout=15,
        check=False,
        env=env,
    )
    assert result.returncode == 0, result.stderr
    rendered = strip_ansi(result.stdout.strip())
    assert len(rendered) <= 32, rendered
    assert "prompt-width-testing" not in rendered, rendered
    assert "…" in rendered, rendered


def test_bash_prompt_preserves_non_prompt_width():
    if not shell_available("bash") or not BASH_PROMPT.exists() or not shutil.which("git"):
        return

    repo = make_branch_repo(
        "bash-width-",
        "feature/super-long-branch-name-for-prompt-width-testing",
    )
    script = textwrap.dedent(
        f"""
        source "{BASH_PROMPT}"
        COLUMNS=80
        cd "{repo}"
        __dot_prompt_precmd
        sleep 0.5
        __dot_prompt_precmd
        printf '%s\n' "$PS1"
        """
    )
    result = run_shell(["bash", "--noprofile", "--norc", "-ic"], script)
    assert result.returncode == 0, result.stderr
    rendered = strip_ansi(last_nonempty_line(result.stdout, "bash prompt width"))
    assert len(rendered) <= 32, rendered
    assert "prompt-width-testing" not in rendered, rendered
    assert "…" in rendered, rendered


def test_zsh_prompt_respects_width_with_many_indicators():
    """Prompt with long branch + dirty/staged/untracked/stash must fit within budget."""
    if not shell_available("zsh") or not ZSH_PROMPT.exists() or not shutil.which("git"):
        return

    repo = make_dirty_branch_repo(
        "zsh-indicators-",
        "feature/super-long-branch-name-for-indicator-testing",
    )
    env = isolated_prompt_env()
    script = textwrap.dedent(
        f"""
        source {ZSH_PROMPT}
        COLUMNS=80
        cd {repo}
        _prompt_build 0
        print -P -- "$PROMPT"
        """
    )
    result = subprocess.run(
        ["zsh", "-f", "-i", "-c", script],
        capture_output=True,
        text=True,
        timeout=15,
        check=False,
        env=env,
    )
    assert result.returncode == 0, result.stderr
    rendered = strip_ansi(last_nonempty_line(result.stdout, "zsh indicator width"))
    # Total prompt must leave at least 48 cols remaining
    assert len(rendered) <= 32, f"prompt too wide ({len(rendered)} chars): {rendered}"


def test_fish_prompt_respects_width_with_many_indicators():
    """Prompt with long branch + dirty/staged/untracked/stash must fit within budget."""
    if not shell_available("fish") or not FISH_PROMPT.exists() or not shutil.which("git"):
        return

    repo = make_dirty_branch_repo(
        "fish-indicators-",
        "feature/super-long-branch-name-for-indicator-testing",
    )
    env = isolated_prompt_env()
    # Warm cache
    warm = subprocess.run(
        ["fish", "-c", textwrap.dedent(
            f"""
            source {FISH_PROMPT}
            set -gx COLUMNS 80
            cd {repo}
            fish_prompt >/dev/null
            sleep 0.5
            """
        )],
        capture_output=True,
        text=True,
        timeout=15,
        check=False,
        env=env,
    )
    assert warm.returncode == 0, warm.stderr

    script = textwrap.dedent(
        f"""
        source {FISH_PROMPT}
        set -gx COLUMNS 80
        cd {repo}
        fish_prompt
        """
    )
    result = subprocess.run(
        ["fish", "-c", script],
        capture_output=True,
        text=True,
        timeout=15,
        check=False,
        env=env,
    )
    assert result.returncode == 0, result.stderr
    rendered = strip_ansi(result.stdout.strip())
    assert len(rendered) <= 32, f"prompt too wide ({len(rendered)} chars): {rendered}"


def test_bash_prompt_respects_width_with_many_indicators():
    """Prompt with long branch + dirty/staged/untracked/stash must fit within budget."""
    if not shell_available("bash") or not BASH_PROMPT.exists() or not shutil.which("git"):
        return

    repo = make_dirty_branch_repo(
        "bash-indicators-",
        "feature/super-long-branch-name-for-indicator-testing",
    )
    script = textwrap.dedent(
        f"""
        source "{BASH_PROMPT}"
        COLUMNS=80
        cd "{repo}"
        __dot_prompt_precmd
        sleep 0.5
        __dot_prompt_precmd
        printf '%s\\n' "$PS1"
        """
    )
    result = run_shell(["bash", "--noprofile", "--norc", "-ic"], script)
    assert result.returncode == 0, result.stderr
    rendered = strip_ansi(last_nonempty_line(result.stdout, "bash indicator width"))
    assert len(rendered) <= 32, f"prompt too wide ({len(rendered)} chars): {rendered}"


def test_bash_prompt_clears_git_segment_after_leaving_repo():
    if not shell_available("bash") or not BASH_PROMPT.exists() or not shutil.which("git"):
        return

    repo = make_repo()
    outside = Path(tempfile.mkdtemp(prefix="bash-outside-")) / "plain"
    outside.mkdir(parents=True)
    script = textwrap.dedent(
        f"""
        source "{BASH_PROMPT}"
        COLUMNS=120
        cd "{repo}"
        __dot_prompt_precmd
        sleep 0.5
        __dot_prompt_precmd
        cd "{outside}"
        __dot_prompt_precmd
        printf '%s\n' "$PS1"
        """
    )
    result = run_shell(["bash", "--noprofile", "--norc", "-ic"], script)
    assert result.returncode == 0, result.stderr
    rendered = strip_ansi(last_nonempty_line(result.stdout, "bash outside repo prompt"))
    assert repo.name not in rendered, rendered
    assert "main" not in rendered and "master" not in rendered, rendered


def test_powershell_prompt_preserves_non_prompt_width():
    if not shell_available("pwsh") or not PWSH_PROMPT.exists() or not shutil.which("git"):
        return

    repo = make_branch_repo(
        "pwsh-width-",
        "feature/super-long-branch-name-for-prompt-width-testing",
    )
    script = textwrap.dedent(
        f"""
        . "{PWSH_PROMPT}"
        Set-Location "{repo}"
        $Host.UI.RawUI.WindowSize = New-Object Management.Automation.Host.Size(80, 40)
        prompt
        """
    )
    result = run_shell(["pwsh", "-NoProfile", "-NonInteractive", "-Command"], script)
    assert result.returncode == 0, result.stderr
    rendered = strip_ansi(last_nonempty_line(result.stdout, "powershell prompt width"))
    assert len(rendered) <= 32, rendered
    assert "prompt-width-testing" not in rendered, rendered
    assert "…" in rendered, rendered


def test_powershell_prompt_renders_stash_count():
    if not shell_available("pwsh") or not PWSH_PROMPT.exists() or not shutil.which("git"):
        return

    repo = make_repo()
    (repo / "tracked.txt").write_text("updated\n")
    subprocess.run(["git", "-C", str(repo), "stash", "push", "-m", "prompt-test"], check=True)
    script = textwrap.dedent(
        f"""
        . "{PWSH_PROMPT}"
        Set-Location "{repo}"
        prompt
        """
    )
    result = run_shell(["pwsh", "-NoProfile", "-NonInteractive", "-Command"], script)
    assert result.returncode == 0, result.stderr
    rendered = strip_ansi(last_nonempty_line(result.stdout, "powershell stash count"))
    assert "*1" in rendered, rendered

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
            for idx in (seq 20)
                fish_prompt >/dev/null
            end
            """
        ),
    )
    elapsed = time.perf_counter() - start
    assert result.returncode == 0, result.stderr
    assert elapsed < 0.5, elapsed


def test_bash_prompt_non_repo_is_fast():
    if not shell_available("bash") or not BASH_PROMPT.exists():
        return

    long_dir = Path(tempfile.mkdtemp(prefix="bash-fast-")) / "outside" / "repo"
    long_dir.mkdir(parents=True)
    result = run_shell(
        ["bash", "--noprofile", "--norc", "-ic"],
        textwrap.dedent(
            f"""
            source "{BASH_PROMPT}"
            COLUMNS=120
            PROMPT_COMMAND=
            cd "{long_dir}"
            start=$EPOCHREALTIME
            for idx in $(seq 20); do
                __dot_prompt_precmd
            done
            end=$EPOCHREALTIME
            python3 - "$start" "$end" <<'PY'
import sys
print(float(sys.argv[2]) - float(sys.argv[1]))
PY
            """
        ),
    )
    assert result.returncode == 0, result.stderr
    elapsed = float(last_nonempty_line(result.stdout, "bash non-repo timing"))
    assert elapsed < 0.9, elapsed


def test_fish_prompt_git_refresh_is_async():
    """After initial sync populate, subsequent cache refreshes are async (non-blocking)."""
    if not shell_available("fish") or not FISH_PROMPT.exists() or not shutil.which("git"):
        return

    repo = make_repo()
    slow_git_dir = make_slow_git_dir()
    prompt_path = os.pathsep.join([str(slow_git_dir), os.environ.get("PATH", "")])
    # First prompt does a sync fetch (populates cache).
    # Second prompt should be fast — cache hit, async refresh in background.
    result = run_shell(
        ["env", f"PATH={prompt_path}", "fish", "-c"],
        textwrap.dedent(
            f"""
            source {FISH_PROMPT}
            set -gx COLUMNS 120
            cd {repo}
            fish_prompt >/dev/null
            set -l t0 (date +%s%N)
            fish_prompt >/dev/null
            set -l t1 (date +%s%N)
            math "($t1 - $t0) / 1000000000.0"
            """
        ),
        timeout=20,
    )
    assert result.returncode == 0, result.stderr
    elapsed = float(last_nonempty_line(result.stdout, "fish async timing"))
    assert elapsed < 0.18, elapsed


def test_bash_prompt_git_refresh_is_async():
    """After initial sync populate, subsequent cache refreshes are async (non-blocking)."""
    if not shell_available("bash") or not BASH_PROMPT.exists() or not shutil.which("git"):
        return

    repo = make_repo()
    slow_git_dir = make_slow_git_dir()
    prompt_path = os.pathsep.join([str(slow_git_dir), os.environ.get("PATH", "")])
    result = run_shell(
        ["env", f"PATH={prompt_path}", "bash", "--noprofile", "--norc", "-ic"],
        textwrap.dedent(
            f"""
            source "{BASH_PROMPT}"
            COLUMNS=120
            cd "{repo}"
            # First prompt: sync (populates cache, may be slow with slow git)
            __dot_prompt_precmd
            # Second prompt: should be fast (cache hit, async refresh)
            start=$EPOCHREALTIME
            __dot_prompt_precmd
            end=$EPOCHREALTIME
            python3 - "$start" "$end" <<'PY'
import sys
print(float(sys.argv[2]) - float(sys.argv[1]))
PY
            """
        ),
        timeout=20,
    )
    assert result.returncode == 0, result.stderr
    elapsed = float(last_nonempty_line(result.stdout, "bash async timing"))
    assert elapsed < 0.18, elapsed


def test_fish_prompt_uses_cached_git_segment_without_sync_rebuild():
    if not shell_available("fish") or not FISH_PROMPT.exists() or not shutil.which("git"):
        return

    repo = make_branch_repo(
        "fish-cache-",
        "feature/super-long-branch-name-for-prompt-width-testing",
    )
    slow_git_dir = make_slow_git_dir()
    warm_env = isolated_prompt_env()
    warm = subprocess.run(
        ["fish", "-c", textwrap.dedent(
            f"""
            source {FISH_PROMPT}
            set -gx COLUMNS 80
            cd {repo}
            fish_prompt >/dev/null
            sleep 0.5
            fish_prompt >/dev/null
            """
        )],
        capture_output=True,
        text=True,
        timeout=20,
        check=False,
        env=warm_env,
    )
    assert warm.returncode == 0, warm.stderr
    cache, head_cache = prompt_cache_paths(repo, warm_env, "fish")
    cache_text = wait_for_prompt_cache(cache, head_cache)
    # Cache stores raw data (branch\tcounts); verify branch is present
    assert "prompt-width-testing" in cache_text, cache_text

    env = warm_env.copy()
    env["PATH"] = os.pathsep.join([str(slow_git_dir), env.get("PATH", "")])
    start = time.perf_counter()
    result = subprocess.run(
        ["fish", "-c", textwrap.dedent(
            f"""
            source {FISH_PROMPT}
            set -gx COLUMNS 80
            cd {repo}
            fish_prompt
            """
        )],
        capture_output=True,
        text=True,
        timeout=20,
        check=False,
        env=env,
    )
    elapsed = time.perf_counter() - start
    assert result.returncode == 0, result.stderr
    assert elapsed < 0.18, elapsed
    rendered = strip_ansi(result.stdout.strip())
    assert "prompt-width-testing" not in rendered, rendered
    assert "…" in rendered, rendered


def test_bash_prompt_uses_cached_git_segment_without_sync_rebuild():
    if not shell_available("bash") or not BASH_PROMPT.exists() or not shutil.which("git"):
        return

    repo = make_branch_repo(
        "bash-cache-",
        "feature/super-long-branch-name-for-prompt-width-testing",
    )
    warm = run_shell(
        ["bash", "--noprofile", "--norc", "-ic"],
        textwrap.dedent(
            f"""
            source "{BASH_PROMPT}"
            COLUMNS=80
            cd "{repo}"
            __dot_prompt_precmd
            sleep 0.5
            __dot_prompt_precmd
            """
        ),
        timeout=20,
    )
    assert warm.returncode == 0, warm.stderr

    slow_git_dir = make_slow_git_dir()
    prompt_path = os.pathsep.join([str(slow_git_dir), os.environ.get("PATH", "")])
    result = run_shell(
        ["env", f"PATH={prompt_path}", "bash", "--noprofile", "--norc", "-ic"],
        textwrap.dedent(
            f"""
            source "{BASH_PROMPT}"
            COLUMNS=80
            cd "{repo}"
            start=$EPOCHREALTIME
            __dot_prompt_precmd
            end=$EPOCHREALTIME
            printf '%s\\n' "$PS1"
            python3 - "$start" "$end" <<'PY'
import sys
print(float(sys.argv[2]) - float(sys.argv[1]))
PY
            """
        ),
        timeout=20,
    )
    assert result.returncode == 0, result.stderr
    lines = [line for line in result.stdout.splitlines() if line.strip()]
    assert len(lines) >= 2, result.stdout
    rendered = strip_ansi(lines[-2])
    elapsed = float(lines[-1])
    assert elapsed < 0.18, elapsed
    assert "prompt-width-testing" not in rendered, rendered
    assert "…" in rendered, rendered


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
        ["bash", "--noprofile", "--norc", "-ic"],
        textwrap.dedent(
            f"""
            source "{BASH_PROMPT}"
            COLUMNS=120
            cd "{repo}"
            __dot_prompt_precmd
            for idx in $(seq 20); do
                sleep 0.2
                __dot_prompt_precmd
                case "$PS1" in
                    *main*|*master*)
                        printf 'ok\n'
                        exit 0
                        ;;
                esac
            done
            printf '%s\n' "$PS1"
            exit 1
            """
        ),
        timeout=20,
    )
    rendered = strip_ansi(result.stdout.strip() or result.stderr)
    assert result.returncode == 0, rendered


def make_worktree_repo() -> tuple[Path, Path]:
    """Create a repo with a linked worktree.  Returns (main_repo, worktree)."""
    main = Path(tempfile.mkdtemp(prefix="prompt-wt-main-")) / "repo"
    main.mkdir(parents=True)
    subprocess.run(["git", "init", str(main)], check=True, capture_output=True, text=True)
    _git_config_repo(main)
    (main / "tracked.txt").write_text("hello\n")
    subprocess.run(["git", "-C", str(main), "add", "tracked.txt"], check=True)
    subprocess.run(["git", "-C", str(main), "commit", "-m", "init"], check=True, capture_output=True)
    wt = Path(tempfile.mkdtemp(prefix="prompt-wt-tree-"))
    shutil.rmtree(wt)  # git worktree add needs a non-existing target
    subprocess.run(
        ["git", "-C", str(main), "worktree", "add", str(wt), "-b", "wt-branch"],
        check=True, capture_output=True, text=True,
    )
    return main, wt


def test_bash_prompt_worktree_shows_git_info():
    """First prompt in a worktree must show git info (no async wait)."""
    if not shell_available("bash") or not BASH_PROMPT.exists() or not shutil.which("git"):
        return

    _main, wt = make_worktree_repo()
    env = isolated_prompt_env()
    result = run_shell(
        ["bash", "--noprofile", "--norc", "-ic"],
        textwrap.dedent(
            f"""
            export HOME="{env['HOME']}"
            export XDG_CACHE_HOME="{env['XDG_CACHE_HOME']}"
            source "{BASH_PROMPT}"
            COLUMNS=120
            cd "{wt}"
            __dot_prompt_precmd
            printf '%s\\n' "$PS1"
            """
        ),
        timeout=10,
    )
    assert result.returncode == 0, result.stderr
    assert "wt-branch" in result.stdout, (
        f"first prompt in worktree must show branch: {strip_ansi(result.stdout)!r}"
    )


def test_bash_prompt_worktree_shows_indicator():
    """First prompt in a worktree includes the ⊕ prefix."""
    if not shell_available("bash") or not BASH_PROMPT.exists() or not shutil.which("git"):
        return

    _main, wt = make_worktree_repo()
    env = isolated_prompt_env()
    result = run_shell(
        ["bash", "--noprofile", "--norc", "-ic"],
        textwrap.dedent(
            f"""
            export HOME="{env['HOME']}"
            export XDG_CACHE_HOME="{env['XDG_CACHE_HOME']}"
            source "{BASH_PROMPT}"
            COLUMNS=120
            cd "{wt}"
            __dot_prompt_precmd
            printf '%s\\n' "$PS1"
            """
        ),
        timeout=10,
    )
    assert result.returncode == 0, result.stderr
    rendered = result.stdout
    assert "⊕" in rendered, (
        f"first prompt in worktree must show ⊕ indicator: {strip_ansi(rendered)!r}"
    )


def test_bash_prompt_non_worktree_no_indicator():
    """Regular repo prompt does NOT include the ⊕ prefix."""
    if not shell_available("bash") or not BASH_PROMPT.exists() or not shutil.which("git"):
        return

    repo = make_repo()
    env = isolated_prompt_env()
    result = run_shell(
        ["bash", "--noprofile", "--norc", "-ic"],
        textwrap.dedent(
            f"""
            export HOME="{env['HOME']}"
            export XDG_CACHE_HOME="{env['XDG_CACHE_HOME']}"
            source "{BASH_PROMPT}"
            COLUMNS=120
            cd "{repo}"
            __dot_prompt_precmd
            for idx in $(seq 20); do
                sleep 0.2
                __dot_prompt_precmd
                case "$PS1" in
                    *main*|*master*)
                        case "$PS1" in
                            *⊕*)
                                printf 'unexpected-indicator\\n'
                                exit 1
                                ;;
                            *)
                                printf 'ok\\n'
                                exit 0
                                ;;
                        esac
                        ;;
                esac
            done
            printf '%s\\n' "$PS1"
            exit 1
            """
        ),
        timeout=20,
    )
    rendered = strip_ansi(result.stdout.strip() or result.stderr)
    assert result.returncode == 0, f"regular repo should not have ⊕: {rendered}"


def test_fish_prompt_worktree_shows_git_info():
    """First prompt in a worktree shows git info (Fish)."""
    if not shell_available("fish") or not FISH_PROMPT.exists() or not shutil.which("git"):
        return

    _main, wt = make_worktree_repo()
    result = run_shell(
        ["fish", "-c"],
        textwrap.dedent(
            f"""
            source {FISH_PROMPT}
            set -gx COLUMNS 120
            cd {wt}
            fish_prompt
            """
        ),
        timeout=20,
    )
    assert result.returncode == 0, result.stderr
    rendered = strip_ansi(result.stdout.strip())
    assert "wt-branch" in rendered, f"first prompt in worktree must show branch: {rendered!r}"


def test_fish_prompt_worktree_shows_indicator():
    """First prompt in a worktree includes the ⊕ prefix (Fish)."""
    if not shell_available("fish") or not FISH_PROMPT.exists() or not shutil.which("git"):
        return

    _main, wt = make_worktree_repo()
    result = run_shell(
        ["fish", "-c"],
        textwrap.dedent(
            f"""
            source {FISH_PROMPT}
            set -gx COLUMNS 120
            cd {wt}
            fish_prompt
            """
        ),
        timeout=20,
    )
    assert result.returncode == 0, result.stderr
    rendered = strip_ansi(result.stdout.strip())
    assert "⊕" in rendered, f"first prompt in worktree must show ⊕: {rendered!r}"


TESTS = [
    test_fish_prompt_truncates_paths,
    test_bash_prompt_truncates_paths,
    test_zsh_prompt_truncates_paths,
    test_fish_prompt_preserves_non_prompt_width,
    test_bash_prompt_preserves_non_prompt_width,
    test_bash_prompt_clears_git_segment_after_leaving_repo,
    test_zsh_prompt_preserves_non_prompt_width,
    test_powershell_prompt_preserves_non_prompt_width,
    test_zsh_prompt_respects_width_with_many_indicators,
    test_fish_prompt_respects_width_with_many_indicators,
    test_bash_prompt_respects_width_with_many_indicators,
    test_powershell_prompt_renders_stash_count,
    test_fish_prompt_non_repo_is_fast,
    test_bash_prompt_non_repo_is_fast,
    test_fish_prompt_eventually_renders_git_info,
    test_bash_prompt_eventually_renders_git_info,
    test_fish_prompt_git_refresh_is_async,
    test_bash_prompt_git_refresh_is_async,
    test_fish_prompt_uses_cached_git_segment_without_sync_rebuild,
    test_bash_prompt_uses_cached_git_segment_without_sync_rebuild,
    test_bash_prompt_worktree_shows_git_info,
    test_bash_prompt_worktree_shows_indicator,
    test_bash_prompt_non_worktree_no_indicator,
    test_fish_prompt_worktree_shows_git_info,
    test_fish_prompt_worktree_shows_indicator,
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
