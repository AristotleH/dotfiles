#!/usr/bin/env python3
"""
Tests for zsh configuration files.

Validates syntax, load order, structure, plugin configuration, and absence
of dead code in the chezmoi-managed zsh config.

Run with: python3 .tests/test_zsh.py
"""

import re
import subprocess
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).parent.parent
ZSH_DIR = REPO_ROOT / "dot_config" / "zsh"
ZSHRC = ZSH_DIR / "dot_zshrc"
ZSHRC_D = ZSH_DIR / "dot_zshrc.d"
ZSHENV = ZSH_DIR / "dot_zshenv"
PLUGINS_TXT = ZSH_DIR / "dot_zsh_plugins.txt"
P10K = ZSH_DIR / "dot_p10k.zsh"
ZFUNCTIONS = ZSH_DIR / "dot_zfunctions"

# Expected numeric prefix pattern: NN-name.zsh
NUMBERED_RE = re.compile(r"^\d{2}-.+\.zsh$")


# ---- File existence & structure ----

def test_zshrc_exists():
    """dot_zshrc must exist."""
    assert ZSHRC.is_file(), f"{ZSHRC} not found"


def test_zshenv_exists():
    """dot_zshenv must exist."""
    assert ZSHENV.is_file(), f"{ZSHENV} not found"


def test_zshrc_d_exists():
    """dot_zshrc.d directory must exist."""
    assert ZSHRC_D.is_dir(), f"{ZSHRC_D} not found"


def test_zfunctions_dir_exists():
    """dot_zfunctions directory must exist."""
    assert ZFUNCTIONS.is_dir(), f"{ZFUNCTIONS} not found"


def test_plugins_txt_exists():
    """dot_zsh_plugins.txt must exist (antidote plugin list)."""
    assert PLUGINS_TXT.is_file(), f"{PLUGINS_TXT} not found"


def test_p10k_config_exists():
    """dot_p10k.zsh must exist (powerlevel10k configuration)."""
    assert P10K.is_file(), f"{P10K} not found"


# ---- .zshrc.d load order ----

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


def test_zshrc_d_files_have_shebang():
    """Hand-managed .zsh files in .zshrc.d/ should start with #!/bin/zsh."""
    gitignore = (ZSHRC_D / ".gitignore").read_text() if (ZSHRC_D / ".gitignore").exists() else ""
    generated = {l.strip() for l in gitignore.splitlines()
                 if l.strip() and not l.strip().startswith("#")}

    missing = []
    for f in sorted(ZSHRC_D.glob("*.zsh")):
        if f.name in generated:
            continue
        first_line = f.read_text().splitlines()[0] if f.read_text().strip() else ""
        if not first_line.startswith("#!"):
            missing.append(f.name)

    assert not missing, (
        f".zshrc.d files missing shebang (#!/bin/zsh): {missing}"
    )


# ---- Syntax check ----

def test_zsh_syntax():
    """All .zsh files must pass zsh -n syntax check."""
    try:
        result = subprocess.run(["zsh", "--version"], capture_output=True, text=True)
    except FileNotFoundError:
        print("SKIP: zsh not available")
        return
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


# ---- dot_zshrc structure ----

def test_zshrc_sources_zshrc_d():
    """dot_zshrc must have the glob loop that sources .zshrc.d/*.zsh."""
    content = ZSHRC.read_text()
    assert ".zshrc.d/*.zsh" in content, (
        "dot_zshrc missing .zshrc.d/*.zsh sourcing loop"
    )


def test_zshrc_instant_prompt_at_top():
    """Powerlevel10k instant prompt must be near the top of dot_zshrc.

    p10k instant prompt enables the prompt to appear before the rest of
    the config finishes loading. Any console output before it breaks
    the feature.
    """
    content = ZSHRC.read_text()
    p10k_pos = content.find("p10k-instant-prompt")
    assert p10k_pos != -1, "Missing p10k instant prompt block"
    # Should be in the first 5 non-blank lines
    lines = [l for l in content.splitlines() if l.strip()]
    found_in_first_5 = any("p10k-instant-prompt" in l for l in lines[:5])
    assert found_in_first_5, (
        "p10k instant prompt must be in the first few lines of dot_zshrc"
    )


def test_zshrc_loads_p10k():
    """dot_zshrc must source the p10k configuration file."""
    content = ZSHRC.read_text()
    assert ".p10k.zsh" in content, "dot_zshrc missing p10k.zsh sourcing"


def test_zshrc_supports_local_override():
    """dot_zshrc must source .zshrc.local if it exists."""
    content = ZSHRC.read_text()
    assert ".zshrc.local" in content, (
        "dot_zshrc missing local override support (.zshrc.local)"
    )


def test_zshrc_local_override_at_end():
    """Local overrides should be sourced after everything else in dot_zshrc."""
    content = ZSHRC.read_text()
    local_pos = content.find(".zshrc.local")
    zshrc_d_pos = content.find(".zshrc.d/*.zsh")
    assert local_pos > zshrc_d_pos, (
        ".zshrc.local must be sourced AFTER .zshrc.d modules"
    )


def test_zshrc_autoloads_zfunctions():
    """dot_zshrc must set up fpath and autoload custom functions."""
    content = ZSHRC.read_text()
    assert ".zfunctions" in content, "dot_zshrc missing .zfunctions in fpath"
    assert "autoload" in content, "dot_zshrc missing autoload for .zfunctions"


# ---- Plugin configuration ----

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


def test_plugins_has_autocomplete():
    """Plugin list must include zsh-autocomplete."""
    content = PLUGINS_TXT.read_text()
    assert "zsh-autocomplete" in content, (
        "dot_zsh_plugins.txt missing marlonrichert/zsh-autocomplete"
    )


def test_plugins_has_syntax_highlighting():
    """Plugin list must include syntax highlighting."""
    content = PLUGINS_TXT.read_text()
    assert "syntax-highlighting" in content, (
        "dot_zsh_plugins.txt missing syntax highlighting plugin"
    )


def test_plugins_syntax_highlighting_before_autocomplete():
    """syntax-highlighting must load before zsh-autocomplete.

    zsh-autocomplete wraps ZLE widgets at load time. If syntax-highlighting
    loads after autocomplete, its widgets are unknown and you get
    'unhandled ZLE widget' warnings.
    """
    # Only check active (uncommented) plugin lines
    active_lines = [
        l.strip() for l in PLUGINS_TXT.read_text().splitlines()
        if l.strip() and not l.strip().startswith("#")
    ]
    sh_idx = None
    ac_idx = None
    for i, line in enumerate(active_lines):
        if "syntax-highlighting" in line:
            sh_idx = i
        if "zsh-autocomplete" in line:
            ac_idx = i
    assert sh_idx is not None, "Missing syntax-highlighting plugin"
    assert ac_idx is not None, "Missing zsh-autocomplete plugin"
    assert sh_idx < ac_idx, (
        "syntax-highlighting must load BEFORE zsh-autocomplete to avoid "
        "'unhandled ZLE widget' warnings"
    )


def test_plugins_no_compinit():
    """Plugin list must NOT include ez-compinit (zsh-autocomplete calls compinit)."""
    content = PLUGINS_TXT.read_text()
    # Only check uncommented lines
    active_lines = [
        l for l in content.splitlines()
        if l.strip() and not l.strip().startswith("#")
    ]
    for line in active_lines:
        assert "compinit" not in line.lower(), (
            f"Found compinit plugin in active plugins: {line}\n"
            "zsh-autocomplete calls compinit itself"
        )


# ---- dot_zshenv ----

def test_zshenv_sets_zdotdir():
    """dot_zshenv must set ZDOTDIR to XDG-compliant location."""
    content = ZSHENV.read_text()
    assert "ZDOTDIR" in content, "dot_zshenv missing ZDOTDIR"


def test_zshenv_sets_xdg_dirs():
    """dot_zshenv must set XDG base directory variables."""
    content = ZSHENV.read_text()
    for var in ["XDG_CONFIG_HOME", "XDG_CACHE_HOME", "XDG_DATA_HOME", "XDG_STATE_HOME"]:
        assert var in content, f"dot_zshenv missing {var}"


def test_zshenv_deduplicates_path():
    """dot_zshenv should use typeset -U to prevent PATH duplicates."""
    content = ZSHENV.read_text()
    assert "typeset -gU" in content or "typeset -U" in content, (
        "dot_zshenv should use 'typeset -gU' to deduplicate path arrays"
    )


def test_zshenv_no_interactive_code():
    """dot_zshenv runs for ALL shell types and must not have interactive code.

    Interactive commands (prompt setup, key bindings, aliases) belong in
    zshrc, not zshenv.
    """
    content = ZSHENV.read_text()
    bad_patterns = [
        (r'\bbindkey\b', "bindkey (key bindings)"),
        (r'\balias\b', "alias definitions"),
        (r'\bprompt\b', "prompt configuration"),
        (r'\bcompinit\b', "compinit (completion init)"),
    ]

    violations = []
    for pattern, desc in bad_patterns:
        for i, line in enumerate(content.splitlines(), 1):
            if line.strip().startswith("#"):
                continue
            if re.search(pattern, line):
                violations.append(f"  line {i}: {desc} — {line.strip()}")

    assert not violations, (
        "dot_zshenv contains interactive code (should be in dot_zshrc):\n"
        + "\n".join(violations)
    )


# ---- Autocomplete configuration ----

def test_autocomplete_min_input_not_zero():
    """min-input must not be 0 — showing completions on empty line is noisy."""
    content = ZSHRC.read_text()
    match = re.search(r"min-input\s+(\d+)", content)
    assert match, "Missing min-input zstyle for autocomplete"
    value = int(match.group(1))
    assert value >= 1, (
        f"min-input is {value} — should be >= 1 to avoid showing "
        "completions below an empty command line"
    )


def test_autocomplete_post_plugin_uses_precmd():
    """30-autocomplete.zsh must use a precmd hook to set up key bindings.

    zsh-autocomplete creates widgets in a precmd hook, so post-plugin
    bindings must also use precmd to run after the widgets exist.
    """
    ac_file = ZSHRC_D / "30-autocomplete.zsh"
    if not ac_file.exists():
        return
    content = ac_file.read_text()
    assert "add-zsh-hook" in content, (
        "30-autocomplete.zsh should use add-zsh-hook precmd for setup"
    )
    assert "precmd" in content, (
        "30-autocomplete.zsh should use a precmd hook"
    )


def test_autocomplete_binds_menu_select():
    """Post-plugin autocomplete setup should bind Tab to menu-select."""
    ac_file = ZSHRC_D / "30-autocomplete.zsh"
    if not ac_file.exists():
        return
    content = ac_file.read_text()
    assert "menu-select" in content, (
        "30-autocomplete.zsh should bind Tab to menu-select"
    )


# ---- Options (05-options.zsh) ----

def test_options_file_exists():
    """05-options.zsh must exist for shell options."""
    opts_file = ZSHRC_D / "05-options.zsh"
    assert opts_file.is_file(), "05-options.zsh not found"


def test_history_file_xdg_compliant():
    """History file should be stored under XDG_STATE_HOME, not $HOME."""
    opts_file = ZSHRC_D / "05-options.zsh"
    if not opts_file.exists():
        return
    content = opts_file.read_text()
    assert "HISTFILE" in content, "05-options.zsh missing HISTFILE"
    # Should reference XDG_STATE_HOME, not bare $HOME/.zsh_history
    assert "XDG_STATE_HOME" in content, (
        "HISTFILE should use XDG_STATE_HOME for XDG compliance"
    )


def test_no_duplicate_setopts():
    """No option should be set/unset more than once across all .zshrc.d files."""
    seen = {}  # option_name -> (file, line)
    setopt_re = re.compile(r'^\s*setopt\s+(\w+)', re.IGNORECASE)
    no_re = re.compile(r'^\s*setopt\s+NO_?(\w+)', re.IGNORECASE)

    for f in sorted(ZSHRC_D.glob("*.zsh")):
        for i, line in enumerate(f.read_text().splitlines(), 1):
            if line.strip().startswith("#"):
                continue
            m = setopt_re.match(line)
            if m:
                opt = m.group(1).lower()
                key = f"setopt:{opt}"
                if key in seen:
                    prev_file, prev_line = seen[key]
                    assert False, (
                        f"Duplicate setopt {opt}: "
                        f"{f.name}:{i} and {prev_file}:{prev_line}"
                    )
                seen[key] = (f.name, i)


# ---- gitignore ----

def test_gitignore_covers_generated_files():
    """.zshrc.d/.gitignore must list generated files."""
    gi = ZSHRC_D / ".gitignore"
    if not gi.exists():
        return
    content = gi.read_text()
    assert "generate_shell.py" in content, (
        ".zshrc.d/.gitignore should have the generate_shell.py header"
    )


def test_zsh_gitignore_excludes_transient():
    """Top-level zsh .gitignore should exclude common transient files."""
    gi = ZSH_DIR / ".gitignore"
    if not gi.exists():
        return
    content = gi.read_text()
    for pattern in [".zcompdump", ".antidote/"]:
        assert pattern in content, (
            f"zsh/.gitignore should exclude {pattern}"
        )


def run_all_tests():
    """Run all tests manually (for systems without pytest)."""
    tests = [
        # File existence & structure
        test_zshrc_exists,
        test_zshenv_exists,
        test_zshrc_d_exists,
        test_zfunctions_dir_exists,
        test_plugins_txt_exists,
        test_p10k_config_exists,
        # Load order
        test_zshrc_d_files_are_numbered,
        test_no_duplicate_prefixes,
        test_load_order_is_monotonic,
        test_no_dead_files,
        test_zshrc_d_files_have_shebang,
        # Syntax
        test_zsh_syntax,
        # dot_zshrc structure
        test_zshrc_sources_zshrc_d,
        test_zshrc_instant_prompt_at_top,
        test_zshrc_loads_p10k,
        test_zshrc_supports_local_override,
        test_zshrc_local_override_at_end,
        test_zshrc_autoloads_zfunctions,
        # Plugins
        test_zshrc_pre_plugin_zstyles,
        test_plugins_has_autocomplete,
        test_plugins_has_syntax_highlighting,
        test_plugins_syntax_highlighting_before_autocomplete,
        test_plugins_no_compinit,
        # dot_zshenv
        test_zshenv_sets_zdotdir,
        test_zshenv_sets_xdg_dirs,
        test_zshenv_deduplicates_path,
        test_zshenv_no_interactive_code,
        # Autocomplete
        test_autocomplete_min_input_not_zero,
        test_autocomplete_post_plugin_uses_precmd,
        test_autocomplete_binds_menu_select,
        # Options
        test_options_file_exists,
        test_history_file_xdg_compliant,
        test_no_duplicate_setopts,
        # Gitignore
        test_gitignore_covers_generated_files,
        test_zsh_gitignore_excludes_transient,
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
