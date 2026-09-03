#!/usr/bin/env python3
"""
External Repository Validation Script.
This script is intended to be run periodically (e.g., nightly or pre-release)
to validate the src engine against pinned real-world projects.

It avoids dynamically cloning these during unit tests to ensure deterministic
and fast test cycles.
"""
import os
import sys
import time
import subprocess
import tempfile
import argparse
from typing import Dict, Any

from src.pipeline.orchestrator import ScanPipeline

PINNED_REPOS = {
    "flask": "https://github.com/pallets/flask.git",
    "requests": "https://github.com/psf/requests.git",
    "typer": "https://github.com/tiangolo/typer.git",
    "fastapi": "https://github.com/tiangolo/fastapi.git"
}

def clone_repo(name: str, url: str, base_dir: str) -> str:
    target_dir = os.path.join(base_dir, name)
    if os.path.exists(target_dir):
        print(f"[{name}] Already cloned at {target_dir}")
        return target_dir
    
    print(f"[{name}] Cloning {url} into {target_dir}...")
    subprocess.run(["git", "clone", "--depth", "1", url, target_dir], check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    return target_dir

def analyze_repo(name: str, repo_path: str, catalog_path: str, output_dir: str) -> Dict[str, Any]:
    print(f"[{name}] Starting semantic scan...")
    t0 = time.time()
    
    try:
        pipeline = ScanPipeline(repo_path, catalog_path, workers=0)
        pipeline.run(output_dir)
        t1 = time.time()
        
        print(f"[{name}] Scan completed in {t1 - t0:.2f}s")
        print(f"  - Files parsed: {pipeline.files_parsed} / {pipeline.files_discovered}")
        print(f"  - Total findings: {len(pipeline.pattern_findings)}")
        
        return {
            "status": "SUCCESS",
            "time": t1 - t0,
            "files_parsed": pipeline.files_parsed,
            "findings": len(pipeline.pattern_findings)
        }
    except Exception as e:
        print(f"[{name}] Scan failed: {e}")
        return {
            "status": "FAILED",
            "error": str(e)
        }

def main():
    parser = argparse.ArgumentParser(description="Validate against real-world repositories.")
    parser.add_argument("--catalog", default="src/knowledge/catalog", help="Path to catalog")
    parser.add_argument("--output", default="tmp_external_validation", help="Output directory")
    args = parser.parse_args()
    
    os.makedirs(args.output, exist_ok=True)
    
    # We use a temporary directory for cloning to keep the workspace clean
    # unless the user specifies a cache dir. For simplicity, we use a temp dir.
    with tempfile.TemporaryDirectory() as temp_dir:
        results = {}
        for name, url in PINNED_REPOS.items():
            try:
                repo_path = clone_repo(name, url, temp_dir)
                res = analyze_repo(name, repo_path, args.catalog, args.output)
                results[name] = res
            except Exception as e:
                print(f"[{name}] Error preparing repository: {e}")
                results[name] = {"status": "FAILED", "error": str(e)}
        
        print("\n" + "="*50)
        print("EXTERNAL VALIDATION SUMMARY")
        print("="*50)
        all_passed = True
        for name, res in results.items():
            status = res["status"]
            if status == "SUCCESS":
                print(f"✅ {name}: {res['files_parsed']} files parsed, {res['findings']} findings ({res['time']:.2f}s)")
            else:
                all_passed = False
                print(f"❌ {name}: FAILED - {res.get('error', 'Unknown Error')}")
                
        if not all_passed:
            sys.exit(1)

if __name__ == "__main__":
    main()
