.PHONY: help generate generate-shell generate-shell-target test test-sync test-unit test-zsh test-shell-unit test-shell-sync clean check

help:  ## Show this help
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | sort | awk 'BEGIN {FS = ":.*?## "}; {printf "\033[36m%-15s\033[0m %s\n", $$1, $$2}'

generate:  ## Generate all package lists and shell configs
	@echo "🔄 Generating package lists..."
	@python3 generate_packages.py
	@echo "🔄 Generating shell configs (to chezmoi source dir)..."
	@python3 generate_shell.py
	@echo "✅ Done!"

generate-shell:  ## Generate shell configs from shell.yaml (source dir)
	@python3 generate_shell.py

generate-shell-target:  ## Generate shell configs to ~/.config (like chezmoi apply)
	@python3 generate_shell.py --target ~/.config shell.yaml ~/.config/shell.d

test:  ## Run all tests
	@echo "🧪 Running all tests..."
	@python3 tests/test_generator.py
	@python3 tests/test_sync.py
	@python3 tests/test_zsh.py
	@python3 tests/test_shell_generator.py
	@python3 tests/test_shell_sync.py
	@echo "✅ All tests passed!"

test-unit:  ## Run unit tests only
	@echo "🧪 Running unit tests..."
	@python3 tests/test_generator.py

test-sync:  ## Test that generated files are in sync
	@echo "🔍 Checking if generated files are in sync..."
	@python3 tests/test_sync.py
	@python3 tests/test_shell_sync.py

test-zsh:  ## Run zsh configuration tests
	@echo "🔍 Checking zsh configuration..."
	@python3 tests/test_zsh.py

test-shell-unit:  ## Run shell generator unit tests
	@echo "🧪 Running shell generator unit tests..."
	@python3 tests/test_shell_generator.py

test-shell-sync:  ## Validate shell generator output in temp dir
	@echo "🔍 Validating shell generator output..."
	@python3 tests/test_shell_sync.py

check: test-sync test-zsh  ## Quick check before commit

clean:  ## Remove Python cache files
	@echo "🧹 Cleaning up..."
	@find . -type d -name __pycache__ -exec rm -rf {} + 2>/dev/null || true
	@find . -type f -name "*.pyc" -delete
	@echo "✅ Cleaned!"

workflow:  ## Show typical workflow
	@echo "📋 Package Management Workflow:"
	@echo ""
	@echo "1. Edit packages.yaml or shell.yaml"
	@echo "   vim packages.yaml"
	@echo "   vim shell.yaml"
	@echo ""
	@echo "2. Generate platform files"
	@echo "   make generate"
	@echo ""
	@echo "3. Test everything"
	@echo "   make test"
	@echo ""
	@echo "4. Review and commit"
	@echo "   git diff && git add -p && git commit"
	@echo ""
	@echo "5. Apply (shell configs are generated automatically)"
	@echo "   chezmoi apply"
	@echo ""
	@echo "📋 Per-machine shell customization:"
	@echo "   Create ~/.config/shell.d/*.yaml with extra functions/modules"
	@echo "   See SHELL.md for details"
