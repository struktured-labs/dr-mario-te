#!/bin/bash
# settle lane Mesen batch 1 (sequential; each run waits for the single Mesen seat)
cd "$(dirname "$0")/../.."
KIT=/home/struktured/projects/dr_mario_rl/tmp/couch_kit/lateguard_20261003
C=tmp/carts
run() { tag=$1; shift; rom=$1; shift; probe=$1; shift; frames=$1; shift
  env "$@" timeout 5400 tools/settle/run_probe.sh "$tag" "$rom" "$probe" "$frames" 2>&1 | tail -2; }
run couchS3np_s11 $C/couch_settle3_nopin.nes tools/settle/settle_probe.lua 60000 ST_SETTLE=3 ST_HUMAN=1 ST_SEED=11 ST_POKE_EVERY=500
run couchS3_s11   $C/couch_settle3.nes       tools/settle/settle_probe.lua 60000 ST_SETTLE=3 ST_HUMAN=1 ST_SEED=11 ST_POKE_EVERY=500
run cvc387_s21    $KIT/drmario_cvc_lateguard_387bb7bd.nes tools/settle/settle_probe.lua 60000 ST_SETTLE=15 ST_HUMAN=0 ST_SEED=21 ST_POKE_EVERY=400
run cvcS3np_s21   $C/cvc_settle3_nopin.nes   tools/settle/settle_probe.lua 60000 ST_SETTLE=3 ST_HUMAN=0 ST_SEED=21 ST_POKE_EVERY=400
run mutNG_s11     $C/mut_couch_settle3_noguard.nes tools/settle/settle_probe.lua 30000 ST_SETTLE=3 ST_HUMAN=1 ST_SEED=11 ST_POKE_EVERY=0 ST_PRAND=0.5
run base_med      /home/struktured/projects/dr-mario-mods/drmario.nes tools/settle/base_gravity_probe.lua 60000 BS_SPEED=1 BS_LEVEL=11
run base_hi       /home/struktured/projects/dr-mario-mods/drmario.nes tools/settle/base_gravity_probe.lua 60000 BS_SPEED=2 BS_LEVEL=11
echo BATCH1_DONE
