"""Fail closed on unsupported MIPS ABI or unresolved VTi runtime imports."""
import argparse
import json
import struct
from pathlib import Path
from elftools.elf.elffile import ELFFile


def inspect(path):
    with path.open('rb') as stream:
        elf = ELFFile(stream)
        if elf.elfclass != 32 or not elf.little_endian or elf.header.e_machine != 'EM_MIPS':
            raise ValueError('Not a 32-bit little-endian MIPS ELF: ' + str(path))
        needed, soname, interp = [], None, None
        abi_section = elf.get_section_by_name('.MIPS.abiflags')
        fp_abi = abi_section.data()[7] if abi_section else None
        dynamic = elf.get_section_by_name('.dynamic')
        if dynamic:
            for tag in dynamic.iter_tags():
                kind = tag.entry.d_tag
                if kind == 'DT_NEEDED': needed.append(tag.needed)
                elif kind == 'DT_SONAME': soname = tag.soname
        for segment in elf.iter_segments():
            if segment.header.p_type == 'PT_INTERP': interp = segment.get_interp_name()
        versions, defaults = {}, {}
        definitions = elf.get_section_by_name('.gnu.version_d')
        if definitions:
            for version, auxiliaries in definitions.iter_versions():
                versions[version.entry.vd_ndx] = next(auxiliaries).name
        requirements = {}
        section = elf.get_section_by_name('.gnu.version_r')
        if section:
            for dependency, auxiliaries in section.iter_versions():
                for entry in auxiliaries:
                    requirements[entry.entry.vna_other] = (dependency.name, entry.name)
        symbol_versions = elf.get_section_by_name('.gnu.version')
        exports, imports = {}, []
        symbols = elf.get_section_by_name('.dynsym')
        if symbols:
            for index, symbol in enumerate(symbols.iter_symbols()):
                if not symbol.name: continue
                version_index = symbol_versions.get_symbol(index).entry.ndx if symbol_versions else 1
                version_number = version_index & 0x7fff if isinstance(version_index, int) else 1
                hidden_version = bool(version_index & 0x8000) if isinstance(version_index, int) else False
                if symbol.entry.st_shndx == 'SHN_UNDEF':
                    if symbol.entry.st_info.bind != 'STB_WEAK':
                        imports.append((symbol.name, requirements.get(version_number)))
                elif symbol.entry.st_other.visibility in ('STV_DEFAULT', 'STV_PROTECTED'):
                    exports.setdefault(symbol.name, set()).add(versions.get(version_number))
                    if not hidden_version: defaults[symbol.name] = True
        return {'needed': needed, 'soname': soname, 'interp': interp,
                'exports': exports, 'defaults': defaults, 'imports': imports,
                'flags': elf.header.e_flags, 'fp_abi': fp_abi}


def timer_accesses(path, name):
    """Read MIPS this-relative loads/stores; never run the Enigma executable."""
    with path.open('rb') as stream:
        elf = ELFFile(stream)
        symbol = elf.get_section_by_name('.dynsym').get_symbol_by_name(name)[0]
        address, length = symbol.entry.st_value, symbol.entry.st_size
        segment = next(p for p in elf.iter_segments() if p.header.p_type == 'PT_LOAD'
                       and p.header.p_vaddr <= address < p.header.p_vaddr + p.header.p_filesz)
        stream.seek(segment.header.p_offset + address - segment.header.p_vaddr)
        code = stream.read(length)
    aliases, accesses = {4: 0}, []  # a0 initially holds this; preserve saved-register aliases.
    memory_ops = {0x23: 'lw', 0x24: 'lbu', 0x28: 'sb', 0x2b: 'sw', 0x30: 'll', 0x38: 'sc'}
    for position in range(0, len(code), 4):
        instruction = struct.unpack_from('<I', code, position)[0]
        op, rs, rt, rd, function = (instruction >> 26, (instruction >> 21) & 31,
                                    (instruction >> 16) & 31, (instruction >> 11) & 31,
                                    instruction & 63)
        offset = instruction & 0xffff
        if offset & 0x8000: offset -= 0x10000
        if op in memory_ops:
            if rs in aliases: accesses.append((memory_ops[op], aliases[rs] + offset))
            if op in (0x23, 0x24, 0x30, 0x38): aliases.pop(rt, None)
        elif op == 9:  # addiu, including a pointer into this object.
            if rs in aliases: aliases[rt] = aliases[rs] + offset
            else: aliases.pop(rt, None)
        elif op == 0 and function in (0x21, 0x25):  # addu/or move pseudoinstructions.
            source = rs if rt == 0 else rt if rs == 0 else None
            if source in aliases: aliases[rd] = aliases[source]
            else: aliases.pop(rd, None)
        elif op == 3 or (op == 0 and function == 9):  # calls clobber argument/temp registers.
            aliases = {register: value for register, value in aliases.items() if 16 <= register <= 23}
    return accesses


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('reference', type=Path)
    parser.add_argument('candidates', type=Path)
    args = parser.parse_args()
    library_files = [p for p in (args.reference / 'lib').iterdir() if not p.is_symlink()]
    providers = [inspect(args.reference / 'enigma2')]
    sonames = {}
    for path in library_files:
        provider = inspect(path)
        providers.append(provider)
        if provider['soname']: sonames[provider['soname']] = provider
    reference_interp = providers[0]['interp']
    report = {'scope': 'Static MIPS ABI/import checks; hardware playback untested', 'files': {}}
    layout = json.loads((args.candidates / 'layout.json').read_text())
    if layout['pointer'] != 4: raise ValueError('Layout probe is not 32-bit MIPS')
    accesses = timer_accesses(args.reference / 'enigma2', '_ZN6eTimer5startElb')
    expected = [('lw', layout['context']), ('sw', layout['interval']),
                ('lbu', layout['active']), ('sb', layout['single'])]
    for operation in expected:
        if operation not in accesses:
            raise ValueError('Public SDK timer layout conflicts with VTi core: '
                             + repr(operation) + ' vs ' + repr(accesses))
    report['timer_layout_probe'] = layout
    report['timer_reference_accesses'] = accesses
    for name in ('serviceapp.so', 'exteplayer3'):
        candidate = inspect(args.candidates / name)
        if candidate['flags'] & 0xf0000000 != 0x50000000 or candidate['flags'] & 0xf000 != 0x1000:
            raise ValueError('Candidate requires a different MIPS ISA/O32 ABI: ' + name)
        if candidate['fp_abi'] != 1:
            raise ValueError('Candidate must use MIPS O32 hard-float FP32 ABI: ' + name)
        if candidate['interp'] and candidate['interp'] != reference_interp:
            raise ValueError('Wrong receiver loader path: ' + name)
        missing_libraries = [lib for lib in candidate['needed'] if lib not in sonames]
        if missing_libraries: raise ValueError('Missing reference libraries: ' + repr(missing_libraries))
        missing = []
        for symbol, requirement in candidate['imports']:
            if requirement:
                library, version = requirement
                supported = version in sonames.get(library, {}).get('exports', {}).get(symbol, set())
            else:
                supported = any(symbol in provider['defaults'] for provider in providers)
            if not supported: missing.append((symbol, requirement))
        if missing: raise ValueError('Unresolved VTi imports in ' + name + ': ' + repr(missing))
        if name == 'serviceapp.so' and 'initserviceapp' not in candidate['exports']:
            raise ValueError('Python 2 module initializer missing')
        report['files'][name] = {'needed': candidate['needed'], 'elf_flags': hex(candidate['flags']),
                                'checked_strong_imports': len(candidate['imports'])}
    (args.candidates / 'static-abi.json').write_text(json.dumps(report, indent=2) + '\n')
    print(json.dumps(report, indent=2))


if __name__ == '__main__': main()
