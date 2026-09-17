from pathlib import Path
import xml.etree.ElementTree as ET

CAT=Path('Legiones Astartes.cat'); OUT=Path('inspection-live-r3-world-eaters.txt')
NS='http://www.battlescribe.net/schema/catalogueSchema'; C=lambda t:f'{{{NS}}}{t}'
r=ET.parse(CAT).getroot()
lines=[f'CAT={r.get("revision")} GSTref={r.get("gameSystemRevision")}']

def cons(e):
    out=[]
    cs=e.find(C('constraints'))
    if cs is not None:
        for x in cs.findall(C('constraint')):
            if x.get('field')=='selections': out.append(f"{x.get('type')}={x.get('value')} scope={x.get('scope')}")
    return ', '.join(out)

def pts(e):
    cs=e.find(C('costs'))
    if cs is None:return ''
    for x in cs.findall(C('cost')):
        if x.get('typeId')=='pts':return x.get('value','')
    return ''

def dump(e,depth=0,maxdepth=5):
    ind='  '*depth
    lines.append(f"{ind}- {e.tag.split('}')[-1]} | id={e.get('id')} | name={e.get('name')} | type={e.get('type')} | pts={pts(e)} | {cons(e)}")
    rs=e.find(C('rules'))
    if rs is not None:
        for q in rs.findall(C('rule')):
            d=q.find(C('description')); tx=(d.text or '').strip() if d is not None else ''
            lines.append(f"{ind}  RULE {q.get('name')}: {tx[:500]}")
    if depth>=maxdepth:return
    for tag in ('selectionEntries','selectionEntryGroups','entryLinks'):
        h=e.find(C(tag))
        if h is not None:
            for ch in list(h):dump(ch,depth+1,maxdepth)

we=[]
for e in r.iter(C('selectionEntry')):
    if (e.get('id') or '').startswith('r41-unit-xii-') and e.get('type')=='unit':
        # only canonical top-level/imported units, not nested clones
        we.append(e)
lines.append(f'WORLD EATERS UNIT ENTRIES FOUND={len(we)}')
seen=set()
for e in we:
    if e.get('id') in seen:continue
    seen.add(e.get('id'))
    lines.append('\n=== '+(e.get('name') or '')+' ===')
    dump(e)

# Also list anything named Angron / Triarii / retinue among all entries for ID discovery.
for key in ('angron','triarii','trarii','retinue'):
    lines.append(f'\n=== GLOBAL NAME MATCH: {key} ===')
    n=0
    for e in r.iter():
        if key in (e.get('name') or '').lower():
            lines.append(f"{e.tag.split('}')[-1]} | id={e.get('id')} | name={e.get('name')} | type={e.get('type')} | pts={pts(e)} | {cons(e)}")
            n+=1
            if n>=250:break

OUT.write_text('\n'.join(lines),encoding='utf-8')
print(f'wrote {OUT} lines={len(lines)}')