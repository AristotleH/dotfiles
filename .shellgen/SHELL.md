# Shell Configuration Transpiler

A YAML-to-shell transpiler that generates idiomatic configuration files for **Fish**, **Zsh**, **Bash**, and **PowerShell** from a single declarative manifest.

## Architecture

```
                          ┌──► Fish    (conf.d/*.fish, functions/*.fish)
shell.yaml  ──┐           │
               ├─ generate_shell.py ──┼──► Zsh     (.zshrc.d/*.zsh, .zfunctions/*)
shell.d/*.yaml ┘           │
                          ├──► Bash    (bashrc.d/*.bash, functions/*.bash)
                          │
                          └──► PowerShell (conf.d/*.ps1, functions/*.ps1)
```

### Platform Matrix

| Shell | macOS | Linux | Windows | Shell name in code |
|-------|-------|-------|---------|--------------------|
| Fish  | ✓     | ✓     |         | `fish`             |
| Zsh   | ✓     | ✓     |         | `zsh`              |
| Bash  | ✓     | ✓     | ✓ (Git Bash) | `bash`        |
| PowerShell | |       | ✓       | `pwsh`             |

### Output Layout

| Shell | Functions | Modules |
|-------|-----------|---------|
| Fish  | `~/.config/fish/functions/{name}.fish` | `~/.config/fish/conf.d/{prefix}-{name}.fish` |
| Zsh   | `~/.config/zsh/.zfunctions/{name}` (no ext) | `~/.config/zsh/.zshrc.d/{prefix}-{name}.zsh` |
| Bash  | `~/.config/bash/functions/{name}.bash` | `~/.config/bash/bashrc.d/{prefix}-{name}.bash` |
| PowerShell | `~/.config/powershell/functions/{name}.ps1` | `~/.config/powershell/conf.d/{prefix}-{name}.ps1` |

In the chezmoi source tree, dotfiles use `dot_` prefix convention (e.g., `dot_config/zsh/dot_zshrc.d/`).

## Usage

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

**`chezmoi apply`** runs `run_after_generate_shell.sh` which calls the generator with `--target ~/.config`, passing the main manifest and extras directory as positional args.

---

## Transpilation Source Language

The source language is a YAML document with two top-level keys: `functions` and `modules`. Each entry is a declarative specification that the transpiler converts into idiomatic syntax for all four target shells.

### Functions

Functions produce one file per shell. Two types:

#### Predicate Functions

One-liner check functions using built-in predicate expressions.

```yaml
functions:
  - name: is-darwin
    description: Check if running on macOS
    predicate: os_is_darwin    # see Predicate Reference below
```

**Translation:**

| Shell | Output |
|-------|--------|
| Fish  | `function is-darwin --description '...' ↵ test (uname) = "Darwin" ↵ end` |
| Zsh   | `[[ $OSTYPE == *darwin* ]]` (bare body, autoload) |
| Bash  | `is-darwin() { ↵ [[ $OSTYPE == darwin* ]] ↵ }` |
| PowerShell | `function is-darwin { ↵ $IsMacOS ↵ }` |

#### Complex Functions

Functions with shell-specific or shared bodies.

```yaml
  - name: my_func
    description: Does something
    usage: "my_func <arg>"     # optional, added as comment
    body:
      fish: |
        echo hello from fish
      posix: |               # fallback used by zsh + bash
        echo hello from POSIX shells
      pwsh: |
        Write-Output "hello from pwsh"
      # Or use 'shared:' as a fallback for any missing shell key
    # Or use string shorthand:
    # body: "echo hello from every shell"
```

**Key precedence:** shell-specific key (`fish:`, `zsh:`, `bash:`, `pwsh:`) > `posix:` (for zsh/bash) > `shared:` fallback.

**Translation wrapping:**

| Shell | Wrapper |
|-------|---------|
| Fish  | `function name ↵ {body indented 4 spaces} ↵ end` |
| Zsh   | `{bare body, no wrapper}` (autoload pattern) |
| Bash  | `name() { ↵ {body indented 4 spaces} ↵ }` |
| PowerShell | `function name { ↵ {body indented 4 spaces} ↵ }` |

### Modules

Modules produce one file per shell. Each has a `prefix` (two-digit string) that determines load order and a body type.

Required fields: `name`, `prefix`, `description`.
Optional fields: `url`, `comment`, `guard`/`guards`.

#### Body Types

A module must have **at least one** of the following body types. Multiple can be combined in a single module.

##### `paths` — PATH Additions

```yaml
- name: path
  prefix: "00"
  description: PATH additions
  paths:
    - "$HOME/.local/bin"
```

| Shell | Output |
|-------|--------|
| Fish  | `fish_add_path "$HOME/.local/bin"` |
| Zsh   | `export PATH="$HOME/.local/bin:$PATH"` |
| Bash  | `export PATH="$HOME/.local/bin:$PATH"` |
| PowerShell | `$env:PATH = "$HOME/.local/bin" + [IO.Path]::PathSeparator + $env:PATH` |

##### `aliases` — Alias Definitions

```yaml
- name: eza
  prefix: "40"
  description: Modern ls replacement
  guard: { command_exists: eza }
  aliases:
    ls: "eza"
    ll: "eza -l"
```

| Shell | Output |
|-------|--------|
| Fish  | `alias ls='eza'` (single quotes) |
| Zsh   | `alias ls="eza"` (double quotes) |
| Bash  | `alias ls="eza"` (double quotes) |
| PowerShell | `function ls { eza @args }` (function form, since `Set-Alias` can't handle arguments) |

##### `env` — Environment Variable Exports

```yaml
- name: editor
  prefix: "05"
  description: Default editor
  env:
    EDITOR: vim
    VISUAL: vim
```

| Shell | Output |
|-------|--------|
| Fish  | `set -gx EDITOR "vim"` |
| Zsh   | `export EDITOR="vim"` |
| Bash  | `export EDITOR="vim"` |
| PowerShell | `$env:EDITOR = "vim"` |

##### `tool` — Tool Init Pattern

For tools that follow the `tool init <shell> | source` convention.

```yaml
- name: zoxide
  prefix: "50"
  description: Zoxide
  guard: { command_exists: zoxide }
  tool: zoxide
```

| Shell | Output |
|-------|--------|
| Fish  | `zoxide init fish \| source` |
| Zsh   | `eval "$(zoxide init zsh)"` |
| Bash  | `eval "$(zoxide init bash)"` |
| PowerShell | `(& zoxide init pwsh) \| Invoke-Expression` |

##### `eval_command` — Evaluate Command Output

For arbitrary commands whose output should be sourced. Supports `{shell}` placeholder.

```yaml
- name: brew-env
  prefix: "10"
  description: Homebrew environment
  eval_command: /opt/homebrew/bin/brew shellenv
```

| Shell | Output |
|-------|--------|
| Fish  | `{command} \| source` |
| Zsh   | `eval "$({command})"` |
| Bash  | `eval "$({command})"` |
| PowerShell | `(& {command}) \| Invoke-Expression` |

With `{shell}` placeholder (e.g., `mise activate {shell}`), the placeholder is replaced with `fish`, `zsh`, `bash`, or `pwsh`.

##### `source_file` — Source Another File

String or list of strings. Files are sourced with a file-existence check (safe if missing).

```yaml
- name: local
  prefix: "99"
  description: Local overrides
  source_file: "$HOME/.shellrc.local"
  # or a list:
  # source_file:
  #   - "$HOME/.shellrc.local"
  #   - "$HOME/.shellrc.work"
```

| Shell | Output |
|-------|--------|
| Fish  | `test -f "path"; and source "path"` |
| Zsh   | `[[ -f "path" ]] && source "path"` |
| Bash  | `[[ -f "path" ]] && source "path"` |
| PowerShell | `if (Test-Path "path") { . "path" }` |

##### `conditional` — If/Elif/Else Blocks

A list of branches using guards as conditions. First branch must have `if:`, subsequent use `elif:` or `else:`. Each branch contains one or more body constructs.

```yaml
- name: editor-setup
  prefix: "05"
  description: Editor configuration
  conditional:
    - if: { command_exists: nvim }
      env: { EDITOR: nvim, VISUAL: nvim }
    - elif: { command_exists: vim }
      env: { EDITOR: vim, VISUAL: vim }
    - else:
      env: { EDITOR: vi, VISUAL: vi }
```

Translation uses the **condition** form of guards (not the bail form):

**Fish:**
```fish
if command -q nvim
    set -gx EDITOR "nvim"
    set -gx VISUAL "nvim"
else if command -q vim
    set -gx EDITOR "vim"
    set -gx VISUAL "vim"
else
    set -gx EDITOR "vi"
    set -gx VISUAL "vi"
end
```

**Bash/Zsh:**
```bash
if command -v nvim &>/dev/null; then
    export EDITOR="nvim"
elif command -v vim &>/dev/null; then
    export EDITOR="vim"
else
    export EDITOR="vi"
fi
```

**PowerShell:**
```powershell
if (Get-Command 'nvim' -EA SilentlyContinue) {
    $env:EDITOR = "nvim"
} elseif (Get-Command 'vim' -EA SilentlyContinue) {
    $env:EDITOR = "vim"
} else {
    $env:EDITOR = "vi"
}
```

Branches can contain any body type: `env`, `aliases`, `paths`, `tool`, `source_file`, `eval_command`, `body`.

##### `body` — Custom Shell Code

Raw shell code with shell-specific or shared variants.

```yaml
- name: tmux
  prefix: "70"
  description: Tmux auto-attach
  body:
    shared: |
      tmux attach 2>/dev/null || tmux new-session
    # or per-shell:
    # fish: |
    #   ...
    # pwsh: |
    #   ...
```

Key precedence: shell-specific key > `posix:` (zsh/bash) > `shared:` fallback.

---

## Guard Reference

Guards are conditional checks that control execution. They appear in two forms:

1. **Bail form** — used in module preambles: "if condition is NOT met, `return 0` (skip this file)"
2. **Condition form** — used in `conditional` branches: expression that evaluates to truthy when condition IS met

### Syntax

```yaml
# Single guard (dict key)
guard: { command_exists: eza }

# Multiple guards (list)
guards:
  - { command_exists: tmux }
  - is_tty
  - { env_not_set: TMUX }

# Negated guard
guard: { not: { command_exists: nvim } }

# Composed guards
guard:
  all:
    - { command_exists: git }
    - { any: [{ command_exists: brew }, { command_exists: apt-get }] }
```

### Guard Types — Bail Form

| Guard | Fish | Zsh | Bash | PowerShell |
|-------|------|-----|------|------------|
| `{ command_exists: cmd }` | `command -q cmd; or return 0` | `(( $+commands[cmd] )) \|\| return 0` | `command -v cmd &>/dev/null \|\| return 0` | `if (-not (Get-Command 'cmd' -EA SilentlyContinue)) { return }` |
| `{ env_not_set: VAR }` | `not set -q VAR; or return 0` | `[[ -z $VAR ]] \|\| return 0` | `[[ -z "$VAR" ]] \|\| return 0` | `if ($env:VAR) { return }` |
| `{ env_set: VAR }` | `set -q VAR; or return 0` | `[[ -n $VAR ]] \|\| return 0` | `[[ -n "$VAR" ]] \|\| return 0` | `if (-not $env:VAR) { return }` |
| `{ env_equals: { var: V, value: X } }` | `test "$V" = "X"; or return 0` | `[[ "$V" == "X" ]] \|\| return 0` | `[[ "$V" == "X" ]] \|\| return 0` | `if ($env:V -ne 'X') { return }` |
| `{ not_env_equals: { var: V, value: X } }` | `test "$V" != "X"; or return 0` | `[[ "$V" != "X" ]] \|\| return 0` | `[[ "$V" != "X" ]] \|\| return 0` | `if ($env:V -eq 'X') { return }` |
| `{ file_exists: path }` | `test -f path; or return 0` | `[[ -f path ]] \|\| return 0` | `[[ -f path ]] \|\| return 0` | `if (-not (Test-Path 'path' -PathType Leaf)) { return }` |
| `{ dir_exists: path }` | `test -d path; or return 0` | `[[ -d path ]] \|\| return 0` | `[[ -d path ]] \|\| return 0` | `if (-not (Test-Path 'path' -PathType Container)) { return }` |
| `is_tty` | `isatty stdin; or return 0` | `[[ -t 0 ]] \|\| return 0` | `[[ -t 0 ]] \|\| return 0` | `if (-not [Environment]::UserInteractive) { return }` |
| `is_interactive` | `status is-interactive; or return 0` | `[[ -o interactive ]] \|\| return 0` | `[[ $- == *i* ]] \|\| return 0` | `if (-not [Environment]::UserInteractive) { return }` |

### Guard Types — Condition Form (for `conditional`)

| Guard | Fish | Zsh | Bash | PowerShell |
|-------|------|-----|------|------------|
| `{ command_exists: cmd }` | `command -q cmd` | `(( $+commands[cmd] ))` | `command -v cmd &>/dev/null` | `(Get-Command 'cmd' -EA SilentlyContinue)` |
| `{ env_not_set: VAR }` | `not set -q VAR` | `[[ -z $VAR ]]` | `[[ -z "$VAR" ]]` | `(-not $env:VAR)` |
| `{ env_set: VAR }` | `set -q VAR` | `[[ -n $VAR ]]` | `[[ -n "$VAR" ]]` | `($env:VAR)` |
| `{ env_equals: { var: V, value: X } }` | `test "$V" = "X"` | `[[ "$V" == "X" ]]` | `[[ "$V" == "X" ]]` | `($env:V -eq 'X')` |
| `{ file_exists: path }` | `test -f path` | `[[ -f path ]]` | `[[ -f path ]]` | `(Test-Path 'path' -PathType Leaf)` |
| `{ dir_exists: path }` | `test -d path` | `[[ -d path ]]` | `[[ -d path ]]` | `(Test-Path 'path' -PathType Container)` |
| `is_tty` | `isatty stdin` | `[[ -t 0 ]]` | `[[ -t 0 ]]` | `[Environment]::UserInteractive` |
| `is_interactive` | `status is-interactive` | `[[ -o interactive ]]` | `[[ $- == *i* ]]` | `[Environment]::UserInteractive` |

### `not` Meta-Guard

Wraps any guard to negate it:

```yaml
guard: { not: { command_exists: nvim } }
```

**Bail form:** if condition IS met, bail (reversed logic).
**Condition form:** `not <condition>` (Fish), `! <condition>` (Bash/Zsh), `(-not <condition>)` (PowerShell).

### `all` and `any` Meta-Guards

Compose guards for nested boolean logic:

```yaml
guard:
  all:
    - { env_set: HOME }
    - { any: [{ command_exists: git }, { command_exists: hg }] }
```

- `all`: logical AND of nested guards
- `any`: logical OR of nested guards

---

## Predicate Reference

Predicates are used in predicate functions to generate one-liner body expressions.

| Predicate | Fish | Zsh | Bash | PowerShell |
|-----------|------|-----|------|------------|
| `os_is_darwin` | `test (uname) = "Darwin"` | `[[ $OSTYPE == *darwin* ]]` | `[[ $OSTYPE == darwin* ]]` | `$IsMacOS` |
| `os_is_linux` | `test (uname) = "Linux"` | `[[ $OSTYPE == *linux* ]]` | `[[ $OSTYPE == linux* ]]` | `$IsLinux` |
| `os_is_windows` | `string match -q "Msys" (uname -o ...)` | `[[ $OSTYPE == msys* ]]` | `[[ $OSTYPE == msys* ]]` | `$IsWindows` |
| `arch_is_arm64` | `test (uname -m) = arm64; or ... aarch64` | `[[ $(uname -m) == (arm64\|aarch64) ]]` | `[[ $(uname -m) == arm64 \|\| ... ]]` | `...OSArchitecture -eq 'Arm64'` |
| `arch_is_x86_64` | `test (uname -m) = "x86_64"` | `[[ $(uname -m) == x86_64 ]]` | `[[ $(uname -m) == x86_64 ]]` | `...OSArchitecture -eq 'X64'` |

---

## Prefix Convention

Prefix (two-digit string) determines module load order:

| Range | Purpose | Example |
|-------|---------|---------|
| `00–09` | Early: PATH, environment | `00-path`, `05-editor` |
| `10–39` | Setup: tool init, options | `10-brew`, `20-completions` |
| `40–69` | Aliases, utilities | `40-eza`, `50-zoxide` |
| `70–99` | Late: interactive, local | `70-tmux`, `99-local` |

---

## Transpilation Process

The transpiler operates in these stages:

1. **Source collection** — Resolve CLI args + stdin to YAML file paths
2. **Manifest loading** — Load each YAML file via PyYAML
3. **Manifest merging** — Left-to-right merge with last-wins-by-name dedup
4. **Validation** — Check all required fields, guard/predicate names, body keys
5. **Code generation** — For each function and module, for each of the 4 shells:
   - Select template from data tables (GUARDS, PREDICATES, GUARD_CONDITIONS)
   - Render body constructs via render helpers
   - Wrap in shell-specific function/module structure
   - Write to output directory
6. **Gitignore generation** — Write `.gitignore` per output directory

The generator is **idempotent**: same manifest always produces identical output.

### Extensibility

The transpiler is data-driven. To extend:

| Add | Action |
|-----|--------|
| New guard type | Add one 4-tuple to `GUARDS` and `GUARD_CONDITIONS` dicts |
| New predicate | Add one 4-tuple to `PREDICATES` dict |
| New body type | Add render helper + branch in `generate_module()` |

---

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
```

Files are merged in the order given. If two sources define a function or module with the same name, the later one wins.

---

## Development

```bash
# Edit the manifest
vim .shellgen/shell.yaml

# Test (generates to temp dir, validates output)
cd .shellgen && make test

# Generate to source dir (for committing)
cd .shellgen && make generate

# Generate to ~/.config (what chezmoi apply does)
cd .shellgen && make generate-target
```
