"""Audit the receiver IPKs and create a downloadable test bundle."""
import argparse
import hashlib
import io
import json
from pathlib import Path
import tarfile
import zipfile


def members(data):
    if data.startswith(b'!<arch>\n'):
        offset = 8
        while offset < len(data):
            header = data[offset:offset + 60]
            if len(header) != 60 or header[58:60] != b'`\n':
                raise ValueError('Invalid IPK archive')
            size = int(header[48:58])
            start = offset + 60
            if start + size > len(data):
                raise ValueError('Truncated IPK archive')
            yield header[:16].decode('ascii').strip().rstrip('/'), data[start:start + size]
            offset = start + size + size % 2
    else:
        with tarfile.open(fileobj=io.BytesIO(data), mode='r:*') as archive:
            for member in archive:
                if member.isfile():
                    name = member.name[2:] if member.name.startswith('./') else member.name
                    yield name, archive.extractfile(member).read()


def audit(path):
    result = {'filename': path.name, 'elf': {}}
    for name, data in members(path.read_bytes()):
        if not (name.startswith('control.tar') or name.startswith('data.tar')):
            continue
        with tarfile.open(fileobj=io.BytesIO(data), mode='r:*') as archive:
            for member in archive:
                if not member.isfile():
                    continue
                payload = archive.extractfile(member).read()
                filename = member.name[2:] if member.name.startswith('./') else member.name
                if Path(filename).is_absolute() or '..' in Path(filename).parts:
                    raise ValueError('Unsafe install path')
                if name.startswith('control.tar') and filename == 'control':
                    result['control'] = dict(line.split(': ', 1) for line in payload.decode().splitlines()
                                             if ': ' in line and not line.startswith(' '))
                elif name.startswith('data.tar'):
                    result.setdefault('files', []).append(filename)
                    if payload.startswith(b'\x7fELF'):
                        if payload[4:6] != b'\x01\x01' or int.from_bytes(payload[18:20], 'little') != 40:
                            raise ValueError('Expected little-endian 32-bit ARM ELF: ' + filename)
                        flags = int.from_bytes(payload[36:40], 'little')
                        if flags & 0xff000000 != 0x05000000 or not flags & 0x400:
                            raise ValueError('Expected ARM EABI5 hard-float: ' + filename)
                        result['elf'][filename] = hex(flags)
                        if filename.endswith('/serviceapp.so'):
                            result['bundled_player'] = b'exteplayer3-serviceapp\0' in payload
    if 'control' not in result:
        raise ValueError('Missing package control: ' + path.name)
    return result


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('machine', choices=['vuzero4k', 'vuduo4k', 'sf8008'])
    parser.add_argument('directory', type=Path)
    args = parser.parse_args()
    folder = args.directory
    packages = [audit(p) for p in sorted(folder.glob('*.ipk'))]
    names = {p['control']['Package']: p for p in packages}
    companion = args.machine in ('vuzero4k', 'vuduo4k')
    player = 'exteplayer3-serviceapp' if companion else 'exteplayer3'
    plugin_name = 'enigma2-plugin-systemplugins-serviceapp'
    if len(packages) != 2 or set(names) != {plugin_name, player}:
        raise ValueError('Bundle requires exactly the plugin and its player: ' + repr(set(names)))
    if names[plugin_name]['control']['Architecture'] != args.machine:
        raise ValueError('Wrong receiver-specific plugin package')
    allowed = {'all', 'any', 'noarch', 'armv5hf-vfp', 'armv5ehf-vfp', 'armv6hf-vfp',
               'armv7ahf-vfp', 'armv7ahf-neon', args.machine}
    if args.machine == 'sf8008':
        allowed |= {'armv7vehf-vfp', 'armv7vehf-neon', 'armv7vehf-neon-vfpv4',
                    'cortexa15hf-vfp', 'cortexa15hf-neon', 'cortexa15hf-neon-vfpv4'}
    elif args.machine == 'vuzero4k':
        # The pinned meta-vuplus vuxxo4k.inc sets DEFAULTTUNE=armv7ahf-neon.
        allowed = {'armv7ahf-neon', 'vuzero4k'}
    if names[player]['control']['Architecture'] not in allowed:
        raise ValueError('Player architecture is incompatible with the target receiver')
    if not any(name.endswith('/serviceapp.so') for name in names[plugin_name]['elf']):
        raise ValueError('Native ServiceApp module missing')
    binary = 'usr/bin/' + player
    if set(names[player].get('files', [])) != {binary} or binary not in names[player]['elf']:
        raise ValueError('Unexpected player install paths')
    if companion:
        if not names[plugin_name].get('bundled_player'):
            raise ValueError('ServiceApp is not configured for its separate player')
        if player not in names[plugin_name]['control'].get('Depends', ''):
            raise ValueError('Separate player dependency is missing')
    (folder / 'PACKAGE-AUDIT.json').write_text(json.dumps(packages, indent=2) + '\n', encoding='utf-8')
    install = 'opkg install /tmp/' + names[player]['filename'] + ' /tmp/' + names[plugin_name]['filename']
    note = ('ServiceApp používá /usr/bin/exteplayer3-serviceapp. Původní exteplayer3 '
            'zůstává pro ostatní pluginy. '
            'Samostatný přehrávač vychází z ověřeného zdroje OpenPLi řady 69, '
            'nejde o úpravu zdroje původního přehrávače v přijímači.\n') if companion else ''
    readme = ('TESTOVACÍ BALÍČEK: OpenPLi 9.2 / ' + args.machine + ' / ARM / Python 3.9.\n'
              'Přehrávání na tomto přijímači zatím není ověřené.\n' + note +
              '\nObsahuje ServiceApp a upravený exteplayer3. Neobsahuje nový FFmpeg ani image.\n'
              'Před instalací si vytvoř zálohu nastavení a původního ServiceApp.\n'
              'Rozbal ZIP a oba soubory IPK přenes do /tmp přijímače. Potom spusť:\n'
              'opkg update\n' + install + '\n'
              'Při chybě nepoužívej --force-depends ani --force-architecture.\n'
              'Restartuj GUI přes menu přijímače.\n\n'
              'Pro kanály typu 4097 v hlavním nastavení ServiceApp zvol:\n'
              'Enigma2 playback system = serviceapp, Player = exteplayer3. Potvrď restart GUI.\n'
              'Typ 5002 používá exteplayer3 přes ServiceApp přímo.\n'
              'Uložení nastavení streamu samo nepřepne nativní přehrávač Enigmy.\n\n'
              'Rozšíření -> ServiceApp: current stream: Player = exteplayer3; profil Live TS nebo HLS;\n'
              'Live stream recovery = Live; HLS Explorer = Native player HLS. Ulož a přepni pryč a zpět.\n'
              'Volby platí pro konkrétní URL. Recovery je standardně vypnuté a má konečný počet pokusů.\n'
              'Obnovuje ukončený proces; zamrzlý přehrávač, který stále běží, tímto není pokryt.\n'
              'Vyzkoušej TS i HLS, krátký/dlouhý výpadek, přepnutí během obnovy a VOD bez opakování na konci.\n'
              '\nZdroj a podrobná omezení: https://github.com/pohoda6jb-hue/serviceapp-openpli/tree/feature/openpli-ts-hls-profiles\n')
    (folder / 'CTI-NEJDRIV.txt').write_text(readme, encoding='utf-8')
    files = [p for p in sorted(folder.iterdir()) if p.is_file() and p.suffix != '.zip' and p.name != 'SHA256SUMS']
    (folder / 'SHA256SUMS').write_text(''.join(hashlib.sha256(p.read_bytes()).hexdigest() + '  ' + p.name + '\n'
                                             for p in files), encoding='utf-8')
    with zipfile.ZipFile(folder / ('ServiceApp-exteplayer3-' + args.machine + '-OpenPLi92-test.zip'),
                         'w', zipfile.ZIP_DEFLATED) as archive:
        for path in files + [folder / 'SHA256SUMS']:
            archive.write(path, path.name)
    print('Receiver package audit and bundle complete:', args.machine)


if __name__ == '__main__':
    main()
