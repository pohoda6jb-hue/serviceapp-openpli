"""Inspect an official VTi 15.0.04 Solo2 package without executing its code.

This is a reference audit, not a ServiceApp build or receiver playback test.
Use --package for an already downloaded IPK, otherwise fetch the pinned IPK.
"""
import argparse
import hashlib
import io
import json
from pathlib import Path
import struct
import tarfile
from urllib.request import urlopen


FEED = ('https://vuplus-support.org/openembedded/2.0/vti/'
        '20200910_vti-15.0_04_Su4oophuraey/')
PACKAGE = 'enigma2_vti-15.0.04-20200921-r01r04_vusolo2.ipk'
SHA256 = '0fd669c37614d76ede7c1e8f966fbb8de89a5dddf66d8c297c5c513640f6f3b6'


def package_members(data):
    if data.startswith(b'!<arch>\n'):
        offset = 8
        while offset < len(data):
            header = data[offset:offset + 60]
            if len(header) != 60 or header[58:60] != b'`\n':
                raise ValueError('invalid ar header')
            size = int(header[48:58])
            if size < 0 or offset + 60 + size > len(data):
                raise ValueError('invalid ar member size')
            name = header[:16].decode('ascii').strip().rstrip('/')
            offset += 60
            yield name, data[offset:offset + size]
            offset += size + size % 2
    else:
        with tarfile.open(fileobj=io.BytesIO(data), mode='r:*') as archive:
            for entry in archive:
                if entry.isfile():
                    yield entry.name, archive.extractfile(entry).read()


def enigma_elf(package):
    for name, payload in package_members(package):
        if 'data.tar' not in name:
            continue
        with tarfile.open(fileobj=io.BytesIO(payload), mode='r:*') as archive:
            for entry in archive:
                if entry.isfile() and entry.name.lstrip('./') == 'usr/bin/enigma2':
                    return archive.extractfile(entry).read()
    raise ValueError('Enigma2 executable missing from pinned package')


def elf_symbols(data):
    if data[:7] != b'\x7fELF\x01\x01\x01':
        raise ValueError('expected ELF32 little endian')
    header = struct.unpack_from('<HHIIIIIHHHHHH', data, 16)
    if header[1] != 8:
        raise ValueError('expected MIPS machine')
    flags = header[6]
    if flags & 0xf0000000 != 0x50000000 or flags & 0xf000 != 0x1000:
        raise ValueError('expected MIPS32 O32 ABI')
    offset, size, count = header[5], header[10], header[11]
    sections = [struct.unpack_from('<IIIIIIIIII', data, offset + i * size)
                for i in range(count)]
    symbols = {}
    for section in sections:
        if section[1] != 11:  # SHT_DYNSYM: exported/runtime symbols only.
            continue
        strings = sections[section[6]]
        names = data[strings[4]:strings[4] + strings[5]]
        for position in range(section[4], section[4] + section[5], section[9]):
            name, address, length, info, other, index = struct.unpack_from(
                '<IIIBBH', data, position)
            if not index:
                continue
            end = names.find(b'\0', name)
            symbol = names[name:end].decode('ascii')
            symbols[symbol] = {'size': length, 'address': address}
    return flags, symbols


def audit(package):
    digest = hashlib.sha256(package).hexdigest()
    if digest != SHA256:
        raise ValueError('pinned IPK SHA256 mismatch; refusing a different reference')
    flags, symbols = elf_symbols(enigma_elf(package))
    tables = {
        'iPlayableService': 104,
        'iStaticServiceInformation': 60,
        'iServiceInformation': 52,
        'iStreamedService': 32,
        'eTimer': 24,
        'eConnection': 24,
    }
    for name, expected in tables.items():
        symbol = '_ZTV%d%s' % (len(name), name)
        if symbols[symbol]['size'] != expected:
            raise ValueError('unexpected reference vtable size: ' + name)
    required = {
        'eServiceMP3::setTarget(int)': '_ZN11eServiceMP39setTargetEi',
        'iServiceInformation::getInfoObject(int)':
            '_ZN19iServiceInformation13getInfoObjectEi',
        'iStaticServiceInformation::getInfoObject(reference,int)':
            '_ZN25iStaticServiceInformation13getInfoObjectERK17eServiceReferencei',
        'eTimer::start(long,bool)': '_ZN6eTimer5startElb',
        'eTimer::startLongTimer(int)': '_ZN6eTimer14startLongTimerEi',
        'eConnection::AddRef()': '_ZN11eConnection6AddRefEv',
        'eConnection::Release()': '_ZN11eConnection7ReleaseEv',
    }
    for symbol in required.values():
        if symbol not in symbols:
            raise ValueError('required reference export missing: ' + symbol)
    return {
        'scope': 'official reference inspection; NOT a port build/playback test',
        'source_url': FEED + 'vusolo2/' + PACKAGE,
        'package_sha256': digest,
        'reference_version': 'vti-15.0.04-20200921-r01r04',
        'architecture': 'ELF32 little-endian MIPS32 O32',
        'elf_flags': hex(flags),
        'vtable_sizes_bytes': tables,
        'confirmed_exports': list(required),
        'limitations': [
            'Feed version does not prove the exact installed Enigma2 version.',
            'Vtable sizes alone do not prove method order or object field layout.',
            'No target IPK or receiver compatibility is certified by this audit.',
        ],
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--package', type=Path)
    parser.add_argument('--output', type=Path)
    args = parser.parse_args()
    if args.package:
        package = args.package.read_bytes()
    else:
        with urlopen(FEED + 'vusolo2/' + PACKAGE, timeout=30) as response:
            package = response.read(2 * 1024 * 1024 + 1)
    report = json.dumps(audit(package), indent=2) + '\n'
    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(report, encoding='utf-8')
    print(report, end='')


if __name__ == '__main__':
    main()
