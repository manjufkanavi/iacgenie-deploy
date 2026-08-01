#!/usr/bin/env python3
"""Deploy CI/CD workflow files to Gitea repos via API."""
import subprocess, json, base64, sys

GITEA_TOKEN = "483d18c3f8ea979e07aa9ac1decd62a2a62ea5a8"
GITEA_BASE = "https://gitea.iacgenie.com/api/v1/repos/manjufkanavi"

def get_sha(repo, filepath):
    try:
        out = subprocess.run(
            ["curl", "-sf", "-H", f"Authorization: token {GITEA_TOKEN}",
             f"{GITEA_BASE}/{repo}/contents/{filepath}"],
            capture_output=True, text=True, timeout=10
        )
        if out.returncode == 0:
            data = json.loads(out.stdout)
            return data.get("sha", "")
    except Exception:
        pass
    return ""

def deploy_file(repo, filepath, content):
    encoded = base64.b64encode(content.encode()).decode()
    sha = get_sha(repo, filepath)
    action = "update" if sha else "create"
    
    payload = {
        "content": encoded,
        "encoding": "base64",
        "message": f"ci: deploy {filepath}",
        "branch": "main",
    }
    if sha:
        payload["sha"] = sha
    
    try:
        result = subprocess.run(
            ["curl", "-sfX", "PUT", "-H", f"Authorization: token {GITEA_TOKEN}",
             "-H", "Content-Type: application/json",
             "-d", json.dumps(payload),
             f"{GITEA_BASE}/{repo}/contents/{filepath}"],
            capture_output=True, text=True, timeout=15
        )
        if result.returncode == 0:
            print(f"  OK {filepath} ({action})")
            return True
        else:
            stderr_short = result.stderr[:200].strip() if result.stderr else "(no output)"
            print(f"  FAIL {filepath}: {stderr_short}")
            return False
    except Exception as e:
        print(f"  FAIL {filepath}: {e}")
        return False

def main():
    local_dir = "/Users/manjunathkanavi/projects/iacgenie-deploy"
    workflows = {
        "iacgenie": [
            ("playbooks/workflows/iacgenie-smoke-test.yml", ".github/workflows/smoke-test.yml"),
            ("playbooks/workflows/iacgenie-full.yml", ".github/workflows/docker-build-deploy.yml"),
        ],
        "LightSerp": [
            ("playbooks/workflows/lightserv-ci.yml", ".github/workflows/smoke-test.yml"),
            ("playbooks/workflows/docker-build-deploy.yml", ".github/workflows/docker-build-deploy.yml"),
        ],
        "iacgenie-unified-infra": [
            ("playbooks/workflows/docker-build-deploy.yml", ".github/workflows/docker-build-deploy.yml"),
        ],
    }
    
    all_ok = True
    for repo, files in workflows.items():
        print(f"=== {repo} ===")
        for src_path, dest_path in files:
            full_src = f"{local_dir}/{src_path}"
            try:
                with open(full_src) as f:
                    content = f.read()
                if not deploy_file(repo, dest_path, content):
                    all_ok = False
            except FileNotFoundError:
                print(f"  SKIP {src_path} not found locally")
                all_ok = False
        print()
    
    if all_ok:
        print("All workflows deployed successfully!")
    else:
        print("Some deployments failed")
    sys.exit(0)

if __name__ == "__main__":
    main()
