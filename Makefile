# IacGenie Ansible Deployment Makefile

.SHELLFLAGS := -c
ANSIBLE ?= ansible
ANSIBLE_PLAYBOOK ?= ansible-playbook
VENV ?= .venv
VAULT_KEY ?= .vault_key

.PHONY: help install bootstrap services validate backup clean install-ansible lint sync

help: ## Show this help message
	@grep -E '^[a-zA-Z_-]+:.*##' $(MAKEFILE_LIST) | sort | awk 'BEGIN {FS = ":.*## "}; {printf "\033[36m%-30s\033[0m %s\n", $$1, $$2}'

install: ## Install Python dependencies
	python3 -m venv $(VENV)
	. $(VENV)/bin/activate && pip install -r requirements.txt
	@echo "Installed dependencies in $(VENV)/"

install-ansible: ## Install Ansible
	pip install "ansible-core>=2.15" "ansible-lint>=24.0"

lint: ## Run ansible-lint on all playbooks and roles
	$(ANSIBLE_LINT) -c .ansible-lint . || echo "Lint failed - see errors above"

sync: ## Install Ansible collections
	$(ANSIBLE) galaxy collection install -r collections/requirements.yml

bootstrap: ## Run bootstrap playbook (system setup only)
	$(ANSIBLE_PLAYBOOK) playbooks/bootstrap.yml --limit iacgenie-server

services: ## Deploy all Docker services
	$(ANSIBLE_PLAYBOOK) playbooks/services.yml --limit iacgenie-server

validate: ## Run post-deploy validation
	$(ANSIBLE_PLAYBOOK) playbooks/validate.yml --limit iacgenie-server

backup: ## Run backup playbook
	$(ANSIBLE_PLAYBOOK) playbooks/backup.yml --limit iacgenie-server

full-deploy: bootstrap services validate ## Full deployment: bootstrap + services + validate
	@echo "Full deployment complete"

dry-run: ## Run bootstrap + services in check mode (no changes)
	$(ANSIBLE_PLAYBOOK) playbooks/bootstrap.yml --limit iacgenie-server --check --diff
	$(ANSIBLE_PLAYBOOK) playbooks/services.yml --limit iacgenie-server --check --diff

vault-edit: ## Edit Ansible Vault
	vi $(VAULT_KEY)
	$(ANSIBLE) vault encrypt --vault-password-file $(VAULT_KEY) secrets/vault.yml

gen-vault-key: ## Generate a new vault key
	openssl rand -base64 32 > $(VAULT_KEY)
	chmod 600 $(VAULT_KEY)

clean: ## Clean generated files
	rm -rf .ansible/
	rm -rf .pytest_cache/
	rm -rf __pycache__/
	rm -rf .venv/

docker-compose: ## Generate docker-compose.yml from templates
	$(ANSIBLE) playbooks/services.yml --tags compose-only

help:
	@echo "IacGenie Infrastructure Deployment"
	@echo "=================================="
	@echo ""
	@echo "Usage: make [target]"
	@echo ""
	@echo "Targets:"
	@grep -E '^[a-zA-Z_-]+:.*##' $(MAKEFILE_LIST) | sort | awk 'BEGIN {FS = ":.*## "}; {printf "  \033[36m%-20s\033[0m %s\n", $$1, $$2}'
