import json
import os
import shutil
import subprocess
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


class UpdateScriptTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        shutil.copy(ROOT / 'update_tailscale.sh', self.root / 'update_tailscale.sh')
        (self.root / 'bin').mkdir()
        (self.root / 'src').mkdir()
        (self.root / 'src/version').write_text('1.92.1.0\n')
        curl = self.root / 'bin/curl'
        curl.write_text('''#!/bin/bash
case "$*" in
  *mode=json*) printf '{"TarballsVersion":"1.102.4"}' ;;
  *.sha256*) printf '%064d' 0 ;;
  *) while [ "$#" -gt 0 ]; do
       if [ "$1" = -o ]; then printf 'not a valid tarball' > "$2"; exit 0; fi
       shift
     done ;;
esac
''')
        curl.chmod(0o755)
        self.env = {**os.environ, 'PATH': str(self.root / 'bin') + ':' + os.environ['PATH']}

    def test_invalid_version_does_not_change_source(self) -> None:
        result = subprocess.run(
            ['bash', str(self.root / 'update_tailscale.sh'), '1.2.3;echo injected'],
            env=self.env, capture_output=True, text=True,
        )
        self.assertNotEqual(result.returncode, 0)
        self.assertIn('Version must be X.Y.Z', result.stderr)
        self.assertEqual((self.root / 'src/version').read_text(), '1.92.1.0\n')

    def test_corrupt_upstream_download_rejected_before_extraction(self) -> None:
        result = subprocess.run(
            ['bash', str(self.root / 'update_tailscale.sh'), 'latest'],
            env=self.env, capture_output=True, text=True,
        )
        self.assertNotEqual(result.returncode, 0)
        self.assertIn('Official tarball SHA256 mismatch', result.stderr)
        self.assertEqual((self.root / 'src/version').read_text(), '1.92.1.0\n')
        self.assertFalse((self.root / 'src/bin').exists())

    def test_package_metadata_matches_version(self) -> None:
        self.assertEqual(json.loads((ROOT / 'src/config.ini').read_text())['version'],
                         (ROOT / 'src/version').read_text().strip())


if __name__ == '__main__':
    unittest.main()
