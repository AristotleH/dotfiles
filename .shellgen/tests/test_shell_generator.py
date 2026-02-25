#!/usr/bin/env python3
"""
Unit tests for generate_shell.py

Run with: python3 tests/test_shell_generator.py
"""

import sys
from pathlib import Path

# Add parent directory to path so we can import the generator
sys.path.insert(0, str(Path(__file__).parent.parent))
from generate_shell import (
    PREDICATES,
    GUARDS,
    translate_guard,
    generate_function,
    generate_module,
    generate_all,
    validate_manifest,
    load_manifest,
    merge_manifests,
    resolve_sources,
    get_output_dirs,
    HEADER,
)


# ---------------------------------------------------------------------------
# Predicate functions
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


def test_predicate_linux():
    """Linux predicate works for both shells."""
    func = {"name": "is-linux", "description": "Check if running on Linux",
            "predicate": "os_is_linux"}
    fish = generate_function(func, "fish")
    zsh = generate_function(func, "zsh")
    assert 'test (uname) = "Linux"' in fish
    assert "[[ $OSTYPE == *linux* ]]" in zsh


# ---------------------------------------------------------------------------
# Complex functions
# ---------------------------------------------------------------------------

def test_complex_fish():
    """Complex function wraps body in function/end for Fish."""
    func = {
        "name": "in_dir",
        "description": "Run a command in a different directory",
        "usage": "in_dir <dir> <cmd>",
        "body": {
            "fish": "echo hello\necho world",
            "zsh": 'echo "hello"\necho "world"',
        },
    }
    result = generate_function(func, "fish")
    assert "function in_dir" in result
    assert "end" in result.split("\n")[-2]  # second to last line
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
        },
    }
    result = generate_function(func, "zsh")
    assert "function" not in result.split("\n")[1]  # no function wrapper
    assert 'echo "hello"' in result


# ---------------------------------------------------------------------------
# Guards
# ---------------------------------------------------------------------------

def test_guard_command_exists_fish():
    guard = {"command_exists": "eza"}
    result = translate_guard(guard, "fish")
    assert result == "command -q eza; or return 0"


def test_guard_command_exists_zsh():
    guard = {"command_exists": "eza"}
    result = translate_guard(guard, "zsh")
    assert result == "(( $+commands[eza] )) || return 0"


def test_guard_env_equals_fish():
    guard = {"env_equals": {"var": "TMUX_AUTO_ATTACH", "value": "1"}}
    result = translate_guard(guard, "fish")
    assert 'test "$TMUX_AUTO_ATTACH" = "1"' in result


def test_guard_env_equals_zsh():
    guard = {"env_equals": {"var": "TMUX_AUTO_ATTACH", "value": "1"}}
    result = translate_guard(guard, "zsh")
    assert '[[ "$TMUX_AUTO_ATTACH" == "1" ]]' in result


def test_guard_env_not_set_fish():
    guard = {"env_not_set": "TMUX"}
    result = translate_guard(guard, "fish")
    assert "not set -q TMUX; or return 0" == result


def test_guard_env_not_set_zsh():
    guard = {"env_not_set": "TMUX"}
    result = translate_guard(guard, "zsh")
    assert "[[ -z $TMUX ]] || return 0" == result


def test_guard_is_tty():
    assert "isatty stdin" in translate_guard("is_tty", "fish")
    assert "[[ -t 0 ]]" in translate_guard("is_tty", "zsh")


def test_guard_is_interactive():
    assert "status is-interactive" in translate_guard("is_interactive", "fish")
    assert "[[ -o interactive ]]" in translate_guard("is_interactive", "zsh")


def test_guard_not_env_equals():
    guard = {"not_env_equals": {"var": "TERM_PROGRAM", "value": "vscode"}}
    fish = translate_guard(guard, "fish")
    zsh = translate_guard(guard, "zsh")
    assert '!= "vscode"' in fish
    assert '!= "vscode"' in zsh


# ---------------------------------------------------------------------------
# Module generators
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


def test_custom_module_shared_body():
    """Custom module with shared body works for both shells."""
    mod = {
        "name": "tmux", "prefix": "70",
        "description": "Tmux auto-attach",
        "guards": [{"command_exists": "tmux"}],
        "body": {"shared": "tmux attach 2>/dev/null || tmux new-session"},
    }
    fish = generate_module(mod, "fish")
    zsh = generate_module(mod, "zsh")
    assert "tmux attach 2>/dev/null || tmux new-session" in fish
    assert "tmux attach 2>/dev/null || tmux new-session" in zsh
    assert "command -q tmux; or return 0" in fish
    assert "(( $+commands[tmux] )) || return 0" in zsh


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
    result = generate_module(mod, "zsh")
    lines = result.split("\n")
    guard_lines = [l for l in lines if "return 0" in l]
    assert len(guard_lines) == 3


def test_header_present():
    """All generated content starts with the DO NOT EDIT header."""
    func = {"name": "is-darwin", "description": "macOS check",
            "predicate": "os_is_darwin"}
    mod = {"name": "path", "prefix": "00", "description": "PATH",
           "paths": ["$HOME/bin"]}

    for output in [
        generate_function(func, "fish"),
        generate_function(func, "zsh"),
        generate_module(mod, "fish"),
        generate_module(mod, "zsh"),
    ]:
        assert output.startswith(HEADER), f"Missing header in output:\n{output[:80]}"


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
         "guard": {"file_exists": "/tmp/foo"}, "aliases": {"ls": "ls"}}
    ]}
    errors = validate_manifest(manifest)
    assert any("unknown guard type 'file_exists'" in e for e in errors)


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
    from pathlib import Path
    repo = Path("/repo")
    dirs = get_output_dirs(None, repo)
    assert dirs[0] == repo / "dot_config" / "fish" / "functions"
    assert dirs[1] == repo / "dot_config" / "zsh" / "dot_zfunctions"
    assert dirs[2] == repo / "dot_config" / "fish" / "conf.d"
    assert dirs[3] == repo / "dot_config" / "zsh" / "dot_zshrc.d"


def test_get_output_dirs_target():
    """get_output_dirs with target returns real config paths."""
    from pathlib import Path
    target = Path("/home/user/.config")
    dirs = get_output_dirs(target, Path("/unused"))
    assert dirs[0] == target / "fish" / "functions"
    assert dirs[1] == target / "zsh" / ".zfunctions"
    assert dirs[2] == target / "fish" / "conf.d"
    assert dirs[3] == target / "zsh" / ".zshrc.d"


# ---------------------------------------------------------------------------
# generate_all
# ---------------------------------------------------------------------------

def test_generate_all_to_tempdir():
    """generate_all creates files in a temp directory."""
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
        assert len(files) == 4
        for f in files:
            assert f.exists()
            assert f.read_text().startswith(HEADER)


# ---------------------------------------------------------------------------
# Test runner
# ---------------------------------------------------------------------------

def run_all_tests():
    tests = [v for k, v in sorted(globals().items()) if k.startswith("test_")]
    passed = failed = 0
    for test in tests:
        try:
            test()
            print(f"  ✓ {test.__name__}")
            passed += 1
        except AssertionError as e:
            print(f"  ✗ {test.__name__}: {e}")
            failed += 1
        except Exception as e:
            print(f"  ✗ {test.__name__}: Unexpected error: {e}")
            failed += 1

    print(f"\n{passed} passed, {failed} failed")
    return 0 if failed == 0 else 1


if __name__ == "__main__":
    sys.exit(run_all_tests())
