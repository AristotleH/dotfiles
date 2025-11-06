#!/usr/bin/env fish

if status is-interactive
    # Commands to run in interactive sessions can go here

    # Fix for prompt disappearing after Ctrl-C
    # Ensure prompt is redrawn after SIGINT
    function __restore_prompt_on_sigint --on-signal SIGINT
        commandline -f repaint
    end
end

# Source external/local fish config if it exists (for machine-specific settings)
# This file is NOT managed by chezmoi - keep private/local settings here
if test -f ~/.config/fish/config.local.fish
    source ~/.config/fish/config.local.fish
end
