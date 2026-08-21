#!/usr/bin/env bash
# respin-144 MANDATORY VIDEO-OUTPUT GATE (run ONLY inside the team-lead-brokered window).
# Usage: onbox_video_gate.sh /path/to/NES_theta400dblcanon_20260821_c0pin.rbf
# Requested-mode CTS/VIC must match spec for BOTH 1080p and 720p. One approved SD write:
# MiSTer.ini video_mode 8->4 and byte-exact restore (hash-verified). Core goes to /tmp only.
set -uo pipefail
RBF="${1:?usage: onbox_video_gate.sh <rbf>}"
BOX=root@10.42.0.233
S() { sshpass -p 1 ssh -o StrictHostKeyChecking=no -o ConnectTimeout=5 $BOX "$@"; }
# NOTE: exactly the standing-order connection form (sshpass -p 1, no identity probing). A
# connection that would prompt fails loudly instead (containment rule, 4 popup incidents).
SC() { sshpass -p 1 scp -o StrictHostKeyChecking=no -o ConnectTimeout=5 "$1" "$BOX:$2"; }
fails=0
chk() { if [ "$2" = 1 ]; then echo "PASS $1: $3"; else echo "FAIL $1: $3"; fails=$((fails+1)); fi }

adv() { # print "CTS VIC PLLOK"
  S 'c4=$(i2cget -y 1 0x39 0x04); c5=$(i2cget -y 1 0x39 0x05); c6=$(i2cget -y 1 0x39 0x06);
     vic=$(i2cget -y 1 0x39 0x3e); pll=$(i2cget -y 1 0x39 0x9e);
     echo $(( ((c4&0xF)<<16) | (c5<<8) | c6 )) $(( vic>>2 )) $(( (pll>>4)&1 ))'
}

lm=$(md5sum "$RBF" | cut -d' ' -f1)
SC "$RBF" /tmp/respin144_c0pin.rbf
rm5=$(S 'md5sum /tmp/respin144_c0pin.rbf' | cut -d' ' -f1)
chk V0-deploy $([ "$lm" = "$rm5" ] && echo 1 || echo 0) "on-box rbf md5 $rm5 == staged $lm (hash the core that boots)"

ini5=$(S 'md5sum /media/fat/MiSTer.ini' | cut -d' ' -f1)
S 'cp -p /media/fat/MiSTer.ini /tmp/MiSTer.ini.respin144_backup'   # tmpfs backup, pre-anything
echo "ini md5 before gate: $ini5 (backup in /tmp/MiSTer.ini.respin144_backup)"

# Leg 1: current ini (video_mode=8, 1080p60): expect VIC=16 CTS=148500
S 'echo "load_core /tmp/respin144_c0pin.rbf" > /dev/MiSTer_cmd'; sleep 12
read cts vic pll <<< "$(adv)"
chk V1-1080p $([ "$cts" = 148500 ] && [ "$vic" = 16 ] && [ "$pll" = 1 ] && echo 1 || echo 0) "1080p leg: CTS=$cts (want 148500) VIC=$vic (want 16) PLL=$pll"

# Leg 2 (THE fix proof, approved SD write): video_mode 8->4 (720p60): expect VIC=4 CTS=74250.
# Broken cores emitted 148500 here.
S 'sed -i "s/^video_mode=8/video_mode=4/" /media/fat/MiSTer.ini'
S 'echo "load_core /tmp/respin144_c0pin.rbf" > /dev/MiSTer_cmd'; sleep 12
read cts vic pll <<< "$(adv)"
chk V2-720p $([ "$cts" = 74250 ] && [ "$vic" = 4 ] && [ "$pll" = 1 ] && echo 1 || echo 0) "720p leg: CTS=$cts (want 74250, stuck-C3 defect would show 148500) VIC=$vic (want 4) PLL=$pll"

# Restore byte-exact + hash-verify (the granted exception ends here)
S 'cp -p /tmp/MiSTer.ini.respin144_backup /media/fat/MiSTer.ini'
post=$(S 'md5sum /media/fat/MiSTer.ini' | cut -d' ' -f1)
chk V3-restore $([ "$post" = "$ini5" ] && echo 1 || echo 0) "ini restored byte-exact ($post == $ini5)"
S 'echo "load_core /tmp/respin144_c0pin.rbf" > /dev/MiSTer_cmd'; sleep 12
read cts vic pll <<< "$(adv)"
chk V4-reverify $([ "$cts" = 148500 ] && [ "$vic" = 16 ] && echo 1 || echo 0) "post-restore: CTS=$cts VIC=$vic"

echo; [ "$fails" = 0 ] && echo "VIDEO GATE: PASS (both requested modes follow)" || echo "VIDEO GATE: $fails FAILURE(S)"
exit "$fails"
