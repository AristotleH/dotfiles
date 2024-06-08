#!/bin/zsh
# Path: lib/colors.zsh
# Color definitions

### only use colors if capable
[[ "$TERM" != 'dumb' ]] || return 1

### built-in colors
autoload -Uz colors && colors
