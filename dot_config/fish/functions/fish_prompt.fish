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
set -g __dot_prompt_cache_dir "$HOME/.cache/dot_prompt"

function _prompt_path_parts_length
    set -l total 0
    for p in $argv
        set total (math $total + (string length -- $p))
    end
    if test (count $argv) -gt 1
        set total (math $total + (count $argv) - 1)
    end
    printf '%s' $total
end

function _prompt_truncate_tail
    set -l text $argv[1]
    set -l keep $argv[2]
    if test $keep -le 1
        printf '…'
        return
    end
    set -l tail_len (math $keep - 1)
    if test $tail_len -ge (string length -- $text)
        printf '%s' $text
        return
    end
    printf '…%s' (string sub -s -$tail_len -- $text)
end

function _prompt_max_width
    set -l cols $COLUMNS
    test -n "$cols"; or set cols 80
    printf '%s' (math "max(0, $cols - 30)")
end

function _prompt_segment_limit
    set -l cols $argv[1]
    if test $cols -lt 40
        printf '0'
    else if test $cols -lt 60
        printf '1'
    else if test $cols -lt 80
        printf '2'
    else
        printf '%s' $cols
    end
end

function _prompt_pwd
    set -l max_width $argv[1]
    test -n "$max_width"; or set max_width (_prompt_max_width)
    set -l home (string escape --style=regex $HOME)
    set -l cwd (string replace -r "^$home" '~' $PWD)
    set -l cols $COLUMNS
    test -n "$cols"; or set cols 80

    set -l raw_parts (string split / $cwd)
    set -l display_parts $raw_parts
    set -l n (count $display_parts)
    set -l budget (math "max(10, $max_width - 2)")
    set -l limit (_prompt_segment_limit $cols)

    if test $limit -eq 0 -a $n -gt 2
        if test "$display_parts[1]" = '' -o "$display_parts[1]" = '~'
            set display_parts $display_parts[1] '…' $display_parts[$n]
        else
            set display_parts '…' $display_parts[$n]
        end
    else if test $limit -lt $cols
        for i in (seq 2 (math $n - 1))
            set -l seg $display_parts[$i]
            if test -n "$seg" -a (string length -- $seg) -gt $limit
                set display_parts[$i] (string sub -l $limit -- $seg)
            end
        end
    end

    set n (count $display_parts)
    set -l length (_prompt_path_parts_length $display_parts)

    if test $length -gt $budget -a $n -gt 2
        set -l compact_parts
        set -l start 1
        if test "$display_parts[1]" = '' -o "$display_parts[1]" = '~'
            set compact_parts $display_parts[1]
            set start 2
        end

        set -l tail_parts $display_parts[$n]
        for i in (seq (math $n - 1) -1 $start)
            set -l candidate $compact_parts '…' $display_parts[$i] $tail_parts
            if test (_prompt_path_parts_length $candidate) -gt $budget
                break
            end
            set tail_parts $display_parts[$i] $tail_parts
        end

        set display_parts $compact_parts '…' $tail_parts
        set n (count $display_parts)
        set length (_prompt_path_parts_length $display_parts)
    end

    if test $length -gt $budget -a $n -ge 1
        set -l other 0
        if test $n -gt 1
            set other (_prompt_path_parts_length $display_parts[1..(math $n - 1)])
        end
        set -l keep (math "max(1, $budget - $other - 1)")
        set display_parts[$n] (_prompt_truncate_tail $display_parts[$n] $keep)
    end

    set -l out
    for i in (seq $n)
        set -l p $display_parts[$i]
        if test $i -eq 1 -o $i -eq $n
            set -a out "$_c_brcyan$p"
        else if test -z "$p"
            set -a out ''
        else
            set -a out "$_c_brmag$p"
        end
    end
    printf '%s' (string join "$_c_cyan/$_c_reset" $out)
end

function _prompt_git_root
    set -l dir $PWD
    while true
        if test -e "$dir/.git"
            printf '%s' $dir
            return 0
        end
        if test "$dir" = '/'
            return 1
        end
        set dir (path dirname $dir)
    end
end

function _prompt_git_cache_key
    printf '%s.fish' (string replace -ra '[^A-Za-z0-9_.-]' '_' -- $argv[1])
end

function _prompt_git_build
    set -l repo $argv[1]
    set -l max_branch $argv[2]
    test -n "$max_branch"; or set max_branch 24
    set -l branch (command git -C "$repo" branch --show-current 2>/dev/null)
    if test -z "$branch"
        set branch (command git -C "$repo" tag --points-at HEAD 2>/dev/null | head -1)
        if test -n "$branch"
            set branch "#$branch"
        else
            set branch "@"(command git -C "$repo" rev-parse --short HEAD 2>/dev/null)
        end
    end
    test $max_branch -lt 4; and return
    if test (string length -- $branch) -gt $max_branch
        set branch (_prompt_truncate_tail $branch $max_branch)
    end

    set -l stat (command git -C "$repo" --no-optional-locks status --porcelain 2>/dev/null)
    set -l stash (command git -C "$repo" stash list 2>/dev/null | count)
    set -l staged (string match -r '^[ADMR]' $stat | count)
    set -l dirty (string match -r '^.[ADMR]' $stat | count)
    set -l untracked (string match -r '^\?\?' $stat | count)
    set -l conflicted (string match -r '^UU' $stat | count)
    set -l behind 0
    set -l ahead 0
    set -l upstream (command git -C "$repo" rev-list --count --left-right \
        @{upstream}...HEAD 2>/dev/null)
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
    true
end

function _prompt_git_refresh_async
    set -l repo $argv[1]
    set -l max_branch $argv[2]
    test -n "$max_branch"; or set max_branch 24
    set -l key (_prompt_git_cache_key $repo)
    set -l cache "$__dot_prompt_cache_dir/$key.git"
    set -l lock "$cache.lock"

    mkdir -p $__dot_prompt_cache_dir 2>/dev/null
    if not command mkdir "$lock" 2>/dev/null
        return
    end

    set -l head_cache "$__dot_prompt_cache_dir/$key.head"
    set -l script "$__dot_prompt_cache_dir/$key.worker.fish"
    set -l repo_q (string escape -- $repo)
    set -l cache_q (string escape -- $cache)
    set -l lock_q (string escape -- $lock)
    set -l head_q (string escape -- $head_cache)
    printf '%s\n' \
        "set _c_reset  \\e'[0m'" \
        "set _c_brgrn  \\e'[92m'" \
        "set _c_brylw  \\e'[93m'" \
        "set _c_brred  \\e'[91m'" \
        "set _c_brblu  \\e'[94m'" \
        (functions _prompt_git_build) \
        "_prompt_git_build $repo_q $max_branch > $cache_q.tmp" \
        "and mv $cache_q.tmp $cache_q" \
        "cat $repo_q/.git/HEAD > $head_q 2>/dev/null" \
        "rmdir $lock_q" \
        "rm -f (status filename)" \
        > $script
    fish --private $script >/dev/null 2>&1 &
end

function _prompt_git
    set -l max_branch $argv[1]
    test -n "$max_branch"; or set max_branch 24
    command -sq git; or return
    set -l repo (_prompt_git_root)
    or return

    set -l key (_prompt_git_cache_key $repo)
    set -l cache "$__dot_prompt_cache_dir/$key.git"
    set -l head_cache "$__dot_prompt_cache_dir/$key.head"
    set -l head_now (cat "$repo/.git/HEAD" 2>/dev/null)

    # If HEAD changed since last cache, rebuild synchronously.
    if test -f "$cache" -a -n "$head_now"
        set -l head_prev (cat "$head_cache" 2>/dev/null)
        if test "$head_now" != "$head_prev"
            _prompt_git_build $repo $max_branch > "$cache.sync"
            and mv "$cache.sync" "$cache"
            printf '%s' "$head_now" > "$head_cache"
            cat "$cache"
            return
        end
    end

    _prompt_git_refresh_async $repo $max_branch

    test -f "$cache"; and cat "$cache"
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

    set -l max_width (_prompt_max_width)
    set -l pwd_info (_prompt_pwd $max_width)
    set -l pwd_plain (string replace -ra '\e\\[[0-9;]*m' '' -- $pwd_info)
    set -l git_branch_budget \
        (math "$max_width - "(string length -- $pwd_plain)" - 2 - 2")
    set -l git_info
    if test $git_branch_budget -ge 4
        set -l repo (_prompt_git_root)
        if test -n "$repo"
            set git_info (_prompt_git $git_branch_budget 2>/dev/null)
        end
    end
    if test -n "$git_info"
        printf '%s%s %s ' $pwd_info $_c_reset $git_info
    else
        printf '%s ' $pwd_info
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
