#!/usr/bin/env python3
"""PC side of the MiSTer pad bridge: read the 8BitDo evdev device raw, forward
EV_KEY/EV_ABS/EV_SYN as fixed 8-byte records on stdout (binary, unbuffered).

    ./pc_pad_reader.py /dev/input/by-id/usb-8BitDo_..._-event-joystick | \
        ssh root@mister.local 'python3 /tmp/mister_uinput_pad.py'

Record format (little-endian): <HHi  = type:u16, code:u16, value:i32.
64-bit host input_event = 24 bytes (16B timeval + type/code/value).
"""
import struct
import sys
import os

DEV = sys.argv[1] if len(sys.argv) > 1 else \
    "/dev/input/by-id/usb-8BitDo_8BitDo_Ultimate_2_Wireless_Controller_for_PC_DF1F7104CB-event-joystick"

EV_SYN, EV_KEY, EV_ABS = 0x00, 0x01, 0x03
IE = struct.Struct("llHHi")          # 64-bit input_event
OUT = struct.Struct("<HHi")

fd = os.open(DEV, os.O_RDONLY)
out = os.fdopen(sys.stdout.fileno(), "wb", buffering=0)
sys.stderr.write("pad bridge: reading %s\n" % DEV)
while True:
    data = os.read(fd, IE.size)
    if len(data) != IE.size:
        break
    _, _, etype, code, value = IE.unpack(data)
    if etype in (EV_SYN, EV_KEY, EV_ABS):
        out.write(OUT.pack(etype, code, value))
