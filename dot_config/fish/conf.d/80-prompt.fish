status is-interactive; or return 0

# Transient prompt keybindings.
# Functions are defined in functions/fish_prompt.fish.
bind \r _transient_execute
bind \cc _transient_cancel
