from pathlib import Path
import xml.etree.ElementTree as ET

CAT=Path('Legiones Astartes.cat')
OUT=Path('inspection-r17-ts-transport-sources.txt')
NS='http://www.battlescribe.net/schema/catalogueSchema'
C=lambda t:f'{{{NS}}}{t}'
root=ET.parse(CAT).getroot()

lines=[f'CAT={root.get("revision")}', '']

def pts(e):
    cs=e.find(C('costs'))
    if cs is None: return ''
    return ','.join(f"{x.get('name')}={x.get('value')}" for x in cs)

def cats(e):
    c=e.find(C('categoryLinks'))
    if c is None: return ''
    return ','.join(f"{x.get('name')}->{x.get('targetId')}" for x in c)

lines.append('=== DIRECT TERMINATOR DEDICATED TRANSPORT GROUP ===')
term=next((x for x in root.iter(C('selectionEntry')) if x.get('id')=='terminator-unit'),None)
if term is not None:
    sgs=term.find(C('selectionEntryGroups'))
    tg=next((g for g in list(sgs) if (g.get('name') or '')=='Dedicated Transport'),None) if sgs is not None else None
    if tg is not None:
        for x in tg.iter():
            tag=x.tag.rsplit('}',1)[-1]
            if tag in ('selectionEntry','entryLink','selectionEntryGroup'):
                lines.append(f"{tag} | id={x.get('id')} | name={x.get('name')} | type={x.get('type')} | hidden={x.get('hidden')} | target={x.get('targetId')} | pts={pts(x)}")
    else: lines.append('MISSING')
else: lines.append('TERMINATOR UNIT MISSING')

lines += ['', '=== ALL DEDICATED TRANSPORT GROUPS WITH LAND RAIDER / SPARTAN / DREADCLAW CHILDREN ===']
for g in root.iter(C('selectionEntryGroup')):
    if 'Dedicated Transport' not in (g.get('name') or ''):
        continue
    hits=[]
    for x in g.iter():
        if x is g: continue
        tag=x.tag.rsplit('}',1)[-1]
        if tag not in ('selectionEntry','entryLink','selectionEntryGroup'): continue
        n=(x.get('name') or '')
        low=n.lower()
        if 'land raider' in low or 'spartan' in low or 'dreadclaw' in low:
            hits.append(f"  {tag} | id={x.get('id')} | name={n} | type={x.get('type')} | hidden={x.get('hidden')} | target={x.get('targetId')} | pts={pts(x)}")
    if hits:
        lines.append(f"GROUP | id={g.get('id')} | name={g.get('name')} | hidden={g.get('hidden')}")
        lines.extend(hits[:30])

lines += ['', '=== ROOT / SHARED CANDIDATES ===']
for x in root.iter(C('selectionEntry')):
    n=(x.get('name') or '')
    low=n.lower()
    if ('land raider' in low or 'spartan' in low or 'dreadclaw' in low) and x.get('type') in ('unit','model'):
        lines.append(f"selectionEntry | id={x.get('id')} | name={n} | type={x.get('type')} | hidden={x.get('hidden')} | pts={pts(x)} | cats={cats(x)}")

OUT.write_text('\n'.join(lines)+'\n',encoding='utf-8')
print('\n'.join(lines[:200]))
