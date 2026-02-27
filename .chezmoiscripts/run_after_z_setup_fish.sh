#!/bin/sh

internet_available() {
    command -v curl >/dev/null 2>&1 || return 1
    curl -fsSLI --connect-timeout 2 --max-time 5 https://github.com >/dev/null 2>&1
}

if ! command -v fish >/dev/null 2>&1; then
    exit 0
fi

if fish -c "functions -q tide" >/dev/null 2>&1; then
    fish -c "
        if not set -q tide_left_items
            tide configure --auto --style=Lean --prompt_colors='16 colors' --show_time=No --lean_prompt_height='One line' --prompt_spacing=Compact --icons='Few icons' --transient=Yes
        end
    " >/dev/null 2>&1 || true
    exit 0
fi

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
restore_prompt() {
    if [ -f "$FISH_PROMPT.bak" ]; then
        mv "$FISH_PROMPT.bak" "$FISH_PROMPT"
    fi
}
trap restore_prompt EXIT

if [ -f "$FISH_PROMPT" ]; then
    mv "$FISH_PROMPT" "$FISH_PROMPT.bak"
fi

if internet_available; then
    fish -c "
        if not functions -q fisher
            if command -sq curl
                curl -sL https://raw.githubusercontent.com/jorgebucaran/fisher/main/functions/fisher.fish | source
            end
        end
        if functions -q fisher
            fisher install
        end
    " >/dev/null 2>&1
else
    exit 0
fi

# Configure tide universal variables on first setup
fish -c "
    if functions -q tide; and not set -q tide_left_items
        tide configure --auto --style=Lean --prompt_colors='16 colors' --show_time=No --lean_prompt_height='One line' --prompt_spacing=Compact --icons='Few icons' --transient=Yes
    end
" >/dev/null 2>&1 || true

trap - EXIT
restore_prompt
