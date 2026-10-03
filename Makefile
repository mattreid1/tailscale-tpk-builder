# Tailscale TPK Builder Makefile

VERSION ?= $(shell cat src/version 2>/dev/null || echo "0.0.0.0")
PLATFORM := x86_64
OUTPUT := dist/Tailscale TOS5 $(VERSION) $(PLATFORM).tpk

.PHONY: all build clean verify update-latest update lint format typecheck check help

all: build

build: ## Build the TPK package
	@uv run python build.py build --platform $(PLATFORM)

clean: ## Remove built packages
	@rm -rf dist/*.tpk
	@echo "Cleaned dist/"

verify: ## Verify the built package
	@uv run python build.py verify "$(OUTPUT)"

update-latest: ## Update Tailscale to latest version
	@./update_tailscale.sh latest

update: ## Update Tailscale to specific version (usage: make update VERSION=1.92.1)
ifndef VERSION
	@echo "Usage: make update VERSION=1.92.1"
	@exit 1
endif
	@./update_tailscale.sh $(VERSION)

extract: ## Extract a TPK file (usage: make extract FILE=package.tpk)
ifndef FILE
	@echo "Usage: make extract FILE=package.tpk"
	@exit 1
endif
	@uv run python extract.py "$(FILE)"

lint: ## Run ruff linter
	@uv run ruff check .

format: ## Format code with ruff
	@uv run ruff format .
	@uv run ruff check --fix .

typecheck: ## Run mypy type checker
	@uv run mypy build.py extract.py

check: lint typecheck ## Run all checks (lint + typecheck)

help: ## Show this help
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | \
		awk 'BEGIN {FS = ":.*?## "}; {printf "  %-15s %s\n", $$1, $$2}'
