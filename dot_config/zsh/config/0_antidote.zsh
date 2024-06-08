#!/bin/zsh
# Path: config/0_prelude.zsh
# First config file to load, loads antidote and sets up before plugin config

# Setup antidote.
: ${ZSH_CUSTOM:=$ZDOTDIR}
: ${ANTIDOTE_HOME:=${XDG_CACHE_HOME:-~/.cache}/repos}
zstyle -s ':antidote:repo' path antidote_path || antidote_path=$ANTIDOTE_HOME/mattmc3/antidote
zstyle ':antidote:bundle' use-friendly-names 'yes'

zplugins_txt=${ZDOTDIR}/.zplugins
zplugins_static=${ZDOTDIR}/.zplugins.zsh
zstyle ':antidote:bundle' file $zplugins_txt
zstyle ':antidote:static' file $zplugins_static

# Clone antidote if missing.
[[ -d $antidote_path ]] || git clone --depth 1 --quiet https://github.com/mattmc3/antidote $antidote_path

# Lazy-load antidote from its functions directory.
fpath=($antidote_path/functions $fpath)
autoload -Uz antidote

# Generate static file in a subshell whenever .zplugins is updated.
if [[ ! ${zplugins}.zsh -nt ${zplugins} ]] || [[ ! -e $ANTIDOTE_HOME/.lastupdated ]]; then
    antidote bundle <${zplugins_txt} >|${zplugins_static}
    date +%Y-%m-%dT%H:%M:%S%z >| $ANTIDOTE_HOME/.lastupdated
fi

# Source the static file.
source $zplugins_static
