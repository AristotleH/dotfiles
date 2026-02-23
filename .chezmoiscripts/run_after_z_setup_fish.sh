#!/bin/sh

if ! command -v fish >/dev/null 2>&1; then
    exit 0
fi

echo "Setting up fish shell..."

# Ensure fish_plugins exists before running fisher.
FISH_PLUGINS="$HOME/.config/fish/fish_plugins"
if [ ! -f "$FISH_PLUGINS" ]; then
    CHEZMOI_SRC=$(chezmoi source-path 2>/dev/null)
    if [ -n "$CHEZMOI_SRC" ] && [ -f "$CHEZMOI_SRC/dot_config/fish/fish_plugins" ]; then
        mkdir -p "$HOME/.config/fish"
        cp "$CHEZMOI_SRC/dot_config/fish/fish_plugins" "$FISH_PLUGINS"
    fi
fi

# Temporarily move fish_prompt.fish out of the way so tide can install without conflict.
# After fisher finishes, we restore chezmoi's version.
FISH_PROMPT="$HOME/.config/fish/functions/fish_prompt.fish"
if [ -f "$FISH_PROMPT" ]; then
    mv "$FISH_PROMPT" "$FISH_PROMPT.bak"
fi

fish -c "
    if not functions -q fisher
        echo 'Bootstrapping fisher...'
        curl -sL https://raw.githubusercontent.com/jorgebucaran/fisher/main/functions/fisher.fish | source
    end
    fisher update
"

# Configure tide universal variables on first setup
fish -c "
    if functions -q tide; and not set -q tide_left_items
        tide configure --auto --style=Lean --prompt_colors='16 colors' --show_time=No --lean_prompt_height='One line' --prompt_spacing=Compact --icons='Few icons' --transient=Yes
    end
"

# Restore chezmoi's fish_prompt.fish over tide's generated version
if [ -f "$FISH_PROMPT.bak" ]; then
    mv "$FISH_PROMPT.bak" "$FISH_PROMPT"
fi
