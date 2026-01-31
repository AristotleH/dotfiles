#!/bin/zsh
# Homebrew shell environment setup
# https://github.com/orgs/Homebrew/discussions/4412#discussioncomment-8651316

# Only run if brew is installed
(( $+commands[brew] )) || return 0

# Initialize Homebrew environment (sets PATH, MANPATH, INFOPATH)
eval "$(brew shellenv)"
