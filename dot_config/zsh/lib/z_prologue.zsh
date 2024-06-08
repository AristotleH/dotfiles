#!/bin/zsh
# Path: lib/z_prologue.zsh
# Last lib file to load

# Init completions.
(( $+functions[compinit] )) || custom-compinit

# Source config files.
for _zshconfig in $ZDOTDIR/config/*.zsh(N); source $_zshconfig; unset _zshconfig

# Source aliases.
for _zshalias in $ZDOTDIR/aliases/*.zsh(N); source $_zshalias; unset _zshalias

function zshrc-finale {
    # Init prompt if needed
    if (( $#prompt_themes == 0 )); then
        promptinit

        if [[ $TERM == dumb ]]; then
            prompt 'off'
        else
            local -a prompt_argv
            prompt_argv=(off)
            prompt "$prompt_argv[@]"
        fi
    fi

    # Set prompt
    prompt p10k
}
