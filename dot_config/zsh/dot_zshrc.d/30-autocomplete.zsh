#!/bin/zsh
# zsh-autocomplete post-plugin overrides
#
# zsh-autocomplete creates its completion widgets in a precmd hook,
# so we must also use a precmd hook to bind Tab AFTER those widgets exist.

_autocomplete_tab_setup() {
  # Remove zsh-autocomplete's `menu no no-select` — it prevents the
  # menu-select widget from entering interactive menu mode, falling back
  # to listing which triggers "do you wish to see?" on short terminals.
  zstyle -d ':completion:*:*:*:*:default' menu

  # Bind Tab/Shift-Tab to zsh-autocomplete's menu-select widget
  bindkey              '^I' menu-select
  bindkey "$terminfo[kcbt]" menu-select

  # Inside the menu: Tab cycles forward, Shift-Tab cycles backward
  bindkey -M menuselect              '^I' menu-complete
  bindkey -M menuselect "$terminfo[kcbt]" reverse-menu-complete

  # Only need to run once
  add-zsh-hook -d precmd _autocomplete_tab_setup
}

autoload -Uz add-zsh-hook
add-zsh-hook precmd _autocomplete_tab_setup
