#!/bin/zsh
# Modern ls replacement using eza
# https://github.com/eza-community/eza

# Only set aliases if eza is installed
(( $+commands[eza] )) || return 0

alias ls="eza"
alias ll="eza -l"
alias la="eza -la"
alias lt="eza --tree"
