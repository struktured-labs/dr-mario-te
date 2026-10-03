#!/usr/bin/env python3
"""Write the Lua address table nmi_witness.lua needs, from a capture_ir.py IR, and REFUSE unless the IR's driver
bytes are byte-identical to the cart's (so a witness address can never point into a different program).

  nmi_addrs.py IR.json CART.nes OUT.lua
"""
import json
import sys

WANT = ["main", "lg_gate", "lg_live", "lg_done", "pre_tick", "pp_disp", "pp_ph1", "pt_edge", "pt_commit", "pt_bail",
        "h2_cp", "act", "act_dn"]


def main():
    ir, cart, out = sys.argv[1], sys.argv[2], sys.argv[3]
    ir = json.load(open(ir))
    data = open(cart, "rb").read()
    prg = data[16:16 + data[4] * 16384]
    drv = prg[32768:65536]                              # MMC1 32 KB mode: bank 1 = the driver bank at $8000
    for name, u in ir["units"].items():
        b = bytes.fromhex(u["bytes"])
        off = u["base"] - 0x8000
        if drv[off:off + len(b)] != b:
            raise SystemExit(f"REFUSE: IR unit {name} is not byte-identical to {cart} driver bank at ${u['base']:04X}")
    u = ir["units"]["main"]
    L = {k: u["base"] + v for k, v in u["labels"].items()}
    phases = ["pp_ph1"] + sorted((k for k in L if k.startswith("pp_m") and k[4:].isdigit()), key=lambda k: int(k[4:]))
    phases = [p for p in phases if p in L]               # [] on an image without DRPRESPIPE (e.g. the CvC cart)
    names = [n for n in WANT if n in L] + [p for p in phases if p not in WANT]
    lines = ["return {", "  addr = {"]
    lines += [f"    {n} = 0x{L[n]:04X}," for n in names]
    lines += ["  },", "  phases = {" + ", ".join(f'"{p}"' for p in phases) + "},", "}"]
    open(out, "w").write("\n".join(lines) + "\n")
    print(f"OK {cart}: {len(names)} addresses, phases {phases or 'none (no DRPRESPIPE)'} -> {out}")


if __name__ == "__main__":
    main()
