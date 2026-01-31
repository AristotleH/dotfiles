#!/usr/bin/env fish
# Run a command in a different directory and return to the original
# Usage: in_dir <directory> <command> [args...]
# Returns the exit code of the command

function in_dir
    if test (count $argv) -lt 2
        echo "Usage: in_dir <directory> <command> [args...]" >&2
        return 1
    end

    set -l target_dir $argv[1]
    set -l original_dir $PWD

    if not cd $target_dir 2>/dev/null
        echo "in_dir: cannot access directory: $target_dir" >&2
        return 1
    end

    # Run the command (from argv[2] onwards)
    $argv[2..]
    set -l exit_code $status

    cd $original_dir
    return $exit_code
end
