#!/bin/bash
# Deploy CI/CD workflow files to Gitea repos via SSH
# Run from local machine - deploys to VM
set -euo pipefail

# Workflow file paths (local)
SMOKE_TEST=$(pwd)/playbooks/workflows/iacgenie-smoke-test.yml
FULL_PIPELINE=$(pwd)/playbooks/workflows/iacgenie-full.yml
LIGHTSERP_CI=$(pwd)/playbooks/workflows/lightserv-ci.yml
DOCKER_BUILD=$(pwd)/playbooks/workflows/docker-build-deploy.yml

# Remote paths
VM="mkanavi@192.168.0.118"
GITEA_BASE="/home/mkanavi/docker/iacgenie/gitea_data/data/git/repositories/manjufkanavi"

# Function to create a file in a bare Gitea repo using git plumbing
deploy_gitea_file() {
    local repo=$1
    local file_path=$2
    local content=$3
    
    local repo_path="${GITEA_BASE}/${repo}.git"
    
    echo "  Creating blob..."
    local blob_sha
    blob_sha=$(echo "$content" | git -C "$repo_path" hash-object -w --stdin 2>/dev/null) || \
        blob_sha=$(git hash-object -w --stdin <<< "$content" 2>/dev/null) || \
        blob_sha=$(echo "$content" | git hash-object -w --stdin)
    echo "  Blob: $blob_sha"
    
    echo "  Getting tree..."
    local current_tree
    current_tree=$(git -C "$repo_path" rev-parse HEAD^{tree} 2>/dev/null) || current_tree=""
    echo "  Current tree: ${current_tree:-empty}"
    
    echo "  Creating new tree..."
    local new_tree
    if [ -z "$current_tree" ]; then
        new_tree=$(echo "100644 blob $blob_sha	$file_path" | git -C "$repo_path" mktree)
    else
        new_tree=$(echo "100644 blob $blob_sha	$file_path" | git -C "$repo_path" mktree --missing)
    fi
    echo "  New tree: $new_tree"
    
    echo "  Creating commit..."
    local commit_sha
    commit_sha=$(GIT_AUTHOR_NAME="Gitea CI" GIT_AUTHOR_EMAIL="ci@gitea.iacgenie.com" \
        GIT_COMMITTER_NAME="Gitea CI" GIT_COMMITTER_EMAIL="ci@gitea.iacgenie.com" \
        git -C "$repo_path" commit-tree "$new_tree" -p HEAD 2>/dev/null)
    echo "  Commit: $commit_sha"
    
    echo "  Updating main ref..."
    git -C "$repo_path" update-ref refs/heads/main "$commit_sha"
    echo "  DONE: $file_path"
}

# === Deploy to iacgenie ===
echo "=== iacgenie ==="
ssh "$VM" "
deploy_gitea_file() {
    local repo_path='/home/mkanavi/docker/iacgenie/gitea_data/data/git/repositories/manjufkanavi/${1}.git'
    echo '  Blob:'
    echo '\$3' | git -C \"\$repo_path\" hash-object -w --stdin
    echo '  Tree:'
    git -C \"\$repo_path\" rev-parse HEAD^{tree}
    echo '  New tree:'
    echo \"100644 blob \$2	\$4\" | git -C \"\$repo_path\" mktree --missing
    echo '  Done'
}
deploy_gitea_file iacgenie PLACEHOLDER '.github/workflows/smoke-test.yml' 'PLACEHOLDER'
" 2>&1 || echo "  SSH approach failed, trying git plumbing directly"

echo "  This approach is too complex via SSH - will use direct commands"
