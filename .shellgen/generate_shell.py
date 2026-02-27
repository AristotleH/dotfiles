#!/usr/bin/env python3
"""
Shell configuration transpiler: YAML DSL → Fish, Zsh, Bash, PowerShell

Transpiles a declarative YAML manifest into shell-specific configuration
files for four target shells. The YAML DSL provides high-level constructs
(environment variables, aliases, conditionals, guards, etc.) that are
translated into idiomatic syntax for each shell.

Target shells:
    fish  — Fish shell (macOS, Linux)
    zsh   — Z shell (macOS, Linux)
    bash  — Bash / Git Bash (macOS, Linux, Windows)
    pwsh  — PowerShell Core (Windows)

Usage:
    # No args — default to script_dir/shell.yaml (backward compat)
    python3 generate_shell.py

    # Positional args: files or directories (dir → dir/shell.yaml)
    python3 generate_shell.py shell.yaml ~/.config/shell.d/work.yaml

    # Pipe paths from stdin (one per line)
    find ~/.config/shell.d -name 'shell.yaml' | python3 generate_shell.py

    # Mixed: positional + stdin
    echo ~/.config/shell.d/work.yaml | python3 generate_shell.py shell.yaml

    # --target still works
    python3 generate_shell.py shell.yaml extras.yaml --target ~/.config
"""

import argparse
import sys
import warnings
import yaml
from pathlib import Path
from typing import Any, Dict, List, Optional


HEADER = "# Generated from .shellgen/shell.yaml -- DO NOT EDIT"

# ---------------------------------------------------------------------------
# Shell constants
# ---------------------------------------------------------------------------

SHELLS = ("fish", "zsh", "bash", "pwsh")
SHELL_INDEX = {"fish": 0, "zsh": 1, "bash": 2, "pwsh": 3}

# File extensions for modules ({prefix}-{name}{ext})
SHELL_MODULE_EXT = {
    "fish": ".fish",
    "zsh":  ".zsh",
    "bash": ".bash",
    "pwsh": ".ps1",
}

# File extensions for functions ({name}{ext})  — zsh autoload has no extension
SHELL_FUNC_EXT = {
    "fish": ".fish",
    "zsh":  "",
    "bash": ".bash",
    "pwsh": ".ps1",
}


# ---------------------------------------------------------------------------
# Data tables — add a new guard or predicate by adding one line
# ---------------------------------------------------------------------------
# Each entry is a 4-tuple: (fish, zsh, bash, pwsh)

# Guards as bail / early-return lines (used in module preamble).
# Guard semantics: "if condition is NOT met, return 0 (skip this file)."
GUARDS = {
    "command_exists": (
        "command -q {0}; or return 0",
        "(( $+commands[{0}] )) || return 0",
        "command -v {0} &>/dev/null || return 0",
        "if (-not (Get-Command '{0}' -ErrorAction SilentlyContinue)) {{ return }}",
    ),
    "env_not_set": (
        "not set -q {0}; or return 0",
        "[[ -z ${0} ]] || return 0",
        '[[ -z "${0}" ]] || return 0',
        "if ($env:{0}) {{ return }}",
    ),
    "env_set": (
        "set -q {0}; or return 0",
        "[[ -n ${0} ]] || return 0",
        '[[ -n "${0}" ]] || return 0',
        "if (-not $env:{0}) {{ return }}",
    ),
    "env_equals": (
        'test "${var}" = "{value}"; or return 0',
        '[[ "${var}" == "{value}" ]] || return 0',
        '[[ "${var}" == "{value}" ]] || return 0',
        "if ($env:{var} -ne '{value}') {{ return }}",
    ),
    "not_env_equals": (
        'test "${var}" != "{value}"; or return 0',
        '[[ "${var}" != "{value}" ]] || return 0',
        '[[ "${var}" != "{value}" ]] || return 0',
        "if ($env:{var} -eq '{value}') {{ return }}",
    ),
    "is_tty": (
        "isatty stdin; or return 0",
        "[[ -t 0 ]] || return 0",
        "[[ -t 0 ]] || return 0",
        "if (-not [Environment]::UserInteractive) { return }",
    ),
    "is_interactive": (
        "status is-interactive; or return 0",
        "[[ -o interactive ]] || return 0",
        '[[ $- == *i* ]] || return 0',
        "if (-not [Environment]::UserInteractive) { return }",
    ),
    "file_exists": (
        "test -f {0}; or return 0",
        "[[ -f {0} ]] || return 0",
        "[[ -f {0} ]] || return 0",
        "if (-not (Test-Path '{0}' -PathType Leaf)) {{ return }}",
    ),
    "dir_exists": (
        "test -d {0}; or return 0",
        "[[ -d {0} ]] || return 0",
        "[[ -d {0} ]] || return 0",
        "if (-not (Test-Path '{0}' -PathType Container)) {{ return }}",
    ),
}

# Guard conditions (for use in if/elif — no bail/return).
# Same semantics: expression is truthy when condition IS met.
GUARD_CONDITIONS = {
    "command_exists": (
        "command -q {0}",
        "(( $+commands[{0}] ))",
        "command -v {0} &>/dev/null",
        "(Get-Command '{0}' -ErrorAction SilentlyContinue)",
    ),
    "env_not_set": (
        "not set -q {0}",
        "[[ -z ${0} ]]",
        '[[ -z "${0}" ]]',
        "(-not $env:{0})",
    ),
    "env_set": (
        "set -q {0}",
        "[[ -n ${0} ]]",
        '[[ -n "${0}" ]]',
        "($env:{0})",
    ),
    "env_equals": (
        'test "${var}" = "{value}"',
        '[[ "${var}" == "{value}" ]]',
        '[[ "${var}" == "{value}" ]]',
        "($env:{var} -eq '{value}')",
    ),
    "not_env_equals": (
        'test "${var}" != "{value}"',
        '[[ "${var}" != "{value}" ]]',
        '[[ "${var}" != "{value}" ]]',
        "($env:{var} -ne '{value}')",
    ),
    "is_tty": (
        "isatty stdin",
        "[[ -t 0 ]]",
        "[[ -t 0 ]]",
        "[Environment]::UserInteractive",
    ),
    "is_interactive": (
        "status is-interactive",
        "[[ -o interactive ]]",
        '[[ $- == *i* ]]',
        "[Environment]::UserInteractive",
    ),
    "file_exists": (
        "test -f {0}",
        "[[ -f {0} ]]",
        "[[ -f {0} ]]",
        "(Test-Path '{0}' -PathType Leaf)",
    ),
    "dir_exists": (
        "test -d {0}",
        "[[ -d {0} ]]",
        "[[ -d {0} ]]",
        "(Test-Path '{0}' -PathType Container)",
    ),
}

# Predicate bodies (used in predicate functions).
# Each entry: predicate_name -> (fish_body, zsh_body, bash_body, pwsh_body)
PREDICATES = {
    "os_is_darwin": (
        'test (uname) = "Darwin"',
        "[[ $OSTYPE == *darwin* ]]",
        "[[ $OSTYPE == darwin* ]]",
        "$IsMacOS",
    ),
    "os_is_linux": (
        'test (uname) = "Linux"',
        "[[ $OSTYPE == *linux* ]]",
        "[[ $OSTYPE == linux* ]]",
        "$IsLinux",
    ),
    "os_is_windows": (
        'string match -q "Msys" (uname -o 2>/dev/null; or echo unknown)',
        "[[ $OSTYPE == msys* ]]",
        "[[ $OSTYPE == msys* ]]",
        "$IsWindows",
    ),
    "arch_is_arm64": (
        'test (uname -m) = arm64; or test (uname -m) = aarch64',
        "[[ $(uname -m) == (arm64|aarch64) ]]",
        '[[ $(uname -m) == arm64 || $(uname -m) == aarch64 ]]',
        "[Runtime.InteropServices.RuntimeInformation]::OSArchitecture -eq 'Arm64'",
    ),
    "arch_is_x86_64": (
        'test (uname -m) = "x86_64"',
        "[[ $(uname -m) == x86_64 ]]",
        '[[ $(uname -m) == x86_64 ]]',
        "[Runtime.InteropServices.RuntimeInformation]::OSArchitecture -eq 'X64'",
    ),
}

# All recognized guard keys (for validation)
ALL_GUARD_KEYS = set(GUARDS.keys()) | {"not"}


# ---------------------------------------------------------------------------
# Validation
# ---------------------------------------------------------------------------

# Recognized body keys for modules (and conditional branches)
BODY_KEYS = {"paths", "aliases", "tool", "body", "env", "source_file",
             "eval_command", "conditional"}


def validate_manifest(manifest: Dict) -> List[str]:
    """Validate the manifest and return a list of error messages (empty = OK)."""
    errors: List[str] = []

    for i, func in enumerate(manifest.get("functions", [])):
        ctx = f"functions[{i}]"
        if "name" not in func:
            errors.append(f"{ctx}: missing required field 'name'")
            continue
        ctx = f"function '{func['name']}'"
        if "description" not in func:
            errors.append(f"{ctx}: missing required field 'description'")

        has_predicate = "predicate" in func
        has_body = "body" in func
        if not has_predicate and not has_body:
            errors.append(f"{ctx}: must have either 'predicate' or 'body'")
        if has_predicate and func["predicate"] not in PREDICATES:
            errors.append(
                f"{ctx}: unknown predicate '{func['predicate']}' "
                f"(known: {', '.join(sorted(PREDICATES))})"
            )

    for i, mod in enumerate(manifest.get("modules", [])):
        ctx = f"modules[{i}]"
        if "name" not in mod:
            errors.append(f"{ctx}: missing required field 'name'")
            continue
        ctx = f"module '{mod['name']}'"
        if "prefix" not in mod:
            errors.append(f"{ctx}: missing required field 'prefix'")
        if "description" not in mod:
            errors.append(f"{ctx}: missing required field 'description'")

        # Check that module has at least one recognized body key
        if not any(k in mod for k in BODY_KEYS):
            errors.append(
                f"{ctx}: must have at least one of: "
                f"{', '.join(sorted(BODY_KEYS))}"
            )

        # Validate env
        if "env" in mod:
            _validate_env(mod["env"], ctx, errors)

        # Validate source_file
        if "source_file" in mod:
            _validate_source_file(mod["source_file"], ctx, errors)

        # Validate eval_command
        if "eval_command" in mod:
            if not isinstance(mod["eval_command"], str):
                errors.append(f"{ctx}: 'eval_command' must be a string")

        # Validate conditional
        if "conditional" in mod:
            _validate_conditional(mod["conditional"], ctx, errors)

        # Validate guards
        for guard in _collect_guards(mod):
            _validate_guard(guard, ctx, errors)

    return errors


def _validate_env(env: Any, ctx: str, errors: List[str]):
    """Validate an env block."""
    if not isinstance(env, dict):
        errors.append(f"{ctx}: 'env' must be a dict of VAR: value pairs")
        return
    for key, val in env.items():
        if not isinstance(key, str):
            errors.append(f"{ctx}: env key must be a string, got {type(key)}")
        if not isinstance(val, (str, int, float)):
            errors.append(f"{ctx}: env value for '{key}' must be a string or number")


def _validate_source_file(sf: Any, ctx: str, errors: List[str]):
    """Validate a source_file block."""
    if isinstance(sf, str):
        return
    if isinstance(sf, list):
        for item in sf:
            if not isinstance(item, str):
                errors.append(f"{ctx}: source_file list items must be strings")
        return
    errors.append(f"{ctx}: 'source_file' must be a string or list of strings")


def _validate_conditional(cond: Any, ctx: str, errors: List[str]):
    """Validate a conditional block."""
    if not isinstance(cond, list) or len(cond) == 0:
        errors.append(f"{ctx}: 'conditional' must be a non-empty list")
        return

    first = cond[0]
    if not isinstance(first, dict) or "if" not in first:
        errors.append(f"{ctx}: first conditional branch must have an 'if' key")
        return

    # Validate the if condition guard
    _validate_guard(first["if"], f"{ctx} conditional[0]", errors)
    _validate_conditional_branch_body(first, f"{ctx} conditional[0]", errors)

    for i, branch in enumerate(cond[1:], start=1):
        bctx = f"{ctx} conditional[{i}]"
        if not isinstance(branch, dict):
            errors.append(f"{bctx}: branch must be a dict")
            continue
        has_elif = "elif" in branch
        has_else = "else" in branch
        if not has_elif and not has_else:
            errors.append(f"{bctx}: branch must have 'elif' or 'else' key")
        if has_elif and has_else:
            errors.append(f"{bctx}: branch cannot have both 'elif' and 'else'")
        if has_elif:
            _validate_guard(branch["elif"], bctx, errors)
        _validate_conditional_branch_body(branch, bctx, errors)


def _validate_conditional_branch_body(branch: Dict, ctx: str,
                                       errors: List[str]):
    """Validate that a conditional branch has at least one body key."""
    branch_body_keys = BODY_KEYS - {"conditional"}  # no nested conditionals
    if not any(k in branch for k in branch_body_keys
               if k not in ("if", "elif", "else")):
        # Filter out the condition keys
        body_found = False
        for k in branch:
            if k in branch_body_keys:
                body_found = True
                break
        if not body_found:
            errors.append(
                f"{ctx}: conditional branch must have at least one body key "
                f"({', '.join(sorted(branch_body_keys))})"
            )


def _validate_guard(guard: Any, ctx: str, errors: List[str]):
    """Validate a single guard entry."""
    if isinstance(guard, str):
        if guard not in GUARDS:
            errors.append(
                f"{ctx}: unknown string guard '{guard}' "
                f"(known: {', '.join(sorted(ALL_GUARD_KEYS))})"
            )
    elif isinstance(guard, dict):
        key = next(iter(guard), None)
        if key == "not":
            # Recursive: validate inner guard
            inner = guard["not"]
            _validate_guard(inner, f"{ctx} (inside 'not')", errors)
        elif key not in GUARDS:
            errors.append(
                f"{ctx}: unknown guard type '{key}' "
                f"(known: {', '.join(sorted(ALL_GUARD_KEYS))})"
            )
    else:
        errors.append(f"{ctx}: invalid guard type: {type(guard)}")


# ---------------------------------------------------------------------------
# Guard translation
# ---------------------------------------------------------------------------

def _collect_guards(mod: Dict) -> List[Any]:
    """Collect guards from a module (singular 'guard' or list 'guards')."""
    if "guards" in mod:
        return mod["guards"]
    if "guard" in mod:
        return [mod["guard"]]
    return []


def translate_guard(guard: Any, shell: str) -> str:
    """Convert a declarative guard to a shell-specific bail line."""
    idx = SHELL_INDEX[shell]

    # Handle 'not' meta-guard
    if isinstance(guard, dict) and next(iter(guard), None) == "not":
        inner = guard["not"]
        cond = translate_guard_condition(inner, shell)
        # Negate: if condition IS true, bail
        if shell == "fish":
            return f"{cond}; and return 0"
        elif shell == "pwsh":
            return f"if ({cond}) {{ return }}"
        else:  # bash, zsh
            return f"{cond} && return 0"

    if isinstance(guard, str):
        if guard not in GUARDS:
            raise ValueError(f"Unknown string guard: {guard}")
        return GUARDS[guard][idx]

    if isinstance(guard, dict):
        key = next(iter(guard))
        if key not in GUARDS:
            raise ValueError(f"Unknown dict guard: {guard}")
        value = guard[key]
        template = GUARDS[key][idx]

        if isinstance(value, dict):
            return template.format(**value)
        else:
            return template.format(value)

    raise ValueError(f"Invalid guard type: {type(guard)}")


def translate_guard_condition(guard: Any, shell: str) -> str:
    """Convert a declarative guard to a shell-specific condition expression.

    Unlike translate_guard(), this returns a condition (no bail/return).
    Used for if/elif in conditional blocks.
    """
    idx = SHELL_INDEX[shell]

    # Handle 'not' meta-guard
    if isinstance(guard, dict) and next(iter(guard), None) == "not":
        inner = guard["not"]
        cond = translate_guard_condition(inner, shell)
        if shell == "fish":
            return f"not {cond}"
        elif shell == "pwsh":
            return f"(-not {cond})"
        else:  # bash, zsh
            return f"! {cond}"

    if isinstance(guard, str):
        if guard not in GUARD_CONDITIONS:
            raise ValueError(f"Unknown string guard: {guard}")
        return GUARD_CONDITIONS[guard][idx]

    if isinstance(guard, dict):
        key = next(iter(guard))
        if key not in GUARD_CONDITIONS:
            raise ValueError(f"Unknown dict guard: {guard}")
        value = guard[key]
        template = GUARD_CONDITIONS[key][idx]

        if isinstance(value, dict):
            return template.format(**value)
        else:
            return template.format(value)

    raise ValueError(f"Invalid guard type: {type(guard)}")


# ---------------------------------------------------------------------------
# Render helpers — per-construct output for each shell
# ---------------------------------------------------------------------------

def _render_path(path: str, shell: str) -> str:
    """Render a single PATH addition."""
    if shell == "fish":
        return f"fish_add_path {path}"
    elif shell == "pwsh":
        return f'$env:PATH = "{path}" + [IO.Path]::PathSeparator + $env:PATH'
    else:  # bash, zsh
        return f'export PATH="{path}:$PATH"'


def _render_alias(name: str, cmd: str, shell: str) -> str:
    """Render a single alias definition."""
    if shell == "fish":
        return f"alias {name}='{cmd}'"
    elif shell == "pwsh":
        # PowerShell can't do alias with args, so always use function form
        return f"function {name} {{ {cmd} @args }}"
    else:  # bash, zsh
        return f'alias {name}="{cmd}"'


def _render_tool_init(tool: str, shell: str) -> str:
    """Render a tool init invocation."""
    if shell == "fish":
        return f"{tool} init fish | source"
    elif shell == "pwsh":
        return f"(& {tool} init pwsh) | Invoke-Expression"
    else:  # bash, zsh
        return f'eval "$({tool} init {shell})"'


def _render_env_var(var: str, value: Any, shell: str) -> str:
    """Render a single environment variable export."""
    value = str(value)
    if shell == "fish":
        return f'set -gx {var} "{value}"'
    elif shell == "pwsh":
        return f'$env:{var} = "{value}"'
    else:  # bash, zsh
        return f'export {var}="{value}"'


def _render_source_file(path: str, shell: str) -> str:
    """Render a source-file-if-exists line."""
    if shell == "fish":
        return f'test -f "{path}"; and source "{path}"'
    elif shell == "pwsh":
        return f'if (Test-Path "{path}") {{ . "{path}" }}'
    else:  # bash, zsh
        return f'[[ -f "{path}" ]] && source "{path}"'


def _render_eval_command(cmd: str, shell: str) -> str:
    """Render an eval-command invocation.

    The command string may contain {shell} which is replaced with the
    target shell name.
    """
    resolved = cmd.replace("{shell}", shell if shell != "pwsh" else "pwsh")
    if shell == "fish":
        return f"{resolved} | source"
    elif shell == "pwsh":
        return f"(& {resolved}) | Invoke-Expression"
    else:  # bash, zsh
        return f'eval "$({resolved})"'


def _render_body_lines(section: Dict, shell: str) -> List[str]:
    """Render body constructs from a dict (module or conditional branch).

    Returns a flat list of output lines (no header, no guards).
    Handles: env, paths, aliases, tool, source_file, eval_command, body.
    """
    lines: List[str] = []

    if "env" in section:
        for var, val in section["env"].items():
            lines.append(_render_env_var(var, val, shell))

    if "paths" in section:
        for p in section["paths"]:
            lines.append(_render_path(p, shell))

    if "aliases" in section:
        for alias_name, alias_cmd in section["aliases"].items():
            lines.append(_render_alias(alias_name, alias_cmd, shell))

    if "tool" in section:
        lines.append(_render_tool_init(section["tool"], shell))

    if "source_file" in section:
        sf = section["source_file"]
        if isinstance(sf, str):
            lines.append(_render_source_file(sf, shell))
        elif isinstance(sf, list):
            for path in sf:
                lines.append(_render_source_file(path, shell))

    if "eval_command" in section:
        lines.append(_render_eval_command(section["eval_command"], shell))

    if "body" in section:
        body_section = section["body"]
        if shell in body_section:
            body = body_section[shell].rstrip("\n")
        elif "shared" in body_section:
            body = body_section["shared"].rstrip("\n")
        else:
            body = ""
        if body:
            lines.extend(body.split("\n"))

    return lines


def _render_conditional(conditional: List[Dict], shell: str) -> str:
    """Render a conditional (if/elif/else) block."""
    parts: List[str] = []

    for i, branch in enumerate(conditional):
        if "if" in branch:
            cond = translate_guard_condition(branch["if"], shell)
            body_lines = _render_body_lines(branch, shell)
            if shell == "fish":
                parts.append(f"if {cond}")
            elif shell == "pwsh":
                parts.append(f"if ({cond}) {{")
            else:  # bash, zsh
                parts.append(f"if {cond}; then")
            for line in body_lines:
                parts.append(f"    {line}" if line.strip() else "")

        elif "elif" in branch:
            cond = translate_guard_condition(branch["elif"], shell)
            body_lines = _render_body_lines(branch, shell)
            if shell == "fish":
                parts.append(f"else if {cond}")
            elif shell == "pwsh":
                parts.append(f"}} elseif ({cond}) {{")
            else:  # bash, zsh
                parts.append(f"elif {cond}; then")
            for line in body_lines:
                parts.append(f"    {line}" if line.strip() else "")

        elif "else" in branch:
            body_lines = _render_body_lines(branch, shell)
            if shell == "fish":
                parts.append("else")
            elif shell == "pwsh":
                parts.append("} else {")
            else:  # bash, zsh
                parts.append("else")
            for line in body_lines:
                parts.append(f"    {line}" if line.strip() else "")

    # Close the block
    if shell == "fish":
        parts.append("end")
    elif shell == "pwsh":
        parts.append("}")
    else:  # bash, zsh
        parts.append("fi")

    return "\n".join(parts)


# ---------------------------------------------------------------------------
# Function generator
# ---------------------------------------------------------------------------

def generate_function(func: Dict, shell: str) -> str:
    """Generate a function file for the given shell."""
    name = func["name"]
    desc = func["description"]

    if "predicate" in func:
        return _generate_predicate(name, desc, func["predicate"], shell)
    else:
        return _generate_complex(name, desc, func, shell)


def _generate_predicate(name: str, desc: str, predicate: str,
                        shell: str) -> str:
    idx = SHELL_INDEX[shell]
    body = PREDICATES[predicate][idx]
    lines = [HEADER]

    if shell == "fish":
        lines.append(f"# {desc}")
        lines.append(f"function {name} --description '{desc}'")
        lines.append(f"    {body}")
        lines.append("end")
    elif shell == "bash":
        lines.append(f"# {desc}")
        lines.append(f"{name}() {{")
        lines.append(f"    {body}")
        lines.append("}")
    elif shell == "pwsh":
        lines.append(f"# {desc}")
        lines.append(f"function {name} {{")
        lines.append(f"    {body}")
        lines.append("}")
    else:  # zsh — autoload, no wrapper
        lines.append("")
        lines.append(body)

    return "\n".join(lines) + "\n"


def _generate_complex(name: str, desc: str, func: Dict, shell: str) -> str:
    lines = [HEADER]

    if "usage" in func:
        lines.append(f"# {desc}")
        lines.append(f"# Usage: {func['usage']}")
        lines.append(f"# Returns the exit code of the command")
    else:
        lines.append(f"# {desc}")
    lines.append("")

    # Resolve body text: prefer shell-specific, fall back to shared
    body_section = func["body"]
    if shell in body_section:
        body_text = body_section[shell].rstrip("\n")
    elif "shared" in body_section:
        body_text = body_section["shared"].rstrip("\n")
    else:
        body_text = ""

    if shell == "fish":
        lines.append(f"function {name}")
        for line in body_text.split("\n"):
            lines.append(f"    {line}" if line.strip() else "")
        lines.append("end")
    elif shell == "bash":
        lines.append(f"{name}() {{")
        for line in body_text.split("\n"):
            lines.append(f"    {line}" if line.strip() else "")
        lines.append("}")
    elif shell == "pwsh":
        lines.append(f"function {name} {{")
        for line in body_text.split("\n"):
            lines.append(f"    {line}" if line.strip() else "")
        lines.append("}")
    else:  # zsh — autoload, bare body
        lines.append(body_text)

    return "\n".join(lines) + "\n"


# ---------------------------------------------------------------------------
# Module generator
# ---------------------------------------------------------------------------

def generate_module(mod: Dict, shell: str) -> str:
    """Generate a module file for the given shell."""
    desc = mod["description"]
    url = mod.get("url", "")
    comment = mod.get("comment", "")
    guards = _collect_guards(mod)

    lines = [HEADER, f"# {desc}"]
    if url:
        lines.append(f"# {url}")
    if comment:
        lines.append(f"# {comment}")
    lines.append("")

    # Guards
    for guard in guards:
        lines.append(translate_guard(guard, shell))
    if guards:
        lines.append("")

    # Body — render all body constructs
    body_lines = _render_body_lines(mod, shell)
    lines.extend(body_lines)

    # Conditional (rendered separately because it's a multi-line block)
    if "conditional" in mod:
        lines.append(_render_conditional(mod["conditional"], shell))

    return "\n".join(lines) + "\n"


# ---------------------------------------------------------------------------
# Manifest loading and merging
# ---------------------------------------------------------------------------

def load_manifest(path: Path) -> Dict:
    """Load and validate a single YAML manifest file."""
    with open(path) as f:
        manifest = yaml.safe_load(f) or {}
    return manifest


def merge_manifests(base: Dict, extra: Dict) -> Dict:
    """Merge an extra manifest into a base manifest.

    Uses last-wins dedup by name: if two sources define a function or module
    with the same name, the later one replaces the earlier.
    """
    merged = dict(base)
    for key in ("functions", "modules"):
        seen: Dict[str, Dict] = {}
        for item in list(base.get(key, [])) + list(extra.get(key, [])):
            seen[item["name"]] = item
        merged[key] = list(seen.values())
    return merged


def resolve_sources(paths: List[str], quiet: bool = False) -> List[Path]:
    """Resolve a list of path strings to YAML file paths.

    Each path is resolved as:
    - File -> load directly
    - Directory -> load shell.yaml inside it (error if not found)
    - Nonexistent -> skip with warning
    """
    resolved = []
    for p in paths:
        path = Path(p).expanduser()
        if path.is_file():
            resolved.append(path)
        elif path.is_dir():
            yaml_path = path / "shell.yaml"
            if yaml_path.is_file():
                resolved.append(yaml_path)
            else:
                if not quiet:
                    warnings.warn(f"No shell.yaml found in directory: {path}")
        else:
            if not quiet:
                warnings.warn(f"Source path does not exist, skipping: {path}")
    return resolved


# ---------------------------------------------------------------------------
# Output directory mapping
# ---------------------------------------------------------------------------

def get_output_dirs(target: Optional[Path], repo_root: Path) -> Dict[str, Dict[str, Path]]:
    """Return output directories keyed by shell and type.

    Returns a dict like:
        {
            "fish":  {"functions": Path(...), "modules": Path(...)},
            "zsh":   {"functions": Path(...), "modules": Path(...)},
            "bash":  {"functions": Path(...), "modules": Path(...)},
            "pwsh":  {"functions": Path(...), "modules": Path(...)},
        }

    When target is None, returns chezmoi source-dir paths (dot_ prefixed).
    When target is set, returns real config paths under target.
    """
    if target is None:
        return {
            "fish": {
                "functions": repo_root / "dot_config" / "fish" / "functions",
                "modules":   repo_root / "dot_config" / "fish" / "conf.d",
            },
            "zsh": {
                "functions": repo_root / "dot_config" / "zsh" / "dot_zfunctions",
                "modules":   repo_root / "dot_config" / "zsh" / "dot_zshrc.d",
            },
            "bash": {
                "functions": repo_root / "dot_config" / "bash" / "functions",
                "modules":   repo_root / "dot_config" / "bash" / "bashrc.d",
            },
            "pwsh": {
                "functions": repo_root / "dot_config" / "powershell" / "functions",
                "modules":   repo_root / "dot_config" / "powershell" / "conf.d",
            },
        }
    else:
        return {
            "fish": {
                "functions": target / "fish" / "functions",
                "modules":   target / "fish" / "conf.d",
            },
            "zsh": {
                "functions": target / "zsh" / ".zfunctions",
                "modules":   target / "zsh" / ".zshrc.d",
            },
            "bash": {
                "functions": target / "bash" / "functions",
                "modules":   target / "bash" / "bashrc.d",
            },
            "pwsh": {
                "functions": target / "powershell" / "functions",
                "modules":   target / "powershell" / "conf.d",
            },
        }


# ---------------------------------------------------------------------------
# File generation
# ---------------------------------------------------------------------------

def _write_gitignore(directory: Path, filenames: List[str]):
    """Write a .gitignore in directory listing the generated filenames."""
    lines = ["# Generated by generate_shell.py -- DO NOT EDIT"]
    lines.extend(sorted(filenames))
    (directory / ".gitignore").write_text("\n".join(lines) + "\n")


def generate_all(manifest: Dict, target: Optional[Path],
                 repo_root: Path, quiet: bool = False) -> List[Path]:
    """Generate all shell config files and return list of written paths."""
    dirs = get_output_dirs(target, repo_root)

    # Ensure all output directories exist
    for shell_dirs in dirs.values():
        for d in shell_dirs.values():
            d.mkdir(parents=True, exist_ok=True)

    generated_files: List[Path] = []
    # Track filenames per directory for .gitignore
    dir_files: Dict[Path, List[str]] = {}
    for shell_dirs in dirs.values():
        for d in shell_dirs.values():
            dir_files[d] = []

    # --- Functions ---
    for func in manifest.get("functions", []):
        name = func["name"]
        for shell in SHELLS:
            func_ext = SHELL_FUNC_EXT[shell]
            func_dir = dirs[shell]["functions"]
            filename = f"{name}{func_ext}"
            func_path = func_dir / filename

            func_path.write_text(generate_function(func, shell))
            generated_files.append(func_path)
            dir_files[func_dir].append(filename)
            if not quiet:
                print(f"  {func_path}")

    # --- Modules ---
    for mod in manifest.get("modules", []):
        name = mod["name"]
        prefix = mod["prefix"]
        for shell in SHELLS:
            mod_ext = SHELL_MODULE_EXT[shell]
            mod_dir = dirs[shell]["modules"]
            filename = f"{prefix}-{name}{mod_ext}"
            mod_path = mod_dir / filename

            mod_path.write_text(generate_module(mod, shell))
            generated_files.append(mod_path)
            dir_files[mod_dir].append(filename)
            if not quiet:
                print(f"  {mod_path}")

    # Write per-directory .gitignore files
    for d, names in dir_files.items():
        if names:
            _write_gitignore(d, names)

    return generated_files


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main():
    parser = argparse.ArgumentParser(
        description="Transpile shell.yaml into Fish, Zsh, Bash, and "
                    "PowerShell config files")
    parser.add_argument(
        "sources", nargs="*",
        help="YAML files or directories (dir -> dir/shell.yaml). "
             "If omitted, defaults to script_dir/shell.yaml.")
    parser.add_argument(
        "--target", type=Path, default=None,
        help="Write to real config paths under DIR (e.g. ~/.config). "
             "Without this flag, writes to chezmoi source dir.")
    parser.add_argument(
        "--quiet", action="store_true",
        help="Suppress non-error output.")
    args = parser.parse_args()

    script_dir = Path(__file__).parent
    repo_root = script_dir.parent

    # Collect sources: stdin lines first, then positional args
    raw_sources: List[str] = []
    if not sys.stdin.isatty():
        for line in sys.stdin:
            line = line.strip()
            if line:
                raw_sources.append(line)
    raw_sources.extend(args.sources)

    # Default to script_dir/shell.yaml if no sources given
    if not raw_sources:
        raw_sources = [str(script_dir / "shell.yaml")]

    source_files = resolve_sources(raw_sources, quiet=args.quiet)
    if not source_files:
        print("Error: no valid source files found")
        return 1

    # Load and merge left-to-right (last wins)
    manifest: Dict = {"functions": [], "modules": []}
    for source_file in source_files:
        extra = load_manifest(source_file)
        manifest = merge_manifests(manifest, extra)

    # Validate merged manifest
    errors = validate_manifest(manifest)
    if errors:
        print("Validation errors:")
        for err in errors:
            print(f"  - {err}")
        return 1

    generated_files = generate_all(manifest, args.target, repo_root,
                                   quiet=args.quiet)
    if not args.quiet:
        print(f"\nGenerated {len(generated_files)} shell config files "
              f"for {len(SHELLS)} shells.")
    return 0


if __name__ == "__main__":
    exit(main())
