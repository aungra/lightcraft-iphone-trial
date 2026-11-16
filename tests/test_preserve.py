"""The previously published revision is immutable across later deployments."""
import hashlib
import io
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch
import sys
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'scripts'))
import build_site as builder

class PreserveTests(unittest.TestCase):
    def test_existing_revision_preserved_or_tampering_rejected(self):
        for tampered in (False, True):
            with self.subTest(tampered=tampered), tempfile.TemporaryDirectory() as tmp:
                root = Path(tmp)
                repo = root / 'repo'
                (repo / 'releases').mkdir(parents=True)
                stage = root / 'stage'
                stage.mkdir()
                payload = b'original published bytes'
                manifest = {name: {'bytes': len(payload), 'sha256': hashlib.sha256(payload).hexdigest()}
                            for name in builder.REQUIRED_FILES}
                (repo / 'releases/iphone-r1-files.json').write_text(json.dumps(manifest))
                with patch.object(builder, 'REPO_ROOT', repo), patch.object(builder.urllib.request, 'urlopen',
                       side_effect=lambda *a, **kw: io.BytesIO(b'x' * len(payload) if tampered else payload)):
                    if tampered:
                        with self.assertRaisesRegex(ValueError, 'has changed'):
                            builder.preserve_r1(stage)
                    else:
                        builder.preserve_r1(stage)
                        self.assertEqual(builder.file_manifest(stage / 'iphone-r1'), manifest)
