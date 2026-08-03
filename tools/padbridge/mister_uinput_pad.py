#!/usr/bin/env python3
"""MiSTer side of the pad bridge: create a uinput virtual gamepad and replay
8-byte <HHi records (type,code,value) arriving on stdin as input events.

Runs on the MiSTer's own python3 (armv7l, 32-bit: input_event = 16 bytes).
MiSTer Main picks the virtual device up like any USB pad; map buttons once
in the OSD (driven by this same pad).
"""
import fcntl
import os
import struct
import sys

EV_SYN, EV_KEY, EV_ABS = 0x00, 0x01, 0x03

# buttons the 8BitDo sends in gamepad mode
KEYS = [0x130, 0x131, 0x133, 0x134,          # BTN_SOUTH/EAST/NORTH/WEST
        0x136, 0x137, 0x138, 0x139,          # BTN_TL/TR/TL2/TR2
        0x13A, 0x13B, 0x13C, 0x13D, 0x13E]   # SELECT/START/MODE/THUMBL/THUMBR
ABSES = [0x00, 0x01, 0x02, 0x03, 0x04, 0x05, 0x10, 0x11]  # sticks/triggers/hat

UI_SET_EVBIT  = 0x40045564
UI_SET_KEYBIT = 0x40045565
UI_SET_ABSBIT = 0x40045567
UI_DEV_CREATE  = 0x5501
UI_DEV_DESTROY = 0x5502

fd = os.open("/dev/uinput", os.O_WRONLY | os.O_NONBLOCK)
for ev in (EV_SYN, EV_KEY, EV_ABS):
    fcntl.ioctl(fd, UI_SET_EVBIT, ev)
for k in KEYS:
    fcntl.ioctl(fd, UI_SET_KEYBIT, k)
for a in ABSES:
    fcntl.ioctl(fd, UI_SET_ABSBIT, a)

# legacy uinput_user_dev: name[80] + input_id(4xu16) + ff_effects_max(u32) + 4x64 s32 arrays
absmax = [0] * 64
absmin = [0] * 64
for a in (0x00, 0x01, 0x02, 0x05):     # ABS_X/Y/RX?/RY-ish sticks
    absmax[a], absmin[a] = 32767, -32768
for a in (0x03, 0x04):                 # triggers
    absmax[a], absmin[a] = 1023, 0
for a in (0x10, 0x11):                 # hat (d-pad)
    absmax[a], absmin[a] = 1, -1
dev = struct.pack("80sHHHHI", b"8BitDo LAN Bridge", 0x03, 0x2DC8, 0x301C, 1, 0)
dev += struct.pack("64i", *absmax) + struct.pack("64i", *absmin)
dev += struct.pack("64i", *[0] * 64) + struct.pack("64i", *[0] * 64)
os.write(fd, dev)
fcntl.ioctl(fd, UI_DEV_CREATE)
sys.stderr.write("virtual pad created\n")

REC = struct.Struct("<HHi")
IE32 = struct.Struct("llHHi")          # 32-bit input_event (16 bytes)
stdin = os.fdopen(sys.stdin.fileno(), "rb", buffering=0)
try:
    buf = b""
    while True:
        chunk = stdin.read(4096)
        if not chunk:
            break
        buf += chunk
        while len(buf) >= REC.size:
            etype, code, value = REC.unpack(buf[:REC.size])
            buf = buf[REC.size:]
            os.write(fd, IE32.pack(0, 0, etype, code, value))
finally:
    fcntl.ioctl(fd, UI_DEV_DESTROY)
    os.close(fd)
