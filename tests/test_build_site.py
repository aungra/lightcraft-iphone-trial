"""Synthetic checks for the download/extraction boundary; no user media or network."""
import importlib.util
import json
from pathlib import Path
import stat
import sys
import tempfile
import unittest
from unittest.mock import patch
import zipfile

SCRIPT = Path(__file__).resolve().parents[1] / "scripts" / "build_site.py"
SPEC = importlib.util.spec_from_file_location("build_site", SCRIPT)
builder = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(builder)
sys.path.insert(0, str(SCRIPT.parent))
from record_candidate import validate_gate
from verify_candidate import verify_files


class BuildTests(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory()
        self.addCleanup(self.temporary.cleanup)
        self.directory = Path(self.temporary.name)
        self.archive = self.directory / "fixture.zip"
        self.output = self.directory / "site"

    def fixture(self, extra=None, omit=None):
        with zipfile.ZipFile(self.archive, "w") as archive:
            for name in sorted(builder.REQUIRED_FILES | {"OFL-synthetic.txt", "README.md"}):
                if name != omit:
                    archive.writestr(f"{builder.ARCHIVE_ROOT}/{name}", f"synthetic content: {name}\n")
            if extra:
                archive.writestr(*extra)
        self.enterContext(patch.object(builder, "ARCHIVE_BYTES", self.archive.stat().st_size))
        self.enterContext(patch.object(builder, "ARCHIVE_SHA256", builder.sha256(self.archive)))

    def test_verified_files_preserved_and_existing_output_refused(self):
        self.fixture()
        builder.build_site(self.archive, self.output)
        with zipfile.ZipFile(self.archive) as archive:
            for item in archive.infolist():
                relative = Path(*Path(item.filename).parts[1:])
                self.assertEqual(archive.read(item), (self.output / f"v{builder.VERSION}" / relative).read_bytes())
        self.assertTrue((self.output / "deployment.json").is_file())
        with self.assertRaises(FileExistsError):
            builder.build_site(self.archive, self.output)

    def test_hash_mismatch_does_not_create_output(self):
        self.fixture()
        contents = bytearray(self.archive.read_bytes())
        contents[20] ^= 1
        self.archive.write_bytes(contents)
        with self.assertRaisesRegex(ValueError, "SHA-256"):
            builder.build_site(self.archive, self.output)
        self.assertFalse(self.output.exists())

    def test_path_traversal_does_not_escape_or_publish(self):
        self.fixture(extra=(f"{builder.ARCHIVE_ROOT}/../../escaped", "bad"))
        with self.assertRaisesRegex(ValueError, "Unsafe archive path"):
            builder.build_site(self.archive, self.output)
        self.assertFalse((self.directory / "escaped").exists())
        self.assertFalse(self.output.exists())

    def test_symlink_refused(self):
        link = zipfile.ZipInfo(f"{builder.ARCHIVE_ROOT}/linked")
        link.create_system = 3
        link.external_attr = (stat.S_IFLNK | 0o777) << 16
        self.fixture(extra=(link, "../../elsewhere"))
        with self.assertRaisesRegex(ValueError, "Unsupported archive entry"):
            builder.build_site(self.archive, self.output)
        self.assertFalse(self.output.exists())

    def test_missing_license_does_not_publish(self):
        self.fixture(omit="NOTICE")
        with self.assertRaisesRegex(ValueError, "license files missing"):
            builder.build_site(self.archive, self.output)
        self.assertFalse(self.output.exists())

    def candidate_fixture(self, gate=True):
        self.fixture()
        repository = self.directory / "repo"
        (repository / "patches").mkdir(parents=True)
        (repository / "site").mkdir()
        (repository / "site/index.html").write_text("<a href='iphone-r1/'>Trial</a>")
        (repository / "patches/iphone-layout.patch").write_text("synthetic reviewed patch")
        self.enterContext(patch.object(builder, "REPO_ROOT", repository))
        modified = self.directory / "modified.zip"
        with zipfile.ZipFile(modified, "w") as archive:
            for name in builder.REQUIRED_FILES | {"OFL-synthetic.txt"}:
                archive.writestr(f"lightcraft-web-{builder.VERSION}-{builder.IPHONE_ID}/{name}", f"modified {name}")
        proof = {"id": builder.IPHONE_ID, "upstream_commit": builder.SOURCE_COMMIT,
                 "fonts_commit": builder.FONTS_COMMIT, "rust_version": builder.RUST_VERSION,
                 "full_gate_passed": gate, "modified_build": True,
                 "archive_sha256": builder.sha256(modified),
                 "patch_sha256": builder.sha256(repository / "patches/iphone-layout.patch")}
        proof_path = self.directory / "proof.json"
        proof_path.write_text(json.dumps(proof))
        return modified, proof_path

    def test_candidate_preserves_official_and_detects_changed_files(self):
        modified, proof = self.candidate_fixture()
        builder.build_site(self.archive, self.output, modified, proof)
        with zipfile.ZipFile(self.archive) as archive:
            for item in archive.infolist():
                relative = Path(*Path(item.filename).parts[1:])
                self.assertEqual(archive.read(item), (self.output / f"v{builder.VERSION}" / relative).read_bytes())
        candidate = json.loads((self.output / "candidate.json").read_text())
        modified_readme = (self.output / "iphone-r1/README.md").read_text()
        self.assertIn("unofficial modified build", modified_readme)
        self.assertIn("browser-compatible timing fix", modified_readme)
        self.assertNotIn("<img", modified_readme.lower())
        self.assertNotIn("docs/brand/", modified_readme)
        self.assertEqual((self.output / "v0.21.1/README.md").read_text(), "synthetic content: README.md\n")
        verify_files(self.output, candidate["files"])
        (self.output / "iphone-r1/index.html").write_text("changed after review")
        with self.assertRaisesRegex(ValueError, "hashes differ"):
            verify_files(self.output, candidate["files"])

    def test_candidate_without_successful_gate_is_not_published(self):
        modified, proof = self.candidate_fixture(gate=False)
        with self.assertRaisesRegex(ValueError, "full_gate_passed"):
            builder.build_site(self.archive, self.output, modified, proof)
        self.assertFalse(self.output.exists())

    def test_partial_or_quick_gate_rejected(self):
        with self.assertRaises(ValueError):
            validate_gate({"result": "pass", "quick": None, "steps": [{"name": "fmt", "status": "ok"}]})
        with self.assertRaises(ValueError):
            validate_gate({"result": "pass", "quick": {"base": "main"}, "steps": []})

    def test_complete_gate_accepted(self):
        validate_gate({"result": "pass", "quick": None, "steps": [
            {"name": name, "status": "ok"} for name in
            ["fmt", "clippy", "heif", "test", "parity", "layers", "assets", "roots", "wasm"]]})


if __name__ == "__main__":
    unittest.main()
