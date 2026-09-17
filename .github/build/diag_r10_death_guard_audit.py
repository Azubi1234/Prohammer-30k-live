from pathlib import Path
import xml.etree.ElementTree as ET

CAT=Path('Legiones Astartes.cat'); OUT=Path('inspection-r10-death-guard-audit.txt')
NS='http://www.battlescribe.net/schema/catalogueSchema'; C=lambda t:f'{{{NS}}}{t}'
root=ET.parse(CAT).getroot()

def cons(e):
    c=e.find(C('constraints')); out=[]
    if c is not None:
        for x in c:
            out.append(f"{x.get('type')}={x.get('value')} field={x.get('field')} scope={x.get('scope')} child={x.get('childId')}")
    return '; '.join(out)

def cost(e):
    cs=e.find(C('costs'))
    if cs is not None:
        for x in cs:
            if x.get('typeId')=='pts': return x.get('value')
    return ''

def cats(e):
    cl=e.find(C('categoryLinks')); out=[]
    if cl is not None:
        for x in cl: out.append(f"{x.get('name')}->{x.get('targetId')} primary={x.get('primary')}")
    return ', '.join(out)

def dump_entry(e,depth=0,maxdepth=3):
    p='  '*depth; lines=[f"{p}{e.tag.split('}')[-1]} {e.get('id')} | {e.get('name')} | type={e.get('type')} hidden={e.get('hidden')} pts={cost(e)} cons={cons(e)} cats={cats(e)}"]
    if depth>=maxdepth: return lines
    for cn in ('selectionEntryGroups','selectionEntries','entryLinks'):
        cont=e.find(C(cn))
        if cont is None: continue
        for x in cont:
            if x.tag in (C('selectionEntryGroup'),C('selectionEntry'),C('entryLink')):
                lines += dump_entry(x,depth+1,maxdepth)
    return lines

lines=[f"CAT revision={root.get('revision')} GSTref={root.get('gameSystemRevision')}",""]
# All entries whose names or IDs clearly belong to Death Guard.
seen=set()
for e in root.iter(C('selectionEntry')):
    n=(e.get('name') or '').lower(); i=(e.get('id') or '').lower()
    if any(k in n for k in ('deathshroud','grave warden','mortus poisoner','calas typhon','nathaniel garro','mortarion')) or 'xiv-' in i or 'death-guard' in i:
        if e.get('id') in seen: continue
        seen.add(e.get('id')); lines += ['=== ENTRY ===']+dump_entry(e,0,3)+['']

# Rite / legion selection structures, including Death Guard-specific names and old DG armoury links.
for e in root.iter():
    if e.tag not in (C('selectionEntry'),C('selectionEntryGroup'),C('entryLink')): continue
    n=(e.get('name') or '').lower(); i=(e.get('id') or '').lower()
    if any(k in n for k in ('the reaping','creeping death','death guard armoury','manreaper','alchem flamer','foot-slogging','footslogging','resilience of barbarus','steady assault')) or any(k in i for k in ('rite-xiv','dg-','death-guard')):
        key=(e.tag,e.get('id'))
        if e.get('id') in seen: continue
        seen.add(e.get('id')); lines += ['=== DG STRUCTURE ===']+dump_entry(e,0,2)+['']

OUT.write_text('\n'.join(lines),encoding='utf-8')
print(OUT.read_text(encoding='utf-8'))
