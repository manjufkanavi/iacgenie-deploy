#!/usr/bin/env python3
"""
Deploy CI/CD workflow files to Gitea repos using git plumbing commands.
Runs via SSH on the VM host where Gitea data directory is accessible.
"""
import json, base64, subprocess, sys, tempfile, os

GITEA_BASE = "/home/mkanavi/docker/iacgenie/gitea_data/data/git/repositories/manjufkanavi"
WORKFLOW_DIR = "/Users/manjunathkanavi/projects/iacgenie-deploy/playbooks/workflows"

WORKFLOWS = {
    "iacgenie": {
        "ci": "iacgenie-smoke-test.yml",
        "docker": "iacgenie-full.yml",
    },
    "lightserp": {
        "ci": "lightserv-ci.yml",
        "docker": "docker-build-deploy.yml",
    },
    "iacgenie-unified-infra": {
        "docker": "docker-build-deploy.yml",
    },
}

def git_cmd(repo, *args, **kwargs):
    """Run a git command inside a bare repo."""
    repo_path = f"{GITEA_BASE}/{repo}.git"
    result = subprocess.run(
        ["git", f"--git-dir={repo_path}"] + list(args),
        capture_output=True, text=True, timeout=30, **kwargs
    )
    if result.returncode != 0 and not kwargs.get("check", False):
        print(f"  Git error: {result.stderr[:200]}")
    return result

def deploy_file(repo, filepath, content):
    """Add/update a file in a Gitea repo using git plumbing."""
    repo_path = f"{GITEA_BASE}/{repo}.git"
    
    # Create blob
    blob_result = git_cmd(repo, "hash-object", "-w", "--stdin", input=content)
    if blob_result.returncode != 0:
        print(f"  FAIL blob for {filepath}")
        return False
    blob_sha = blob_result.stdout.strip()
    
    # Get current tree
    tree_result = git_cmd(repo, "rev-parse", "HEAD^{tree}")
    if tree_result.returncode != 0:
        print(f"  FAIL tree for {filepath}")
        return False
    current_tree = tree_result.stdout.strip()
    
    if not current_tree:
        # First file - create new tree
        tree_input = f"100644 blob {blob_sha}\t{filepath}"
        new_tree = subprocess.run(
            ["git", f"--git-dir={repo_path}", "mktree"],
            input=tree_input, capture_output=True, text=True, timeout=10
        )
    else:
        # Add file to existing tree
        tree_input = f"100644 blob {blob_sha}\t{filepath}"
        new_tree = subprocess.run(
            ["git", f"--git-dir={repo_path}", "mktree", "--missing"],
            input=tree_input, capture_output=True, text=True, timeout=10
        )
    
    if new_tree.returncode != 0:
        print(f"  FAIL mktree for {filepath}: {new_tree.stderr[:200]}")
        return False
    new_tree_sha = new_tree.stdout.strip()
    
    # Create commit
    commit_env = {
        **os.environ,
        "GIT_AUTHOR_NAME": "Gitea CI",
        "GIT_AUTHOR_EMAIL": "ci@gitea.iacgenie.com",
        "GIT_COMMITTER_NAME": "Gitea CI",
        "GIT_COMMITTER_EMAIL": "ci@gitea.iacgenie.com",
    }
    commit_args = ["commit-tree", new_tree_sha, "-p", "HEAD"]
    commit_result = subprocess.run(
        ["git", f"--git-dir={repo_path}"] + commit_args,
        capture_output=True, text=True, timeout=10,
        env=commit_env
    )
    
    if commit_result.returncode != 0:
        print(f"  FAIL commit for {filepath}: {commit_result.stderr[:200]}")
        return False
    commit_sha = commit_result.stdout.strip()
    
    # Update main branch
    update_result = git_cmd(repo, "update-ref", "refs/heads/main", commit_sha)
    if update_result.returncode != 0:
        print(f"  FAIL update-ref for {filepath}")
        return False
    
    print(f"  OK {filepath}")
    return True

def main():
    all_ok = True
    for repo, files in WORKFLOWS.items():
        print(f"=== {repo} ===")
        for name, src_path in files.items():
            full_src = os.path.join(WORKFLOW_DIR, src_path)
            try:
                with open(full_src) as f:
                    content = f.read()
                if not deploy_file(repo, f".github/workflows/{name}.yml", content):
                    all_ok = False
            except FileNotFoundError:
                print(f"  SKIP {src_path} not found")
                all_ok = False
        print()
    
    if all_ok:
        print("All workflows deployed!")
    else:
        print("Some deployments failed")
    return 0 if all_ok else 1

if __name__ == "__main__":
    sys.exit(main())
