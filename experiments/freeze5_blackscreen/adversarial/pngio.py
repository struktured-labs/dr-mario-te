"""Minimal stdlib PNG encoder (8-bit RGB, filter 0) + splice helpers for adversarial tests.

Only used to CONSTRUCT adversarial inputs; the watchdog's own decoder reads them back.
"""
import struct
import zlib


def encode_png(w, h, rgb):
    def chunk(typ, body):
        return (struct.pack(">I", len(body)) + typ + body
                + struct.pack(">I", zlib.crc32(typ + body) & 0xFFFFFFFF))
    raw = bytearray()
    stride = w * 3
    for y in range(h):
        raw.append(0)
        raw += rgb[y * stride:(y + 1) * stride]
    return (b"\x89PNG\r\n\x1a\n"
            + chunk(b"IHDR", struct.pack(">IIBBBBB", w, h, 8, 2, 0, 0, 0))
            + chunk(b"IDAT", zlib.compress(bytes(raw), 6))
            + chunk(b"IEND", b""))


def splice(base, donor, w, h, box):
    """Return `donor` with region `box`=(x0,y0,x1,y1) taken from `base`.

    i.e. the box is FROZEN at `base` while the rest of the frame is live `donor`.
    """
    x0, y0, x1, y1 = box
    out = bytearray(donor)
    for y in range(y0, y1):
        i = (y * w + x0) * 3
        j = (y * w + x1) * 3
        out[i:j] = base[i:j]
    return bytes(out)


def freeze_all_but(base, donor, w, h, box):
    """Return `base` with ONLY region `box` taken from `donor` (everything else frozen)."""
    x0, y0, x1, y1 = box
    out = bytearray(base)
    for y in range(y0, y1):
        i = (y * w + x0) * 3
        j = (y * w + x1) * 3
        out[i:j] = donor[i:j]
    return bytes(out)


def toggle_block(base, w, h, x0, y0, bw, bh, on):
    """Flip a rectangle between black and white — a synthetic 'blinking cursor'."""
    out = bytearray(base)
    v = 255 if on else 0
    for y in range(y0, y0 + bh):
        for x in range(x0, x0 + bw):
            i = (y * w + x) * 3
            out[i] = out[i + 1] = out[i + 2] = v
    return bytes(out)
