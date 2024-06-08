#!/bin/zsh
# Path: lib/prompt.zsh
# Zsh prompt settings

# 16.2.8 Prompting
setopt prompt_subst       # Expand parameters in prompt variables.
setopt transient_rprompt  # Remove right prompt artifacts from prior commands.

# Function to load settings for p10k theme
function prompt_p10k_setup {
    if [[ -n "$1" ]]; then
        local -a configs=($ZDOTDIR/themes/$1.p10k.zsh(N))
        (( $#configs )) && source $configs[1]
    else
        source $ZDOTDIR/themes/.p10k.zsh
    fi
    prompt_powerlevel10k_setup
}

# Function to load settings for starship theme
function prompt_starship_setup {
    # When loaded through the prompt command, these prompt_* options will be enabled
    prompt_opts=(cr percent sp subst)

    if [[ -n "$1" ]]; then
        local -a configs=(
        $__zsh_config_dir/themes/$1.toml(N)
        ${XDG_CONFIG_HOME:-$HOME/.config}/starship/$1.toml(N)
        )
        (( $#configs )) && export STARSHIP_CONFIG=$configs[1]
    fi

    source <(starship init zsh)
}

# Wrap promptinit
function promptinit {
    unfunction promptinit
    autoload -Uz promptinit && promptinit

    # Hook P10k into Zsh's prompt system
    if (( $+functions[prompt_powerlevel10k_setup] )); then
        prompt_themes+=( p10k )
    else
        unfunction prompt_p10k_setup
    fi

    # Hook starship into Zsh's prompt system
    if (( $+commands[starship] )); then
        prompt_themes+=( starship )
    else
        unfunction prompt_starship_setup
    fi

    # Keep prompt array sorted
    prompt_themes=( "${(@on)prompt_themes}" )
}
