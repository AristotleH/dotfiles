# Simple prompt: truncated pwd | git info | ❯
# Git info is computed asynchronously — the prompt appears instantly, then
# updates in-place once the background job finishes.
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

# -- async git state -----------------------------------------------------------
set -g __async_git_result ''
set -g __async_git_dir ''
set -g __async_git_pid 0
set -g __async_git_fresh 0

# -- pwd truncation ------------------------------------------------------------

function _prompt_pwd
    set -l home (string escape --style=regex $HOME)
    set -l cwd (string replace -r "^$home" '~' $PWD)
    set -l parts (string split / $cwd)
    set -l n (count $parts)

    set -l half (math -s0 "$COLUMNS / 2")
    set -l truncate false
    if test (string length -- $cwd) -gt $half
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

# -- fast git repo check (no subprocess) --------------------------------------

function _in_git_repo
    set -l dir $PWD
    while test -n "$dir"
        test -e "$dir/.git" && return 0
        set dir (string replace -r '/[^/]*$' '' $dir)
    end
    test -e "/.git"
end

# -- format async git result into colored string ------------------------------

function _format_git_info
    # Input: tab-separated: branch ahead behind stash conflicted staged dirty untracked
    set -l data (string split \t $argv[1])
    test (count $data) -lt 8 && return

    set -l branch $data[1]
    set -l ahead $data[2]
    set -l behind $data[3]
    set -l stash $data[4]
    set -l conflicted $data[5]
    set -l staged $data[6]
    set -l dirty $data[7]
    set -l untracked $data[8]

    if test "$conflicted" -gt 0 2>/dev/null
        printf '%s' $_c_brred
    else if test "$staged" -gt 0 2>/dev/null -o "$dirty" -gt 0 2>/dev/null -o "$untracked" -gt 0 2>/dev/null
        printf '%s' $_c_brylw
    else
        printf '%s' $_c_brgrn
    end
    printf '%s' $branch

    test "$behind" -gt 0 2>/dev/null     && printf '%s ⇣%s' $_c_brgrn $behind
    test "$ahead" -gt 0 2>/dev/null      && printf '%s ⇡%s' $_c_brgrn $ahead
    test "$stash" -gt 0 2>/dev/null      && printf '%s *%s' $_c_brgrn $stash
    test "$conflicted" -gt 0 2>/dev/null && printf '%s ~%s' $_c_brred $conflicted
    test "$staged" -gt 0 2>/dev/null     && printf '%s +%s' $_c_brylw $staged
    test "$dirty" -gt 0 2>/dev/null      && printf '%s !%s' $_c_brylw $dirty
    test "$untracked" -gt 0 2>/dev/null  && printf '%s ?%s' $_c_brblu $untracked
end

# -- arrow --------------------------------------------------------------------

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

# -- async git computation ----------------------------------------------------

function _async_git_start
    # If this repaint was triggered by async completion, skip
    if test $__async_git_fresh -eq 1
        set -g __async_git_fresh 0
        return
    end

    # Kill any pending background job
    if test $__async_git_pid -ne 0
        command kill $__async_git_pid 2>/dev/null
        set -g __async_git_pid 0
        functions -e __async_git_handler 2>/dev/null
    end

    # Fast non-git check (pure filesystem, zero subprocesses)
    if not _in_git_repo
        set -g __async_git_result ''
        set -g __async_git_dir $PWD
        return
    end

    set -l tmpfile /tmp/.fish_git_(status fish-pid)
    set -l dir $PWD

    # Spawn lightweight POSIX sh to compute git info in background.
    # Uses git status --porcelain=v2 --branch (single command) instead of
    # separate git branch + git status + git rev-list + git stash calls.
    command sh -c '
        cd "$1" 2>/dev/null || exit 1
        raw=$(git --no-optional-locks status --porcelain=v2 --branch 2>/dev/null) || exit 1
        branch="" ahead=0 behind=0 staged=0 dirty=0 untracked=0 conflicted=0 stash=0
        while IFS= read -r line; do
            case "$line" in
                "# branch.head "*)  branch="${line#\# branch.head }" ;;
                "# branch.ab "*)
                    ab="${line#\# branch.ab }"
                    ahead="${ab%% *}"; ahead="${ahead#+}"
                    behind="${ab##* }"; behind="${behind#-}" ;;
                "1 "*|"2 "*)
                    xy=$(printf "%.2s" "${line#? }")
                    x=$(printf "%.1s" "$xy")
                    y="${xy#?}"
                    [ "$x" != "." ] && staged=$((staged+1))
                    [ "$y" != "." ] && dirty=$((dirty+1)) ;;
                "u "*)  conflicted=$((conflicted+1)) ;;
                "? "*)  untracked=$((untracked+1)) ;;
            esac
        done <<GITEOF
$raw
GITEOF
        if [ "$branch" = "(detached)" ]; then
            branch=$(git tag --points-at HEAD 2>/dev/null | head -1)
            if [ -n "$branch" ]; then
                branch="#$branch"
            else
                branch="@$(git rev-parse --short HEAD 2>/dev/null)"
            fi
        fi
        [ ${#branch} -gt 24 ] && branch="$(printf "%.21s" "$branch")..."
        if git rev-parse --verify --quiet refs/stash >/dev/null 2>&1; then
            stash=$(git stash list 2>/dev/null | wc -l)
            stash=$(echo $stash)
        fi
        printf "%s\t%s\t%s\t%s\t%s\t%s\t%s\t%s" \
            "$branch" "$ahead" "$behind" "$stash" "$conflicted" "$staged" "$dirty" "$untracked"
    ' _ "$dir" > "$tmpfile" 2>/dev/null &

    set -g __async_git_pid $last_pid
    set -g __async_git_pending_dir $dir

    # Event handler: fires when background sh exits, updates cache, repaints
    functions -e __async_git_handler 2>/dev/null
    function __async_git_handler --on-process-exit $__async_git_pid
        set -l f /tmp/.fish_git_(status fish-pid)
        if test -f "$f"
            set -l raw (cat "$f" 2>/dev/null)
            rm -f "$f"
            if test -n "$raw"
                set -g __async_git_result (_format_git_info "$raw")
            else
                set -g __async_git_result ''
            end
            set -g __async_git_dir $__async_git_pending_dir
        end
        set -g __async_git_pid 0
        set -g __async_git_fresh 1
        commandline -f repaint
        functions -e __async_git_handler
    end
end

# -- prompt -------------------------------------------------------------------

function fish_prompt
    set -l last_status $status

    if set -q _transient_prompt
        set -e _transient_prompt
        printf '%s' $_c_brgrn
        test $last_status -ne 0 && printf '%s' $_c_brred
        printf '❯%s ' $_c_reset
        return
    end

    # Use cached git info if computed for current directory
    set -l git_info ''
    if test "$__async_git_dir" = "$PWD" -a -n "$__async_git_result"
        set git_info $__async_git_result
    end

    if test -n "$git_info"
        printf '%s%s %s ' (_prompt_pwd) $_c_reset $git_info
    else
        printf '%s ' (_prompt_pwd)
    end
    _prompt_arrow $last_status

    # Start async git computation (non-blocking)
    _async_git_start
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

# -- cleanup ------------------------------------------------------------------

function __fish_prompt_cleanup --on-event fish_exit
    rm -f /tmp/.fish_git_(status fish-pid)
end
