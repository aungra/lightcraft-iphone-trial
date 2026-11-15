#!/usr/bin/env python3
"""Record build inputs only after the complete upstream gate has passed."""
import argparse
import json
import os
from pathlib import Path
import subprocess
import tomllib

from build_site import FONTS_COMMIT, IPHONE_ID, REPO_ROOT, RUST_VERSION, SOURCE_COMMIT, sha256


def git(path, revision):
    return subprocess.check_output(["git", "-C", str(path), "rev-parse", revision], text=True).strip()


def validate_gate(report):
    if report.get("result") != "pass" or report.get("quick") is not None:
        raise ValueError("A successful full cargo xtask ci report is required.")
    steps = {step["name"]: step["status"] for step in report.get("steps", [])}
    required = {"fmt", "clippy", "heif", "test", "parity", "layers", "assets", "roots", "wasm"}
    if any(steps.get(step) != "ok" for step in required):
        raise ValueError("Full upstream gate has missing or unsuccessful steps.")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source", required=True, type=Path)
    parser.add_argument("--fonts", required=True, type=Path)
    parser.add_argument("--archive", required=True, type=Path)
    parser.add_argument("--output", required=True, type=Path)
    args = parser.parse_args()
    report_path = args.source / "target/ci/report.json"
    report = json.loads(report_path.read_text())
    validate_gate(report)
    if git(args.source, "HEAD") != SOURCE_COMMIT or git(args.fonts, "HEAD") != FONTS_COMMIT:
        raise ValueError("Source/font checkout differs from the reviewed pins.")
    subprocess.run(["git", "-C", str(args.source), "diff", "--exit-code", "--", "Cargo.lock"], check=True)
    subprocess.run(["git", "-C", str(args.fonts), "diff", "--exit-code"], check=True)
    rust = subprocess.check_output(["rustc", "--version"], text=True).strip()
    if rust.split()[1] != RUST_VERSION:
        raise ValueError("Rust toolchain differs from the reviewed pin.")
    lock = tomllib.loads((args.source / "Cargo.lock").read_text())
    bindgen = next(p["version"] for p in lock["package"] if p["name"] == "wasm-bindgen")
    font_manifest = args.fonts / "fonts/manifest.txt"
    font_lines = [line.split(" | ") for line in font_manifest.read_text().splitlines()
                  if line.startswith("BIZ UDPGothic | Regular |")]
    if len(font_lines) != 1:
        raise ValueError("Pinned Japanese UI font is absent from the font manifest.")
    japanese_font = args.fonts / font_lines[0][2].strip()
    proof = {
        "id": IPHONE_ID,
        "source_repository": os.environ["GITHUB_REPOSITORY"],
        "source_commit": git(REPO_ROOT, "HEAD"),
        "source_tree": git(REPO_ROOT, "HEAD^{tree}"),
        "build_run_id": int(os.environ["GITHUB_RUN_ID"]),
        "build_run_attempt": int(os.environ["GITHUB_RUN_ATTEMPT"]),
        "upstream_commit": SOURCE_COMMIT,
        "fonts_commit": FONTS_COMMIT,
        "font_manifest_sha256": sha256(font_manifest),
        "japanese_font_sha256": sha256(japanese_font),
        "cargo_lock_sha256": sha256(args.source / "Cargo.lock"),
        "rust_version": RUST_VERSION,
        "rustc": rust,
        "wasm_bindgen_version": bindgen,
        "patch_sha256": sha256(REPO_ROOT / "patches/iphone-layout.patch"),
        "archive_sha256": sha256(args.archive),
        "full_gate_passed": True,
        "full_gate_report_sha256": sha256(report_path),
        "full_gate_skips": report.get("skips", []),
        "modified_build": True,
        "iphone_runtime_verified": False,
    }
    args.output.write_text(json.dumps(proof, indent=2) + "\n")


if __name__ == "__main__":
    main()
