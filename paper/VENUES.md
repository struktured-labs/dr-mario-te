# Venues & submission timeline

> Research date: **2026-07-22**. `(verified)` = from the venue's current-cycle page; `(est.)`
> = inferred from the venue's historical cadence because the official CFP isn't posted yet —
> re-verify before relying on it. Bottom line: **all 2026 game-AI deadlines are closed;
> primary target is IEEE CoG 2027.**

## TL;DR

- **Every 2026 game-AI venue is already closed** (CoG 2026, AIIDE 2026, FDG 2026). CoG 2026
  (Madrid, **Sept 1–4, 2026**) even *precedes* our Sept 12–13 RWE demo, so it could not carry
  the human-eval data regardless.
- **PRIMARY: IEEE CoG 2027** — U-Aizu, Japan, **Aug 2–5, 2027 (est.)**; full-paper deadline
  **~March 1, 2027 (est., plan for late-Feb)**. First archival deadline that matches the
  paper's center of gravity *and* sits far enough past the demo to fold in human-eval results.
- **arXiv preprint** in **late Sept / early Oct 2026** (right after the demo) — allowed by both
  CoG (double-blind but preprints permitted) and AIIDE (AAAI, preprints permitted).
- **IEEE Transactions on Games (ToG)** = the no-deadline journal extension/capstone.
- **Hardware spinoff** (optional, non-overlapping): **FCCM 2027** (~mid-Jan 2027, best runway)
  or **ISFPGA "FPGA 2027"** (~early Oct 2026, prestigious but fast). DATE 2027 (Sept 20, 2026)
  is reachable but too tight for demo data.
- **Fallback: AIIDE 2027** — its deadline (~May–June 2027, est.) lands *after* CoG 2027
  notification, so a CoG miss can be revised into AIIDE with no idle time.

## Game-AI venues

### IEEE Conference on Games (CoG) — PRIMARY
- **CoG 2026 (CLOSED, format reference only)** — Madrid, Complutense U., **Sept 1–4, 2026**.
  Full papers were due **Mar 17, 2026**; auxiliary **May 14**; demo/industry **Jun 30**.
  Categories & limits (use as the 2027 guide): short **4 pp**, competition **8 pp**, vision
  **8 pp**, full technical typically **8 pp** IEEE 2-column, limits *include* references.
  **Double-blind — anonymize or desk-reject.** https://cog2026.org/ · https://cog2026.org/call-auxiliary
- **CoG 2027 (TARGET)** — University of Aizu, Aizuwakamatsu, Fukushima, Japan.
  Dates **Aug 2–5, 2027 (est.**; one secondary source said Jul 25–28 — treat as early Aug).
  Full-paper deadline **~March 1, 2027 (est.**; a conflicting snippet said Jan 15 — the
  official CFP is not yet posted; **plan for late-Feb 2027** to be safe, since CoG 2027 runs ~a
  month earlier than 2026). Expect the same track structure + double-blind + IEEE 2-column.
  Official site (live, sparse): https://cog2027.u-aizu.ac.jp/
  **Why primary:** matches game-AI + fairness-methodology + benchmark-corpus contributions; ~5.5
  months after the demo → comfortable write-up; the task names CoG as primary.

### AIIDE (AAAI Conf. on AI and Interactive Digital Entertainment) — FALLBACK
- **AIIDE 2026 (CLOSED)** — UFMG, Belo Horizonte, Brazil, **Nov 9–13, 2026**; abstracts were
  **Jun 19, 2026**. https://sites.google.com/view/aiide2026/ · http://aiide.org/
- **AIIDE 2027 (unannounced)** — historical pattern Oct–Nov 2027, deadline **~May–June 2027
  (est.)**. Viable secondary game-AI target; deadline falls *after* CoG 2027 notification →
  clean fallback. (AAAI forbids concurrent archival multiple-submission — one at a time.)

### FDG (ACM Foundations of Digital Games) — SECONDARY
- **FDG 2026 (CLOSED)** — Copenhagen, **Aug 10–13, 2026**; regular papers were Dec 15, 2025.
  https://fdg2026.org/call-for-papers/
- **FDG 2027 (unannounced)** — regular deadline **~mid-Dec 2026 (est.)**; potentially the
  *earliest* post-demo archival deadline, but FDG is secondary to CoG for this work.

### IEEE Transactions on Games (ToG) — JOURNAL / no deadline
- **Rolling submission**, target ≤3 months to first decision, immediate Xplore + DOI on accept;
  **double-anonymous since Jan 1, 2025.** Best used as the CoG paper's journal extension
  (~≥30% new material: fuller corpus analysis, more human-eval, deeper hardware
  characterization). https://transactions.games/submit/submission-guidelines

## Hardware-systems spinoff venues (optional, keep non-overlapping with the CoG paper)

| Venue | Next reachable | Deadline | Runway vs demo | Notes |
|---|---|---|---|---|
| **ISFPGA "FPGA 2027"** | ~Feb 2027 | abstract **~late Sept 2026**, paper **~early Oct 2026** (est.) | tight but reachable | most prestigious FPGA venue; fits "AI game-player as in-cart FPGA coprocessor" |
| **DATE 2027** | Mar 22, 2027, Dresden | **Sept 20, 2026** (verified) | **too tight** for demo data | https://www.date-conference.com/date-2027-call-papers |
| **FCCM 2027** | ~May 2027 | **~mid-Jan 2027** (est.) | **best runway** | https://www.fccm.org/ |
| **FPL 2027** | ~Sept 2027 | **~April 2027** (est.) | latest | https://2026.fpl.org/calls/call-for-papers/ |

Recommendation within this group: **FCCM 2027 (~mid-Jan 2027)** for a comfortable "second 6502
+ RTL accelerator in cartridge address space" systems paper; **ISFPGA FPGA 2027** if you can
move fast right after the demo. Keep it architecturally focused (RTL accelerator, mapper,
timing closure) and distinct from the CoG game-AI/methodology paper to stay clear of
double-submission rules.

## arXiv preprint

- **Endorsement policy tightened Jan 21, 2026:** institutional email alone no longer qualifies.
  Either (a) institutional email **+** a prior arXiv-accepted paper in the same domain, or (b)
  a personal endorsement from an established arXiv author in cs.AI or cs.AR. **If this is a
  first arXiv paper, line up an endorser now.** https://blog.arxiv.org/2026/01/21/attention-authors-updated-endorsement-policy/
- **Moderation/timing:** moderated, usually 1–2 business days; post at least a week before you
  want it public. Primary category **cs.AI**, cross-list **cs.AR**.
- **Preprints are permitted** by both CoG (double-blind: anonymize the submitted PDF; don't
  self-cite in a de-anonymizing way; reviewers are instructed not to hunt identities) and AIIDE
  (AAAI: only *archival* concurrent publication is barred; arXiv is non-archival). Neither
  forbids a preprint.

## Recommended timeline (single primary deadline: CoG 2027 full paper)

1. **Now → early Sept 2026** — Draft the paper. Instrument the **RWE Hartford demo (Sept 12–13,
   2026)** as a *pre-registered human-evaluation session*: fix the metrics in advance (win/clear
   rate vs demonstrated-caliber humans, fairness/latency telemetry, perceived-difficulty
   survey). Secure an arXiv endorser if needed. Do the meatfighter head-to-head (see `CLAIMS.md`).
2. **~Sept 20–30, 2026** (post-demo) — Post the **arXiv preprint** (cs.AI + cs.AR) with demo
   results folded in. Establishes priority for the coprocessor + corpus contributions.
3. **Fall 2026 → Jan 2027** (optional) — Hardware spinoff to **ISFPGA FPGA 2027** (early Oct, if
   fast) or **FCCM 2027** (mid-Jan, comfortable). Non-overlapping with the CoG paper.
4. **~Feb 27 → Mar 1, 2027** — Submit the **anonymized full paper to CoG 2027**. Notification
   ~May–June 2027; camera-ready early summer; present Aug 2–5, 2027.
5. **Mid-2027 (post-acceptance)** — Prepare the **IEEE ToG** journal extension (rolling; ≥~30%
   new material). Archival capstone, no deadline pressure.
6. **Fallback** — If CoG 2027 rejects, notification precedes the **AIIDE 2027** deadline
   (~May–June 2027); revise and resubmit with no idle time.

## Caveats on inferred dates
CoG 2027's exact deadline (est. ~Mar 1; conflicting Jan 15 snippet) and dates (est. Aug 2–5)
are **not yet on an official CFP** — recheck https://cog2027.u-aizu.ac.jp/ periodically. FPGA
2027, FCCM 2027, FPL 2027, FDG 2027, AIIDE 2027 are cadence-based estimates. DATE 2027 (Sept
20, 2026) and all 2026 editions are verified from current pages.
