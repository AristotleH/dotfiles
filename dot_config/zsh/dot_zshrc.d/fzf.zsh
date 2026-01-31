#!/bin/zsh
# Fuzzy finder integration
# Provides Ctrl-R (history), Ctrl-T (files), Alt-C (directories)

(( $+commands[fzf] )) || return 0

# Default fzf options
export FZF_DEFAULT_OPTS="
  --height=40%
  --layout=reverse
  --border
  --info=inline
  --bind='ctrl-/:toggle-preview'
"

# Use fd for faster file finding if available
if (( $+commands[fd] )); then
  export FZF_DEFAULT_COMMAND='fd --type f --hidden --follow --exclude .git'
  export FZF_CTRL_T_COMMAND="$FZF_DEFAULT_COMMAND"
  export FZF_ALT_C_COMMAND='fd --type d --hidden --follow --exclude .git'
fi

# Preview files with bat if available
if (( $+commands[bat] )); then
  export FZF_CTRL_T_OPTS="--preview 'bat --color=always --style=numbers --line-range=:500 {}'"
fi

# Set up fzf key bindings and fuzzy completion
source <(fzf --zsh)
