# Shell Configuration System

Cross-shell configuration generator that produces Fish and Zsh files from a single YAML manifest.

## How It Works

```
shell.yaml  ──┐
               ├──  generate_shell.py  ──►  Fish + Zsh config files
shell.d/*.yaml ┘
```

The generator accepts positional args (files or directories) with last-wins merge semantics. A directory resolves to `dir/shell.yaml`; nonexistent paths are skipped with a warning.

```bash
# No args — default to script_dir/shell.yaml
python3 generate_shell.py

# Positional: files or directories
python3 generate_shell.py shell.yaml ~/.config/shell.d/work.yaml

# Pipe paths from stdin (one per line)
find ~/.config/shell.d -name 'shell.yaml' | python3 generate_shell.py

# Mixed: positional + stdin + --target
echo ~/.config/shell.d/work.yaml | python3 generate_shell.py shell.yaml --target ~/.config
```

**`chezmoi apply`** runs `run_after_generate_shell.sh` which calls the generator with `--target ~/.config`, passing the main manifest and extras directory as positional args. Generated files are **not** committed to git.

## Schema Reference

### Functions

Predicate (one-liner OS check):
```yaml
functions:
  - name: is-darwin
    description: Check if running on macOS
    predicate: os_is_darwin    # or os_is_linux
```

Complex (shell-specific bodies):
```yaml
  - name: my_func
    description: Does something
    usage: "my_func <arg>"     # optional
    body:
      fish: |
        echo hello from fish
      zsh: |
        echo hello from zsh
```

### Modules

PATH additions:
```yaml
modules:
  - name: path
    prefix: "00"
    description: PATH additions
    paths:
      - "$HOME/.local/bin"
```

Aliases:
```yaml
  - name: eza
    prefix: "40"
    description: Modern ls replacement
    guard: { command_exists: eza }
    aliases:
      ls: "eza"
      ll: "eza -l"
```

Tool init (`tool init shell | source`):
```yaml
  - name: zoxide
    prefix: "50"
    description: Zoxide
    guard: { command_exists: zoxide }
    tool: zoxide
```

Custom body:
```yaml
  - name: tmux
    prefix: "70"
    description: Tmux auto-attach
    guards:
      - { command_exists: tmux }
      - is_interactive
    body:
      shared: |
        tmux attach 2>/dev/null || tmux new-session
```

Shell-specific body (use `fish:`/`zsh:` keys instead of `shared:`).

### Guards

| Guard | Fish | Zsh |
|-------|------|-----|
| `{ command_exists: cmd }` | `command -q cmd; or return 0` | `(( $+commands[cmd] )) \|\| return 0` |
| `{ env_not_set: VAR }` | `not set -q VAR; or return 0` | `[[ -z $VAR ]] \|\| return 0` |
| `{ env_equals: { var: V, value: X } }` | `test "$V" = "X"; or return 0` | `[[ "$V" == "X" ]] \|\| return 0` |
| `{ not_env_equals: { var: V, value: X } }` | `test "$V" != "X"; or return 0` | `[[ "$V" != "X" ]] \|\| return 0` |
| `is_tty` | `isatty stdin; or return 0` | `[[ -t 0 ]] \|\| return 0` |
| `is_interactive` | `status is-interactive; or return 0` | `[[ -o interactive ]] \|\| return 0` |

Use singular `guard:` for one guard, `guards:` (list) for multiple.

### Prefix Convention

Prefix determines load order: `00` (early/PATH), `40` (aliases), `50` (tool init), `70` (late/interactive).

## Per-Machine Customization

Create YAML files in `~/.config/shell.d/` to add machine-specific functions or modules:

```yaml
# ~/.config/shell.d/work.yaml
modules:
  - name: work-path
    prefix: "01"
    description: Work-specific PATH additions
    paths:
      - "/opt/company/bin"
      - "$HOME/work/scripts"

functions:
  - name: deploy
    description: Deploy to staging
    body:
      fish: |
        ssh staging "cd /app && git pull && make deploy"
      zsh: |
        ssh staging "cd /app && git pull && make deploy"
```

Files are merged in the order given. If two sources define a function or module with the same name, the later one wins.

## Development

```bash
# Edit the manifest
vim .shellgen/shell.yaml

# Test (generates to temp dir, validates output)
cd .shellgen && make test

# Generate to source dir (for local testing only)
cd .shellgen && make generate

# Generate to ~/.config (what chezmoi apply does)
cd .shellgen && make generate-target
```
