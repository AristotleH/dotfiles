.PHONY: help generate generate-target test test-unit test-sync clean

help:  ## Show this help
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | sort | awk 'BEGIN {FS = ":.*?## "}; {printf "\033[36m%-15s\033[0m %s\n", $$1, $$2}'

generate:  ## Generate shell configs for all 4 shells (to chezmoi source dir)
	@python3 generate_shell.py

generate-target:  ## Generate shell configs for all 4 shells to ~/.config (like chezmoi apply)
	@python3 generate_shell.py --target ~/.config shell.yaml ~/.config/shell.d

test:  ## Run all shell generator tests
	@echo "🧪 Running shell generator tests..."
	@python3 tests/test_shell_generator.py
	@python3 tests/test_shell_sync.py
	@echo "✅ All tests passed!"

test-unit:  ## Run shell generator unit tests
	@echo "🧪 Running shell generator unit tests..."
	@python3 tests/test_shell_generator.py

test-sync:  ## Validate shell generator output in temp dir
	@echo "🔍 Validating shell generator output..."
	@python3 tests/test_shell_sync.py

clean:  ## Remove Python cache files
	@find . -type d -name __pycache__ -exec rm -rf {} + 2>/dev/null || true
	@find . -type f -name "*.pyc" -delete
