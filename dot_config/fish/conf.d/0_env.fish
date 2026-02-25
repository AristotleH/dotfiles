#!/usr/bin/env fish
# Environment configuration - runs on every shell start

# Disable greeting message (use -g not -U to avoid setting universal var repeatedly)
set -g fish_greeting

# Tide prompt truncation settings (configured via official tide variables).
set -g tide_git_truncation_strategy l
set -g tide_git_truncation_length 24
set -g tide_prompt_min_cols 70
