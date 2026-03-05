# ─────────────────────────────────────────────
# Makefile — facebook-personal-ai-automation
# ─────────────────────────────────────────────
.PHONY: install test lint dom-learn clean help

PYTHON    := python
ACCOUNT   ?= pham_thanh
COOKIE    ?= accounts/$(ACCOUNT)/cookies.json

help:        ## Show this help
	@grep -E '^[a-z_-]+:.*##' Makefile | awk 'BEGIN{FS=":.*## "}{printf "  \033[36m%-18s\033[0m%s\n",$$1,$$2}'

install:     ## Install Python dependencies + Playwright browsers
	$(PYTHON) -m pip install --upgrade pip
	$(PYTHON) -m pip install -r requirements.txt
	$(PYTHON) -m playwright install chromium
	$(PYTHON) -m pip install pytest pytest-cov ruff

test:        ## Run unit tests
	$(PYTHON) -m pytest tests/ -v --tb=short

test-cov:    ## Run tests with coverage report
	$(PYTHON) -m pytest tests/ -v --tb=short --cov=scripts --cov-report=term-missing

lint:        ## Lint all Python files with ruff
	$(PYTHON) -m ruff check scripts/ tests/ --ignore=E501,E402

lint-fix:    ## Auto-fix lint issues
	$(PYTHON) -m ruff check scripts/ tests/ --fix --ignore=E501,E402

dom-learn:   ## Re-discover Facebook selectors (requires valid cookies)
	$(PYTHON) scripts/dom_learner.py \
		--cookie-file $(COOKIE) \
		--account $(ACCOUNT) \
		--headless

post-text:   ## Quick test: post text-only (use TEXT="..." make post-text)
	$(PYTHON) scripts/post.py \
		--account $(ACCOUNT) \
		--text "$(TEXT)" \
		--auto-approve

list-accounts: ## List all registered accounts
	$(PYTHON) scripts/account_manager.py list

check-proxy:  ## Check all proxy health
	$(PYTHON) scripts/proxy_manager.py health

daemon:       ## Start scheduler daemon
	$(PYTHON) scripts/scheduler.py --daemon

clean:        ## Remove Python cache files
	find . -type d -name "__pycache__" -exec rm -rf {} + 2>/dev/null || true
	find . -name "*.pyc" -delete 2>/dev/null || true
