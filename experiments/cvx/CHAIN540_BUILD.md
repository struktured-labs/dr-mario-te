# CHAIN540 core — build record (2026-09-24, Claude solo; owner: "yes build it")
**rbf** `NES_childproof_chain540_20260924.rbf` md5 **11c4b46debde8e96948ef57a5fdfc784**
(archive `dr_mario_rl/tmp/rtl_chain/ship/childproof-chain540-seed13/`, unique across 18 archived builds)

| input | value |
|---|---|
| RTL | 08f2343 (claude/winner-single-copro = Childproof's RTL; winner leaf, R_HOLES 20) |
| settings | Childproof's archived `NES.qsf.used` verbatim, SEED 13 |
| firmware | `fw540.hex` md5 6d13e6a1 = Childproof's veto2fixa recipe with DRCHAIN=540 |
| recipe | DRSTRAND=20 DRCHAIN=540 DRCOPRO_ARM=1 DRFIX=1 DRCOPRO_TUCKBFS=1 TUCKBFS_TIER3=1 TUCKV3_THETA=400 DRDBLCANON=1 TUCKV3_FIXSLOT=1 DRVETO=1, USE_DELTA=True |
| recipe check | same builder at DRCHAIN=180 reproduces shipped a2b2e4ac byte-exact |
| diff vs Childproof fw | exactly ONE byte: copro ROM $8006 0x2D -> 0x87 (a_chw 45 -> 135) |

**Gates:** copro slack **+0.165 ns**, pll_hdmi **+0.381 ns**, ALMs 37,664 (4,246 free) — IDENTICAL to
Childproof (4th firmware-swap placement reproduction at seed 13). **FW-in-image:** perfect 16/16 bijection
with fw540; control fw180 mismatches exactly lanes 1,3,5,7 of the low half (= 0x2D xor 0x87 = 0xAA) .
Overflow: 16-bit chain_bonus saturates at chain 15 → worst 7,560 << ~25.5k leaf headroom.
**Why:** RESULT_DOSEKNEE.md — vs a 177-s human racer +7.3pp (screen) / +8.5pp (holdout), tap-out not worse.
**Deployed:** rivalmage `AA_DRMARIO_CHAIN540.mgl` (+ TE study cart 6c3c3168), LOADED 2026-09-24 23:17Z,
boot screenshot clean. NOT soaked (owner: load even if unsoaked). Bluemage soak pending (box offline).
Shared fork restored after build: HEAD 18cf064, hex f78f1e93, qsf identical to pre-build backup, rtl clean.
