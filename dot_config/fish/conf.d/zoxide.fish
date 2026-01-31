#!/usr/bin/env fish
# Zoxide - smarter cd command
# Usage: z <partial-path> to jump to frequently used directories

command -q zoxide; or return 0

zoxide init fish | source
