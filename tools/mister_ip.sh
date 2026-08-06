#!/bin/bash
# Resolve the MiSTer robustly: mDNS first, then ARP-scan for its known MAC.
# The box DHCP-wanders (.225/.226 observed) AND mDNS drops after some reboots.
MAC="02:03:04:05:06:07"
IP=$(getent hosts MiSTer.local 2>/dev/null | awk '{print $1; exit}')
if [ -n "$IP" ] && ping -c1 -W1 "$IP" >/dev/null 2>&1; then echo "$IP"; exit 0; fi
for ip in $(seq 220 240); do ping -c1 -W1 10.42.0.$ip >/dev/null 2>&1; done
IP=$(ip neigh | awk -v m="$MAC" 'tolower($5)==tolower(m) && $1 ~ /^10\.42\.0\./ {print $1; exit}')
[ -n "$IP" ] && echo "$IP" && exit 0
echo "10.42.0.226"   # last-known fallback
