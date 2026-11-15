#!/usr/bin/env python3
"""Verify a reviewed Actions candidate before uploading it to Pages."""
import argparse
import json
import os
from pathlib import Path
import re
import subprocess
import urllib.request

from build_site import IPHONE_ID, REPO_ROOT, file_manifest, sha256


def verify_files(directory, expected):
    actual = file_manifest(directory)
    actual.pop("candidate.json", None)
    if actual != expected:
        raise ValueError("Candidate file list, sizes or SHA-256 hashes differ from its manifest.")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--run-id", required=True)
    parser.add_argument("--source-commit", required=True)
    parser.add_argument("--directory", type=Path, required=True)
    args = parser.parse_args()
    if not re.fullmatch(r"[0-9]+", args.run_id) or not re.fullmatch(r"[0-9a-f]{40}", args.source_commit):
        raise ValueError("Use a numeric run ID and a full lowercase source commit SHA.")
    if os.environ.get("GITHUB_REF") != "refs/heads/main":
        raise ValueError("Promotion is restricted to main.")
    repository = os.environ["GITHUB_REPOSITORY"]
    request = urllib.request.Request(
        f"https://api.github.com/repos/{repository}/actions/runs/{args.run_id}",
        headers={"Authorization": f"Bearer {os.environ['GH_TOKEN']}",
                 "Accept": "application/vnd.github+json", "X-GitHub-Api-Version": "2022-11-28"},
    )
    with urllib.request.urlopen(request, timeout=30) as response:
        run = json.load(response)
    if (run.get("status") != "completed" or run.get("conclusion") != "success"
            or run.get("path") != ".github/workflows/build-iphone.yml"
            or run.get("event") not in {"pull_request", "workflow_dispatch"}
            or run.get("repository", {}).get("full_name") != repository):
        raise ValueError("Candidate must come from a successful build-iphone workflow in this repository.")
    candidate = json.loads((args.directory / "candidate.json").read_text())
    proof = candidate["build"]
    tree = subprocess.check_output(["git", "rev-parse", "HEAD^{tree}"], text=True).strip()
    expected = {"id": IPHONE_ID, "source_repository": repository,
                "source_commit": args.source_commit, "source_tree": tree,
                "build_run_id": int(args.run_id), "full_gate_passed": True,
                "patch_sha256": sha256(REPO_ROOT / "patches/iphone-layout.patch")}
    for key, value in expected.items():
        if proof.get(key) != value:
            raise ValueError(f"Candidate differs from the reviewed main tree: {key}")
    verify_files(args.directory, candidate["files"])
    print(f"Verified reviewed {IPHONE_ID} candidate from run {args.run_id}.")


if __name__ == "__main__":
    main()
