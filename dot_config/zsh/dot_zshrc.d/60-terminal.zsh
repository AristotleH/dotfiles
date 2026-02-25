#!/bin/zsh
# Terminal integration - OSC sequences for modern terminals
# Enables CWD reporting, semantic prompts, etc.

# Report CWD to terminal via OSC 7 (works with tmux passthrough)
function _osc7_cwd {
  printf '\e]7;file://%s%s\e\\' "$HOST" "${PWD// /%20}"
}
autoload -Uz add-zsh-hook
add-zsh-hook chpwd _osc7_cwd
_osc7_cwd  # Run once at startup
