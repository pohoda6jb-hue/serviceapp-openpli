"""Fetch official VTi runtime libraries as data; never install/execute their IPKs."""
import argparse
import gzip
import hashlib
import io
import json
import re
import subprocess
from pathlib import Path
import tarfile
from urllib.request import urlopen
from audit_reference import FEED, PACKAGE, SHA256, package_members, enigma_elf

EXPECTED = {
    'libc6': '2.21-r0', 'libgcc1': '4.9.2-r0', 'libstdc++6': '4.9.2-r0',
    'libsigc-1.2-5': '1.2.5-r2', 'libpython2.7-1.0': '2.7.9-r1-vuplus1',
    'libssl1.0.0': '1.0.2a-r0', 'libcrypto1.0.0': '1.0.2a-r0',
    'uchardet': '0.0.6-r0', 'gstplayer': '0.1-r06',
    'libavcodec57': 'VTi001.3.4.1-r14', 'libavformat57': 'VTi001.3.4.1-r14',
    'libavutil55': 'VTi001.3.4.1-r14', 'libswresample2': 'VTi001.3.4.1-r14',
}


def fetch(url):
    with urlopen(url, timeout=60) as response:
        return response.read()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('destination', type=Path)
    args = parser.parse_args()
    root = args.destination
    libs, packages = root / 'lib', root / 'packages'
    libs.mkdir(parents=True, exist_ok=True)
    packages.mkdir(parents=True, exist_ok=True)
    index = gzip.decompress(fetch(FEED + 'mips32el/static/Packages.gz')).decode()
    entries = {}
    for block in index.replace('\r', '').split('\n\n'):
        fields = dict(line.split(': ', 1) for line in block.splitlines()
                      if ': ' in line and not line.startswith(' '))
        if 'Package' in fields:
            entries[fields['Package']] = fields
    manifest = []
    pending = list(EXPECTED)
    fetched = set()
    while pending:
        name = pending.pop(0)
        if name in fetched:
            continue
        fetched.add(name)
        entry = entries[name]
        version = entry['Version']
        if (name in EXPECTED and version != EXPECTED[name]) or entry['Architecture'] != 'mips32el':
            raise ValueError('unexpected official reference package: ' + name)
        # Linker inputs need the codec libraries' own dependencies too. GstPlayer
        # is only an optional offline install package; do not pull all GST plugins.
        if name != 'gstplayer':
            for dependency in entry.get('Depends', '').split(','):
                match = re.match(r'\s*([\w+.-]+)', dependency)
                if match:
                    dependency_name = match.group(1)
                    if dependency_name not in entries:
                        raise ValueError('missing runtime dependency: ' + dependency_name)
                    pending.append(dependency_name)
        filename = entry['Filename']
        if Path(filename).name != filename:
            raise ValueError('unsafe feed filename')
        url = FEED + 'mips32el/static/' + filename
        data = fetch(url)
        if hashlib.md5(data).hexdigest() != entry['MD5Sum']:
            raise ValueError('official feed checksum mismatch: ' + name)
        (packages / filename).write_bytes(data)
        manifest.append({'package': name, 'version': version, 'url': url,
                         'sha256': hashlib.sha256(data).hexdigest()})
        for archive_name, payload in package_members(data):
            if 'data.tar' not in archive_name:
                continue
            with tarfile.open(fileobj=io.BytesIO(payload), mode='r:*') as archive:
                for member in archive:
                    # Flatten only real ELF libraries; no symlinks or package scripts.
                    if not member.isfile() or '.debug/' in member.name:
                        continue
                    content = archive.extractfile(member).read()
                    if content[:4] != b'\x7fELF' or '.so' not in member.name:
                        continue
                    target = libs / Path(member.name).name
                    if target.exists() and target.read_bytes() != content:
                        raise ValueError('ambiguous reference library: ' + target.name)
                    target.write_bytes(content)
        print('Fetched and verified', name, version, flush=True)
    data = fetch(FEED + 'vusolo2/' + PACKAGE)
    if hashlib.sha256(data).hexdigest() != SHA256:
        raise ValueError('Enigma reference changed')
    (root / 'enigma2').write_bytes(enigma_elf(data))
    for library in sorted(libs.iterdir()):
        # Debian/Vu+ glibc files use names such as libpthread-2.21.so.
        # Resolve both compiler and loader names from the ELF's actual SONAME.
        output = subprocess.check_output(['readelf', '-d', str(library)], text=True)
        match = re.search(r'\(SONAME\).*\[([^\]]+)\]', output)
        if not match:
            continue
        soname = match.group(1)
        if Path(soname).name != soname or '.so' not in soname:
            raise ValueError('unsafe runtime SONAME: ' + soname)
        for name in (soname, soname.partition('.so')[0] + '.so'):
            link = libs / name
            if link == library:
                continue
            if link.exists():
                if link.resolve() != library.resolve():
                    raise ValueError('ambiguous runtime SONAME: ' + name)
            else:
                link.symlink_to(library.name)
    (root / 'manifest.json').write_text(json.dumps(manifest, indent=2) + '\n')


if __name__ == '__main__':
    main()
