#!/usr/bin/env python3
import os
import sys
import mmap
import struct

patchscript = ''

def memmove(dst, src, size):
    global patchscript
    patchscript += f'b[{dst}:{dst+size}] = b[{src}:{src+size}]\n'
def memwrite(dst, val, size):
    global patchscript
    patchscript += f'b[{dst}:{dst+size}] = {val}\n'

def check_magic(b):
    if b[0:12] == b'\0\xFF\xFF\xFF\xFF\xFF\xFF\xFF\xFF\xFF\xFF\0':
        print('Please convert your BIN to ISO first.')
        sys.exit(1)
    if b[0x8000:0x8007] != b'\1CD001\1':
        print('Your file doesn\'t look like an ISO.')
        sys.exit(1)

def get_extent(ent):
    ofs, = struct.unpack('<I', ent[2:6])
    size, = struct.unpack('<I', ent[10:14])
    return ofs*2048, size

def find_rootdir(b):
    ofs, size = get_extent(b[0x809C:0x809C+34])
    return b[ofs:ofs+size]

def find_sfx(b, rootdir):
    print('Searching for sfx.dat...')
    for c in (rootdir[i:i+2048] for i in range(0, len(rootdir), 2048)):
        while len(c) > 0 and c[0] > 0:
            entlen = c[0]
            namelen = c[32]
            if c[33:33+namelen] == b'SFX.DAT;1':
                ofs, size = get_extent(c)
                print(f'sfx.dat found at {ofs} (size {size})')
                return b[ofs:ofs+size], ofs
            c = c[entlen:]
    print('sfx.dat not found')
    sys.exit(1)

def walk_sfx(sfx, sfx_ofs):
    print('reading table of contents...')
    toc_ofs, toc_size = struct.unpack('<II', sfx[:8])
    toc = sfx[toc_ofs:toc_ofs+toc_size]
    def advance(n):
        nonlocal toc
        r, toc = toc[0:n], toc[n:]
        return r

    advance(4)
    ofs_count, = struct.unpack('<I', advance(4))
    ofs_tab = advance(ofs_count*16)
    ent_count, = struct.unpack('<I', advance(4))
    ent_tab = advance(ent_count*8)
    name_count, = struct.unpack('<I', advance(4))
    name_tab = bytes(advance(name_count))

    def get_name(i):
        return name_tab[i:name_tab.find(b'\0', i)]
    def get_ent(i):
        a, b, c = struct.unpack('<hHH', ent_tab[i*8:i*8+6])
        return a, b, get_name(c)
    def entries(i, end):
        while i != end:
            ent = get_ent(i)
            yield ent
            i = ent[1]
    def find_by_name(ents, name):
        for ent in ents:
            if ent[2] == name:
                return ent
        print(f'couldn\'t find {name}')
        sys.exit(1)
    def is_dir(ent):
        return ent[0] > 0

    print('Entering /sfx...')
    sfx_dir = find_by_name(entries(1, 0), b'sfx')
    if not is_dir(sfx_dir):
        print('sfx is not a directory')
        sys.exit(1)

    print('Entering /sfx/music...')
    music_dir = find_by_name(entries(sfx_dir[0], 1), b'music')
    if not is_dir(music_dir):
        print('music is not a directory')
        sys.exit(1)

    def get_data(ent):
        return struct.unpack('<II', ofs_tab[16*-ent[0]:16*-ent[0]+8])
        
    print('Fixing /sfx/music/*.vag...')
    for ent in entries(music_dir[0], 0):
        print(f'{ent[2].decode()}... ', end='')
        if is_dir(ent):
            print('is a directory(?), skipping')
            continue
        if ent[2] in [b'invincil.vag', b'invincir.vag']:
            print('is invincibility theme, skipping')
            continue
        if not is_dir(ent) and ent[2] not in [b'invincil.vag', b'invincir.vag']:
            emptyline = b'\x0c' + 15*b'\0'
            ofs, size = get_data(ent)
            for i in range(0x40, size, 0x10):
                if sfx[ofs+i:ofs+i+0x10] != emptyline:
                    break
            else:
                print('is completely empty(?), skipping')
                continue
            if i == 0x40:
                print('doesn\'t need fixing, skipping')
                continue
            print(f'must be fixed by {i-0x40} bytes')

            memwrite(sfx_ofs+toc_ofs+8+16*-ent[0]+4, struct.pack('<I', size-(i-0x40))*2, 8)
            memmove(sfx_ofs+ofs+0x40, sfx_ofs+ofs+i, size-i)

if __name__ == '__main__':
    if len(sys.argv) < 2 or len(sys.argv) > 3:
        print(f'Usage: {sys.argv[0]} [input] [output]')
        sys.exit(1)
    input_filename = sys.argv[1]
    output_filename = sys.argv[2] if len(sys.argv) == 3 else None

    with open(input_filename, 'rb') as f:
        m = mmap.mmap(f.fileno(), 0, access=mmap.ACCESS_READ)
        b = memoryview(m)
        check_magic(b)
        walk_sfx(*find_sfx(b, find_rootdir(b)))
        b = None
        if output_filename is None:
            print('---')
            print(patchscript)
        else:
            if os.path.exists(output_filename) and os.path.samefile(input_filename, output_filename):
                print(f'Backing up {output_filename}...')
                os.rename(output_filename, output_filename+'.bak')
            with open(output_filename, 'w+b') as fo:
                print('Copying...')
                fo.write(m)
                fo.flush()
                with mmap.mmap(fo.fileno(), 0) as mo:
                    print('Applying patches...')
                    exec(patchscript, {'b': mo})
        m.close()
