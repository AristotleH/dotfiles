#!/bin/zsh
# Path: lib/0_prelude.zsh
# First lib file to load

### Load .zstyles, if it exists
[[ -r ${ZDOTDIR}/.zstyles ]] && source ${ZDOTDIR}/.zstyles

### Setup homebrew
typeset -aU _brew_cmd=(
    $HOME/.homebrew/bin/brew(N)
    $HOME/.linuxbrew/bin/brew(N)
    /opt/homebrew/bin/brew(N)
    /usr/local/bin/brew(N)
    /home/linuxbrew/.linuxbrew/bin/brew(N)
)

if (( $#_brew_cmd )); then
    source <($_brew_cmd[1] shellenv)
fi
unset _brew_cmd

### PATH setup
# Clear dupes from PATH
typeset -gU cdpath fpath mailpath path

# Setup path
path=(
    $HOME/bin(N)
    $HOME/sbin(N)
    $HOME/.local/bin(N)
    $HOMEBREW_PREFIX/bin(N)
    $HOMEBREW_PREFIX/sbin(N)
    /usr/local/bin(N)
    /usr/local/sbin(N)
    $path
)
