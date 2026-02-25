#!/bin/zsh
# Completion system configuration

# Put system zsh functions before homebrew in fpath
# This uses the full native _git completion (8500+ lines) instead of
# homebrew's bash wrapper (295 lines) which doesn't complete subcommand options
fpath=(/usr/share/zsh/${ZSH_VERSION}/functions $fpath)

# Completion styling
zstyle ':completion:*' matcher-list 'm:{a-z}={A-Z}'      # Case-insensitive matching
zstyle ':completion:*' list-colors ${(s.:.)LS_COLORS}    # Colorize completions
zstyle ':completion:*:messages' format '%F{purple}-- %d --%f'
zstyle ':completion:*:warnings' format '%F{red}-- no matches --%f'
zstyle ':completion:*:descriptions' format '%F{yellow}-- %d --%f'
zstyle ':completion:*:git-checkout:*' sort false         # Don't sort git branches
