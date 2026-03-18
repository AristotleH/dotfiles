#!/bin/sh
# Bootstrap dotfiles without chezmoi.
#
# Usage:
#   git clone <repo-url> dotfiles && dotfiles/bootstrap.sh
#
# This copies configs into ~/.config, sets up shell init files,
# and generates a .gitconfig from a template — everything chezmoi
# would normally do, but with no external dependencies beyond
# Python 3 + PyYAML.
set -e

REPO="$(cd "$(dirname "$0")" && pwd)"
CONFIG="${XDG_CONFIG_HOME:-$HOME/.config}"

# --- helpers --------------------------------------------------------

die()  { echo "error: $*" >&2; exit 1; }
info() { echo ":: $*"; }

detect_os() {
    case "$(uname -s)" in
        Darwin)          echo darwin  ;;
        Linux)           echo linux   ;;
        MINGW*|MSYS*)    echo windows ;;
        *)               echo unknown ;;
    esac
}

# Translate chezmoi naming conventions to real paths.
#   dot_foo  -> .foo
#   private_ -> (stripped, just affects permissions)
chezmoi_name() {
    echo "$1" \
        | sed 's/^private_//' \
        | sed 's/^dot_/./' \
        | sed 's|/private_|/|g' \
        | sed 's|/dot_|/.|g'
}

# Copy a file, creating parent dirs. Preserves permissions.
install_file() {
    _src="$1" _dst="$2"
    mkdir -p "$(dirname "$_dst")"
    cp "$_src" "$_dst"
}

# Recursively copy a source dir, translating chezmoi names.
# Skips .gitignore, .DS_Store, and .tmpl files.
copy_tree() {
    _src_dir="$1" _dst_dir="$2"
    find "$_src_dir" -type f | while read -r _f; do
        _rel="${_f#"$_src_dir"/}"
        case "$_rel" in
            *.tmpl) continue ;;
        esac
        case "$(basename "$_rel")" in
            .gitignore|.DS_Store|dot_DS_Store) continue ;;
        esac
        _dst="$_dst_dir/$(chezmoi_name "$_rel")"
        install_file "$_f" "$_dst"
    done
}

# --- pre-flight -----------------------------------------------------

OS="$(detect_os)"

if ! command -v python3 >/dev/null 2>&1; then
    die "python3 is required but not found"
fi

if ! python3 -c "import yaml" 2>/dev/null; then
    die "PyYAML is required: pip3 install pyyaml"
fi

# --- gitconfig (only template in the repo) --------------------------

info "Configuring git..."
if [ -f "$HOME/.gitconfig" ]; then
    info "  ~/.gitconfig already exists, skipping"
else
    printf "Git name:  "; read -r GIT_NAME
    printf "Git email: "; read -r GIT_EMAIL

    # Render the gitconfig template: substitute name/email,
    # strip Go template lines and the trailing empty [include].
    sed -e "s/{{ \.git\.email }}/$GIT_EMAIL/g" \
        -e "s/{{ \.git\.name }}/$GIT_NAME/g" \
        -e '/{{/d' \
        "$REPO/dot_gitconfig.tmpl" \
        | sed -e '$ { /^\[include\]$/d; }' \
        > "$HOME/.gitconfig"
    info "  wrote ~/.gitconfig"
fi

# --- shell config generator ----------------------------------------

info "Generating shell configs..."
SHELLGEN="$REPO/.shellgen/generate_shell.py"
if [ -f "$SHELLGEN" ]; then
    python3 "$SHELLGEN" --target "$CONFIG" --quiet </dev/null
    info "  generated fish/zsh/bash/powershell configs"
else
    die ".shellgen/generate_shell.py not found"
fi

# --- shell init files (top-level dotfiles) --------------------------

info "Installing shell init files..."
for f in dot_bashrc dot_bash_profile dot_zshenv dot_tmux.conf; do
    [ -f "$REPO/$f" ] || continue
    dst="$HOME/$(chezmoi_name "$f")"
    if [ -f "$dst" ]; then
        info "  $dst already exists, skipping"
    else
        install_file "$REPO/$f" "$dst"
        info "  $dst"
    fi
done

# --- dot_config trees (fish, zsh, bash, tmux, etc.) -----------------

info "Installing config directories..."

# fish and zsh are skipped on Windows (matches .chezmoiignore)
for dir in fish zsh bash powershell tmux mise ghostty nvim; do
    [ -d "$REPO/dot_config/$dir" ] || continue
    case "$OS" in
        windows) case "$dir" in fish|zsh) continue ;; esac ;;
    esac
    copy_tree "$REPO/dot_config/$dir" "$CONFIG/$dir"
    info "  $dir"
done

# --- PowerShell bridge (Windows only) ------------------------------

if [ "$OS" = "windows" ]; then
    PS_BRIDGE="$REPO/private_Documents/private_PowerShell/Microsoft.PowerShell_profile.ps1"
    PS_DST="$HOME/Documents/PowerShell/Microsoft.PowerShell_profile.ps1"
    if [ -f "$PS_BRIDGE" ]; then
        if [ -f "$PS_DST" ]; then
            info "  $PS_DST already exists, skipping"
        else
            install_file "$PS_BRIDGE" "$PS_DST"
            info "  PowerShell bridge profile"
        fi
    fi
fi

# --- done -----------------------------------------------------------

info "Bootstrap complete."
info ""
info "To install packages, set up a packages.yaml and run:"
info "  python3 $REPO/.pkgmgmt/generate_packages.py \\"
info "    --manifest /path/to/packages.yaml --output-dir /tmp/pkgs"
