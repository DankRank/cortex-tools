#!/usr/bin/env python3
import sys
sect = bytearray(2352)
while True:
    if sys.stdin.buffer.readinto(sect) != 2352:
        break
    sys.stdout.buffer.write(sect[24:2072])
