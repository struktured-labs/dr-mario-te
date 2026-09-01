# Errata + clock verification (cvc_ab)

## ERRATUM: a wrong DATE in prose, 2026-09-01

Commit `c4e9819`'s message says the first live round transition was
"detected 2026-09-01T23:57Z". **The correct stamp is `2026-08-31T23:57:16Z`.**
The same slip appeared in the report prose for the A/B start, which was
`2026-08-31T23:59:39Z`, not 2026-09-01T23:59Z.

Cause: the run began minutes before UTC midnight, and I carried the 09-01 date
onto the 23:5x times when writing them out by hand.

**Nothing computed used the wrong value, and no analysis is affected.** Every
piece of machinery keys off the epoch, never off prose:
* the transition detector consumes `t_epoch` from the CSV;
* `adjudicate.py` takes an epoch on the command line and derives the video offset
  from it -- the adjudicated death used epoch `1788221151` = `2026-09-01T00:05:51Z`,
  which is correct, and the banked frame
  `death1_20260901T000532Z_TOPOUT_P1.png` is correctly dated;
* the CSV's own `iso` column was right all along (`2026-08-31T23:57:16Z`).

The commit message is left as written rather than rewriting history; this file is
the correction of record.

## CLOCK VERIFICATION (the check that mattered)

A day-skew between the boxes would break arm-to-video attribution silently: every
death would cut the wrong slice of footage and classify confidently wrong. Verified
2026-09-01T00:13:11Z, all three sources agree:

| source | UTC | epoch |
|---|---|---|
| this box (analysis + CSV stamps) | 2026-09-01T00:13:09Z | -- |
| bluemage (freeze_watch stamps, MiSTer grabs) | 2026-09-01T00:13:11Z | 1788221591 |
| blackmage (OBS recording host) | 2026-09-01T00:13:11Z | 1788221591 |

Epochs are identical on both remote boxes; this box's read was issued 2 s earlier.
Local zone is EDT = UTC-4 on all three (blackmage: `2026-08-31T20:13:11 EDT`),
which is what `adjudicate.VIDEO_T0` assumes when converting the OBS filename
`20260831_182902` to `2026-08-31T22:29:02Z`.

⭐ **The mapping is also confirmed EMPIRICALLY, independent of any date reasoning**:
the video decoder reads 47/25 at exactly the instant the MiSTer poller logged 47/25
(`2026-09-01T00:05:24Z`). Two independent capture paths agreeing on a counter value
at one instant validates the whole wall-clock -> video-offset chain end to end. That
cross-check, not the arithmetic, is why the attribution can be trusted.
