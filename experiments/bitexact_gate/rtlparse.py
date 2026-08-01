"""Parse a LeafEval.sv for its baked-in eval constants + structural flags.

WHY: the project has been burned by python goldens that silently drifted from
the RTL (memory: dr-mario-golden-is-weekend-era; leaf_r47.py is ALREADY stale vs
the winner tree today).  This gate therefore never hardcodes the RTL's weights:
it re-parses the .sv it is about to co-simulate, and the parsed config is then
EMPIRICALLY verified by the Verilator run itself (a subtly-wrong parse cannot
pass level 2 -- the scores would mismatch).

Parse failures are LOUD: an unknown term in the combine, a missing expected
term, or disagreeing multi-site constants (the W_MATCHED 3-site hazard, memory:
dr-mario-wmatched-3site-edit) all raise instead of guessing.

Handles the three live structures:
  - winner tree   (matched@48 pre-scaled, 5-constant combine, delta engine)
  - canonical/promote (matched@60, r47-era combine, delta engine)
  - qa-wt legacy  (weekend structure: no matched / color-aware / nearest-2)
"""
from __future__ import annotations
import re

from common import make_w, make_fl, file_md5

_TERM_MAP = {
    "maxh": "maxh", "holes": "holes", "toprisk": "toprisk", "spawn": "spawn",
    "setup": "setup", "buried": "buried", "rdy_ext": "rdyext", "vrdy": "vrdy",
    "pollution": "poll",
}
_EXPECTED = set(_TERM_MAP.values())


class RtlParseError(RuntimeError):
    pass


def parse_leafeval(path):
    """-> dict(w=float64[16], fl=int32[3], meta=dict).  Raises RtlParseError."""
    src = open(path).read()

    # ---- combine block: from 'sco <= 16'dBIAS' to the terminating ';' ----
    blocks = re.findall(r"sco\s*<=\s*16'd(\d+)\s*((?:[^;])*?);", src)
    if len(blocks) != 1:
        raise RtlParseError("%s: expected exactly 1 'sco <= 16'dN ...;' combine, found %d"
                            % (path, len(blocks)))
    bias, body = int(blocks[0][0]), blocks[0][1]

    weights = {}
    matched_in_combine = False
    seen_terms = set()
    # every +/- term in the body must be understood; anything else is a hard fail
    for line in body.splitlines():
        line = line.split("//")[0].strip()
        if not line:
            continue
        m = re.fullmatch(r"([+-])\s*16'd(\d+)\s*\*\s*(\w+?)(_p)?", line)
        if m:
            sign, const, term = m.group(1), int(m.group(2)), m.group(3)
            if term not in _TERM_MAP:
                raise RtlParseError("%s: UNKNOWN combine term '%s' -- the RTL grew a "
                                    "term this gate does not model; refusing to guess"
                                    % (path, term))
            name = _TERM_MAP[term]
            expect_sign = "+" if name in ("setup", "rdyext", "vrdy") else "-"
            if sign != expect_sign:
                raise RtlParseError("%s: term %s has sign %s (model expects %s)"
                                    % (path, term, sign, expect_sign))
            if name in seen_terms:
                raise RtlParseError("%s: term %s appears twice in combine" % (path, term))
            seen_terms.add(name)
            weights[name] = const
            continue
        m = re.fullmatch(r"\+\s*matched60(_p)?", line)
        if m:
            matched_in_combine = True
            continue
        raise RtlParseError("%s: unparseable combine line: %r" % (path, line))

    missing = _EXPECTED - seen_terms
    if missing:
        raise RtlParseError("%s: combine is missing expected terms: %s" % (path, missing))

    # ---- matched weight: pre-scaled accumulator, possibly multi-site ----
    matched_w = 0
    if matched_in_combine:
        acc = [int(x) for x in re.findall(r"matched60\s*<=\s*matched60\s*\+\s*13'd(\d+)", src)]
        # dd_matched: closed-form delta site(s) -- take the TRUE arms of the full
        # statement (the ': 13'd0' false arms and 'dd_matched <= 13'd0' resets are
        # inits, not weight sites)
        dd = []
        for stmt in re.findall(r"dd_matched\s*<=(.*?);", src, re.S):
            dd += [int(x) for x in re.findall(r"\?\s*13'd(\d+)", stmt)]
        sites = acc + dd
        if not acc:
            raise RtlParseError("%s: matched60 in combine but no accumulate site found" % path)
        if len(set(sites)) != 1:
            raise RtlParseError("%s: matched sites DISAGREE %s (acc) %s (dd_matched) -- "
                                "the 3-site W_MATCHED hazard; refusing" % (path, acc, dd))
        matched_w = sites[0]

    # ---- structural flags (heuristic here; PROVEN by the level-2 co-sim run) ----
    color_aware = 1 if re.search(r"\bcurlen\b", src) else 0
    nearest2 = 1 if re.search(r"\bvseen\b", src) else 0
    fl = make_fl(color_aware=color_aware, nearest2=nearest2,
                 matched=1 if matched_in_combine else 0)

    # ---- imm constants (NODE reward) ----
    mi = re.search(r"imm\s*<=\s*16'd(\d+)\s*\*\s*rv_vir\s*\+\s*16'd(\d+)\s*\*\s*rv_cells", src)
    imm = (int(mi.group(1)), int(mi.group(2))) if mi else None

    w = make_w(bias=bias, matched=matched_w, cross=0, **weights)
    meta = dict(path=path, md5=file_md5(path),
                weights={"bias": bias, "matched": matched_w, **weights},
                flags=dict(color_aware=color_aware, nearest2=nearest2,
                           matched=1 if matched_in_combine else 0),
                imm=imm,
                has_delta_engine=bool(re.search(r"\bS_DPOL\b", src)),
                has_node_cmd=bool(re.search(r"cmd\s*==\s*4'd4", src)))
    return dict(w=w, fl=fl, meta=meta)


if __name__ == "__main__":
    import json, sys
    r = parse_leafeval(sys.argv[1])
    print(json.dumps(r["meta"], indent=2))
