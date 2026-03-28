#!/usr/bin/env python3
"""
Chaos monkey tests for generate_shell.py — 4-shell transpiler

These tests pin critical invariants across all four shells. Each test was
written to catch a specific deliberate breakage (chaos monkey), then kept
as a regression guard after the breakage was reverted.

Run with: python3 tests/test_chaos_monkey.py
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))
from generate_shell import (
    PREDICATES,
    GUARDS,
    GUARD_CONDITIONS,
    SHELLS,
    SHELL_INDEX,
    HEADER,
    translate_guard,
    translate_guard_condition,
    generate_function,
    generate_module,
    _render_path,
    _render_alias,
    _render_tool_init,
    _render_env_var,
    _render_source_file,
    _render_eval_command,
    _render_conditional,
    _resolve_body_text,
)


# ---------------------------------------------------------------------------
# Chaos 1: Fish alias syntax — must use alias name='cmd' (single quotes)
# ---------------------------------------------------------------------------

def test_fish_alias_uses_single_quotes():
    """Fish aliases must wrap the command in single quotes."""
    result = _render_alias("ls", "eza --icons", "fish")
    assert result == "alias ls='eza --icons'", f"Got: {result}"


def test_fish_alias_not_double_quotes():
    """Fish aliases must NOT use double quotes (breaks variable expansion)."""
    result = _render_alias("cat", "bat", "fish")
    assert "'" in result and '"' not in result, f"Got: {result}"


# ---------------------------------------------------------------------------
# Chaos 1b: Zsh/Bash alias syntax — must use double quotes
# ---------------------------------------------------------------------------

def test_zsh_alias_uses_double_quotes():
    """Zsh aliases must wrap the command in double quotes."""
    result = _render_alias("ls", "eza", "zsh")
    assert result == 'alias ls="eza"', f"Got: {result}"


def test_bash_alias_uses_double_quotes():
    """Bash aliases must wrap the command in double quotes."""
    result = _render_alias("ll", "eza -l", "bash")
    assert result == 'alias ll="eza -l"', f"Got: {result}"


# ---------------------------------------------------------------------------
# Chaos 2: Zsh autoload — predicate must NOT have function wrapper
# ---------------------------------------------------------------------------

def test_zsh_predicate_no_function_keyword():
    """Zsh predicate functions use autoload convention: bare body, no wrapper."""
    func = {"name": "is-linux", "description": "Linux check",
            "predicate": "os_is_linux"}
    result = generate_function(func, "zsh")
    lines = result.strip().split("\n")
    # Should just be HEADER, blank, body — no "function" anywhere
    for line in lines:
        assert not line.strip().startswith("function "), \
            f"Zsh autoload must not have function wrapper, got: {line}"


def test_zsh_complex_no_function_wrapper():
    """Zsh complex functions also use autoload convention: bare body."""
    func = {"name": "greet", "description": "Greet",
            "body": {"zsh": "echo hello"}}
    result = generate_function(func, "zsh")
    assert "function greet" not in result
    assert "greet()" not in result
    assert "echo hello" in result


# ---------------------------------------------------------------------------
# Chaos 3: Bash PATH export — must use export PATH="...:$PATH"
# ---------------------------------------------------------------------------

def test_bash_path_export_format():
    """Bash PATH addition must use export PATH=\"path:$PATH\" format."""
    result = _render_path("$HOME/.local/bin", "bash")
    assert result == 'export PATH="$HOME/.local/bin:$PATH"', f"Got: {result}"


def test_zsh_path_export_format():
    """Zsh PATH addition must also use export PATH format (same as bash)."""
    result = _render_path("/usr/local/bin", "zsh")
    assert result == 'export PATH="/usr/local/bin:$PATH"', f"Got: {result}"


def test_fish_path_uses_fish_add_path():
    """Fish must use fish_add_path, not export."""
    result = _render_path("$HOME/.local/bin", "fish")
    assert result == "fish_add_path $HOME/.local/bin", f"Got: {result}"
    assert "export" not in result


# ---------------------------------------------------------------------------
# Chaos 4: PowerShell env var syntax — must use $env:VAR = "value"
# ---------------------------------------------------------------------------

def test_pwsh_env_var_format():
    """PowerShell env vars must use $env:VAR = \"value\" syntax."""
    result = _render_env_var("EDITOR", "nvim", "pwsh")
    assert result == '$env:EDITOR = "nvim"', f"Got: {result}"


def test_fish_env_var_format():
    """Fish env vars must use set -gx VAR \"value\" syntax."""
    result = _render_env_var("EDITOR", "vim", "fish")
    assert result == 'set -gx EDITOR "vim"', f"Got: {result}"


def test_bash_env_var_format():
    """Bash env vars must use export VAR=\"value\" syntax."""
    result = _render_env_var("PAGER", "less", "bash")
    assert result == 'export PAGER="less"', f"Got: {result}"


# ---------------------------------------------------------------------------
# Chaos 5: Fish guard bail — must use "; or return 0"
# ---------------------------------------------------------------------------

def test_fish_guard_command_exists_bail():
    """Fish command_exists guard must bail with 'command -q X; or return 0'."""
    result = translate_guard({"command_exists": "eza"}, "fish")
    assert result == "command -q eza; or return 0", f"Got: {result}"


def test_fish_guard_is_interactive_bail():
    """Fish is_interactive guard must bail with 'status is-interactive; or return 0'."""
    result = translate_guard("is_interactive", "fish")
    assert result == "status is-interactive; or return 0", f"Got: {result}"


def test_zsh_guard_command_exists_bail():
    """Zsh command_exists guard must use (( $+commands[X] )) || return 0."""
    result = translate_guard({"command_exists": "zoxide"}, "zsh")
    assert result == "(( $+commands[zoxide] )) || return 0", f"Got: {result}"


def test_bash_guard_command_exists_bail():
    """Bash command_exists guard must use command -v X &>/dev/null || return 0."""
    result = translate_guard({"command_exists": "fzf"}, "bash")
    assert result == "command -v fzf &>/dev/null || return 0", f"Got: {result}"


# ---------------------------------------------------------------------------
# Chaos 6: Zsh conditional elif syntax — must use "elif COND; then"
# ---------------------------------------------------------------------------

def test_zsh_conditional_elif_syntax():
    """Zsh conditional must use 'elif' keyword, not 'else if'."""
    cond = [
        {"if": {"command_exists": "nvim"}, "env": {"EDITOR": "nvim"}},
        {"elif": {"command_exists": "vim"}, "env": {"EDITOR": "vim"}},
        {"else": True, "env": {"EDITOR": "vi"}},
    ]
    result = _render_conditional(cond, "zsh")
    assert "elif " in result, f"Zsh must use 'elif', got:\n{result}"
    assert "fi" in result
    assert "else if" not in result


def test_bash_conditional_elif_syntax():
    """Bash conditional must also use 'elif', not 'else if'."""
    cond = [
        {"if": {"command_exists": "nvim"}, "env": {"EDITOR": "nvim"}},
        {"elif": {"command_exists": "vim"}, "env": {"EDITOR": "vim"}},
    ]
    result = _render_conditional(cond, "bash")
    assert "elif " in result
    assert "fi" in result


def test_fish_conditional_uses_else_if():
    """Fish conditional must use 'else if' (Fish syntax), not 'elif'."""
    cond = [
        {"if": {"command_exists": "nvim"}, "env": {"EDITOR": "nvim"}},
        {"elif": {"command_exists": "vim"}, "env": {"EDITOR": "vim"}},
    ]
    result = _render_conditional(cond, "fish")
    assert "else if " in result, f"Fish must use 'else if', got:\n{result}"
    assert "end" in result


def test_pwsh_conditional_uses_elseif():
    """PowerShell conditional must use '} elseif (' syntax."""
    cond = [
        {"if": {"command_exists": "nvim"}, "env": {"EDITOR": "nvim"}},
        {"elif": {"command_exists": "vim"}, "env": {"EDITOR": "vim"}},
        {"else": True, "env": {"EDITOR": "vi"}},
    ]
    result = _render_conditional(cond, "pwsh")
    assert "elseif" in result, f"PowerShell must use 'elseif', got:\n{result}"
    assert "}" in result


# ---------------------------------------------------------------------------
# Chaos 7: Bash function closure — must use name() { ... }
# ---------------------------------------------------------------------------

def test_bash_predicate_function_closure():
    """Bash predicate must use name() { body } syntax."""
    func = {"name": "is-darwin", "description": "macOS check",
            "predicate": "os_is_darwin"}
    result = generate_function(func, "bash")
    assert "is-darwin() {" in result, f"Got:\n{result}"
    lines = [l.strip() for l in result.strip().split("\n")]
    assert lines[-1] == "}", f"Last line must be '}}', got: {lines[-1]}"


def test_fish_predicate_function_closure():
    """Fish predicate must use function name ... end syntax."""
    func = {"name": "is-darwin", "description": "macOS check",
            "predicate": "os_is_darwin"}
    result = generate_function(func, "fish")
    assert "function is-darwin" in result
    lines = [l.strip() for l in result.strip().split("\n")]
    assert lines[-1] == "end", f"Last line must be 'end', got: {lines[-1]}"


def test_pwsh_predicate_function_closure():
    """PowerShell predicate must use function name { body } syntax."""
    func = {"name": "is-linux", "description": "Linux check",
            "predicate": "os_is_linux"}
    result = generate_function(func, "pwsh")
    assert "function is-linux {" in result
    lines = [l.strip() for l in result.strip().split("\n")]
    assert lines[-1] == "}", f"Last line must be '}}', got: {lines[-1]}"


# ---------------------------------------------------------------------------
# Chaos 8: PowerShell tool init — Invoke-Expression pattern
# ---------------------------------------------------------------------------

def test_pwsh_tool_init_invoke_expression():
    """PowerShell tool init must use Invoke-Expression pattern."""
    result = _render_tool_init("zoxide", "pwsh")
    assert "Invoke-Expression" in result, f"Got: {result}"
    assert "zoxide init powershell" in result


def test_fish_tool_init_pipe_source():
    """Fish tool init must pipe to source."""
    result = _render_tool_init("zoxide", "fish")
    assert result == "zoxide init fish | source", f"Got: {result}"


def test_bash_tool_init_eval():
    """Bash tool init must use eval \"$(tool init bash)\" pattern."""
    result = _render_tool_init("zoxide", "bash")
    assert result == 'eval "$(zoxide init bash)"', f"Got: {result}"


def test_zsh_tool_init_eval():
    """Zsh tool init must use eval \"$(tool init zsh)\" pattern."""
    result = _render_tool_init("zoxide", "zsh")
    assert result == 'eval "$(zoxide init zsh)"', f"Got: {result}"


# ---------------------------------------------------------------------------
# Chaos 9: Posix fallback resolution — zsh/bash use posix, fish doesn't
# ---------------------------------------------------------------------------

def test_posix_fallback_applies_to_zsh():
    """Body resolution: zsh falls back to 'posix' key when no 'zsh' key."""
    body = {"fish": "echo fish", "posix": "echo posix", "pwsh": "echo pwsh"}
    assert _resolve_body_text(body, "zsh") == "echo posix"


def test_posix_fallback_applies_to_bash():
    """Body resolution: bash falls back to 'posix' key when no 'bash' key."""
    body = {"fish": "echo fish", "posix": "echo posix", "pwsh": "echo pwsh"}
    assert _resolve_body_text(body, "bash") == "echo posix"


def test_posix_fallback_does_not_apply_to_fish():
    """Body resolution: fish must NOT fall back to 'posix'."""
    body = {"posix": "echo posix", "pwsh": "echo pwsh"}
    result = _resolve_body_text(body, "fish")
    assert result == "", f"Fish should get empty body, got: {result}"


def test_posix_fallback_does_not_apply_to_pwsh():
    """Body resolution: pwsh must NOT fall back to 'posix'."""
    body = {"posix": "echo posix", "fish": "echo fish"}
    result = _resolve_body_text(body, "pwsh")
    assert result == "", f"PowerShell should get empty body, got: {result}"


def test_shared_fallback_applies_to_all():
    """Body resolution: 'shared' is fallback for ALL shells."""
    body = {"shared": "echo shared"}
    for shell in SHELLS:
        result = _resolve_body_text(body, shell)
        assert result == "echo shared", f"{shell} should get shared body, got: {result}"


def test_explicit_shell_key_overrides_posix():
    """Body resolution: explicit shell key takes priority over posix."""
    body = {"zsh": "echo zsh-specific", "posix": "echo posix"}
    assert _resolve_body_text(body, "zsh") == "echo zsh-specific"


def test_explicit_shell_key_overrides_shared():
    """Body resolution: explicit shell key takes priority over shared."""
    body = {"fish": "echo fish-specific", "shared": "echo shared"}
    assert _resolve_body_text(body, "fish") == "echo fish-specific"


# ---------------------------------------------------------------------------
# Chaos 10: Fish predicate body correctness
# ---------------------------------------------------------------------------

def test_fish_darwin_predicate_uses_uname():
    """Fish os_is_darwin must test uname output, not $OSTYPE."""
    body = PREDICATES["os_is_darwin"][SHELL_INDEX["fish"]]
    assert "uname" in body, f"Fish darwin check must use uname, got: {body}"
    assert "Darwin" in body


def test_fish_linux_predicate_uses_uname():
    """Fish os_is_linux must test uname output."""
    body = PREDICATES["os_is_linux"][SHELL_INDEX["fish"]]
    assert "uname" in body
    assert "Linux" in body


def test_bash_darwin_predicate_uses_ostype():
    """Bash os_is_darwin must use $OSTYPE, not uname."""
    body = PREDICATES["os_is_darwin"][SHELL_INDEX["bash"]]
    assert "OSTYPE" in body, f"Bash darwin check must use OSTYPE, got: {body}"
    assert "darwin" in body


def test_pwsh_darwin_predicate_uses_is_macos():
    """PowerShell os_is_darwin must use $IsMacOS built-in."""
    body = PREDICATES["os_is_darwin"][SHELL_INDEX["pwsh"]]
    assert body == "$IsMacOS", f"Got: {body}"


def test_pwsh_linux_predicate_uses_is_linux():
    """PowerShell os_is_linux must use $IsLinux built-in."""
    body = PREDICATES["os_is_linux"][SHELL_INDEX["pwsh"]]
    assert body == "$IsLinux", f"Got: {body}"


# ---------------------------------------------------------------------------
# Chaos 11: Source file rendering — all 4 shells
# ---------------------------------------------------------------------------

def test_fish_source_file():
    """Fish source_file must use 'test -f' and 'and source' pattern."""
    result = _render_source_file("$HOME/.shellrc.local", "fish")
    assert 'test -f' in result
    assert 'and source' in result
    assert '$HOME/.shellrc.local' in result


def test_zsh_source_file():
    """Zsh source_file must use [[ -f ]] && source pattern."""
    result = _render_source_file("$HOME/.zshrc.local", "zsh")
    assert '[[ -f' in result
    assert '&& source' in result


def test_bash_source_file():
    """Bash source_file must use [[ -f ]] && source pattern."""
    result = _render_source_file("$HOME/.bashrc.local", "bash")
    assert '[[ -f' in result
    assert '&& source' in result


def test_pwsh_source_file():
    """PowerShell source_file must use Test-Path and dot-source pattern."""
    result = _render_source_file("$HOME/.psrc.local", "pwsh")
    assert 'Test-Path' in result
    assert '. "' in result


# ---------------------------------------------------------------------------
# Chaos 12: Eval command {shell} substitution
# ---------------------------------------------------------------------------

def test_eval_command_fish_shell_substitution():
    """Fish eval_command replaces {shell} with 'fish'."""
    result = _render_eval_command("mise activate {shell}", "fish")
    assert "mise activate fish" in result
    assert "{shell}" not in result
    assert "| source" in result


def test_eval_command_zsh_shell_substitution():
    """Zsh eval_command replaces {shell} with 'zsh'."""
    result = _render_eval_command("mise activate {shell}", "zsh")
    assert "mise activate zsh" in result
    assert "{shell}" not in result
    assert 'eval "$(' in result


def test_eval_command_bash_shell_substitution():
    """Bash eval_command replaces {shell} with 'bash'."""
    result = _render_eval_command("mise activate {shell}", "bash")
    assert "mise activate bash" in result
    assert "{shell}" not in result


def test_eval_command_pwsh_shell_substitution():
    """PowerShell eval_command replaces {shell} with 'powershell' (not 'pwsh')."""
    result = _render_eval_command("mise activate {shell}", "pwsh")
    assert "mise activate powershell" in result
    assert "mise activate pwsh" not in result
    assert "{shell}" not in result
    assert "Invoke-Expression" in result


# ---------------------------------------------------------------------------
# Chaos 13: Module header — all modules must start with HEADER
# ---------------------------------------------------------------------------

def test_module_starts_with_header():
    """Generated modules must start with the DO NOT EDIT header."""
    mod = {"name": "test", "prefix": "99", "description": "Test module",
           "aliases": {"foo": "bar"}}
    for shell in SHELLS:
        result = generate_module(mod, shell)
        assert result.startswith(HEADER), \
            f"{shell} module must start with header"


def test_function_starts_with_header():
    """Generated functions must start with the DO NOT EDIT header."""
    func = {"name": "is-darwin", "description": "macOS check",
            "predicate": "os_is_darwin"}
    for shell in SHELLS:
        result = generate_function(func, shell)
        assert result.startswith(HEADER), \
            f"{shell} function must start with header"


# ---------------------------------------------------------------------------
# Chaos 14: Guard condition form vs bail form consistency
# ---------------------------------------------------------------------------

def test_guard_tables_have_same_keys():
    """GUARDS and GUARD_CONDITIONS must define the exact same set of keys."""
    assert set(GUARDS.keys()) == set(GUARD_CONDITIONS.keys()), \
        f"Mismatch: GUARDS has {set(GUARDS.keys()) - set(GUARD_CONDITIONS.keys())}, " \
        f"GUARD_CONDITIONS has {set(GUARD_CONDITIONS.keys()) - set(GUARDS.keys())}"


def test_guard_tables_have_four_shells():
    """Every guard entry must be a 4-tuple (one per shell)."""
    for key, val in GUARDS.items():
        assert len(val) == 4, f"GUARDS[{key}] has {len(val)} entries, need 4"
    for key, val in GUARD_CONDITIONS.items():
        assert len(val) == 4, f"GUARD_CONDITIONS[{key}] has {len(val)} entries, need 4"


def test_bail_guards_contain_return():
    """Bail-form guards must contain 'return' to skip the module."""
    for key, shells in GUARDS.items():
        for i, shell_name in enumerate(SHELLS):
            assert "return" in shells[i], \
                f"GUARDS[{key}][{shell_name}] missing 'return': {shells[i]}"


def test_condition_guards_do_not_contain_return():
    """Condition-form guards must NOT contain 'return' (used in if/elif)."""
    for key, shells in GUARD_CONDITIONS.items():
        for i, shell_name in enumerate(SHELLS):
            assert "return" not in shells[i], \
                f"GUARD_CONDITIONS[{key}][{shell_name}] should not have 'return': {shells[i]}"


# ---------------------------------------------------------------------------
# Chaos 15: PowerShell alias — must use function form, not Set-Alias
# ---------------------------------------------------------------------------

def test_pwsh_alias_uses_function_form():
    """PowerShell aliases must be function wrappers (to support args)."""
    result = _render_alias("ls", "eza --icons", "pwsh")
    assert "function ls" in result, f"Got: {result}"
    assert "@args" in result, f"PowerShell must pass @args, got: {result}"
    assert "Set-Alias" not in result


# ---------------------------------------------------------------------------
# Chaos 16: Fish conditional end block
# ---------------------------------------------------------------------------

def test_fish_conditional_ends_with_end():
    """Fish conditional blocks must close with 'end'."""
    cond = [
        {"if": {"command_exists": "nvim"}, "env": {"EDITOR": "nvim"}},
        {"else": True, "env": {"EDITOR": "vi"}},
    ]
    result = _render_conditional(cond, "fish")
    lines = result.strip().split("\n")
    assert lines[-1].strip() == "end", f"Fish conditional must end with 'end', got: {lines[-1]}"


def test_bash_conditional_ends_with_fi():
    """Bash conditional blocks must close with 'fi'."""
    cond = [
        {"if": {"command_exists": "nvim"}, "env": {"EDITOR": "nvim"}},
        {"else": True, "env": {"EDITOR": "vi"}},
    ]
    result = _render_conditional(cond, "bash")
    lines = result.strip().split("\n")
    assert lines[-1].strip() == "fi", f"Bash conditional must end with 'fi', got: {lines[-1]}"


def test_pwsh_conditional_ends_with_brace():
    """PowerShell conditional blocks must close with '}'."""
    cond = [
        {"if": {"command_exists": "nvim"}, "env": {"EDITOR": "nvim"}},
        {"else": True, "env": {"EDITOR": "vi"}},
    ]
    result = _render_conditional(cond, "pwsh")
    lines = result.strip().split("\n")
    assert lines[-1].strip() == "}", f"PowerShell conditional must end with '}}', got: {lines[-1]}"


# ---------------------------------------------------------------------------
# Chaos 17: Not-guard negation — each shell uses correct negation
# ---------------------------------------------------------------------------

def test_not_guard_fish():
    """Fish 'not' guard condition uses 'not' keyword."""
    result = translate_guard_condition({"not": {"command_exists": "eza"}}, "fish")
    assert result.startswith("not "), f"Got: {result}"


def test_not_guard_zsh():
    """Zsh 'not' guard condition uses '!' prefix."""
    result = translate_guard_condition({"not": {"command_exists": "eza"}}, "zsh")
    assert result.startswith("! "), f"Got: {result}"


def test_not_guard_bash():
    """Bash 'not' guard condition uses '!' prefix."""
    result = translate_guard_condition({"not": {"command_exists": "eza"}}, "bash")
    assert result.startswith("! "), f"Got: {result}"


def test_not_guard_pwsh():
    """PowerShell 'not' guard condition uses '-not' operator."""
    result = translate_guard_condition({"not": {"command_exists": "eza"}}, "pwsh")
    assert "-not" in result, f"Got: {result}"


# ---------------------------------------------------------------------------
# Chaos 18: Module with guard — guard appears before body
# ---------------------------------------------------------------------------

def test_guard_appears_before_alias_in_module():
    """In a guarded module, guard line must come before the alias lines."""
    mod = {"name": "eza", "prefix": "40", "description": "eza aliases",
           "guard": {"command_exists": "eza"}, "aliases": {"ls": "eza"}}
    for shell in SHELLS:
        result = generate_module(mod, shell)
        lines = result.split("\n")
        guard_idx = None
        alias_idx = None
        for i, line in enumerate(lines):
            if "return" in line or ("if (-not" in line and "return" in line):
                guard_idx = i
            if "ls" in line and ("alias" in line or "function ls" in line):
                alias_idx = i
        assert guard_idx is not None, f"{shell}: no guard found in:\n{result}"
        assert alias_idx is not None, f"{shell}: no alias found in:\n{result}"
        assert guard_idx < alias_idx, \
            f"{shell}: guard (line {guard_idx}) must come before alias (line {alias_idx})"


# ---------------------------------------------------------------------------
# Chaos 19: PATH rendering — pwsh uses PathSeparator
# ---------------------------------------------------------------------------

def test_pwsh_path_uses_path_separator():
    """PowerShell PATH must use [IO.Path]::PathSeparator for cross-platform."""
    result = _render_path("$HOME/.local/bin", "pwsh")
    assert "PathSeparator" in result, f"Got: {result}"
    assert "$env:PATH" in result


# ---------------------------------------------------------------------------
# Chaos 20: Predicate table completeness
# ---------------------------------------------------------------------------

def test_all_predicates_have_four_shells():
    """Every PREDICATES entry must be a 4-tuple."""
    for key, val in PREDICATES.items():
        assert len(val) == 4, f"PREDICATES[{key}] has {len(val)} entries, need 4"


def test_predicates_are_nonempty():
    """No predicate body should be empty."""
    for key, shells in PREDICATES.items():
        for i, shell_name in enumerate(SHELLS):
            assert shells[i].strip(), \
                f"PREDICATES[{key}][{shell_name}] is empty"


# ---------------------------------------------------------------------------
# Runner
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    import pytest
    sys.exit(pytest.main([__file__, "-v"]))
