#!/usr/bin/env python3
"""Keep the official release intact, optionally adding a tested iPhone build."""

import argparse
import hashlib
import json
from pathlib import Path, PurePosixPath
import shutil
import stat
import sys
import tempfile
import urllib.request
import zipfile

VERSION = "0.21.1"
ARCHIVE_NAME = f"lightcraft-web-{VERSION}.zip"
ARCHIVE_ROOT = f"lightcraft-web-{VERSION}"
ARCHIVE_URL = (
    "https://github.com/storytold/lightcraft/releases/download/"
    f"v{VERSION}/{ARCHIVE_NAME}"
)
ARCHIVE_SHA256 = "57147383a46eaab3b0cc036acf9443b221450c6a19f5dc303ae165bb9678b8cb"
ARCHIVE_BYTES = 74_569_049
SOURCE_COMMIT = "361e3bc0c838ffe5e5cea515b1fe5b71951989c6"
PUBLIC_URL = "https://lightcraft.aun-graphic.jp/v0.21.1/?workers=1"
MAX_UNPACKED_BYTES = 128 * 1024 * 1024
MAX_ENTRIES = 128
REQUIRED_FILES = {
    "index.html", "lightcraft_web.js", "lightcraft_web_bg.wasm", "worker.js",
    "LICENSE-MIT", "LICENSE-APACHE", "NOTICE", "HOSTING.md",
}
REPO_ROOT = Path(__file__).resolve().parent.parent
IPHONE_ID = "iphone-r1"
FONTS_COMMIT = "b076417b5880bd4154bd22f00695b1d28c6bea83"
RUST_VERSION = "1.100.0"


def sha256(path):
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def verify_archive(path):
    if not path.is_file() or path.stat().st_size != ARCHIVE_BYTES:
        raise ValueError("Official archive size mismatch; no site was published.")
    if sha256(path) != ARCHIVE_SHA256:
        raise ValueError("Official archive SHA-256 mismatch; no site was published.")


def get_archive(cache):
    cache.mkdir(parents=True, exist_ok=True)
    archive = cache / ARCHIVE_NAME
    if archive.exists():
        verify_archive(archive)
        return archive
    # A new temporary file prevents a partial download being accepted on a later run.
    with tempfile.NamedTemporaryFile(dir=cache, prefix="download-", suffix=".part", delete=False) as output:
        temporary = Path(output.name)
        try:
            request = urllib.request.Request(ARCHIVE_URL, headers={"User-Agent": "lightcraft-iphone-trial/1"})
            with urllib.request.urlopen(request, timeout=60) as response:
                count = 0
                while chunk := response.read(1024 * 1024):
                    count += len(chunk)
                    if count > ARCHIVE_BYTES:
                        raise ValueError("Download exceeds pinned archive size.")
                    output.write(chunk)
            output.flush()
            verify_archive(temporary)
            if archive.exists():
                raise FileExistsError(f"Archive appeared during download: {archive}")
            temporary.rename(archive)
        finally:
            temporary.unlink(missing_ok=True)
    return archive


def checked_members(archive, expected_root=ARCHIVE_ROOT):
    """Validate the whole ZIP before extraction; never follow links or escape its root."""
    entries = archive.infolist()
    if len(entries) > MAX_ENTRIES or sum(item.file_size for item in entries) > MAX_UNPACKED_BYTES:
        raise ValueError("Archive exceeds the reviewed release limits.")
    seen = set()
    members = []
    for item in entries:
        name = item.filename
        path = PurePosixPath(name)
        if ("\\" in name or path.is_absolute() or ".." in path.parts
                or not path.parts or path.parts[0] != expected_root):
            raise ValueError(f"Unsafe archive path: {name!r}")
        mode = item.external_attr >> 16
        kind = stat.S_IFMT(mode)
        if kind not in (0, stat.S_IFREG, stat.S_IFDIR):
            raise ValueError(f"Unsupported archive entry: {name!r}")
        if item.flag_bits & 1:
            raise ValueError("Encrypted archive entries are unsupported.")
        relative = Path(*path.parts[1:])
        normalized = relative.as_posix()
        if normalized in seen:
            raise ValueError(f"Duplicate archive entry: {name!r}")
        seen.add(normalized)
        if not item.is_dir() and not path.parts[1:]:
            raise ValueError("Expected an enclosing archive directory.")
        members.append((item, relative))
    return members


def unpack(archive_path, destination, expected_root):
    destination.mkdir(parents=True)
    with zipfile.ZipFile(archive_path) as archive:
        for item, relative in checked_members(archive, expected_root):
            target = destination / relative
            if item.is_dir():
                target.mkdir(parents=True, exist_ok=True)
            else:
                target.parent.mkdir(parents=True, exist_ok=True)
                with archive.open(item) as source, target.open("xb") as output:
                    shutil.copyfileobj(source, output, 1024 * 1024)
    missing = sorted(name for name in REQUIRED_FILES if not (destination / name).is_file())
    if missing:
        raise ValueError(f"Required application/license files missing: {missing}")
    if not list(destination.glob("OFL-*.txt")):
        raise ValueError("Font license files missing.")


def file_manifest(directory):
    files = {}
    for path in sorted(directory.rglob("*")):
        if path.is_symlink():
            raise ValueError(f"Symlinks are not allowed in a published site: {path}")
        if path.is_file():
            files[path.relative_to(directory).as_posix()] = {"bytes": path.stat().st_size, "sha256": sha256(path)}
    return files


def add_iphone_build(stage, archive, proof_path):
    proof = json.loads(proof_path.read_text(encoding="utf-8"))
    required = {
        "id": IPHONE_ID, "upstream_commit": SOURCE_COMMIT,
        "fonts_commit": FONTS_COMMIT, "rust_version": RUST_VERSION,
        "full_gate_passed": True, "modified_build": True,
    }
    for key, expected in required.items():
        if proof.get(key) != expected:
            raise ValueError(f"Candidate provenance mismatch: {key}")
    if proof.get("archive_sha256") != sha256(archive):
        raise ValueError("Candidate archive SHA-256 mismatch.")
    patch = REPO_ROOT / "patches" / "iphone-layout.patch"
    if proof.get("patch_sha256") != sha256(patch):
        raise ValueError("Candidate patch SHA-256 mismatch.")
    app = stage / IPHONE_ID
    unpack(archive, app, f"lightcraft-web-{VERSION}-{IPHONE_ID}")
    shutil.copyfile(patch, app / "iphone-layout.patch")
    # Upstream README includes official brand artwork and product claims. The fork
    # gets its own plain-text introduction; the official version remains untouched.
    (app / "README.md").write_text(
        "# Unofficial iPhone layout trial\n\n"
        f"Revision: {IPHONE_ID}, based on LightCraft v{VERSION}.\n\n"
        "This is an unofficial modified build, not an official ArtCraft product.\n"
        "LightCraft is made by the ArtCraft Team and its contributors; this trial is not\n"
        "made, endorsed, certified or supported by that team.\n\n"
        "Changes: compact portrait menus and editing panels, Safari visible-viewport\n"
        "handling, and a browser-compatible timing fix in the image loader.\n"
        "See iphone-layout.patch, MODIFICATIONS.txt and build-provenance.json for the\n"
        "exact changes and pinned inputs. iPhone runtime acceptance is separate from CI.\n\n"
        "Upstream source: https://github.com/storytold/lightcraft/tree/v0.21.1\n"
        "Upstream web documentation: https://github.com/storytold/lightcraft/blob/v0.21.1/docs/web.md\n\n"
        "LICENSE-MIT, LICENSE-APACHE, NOTICE and the bundled OFL font licenses are retained.\n"
        "Keep original photos and use File > Back Up Library before changing versions.\n",
        encoding="utf-8",
    )
    (app / "MODIFICATIONS.txt").write_text(
        "Unofficial modified build based on LightCraft v0.21.1.\n"
        "iPhone portrait layout and browser image-loader timing changes; see iphone-layout.patch and build-provenance.json.\n"
        "This build is not made, endorsed or supported by the ArtCraft Team.\n",
        encoding="utf-8",
    )
    (app / "build-provenance.json").write_text(json.dumps(proof, indent=2) + "\n", encoding="utf-8")
    return proof


def build_site(archive_path, destination, patched_archive=None, provenance=None):
    if destination.exists() or destination.is_symlink():
        raise FileExistsError(f"Refusing to overwrite existing output: {destination}")
    destination.parent.mkdir(parents=True, exist_ok=True)
    verify_archive(archive_path)
    with tempfile.TemporaryDirectory(prefix=".lightcraft-build-", dir=destination.parent) as staging:
        stage = Path(staging) / "site"
        app = stage / f"v{VERSION}"
        unpack(archive_path, app, ARCHIVE_ROOT)
        for relative in file_manifest(REPO_ROOT / "site"):
            source = REPO_ROOT / "site" / relative
            if source.suffix not in {".html", ".css", ".js", ".txt"}:
                raise ValueError(f"Unexpected landing-page file type: {relative}")
            target = stage / relative
            if target.exists():
                raise ValueError(f"Landing files must not replace application files: {relative}")
            target.parent.mkdir(parents=True, exist_ok=True)
            shutil.copyfile(source, target)
        (stage / ".nojekyll").touch()
        manifest = {
            "version": VERSION,
            "source_commit": SOURCE_COMMIT,
            "archive_url": ARCHIVE_URL,
            "archive_sha256": ARCHIVE_SHA256,
            "archive_bytes": ARCHIVE_BYTES,
            "app_files_unmodified": True,
            "suggested_entry_url": PUBLIC_URL,
            "files": file_manifest(app),
        }
        (stage / "deployment.json").write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")
        if patched_archive:
            proof = add_iphone_build(stage, patched_archive, provenance)
            candidate = {"build": proof, "files": file_manifest(stage)}
            (stage / "candidate.json").write_text(json.dumps(candidate, indent=2) + "\n", encoding="utf-8")
        stage.rename(destination)
    print(f"Verified official v{VERSION}; site ready: {destination}")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--archive", type=Path, help="Use an already-downloaded ZIP; exact official hash is still mandatory.")
    parser.add_argument("--output", type=Path, default=REPO_ROOT / "_site", help="New output directory; existing output is never overwritten.")
    parser.add_argument("--patched-archive", type=Path, help="Freshly built iPhone package, alongside the preserved official release.")
    parser.add_argument("--provenance", type=Path, help="Successful full-gate/build provenance for --patched-archive.")
    args = parser.parse_args()
    if bool(args.patched_archive) != bool(args.provenance):
        parser.error("--patched-archive and --provenance must be supplied together.")
    destination = args.output.absolute()
    if destination.exists() or destination.is_symlink():
        parser.error(f"Output already exists: {destination}; use a fresh --output directory.")
    try:
        archive = args.archive or get_archive(REPO_ROOT / ".cache")
        build_site(archive, destination, args.patched_archive, args.provenance)
    except (OSError, ValueError, zipfile.BadZipFile) as error:
        print(f"Build stopped: {error}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
