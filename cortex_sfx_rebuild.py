#!/usr/bin/env python3
import mmap
import struct
dirs = {}
ents = []
fileoffsets = []
namebuf = bytearray()
padding = b'\0'*2048
def add_ent(is_dir, dirname, pathname, fullname):
    global namebuf
    backlink = 0
    if dirname != '':
        backlink = ents[dirs[dirname]][0]
        ents[dirs[dirname]][0] = len(ents)
        if backlink == 0 and is_dir:
            backlink = dirs[dirname]
    if is_dir:
        dirs[fullname] = len(ents)
    ents.append([0, backlink, len(namebuf), fullname, is_dir])
    namebuf += pathname.encode()
    namebuf += b'\0'
    
with open('index.txt') as f:
    for line in f:
        line = line.strip()
        if line == '':
            continue
        p = line.split('/');
        is_dir = p[-1] == ''
        if is_dir:
            p = p[:-1]
        add_ent(is_dir, '/'.join(p[:-1]), p[-1], '/'.join(p))

namebuf += padding[:(len(namebuf)+15)//16*16 - len(namebuf)]

def copy_file(outf, filename):
    with open(filename, 'rb') as f:
        with mmap.mmap(f.fileno(), 0, access=mmap.ACCESS_READ) as m:
            ofs = outf.tell()
            outf.write(padding[:(ofs+2047)//2048*2048 - ofs])
            ofs = outf.tell()
            outf.write(m)
            return ofs, len(m)

with open('sfx2.dat', 'wb') as outf:
    outf.write(padding)
    for ent in ents:
        if not ent[4]:
            ent[0] = -len(fileoffsets)
            fileoffsets.append(copy_file(outf, ent[3]))
    toc_ofs = outf.tell()
    outf.write(struct.pack('<iI', -1, len(fileoffsets)))
    for x in fileoffsets:
        outf.write(struct.pack('<IIII', x[0], x[1], x[1], 0))
    outf.write(struct.pack('<I', len(ents)))
    for ent in ents:
        outf.write(struct.pack('<hHHH', ent[0], ent[1], ent[2], 0))
    outf.write(struct.pack('<I', len(namebuf)))
    outf.write(namebuf)
    toc_size = outf.tell() - toc_ofs
    outf.seek(0)
    outf.write(struct.pack('<II', toc_ofs, toc_size))
