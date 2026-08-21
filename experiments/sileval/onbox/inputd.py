#!/usr/bin/env python3
"""inputd.py -- persistent uinput keyboard for the sileval lane (runs ON the box).

Creates one virtual keyboard at startup, then serves key-chord commands from
/tmp/sileval_input.fifo ("combo leftalt f2" per line). Cuts per-keypress latency
from ~1.2 s (transient device + registration sleep) to the ssh round-trip only —
needed because the seedjit pre-generation capture window is ~1 s wide.

  start:  nohup python3 /media/fat/linux/sileval_inputd.py >/tmp/sileval_inputd.log 2>&1 &
  send:   echo "combo leftalt f2" > /tmp/sileval_input.fifo
  stop:   echo quit > /tmp/sileval_input.fifo
"""
import fcntl, os, struct, time

KEYS = {
    "f1": 59, "f2": 60, "f3": 61, "f4": 62, "f12": 88,
    "leftalt": 56, "leftctrl": 29, "leftshift": 42,
    "enter": 28, "esc": 1, "up": 103, "down": 108, "left": 105, "right": 106,
}
EV_KEY, EV_SYN, SYN_REPORT = 0x01, 0x00, 0
UI_SET_EVBIT, UI_SET_KEYBIT = 0x40045564, 0x40045565
UI_DEV_CREATE, UI_DEV_DESTROY = 0x5501, 0x5502
EVENT_FMT = "llHHi"
FIFO = "/tmp/sileval_input.fifo"


def emit(f, etype, code, value):
    f.write(struct.pack(EVENT_FMT, 0, 0, etype, code, value))
    f.flush()


def main():
    f = open("/dev/uinput", "wb")
    fcntl.ioctl(f, UI_SET_EVBIT, EV_KEY)
    for c in KEYS.values():
        fcntl.ioctl(f, UI_SET_KEYBIT, c)
    dev = struct.pack("80sHHHHi", b"sileval-inputd", 0x03, 0x1, 0x1, 1, 0) + b"\0" * (4 * 64 * 4)
    f.write(dev)
    f.flush()
    fcntl.ioctl(f, UI_DEV_CREATE)
    time.sleep(1.0)
    if os.path.exists(FIFO):
        os.remove(FIFO)
    os.mkfifo(FIFO)
    print("ready", flush=True)
    while True:
        with open(FIFO) as fifo:
            for line in fifo:
                parts = line.strip().split()
                if not parts:
                    continue
                if parts[0] == "quit":
                    fcntl.ioctl(f, UI_DEV_DESTROY)
                    return
                if parts[0] == "reset":
                    # MiSTer loses pre-existing virtual devices across load_core;
                    # recreate so the next combo lands. ~1.1 s.
                    fcntl.ioctl(f, UI_DEV_DESTROY)
                    time.sleep(0.1)
                    f.write(dev)
                    f.flush()
                    fcntl.ioctl(f, UI_DEV_CREATE)
                    time.sleep(1.0)
                    continue
                if parts[0] == "combo" and all(k in KEYS for k in parts[1:]):
                    codes = [KEYS[k] for k in parts[1:]]
                    for c in codes:
                        emit(f, EV_KEY, c, 1)
                    emit(f, EV_SYN, SYN_REPORT, 0)
                    time.sleep(0.06)
                    for c in reversed(codes):
                        emit(f, EV_KEY, c, 0)
                    emit(f, EV_SYN, SYN_REPORT, 0)


if __name__ == "__main__":
    main()
