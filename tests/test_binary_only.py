"""Exercise the NAS updater with independent local release/upstream fixtures."""
import hashlib
import io
import json
import lzma
import os
import shlex
import shutil
import subprocess
import sys
import tarfile
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


@unittest.skipUnless(sys.platform == 'linux' and shutil.which('cc'), 'Linux NAS/CI test')
class BinaryOnlyTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.app = self.root / 'app'
        self.bin = self.app / 'bin/program'
        self.bin.mkdir(parents=True)
        current = self.bin / 'tailscale'
        current.write_text("#!/bin/sh\nprintf '1.0.0\\n'\n")
        current.chmod(0o755)
        self.marker = self.root / 'malicious-script-ran'
        self.state = self.root / 'state'
        source = self.root / 'version.c'
        source.write_text('#include <stdio.h>\nint main(void) { puts("9.0.0"); return 0; }\n')
        binary = self.root / 'official'
        subprocess.run(['cc', str(source), '-o', str(binary)], check=True)
        self.official = binary.read_bytes()
        self.packaged = self.official[:8] + b'TOS' + self.official[11:]
        self.updater = self.root / 'updater.sh'
        # Only adapt root requirement and HTTP transport; exercise real validation.
        script = (ROOT / 'scripts/tnas-update.sh').read_text()
        script = script.replace('$(id -u)', '0')
        script = script.replace('CURL=$(command -v ter_curl || command -v curl)',
                                'CURL=' + shlex.quote(str(self.root / 'curl')))
        self.updater.write_text(script)
        self.make_upstream()
        (self.root / 'release.json').write_text('{"tag_name":"v9.0.0"}')
        curl = self.root / 'curl'
        curl.write_text('''#!/usr/bin/env python3
import pathlib,sys
root=pathlib.Path(__file__).parent
args=sys.argv[1:]
url=next(a for a in args if a.startswith('https://'))
if '/api.github.com/' in url: name='release.json'
elif url.endswith('/SHA256SUMS'): name='SHA256SUMS'
elif url.endswith('.tpk'): name='package.tpk'
elif url.endswith('.sha256'): name='upstream.sha256'
else: name='upstream.tgz'
data=(root/name).read_bytes()
if '-o' in args: pathlib.Path(args[args.index('-o')+1]).write_bytes(data)
else: sys.stdout.buffer.write(data)
''')
        curl.chmod(0o755)

    def archive(self, members: dict[str, bytes], mode: str) -> bytes:
        result = io.BytesIO()
        with tarfile.open(fileobj=result, mode=mode) as archive:
            for name, data in members.items():
                info = tarfile.TarInfo(name)
                info.size = len(data)
                info.mode = 0o755
                archive.addfile(info, io.BytesIO(data))
        return result.getvalue()

    def make_upstream(self) -> None:
        content = self.archive({f'tailscale_9.0.0_amd64/{name}': self.official
                                for name in ('tailscale', 'tailscaled')}, 'w:gz')
        (self.root / 'upstream.tgz').write_bytes(content)
        (self.root / 'upstream.sha256').write_text(hashlib.sha256(content).hexdigest())

    def make_package(self, binary: bytes) -> None:
        payload = lzma.compress(self.archive({
            'bin/program/tailscale': binary,
            'bin/program/tailscaled': self.packaged,
            'init.d/service': f'#!/bin/sh\ntouch {self.marker}\n'.encode(),
            'webui/api.php': b'<?php system("untrusted command");',
        }, 'w'))
        header = json.dumps({'id': 'Tailscale', 'platform': 'x86_64',
                             'version': '9.0.0.0', 'md5': hashlib.md5(payload).hexdigest()})
        package = header.encode().ljust(2048, b' ') + bytes(8192) + payload
        (self.root / 'package.tpk').write_bytes(package)
        (self.root / 'SHA256SUMS').write_text(hashlib.sha256(package).hexdigest()
                                            + '  tailscale-tos5-x86_64.tpk\n')

    def run_updater(self) -> subprocess.CompletedProcess[str]:
        return subprocess.run(['bash', str(self.updater), '--download-only'],
                              env={**os.environ, 'TAILSCALE_REPO': 'example/packages',
                                   'TAILSCALE_APP': str(self.app),
                                   'TAILSCALE_UPDATE_DIR': str(self.state)},
                              capture_output=True, text=True, timeout=30)

    def test_repository_checksum_cannot_authorize_modified_binary(self) -> None:
        self.make_package(self.packaged + b'rogue-publisher-change')
        result = self.run_updater()
        self.assertNotEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertIn('differs from official upstream', result.stdout)
        self.assertFalse(self.marker.exists())
        self.assertEqual((self.bin / 'tailscale').read_text(), "#!/bin/sh\nprintf '1.0.0\\n'\n")

    def test_matching_binaries_validate_without_installing_package_scripts(self) -> None:
        self.make_package(self.packaged)
        result = self.run_updater()
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertIn('all other package files ignored', result.stdout)
        self.assertFalse(self.marker.exists())
        self.assertFalse((self.app / 'init.d').exists())
        self.assertTrue((self.state / 'downloads/Tailscale-9.0.0.tpk').exists())
