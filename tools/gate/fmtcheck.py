import re, sys, glob, os
# fmtcheck.py -- PRE-FLIGHT for any instrument whose payload is a single end-of-run line.
#
# WHY THIS EXISTS. A SUMMARY line fires ONCE, at the very end of an 18,000-frame run. A
# format/arg mismatch there costs the ENTIRE run and produces exactly the summary-less log
# we treat as void -- the worst possible placement for a defect, because nothing earlier
# warns you and the cost is only paid after all the compute is spent. Found live: probes
# 5/6/7 had 30 specifiers against 27 args after an edit that touched the format string and
# not the arg list. Invisible to reading; visible only to execution or to this check.
#
# Usage:  python3 tools/gate/fmtcheck.py [file.lua ...]      (default: all of tools/gate/*.lua)
# Exit 1 on any mismatch, so it can gate a launch.
def split_top(s):
    out, depth, cur, i, instr = [], 0, '', 0, None
    while i < len(s):
        c = s[i]
        if instr:
            if c == '\\': cur += s[i:i+2]; i += 2; continue
            if c == instr: instr = None
        elif c in '"\'': instr = c
        elif c in '([{': depth += 1
        elif c in ')]}': depth -= 1
        elif c == ',' and depth == 0:
            out.append(cur.strip()); cur = ''; i += 1; continue
        cur += c; i += 1
    if cur.strip(): out.append(cur.strip())
    return out

targets = sys.argv[1:] or sorted(glob.glob(os.path.join(os.path.dirname(os.path.abspath(__file__)), '*.lua')))
bad = 0
checked = 0
for p in targets:
    src = open(p, errors='replace').read()
    checked += 1
    for m in re.finditer(r'string\.format\(', src):
        i = m.end(); depth = 1; j = i; instr = None
        while j < len(src) and depth:
            c = src[j]
            if instr:
                if c == '\\': j += 2; continue
                if c == instr: instr = None
            elif c in '"\'': instr = c
            elif c == '(': depth += 1
            elif c == ')': depth -= 1
            j += 1
        body = src[i:j-1]
        parts = split_top(body)
        if not parts: continue
        # the format string may be a concatenation of literals
        fs = parts[0]
        lits = re.findall(r'"((?:[^"\\]|\\.)*)"', fs)
        if not lits: continue
        fmt = ''.join(lits)
        nspec = len(re.findall(r'%[-+ #0-9.]*[dsxXfg]', fmt))
        nargs = len(parts) - 1
        line = src[:m.start()].count('\n') + 1
        name = os.path.basename(p)
        if nspec != nargs:
            bad += 1
            print(f'  MISMATCH {name}:{line}  specifiers={nspec} args={nargs}')
            print(f'    fmt head: {fmt[:70]!r}')
print(f'FORMAT ARITY over {checked} file(s):', 'ALL OK' if not bad else f'{bad} MISMATCH(ES)')
sys.exit(1 if bad else 0)
