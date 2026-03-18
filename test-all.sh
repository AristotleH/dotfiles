#!/bin/sh
# Run all tests that GHA would run, locally.
# Usage: ./test-all.sh [suite...]
#   No args  → run all suites
#   Args     → run only named suites (e.g. ./test-all.sh shell pkg)
#
# Suites: shell, shellgen, pkg, bootstrap, entrypoints
set -e

cd "$(dirname "$0")"

RED='\033[0;31m'
GREEN='\033[0;32m'
CYAN='\033[0;36m'
RESET='\033[0m'

passed=0
failed=0
failures=""

run() {
    name="$1"; shift
    printf "${CYAN}--- %s${RESET}\n" "$name"
    if "$@"; then
        passed=$((passed + 1))
        printf "${GREEN}    PASS${RESET}\n"
    else
        failed=$((failed + 1))
        failures="${failures}  - ${name}\n"
        printf "${RED}    FAIL${RESET}\n"
    fi
}

want() {
    _want_name="$1"; shift
    [ $# -eq 0 ] && return 0
    for _s in "$@"; do [ "$_s" = "$_want_name" ] && return 0; done
    return 1
}

suites="$*"

# --- Shell config validation (test-dotfiles.yml: shell-config) ---
if want shell $suites; then
    run "zsh config"       python3 .tests/test_zsh.py
    run "fish config"      python3 .tests/test_fish.py
    run "shell entrypoints" python3 .tests/test_shell_entrypoints.py
fi

# --- Shell generator (test-dotfiles.yml: shell-generator) ---
if want shellgen $suites; then
    run "shellgen unit"    python3 .shellgen/tests/test_shell_generator.py
    run "shellgen sync"    python3 .shellgen/tests/test_shell_sync.py
fi

# --- Package management (test-packages.yml: unit-tests) ---
if want pkg $suites; then
    run "pkg generator"    python3 .pkgmgmt/tests/test_generator.py
fi

# --- Bootstrap (test-dotfiles.yml: bootstrap) ---
if want bootstrap $suites; then
    run "bootstrap"        python3 .tests/test_bootstrap.py
fi

# --- Summary ---
echo ""
total=$((passed + failed))
if [ "$failed" -eq 0 ]; then
    printf "${GREEN}All %d suites passed.${RESET}\n" "$total"
else
    printf "${RED}%d/%d failed:${RESET}\n" "$failed" "$total"
    printf "$failures"
    exit 1
fi
