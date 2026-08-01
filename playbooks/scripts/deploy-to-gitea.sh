#!/bin/bash
# Deploy workflow files to Gitea repos using git plumbing
# Run on VM: chmod +x /tmp/deploy-to-gitea.sh && bash /tmp/deploy-to-gitea.sh
set -euo pipefail

GITEA_BASE="/home/mkanavi/docker/iacgenie/gitea_data/data/git/repositories/manjufkanavi"
WORKFLOWS="/tmp/gitea-workflows"

deploy_file() {
    local repo="$1"
    local src_file="$2"
    local dest_path="$3"
    local repo_path="${GITEA_BASE}/${repo}.git"
    
    echo "  Deploying ${repo}: ${dest_path}"
    
    local blob
    blob=$(cat "$src_file" | git -C "$repo_path" hash-object -w --stdin)
    
    local current_tree
    current_tree=$(git -C "$repo_path" rev-parse HEAD^{tree} 2>/dev/null || true)
    
    local new_tree
    if [ -z "$current_tree" ]; then
        new_tree=$(printf "100644 blob %s\t%s" "$blob" "$dest_path" | git -C "$repo_path" mktree)
    else
        new_tree=$(printf "100644 blob %s\t%s" "$blob" "$dest_path" | git -C "$repo_path" mktree --missing)
    fi
    
    local commit
    commit=$(GIT_AUTHOR_NAME="Gitea CI" GIT_AUTHOR_EMAIL="ci@gitea.iacgenie.com" \
        GIT_COMMITTER_NAME="Gitea CI" GIT_COMMITTER_EMAIL="ci@gitea.iacgenie.com" \
        git -C "$repo_path" commit-tree "$new_tree" -p HEAD)
    
    git -C "$repo_path" update-ref refs/heads/main "$commit"
    echo "    OK"
}

echo "=== iacgenie ==="
deploy_file "iacgenie" "$WORKFLOWS/iacgenie-smoke-test.yml" ".github/workflows/smoke-test.yml"
deploy_file "iacgenie" "$WORKFLOWS/iacgenie-full.yml" ".github/workflows/docker-build-deploy.yml"

echo "=== lightserp ==="
deploy_file "lightserp" "$WORKFLOWS/lightserv-ci.yml" ".github/workflows/smoke-test.yml"
deploy_file "lightserp" "$WORKFLOWS/docker-build-deploy.yml" ".github/workflows/docker-build-deploy.yml"

echo "=== iacgenie-unified-infra ==="
deploy_file "iacgenie-unified-infra" "$WORKFLOWS/docker-build-deploy.yml" ".github/workflows/docker-build-deploy.yml"

echo "=== All deployments complete ==="
