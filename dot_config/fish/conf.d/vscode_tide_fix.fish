# VSCode shell integration fix for Tide prompt in Fish
# Loads our fish_prompt wrapper to prevent extra newlines

if status is-interactive
    # Detect VSCode environment through any relevant env variable
    if test -n "$VSCODE_SHELL_INTEGRATION" -o \
            -n "$VSCODE_PID" -o \
            -n "$VSCODE" -o \
            -n "$VSCODE_CLI" -o \
            "$TERM_PROGRAM" = "vscode"
            
        # Load our fix when in VSCode
        source "$__fish_config_dir/functions/fish_prompt_vscode_fix.fish"
    end
end
