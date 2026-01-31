#!/usr/bin/env fish
# Fuzzy finder integration
# Provides Ctrl-R (history), Ctrl-T (files), Alt-C (directories)

command -q fzf; or return 0

# Default fzf options
set -gx FZF_DEFAULT_OPTS "\
--height=40% \
--layout=reverse \
--border \
--info=inline \
--bind='ctrl-/:toggle-preview'"

# Use fd for faster file finding if available
if command -q fd
    set -gx FZF_DEFAULT_COMMAND 'fd --type f --hidden --follow --exclude .git'
    set -gx FZF_CTRL_T_COMMAND $FZF_DEFAULT_COMMAND
    set -gx FZF_ALT_C_COMMAND 'fd --type d --hidden --follow --exclude .git'
end

# Preview files with bat if available
if command -q bat
    set -gx FZF_CTRL_T_OPTS "--preview 'bat --color=always --style=numbers --line-range=:500 {}'"
end

# Set up fzf key bindings
fzf --fish | source
