#!/usr/bin/env fish
# Environment configuration - runs on every shell start

# Disable greeting message (use -g not -U to avoid setting universal var repeatedly)
set -g fish_greeting

# Tide prompt truncation settings (configured via official tide variables).
# Keep the start of branch names and truncate from the end.
# Empty strategy maps to `string shorten -m...` (default right-side truncation).
set -g tide_git_truncation_strategy ""
set -g tide_git_truncation_length 24
set -g tide_prompt_min_cols 70
