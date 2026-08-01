#!/usr/bin/env python3
"""Deploy CI/CD workflow files to Gitea repos via API (debug version)."""
import subprocess, json, base64, sys, tempfile

GITEA_TOKEN = "483d18c3f8ea979e07aa9ac1decd62a2a62ea5a8"
GITEA_BASE = "https://gitea.iacgenie.com/api/v1/repos/manjufkanavi"

def get_sha(repo, filepath):
    try:
        out = subprocess.run(
            ["curl", "-sk", "-s", "-w", "%{http_code}", "-o", "/tmp/gitea_get.json",
             "-H", f"Authorization: token {GITEA_TOKEN}",
             f"{GITEA_BASE}/{repo}/contents/{filepath}"],
            capture_output=True, text=True, timeout=10
        )
        http_code = out.stdout.strip()
        if http_code == "200":
            with open("/tmp/gitea_get.json") as f:
                data = json.loads(f.read())
            return data.get("sha", "")
        else:
            print(f"  GET {filepath}: HTTP {http_code}")
    except Exception as e:
        print(f"  GET error: {e}")
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
    
    # Write payload to temp file and use @- for curl
    with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
        json.dump(payload, f)
        payload_file = f.name
    
    try:
        result = subprocess.run(
            ["curl", "-sk", "-s", "-w", "%{http_code}", "-o", "/tmp/gitea_put.json",
             "-X", "PUT",
             "-H", f"Authorization: token {GITEA_TOKEN}",
             "-H", "Content-Type: application/json",
             f"--data-binary=@{payload_file}",
             f"{GITEA_BASE}/{repo}/contents/{filepath}"],
            capture_output=True, text=True, timeout=15
        )
        http_code = result.stdout.strip()
        if http_code == "200" or http_code == "201":
            print(f"  OK {filepath} ({action}) HTTP {http_code}")
            return True
        else:
            try:
                with open("/tmp/gitea_put.json") as f:
                    err_body = f.read()
            except:
                err_body = result.stderr[:200] if result.stderr else "(no output)"
            print(f"  FAIL {filepath}: HTTP {http_code} - {err_body[:200]}")
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
