import re, sys
# Verify every string.format(...) in the probes has #specifiers == #args.
# Motivation: the SUMMARY fires ONCE, at the very end of a 12k-frame run. A format/arg
# mismatch there destroys the whole run's result and nothing earlier warns you.
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

bad = 0
for n in (5, 6, 7, 8):
    p = f'/home/struktured/projects/dr-mario-v8-wt/tools/gate/probe{n}.lua'
    src = open(p).read()
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
        if nspec != nargs:
            bad += 1
            print(f'  MISMATCH probe{n}.lua:{line}  specifiers={nspec} args={nargs}')
            print(f'    fmt head: {fmt[:70]!r}')
print('FORMAT ARITY:', 'ALL OK' if not bad else f'{bad} MISMATCH(ES)')
sys.exit(1 if bad else 0)
