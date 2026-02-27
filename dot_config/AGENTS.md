# User-Level Agent Guidelines

## Philosophy

* Create only what you need, and nothing more. Don't be speculative. YAGNI.
* All code should be pleasantly human-readable. Don't be clever. KISS.
* The less code you write, the better. Conciseness is a virtue, along with readability. DRY.
* Write at a reasonable level of abstraction. Only deduplicate when you are confident it will be useful.
* Proactively delete dead code.
* Only add dependencies when absolutely necessary.
* If you're able to verify that you code works, do so before you finish responding. If there's no way to do this, but you can make a durable one, do so.
* If you've acted twice or more at the same level of abstraction and it still doesn't work, take a step back and try to understand the problem better. Then respond to me with your understanding and pause for feedback from me. Don't waste tokens doing the same kind of thing over and over again.
* Proactively handle edge cases and improve code quality, when directly relevant.

## Rules

* Lines must be at most 120 characters long. Better if they're at most 80.
* Write comments to explain why, not what. If your code isn't self-documenting, rewrite it.
* Fix warnings. If you can't fix them, document why.
* Added code should have tests, if possible. Tests should exercise intended behavior, not implementation.
* Work on feature branches, never on the trunk.

## Workflow

* At the start of each session, review the current state of the relevant parts of the codebase and the state of the problem we're trying to solve.
* Think about my request before implementing. Plan if necessary, but only if necessary.
* When planning, make durable, long-term solutions. Address the tough, open questions and ask for clarifications if needed. If you think my prompt is too vague, ask me for more details. Feel free to do this before or after you've started to plan.
* Make targeted, incremental changes. Don't get stuck in trial-and-error loops for too long. If you find yourself stuck, go back to planning.
* Commit frequently. Once you've made significant, quality progress, push the commits. Use the imperative mood and keep your messages concise, but detailed.
