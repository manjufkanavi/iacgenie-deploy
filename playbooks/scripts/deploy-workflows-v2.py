#!/usr/bin/env python3
"""Deploy CI/CD workflow files to Gitea repos via API using urllib."""
import json, base64, sys, ssl
from urllib.request import Request, urlopen
from urllib.error import HTTPError

GITEA_TOKEN = "951d8437d0a3d3ba0540126544d74f78771aed06"
GITEA_BASE = "https://gitea.iacgenie.com/api/v1/repos/admin"

def api_get(repo, filepath):
    url = f"{GITEA_BASE}/{repo}/contents/{filepath}"
    req = Request(url)
    req.add_header("Authorization", f"token {GITEA_TOKEN}")
    req.add_header("Accept", "application/json")
    try:
        ctx = ssl.create_default_context()
        ctx.check_hostname = False
        ctx.verify_mode = ssl.CERT_NONE
        with urlopen(req, context=ctx) as resp:
            return json.loads(resp.read())
    except HTTPError as e:
        if e.code == 404:
            return None
        print(f"  GET error for {filepath}: HTTP {e.code}")
        return None
    except Exception as e:
        print(f"  GET error for {filepath}: {e}")
        return None

def api_put(repo, filepath, content, sha=""):
    url = f"{GITEA_BASE}/{repo}/contents/{filepath}"
    payload = {
        "content": base64.b64encode(content.encode()).decode(),
        "encoding": "base64",
        "message": f"ci: deploy {filepath}",
        "branch": "main",
    }
    if sha:
        payload["sha"] = sha
    
    data = json.dumps(payload).encode()
    req = Request(url, data=data, method="PUT")
    req.add_header("Authorization", f"token {GITEA_TOKEN}")
    req.add_header("Content-Type", "application/json")
    try:
        ctx = ssl.create_default_context()
        ctx.check_hostname = False
        ctx.verify_mode = ssl.CERT_NONE
        with urlopen(req, context=ctx, timeout=15) as resp:
            status = resp.status
            body = json.loads(resp.read())
            print(f"  OK {filepath} (HTTP {status})")
            return True
    except HTTPError as e:
        try:
            err_body = json.loads(e.read())
            print(f"  FAIL {filepath}: HTTP {e.code} - {err_body.get('message','unknown')}")
        except:
            print(f"  FAIL {filepath}: HTTP {e.code}")
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
                sha = api_get(repo, dest_path)
                if sha is None:
                    print(f"  SKIP {dest_path} not found (404)")
                else:
                    print(f"  Found existing SHA: {sha.get('sha','?')}")
            except FileNotFoundError:
                print(f"  SKIP {src_path} not found locally")
                all_ok = False
        print()
    
    sys.exit(0)

if __name__ == "__main__":
    main()
