import re, sys, collections
def rows(path):
    out=[]
    for l in open(path, errors='replace'):
        if 'TUCKPILL' not in l: continue
        m=dict(re.findall(r'(\w+)=(-?\w+)', l))
        out.append(dict(appr=int(m['appr']), final=int(m['final']), trigY=int(m['trigY']),
                        hi=m['hi']=='true', lo=m['lo']=='true', px=m['pxAppr']=='true',
                        dwell=int(m['dwell']), land=int(m['land'])))
    return out

B='/home/struktured/projects/dr-mario-v8-wt/tmp/clean/'
sets={'u-func (synthetic, v8+tuck)': B+'u-func/probe6.log',
      'w-v1-func (tuck-v1, v8+tuck)': B+'w-v1-func/probe7.log',
      'u-ctl (synthetic, v8 PLAIN)': B+'u-ctl/probe6.log',
      'w-v1-ctl (tuck-v1, v8 PLAIN)': B+'w-v1-ctl/probe7.log'}

for name,p in sets.items():
    r=rows(p)
    if not r: print(f'{name}: no rows'); continue
    print(f'\n=== {name}  n={len(r)} ===')
    # classify
    def cls(x):
        if not x['hi']:  return 'A_never_engaged (descriptor late / not adopted)'
        if not x['lo']:  return 'B_engaged_no_switch'
        if not x['px']:  return 'C_switch_but_never_reached_approach'
        if x['land']==x['final']: return 'D_COMPLETED'
        if x['land']==x['appr']: return 'E_SWITCHED_BUT_STRANDED_on_approach'
        return 'F_other'
    c=collections.Counter(cls(x) for x in r)
    for k in sorted(c): print(f'  {c[k]:3d}  {k}')
    # completion vs trigger depth, only pills that ENGAGED (hi=true) -- latency excluded
    eng=[x for x in r if x['hi'] and x['lo']]
    if eng:
        print(f'  -- engaged+switched n={len(eng)}: completion by trigY ($0386; LOWER = DEEPER on board) --')
        by=collections.defaultdict(lambda:[0,0])
        for x in eng:
            ok = 1 if x['land']==x['final'] else 0
            by[x['trigY']][ok]+=1
        for t in sorted(by):
            bad,good=by[t]
            print(f'     trigY={t:2d} (board row {15-t:2d}): completed {good}/{good+bad}')
