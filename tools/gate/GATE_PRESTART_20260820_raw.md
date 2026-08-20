
## G1 probe6 18000 (rc=0)
[p6_hardened-prestart-20260820_18000] OK try 1
SUMMARY tag=p6_hardened-prestart-20260820_18000 cart=p6_hardened-prestart-20260820_18000_mmc1.nes cartid=? nonce=86b560-a82860 frames=18000 goes=178 dones=172 sr_loads=89881 sr_resets=71982 MIXED_total=0 MIXED_boot=0 MIXED_PRG_nonboot=0 soft8036=2 wipes=14 brk_a02e=0 matches_started=15 matches_ended=14 clean_ends=14 ABORT_4to0=0 pills=163 tuck_opp=1 tuck_pub=1 tuck_desc=3 desc_changed=0 TUCK_EXEC_D1=1 TUCK_EXEC_D2=1 fail_hi=0 fail_lo=2 fail_reach=0 fail_land=0
D135 blocked=10 leaked=0 guard=ON

## G2 sggate pause2e 9000 (rc=0)
SUMMARY tag=sg_hardened-prestart-20260820_pause2e_m4_9000 arm=pause2e verdict=PAUSED_THEN_RESUMED pauseIters=240 entryHits=1 exitTaken=1 distinctP2Y=6 frames=1267 goes=8 dones=7

## G3 hgate unpause o3 4000 s114 (rc=0)
SUMMARY tag=hg_hardened-prestart-20260820_o3_4000_s114_unpause arm=unpause orient=3 verdict=RESUMED wedgeFrame=1471 exitTaken=1 distinctP2Y=7 pauseIters=304 entryHits=1 entryFrame=1170 servedN=0 navStartHits=34 navInMode4=0 frames=1651 goes=13 dones=12

## G4 probe9 arm 9000 wedge129_ram.hex (rc=0)
SUMMARY tag=p136prestart-arm mode=arm cart=p136prestart-arm_mmc1.nes cartid=? nonce=86b598-e93b00 frames=4860 inj_f=3000 verdict=NO_WEDGE fc_values=256 step_left_at=3002 field_changed_at=3002 mode_left_at=-1 goes=47 dones=45
