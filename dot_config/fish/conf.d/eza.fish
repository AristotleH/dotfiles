#!/usr/bin/env fish
# Modern ls replacement using eza
# https://github.com/eza-community/eza

command -q eza; or return 0

alias ls='eza'
alias ll='eza -l'
alias la='eza -la'
alias lt='eza --tree'
