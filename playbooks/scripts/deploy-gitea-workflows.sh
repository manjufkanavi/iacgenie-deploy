#!/bin/bash
# Deploy CI workflows to Gitea repos.
# Run locally on the iacgenie-deploy machine.
set -euo pipefail

WORKFLOWS_DIR="playbooks/workflows"
GITEA_URL="https://gitea.iacgenie.com"

# Get Gitea admin token from vault env or prompt
GITEA_TOKEN="${GITEA_TOKEN:-$(cat /tmp/gitea_token 2>/dev/null || echo '')}"

if [ -z "$GITEA_TOKEN" ]; then
    echo "ERROR: Set GITEA_TOKEN env var or create /tmp/gitea_token"
    exit 1
fi

REPOS="iacgenie LightSerp iacgenie-unified-infra"

deploy_workflows() {
    local repo=$1
    local files=("$@")
    # Skip first 2 args (repo name + function args marker)
    shift 2
    files=("$@")
    
    echo "=== Deploying to $repo ==="
    
    local tmpdir=$(mktemp -d)
    mkdir -p "$tmpdir/.github/workflows"
    
    for f in "${files[@]}"; do
        cp "$f" "$tmpdir/.github/workflows/"
    done
    
    cd "$tmpdir"
    git init -b main 2>/dev/null || true
    git config user.email "ci@gitea.iacgenie.com"
    git config user.name "Gitea CI"
    git add -A
    git commit -m "chore(ci): add/update workflows" --allow-empty 2>/dev/null || echo "Commit (may already exist)"
    
    git remote add origin "${GITEA_URL}/manjufkanavi/${repo}.git" 2>/dev/null || git remote set-url origin "${GITEA_URL}/manjufkanavi/${repo}.git"
    git push -f origin main 2>&1
    
    cd - > /dev/null
    rm -rf "$tmpdir"
    echo "  Done"
}

# Deploy to iacgenie
deploy_workflows iacgenie \
    "$WORKFLOWS_DIR/iacgenie-smoke-test.yml" \
    "$WORKFLOWS_DIR/iacgenie-full.yml"

# Deploy to LightSerp
deploy_workflows LightSerp \
    "$WORKFLOWS_DIR/lightserv-ci.yml"

# Deploy to unified-infra
deploy_workflows iacgenie-unified-infra \
    "$WORKFLOWS_DIR/infra-ci.yml" \
    "$WORKFLOWS_DIR/iacgenie-ci.yml" \
    "$WORKFLOWS_DIR/docker-build-deploy.yml"

echo "=== All workflows deployed ==="
