#!/bin/zsh
# Zoxide - smarter cd command
# Usage: z <partial-path> to jump to frequently used directories

(( $+commands[zoxide] )) || return 0

eval "$(zoxide init zsh)"
