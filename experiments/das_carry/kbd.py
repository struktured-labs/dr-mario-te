#!/usr/bin/env python3
"""Tiny uinput keyboard for MiSTer (armv7, legacy uinput API) that can HOLD keys.
Same VID:PID as the misterclaw keyboard (4711:0815) so /media/fat/config/inputs/NES_input_4711_0815_v3.map
applies: RIGHT=106 LEFT=105 DOWN=108 UP=103 A=45 B=44 SELECT=54 START=28.
Timeline file, one command per line:
  down CODE | up CODE | tap CODE [ms] | sleep MS | combo CODE CODE | save LABEL | shot | note TEXT
'save LABEL' = Alt+F1 then copy the slot-1 savestate to OUTDIR/LABEL.ss (waits for the file to change).
Usage: kbd.py TIMELINE OUTDIR ROMBASENAME
"""
import os, sys, time, fcntl, struct, shutil

UI_SET_EVBIT, UI_SET_KEYBIT, UI_DEV_CREATE, UI_DEV_DESTROY = 0x40045564, 0x40045565, 0x5501, 0x5502
EV_SYN, EV_KEY, SYN_REPORT = 0, 1, 0
ALT, F1 = 56, 59


def emit(fd, typ, code, val):
    t = time.time()
    os.write(fd, struct.pack("=iiHHi", int(t), int((t % 1) * 1e6), typ, code, val))


def key(fd, code, val):
    emit(fd, EV_KEY, code, val); emit(fd, EV_SYN, SYN_REPORT, 0)


def main():
    timeline, outdir, rom = sys.argv[1], sys.argv[2], sys.argv[3]
    os.makedirs(outdir, exist_ok=True)
    ss = "/media/fat/savestates/NES/%s_1.ss" % rom
    log = open(os.path.join(outdir, "log.txt"), "a")
    fd = os.open("/dev/uinput", os.O_WRONLY | os.O_NONBLOCK)
    fcntl.ioctl(fd, UI_SET_EVBIT, EV_KEY)
    for k in range(1, 256):
        fcntl.ioctl(fd, UI_SET_KEYBIT, k)
    os.write(fd, struct.pack("=80s4HI256i", b"misterclaw", 0x06, 0x4711, 0x0815, 1, 0, *([0] * 256)))
    fcntl.ioctl(fd, UI_DEV_CREATE)
    time.sleep(2.0)                                     # let MiSTer main enumerate the device
    held = set()
    t0 = time.time()
    try:
        for line in open(timeline):
            p = line.split()
            if not p or p[0].startswith("#"):
                continue
            c = p[0]
            log.write("%8.3f %s\n" % (time.time() - t0, line.strip())); log.flush()
            if c == "down":
                key(fd, int(p[1]), 1); held.add(int(p[1]))
            elif c == "up":
                key(fd, int(p[1]), 0); held.discard(int(p[1]))
            elif c == "tap":
                key(fd, int(p[1]), 1); time.sleep((int(p[2]) if len(p) > 2 else 40) / 1000.0); key(fd, int(p[1]), 0)
            elif c == "sleep":
                time.sleep(int(p[1]) / 1000.0)
            elif c == "combo":
                a, b = int(p[1]), int(p[2])
                key(fd, a, 1); time.sleep(0.05); key(fd, b, 1); time.sleep(0.08); key(fd, b, 0); time.sleep(0.03); key(fd, a, 0)
            elif c == "save":
                before = os.path.getmtime(ss) if os.path.exists(ss) else 0
                key(fd, ALT, 1); time.sleep(0.05); key(fd, F1, 1); time.sleep(0.08); key(fd, F1, 0); time.sleep(0.03); key(fd, ALT, 0)
                for _ in range(60):
                    time.sleep(0.1)
                    if os.path.exists(ss) and os.path.getmtime(ss) != before and os.path.getsize(ss) == 1327112:
                        break
                time.sleep(0.3)
                shutil.copy(ss, os.path.join(outdir, p[1] + ".ss"))
                log.write("         saved %s (%s)\n" % (p[1], "changed" if os.path.getmtime(ss) != before else "UNCHANGED"))
            elif c == "shot":
                open("/dev/MiSTer_cmd", "w").write("screenshot\n"); time.sleep(1.2)
            elif c == "note":
                pass
    finally:
        for k in list(held):
            key(fd, k, 0)
        time.sleep(0.2)
        fcntl.ioctl(fd, UI_DEV_DESTROY); os.close(fd)
        log.write("%8.3f done\n" % (time.time() - t0)); log.close()


if __name__ == "__main__":
    main()
