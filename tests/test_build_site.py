"""Synthetic checks for the download/extraction boundary; no user media or network."""
import importlib.util
from pathlib import Path
import stat
import tempfile
import unittest
from unittest.mock import patch
import zipfile

SCRIPT = Path(__file__).resolve().parents[1] / "scripts" / "build_site.py"
SPEC = importlib.util.spec_from_file_location("build_site", SCRIPT)
builder = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(builder)


class BuildTests(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory()
        self.addCleanup(self.temporary.cleanup)
        self.directory = Path(self.temporary.name)
        self.archive = self.directory / "fixture.zip"
        self.output = self.directory / "site"

    def fixture(self, extra=None, omit=None):
        with zipfile.ZipFile(self.archive, "w") as archive:
            for name in sorted(builder.REQUIRED_FILES | {"OFL-synthetic.txt"}):
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


if __name__ == "__main__":
    unittest.main()
