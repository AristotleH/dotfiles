#!/usr/bin/env fish

if type -q eza
    alias ls="eza"
    alias ll="eza -l"
    alias la="eza -la"
    alias lt="eza --tree"
end
