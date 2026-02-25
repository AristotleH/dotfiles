#!/usr/bin/env python3
"""
Generate Fish and Zsh configuration files from shell.yaml

Run this script from the chezmoi source directory to regenerate
all shell configuration files that have cross-shell equivalents.

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
from typing import Any, Dict, List


HEADER = "# Generated from .shellgen/shell.yaml -- DO NOT EDIT"

# ---------------------------------------------------------------------------
# Data tables — add a new guard or predicate by adding one line
# ---------------------------------------------------------------------------

# Each entry: guard_name -> (fish_template, zsh_template)
# Templates use {0} for simple value, {var}/{value} for dict values.
GUARDS = {
    "command_exists":  ("command -q {0}; or return 0",
                        "(( $+commands[{0}] )) || return 0"),
    "env_not_set":     ("not set -q {0}; or return 0",
                        "[[ -z ${0} ]] || return 0"),
    "env_equals":      ('test "${var}" = "{value}"; or return 0',
                        '[[ "${var}" == "{value}" ]] || return 0'),
    "not_env_equals":  ('test "${var}" != "{value}"; or return 0',
                        '[[ "${var}" != "{value}" ]] || return 0'),
    "is_tty":          ("isatty stdin; or return 0",
                        "[[ -t 0 ]] || return 0"),
    "is_interactive":  ("status is-interactive; or return 0",
                        "[[ -o interactive ]] || return 0"),
}

# Each entry: predicate_name -> (fish_body, zsh_body)
PREDICATES = {
    "os_is_darwin": ('test (uname) = "Darwin"',
                     "[[ $OSTYPE == *darwin* ]]"),
    "os_is_linux":  ('test (uname) = "Linux"',
                     "[[ $OSTYPE == *linux* ]]"),
}


# ---------------------------------------------------------------------------
# Validation
# ---------------------------------------------------------------------------

def validate_manifest(manifest: Dict) -> List[str]:
    """Validate the manifest and return a list of error messages (empty = OK)."""
    errors = []

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
        body_keys = {"paths", "aliases", "tool", "body"}
        if not any(k in mod for k in body_keys):
            errors.append(
                f"{ctx}: must have at least one of: "
                f"{', '.join(sorted(body_keys))}"
            )

        # Validate guards
        for guard in _collect_guards(mod):
            _validate_guard(guard, ctx, errors)

    return errors


def _validate_guard(guard: Any, ctx: str, errors: List[str]):
    """Validate a single guard entry."""
    if isinstance(guard, str):
        if guard not in GUARDS:
            errors.append(
                f"{ctx}: unknown string guard '{guard}' "
                f"(known: {', '.join(sorted(GUARDS))})"
            )
    elif isinstance(guard, dict):
        key = next(iter(guard), None)
        if key not in GUARDS:
            errors.append(
                f"{ctx}: unknown guard type '{key}' "
                f"(known: {', '.join(sorted(GUARDS))})"
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
    """Convert a declarative guard to a shell-specific condition line."""
    idx = 0 if shell == "fish" else 1

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


# ---------------------------------------------------------------------------
# Function generator (unified)
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
    idx = 0 if shell == "fish" else 1
    body = PREDICATES[predicate][idx]
    lines = [HEADER]

    if shell == "fish":
        lines.append(f"# {desc}")
        lines.append(f"function {name} --description '{desc}'")
        lines.append(f"    {body}")
        lines.append("end")
    else:
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

    body_text = func["body"][shell].rstrip("\n")

    if shell == "fish":
        lines.append(f"function {name}")
        for line in body_text.split("\n"):
            lines.append(f"    {line}" if line.strip() else "")
        lines.append("end")
    else:
        lines.append(body_text)

    return "\n".join(lines) + "\n"


# ---------------------------------------------------------------------------
# Module generator (unified)
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

    # Body — infer type from which keys are present
    if "paths" in mod:
        for p in mod["paths"]:
            if shell == "fish":
                lines.append(f"fish_add_path {p}")
            else:
                lines.append(f'export PATH="{p}:$PATH"')
    elif "aliases" in mod:
        for alias_name, alias_cmd in mod["aliases"].items():
            if shell == "fish":
                lines.append(f"alias {alias_name}='{alias_cmd}'")
            else:
                lines.append(f'alias {alias_name}="{alias_cmd}"')
    elif "tool" in mod:
        tool = mod["tool"]
        if shell == "fish":
            lines.append(f"{tool} init fish | source")
        else:
            lines.append(f'eval "$({tool} init zsh)"')
    elif "body" in mod:
        body_section = mod["body"]
        if shell in body_section:
            body = body_section[shell].rstrip("\n")
        else:
            body = body_section["shared"].rstrip("\n")
        lines.append(body)

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


def resolve_sources(paths: List[str]) -> List[Path]:
    """Resolve a list of path strings to YAML file paths.

    Each path is resolved as:
    - File → load directly
    - Directory → load shell.yaml inside it (error if not found)
    - Nonexistent → skip with warning
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
                warnings.warn(f"No shell.yaml found in directory: {path}")
        else:
            warnings.warn(f"Source path does not exist, skipping: {path}")
    return resolved


# ---------------------------------------------------------------------------
# Output directory mapping
# ---------------------------------------------------------------------------

def get_output_dirs(target: Path | None, repo_root: Path) -> tuple:
    """Return (fish_func, zsh_func, fish_confd, zsh_confd) directories.

    When target is None, returns chezmoi source-dir paths (dot_ prefixed).
    When target is set, returns real config paths under target.
    """
    if target is None:
        return (
            repo_root / "dot_config" / "fish" / "functions",
            repo_root / "dot_config" / "zsh" / "dot_zfunctions",
            repo_root / "dot_config" / "fish" / "conf.d",
            repo_root / "dot_config" / "zsh" / "dot_zshrc.d",
        )
    else:
        return (
            target / "fish" / "functions",
            target / "zsh" / ".zfunctions",
            target / "fish" / "conf.d",
            target / "zsh" / ".zshrc.d",
        )


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def _write_gitignore(directory: Path, filenames: List[str]):
    """Write a .gitignore in directory listing the generated filenames."""
    lines = ["# Generated by generate_shell.py -- DO NOT EDIT"]
    lines.extend(sorted(filenames))
    (directory / ".gitignore").write_text("\n".join(lines) + "\n")


def generate_all(manifest: Dict, target: Path | None, repo_root: Path) -> List[Path]:
    """Generate all shell config files and return list of written paths."""
    fish_func_dir, zsh_func_dir, fish_confd_dir, zsh_confd_dir = \
        get_output_dirs(target, repo_root)

    # Ensure output directories exist
    for d in (fish_func_dir, zsh_func_dir, fish_confd_dir, zsh_confd_dir):
        d.mkdir(parents=True, exist_ok=True)

    generated_files = []
    # Track filenames per directory for .gitignore
    dir_files: Dict[Path, List[str]] = {
        fish_func_dir: [], zsh_func_dir: [],
        fish_confd_dir: [], zsh_confd_dir: [],
    }

    # --- Functions ---
    for func in manifest.get("functions", []):
        name = func["name"]

        fish_path = fish_func_dir / f"{name}.fish"
        fish_path.write_text(generate_function(func, "fish"))
        generated_files.append(fish_path)
        dir_files[fish_func_dir].append(f"{name}.fish")
        print(f"  {fish_path}")

        zsh_path = zsh_func_dir / name
        zsh_path.write_text(generate_function(func, "zsh"))
        generated_files.append(zsh_path)
        dir_files[zsh_func_dir].append(name)
        print(f"  {zsh_path}")

    # --- Modules ---
    for mod in manifest.get("modules", []):
        name = mod["name"]
        prefix = mod["prefix"]

        fish_path = fish_confd_dir / f"{prefix}-{name}.fish"
        fish_path.write_text(generate_module(mod, "fish"))
        generated_files.append(fish_path)
        dir_files[fish_confd_dir].append(f"{prefix}-{name}.fish")
        print(f"  {fish_path}")

        zsh_path = zsh_confd_dir / f"{prefix}-{name}.zsh"
        zsh_path.write_text(generate_module(mod, "zsh"))
        generated_files.append(zsh_path)
        dir_files[zsh_confd_dir].append(f"{prefix}-{name}.zsh")
        print(f"  {zsh_path}")

    # Write per-directory .gitignore files
    for d, names in dir_files.items():
        if names:
            _write_gitignore(d, names)

    return generated_files


def main():
    parser = argparse.ArgumentParser(
        description="Generate Fish and Zsh config files from shell.yaml")
    parser.add_argument(
        "sources", nargs="*",
        help="YAML files or directories (dir → dir/shell.yaml). "
             "If omitted, defaults to script_dir/shell.yaml.")
    parser.add_argument(
        "--target", type=Path, default=None,
        help="Write to real config paths under DIR (e.g. ~/.config). "
             "Without this flag, writes to chezmoi source dir.")
    args = parser.parse_args()

    script_dir = Path(__file__).parent
    repo_root = script_dir.parent

    # Collect sources: stdin lines first, then positional args
    raw_sources = []
    if not sys.stdin.isatty():
        for line in sys.stdin:
            line = line.strip()
            if line:
                raw_sources.append(line)
    raw_sources.extend(args.sources)

    # Default to script_dir/shell.yaml if no sources given
    if not raw_sources:
        raw_sources = [str(script_dir / "shell.yaml")]

    source_files = resolve_sources(raw_sources)
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

    generated_files = generate_all(manifest, args.target, repo_root)
    print(f"\nGenerated {len(generated_files)} shell config files.")
    return 0


if __name__ == "__main__":
    exit(main())
