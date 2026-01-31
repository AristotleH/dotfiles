#!/usr/bin/env fish
# Homebrew shell environment setup
# https://github.com/orgs/Homebrew/discussions/4412#discussioncomment-8651316

# Detect homebrew location
if test -d /home/linuxbrew/.linuxbrew
    # Linux
    set -gx HOMEBREW_PREFIX /home/linuxbrew/.linuxbrew
    set -gx HOMEBREW_CELLAR $HOMEBREW_PREFIX/Cellar
    set -gx HOMEBREW_REPOSITORY $HOMEBREW_PREFIX/Homebrew
else if test -d /opt/homebrew
    # macOS (Apple Silicon)
    set -gx HOMEBREW_PREFIX /opt/homebrew
    set -gx HOMEBREW_CELLAR $HOMEBREW_PREFIX/Cellar
    set -gx HOMEBREW_REPOSITORY $HOMEBREW_PREFIX
else if test -d /usr/local/Homebrew
    # macOS (Intel)
    set -gx HOMEBREW_PREFIX /usr/local
    set -gx HOMEBREW_CELLAR $HOMEBREW_PREFIX/Cellar
    set -gx HOMEBREW_REPOSITORY /usr/local/Homebrew
else
    # Homebrew not installed
    return 0
end

# Add homebrew to PATH
fish_add_path -gP $HOMEBREW_PREFIX/bin $HOMEBREW_PREFIX/sbin

# Set MANPATH and INFOPATH
set -q MANPATH; or set MANPATH ''
set -gx MANPATH $HOMEBREW_PREFIX/share/man $MANPATH
set -q INFOPATH; or set INFOPATH ''
set -gx INFOPATH $HOMEBREW_PREFIX/share/info $INFOPATH
