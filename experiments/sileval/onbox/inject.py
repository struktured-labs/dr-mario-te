#!/usr/bin/env python3
"""inject.py -- minimal uinput keyboard injector for the sileval lane (new box).

Replaces misterclaw-send's `input combo` on a factory-stock MiSTer (no daemon):
creates a transient virtual keyboard via /dev/uinput, emits the requested key
chord, destroys the device. Pure stdlib; struct sizes are native, so this must
run ON the MiSTer (32-bit ARM), never on the PC.

  inject.py combo f1
  inject.py combo leftalt f2
"""
import fcntl, struct, sys, time

KEYS = {
    "f1": 59, "f2": 60, "f3": 61, "f4": 62, "f12": 88,
    "leftalt": 56, "leftctrl": 29, "leftshift": 42,
    "enter": 28, "esc": 1, "up": 103, "down": 108, "left": 105, "right": 106,
}
EV_KEY, EV_SYN, SYN_REPORT = 0x01, 0x00, 0
UI_SET_EVBIT, UI_SET_KEYBIT = 0x40045564, 0x40045565
UI_DEV_CREATE, UI_DEV_DESTROY = 0x5501, 0x5502
EVENT_FMT = "llHHi"  # native long timeval -> correct on the 32-bit ARM target


def emit(f, etype, code, value):
    f.write(struct.pack(EVENT_FMT, 0, 0, etype, code, value))
    f.flush()


def main(argv):
    if len(argv) < 2 or argv[0] != "combo":
        sys.exit(__doc__)
    codes = [KEYS[k] for k in argv[1:]]
    f = open("/dev/uinput", "wb")
    fcntl.ioctl(f, UI_SET_EVBIT, EV_KEY)
    for c in codes:
        fcntl.ioctl(f, UI_SET_KEYBIT, c)
    # legacy uinput_user_dev: name[80] + input_id(4xu16) + ff_effects_max(i) + 4*absmax[64]
    dev = struct.pack("80sHHHHi", b"sileval-inject", 0x03, 0x1, 0x1, 1, 0) + b"\0" * (4 * 64 * 4)
    f.write(dev)
    f.flush()
    fcntl.ioctl(f, UI_DEV_CREATE)
    time.sleep(1.0)  # let MiSTer's input scan pick the device up
    for c in codes:
        emit(f, EV_KEY, c, 1)
    emit(f, EV_SYN, SYN_REPORT, 0)
    time.sleep(0.06)
    for c in reversed(codes):
        emit(f, EV_KEY, c, 0)
    emit(f, EV_SYN, SYN_REPORT, 0)
    time.sleep(0.3)
    fcntl.ioctl(f, UI_DEV_DESTROY)


if __name__ == "__main__":
    main(sys.argv[1:])
