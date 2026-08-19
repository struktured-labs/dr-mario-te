#!/usr/bin/env python3
"""Cut ss_decode.py's self-test fixtures out of real save-states.

A .ss is 1.3 MB and none of that belongs in git. Every anchor the decoder reads -- the
playfields, the per-player structs, the whole $61xx driver mailbox -- lives inside one
0x1000-byte window starting at the CPU-RAM base, so that window is all a fixture needs.
selftest() rebuilds a full-size container around it and runs the REAL locator, so the
fixture exercises the signature scan on genuine silicon bytes rather than on a mock.

Run this only to regenerate; the outputs are committed.

    ./make_fixtures.py <a.ss> <b.ss> ...
"""
from __future__ import annotations

import gzip
import hashlib
import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import ss_decode as S      # noqa: E402

WINDOW = 0x1000            # CPU RAM $0000-$07FF + cartridge WRAM $6000-$67FF
HERE = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'fixtures')


def base_of(buf):
    """The CPU-RAM base, however the file presents -- including 'not in a match'."""
    try:
        return S.locate_ram(buf)[0]
    except S.NotInAMatch as e:
        # message carries the WRAM base the relaxed scan pinned
        w = int(str(e).split('WRAM 0x')[1].split(' ')[0], 16)
        return w - S.WRAM_DELTA


def main(argv):
    if not argv:
        print(__doc__, file=sys.stderr)
        return 64
    os.makedirs(HERE, exist_ok=True)
    manifest = []
    for path in argv:
        buf = open(path, 'rb').read()
        if len(buf) != S.SS_SIZE:
            print(f"skip {path}: {len(buf)} bytes", file=sys.stderr)
            continue
        ram = base_of(buf)
        win = buf[ram:ram + WINDOW]
        name = os.path.basename(path).replace('.ss', '') + '.win.gz'
        with gzip.open(os.path.join(HERE, name), 'wb', compresslevel=9) as fh:
            fh.write(win)
        manifest.append(dict(name=name, ram_base=ram, source=os.path.basename(path),
                             sha256=hashlib.sha256(win).hexdigest()))
        print(f"{name}: RAM base 0x{ram:06X}  {len(win)} bytes from {path}")
    with open(os.path.join(HERE, 'manifest.json'), 'w') as fh:
        json.dump(manifest, fh, indent=2)
    return 0


if __name__ == '__main__':
    sys.exit(main(sys.argv[1:]))
