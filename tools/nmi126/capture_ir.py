#!/usr/bin/env python3
"""#126 NMI-hook cycle census, stage 1: capture the emitter's instruction IR.

Runs the REAL emitter (patch_cartridge_copro / patch_vs_cpu) under a manifest's
flag_snapshot and records every instruction the Asm6502 assembler emits --
offset, mnemonic, operand bytes, branch/jump targets, labels -- for each code
unit that executes inside the per-frame NMI hook:

  wrapper   $FF54 trampoline (BUSY guard + bank switch + JSR main)
  main      unit-1 driver body at $8000
  p1ai      DRP1NATIVE mirrored v18 depth-1 AI at $9000   (P1NATIVE builds only)
  p1swap    its swap_eval at $9200                        (P1NATIVE builds only)

GROUND-TRUTH GATE (gate-standard rule 2, whole-chain): the bytes reassembled
from the captured IR must equal the bytes the emitter's own assemble() returned
for the same unit. A capture that records a different program than the one that
ships is a hard failure, not a warning.

Usage:
  python3 tools/nmi126/capture_ir.py roms/manifests/v6e.json tmp/nmi126/v6e_ir.json

Must run in a SUBPROCESS per config: patch_cartridge_copro parses flags at
import time.
"""
import json
import os
import sys


def main():
    manifest_path, out_path = sys.argv[1], sys.argv[2]
    man = json.load(open(manifest_path))
    snap = man.get("flag_snapshot") or man.get("flags")
    assert snap, f"{manifest_path} has no flag_snapshot"
    # Emitter reads flags from the environment at import time.
    for k, v in snap.items():
        os.environ[k] = str(v)

    sys.path.insert(0, os.getcwd())
    import patch_vs_cpu as pv

    records_by_unit = {}
    current = []  # capture list the subclass appends into

    class CensusAsm(pv.Asm6502):
        def __init__(self, base_cpu):
            super().__init__(base_cpu)
            self._cap = []
            current.append((base_cpu, self._cap))

        def label(self, name):
            self._cap.append({"k": "label", "off": len(self.code), "name": name})
            super().label(name)

        def ins(self, mnem, *operands):
            self._cap.append({"k": "ins", "off": len(self.code), "m": mnem,
                              "ops": list(operands)})
            super().ins(mnem, *operands)

        def ins16(self, mnem, value):
            self._cap.append({"k": "ins", "off": len(self.code), "m": mnem,
                              "ops": [value & 0xFF, (value >> 8) & 0xFF]})
            super().ins16(mnem, value)

        def br(self, mnem, target):
            self._cap.append({"k": "br", "off": len(self.code), "m": mnem,
                              "target": target})
            super().br(mnem, target)

        def jmp(self, target, mnem="JMP"):
            self._cap.append({"k": "jmp", "off": len(self.code), "m": mnem,
                              "target": target if isinstance(target, str) else int(target)})
            super().jmp(target, mnem)

        def jsr(self, target):
            self._cap.append({"k": "jsr", "off": len(self.code), "m": "JSR",
                              "target": target if isinstance(target, str) else int(target)})
            super().jsr(target)

        def raw(self, *bytes_):
            self._cap.append({"k": "raw", "off": len(self.code), "n": len(bytes_)})
            super().raw(*bytes_)

    # Patch BOTH modules: patch_cartridge_copro binds Asm6502 at import;
    # patch_vs_cpu's own builders (build_v18_ai, build_swap_eval) resolve the
    # module global.
    pv.Asm6502 = CensusAsm
    import patch_cartridge_copro as pcc
    pcc.Asm6502 = CensusAsm

    def grab(name, base_cpu, build):
        """Run one builder, pair its capture with its assembled bytes, gate."""
        n_before = len(current)
        out = build()
        code, labels = out
        # A builder may construct helper Asm6502 instances (TCVC's build_main
        # calls build_p1_native for a label); select by base AND byte identity.
        caps = [c for b, c in current[n_before:] if b == base_cpu]
        assert len(caps) == 1, f"{name}: expected 1 Asm6502 at ${base_cpu:04X}, saw {len(caps)}"
        # Labels ALWAYS from the capture (unit-relative offsets); builders differ
        # in whether their returned dict is offset- or CPU-absolute keyed.
        lab = {r["name"]: r["off"] for r in caps[0] if r["k"] == "label"}
        records_by_unit[name] = {
            "base": base_cpu,
            "bytes": code.hex(),
            "labels": lab,
            "records": caps[0],
        }

    level = int(snap.get("DRLEVEL", "11"))
    speed = int(snap.get("DRSPEED", "1"))

    grab("main", pcc.UNIT1_CPU, lambda: pcc.build_main(level, speed))
    main_cpu = pcc.UNIT1_CPU + records_by_unit["main"]["labels"]["main"]

    # build_wrapper returns bytes only; recover labels from the capture instance.
    n_before = len(current)
    wrap_bytes = pcc.build_wrapper(main_cpu)
    caps = [c for b, c in current[n_before:] if b == pcc.WRAP_CPU]
    assert len(caps) == 1
    # Labels live on the instance; the capture holds label records too -- rebuild.
    wl = {r["name"]: r["off"] for r in caps[0] if r["k"] == "label"}
    records_by_unit["wrapper"] = {"base": pcc.WRAP_CPU, "bytes": wrap_bytes.hex(),
                                  "labels": wl, "records": caps[0]}

    if pcc.P1NATIVE:
        n_before = len(current)
        p1ai, p1lab, p1swap = pcc.build_p1_native()
        ai_caps = [c for b, c in current[n_before:] if b == pcc.P1AI_CPU]
        sw_caps = [c for b, c in current[n_before:] if b == pcc.P1SWAP_CPU]
        assert len(ai_caps) == 1 and len(sw_caps) == 1, (
            f"p1native: expected 1 AI + 1 swap Asm6502, saw {len(ai_caps)}/{len(sw_caps)}")
        al = {r["name"]: r["off"] for r in ai_caps[0] if r["k"] == "label"}
        records_by_unit["p1ai"] = {"base": pcc.P1AI_CPU, "bytes": p1ai.hex(),
                                   "labels": al, "records": ai_caps[0]}
        sl = {r["name"]: r["off"] for r in sw_caps[0] if r["k"] == "label"}
        records_by_unit["p1swap"] = {"base": pcc.P1SWAP_CPU, "bytes": p1swap.hex(),
                                     "labels": sl, "records": sw_caps[0]}

    # ---- GROUND-TRUTH GATE: reassemble each unit from the captured IR and ----
    # ---- require byte equality with what the emitter itself assembled.    ----
    OPS, BR = pv.OPS, pv.BRANCHES
    for name, u in records_by_unit.items():
        got = bytearray()
        for r in u["records"]:
            assert r["off"] == len(got), f"{name}: IR gap at {r}"
            if r["k"] == "label":
                continue
            if r["k"] == "ins":
                got.append(OPS[r["m"]])
                got.extend(b & 0xFF for b in r["ops"])
            elif r["k"] == "br":
                got.append(BR[r["m"]])
                dest = u["labels"][r["target"]]
                got.append((dest - (len(got) + 1)) & 0xFF)
            elif r["k"] in ("jmp", "jsr"):
                got.append(OPS[r["m"]])
                t = r["target"]
                dest = u["base"] + u["labels"][t] if isinstance(t, str) else t
                got.append(dest & 0xFF)
                got.append((dest >> 8) & 0xFF)
            elif r["k"] == "raw":
                # data: copy from the authoritative bytes (content irrelevant
                # to control flow; length keeps offsets aligned)
                auth = bytes.fromhex(u["bytes"])
                got.extend(auth[r["off"]:r["off"] + r["n"]])
        auth = bytes.fromhex(u["bytes"])
        assert bytes(got) == auth, (
            f"GROUND-TRUTH GATE FAILED: unit {name} IR reassembly != emitter bytes "
            f"(len {len(got)} vs {len(auth)})")

    meta = {
        "manifest": manifest_path,
        "flags_on": {k: v for k, v in snap.items() if v not in ("0", "", None)},
        "p1native": pcc.P1NATIVE,
        "main_cpu": main_cpu,
        "units": records_by_unit,
    }
    with open(out_path, "w") as f:
        json.dump(meta, f)
    for name, u in records_by_unit.items():
        n_ins = sum(1 for r in u["records"] if r["k"] != "label")
        print(f"{name}: base=${u['base']:04X} {len(bytes.fromhex(u['bytes']))} B "
              f"{n_ins} records  GROUND-TRUTH OK")


if __name__ == "__main__":
    main()
