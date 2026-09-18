from pathlib import Path
import xml.etree.ElementTree as ET
ct=ET.parse('Legiones Astartes.cat'); root=ct.getroot()
NS=root.tag.split('}')[0].strip('{'); C=lambda t:f'{{{NS}}}{t}'
gt=ET.parse('Prohammer 30k.gst'); groot=gt.getroot(); GNS=groot.tag.split('}')[0].strip('{'); G=lambda t:f'{{{GNS}}}{t}'
def findid(r,i): return next((e for e in r.iter() if e.get('id')==i),None)
def parent_map(r): return {c:p for p in r.iter() for c in p}
pm=parent_map(root)
def line(e):
    if e is None:return 'MISSING'
    tag=e.tag.rsplit('}',1)[-1]
    a=' | '.join(f'{k}={e.get(k)}' for k in ('id','name','type','hidden','targetId','field','value','scope','childId') if e.get(k) is not None)
    return f'{tag} | {a}'
def direct(e,tag):
    if e is None:return []
    x=e.find(C(tag)); return list(x) if x is not None else []
out=[f'CAT={root.get("revision")}']
# parent of librarian power groups + all sibling groups
for iid in ['r61-librarian-power1','r61-librarian-power2']:
    e=findid(root,iid); out+=['',f'=== {iid} PARENT CHAIN ===',line(e)]
    p=pm.get(e)
    for z in range(5):
        if p is None: break
        out.append('P'+str(z+1)+' '+line(p)); p=pm.get(p)
# hq librarian direct structure
lib=findid(root,'hq-librarian')
out+=['','=== HQ LIBRARIAN DIRECT ===']
for c in list(lib) if lib is not None else []:
    out.append(line(c))
    if c.tag==C('selectionEntryGroups'):
        for g in list(c):
            out.append('  '+line(g))
            for e in direct(g,'selectionEntries')[:20]: out.append('    '+line(e))
# TS groups ids + parent
out+=['','=== TS POWER GROUP PARENTS ===']
for e in root.iter(C('selectionEntryGroup')):
    eid=e.get('id') or ''
    if ('r18' in eid or 'r61' in eid) and 'power' in eid.lower():
        out.append(line(e))
        p=pm.get(e)
        if p is not None: out.append('  P '+line(p))
# Cult entries representative
out+=['','=== CULT REPRESENTATIVES ===']
for target in ['r45-cult-tactical-unit-0','r45-cult-veteran-unit-0','r45-cult-terminator-unit-0']:
    e=findid(root,target); out.append(line(e))
    if e is not None:
        for r in e.iter(C('rule')):
            d=r.find(C('description'))
            out.append('  RULE '+line(r)+' DESC='+((d.text or '')[:800] if d is not None else ''))
        for m in e.iter(C('modifier')):
            out.append('  MOD '+line(m))
            for c in m.iter(C('condition')): out.append('    '+line(c))
# Sanakht
san=next((e for e in root.iter(C('selectionEntry')) if (e.get('name') or '').upper()=='SANAKHT'),None)
out+=['','=== SANAKHT DIRECT RULES/GROUPS ===',line(san)]
if san is not None:
    for r in san.iter(C('rule')):
        d=r.find(C('description')); txt=(d.text or '') if d is not None else ''
        out.append('RULE '+line(r)+' LEN='+str(len(txt))+' DESC='+txt[:1000].replace('\n',' '))
    for g in direct(san,'selectionEntryGroups'):
        out.append('GROUP '+line(g))
# rites
out+=['','=== XV RITES ===']
for e in root.iter(C('selectionEntry')):
    if (e.get('id') or '').startswith('r25-rite-xv'):
        out.append('\nRITE '+line(e))
        for m in e.iter(C('modifier')):
            out.append('  MOD '+line(m))
            for c in m.iter(C('condition')): out.append('    '+line(c))
        for c in e.iter(C('constraint')): out.append('  CON '+line(c))
        for r in e.iter(C('rule')):
            d=r.find(C('description')); out.append('  RULE '+line(r)+' DESC='+((d.text or '')[:1200] if d is not None else ''))
# category links in GST force standard
force=findid(groot,'force-standard')
out+=['','=== GST FORCE STANDARD CATEGORY LINKS ===']
if force is not None:
    cls=force.find(G('categoryLinks'))
    for x in list(cls) if cls is not None else []:
        if x.get('targetId') in ('cat-hq','cat-elites','cat-troops','cat-fast','cat-heavy','cat-fortification','cat-low') or 'r18' in (x.get('id') or ''):
            out.append(line(x))
            for c in x.iter(G('constraint')): out.append('  '+line(c))
            for m in x.iter(G('modifier')): 
                out.append('  MOD '+line(m))
                for co in m.iter(G('condition')): out.append('    '+line(co))
Path('inspection-r18-ts-focused.txt').write_text('\n'.join(out),encoding='utf-8')
print('\n'.join(out))
