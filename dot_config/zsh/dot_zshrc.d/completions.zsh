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
zstyle ':completion:*:git-checkout:*' sort false         # Don't sort git branches
zstyle ':completion:*' menu no                           # Let fzf-tab handle the menu

# fzf-tab: group descriptions (don't use escape sequences, fzf-tab ignores them)
zstyle ':completion:*:descriptions' format '[%d]'

# fzf-tab config
zstyle ':fzf-tab:*' switch-group '<' '>'                 # Switch groups with < >
zstyle ':fzf-tab:*' show-group brief                     # Show group name in header
zstyle ':fzf-tab:*' use-fzf-default-opts yes             # Use FZF_DEFAULT_OPTS

# fzf-tab colors and bindings
zstyle ':fzf-tab:*' fzf-flags \
    --color=fg:1,fg+:2 \
    --bind=tab:accept

# Preview for files and directories
zstyle ':fzf-tab:complete:cd:*' fzf-preview 'eza -1 --color=always $realpath'
zstyle ':fzf-tab:complete:ls:*' fzf-preview 'eza -1 --color=always $realpath'
zstyle ':fzf-tab:complete:*:*' fzf-preview 'bat --color=always --style=numbers --line-range=:500 $realpath 2>/dev/null || eza -1 --color=always $realpath 2>/dev/null'
