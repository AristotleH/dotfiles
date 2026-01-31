#!/bin/zsh
# Tmux auto-attach/start
# Set TMUX_AUTO_ATTACH=1 to enable

(( $+commands[tmux] )) || return 0

# Disabled by default - set TMUX_AUTO_ATTACH=1 to enable
[[ "$TMUX_AUTO_ATTACH" != "1" ]] && return 0

# Skip if no TTY, already in tmux, in VSCode, or non-interactive
[[ ! -t 0 || -n "$TMUX" || "$TERM_PROGRAM" == "vscode" || ! -o interactive ]] && return 0

# Attach to existing session or create new one
tmux attach 2>/dev/null || tmux new-session
