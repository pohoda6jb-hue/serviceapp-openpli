"""Package only statically verified candidates; mark receiver testing pending."""
import argparse
import hashlib
import io
import json
from pathlib import Path
import tarfile
import zipfile


def tar_bytes(files):
    stream = io.BytesIO()
    with tarfile.open(fileobj=stream, mode='w:gz') as archive:
        for name, data, mode in files:
            entry = tarfile.TarInfo('./' + name)
            entry.size, entry.mode, entry.uid, entry.gid, entry.mtime = len(data), mode, 0, 0, 0
            archive.addfile(entry, io.BytesIO(data))
    return stream.getvalue()


def ipk(path, control, files):
    data = tar_bytes(files)
    ctrl = tar_bytes([('control', control.encode(), 0o644)])
    with tarfile.open(path, 'w:gz') as archive:
        for name, content in [('debian-binary', b'2.0\n'), ('control.tar.gz', ctrl), ('data.tar.gz', data)]:
            entry = tarfile.TarInfo('./' + name)
            entry.size, entry.mode, entry.uid, entry.gid, entry.mtime = len(content), 0o644, 0, 0, 0
            archive.addfile(entry, io.BytesIO(content))


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('binaries', type=Path)
    parser.add_argument('output', type=Path)
    parser.add_argument('--commit', required=True)
    args = parser.parse_args()
    json.loads((args.binaries / 'static-abi.json').read_text())  # Gate packaging on audit.
    out = args.output
    out.mkdir(parents=True, exist_ok=True)
    common = ('Architecture: mips32el\nSection: multimedia\nPriority: optional\n'
              'Maintainer: ServiceApp port contributors\nLicense: GPL-2.0\n'
              'Homepage: https://github.com/pohoda6jb-hue/serviceapp-openpli\n')
    plugin = Path('src/plugin')
    prefix = 'usr/lib/enigma2/python/Plugins/SystemPlugins/ServiceApp/'
    files = [(prefix + name, (plugin / name).read_bytes(), 0o644)
             for name in ('__init__.py', 'plugin.py', 'serviceapp_client.py', 'streamsettings.py')]
    files.append((prefix + 'serviceapp.so', (args.binaries / 'serviceapp.so').read_bytes(), 0o755))
    ipk(out / 'enigma2-plugin-systemplugins-serviceapp_1+git179+vtilive-r0.1_mips32el.ipk',
        'Package: enigma2-plugin-systemplugins-serviceapp\nVersion: 1+git179+vtilive-r0.1\n'
        'Description: Experimental TS/HLS profiles and live recovery for VTi 15 Solo2\n'
        'Depends: enigma2 (= vti-15.0.04-20200921-r01r04), python-core, python-json, python-crypt, exteplayer3, uchardet, '
        'libsigc-1.2-5, libstdc++6 (>= 4.9.2), libc6 (>= 2.21), '
        'libssl1.0.0, libcrypto1.0.0\nRecommends: gstplayer\n' + common, files)
    ipk(out / 'exteplayer3_69+gitr136+e258b47-r0.vti1_mips32el.ipk',
        'Package: exteplayer3\nVersion: 69+gitr136+e258b47-r0.vti1\n'
        'Description: Legacy exteplayer3 with read-error events and explicit FFmpeg option preservation\n'
        'Depends: libc6 (>= 2.21), libgcc1, libavcodec57, libavformat57, libavutil55, libswresample2\n' + common,
        [('usr/bin/exteplayer3', (args.binaries / 'exteplayer3').read_bytes(), 0o755)])
    readme = '''TESTOVACI BALICEK: VU+ Solo2, VTi 15.0.04, Python 2.7, MIPS32EL.
Neinstalovat do ARM boxu ani OpenPLi. Přehrávání na skutečné Solo2 zatím není ověřeno.

Zálohu nastavení a původních balíčků proveď před instalací. Balíček nemění FFmpeg 3.4.1.
Přenes oba IPK do /tmp, potom nejprve doplň závislosti z vlastního VTi feedu:
opkg update
opkg install uchardet python-json python-crypt gstplayer
opkg install /tmp/exteplayer3_69+gitr136+e258b47-r0.vti1_mips32el.ipk /tmp/enigma2-plugin-systemplugins-serviceapp_1+git179+vtilive-r0.1_mips32el.ipk
Nepoužívej --force-depends ani --force-architecture. Při chybě instalaci neopakuj s vynucením.
Restartuj GUI přes menu přijímače.

U IPTV kanálů typu 4097 nejprve v hlavním nastavení ServiceApp zvol:
Enigma2 playback system = serviceapp a Player = exteplayer3. Potvrď restart GUI.
Kanály typu 5002 používají exteplayer3 přes ServiceApp přímo.
Samotné uložení nastavení streamu nepřepne původní přehrávač Enigmy na ServiceApp.

Pro test streamu otevři Rozšíření -> ServiceApp: current stream:
Player = exteplayer3; profil Live TS nebo HLS; Live stream recovery = Live;
HLS Explorer = vypnuto / nativní HLS. Ulož a přepni pryč a zpět.
Recovery je standardně vypnuté, je pouze pro živé streamy a má konečný počet pokusů.
Testuj zvlášť TS/HLS, krátký/dlouhý výpadek, zapínání jiného kanálu a VOD bez recovery.

Zdroj ServiceApp: https://github.com/pohoda6jb-hue/serviceapp-openpli
Zdroj přehrávače: https://github.com/oe-mirrors/exteplayer3/tree/e258b47863fae1d74dbd1d707c948ae4232fea64
Patch přehrávače je ve zdrojích ServiceApp: CI/openpli/exteplayer3-live.patch.
'''
    (out / 'SOLO2-CTI-NEJDRIV.txt').write_text(readme, encoding='utf-8')
    metadata = {'commit': args.commit, 'status': 'experimental; hardware untested',
                'target': 'VTi 15.0.04 / Solo2 / MIPS32EL / Python 2.7',
                'compiler': (args.binaries / 'compiler.txt').read_text(),
                'static_abi': json.loads((args.binaries / 'static-abi.json').read_text())}
    (out / 'BUILD-INFO.json').write_text(json.dumps(metadata, indent=2) + '\n')
    hashes = [hashlib.sha256(p.read_bytes()).hexdigest() + '  ' + p.name
              for p in sorted(out.iterdir()) if p.is_file()]
    (out / 'SHA256SUMS').write_text('\n'.join(hashes) + '\n')
    with zipfile.ZipFile(out / 'ServiceApp-exteplayer3-Solo2-VTi15-test.zip', 'w', zipfile.ZIP_DEFLATED) as archive:
        for path in sorted(out.iterdir()):
            if path.is_file() and path.suffix != '.zip': archive.write(path, path.name)


if __name__ == '__main__': main()
