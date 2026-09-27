# OPS_LOG — operational notes (not amendments; the registration is unchanged)

## 2026-08-24 ~01:30 EDT — redmage C-deep half REASSIGNED to blackmage
Team-lead order. redmage suspended mid-night (tailscale + LAN unreachable);
the fit must not wait on a sleeping laptop. The 266-game list
`cdeep_split_redmage.txt` runs on BLACKMAGE as unit `drm-cdeep-black2`
(`--set cdeep-redmage` = "the redmage LIST", executed locally). The C-DEEP
REGISTRATION is over the UNION of seeds and is unchanged; the split was
always operational. One-writer-per-seed is preserved by DISARMING the
redmage wake path FIRST: `launch_cdeep.sh` now hard-exits before any action
(no drm-cdeep-red unit was ever created on redmage; the script on this box
was the only trigger). If redmage wakes it does NOT join C-deep — it may
take the autopsy backlog after re-passing the cross-box gate, or idle.
