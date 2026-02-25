#!/bin/zsh

### Completions
setopt always_to_end     # Move cursor to the end of a completed word.
setopt auto_list         # Automatically list choices on ambiguous completion.
setopt auto_menu         # Show completion menu on a successive tab press.
setopt auto_param_slash  # If completed parameter is a directory, add a trailing slash.
setopt complete_in_word  # Complete from both ends of a word.
setopt NO_menu_complete  # Do not autoselect the first completion entry.

### Directory navigation
setopt auto_pushd         # Make cd push the old directory onto the dirstack.
setopt pushd_minus        # Exchanges meanings of +/- when navigating the dirstack.
setopt pushd_silent       # Do not print the directory stack after pushd or popd.
setopt pushd_to_home      # Push to home directory when no argument is given.
setopt extended_glob      # Use more awesome globbing features.
setopt glob_dots          # Include dotfiles when globbing.
setopt path_dirs          # Perform path search even on command names with slashes.
setopt NO_clobber         # Don't overwrite files with >. Use >| to bypass.
setopt NO_rm_star_silent  # Ask for confirmation for `rm *' or `rm path/*'
setopt multios        # Write to multiple descriptors.

### History
# History file location and size
HISTFILE=${XDG_STATE_HOME:-$HOME/.local/state}/zsh/history
HISTSIZE=50000                 # Max events in internal history
SAVEHIST=50000                 # Max events in history file
[[ -d ${HISTFILE:h} ]] || mkdir -p ${HISTFILE:h}  # Create dir if needed

setopt bang_hist               # Treat the '!' character specially during expansion.
setopt extended_history        # Write the history file in the ':start:elapsed;command' format.
setopt hist_expire_dups_first  # Expire a duplicate event first when trimming history.
setopt hist_find_no_dups       # Do not display a previously found event.
setopt hist_ignore_all_dups    # Delete an old recorded event if a new event is a duplicate.
setopt hist_ignore_dups        # Do not record an event that was just recorded again.
setopt hist_ignore_space       # Do not record an event starting with a space.
setopt hist_reduce_blanks      # Remove extra blanks from commands added to the history list.
setopt hist_save_no_dups       # Do not write a duplicate event to the history file.
setopt hist_verify             # Do not execute immediately upon history expansion.
setopt inc_append_history      # Write to the history file immediately, not when the shell exits.
setopt NO_hist_beep            # Don't beep when accessing non-existent history.
setopt NO_share_history        # Don't share history between all sessions.

### Prompt
setopt prompt_subst       # Expand parameters in prompt variables.
setopt transient_rprompt  # Remove right prompt artifacts from prior commands.
