#!/usr/bin/env fish
# Check if running on macOS/Darwin
function is-darwin --description 'Check if running on macOS'
    test (uname) = "Darwin"
end
