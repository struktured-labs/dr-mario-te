# PRE-REG (2026-09-22): MEGADOSE A/B k_clock=40 vs k=0 on live NES

FPGA CLOCK40 is soaking. This is the teacher-on-real-ROM gate, not another Quartus.

**ROM:** base `drmario.nes` (1P). VS-CPU ROM is banned (AI hook eats input).
**Driver:** Mesen2 file bridge + `VsPolicy` d3 winner trunk (same as vs_choose).
**A:** k_clock=0 (= `_choose_base(winner)`). **B:** k_clock=40.
**Level:** 11 MED. **Seeds:** 40..47 (8-bit RNG write at level-select). Paired.
**n=8 per arm** (16 games). Screen, not a ship claim.

**Metrics:** clear (won), pills, end_v. Diverge vs sim is diagnostic only.

**Hold:** B clear rate not >10pp worse than A. Faster (fewer pills) is supporting,
not required. Collapse = MEGADOSE fail; FPGA soak can stay but we do not promote
the term as NES-sane.

**Not this run:** 2P VS on Mesen, Hartford poke, Quartus, kc34.
