# VSCode shell integration fix for fish_prompt
# This file directly replaces the fish_prompt function to prevent extra newlines

# Store the original function if not already stored
if not functions -q __original_fish_prompt
    # Copy the original fish_prompt function before replacing it
    functions -c fish_prompt __original_fish_prompt
end

# Define our replacement fish_prompt
function fish_prompt
    # Get the result from the original function
    set -l original_output (__original_fish_prompt)
    
    # Only trim trailing newlines but preserve spaces
    # Using regex to match only newlines at the end, not spaces
    set -l cleaned_output (string replace -r '\n+$' '' -- "$original_output")
    
    # Output the prompt content using printf to prevent unwanted newlines
    printf "%s" "$cleaned_output"
end