#!/usr/bin/env bash
# sync_to_pocket.sh — vendor the canonical Dr. Mario copro RTL into the Analogue Pocket tree.
#
# Canonical source = THIS directory (dr-mario-mods/fpga/copro). One source of truth; both the
# MiSTer mapper (NES_MiSTer/rtl/mappers) and the Pocket core vendor FROM here — no divergent copies.
#
# Vendors the SYNTHESIS set only into  <pocket>/target/pocket/vendor/copro/  with a DO-NOT-EDIT +
# source-commit header, and (re)generates copro.qip. Idempotent (header date only moves when a file's
# body changes) and diff-printing. Does NOT touch rtl/upstream/ or projects/ (safe during a fit run).
#
# Deliberately EXCLUDED:
#   dpram.v      -> sim-only stub; the real build binds CoproDrMario's `dpram` to agg23's
#                   rtl/upstream/dpram.vhd, which is byte-identical to MiSTer's (same entity/generics).
#                   Vendoring ours would create a duplicate-module collision. See portability audit.
#   cpu.v, ALU.v -> original Arlet Ottens core; superseded by the namespaced copro6502 / copro_alu.
#   tb.v top_v.v top_iface.v sim_*.cpp -> verilator/iverilog harness, not synthesized.
#
# Usage:  ./sync_to_pocket.sh [DEST_DIR]
#   DEST_DIR defaults to the Pocket worktree's vendor dir. Pass a scratch dir for a dry preview.
#
# ============================= INCIDENT / DO NOT REGRESS ==============================
# 2026-07-26: this script used to copy copro_rom.hex over the vendored (shipped) hex
# VERBATIM on any difference. The firmware that actually ships to Pocket/MiSTer is the
# co-sim-validated DELTA build (CMD-6/7 incremental-leaf engine + illegal-exit fix),
# md5 c87e60a1, vendored 2026-07-25. But the COMMITTED canonical hex was the older
# cell-exact BASE build, md5 412615b2 (fd8e495 "R47 brain", 2026-07-22), because several
# build paths (build_copro_d3 / build_firmware / run_gate) default to or leave BASE
# behind. A blind re-run therefore SILENTLY REVERTED the shipped delta engine — and with
# an eval change riding along it, would have presented on silicon as "the new eval plays
# worse", sending everyone chasing the eval instead of the reverted search engine.
# GUARD (HEX section below): never overwrite a DIFFERING vendored hex — fail loudly with
# both md5s. A deliberate firmware change validates cell-exactness via ./run_gate.sh, then
# re-runs with ALLOW_HEX_UPDATE=1. Rebuild the shipped hex with `dbg_build.py all 0`.
# Full base-vs-delta story + the three drift sources: FIRMWARE.md.
# =====================================================================================
set -euo pipefail

# SRC defaults to this script's dir (the canonical copro source); override with COPRO_SRC for testing.
SRC="${COPRO_SRC:-$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)}"
DST="${1:-/home/struktured/projects/pocket-nes-mapper100/target/pocket/vendor/copro}"

RTL=(CoproDrMario.sv LeafEval.sv copro6502.v copro_alu.v)   # order irrelevant; Quartus resolves
HEX=copro_rom.hex

# --- preflight: Pocket instantiates CoproDrMario #(.WIN(...)); the canonical must be parameterized.
if ! grep -qE 'parameter *\[6:0\] *WIN' "$SRC/CoproDrMario.sv"; then
  echo "ERROR: $SRC/CoproDrMario.sv is NOT parameterized (#(.WIN(...)))." >&2
  echo "       The Pocket cart.sv instantiates CoproDrMario #(.WIN(7'b0101_000))." >&2
  echo "       Promote the parameterized form to canonical first" >&2
  echo "       (NES_MiSTer/rtl/mappers/CoproDrMario.sv is the deployed parameterized version)." >&2
  exit 2
fi

HASH="$(git -C "$SRC" rev-parse --short HEAD 2>/dev/null || echo nogit)"
git -C "$SRC" diff --quiet HEAD 2>/dev/null || HASH="${HASH}-dirty"   # flag uncommitted canonical
STAMP="// AUTO-VENDORED from dr-mario-mods/fpga/copro @ ${HASH} ($(date -u +%FT%TZ)) -- DO NOT EDIT HERE."
NOTE="// Edit the canonical source in dr-mario-mods/fpga/copro and re-run sync_to_pocket.sh."

mkdir -p "$DST"
changed=0

vendor_one() {  # $1 = filename
  local f="$1" src="$SRC/$1" dst="$DST/$1" tmp
  tmp="$(mktemp)"
  printf '%s\n%s\n' "$STAMP" "$NOTE" > "$tmp"
  cat "$src" >> "$tmp"
  # compare bodies (skip the 2 header lines) so the date stamp alone never forces a rewrite
  if [ -f "$dst" ] && diff -q <(tail -n +3 "$dst") "$src" >/dev/null 2>&1; then
    rm -f "$tmp"; return 0
  fi
  echo "--- vendor: $f (new/changed) ---"
  [ -f "$dst" ] && diff <(tail -n +3 "$dst") "$src" | head -12 || echo "  (new file)"
  mv "$tmp" "$dst"; changed=$((changed+1))
}

for f in "${RTL[@]}"; do
  [ -f "$SRC/$f" ] || { echo "ERROR: missing $SRC/$f" >&2; exit 3; }
  vendor_one "$f"
done

# firmware hex: pure data (readmemh-parsed). The SHIPPED firmware is the co-sim-validated DELTA build
# (dbg_build.py all 0, md5 c87e60a1); build_copro_d3 / build_firmware / run_gate all DEFAULT to (or
# leave behind) the cell-exact BASE build (412615b2). To stop an RTL-only sync -- or a canonical tree
# that has drifted to the base build -- from silently shipping a firmware regression, we NEVER
# overwrite a differing vendored hex. Fail loudly instead. A deliberate firmware update sets
# ALLOW_HEX_UPDATE=1 AFTER validating cell-exactness via ./run_gate.sh.
#   (History: a blind sync here would have reverted the shipped CMD-6/7 delta engine under the r47b5
#    eval build -- presenting on silicon as "the new eval plays worse." See FIRMWARE.md.)
if [ -f "$SRC/$HEX" ]; then
  if [ ! -f "$DST/$HEX" ]; then
    cp "$SRC/$HEX" "$DST/$HEX"; echo "--- vendor: $HEX (initial, $(wc -l < "$DST/$HEX") lines) ---"; changed=$((changed+1))
  elif diff -q "$SRC/$HEX" "$DST/$HEX" >/dev/null; then
    : # canonical == vendored: firmware already in sync, nothing to do
  elif [ "${ALLOW_HEX_UPDATE:-0}" = "1" ]; then
    echo "--- vendor: $HEX (ALLOW_HEX_UPDATE=1: $(md5sum "$DST/$HEX" | cut -c1-8) -> $(md5sum "$SRC/$HEX" | cut -c1-8)) ---"
    cp "$SRC/$HEX" "$DST/$HEX"; changed=$((changed+1))
  else
    echo "ERROR: canonical firmware hex DIFFERS from the vendored (shipped) hex -- NOT overwriting." >&2
    echo "       canonical  $SRC/$HEX  md5 $(md5sum "$SRC/$HEX" | cut -c1-8)" >&2
    echo "       vendored   $DST/$HEX  md5 $(md5sum "$DST/$HEX" | cut -c1-8)" >&2
    echo "       RTL-only syncs must never touch shipped firmware. The shipped firmware is the DELTA" >&2
    echo "       build: 'python dbg_build.py all 0' (co-sim-validated cell-exact vs base; md5 c87e60a1)." >&2
    echo "       * If canonical drifted to the BASE build (build_copro_d3 / build_firmware / run_gate" >&2
    echo "         leave base behind), restore it:  python dbg_build.py all 0" >&2
    echo "       * If this IS a deliberate firmware change, validate via ./run_gate.sh then re-run" >&2
    echo "         with ALLOW_HEX_UPDATE=1." >&2
    exit 4
  fi
else
  echo "WARN: $SRC/$HEX missing -- regenerate the shipped firmware with 'python dbg_build.py all 0'." >&2
fi

# (re)generate the qip so Quartus compiles the vendored RTL. The hex is found via a SEARCH_PATH
# entry added in nes_pocket.qsf during the M3 apply (see M3 checklist) -- not listed here.
QIP="$DST/copro.qip"
{
  echo "# AUTO-GENERATED by sync_to_pocket.sh from dr-mario-mods/fpga/copro @ ${HASH}. DO NOT EDIT."
  for f in "${RTL[@]}"; do
    case "$f" in *.sv) t=SYSTEMVERILOG_FILE ;; *) t=VERILOG_FILE ;; esac
    printf 'set_global_assignment -name %-18s [file join $::quartus(qip_path) "%s"]\n' "$t" "$f"
  done
} > "$QIP"

echo "OK: vendored ${changed} item(s) into $DST ; wrote $(basename "$QIP")"
