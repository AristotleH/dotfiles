#!/bin/zsh
# Path: $ZSHCONFIGDIR/lib/functions.zsh
# Load functions from $ZSHCONFIGDIR/functions

# Load all functions from the $ZSHCONFIGDIR/functions directory
function load-zsh-funcs {
    local func_file
    local -a func_name
    for func_file in $@; do
        [[ -d "$func_file" ]] || continue
        fpath=("$func_file" $fpath)
        func_name=($func_file/*(N.:t))
        (( $#func_name > 0 )) && autoload -Uz $func_name
    done
}

# Run the load functions function
load-zsh-funcs $ZDOTDIR/functions(N/) $ZDOTDIR/functions/*(N/)
