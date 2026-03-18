.PHONY: help test clean

help:  ## Show this help
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | sort | awk 'BEGIN {FS = ":.*?## "}; {printf "\033[36m%-15s\033[0m %s\n", $$1, $$2}'

test:  ## Run generator unit tests
	@echo "Running package generator tests..."
	@python3 tests/test_generator.py
	@echo "All tests passed!"

clean:  ## Remove Python cache files
	@find . -type d -name __pycache__ -exec rm -rf {} + 2>/dev/null || true
	@find . -type f -name "*.pyc" -delete
