#!/bin/bash
# settle lane Mesen batch 2: tempo arms (a)/(b)/(c), NMI max-cycle census runs, G2/G3/G4 replays (one Mesen at a time)
cd "$(dirname "$0")/../.."
KIT=/home/struktured/projects/dr_mario_rl/tmp/couch_kit/lateguard_20261003
C=tmp/carts
run() { tag=$1; shift; rom=$1; shift; probe=$1; shift; frames=$1; shift
  env "$@" timeout 5400 tools/settle/run_probe.sh "$tag" "$rom" "$probe" "$frames" 2>&1 | tail -2; }
# tempo: same seed, no pokes (settle pills only), human seat
run tempoA_s31 $KIT/drmario_te_couch_lateguard_464a4b75.nes tools/settle/settle_probe.lua 40000 ST_SETTLE=15 ST_HUMAN=1 ST_SEED=31
run tempoB_s31 $C/couch_settle3_nopin.nes tools/settle/settle_probe.lua 40000 ST_SETTLE=3 ST_HUMAN=1 ST_SEED=31
run tempoC_s31 $C/arm_couch_settle15_nopin.nes tools/settle/settle_probe.lua 40000 ST_SETTLE=15 ST_HUMAN=1 ST_SEED=31
# Mesen NMI max-cycle census (review lane's tooling + settings: CH_* couch churn + pokes/30 f, CVC_* CvC churn)
LN_HUMAN=1 LN_SEED=7 LN_POKE_EVERY=30 timeout 5400 tools/lateflip/run_nmi.sh CH_S3np $C/couch_settle3_nopin.nes tools/lateflip/cvc_nmi.lua tmp/audit/couchS3np_ir.json 40000 2>&1 | tail -3
LN_SEED=7 timeout 5400 tools/lateflip/run_nmi.sh CVC_S3np $C/cvc_settle3_nopin.nes tools/lateflip/cvc_nmi.lua tmp/audit/cvcS3np_ir.json 40000 2>&1 | tail -3
# G2/G3/G4 banked copro timelines (fw 1488e158), stock vs fair, same harness
for g in G2 G3 G4; do
  timeout 5400 tools/lateflip/run_lateflip.sh ${g}_464 $KIT/drmario_te_couch_lateguard_464a4b75.nes tmp/settle/cases/cases_${g}.lua 60000 2>&1 | tail -1
  timeout 5400 tools/lateflip/run_lateflip.sh ${g}_S3np $C/couch_settle3_nopin.nes tmp/settle/cases/cases_${g}.lua 60000 2>&1 | tail -1
done
echo BATCH2_DONE
