.PHONY: help generate test test-sync test-unit clean check

help:  ## Show this help
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | sort | awk 'BEGIN {FS = ":.*?## "}; {printf "\033[36m%-15s\033[0m %s\n", $$1, $$2}'

generate:  ## Generate all package lists from packages.yaml
	@echo "🔄 Generating package lists..."
	@python3 generate_packages.py
	@echo "✅ Done! Generated files are ready for commit."

test:  ## Run all tests
	@echo "🧪 Running all tests..."
	@python3 tests/test_generator.py
	@python3 tests/test_sync.py
	@echo "✅ All tests passed!"

test-unit:  ## Run unit tests only
	@echo "🧪 Running unit tests..."
	@python3 tests/test_generator.py

test-sync:  ## Test that generated files are in sync
	@echo "🔍 Checking if generated files are in sync..."
	@python3 tests/test_sync.py

check: test-sync  ## Quick check before commit (alias for test-sync)

clean:  ## Remove Python cache files
	@echo "🧹 Cleaning up..."
	@find . -type d -name __pycache__ -exec rm -rf {} + 2>/dev/null || true
	@find . -type f -name "*.pyc" -delete
	@echo "✅ Cleaned!"

workflow:  ## Show typical workflow
	@echo "📋 Package Management Workflow:"
	@echo ""
	@echo "1. Edit packages.yaml"
	@echo "   vim packages.yaml"
	@echo ""
	@echo "2. Generate platform files"
	@echo "   make generate"
	@echo ""
	@echo "3. Test everything"
	@echo "   make test"
	@echo ""
	@echo "4. Review changes"
	@echo "   git diff"
	@echo ""
	@echo "5. Commit"
	@echo "   git add packages.yaml ../dot_Brewfile_darwin ../dot_config/packages-*.txt.tmpl"
	@echo "   git commit -m 'Add new package: <name>'"
	@echo ""
	@echo "6. Apply with chezmoi"
	@echo "   chezmoi apply"
	@echo ""
	@echo "7. Install packages"
	@echo "   install-packages"
