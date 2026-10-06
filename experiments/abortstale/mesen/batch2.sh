#!/bin/bash
# abort-stale Mesen batch 2: the FINAL abort cart (b1b57638, JSR form) A arms, then the Mesen NMI witness runs.
O=/home/struktured/projects/dr_mario_rl/tmp/abort_stale
W=/home/struktured/projects/dr-mario-abortstale-wt
ARMS="A1488 AV1" $O/tools/batch.sh
cd $W
CA=$O/carts/drmario_te_couch_fair_abort_b1b57638.nes
CD=$O/carts/drmario_te_couch_fair_dbbb5007.nes
C=/home/struktured/projects/dr_mario_rl/tmp/fair_v1_replay/cases
# couch churn + garbage pokes, the settle lane's NMI-max settings (its D number: 12,644)
LN_HUMAN=1 LN_SEED=7 LN_POKE_EVERY=30 timeout 5400 tools/lateflip/run_nmi.sh CH_Dabort $CA tools/lateflip/cvc_nmi.lua tmp/census/couch_D_abort.ir.json 40000 2>&1 | tail -3
# the banked G2 V1 chained replay (21 stale edges -> real aborts) under the NMI witness, abort cart and D
LF_CASES=$C/cases_G2_fwa1ef31c8_chain.lua timeout 5400 tools/lateflip/run_nmi.sh LFN_G2_AV1 $CA tools/lateflip/lateflip_nmi.lua tmp/census/couch_D_abort.ir.json 20000 2>&1 | tail -3
LF_CASES=$C/cases_G2_fwa1ef31c8_chain.lua timeout 5400 tools/lateflip/run_nmi.sh LFN_G2_DV1 $CD tools/lateflip/lateflip_nmi.lua tmp/census/couch_D.ir.json 20000 2>&1 | tail -3
echo BATCH2_DONE
