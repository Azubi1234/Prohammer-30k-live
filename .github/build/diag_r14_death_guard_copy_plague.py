from pathlib import Path
import xml.etree.ElementTree as ET

CAT=Path('Legiones Astartes.cat'); OUT=Path('inspection-r14-death-guard-copy-plague.txt')
NS='http://www.battlescribe.net/schema/catalogueSchema'; C=lambda t:f'{{{NS}}}{t}'
root=ET.parse(CAT).getroot()
lines=[f'CAT={root.get("revision")} GSTref={root.get("gameSystemRevision")}']

def rules(e):
    r=e.find(C('rules'))
    return list(r) if r is not None else []
def desc(r):
    d=r.find(C('description')); return (d.text or '') if d is not None else ''
def costs(e):
    c=e.find(C('costs'))
    return [(x.get('name'),x.get('value')) for x in c] if c is not None else []
def dump(e,depth=0,maxdepth=2):
    ind='  '*depth
    lines.append(f"{ind}{e.tag.split('}')[-1]} {e.get('id')} | {e.get('name')} | type={e.get('type')} hidden={e.get('hidden')} pts={costs(e)}")
    for r in rules(e):
        lines.append(f"{ind}  RULE {r.get('id')} | {r.get('name')} | hidden={r.get('hidden')} | {desc(r).replace(chr(10),' ')[:700]}")
    ps=e.find(C('profiles'))
    if ps is not None:
        for p in ps:
            chars=[]
            ch=p.find(C('characteristics'))
            if ch is not None:
                for x in ch: chars.append(f"{x.get('name')}={x.text}")
            lines.append(f"{ind}  PROFILE {p.get('id')} | {p.get('name')} | {p.get('typeName')} | "+', '.join(chars))
    if depth<maxdepth:
        for cn in ('selectionEntryGroups','selectionEntries','entryLinks'):
            cont=e.find(C(cn))
            if cont is not None:
                for x in cont: dump(x,depth+1,maxdepth)

# Top-level XIV entries and rites
for e in root.iter(C('selectionEntry')):
    i=e.get('id') or ''
    if i.startswith('r41-unit-xiv-') or i.startswith('r25-rite-xiv-'):
        # only top-level or named primary IDs
        if any((p.get('id')==i) for p in root.findall('.//'+C('sharedSelectionEntries')+'/'+C('selectionEntry'))):
            pass

seen=set()
for e in root.iter(C('selectionEntry')):
    i=e.get('id') or ''
    if i.startswith('r41-unit-xiv-') or i.startswith('r25-rite-xiv-'):
        if i in seen: continue
        seen.add(i); lines.append('\n=== XIV ENTRY ==='); dump(e,0,2)

# Any visible Source Entry within Death Guard top-level subtree
lines.append('\n=== VISIBLE SOURCE ENTRY RULES ===')
for e in root.iter():
    i=e.get('id') or ''
    if 'xiv' not in i.lower() and 'dg' not in i.lower(): continue
    for r in rules(e):
        if (r.get('name') or '')=='Source Entry' and r.get('hidden')!='true':
            lines.append(f"{e.tag.split('}')[-1]} {i} {e.get('name')} -> {r.get('id')} | {desc(r).replace(chr(10),' ')[:1200]}")

# plague / Sons references anywhere
lines.append('\n=== PLAGUE / SONS REFERENCES ===')
for e in root.iter():
    blob=' '.join([(e.get('id') or ''),(e.get('name') or '')])
    for r in rules(e): blob+=' '+(r.get('name') or '')+' '+desc(r)
    if 'plague marine' in blob.lower() or 'sons of the plague father' in blob.lower():
        lines.append(f"{e.tag.split('}')[-1]} {e.get('id')} | {e.get('name')} | hidden={e.get('hidden')} pts={costs(e)}")
        ms=e.find(C('modifiers'))
        if ms is not None: lines.append('  MODIFIERS '+ET.tostring(ms,encoding='unicode')[:3000])
        cs=e.find(C('constraints'))
        if cs is not None: lines.append('  CONSTRAINTS '+ET.tostring(cs,encoding='unicode')[:2000])
        for r in rules(e): lines.append(f"  RULE {r.get('name')} | hidden={r.get('hidden')} | {desc(r).replace(chr(10),' ')[:1200]}")

OUT.write_text('\n'.join(lines),encoding='utf-8')
print(OUT.read_text(encoding='utf-8'))