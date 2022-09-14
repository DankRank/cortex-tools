#!/usr/bin/env python3
import os
import mmap
import struct
def mvstrlen(mv, off, limit=256):
    return bytes(mv[off:off+limit]).find(b'\0')
def round2048(x):
    return (x+2047)//2048*2048
def main(b):
    toc1_ofs, = struct.unpack_from('<I', b)
    toc1 = b[toc1_ofs:]
    unused, toc1_count = struct.unpack_from('<II', toc1)
    toc1 = toc1[8:]
    toc2 = toc1[toc1_count*16:]
    print('toc1_count:', toc1_count)
    last_expect = 2048
    fot = []
    for i in range(toc1_count):
        x = struct.unpack_from('<IIII', toc1)
        toc1 = toc1[16:]
        print(i, x[:2])
        fot.append(x[:2])
        if x[0] != last_expect:
            print('huh', hex(x[0]-last_expect), hex(x[0]), hex(last_expect))
        last_expect = round2048(x[0]+x[1])
    toc2_count, = struct.unpack_from('<I', toc2)
    toc2 = toc2[4:]
    fns_limit, = struct.unpack_from('<I', toc2[toc2_count*8:])
    fns = toc2[toc2_count*8 + 4:]
    tabs = ''
    dirstack = []
    namestack = []
    unrollstack = []
    print('toc2_count:', toc2_count)
    for i in range(toc2_count):
        x = struct.unpack_from('<hHHH', toc2)
        namelen = mvstrlen(fns, x[2], fns_limit-x[2])
        name = bytes(fns[x[2]:x[2]+namelen]).decode()
        path = '/'.join(namestack+[name])
        toc2 = toc2[8:]
        print(tabs, i, x[:2], path)
        if i != 0 and x[0] <= 0:
            if len(dirstack) > 0:
                os.makedirs('/'.join(namestack), exist_ok=True)
            ofs, size = fot[-x[0]]
            with open(path, 'wb') as f:
                f.write(b[ofs:ofs+size])
        if i != 0 and x[0] > 0:
            tabs += '  '
            dirstack.append(x[0])
            namestack.append(name)
            if len(dirstack) > 0 and i == dirstack[-1]:
                unrollstack[-1] += 1
            else:
                unrollstack.append(1)
        elif len(dirstack) > 0 and i == dirstack[-1]:
            tabs = tabs[:-unrollstack[-1]*2]
            dirstack = dirstack[:-unrollstack[-1]]
            namestack = namestack[:-unrollstack[-1]]
            unrollstack = unrollstack[:-1]

with open('sfx.dat', 'rb') as f:
    m = mmap.mmap(f.fileno(), 0, access=mmap.ACCESS_READ)
    b = memoryview(m)
    main(b)
    b = None
    m.close()
