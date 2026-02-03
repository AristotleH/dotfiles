#!/usr/bin/env fish
# Check if running on Linux
function is-linux --description 'Check if running on Linux'
    test (uname) = "Linux"
end
