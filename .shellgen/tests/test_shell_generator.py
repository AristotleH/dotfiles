#!/usr/bin/env python3
"""
Unit tests for generate_shell.py — 4-shell transpiler

Run with: python3 tests/test_shell_generator.py
"""

import sys
from pathlib import Path

# Add parent directory to path so we can import the generator
sys.path.insert(0, str(Path(__file__).parent.parent))
from generate_shell import (
    PREDICATES,
    GUARDS,
    GUARD_CONDITIONS,
    SHELLS,
    SHELL_INDEX,
    SHELL_MODULE_EXT,
    SHELL_FUNC_EXT,
    translate_guard,
    translate_guard_condition,
    generate_function,
    generate_module,
    generate_all,
    validate_manifest,
    load_manifest,
    merge_manifests,
    resolve_sources,
    get_output_dirs,
    HEADER,
    _render_path,
    _render_alias,
    _render_tool_init,
    _render_env_var,
    _render_source_file,
    _render_eval_command,
    _render_conditional,
)


# ---------------------------------------------------------------------------
# Predicate functions — all 4 shells
# ---------------------------------------------------------------------------

def test_predicate_fish():
    """Predicate function generates correct Fish wrapper."""
    func = {"name": "is-darwin", "description": "Check if running on macOS",
            "predicate": "os_is_darwin"}
    result = generate_function(func, "fish")
    assert "function is-darwin" in result
    assert "--description" in result
    assert 'test (uname) = "Darwin"' in result
    assert result.startswith(HEADER)


def test_predicate_zsh():
    """Predicate function generates correct Zsh autoload body."""
    func = {"name": "is-darwin", "description": "Check if running on macOS",
            "predicate": "os_is_darwin"}
    result = generate_function(func, "zsh")
    assert "[[ $OSTYPE == *darwin* ]]" in result
    assert "function" not in result  # autoload, no wrapper
    assert result.startswith(HEADER)


def test_predicate_bash():
    """Predicate function generates correct Bash function."""
    func = {"name": "is-darwin", "description": "Check if running on macOS",
            "predicate": "os_is_darwin"}
    result = generate_function(func, "bash")
    assert "is-darwin() {" in result
    assert "[[ $OSTYPE == darwin* ]]" in result
    assert result.startswith(HEADER)


def test_predicate_pwsh():
    """Predicate function generates correct PowerShell function."""
    func = {"name": "is-darwin", "description": "Check if running on macOS",
            "predicate": "os_is_darwin"}
    result = generate_function(func, "pwsh")
    assert "function is-darwin {" in result
    assert "$IsMacOS" in result
    assert result.startswith(HEADER)


def test_predicate_linux():
    """Linux predicate works for all shells."""
    func = {"name": "is-linux", "description": "Check if running on Linux",
            "predicate": "os_is_linux"}
    fish = generate_function(func, "fish")
    zsh = generate_function(func, "zsh")
    bash = generate_function(func, "bash")
    pwsh = generate_function(func, "pwsh")
    assert 'test (uname) = "Linux"' in fish
    assert "[[ $OSTYPE == *linux* ]]" in zsh
    assert "[[ $OSTYPE == linux* ]]" in bash
    assert "$IsLinux" in pwsh


def test_predicate_windows():
    """Windows predicate works for all shells."""
    func = {"name": "is-windows", "description": "Check if running on Windows",
            "predicate": "os_is_windows"}
    fish = generate_function(func, "fish")
    zsh = generate_function(func, "zsh")
    bash = generate_function(func, "bash")
    pwsh = generate_function(func, "pwsh")
    assert "Msys" in fish
    assert "msys" in zsh
    assert "msys" in bash
    assert "$IsWindows" in pwsh


def test_predicate_arch_arm64():
    """ARM64 architecture predicate works for all shells."""
    func = {"name": "is-arm64", "description": "Check if ARM64",
            "predicate": "arch_is_arm64"}
    fish = generate_function(func, "fish")
    bash = generate_function(func, "bash")
    pwsh = generate_function(func, "pwsh")
    assert "arm64" in fish
    assert "aarch64" in fish
    assert "arm64" in bash
    assert "Arm64" in pwsh


def test_predicate_arch_x86_64():
    """x86_64 architecture predicate works for all shells."""
    func = {"name": "is-x86", "description": "Check if x86_64",
            "predicate": "arch_is_x86_64"}
    fish = generate_function(func, "fish")
    bash = generate_function(func, "bash")
    pwsh = generate_function(func, "pwsh")
    assert "x86_64" in fish
    assert "x86_64" in bash
    assert "X64" in pwsh


# ---------------------------------------------------------------------------
# Complex functions — all 4 shells
# ---------------------------------------------------------------------------

def test_complex_fish():
    """Complex function wraps body in function/end for Fish."""
    func = {
        "name": "in_dir",
        "description": "Run a command in a different directory",
        "usage": "in_dir <dir> <cmd>",
        "body": {
            "fish": "echo hello\necho world",
            "zsh": 'echo "hello"',
            "bash": 'echo "hello"',
            "pwsh": 'Write-Output "hello"',
        },
    }
    result = generate_function(func, "fish")
    assert "function in_dir" in result
    assert "end" in result.split("\n")[-2]
    assert "echo hello" in result


def test_complex_zsh():
    """Complex function produces bare body for Zsh autoload."""
    func = {
        "name": "in_dir",
        "description": "Run a command in a different directory",
        "usage": "in_dir <dir> <cmd>",
        "body": {
            "fish": "echo hello",
            "zsh": 'echo "hello"',
            "bash": 'echo "hello"',
            "pwsh": 'Write-Output "hello"',
        },
    }
    result = generate_function(func, "zsh")
    assert "function" not in result.split("\n")[1]  # no function wrapper
    assert 'echo "hello"' in result


def test_complex_bash():
    """Complex function wraps body in name() { ... } for Bash."""
    func = {
        "name": "in_dir",
        "description": "Run a command in a different directory",
        "usage": "in_dir <dir> <cmd>",
        "body": {
            "fish": "echo hello",
            "zsh": 'echo "hello"',
            "bash": 'echo "hello bash"',
            "pwsh": 'Write-Output "hello"',
        },
    }
    result = generate_function(func, "bash")
    assert "in_dir() {" in result
    assert "}" in result.split("\n")[-2]
    assert 'echo "hello bash"' in result
    assert result.startswith(HEADER)


def test_complex_pwsh():
    """Complex function wraps body in function Name { ... } for PowerShell."""
    func = {
        "name": "in_dir",
        "description": "Run a command in a different directory",
        "usage": "in_dir <dir> <cmd>",
        "body": {
            "fish": "echo hello",
            "zsh": 'echo "hello"',
            "bash": 'echo "hello"',
            "pwsh": 'Write-Output "hello pwsh"',
        },
    }
    result = generate_function(func, "pwsh")
    assert "function in_dir {" in result
    assert "}" in result.split("\n")[-2]
    assert 'Write-Output "hello pwsh"' in result
    assert result.startswith(HEADER)


def test_complex_shared_fallback():
    """Complex function falls back to 'shared' body when shell key missing."""
    func = {
        "name": "greet",
        "description": "Greet the user",
        "body": {"shared": "echo hello"},
    }
    for shell in SHELLS:
        result = generate_function(func, shell)
        assert "echo hello" in result


# ---------------------------------------------------------------------------
# Guards — bail form
# ---------------------------------------------------------------------------

def test_guard_command_exists_fish():
    guard = {"command_exists": "eza"}
    result = translate_guard(guard, "fish")
    assert result == "command -q eza; or return 0"


def test_guard_command_exists_zsh():
    guard = {"command_exists": "eza"}
    result = translate_guard(guard, "zsh")
    assert result == "(( $+commands[eza] )) || return 0"


def test_guard_command_exists_bash():
    guard = {"command_exists": "eza"}
    result = translate_guard(guard, "bash")
    assert result == "command -v eza &>/dev/null || return 0"


def test_guard_command_exists_pwsh():
    guard = {"command_exists": "eza"}
    result = translate_guard(guard, "pwsh")
    assert "Get-Command" in result
    assert "eza" in result
    assert "return" in result


def test_guard_env_equals_fish():
    guard = {"env_equals": {"var": "TMUX_AUTO_ATTACH", "value": "1"}}
    result = translate_guard(guard, "fish")
    assert 'test "$TMUX_AUTO_ATTACH" = "1"' in result


def test_guard_env_equals_zsh():
    guard = {"env_equals": {"var": "TMUX_AUTO_ATTACH", "value": "1"}}
    result = translate_guard(guard, "zsh")
    assert '[[ "$TMUX_AUTO_ATTACH" == "1" ]]' in result


def test_guard_env_equals_bash():
    guard = {"env_equals": {"var": "TMUX_AUTO_ATTACH", "value": "1"}}
    result = translate_guard(guard, "bash")
    assert '[[ "$TMUX_AUTO_ATTACH" == "1" ]]' in result
    assert "|| return 0" in result


def test_guard_env_equals_pwsh():
    guard = {"env_equals": {"var": "TMUX_AUTO_ATTACH", "value": "1"}}
    result = translate_guard(guard, "pwsh")
    assert "TMUX_AUTO_ATTACH" in result
    assert "-ne" in result
    assert "return" in result


def test_guard_env_not_set_fish():
    guard = {"env_not_set": "TMUX"}
    result = translate_guard(guard, "fish")
    assert "not set -q TMUX; or return 0" == result


def test_guard_env_not_set_zsh():
    guard = {"env_not_set": "TMUX"}
    result = translate_guard(guard, "zsh")
    assert "[[ -z $TMUX ]] || return 0" == result


def test_guard_env_not_set_bash():
    guard = {"env_not_set": "TMUX"}
    result = translate_guard(guard, "bash")
    assert '[[ -z "$TMUX" ]] || return 0' == result


def test_guard_env_not_set_pwsh():
    guard = {"env_not_set": "TMUX"}
    result = translate_guard(guard, "pwsh")
    assert "$env:TMUX" in result
    assert "return" in result


def test_guard_env_set_all():
    """env_set guard works for all shells."""
    guard = {"env_set": "HOME"}
    fish = translate_guard(guard, "fish")
    zsh = translate_guard(guard, "zsh")
    bash = translate_guard(guard, "bash")
    pwsh = translate_guard(guard, "pwsh")
    assert "set -q HOME; or return 0" == fish
    assert "[[ -n $HOME ]] || return 0" == zsh
    assert '[[ -n "$HOME" ]] || return 0' == bash
    assert "$env:HOME" in pwsh and "return" in pwsh


def test_guard_is_tty():
    assert "isatty stdin" in translate_guard("is_tty", "fish")
    assert "[[ -t 0 ]]" in translate_guard("is_tty", "zsh")
    assert "[[ -t 0 ]]" in translate_guard("is_tty", "bash")
    assert "UserInteractive" in translate_guard("is_tty", "pwsh")


def test_guard_is_interactive():
    assert "status is-interactive" in translate_guard("is_interactive", "fish")
    assert "[[ -o interactive ]]" in translate_guard("is_interactive", "zsh")
    assert '[[ $- == *i* ]]' in translate_guard("is_interactive", "bash")
    assert "UserInteractive" in translate_guard("is_interactive", "pwsh")


def test_guard_not_env_equals():
    guard = {"not_env_equals": {"var": "TERM_PROGRAM", "value": "vscode"}}
    fish = translate_guard(guard, "fish")
    zsh = translate_guard(guard, "zsh")
    bash = translate_guard(guard, "bash")
    pwsh = translate_guard(guard, "pwsh")
    assert '!= "vscode"' in fish
    assert '!= "vscode"' in zsh
    assert '!= "vscode"' in bash
    assert "-eq" in pwsh and "vscode" in pwsh


def test_guard_file_exists_all():
    """file_exists guard works for all shells."""
    guard = {"file_exists": "/opt/homebrew/bin/brew"}
    fish = translate_guard(guard, "fish")
    zsh = translate_guard(guard, "zsh")
    bash = translate_guard(guard, "bash")
    pwsh = translate_guard(guard, "pwsh")
    assert "test -f /opt/homebrew/bin/brew; or return 0" == fish
    assert "[[ -f /opt/homebrew/bin/brew ]] || return 0" == zsh
    assert "[[ -f /opt/homebrew/bin/brew ]] || return 0" == bash
    assert "Test-Path" in pwsh and "Leaf" in pwsh


def test_guard_dir_exists_all():
    """dir_exists guard works for all shells."""
    guard = {"dir_exists": "/opt/homebrew"}
    fish = translate_guard(guard, "fish")
    zsh = translate_guard(guard, "zsh")
    bash = translate_guard(guard, "bash")
    pwsh = translate_guard(guard, "pwsh")
    assert "test -d /opt/homebrew; or return 0" == fish
    assert "[[ -d /opt/homebrew ]] || return 0" == zsh
    assert "[[ -d /opt/homebrew ]] || return 0" == bash
    assert "Test-Path" in pwsh and "Container" in pwsh


def test_guard_not_wrapper():
    """The 'not' meta-guard negates any inner guard."""
    guard = {"not": {"command_exists": "nvim"}}
    fish = translate_guard(guard, "fish")
    zsh = translate_guard(guard, "zsh")
    bash = translate_guard(guard, "bash")
    pwsh = translate_guard(guard, "pwsh")
    # Fish: if command IS found, bail
    assert "command -q nvim; and return 0" == fish
    # Bash/Zsh: same logic
    assert "command -v nvim &>/dev/null && return 0" == bash
    assert "(( $+commands[nvim] )) && return 0" == zsh
    # PowerShell: if command is found, return
    assert "Get-Command" in pwsh and "return" in pwsh


# ---------------------------------------------------------------------------
# Guard conditions (for if/elif in conditionals)
# ---------------------------------------------------------------------------

def test_guard_condition_command_exists():
    guard = {"command_exists": "nvim"}
    assert translate_guard_condition(guard, "fish") == "command -q nvim"
    assert translate_guard_condition(guard, "zsh") == "(( $+commands[nvim] ))"
    assert translate_guard_condition(guard, "bash") == "command -v nvim &>/dev/null"
    assert "Get-Command" in translate_guard_condition(guard, "pwsh")


def test_guard_condition_env_equals():
    guard = {"env_equals": {"var": "EDITOR", "value": "vim"}}
    assert 'test "$EDITOR" = "vim"' == translate_guard_condition(guard, "fish")
    assert '[[ "$EDITOR" == "vim" ]]' == translate_guard_condition(guard, "zsh")
    assert '[[ "$EDITOR" == "vim" ]]' == translate_guard_condition(guard, "bash")
    assert "-eq" in translate_guard_condition(guard, "pwsh")


def test_guard_condition_not_wrapper():
    """Not wrapper in condition form negates the condition."""
    guard = {"not": {"command_exists": "nvim"}}
    assert translate_guard_condition(guard, "fish") == "not command -q nvim"
    assert translate_guard_condition(guard, "bash") == "! command -v nvim &>/dev/null"
    pwsh = translate_guard_condition(guard, "pwsh")
    assert "(-not" in pwsh


def test_guard_condition_string_guard():
    """String guards produce correct conditions."""
    assert translate_guard_condition("is_interactive", "fish") == "status is-interactive"
    assert translate_guard_condition("is_interactive", "bash") == '[[ $- == *i* ]]'
    assert translate_guard_condition("is_tty", "zsh") == "[[ -t 0 ]]"


# ---------------------------------------------------------------------------
# Render helpers
# ---------------------------------------------------------------------------

def test_render_path_all():
    """PATH render works for all shells."""
    assert _render_path("$HOME/bin", "fish") == "fish_add_path $HOME/bin"
    assert _render_path("$HOME/bin", "zsh") == 'export PATH="$HOME/bin:$PATH"'
    assert _render_path("$HOME/bin", "bash") == 'export PATH="$HOME/bin:$PATH"'
    assert "[IO.Path]::PathSeparator" in _render_path("$HOME/bin", "pwsh")


def test_render_alias_all():
    """Alias render works for all shells."""
    assert _render_alias("ls", "eza", "fish") == "alias ls='eza'"
    assert _render_alias("ls", "eza", "zsh") == 'alias ls="eza"'
    assert _render_alias("ls", "eza", "bash") == 'alias ls="eza"'
    pwsh = _render_alias("ls", "eza", "pwsh")
    assert "function ls" in pwsh and "eza" in pwsh and "@args" in pwsh


def test_render_tool_init_all():
    """Tool init render works for all shells."""
    assert _render_tool_init("zoxide", "fish") == "zoxide init fish | source"
    assert _render_tool_init("zoxide", "zsh") == 'eval "$(zoxide init zsh)"'
    assert _render_tool_init("zoxide", "bash") == 'eval "$(zoxide init bash)"'
    assert "Invoke-Expression" in _render_tool_init("zoxide", "pwsh")


def test_render_env_var_all():
    """Env var render works for all shells."""
    assert _render_env_var("EDITOR", "vim", "fish") == 'set -gx EDITOR "vim"'
    assert _render_env_var("EDITOR", "vim", "zsh") == 'export EDITOR="vim"'
    assert _render_env_var("EDITOR", "vim", "bash") == 'export EDITOR="vim"'
    assert _render_env_var("EDITOR", "vim", "pwsh") == '$env:EDITOR = "vim"'


def test_render_source_file_all():
    """Source file render works for all shells."""
    path = "$HOME/.local.sh"
    fish = _render_source_file(path, "fish")
    zsh = _render_source_file(path, "zsh")
    bash = _render_source_file(path, "bash")
    pwsh = _render_source_file(path, "pwsh")
    assert "test -f" in fish and "source" in fish
    assert "[[ -f" in zsh and "source" in zsh
    assert "[[ -f" in bash and "source" in bash
    assert "Test-Path" in pwsh and '". "' not in pwsh


def test_render_eval_command_all():
    """Eval command render works for all shells."""
    cmd = "/opt/homebrew/bin/brew shellenv"
    fish = _render_eval_command(cmd, "fish")
    zsh = _render_eval_command(cmd, "zsh")
    bash = _render_eval_command(cmd, "bash")
    pwsh = _render_eval_command(cmd, "pwsh")
    assert "| source" in fish
    assert 'eval "$(' in zsh
    assert 'eval "$(' in bash
    assert "Invoke-Expression" in pwsh


def test_render_eval_command_with_shell_placeholder():
    """Eval command replaces {shell} placeholder."""
    cmd = "mise activate {shell}"
    assert "mise activate fish | source" == _render_eval_command(cmd, "fish")
    assert 'eval "$(mise activate zsh)"' == _render_eval_command(cmd, "zsh")
    assert 'eval "$(mise activate bash)"' == _render_eval_command(cmd, "bash")
    assert "mise activate pwsh" in _render_eval_command(cmd, "pwsh")


# ---------------------------------------------------------------------------
# Module generators — all 4 shells
# ---------------------------------------------------------------------------

def test_path_module_fish():
    mod = {"name": "path", "prefix": "00", "description": "PATH additions",
           "paths": ["$HOME/.local/bin"]}
    result = generate_module(mod, "fish")
    assert "fish_add_path $HOME/.local/bin" in result
    assert result.startswith(HEADER)


def test_path_module_zsh():
    mod = {"name": "path", "prefix": "00", "description": "PATH additions",
           "paths": ["$HOME/.local/bin"]}
    result = generate_module(mod, "zsh")
    assert 'export PATH="$HOME/.local/bin:$PATH"' in result


def test_path_module_bash():
    mod = {"name": "path", "prefix": "00", "description": "PATH additions",
           "paths": ["$HOME/.local/bin"]}
    result = generate_module(mod, "bash")
    assert 'export PATH="$HOME/.local/bin:$PATH"' in result
    assert result.startswith(HEADER)


def test_path_module_pwsh():
    mod = {"name": "path", "prefix": "00", "description": "PATH additions",
           "paths": ["$HOME/.local/bin"]}
    result = generate_module(mod, "pwsh")
    assert "$env:PATH" in result
    assert "[IO.Path]::PathSeparator" in result


def test_aliases_module_fish():
    mod = {
        "name": "eza", "prefix": "40",
        "description": "eza aliases",
        "guard": {"command_exists": "eza"},
        "aliases": {"ls": "eza", "ll": "eza -l"},
    }
    result = generate_module(mod, "fish")
    assert "command -q eza; or return 0" in result
    assert "alias ls='eza'" in result
    assert "alias ll='eza -l'" in result


def test_aliases_module_zsh():
    mod = {
        "name": "eza", "prefix": "40",
        "description": "eza aliases",
        "guard": {"command_exists": "eza"},
        "aliases": {"ls": "eza", "ll": "eza -l"},
    }
    result = generate_module(mod, "zsh")
    assert "(( $+commands[eza] )) || return 0" in result
    assert 'alias ls="eza"' in result
    assert 'alias ll="eza -l"' in result


def test_aliases_module_bash():
    mod = {
        "name": "eza", "prefix": "40",
        "description": "eza aliases",
        "guard": {"command_exists": "eza"},
        "aliases": {"ls": "eza", "ll": "eza -l"},
    }
    result = generate_module(mod, "bash")
    assert "command -v eza &>/dev/null || return 0" in result
    assert 'alias ls="eza"' in result
    assert 'alias ll="eza -l"' in result


def test_aliases_module_pwsh():
    mod = {
        "name": "eza", "prefix": "40",
        "description": "eza aliases",
        "guard": {"command_exists": "eza"},
        "aliases": {"ls": "eza", "ll": "eza -l"},
    }
    result = generate_module(mod, "pwsh")
    assert "Get-Command" in result
    assert "function ls { eza @args }" in result
    assert "function ll { eza -l @args }" in result


def test_tool_init_fish():
    mod = {
        "name": "zoxide", "prefix": "50",
        "description": "Zoxide",
        "guard": {"command_exists": "zoxide"},
        "tool": "zoxide",
    }
    result = generate_module(mod, "fish")
    assert "zoxide init fish | source" in result
    assert "command -q zoxide; or return 0" in result


def test_tool_init_zsh():
    mod = {
        "name": "zoxide", "prefix": "50",
        "description": "Zoxide",
        "guard": {"command_exists": "zoxide"},
        "tool": "zoxide",
    }
    result = generate_module(mod, "zsh")
    assert 'eval "$(zoxide init zsh)"' in result
    assert "(( $+commands[zoxide] )) || return 0" in result


def test_tool_init_bash():
    mod = {
        "name": "zoxide", "prefix": "50",
        "description": "Zoxide",
        "guard": {"command_exists": "zoxide"},
        "tool": "zoxide",
    }
    result = generate_module(mod, "bash")
    assert 'eval "$(zoxide init bash)"' in result
    assert "command -v zoxide &>/dev/null || return 0" in result


def test_tool_init_pwsh():
    mod = {
        "name": "zoxide", "prefix": "50",
        "description": "Zoxide",
        "guard": {"command_exists": "zoxide"},
        "tool": "zoxide",
    }
    result = generate_module(mod, "pwsh")
    assert "Invoke-Expression" in result
    assert "zoxide init pwsh" in result


def test_custom_module_shared_body():
    """Custom module with shared body works for all shells."""
    mod = {
        "name": "tmux", "prefix": "70",
        "description": "Tmux auto-attach",
        "guards": [{"command_exists": "tmux"}],
        "body": {"shared": "tmux attach 2>/dev/null || tmux new-session"},
    }
    for shell in SHELLS:
        result = generate_module(mod, shell)
        assert "tmux attach 2>/dev/null || tmux new-session" in result


def test_custom_module_multiple_guards():
    """Custom module emits all guards in order."""
    mod = {
        "name": "test", "prefix": "99",
        "description": "Test",
        "guards": [
            {"command_exists": "foo"},
            "is_tty",
            {"env_not_set": "BAR"},
        ],
        "body": {"shared": "echo ok"},
    }
    for shell in SHELLS:
        result = generate_module(mod, shell)
        lines = result.split("\n")
        guard_lines = [l for l in lines if "return" in l]
        assert len(guard_lines) == 3, f"{shell}: expected 3 guard lines, got {len(guard_lines)}"


# ---------------------------------------------------------------------------
# New module types: env, source_file, eval_command
# ---------------------------------------------------------------------------

def test_env_module_all():
    """Env module generates correct output for all shells."""
    mod = {
        "name": "editor", "prefix": "05",
        "description": "Default editor",
        "env": {"EDITOR": "vim", "VISUAL": "vim"},
    }
    fish = generate_module(mod, "fish")
    zsh = generate_module(mod, "zsh")
    bash = generate_module(mod, "bash")
    pwsh = generate_module(mod, "pwsh")
    assert 'set -gx EDITOR "vim"' in fish
    assert 'set -gx VISUAL "vim"' in fish
    assert 'export EDITOR="vim"' in zsh
    assert 'export EDITOR="vim"' in bash
    assert '$env:EDITOR = "vim"' in pwsh
    assert '$env:VISUAL = "vim"' in pwsh


def test_source_file_module_all():
    """Source file module generates correct output for all shells."""
    mod = {
        "name": "local", "prefix": "99",
        "description": "Local overrides",
        "source_file": "$HOME/.shellrc.local",
    }
    fish = generate_module(mod, "fish")
    zsh = generate_module(mod, "zsh")
    bash = generate_module(mod, "bash")
    pwsh = generate_module(mod, "pwsh")
    assert "source" in fish and ".shellrc.local" in fish
    assert "source" in zsh and ".shellrc.local" in zsh
    assert "source" in bash and ".shellrc.local" in bash
    assert "Test-Path" in pwsh and ".shellrc.local" in pwsh


def test_source_file_module_list():
    """Source file module handles list of paths."""
    mod = {
        "name": "extras", "prefix": "99",
        "description": "Extra sources",
        "source_file": ["$HOME/.a", "$HOME/.b"],
    }
    for shell in SHELLS:
        result = generate_module(mod, shell)
        assert ".a" in result and ".b" in result


def test_eval_command_module_all():
    """Eval command module generates correct output for all shells."""
    mod = {
        "name": "brew-env", "prefix": "10",
        "description": "Homebrew env",
        "eval_command": "/opt/homebrew/bin/brew shellenv",
    }
    fish = generate_module(mod, "fish")
    zsh = generate_module(mod, "zsh")
    bash = generate_module(mod, "bash")
    pwsh = generate_module(mod, "pwsh")
    assert "| source" in fish
    assert 'eval "$(' in zsh
    assert 'eval "$(' in bash
    assert "Invoke-Expression" in pwsh


def test_eval_command_shell_placeholder():
    """Eval command with {shell} placeholder is replaced correctly."""
    mod = {
        "name": "mise", "prefix": "50",
        "description": "mise",
        "eval_command": "mise activate {shell}",
    }
    assert "mise activate fish" in generate_module(mod, "fish")
    assert "mise activate zsh" in generate_module(mod, "zsh")
    assert "mise activate bash" in generate_module(mod, "bash")
    assert "mise activate pwsh" in generate_module(mod, "pwsh")


# ---------------------------------------------------------------------------
# Conditional module type
# ---------------------------------------------------------------------------

def test_conditional_module_fish():
    """Conditional module generates correct Fish if/else if/else/end."""
    mod = {
        "name": "editor", "prefix": "05",
        "description": "Editor",
        "conditional": [
            {"if": {"command_exists": "nvim"}, "env": {"EDITOR": "nvim"}},
            {"elif": {"command_exists": "vim"}, "env": {"EDITOR": "vim"}},
            {"else": True, "env": {"EDITOR": "vi"}},
        ],
    }
    result = generate_module(mod, "fish")
    assert "if command -q nvim" in result
    assert 'set -gx EDITOR "nvim"' in result
    assert "else if command -q vim" in result
    assert "else" in result
    assert 'set -gx EDITOR "vi"' in result
    assert "end" in result


def test_conditional_module_zsh():
    """Conditional module generates correct Zsh if/elif/else/fi."""
    mod = {
        "name": "editor", "prefix": "05",
        "description": "Editor",
        "conditional": [
            {"if": {"command_exists": "nvim"}, "env": {"EDITOR": "nvim"}},
            {"elif": {"command_exists": "vim"}, "env": {"EDITOR": "vim"}},
            {"else": True, "env": {"EDITOR": "vi"}},
        ],
    }
    result = generate_module(mod, "zsh")
    assert "if (( $+commands[nvim] )); then" in result
    assert 'export EDITOR="nvim"' in result
    assert "elif (( $+commands[vim] )); then" in result
    assert 'export EDITOR="vi"' in result
    assert "fi" in result


def test_conditional_module_bash():
    """Conditional module generates correct Bash if/elif/else/fi."""
    mod = {
        "name": "editor", "prefix": "05",
        "description": "Editor",
        "conditional": [
            {"if": {"command_exists": "nvim"}, "env": {"EDITOR": "nvim"}},
            {"elif": {"command_exists": "vim"}, "env": {"EDITOR": "vim"}},
            {"else": True, "env": {"EDITOR": "vi"}},
        ],
    }
    result = generate_module(mod, "bash")
    assert "if command -v nvim &>/dev/null; then" in result
    assert 'export EDITOR="nvim"' in result
    assert "elif command -v vim &>/dev/null; then" in result
    assert "fi" in result


def test_conditional_module_pwsh():
    """Conditional module generates correct PowerShell if/elseif/else."""
    mod = {
        "name": "editor", "prefix": "05",
        "description": "Editor",
        "conditional": [
            {"if": {"command_exists": "nvim"}, "env": {"EDITOR": "nvim"}},
            {"elif": {"command_exists": "vim"}, "env": {"EDITOR": "vim"}},
            {"else": True, "env": {"EDITOR": "vi"}},
        ],
    }
    result = generate_module(mod, "pwsh")
    assert "if (" in result
    assert "Get-Command" in result
    assert "} elseif (" in result
    assert "} else {" in result
    assert '$env:EDITOR = "vi"' in result


def test_conditional_if_only():
    """Conditional with only an if branch (no elif/else)."""
    mod = {
        "name": "test", "prefix": "99",
        "description": "Test",
        "conditional": [
            {"if": {"command_exists": "foo"}, "aliases": {"f": "foo"}},
        ],
    }
    fish = generate_module(mod, "fish")
    assert "if command -q foo" in fish
    assert "alias f='foo'" in fish
    assert "end" in fish


def test_conditional_with_paths_and_aliases():
    """Conditional branches can contain different body types."""
    mod = {
        "name": "test", "prefix": "99",
        "description": "Test",
        "conditional": [
            {"if": {"command_exists": "eza"},
             "aliases": {"ls": "eza"}},
            {"else": True,
             "aliases": {"ls": "ls --color=auto"}},
        ],
    }
    result = generate_module(mod, "bash")
    assert "if command -v eza" in result
    assert 'alias ls="eza"' in result
    assert "else" in result
    assert 'alias ls="ls --color=auto"' in result
    assert "fi" in result


# ---------------------------------------------------------------------------
# Header validation
# ---------------------------------------------------------------------------

def test_header_present():
    """All generated content starts with the DO NOT EDIT header."""
    func = {"name": "is-darwin", "description": "macOS check",
            "predicate": "os_is_darwin"}
    mod = {"name": "path", "prefix": "00", "description": "PATH",
           "paths": ["$HOME/bin"]}

    for shell in SHELLS:
        for output in [
            generate_function(func, shell),
            generate_module(mod, shell),
        ]:
            assert output.startswith(HEADER), \
                f"Missing header in {shell} output:\n{output[:80]}"


# ---------------------------------------------------------------------------
# Validation
# ---------------------------------------------------------------------------

def test_validate_missing_function_name():
    """Validation catches missing function name."""
    manifest = {"functions": [{"description": "no name"}]}
    errors = validate_manifest(manifest)
    assert any("missing required field 'name'" in e for e in errors)


def test_validate_missing_function_body():
    """Validation catches function with neither predicate nor body."""
    manifest = {"functions": [{"name": "bad", "description": "no body or predicate"}]}
    errors = validate_manifest(manifest)
    assert any("must have either 'predicate' or 'body'" in e for e in errors)


def test_validate_unknown_predicate():
    """Validation catches unknown predicate name."""
    manifest = {"functions": [
        {"name": "bad", "description": "test", "predicate": "os_is_bsd"}
    ]}
    errors = validate_manifest(manifest)
    assert any("unknown predicate 'os_is_bsd'" in e for e in errors)


def test_validate_missing_module_prefix():
    """Validation catches missing module prefix."""
    manifest = {"modules": [
        {"name": "bad", "description": "test", "paths": ["/bin"]}
    ]}
    errors = validate_manifest(manifest)
    assert any("missing required field 'prefix'" in e for e in errors)


def test_validate_unknown_guard():
    """Validation catches unknown guard type."""
    manifest = {"modules": [
        {"name": "bad", "prefix": "99", "description": "test",
         "guard": {"nonexistent_guard": "/tmp/foo"}, "aliases": {"ls": "ls"}}
    ]}
    errors = validate_manifest(manifest)
    assert any("unknown guard type 'nonexistent_guard'" in e for e in errors)


def test_validate_unknown_string_guard():
    """Validation catches unknown string guard."""
    manifest = {"modules": [
        {"name": "bad", "prefix": "99", "description": "test",
         "guards": ["is_root"], "body": {"shared": "echo ok"}}
    ]}
    errors = validate_manifest(manifest)
    assert any("unknown string guard 'is_root'" in e for e in errors)


def test_validate_module_no_body_keys():
    """Validation catches module with no recognized body keys."""
    manifest = {"modules": [
        {"name": "bad", "prefix": "99", "description": "test"}
    ]}
    errors = validate_manifest(manifest)
    assert any("must have at least one of" in e for e in errors)


def test_validate_good_manifest():
    """Valid manifest produces no errors."""
    manifest = {
        "functions": [
            {"name": "is-darwin", "description": "macOS check",
             "predicate": "os_is_darwin"},
        ],
        "modules": [
            {"name": "path", "prefix": "00", "description": "PATH",
             "paths": ["$HOME/bin"]},
        ],
    }
    errors = validate_manifest(manifest)
    assert errors == []


def test_validate_env_not_dict():
    """Validation catches env that is not a dict."""
    manifest = {"modules": [
        {"name": "bad", "prefix": "99", "description": "test",
         "env": "EDITOR=vim"}
    ]}
    errors = validate_manifest(manifest)
    assert any("'env' must be a dict" in e for e in errors)


def test_validate_source_file_bad_type():
    """Validation catches source_file with wrong type."""
    manifest = {"modules": [
        {"name": "bad", "prefix": "99", "description": "test",
         "source_file": 42}
    ]}
    errors = validate_manifest(manifest)
    assert any("'source_file' must be a string or list" in e for e in errors)


def test_validate_eval_command_bad_type():
    """Validation catches eval_command that is not a string."""
    manifest = {"modules": [
        {"name": "bad", "prefix": "99", "description": "test",
         "eval_command": ["not", "a", "string"]}
    ]}
    errors = validate_manifest(manifest)
    assert any("'eval_command' must be a string" in e for e in errors)


def test_validate_conditional_not_list():
    """Validation catches conditional that is not a list."""
    manifest = {"modules": [
        {"name": "bad", "prefix": "99", "description": "test",
         "conditional": "not a list"}
    ]}
    errors = validate_manifest(manifest)
    assert any("'conditional' must be a non-empty list" in e for e in errors)


def test_validate_conditional_missing_if():
    """Validation catches conditional without 'if' in first branch."""
    manifest = {"modules": [
        {"name": "bad", "prefix": "99", "description": "test",
         "conditional": [{"elif": {"command_exists": "vim"}, "env": {"EDITOR": "vim"}}]}
    ]}
    errors = validate_manifest(manifest)
    assert any("first conditional branch must have an 'if'" in e for e in errors)


def test_validate_not_guard():
    """Validation accepts 'not' meta-guard with valid inner guard."""
    manifest = {"modules": [
        {"name": "good", "prefix": "99", "description": "test",
         "guard": {"not": {"command_exists": "vim"}},
         "body": {"shared": "echo ok"}}
    ]}
    errors = validate_manifest(manifest)
    assert errors == []


def test_validate_not_guard_bad_inner():
    """Validation catches 'not' meta-guard with invalid inner guard."""
    manifest = {"modules": [
        {"name": "bad", "prefix": "99", "description": "test",
         "guard": {"not": {"bad_guard": "x"}},
         "body": {"shared": "echo ok"}}
    ]}
    errors = validate_manifest(manifest)
    assert any("unknown guard type 'bad_guard'" in e for e in errors)


def test_validate_new_guards_accepted():
    """Validation accepts new guard types (file_exists, dir_exists, env_set)."""
    manifest = {"modules": [
        {"name": "a", "prefix": "01", "description": "t",
         "guard": {"file_exists": "/bin/sh"}, "body": {"shared": "echo ok"}},
        {"name": "b", "prefix": "02", "description": "t",
         "guard": {"dir_exists": "/tmp"}, "body": {"shared": "echo ok"}},
        {"name": "c", "prefix": "03", "description": "t",
         "guard": {"env_set": "HOME"}, "body": {"shared": "echo ok"}},
    ]}
    errors = validate_manifest(manifest)
    assert errors == []


def test_validate_good_manifest_with_new_constructs():
    """Valid manifest with all new constructs produces no errors."""
    manifest = {
        "functions": [
            {"name": "is-darwin", "description": "macOS",
             "predicate": "os_is_darwin"},
        ],
        "modules": [
            {"name": "env", "prefix": "05", "description": "Env",
             "env": {"EDITOR": "vim"}},
            {"name": "src", "prefix": "99", "description": "Source",
             "source_file": "$HOME/.local.sh"},
            {"name": "eval", "prefix": "10", "description": "Eval",
             "eval_command": "brew shellenv"},
            {"name": "cond", "prefix": "05", "description": "Cond",
             "conditional": [
                 {"if": {"command_exists": "nvim"}, "env": {"EDITOR": "nvim"}},
                 {"else": True, "env": {"EDITOR": "vi"}},
             ]},
        ],
    }
    errors = validate_manifest(manifest)
    assert errors == [], f"Unexpected errors: {errors}"


# ---------------------------------------------------------------------------
# Manifest merging
# ---------------------------------------------------------------------------

def test_merge_manifests_appends():
    """merge_manifests combines unique functions and modules from both sources."""
    base = {
        "functions": [{"name": "f1", "description": "d", "predicate": "os_is_darwin"}],
        "modules": [{"name": "m1", "prefix": "00", "description": "d", "paths": ["/a"]}],
    }
    extra = {
        "functions": [{"name": "f2", "description": "d2", "predicate": "os_is_linux"}],
        "modules": [{"name": "m2", "prefix": "10", "description": "d2", "paths": ["/b"]}],
    }
    merged = merge_manifests(base, extra)
    names_f = [f["name"] for f in merged["functions"]]
    names_m = [m["name"] for m in merged["modules"]]
    assert names_f == ["f1", "f2"]
    assert names_m == ["m1", "m2"]


def test_merge_manifests_empty_extra():
    """merge_manifests with empty extra returns base unchanged."""
    base = {
        "functions": [{"name": "f1", "description": "d", "predicate": "os_is_darwin"}],
        "modules": [],
    }
    merged = merge_manifests(base, {})
    assert len(merged["functions"]) == 1
    assert len(merged["modules"]) == 0


def test_merge_manifests_override():
    """merge_manifests uses last-wins: same-name item in extra replaces base."""
    base = {
        "functions": [{"name": "f1", "description": "original", "predicate": "os_is_darwin"}],
        "modules": [{"name": "m1", "prefix": "00", "description": "original", "paths": ["/a"]}],
    }
    extra = {
        "functions": [{"name": "f1", "description": "overridden", "predicate": "os_is_linux"}],
        "modules": [{"name": "m1", "prefix": "01", "description": "overridden", "paths": ["/b"]}],
    }
    merged = merge_manifests(base, extra)
    assert len(merged["functions"]) == 1
    assert merged["functions"][0]["description"] == "overridden"
    assert merged["functions"][0]["predicate"] == "os_is_linux"
    assert len(merged["modules"]) == 1
    assert merged["modules"][0]["description"] == "overridden"
    assert merged["modules"][0]["paths"] == ["/b"]


def test_resolve_sources_file():
    """resolve_sources passes through existing files."""
    import tempfile
    with tempfile.TemporaryDirectory() as tmpdir:
        p = Path(tmpdir) / "test.yaml"
        p.write_text("functions: []\n")
        result = resolve_sources([str(p)])
        assert result == [p]


def test_resolve_sources_dir():
    """resolve_sources resolves directory to dir/shell.yaml."""
    import tempfile
    with tempfile.TemporaryDirectory() as tmpdir:
        p = Path(tmpdir)
        yaml_path = p / "shell.yaml"
        yaml_path.write_text("functions: []\n")
        result = resolve_sources([str(p)])
        assert result == [yaml_path]


def test_resolve_sources_missing():
    """resolve_sources skips nonexistent paths with a warning."""
    import warnings as w
    with w.catch_warnings(record=True) as caught:
        w.simplefilter("always")
        result = resolve_sources(["/nonexistent/path/to/nothing"])
        assert result == []
        assert len(caught) == 1
        assert "does not exist" in str(caught[0].message)


# ---------------------------------------------------------------------------
# Output directory mapping
# ---------------------------------------------------------------------------

def test_get_output_dirs_source():
    """get_output_dirs with target=None returns chezmoi source paths."""
    repo = Path("/repo")
    dirs = get_output_dirs(None, repo)
    assert dirs["fish"]["functions"] == repo / "dot_config" / "fish" / "functions"
    assert dirs["zsh"]["functions"] == repo / "dot_config" / "zsh" / "dot_zfunctions"
    assert dirs["bash"]["functions"] == repo / "dot_config" / "bash" / "functions"
    assert dirs["pwsh"]["functions"] == repo / "dot_config" / "powershell" / "functions"
    assert dirs["fish"]["modules"] == repo / "dot_config" / "fish" / "conf.d"
    assert dirs["zsh"]["modules"] == repo / "dot_config" / "zsh" / "dot_zshrc.d"
    assert dirs["bash"]["modules"] == repo / "dot_config" / "bash" / "bashrc.d"
    assert dirs["pwsh"]["modules"] == repo / "dot_config" / "powershell" / "conf.d"


def test_get_output_dirs_target():
    """get_output_dirs with target returns real config paths."""
    target = Path("/home/user/.config")
    dirs = get_output_dirs(target, Path("/unused"))
    assert dirs["fish"]["functions"] == target / "fish" / "functions"
    assert dirs["zsh"]["functions"] == target / "zsh" / ".zfunctions"
    assert dirs["bash"]["functions"] == target / "bash" / "functions"
    assert dirs["pwsh"]["functions"] == target / "powershell" / "functions"
    assert dirs["fish"]["modules"] == target / "fish" / "conf.d"
    assert dirs["zsh"]["modules"] == target / "zsh" / ".zshrc.d"
    assert dirs["bash"]["modules"] == target / "bash" / "bashrc.d"
    assert dirs["pwsh"]["modules"] == target / "powershell" / "conf.d"


# ---------------------------------------------------------------------------
# Shell constants
# ---------------------------------------------------------------------------

def test_shell_constants():
    """Shell constants are properly defined."""
    assert SHELLS == ("fish", "zsh", "bash", "pwsh")
    assert SHELL_INDEX["fish"] == 0
    assert SHELL_INDEX["pwsh"] == 3
    assert len(SHELL_MODULE_EXT) == 4
    assert len(SHELL_FUNC_EXT) == 4
    assert SHELL_FUNC_EXT["zsh"] == ""  # autoload, no extension


def test_guards_and_conditions_consistent():
    """GUARDS and GUARD_CONDITIONS have the same keys."""
    assert set(GUARDS.keys()) == set(GUARD_CONDITIONS.keys())
    for key in GUARDS:
        assert len(GUARDS[key]) == 4, f"GUARDS[{key}] must be 4-tuple"
        assert len(GUARD_CONDITIONS[key]) == 4, f"GUARD_CONDITIONS[{key}] must be 4-tuple"


def test_predicates_are_4_tuples():
    """All predicates are 4-tuples."""
    for key, val in PREDICATES.items():
        assert len(val) == 4, f"PREDICATES[{key}] must be 4-tuple"


# ---------------------------------------------------------------------------
# generate_all
# ---------------------------------------------------------------------------

def test_generate_all_to_tempdir():
    """generate_all creates files for all 4 shells in a temp directory."""
    import tempfile
    manifest = {
        "functions": [
            {"name": "is-darwin", "description": "macOS check",
             "predicate": "os_is_darwin"},
        ],
        "modules": [
            {"name": "path", "prefix": "00", "description": "PATH",
             "paths": ["$HOME/bin"]},
        ],
    }
    with tempfile.TemporaryDirectory() as tmpdir:
        target = Path(tmpdir)
        files = generate_all(manifest, target, Path("/unused"))
        # 1 function × 4 shells + 1 module × 4 shells = 8
        assert len(files) == 8, f"Expected 8 files, got {len(files)}"
        for f in files:
            assert f.exists(), f"File not found: {f}"
            assert f.read_text().startswith(HEADER), f"Missing header: {f}"


def test_generate_all_file_extensions():
    """generate_all uses correct file extensions for each shell."""
    import tempfile
    manifest = {
        "functions": [
            {"name": "test-func", "description": "test",
             "predicate": "os_is_darwin"},
        ],
        "modules": [
            {"name": "test-mod", "prefix": "99", "description": "test",
             "paths": ["$HOME/bin"]},
        ],
    }
    with tempfile.TemporaryDirectory() as tmpdir:
        target = Path(tmpdir)
        files = generate_all(manifest, target, Path("/unused"))
        names = [f.name for f in files]
        # Functions
        assert "test-func.fish" in names
        assert "test-func" in names  # zsh, no ext
        assert "test-func.bash" in names
        assert "test-func.ps1" in names
        # Modules
        assert "99-test-mod.fish" in names
        assert "99-test-mod.zsh" in names
        assert "99-test-mod.bash" in names
        assert "99-test-mod.ps1" in names


# ---------------------------------------------------------------------------
# Test runner
# ---------------------------------------------------------------------------

def run_all_tests():
    tests = [v for k, v in sorted(globals().items()) if k.startswith("test_")]
    passed = failed = 0
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
