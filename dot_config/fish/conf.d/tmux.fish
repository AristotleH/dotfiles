#!/usr/bin/env fish
# Tmux auto-attach/start
# Set TMUX_AUTO_ATTACH=1 to enable

# Skip if tmux not installed
command -v tmux >/dev/null 2>&1; or return 0

# Disabled by default - set TMUX_AUTO_ATTACH=1 to enable
test "$TMUX_AUTO_ATTACH" = "1"; or return 0

# Skip if no TTY, already in tmux, in VSCode, or non-interactive
if not isatty stdin; or set -q TMUX; or test "$TERM_PROGRAM" = "vscode"; or not status is-interactive
    return 0
end

# Attach to existing session or create new one
tmux attach 2>/dev/null; or tmux new-session
