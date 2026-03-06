# Simple prompt: truncated pwd | git info | ❯
# Uses raw ANSI codes to avoid linter spell-check noise on color names.
# Colors: brcyan=96, cyan=36, brmagenta=95, brgreen=92, bryellow=93,
#         brred=91, brblue=94, brblack=90, reset=0

set -g _c_reset  \e'[0m'
set -g _c_cyan   \e'[36m'
set -g _c_brcyan \e'[96m'
set -g _c_brmag  \e'[95m'
set -g _c_brgrn  \e'[92m'
set -g _c_brylw  \e'[93m'
set -g _c_brred  \e'[91m'
set -g _c_brblu  \e'[94m'
set -g _c_brblk  \e'[90m'

function _prompt_pwd
    set -l home (string escape --style=regex $HOME)
    set -l cwd (string replace -r "^$home" '~' $PWD)
    set -l parts (string split / $cwd)
    set -l n (count $parts)

    # Only truncate middle dirs if the full path is wider than half the terminal
    set -l truncate false
    if test (string length -- $cwd) -gt (math -s0 $COLUMNS / 2)
        set truncate true
    end

    set -l out
    for i in (seq $n)
        set -l p $parts[$i]
        if test $i -eq 1 -o $i -eq $n
            set -a out "$_c_brcyan$p"
        else if test -z $p
            set -a out ''
        else if test $truncate = true
            set -a out "$_c_brmag"(string sub -l 1 $p)
        else
            set -a out "$_c_brcyan$p"
        end
    end
    printf '%s' (string join "$_c_cyan/$_c_reset" $out)
end

function _prompt_git
    set -l branch (git branch --show-current 2>/dev/null)
    test $status -ne 0 && return  # not a git repo

    if test -z "$branch"
        set branch (git tag --points-at HEAD 2>/dev/null | head -1)
        test -n "$branch" && set branch "#$branch" \
            || set branch "@"(git rev-parse --short HEAD 2>/dev/null)
    end

    set branch (string shorten -m24 $branch)

    set -l stat (git --no-optional-locks status --porcelain 2>/dev/null)
    set -l stash (git stash list 2>/dev/null | count)
    set -l staged (string match -r '^[ADMR]' $stat | count)
    set -l dirty (string match -r '^.[ADMR]' $stat | count)
    set -l untracked (string match -r '^\?\?' $stat | count)
    set -l conflicted (string match -r '^UU' $stat | count)
    set -l behind 0
    set -l ahead 0
    set -l upstream (git rev-list --count --left-right @{upstream}...HEAD 2>/dev/null)
    if test -n "$upstream"
        echo $upstream | read -l b a
        set behind $b
        set ahead $a
    end

    if test $conflicted -gt 0
        printf '%s' $_c_brred
    else if test $staged -gt 0 -o $dirty -gt 0 -o $untracked -gt 0
        printf '%s' $_c_brylw
    else
        printf '%s' $_c_brgrn
    end
    printf '%s' $branch

    test $behind -gt 0     && printf '%s ⇣%s' $_c_brgrn $behind
    test $ahead -gt 0      && printf '%s ⇡%s' $_c_brgrn $ahead
    test $stash -gt 0      && printf '%s *%s' $_c_brgrn $stash
    test $conflicted -gt 0 && printf '%s ~%s' $_c_brred $conflicted
    test $staged -gt 0     && printf '%s +%s' $_c_brylw $staged
    test $dirty -gt 0      && printf '%s !%s' $_c_brylw $dirty
    test $untracked -gt 0  && printf '%s ?%s' $_c_brblu $untracked
end

function _prompt_arrow
    set -l last_status $argv[1]
    test $last_status -eq 0 && printf '%s' $_c_brgrn || printf '%s' $_c_brred
    # fish_bind_mode defaults to 'default' even without vi bindings, so we
    # must gate on fish_key_bindings to avoid showing ❮ when not in vi mode.
    if string match -q '*vi*' -- $fish_key_bindings
        switch $fish_bind_mode
            case default;             printf '❮'
            case replace replace_one; printf '▶'
            case visual;              printf '❮'
            case '*';                 printf '❯'
        end
    else
        printf '❯'
    end
    printf '%s ' $_c_reset
end

function fish_prompt
    set -l last_status $status

    if set -q _transient_prompt
        set -e _transient_prompt
        printf '%s' $_c_brgrn
        test $last_status -ne 0 && printf '%s' $_c_brred
        printf '❯%s ' $_c_reset
        return
    end

    set -l git_info (_prompt_git)
    if test -n "$git_info"
        printf '%s%s %s\n' (_prompt_pwd) $_c_reset $git_info
    else
        printf '%s\n' (_prompt_pwd)
    end
    _prompt_arrow $last_status
end

function fish_right_prompt
    set -q _transient_prompt && return
    test $CMD_DURATION -lt 3000 && return
    printf '%s' $_c_brblk
    if test $CMD_DURATION -lt 60000
        printf '%ds' (math -s0 $CMD_DURATION / 1000)
    else if test $CMD_DURATION -lt 3600000
        printf '%dm%ds' (math -s0 $CMD_DURATION / 60000) \
            (math -s0 "$CMD_DURATION % 60000 / 1000")
    else
        printf '%dh%dm' (math -s0 $CMD_DURATION / 3600000) \
            (math -s0 "$CMD_DURATION % 3600000 / 60000")
    end
    printf '%s' $_c_reset
end

# -- transient prompt ---------------------------------------------------------
# Collapse full prompt to just the arrow when Enter is pressed.

function _transient_execute
    set -g _transient_prompt 1
    commandline -f repaint
    commandline -f execute
end

function _transient_cancel
    set -g _transient_prompt 1
    commandline -f repaint
    commandline ''
    commandline -f execute
end

