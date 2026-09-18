from pathlib import Path
p=Path('.github/build/live_r19_thousand_sons_cleanup.py')
s=p.read_text(encoding='utf-8')
old="""    # overwrite requirement behavior: XV AND (normal OR fellow)
    for g in (dg,pg):
        # min baseline zero
        for c in list(g.find(C('constraints')) or []):
            if c.get('type')=='min': c.set('value','0')
        add_modifier(g,g.get('id')+'-hide-no-brother','set','hidden','true',
                     groups=[('and',[cond('lessThan',1,normal.get('id'),'root-entry'),cond('lessThan',1,fellow.get('id'),'root-entry')])])
        minc=next(c for c in g.find(C('constraints')) if c.get('type')=='min')
        add_modifier(g,g.get('id')+'-min-brother','set',minc.get('id'),1,
                     groups=[('or',[cond('atLeast',1,normal.get('id'),'root-entry'),cond('atLeast',1,fellow.get('id'),'root-entry')])])
"""
new="""    # overwrite requirement behavior: XV AND (normal OR fellow).
    # Remove the generic XV-only min-on modifier first, otherwise the hidden
    # interface would still demand a power when no Brotherhood upgrade is taken.
    pref='r19-ts-'+uid+'-brotherhood'
    for g in (dg,pg):
        for c in list(g.find(C('constraints')) or []):
            if c.get('type')=='min': c.set('value','0')
        ms=g.find(C('modifiers'))
        if ms is not None:
            for m in list(ms):
                if m.get('id') in (pref+'-disc-min-on',pref+'-pow-min-on',g.get('id')+'-min-brother'):
                    ms.remove(m)
        add_modifier(g,g.get('id')+'-hide-no-brother','set','hidden','true',
                     groups=[('and',[cond('lessThan',1,normal.get('id'),'root-entry'),cond('lessThan',1,fellow.get('id'),'root-entry')])])
        minc=next(c for c in g.find(C('constraints')) if c.get('type')=='min')
        add_modifier(g,g.get('id')+'-min-normal','set',minc.get('id'),1,
                     groups=[('and',[cond('atLeast',1,'legion-xv','roster'),cond('atLeast',1,normal.get('id'),'root-entry')])])
        add_modifier(g,g.get('id')+'-min-fellow','set',minc.get('id'),1,
                     groups=[('and',[cond('atLeast',1,'legion-xv','roster'),cond('atLeast',1,fellow.get('id'),'root-entry')])])
"""
if old not in s:
    raise SystemExit('target block not found')
p.write_text(s.replace(old,new),encoding='utf-8')
print('patched veteran/terminator Brotherhood interface gating')
