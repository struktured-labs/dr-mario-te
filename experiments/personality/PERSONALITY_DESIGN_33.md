# Personality Select — design doc (task #33)

User request (2026-08-02): "lets make sure the final cart has personalities or style
knobs too." This doc turns the week's MEASURED arms into a named roster + the
architecture for selecting them, and prices the engineering per option.

## 1. Roster (every entry is a measured configuration, no speculation)

| Personality | Config | Evidence | Feel |
|---|---|---|---|
| **COMBO STOMPER** (default) | chain180 eval + fast tempo (MT=12/K=32) | 70.9% h2h vs prior champion, garbage-mediated (+16.8 with attacks on) | the champion: builds a dump channel, rains chains |
| **CLASSIC** | chain180 + original commit gates | tempo-rig measured; household-preferred pacing (v3 cart) | same brain, more deliberate hands |
| **RACER** | lnk1 eval | 60.2% holdout-confirmed; wins by out-clearing (55.1% even with attacks off) | clean, fast, chain-light — dr_lulu's stylistic cousin |
| **SHOWOFF** | chain180 + cheap instant-double dose (wcells15) | #26: win-rate wash (~49%), but converts singles→cascades, fixes the abandoned-material aesthetic | flashier clears at no measured strength cost |
| **BRAWLER** (beatable) | wcells60 dose | measured 32.6% — deliberately exploitable | the "hard but beatable" tier (cf. T&DM Hard, which dr_lulu rates beatable) |
| **SPARRING** (easy) | native 6502 depth-1 | DRP1NATIVE lineage, intentionally artless | the warm-up dummy |

Presentation prior art (task #45): SNES T&DM color-codes its three CPU tiers by virus
color (Blue=Easy / Yellow=Med / Red=Hard) — difficulty as visual identity. Our version:
personality named on the title/STUDY screen (branding tiles already exist per-cart).

## 2. The architectural fork: what's cart-cheap vs RTL-expensive

- **Cart-side knobs (cheap, per-personality TODAY as separate .nes files):** tempo gates
  (MT/K), nav behavior, sparring-tier P1. Multiple personalities = multiple romgen builds.
  This is the CURRENT de-facto mechanism (v2/v3/v4 carts on the Pocket SD).
- **Eval-side differences (chain180 vs lnk1 vs dose variants) live in RTL synthesis
  constants (LeafEval S_DONE2) — NOT hex-patchable (established: "arm swap = hex patch"
  REFUTED).** Single-cart multi-personality therefore requires the **weights-in-registers
  refactor**: promote the personality-differentiating constants to writable registers
  (defaulting to STOMPER values at reset), mapped into the existing $70xx window; the
  driver pokes the selected personality's vector at match start. Cost: an RTL change +
  one Quartus resynthesis per PLATFORM (not per personality — that's the entire point),
  timing re-closure (87% ALM headroom known), and a py65/co-sim gate proving
  register-default == today's synthesized champion bit-exactly (the bitexact-gate
  infrastructure covers this pattern).
- lnk1 additionally needs the LINK plane in its board upload — check whether that shipped
  in the current RTL (link/chain work landed the link plane; verify the driver upload path
  feeds it for the lnk1 weights to mean anything).

## 3. Selection UX options (pick one when the user weighs in)

a. **Level-select encoding** (zero new UI): personality = level row chosen at the
   VS-CPU menu (e.g., L11 = STOMPER, L12 = RACER, ...). Cheap, discoverable by
   documentation only.
b. **Held-button at boot** (cheap): D-pad direction held during title → personality;
   branding tile names it. One driver hook + tile write.
c. **Menu patch** (expensive, prettiest): a STUDY-style select screen. Real 6502 UI work +
   free-space negotiation — defer unless the user wants it for the public release.

Recommendation: (b) for the household carts now, (a) as the fallback, (c) only for a
public "arcade" release build.

## 4. Phasing

1. **P0 (this week, cart-side only):** ship what exists as named cart files — STOMPER
   and CLASSIC (built), SPARRING (the CvC P1 path). CORRECTION from first draft: SHOWOFF's
   wcells15 dose and RACER's lnk1 are EVAL-side (RTL synthesis constants), so they cannot
   join via cart flags — they arrive at P1 (register weights) or via their own compiled
   cores, which is a per-personality Quartus cost P1 exists to avoid.
2. **P1 (one Quartus cycle):** weights-in-registers refactor + held-button select →
   single cart, all personalities. Ride-along: the $5089 xlate passenger (#33's original
   note) and any tuck-v3 mailbox needs if #17 revives.
3. **P2 (polish):** named branding per personality on title/pause; T&DM-style color cue.

## Open questions for the user
- Which selection UX (a/b/c)?
- Roster cut: is BRAWLER (deliberately beatable) wanted, or does SPARRING cover it?
- Public-release scope: personalities in the romhacking.net TE line, or household-only?
