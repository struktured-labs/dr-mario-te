#!/bin/bash
# settle lane Mesen batch 5: the fair candidate (couch DRSETTLE=3 DRSETTLEPIN=0 DRPROPHFIRST=1): NMI max, corpus, tempo
cd "$(dirname "$0")/../.."
C=tmp/carts
LN_HUMAN=1 LN_SEED=7 LN_POKE_EVERY=30 timeout 5400 tools/lateflip/run_nmi.sh CH_D $C/couch_fair_D.nes tools/lateflip/cvc_nmi.lua tmp/audit/couch_fair_D_ir.json 40000 2>&1 | tail -3
ST_SETTLE=3 ST_HUMAN=1 ST_SEED=11 ST_POKE_EVERY=500 timeout 5400 tools/settle/run_probe.sh couchD_s11 $C/couch_fair_D.nes tools/settle/settle_probe.lua 60000 2>&1 | tail -1
ST_SETTLE=3 ST_HUMAN=1 ST_SEED=31 timeout 5400 tools/settle/run_probe.sh tempoD_s31 $C/couch_fair_D.nes tools/settle/settle_probe.lua 40000 2>&1 | tail -1
echo BATCH5_DONE
