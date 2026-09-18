from pathlib import Path
import xml.etree.ElementTree as ET
ct=ET.parse('Legiones Astartes.cat'); root=ct.getroot()
NS=root.tag.split('}')[0].strip('{'); C=lambda t:f'{{{NS}}}{t}'
def findid(i): return next((e for e in root.iter() if e.get('id')==i),None)
def line(e):
    if e is None:return 'MISSING'
    tag=e.tag.rsplit('}',1)[-1]
    return tag+' | '+' | '.join(f'{k}={e.get(k)}' for k in ('id','name','type','hidden','targetId','field','value','scope','childId') if e.get(k) is not None)
out=[f'CAT={root.get("revision")}']
# anything named bionics
out.append('\n=== BIONICS MATCHES ===')
for e in root.iter():
    nm=(e.get('name') or '').lower()
    if 'bionic' in nm:
        out.append(line(e))
        # direct modifiers/constraints
        for x in e.iter():
            if x is e: continue
            tag=x.tag.rsplit('}',1)[-1]
            if tag in ('modifier','condition','constraint','entryLink','selectionEntryGroup','selectionEntry'):
                if tag in ('modifier','condition','constraint') or x.get('targetId') or 'bionic' in (x.get('name') or '').lower():
                    out.append('  '+line(x))
# Iron Hands legion-specific ids / names likely iii? X is legion x
out.append('\n=== IRON HANDS / LEGION X MATCHES ===')
for e in root.iter():
    eid=(e.get('id') or '').lower(); nm=(e.get('name') or '').lower()
    if 'iron hands' in nm or 'legion-x' in eid or 'r45-ih' in eid or 'r18-ih' in eid or 'r41-unit-x-' in eid:
        tag=e.tag.rsplit('}',1)[-1]
        if tag in ('selectionEntry','selectionEntryGroup','entryLink','rule','modifier','constraint'):
            out.append(line(e))
# jump/bike generic roots
out.append('\n=== JUMP / BIKE UNIT ROOTS AND BIONICS LINKS ===')
for u in root.iter(C('selectionEntry')):
    if u.get('type')!='unit': continue
    nm=(u.get('name') or '').lower()
    if any(k in nm for k in ('assault squad','bike squadron','sky hunter','attack bike','jump')):
        links=[x for x in u.iter(C('entryLink')) if 'bionic' in (x.get('name') or '').lower() or 'bionic' in (x.get('targetId') or '').lower()]
        if links:
            out.append('UNIT '+line(u))
            for x in links:
                out.append('  LINK '+line(x))
                for m in x.iter(C('modifier')):
                    out.append('    '+line(m))
                    for c in m.iter(C('condition')): out.append('      '+line(c))
# generic armoury bionics eligibility source
out.append('\n=== LINKS TO BIONICS TARGETS ===')
targets=set()
for e in root.iter(C('selectionEntry')):
    if 'bionic' in (e.get('name') or '').lower():
        targets.add(e.get('id'))
for l in root.iter(C('entryLink')):
    if l.get('targetId') in targets:
        out.append(line(l))
        # parent chain
        pm={c:p for p in root.iter() for c in p}
        p=pm.get(l)
        for i in range(4):
            if p is None: break
            out.append('  P'+str(i+1)+' '+line(p)); p=pm.get(p)
Path('inspection-r19-iron-hands-bionics.txt').write_text('\n'.join(out),encoding='utf-8')
print('\n'.join(out[:2000]))
