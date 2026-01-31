#!/bin/zsh
# Tmux auto-attach/start
# Automatically attach to existing session or create new one

(( $+commands[tmux] )) || return 0

# Skip if already in tmux, in VSCode, or non-interactive
[[ -n "$TMUX" || "$TERM_PROGRAM" == "vscode" || ! -o interactive ]] && return 0

# Attach to existing session or create new one
tmux attach 2>/dev/null || tmux new-session
