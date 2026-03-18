#!/usr/bin/env python3
"""
Tests for the bootstrap.sh script.

Runs bootstrap.sh with a fake HOME, then verifies the resulting file
tree matches what chezmoi apply would produce.

Run with: python3 .tests/test_bootstrap.py
"""

import os
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

REPO_ROOT = Path(__file__).parent.parent
BOOTSTRAP = REPO_ROOT / "bootstrap.sh"

# Populated by run_bootstrap(), used by every test.
HOME_DIR: Path = None
CONFIG_DIR: Path = None


# ---- helpers -----------------------------------------------------------

def run_bootstrap():
    """Run bootstrap.sh in an isolated HOME directory."""
    global HOME_DIR, CONFIG_DIR
    # Use TMPDIR so this works inside sandboxed environments.
    base = os.environ.get("TMPDIR", tempfile.gettempdir())
    HOME_DIR = Path(tempfile.mkdtemp(prefix="bootstrap-test-", dir=base))
    CONFIG_DIR = HOME_DIR / ".config"

    env = os.environ.copy()
    env["HOME"] = str(HOME_DIR)
    env["XDG_CONFIG_HOME"] = str(CONFIG_DIR)

    result = subprocess.run(
        ["/bin/sh", str(BOOTSTRAP)],
        input="Test User\ntest@example.com\n",
        capture_output=True,
        text=True,
        env=env,
        timeout=30,
    )
    if result.returncode != 0:
        print(f"bootstrap.sh failed (exit {result.returncode}):")
        print(result.stdout)
        print(result.stderr)
        sys.exit(2)
    return result


def cleanup():
    if HOME_DIR and HOME_DIR.exists():
        shutil.rmtree(HOME_DIR)


def rel(path: Path) -> str:
    """Path relative to HOME_DIR for readable assertions."""
    return str(path.relative_to(HOME_DIR))


# ---- gitconfig ---------------------------------------------------------

def test_gitconfig_exists():
    """bootstrap must create ~/.gitconfig."""
    assert (HOME_DIR / ".gitconfig").is_file(), \
        "~/.gitconfig not created"


def test_gitconfig_has_user():
    """~/.gitconfig must contain the prompted name and email."""
    content = (HOME_DIR / ".gitconfig").read_text()
    assert "test@example.com" in content, \
        ".gitconfig missing email"
    assert "Test User" in content, \
        ".gitconfig missing name"


def test_gitconfig_no_template_directives():
    """~/.gitconfig must not contain Go template syntax."""
    content = (HOME_DIR / ".gitconfig").read_text()
    assert "{{" not in content, \
        ".gitconfig still contains Go template directives"


def test_gitconfig_includes_local():
    """~/.gitconfig must include ~/.gitconfig.local."""
    content = (HOME_DIR / ".gitconfig").read_text()
    assert "~/.gitconfig.local" in content, \
        ".gitconfig missing [include] for .gitconfig.local"


def test_gitconfig_no_orphan_include():
    """~/.gitconfig must not end with an empty [include] section."""
    content = (HOME_DIR / ".gitconfig").read_text().rstrip()
    assert not content.endswith("[include]"), \
        ".gitconfig ends with orphan [include] (no path)"


# ---- shell init files --------------------------------------------------

def test_bashrc_exists():
    assert (HOME_DIR / ".bashrc").is_file(), \
        "~/.bashrc not created"


def test_bash_profile_exists():
    assert (HOME_DIR / ".bash_profile").is_file(), \
        "~/.bash_profile not created"


def test_zshenv_exists():
    assert (HOME_DIR / ".zshenv").is_file(), \
        "~/.zshenv not created"


def test_tmux_conf_exists():
    assert (HOME_DIR / ".tmux.conf").is_file(), \
        "~/.tmux.conf not created"


# ---- shell generator output --------------------------------------------

def test_shellgen_fish_functions():
    """Shell generator must produce fish functions."""
    funcs = CONFIG_DIR / "fish" / "functions"
    assert funcs.is_dir(), f"{rel(funcs)} not found"
    assert any(funcs.glob("*.fish")), \
        f"no .fish files in {rel(funcs)}"


def test_shellgen_zsh_zfunctions():
    """Shell generator must produce zsh zfunctions."""
    funcs = CONFIG_DIR / "zsh" / ".zfunctions"
    assert funcs.is_dir(), f"{rel(funcs)} not found"
    assert any(funcs.iterdir()), \
        f"no files in {rel(funcs)}"


def test_shellgen_bash_functions():
    """Shell generator must produce bash functions."""
    funcs = CONFIG_DIR / "bash" / "functions"
    assert funcs.is_dir(), f"{rel(funcs)} not found"
    assert any(funcs.glob("*.bash")), \
        f"no .bash files in {rel(funcs)}"


def test_shellgen_powershell_functions():
    """Shell generator must produce powershell functions."""
    funcs = CONFIG_DIR / "powershell" / "functions"
    assert funcs.is_dir(), f"{rel(funcs)} not found"
    assert any(funcs.glob("*.ps1")), \
        f"no .ps1 files in {rel(funcs)}"


# ---- chezmoi name translation (dot_ -> .) -----------------------------

def test_zsh_dotfiles_translated():
    """dot_ prefixes inside dot_config/zsh/ must become . prefixes."""
    assert (CONFIG_DIR / "zsh" / ".zshrc").is_file(), \
        "dot_zshrc not translated to .zshrc"
    assert (CONFIG_DIR / "zsh" / ".zshenv").is_file(), \
        "dot_zshenv not translated to .zshenv"
    assert (CONFIG_DIR / "zsh" / ".zsh_plugins.txt").is_file(), \
        "dot_zsh_plugins.txt not translated to .zsh_plugins.txt"


def test_zshrc_d_translated():
    """dot_zshrc.d/ must become .zshrc.d/ with contents."""
    d = CONFIG_DIR / "zsh" / ".zshrc.d"
    assert d.is_dir(), f"{rel(d)} not found"
    zsh_files = list(d.glob("*.zsh"))
    assert len(zsh_files) >= 5, \
        f"expected >= 5 .zsh modules in .zshrc.d, got {len(zsh_files)}"


def test_zfunctions_dir_translated():
    """dot_zfunctions/ must become .zfunctions/."""
    d = CONFIG_DIR / "zsh" / ".zfunctions"
    assert d.is_dir(), f"{rel(d)} not found"


# ---- config directories present ---------------------------------------

def test_fish_config_dir():
    assert (CONFIG_DIR / "fish" / "config.fish").is_file(), \
        "fish/config.fish not found"


def test_fish_conf_d():
    d = CONFIG_DIR / "fish" / "conf.d"
    assert d.is_dir(), f"{rel(d)} not found"
    assert any(d.glob("*.fish")), f"no .fish files in {rel(d)}"


def test_bash_bashrc_d():
    d = CONFIG_DIR / "bash" / "bashrc.d"
    assert d.is_dir(), f"{rel(d)} not found"
    assert any(d.glob("*.bash")), f"no .bash files in {rel(d)}"


def test_powershell_profile():
    assert (CONFIG_DIR / "powershell" /
            "Microsoft.PowerShell_profile.ps1").is_file(), \
        "powershell/Microsoft.PowerShell_profile.ps1 not found"


def test_tmux_config_dir():
    assert (CONFIG_DIR / "tmux" / "tmux.conf").is_file(), \
        "tmux/tmux.conf not found"


def test_mise_config():
    assert (CONFIG_DIR / "mise" / "config.toml").is_file(), \
        "mise/config.toml not found"


def test_ghostty_config():
    assert (CONFIG_DIR / "ghostty" / "config").is_file(), \
        "ghostty/config not found"


def test_nvim_config():
    assert (CONFIG_DIR / "nvim" / "init.lua").is_file(), \
        "nvim/init.lua not found"


# ---- nothing that shouldn't be there ----------------------------------

def test_no_gitignore_files():
    """No .gitignore files should appear in the bootstrapped output."""
    gitignores = list(CONFIG_DIR.rglob(".gitignore"))
    assert len(gitignores) == 0, \
        f"found .gitignore files that should not be deployed: " \
        f"{[str(g.relative_to(CONFIG_DIR)) for g in gitignores]}"


def test_no_tmpl_files():
    """Bootstrap must not copy .tmpl files into config dirs."""
    tmpls = list(CONFIG_DIR.rglob("*.tmpl"))
    assert len(tmpls) == 0, \
        f"found .tmpl files that should have been skipped: " \
        f"{[str(t.relative_to(CONFIG_DIR)) for t in tmpls]}"


def test_no_ds_store():
    """.DS_Store files must not be copied."""
    ds = list(CONFIG_DIR.rglob(".DS_Store")) + \
        list(CONFIG_DIR.rglob("dot_DS_Store"))
    assert len(ds) == 0, \
        f"found .DS_Store files: " \
        f"{[str(d.relative_to(CONFIG_DIR)) for d in ds]}"


# ---- idempotency ------------------------------------------------------

def test_rerun_is_safe():
    """Running bootstrap a second time must not fail."""
    env = os.environ.copy()
    env["HOME"] = str(HOME_DIR)
    env["XDG_CONFIG_HOME"] = str(CONFIG_DIR)
    result = subprocess.run(
        ["/bin/sh", str(BOOTSTRAP)],
        input="Ignored\nignored@ignored.com\n",
        capture_output=True,
        text=True,
        env=env,
        timeout=30,
    )
    assert result.returncode == 0, \
        f"second run failed (exit {result.returncode}): " \
        f"stdout={result.stdout} stderr={result.stderr}"


def test_rerun_preserves_gitconfig():
    """Second run must not overwrite existing .gitconfig."""
    content = (HOME_DIR / ".gitconfig").read_text()
    assert "test@example.com" in content, \
        "second run overwrote .gitconfig (should have skipped)"
    assert "ignored@ignored.com" not in content, \
        "second run overwrote .gitconfig with new values"


# ---- runner ------------------------------------------------------------

def run_all_tests():
    tests = [
        # gitconfig
        test_gitconfig_exists,
        test_gitconfig_has_user,
        test_gitconfig_no_template_directives,
        test_gitconfig_includes_local,
        test_gitconfig_no_orphan_include,
        # shell init files
        test_bashrc_exists,
        test_bash_profile_exists,
        test_zshenv_exists,
        test_tmux_conf_exists,
        # shell generator
        test_shellgen_fish_functions,
        test_shellgen_zsh_zfunctions,
        test_shellgen_bash_functions,
        test_shellgen_powershell_functions,
        # chezmoi name translation
        test_zsh_dotfiles_translated,
        test_zshrc_d_translated,
        test_zfunctions_dir_translated,
        # config directories
        test_fish_config_dir,
        test_fish_conf_d,
        test_bash_bashrc_d,
        test_powershell_profile,
        test_tmux_config_dir,
        test_mise_config,
        test_ghostty_config,
        test_nvim_config,
        # exclusions
        test_no_gitignore_files,
        test_no_tmpl_files,
        test_no_ds_store,
        # idempotency (must run last — re-runs bootstrap)
        test_rerun_is_safe,
        test_rerun_preserves_gitconfig,
    ]

    print("Running bootstrap.sh...")
    run_bootstrap()
    print(f"Bootstrap output in: {HOME_DIR}\n")

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

    cleanup()
    return 0 if failed == 0 else 1


if __name__ == "__main__":
    sys.exit(run_all_tests())
