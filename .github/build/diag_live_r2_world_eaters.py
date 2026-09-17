from pathlib import Path
import xml.etree.ElementTree as ET

CAT=Path('Legiones Astartes.cat'); OUT=Path('inspection-live-r2-world-eaters.txt')
NS='http://www.battlescribe.net/schema/catalogueSchema'; C=lambda t:f'{{{NS}}}{t}'
r=ET.parse(CAT).getroot()

def direct(e,tag):
    x=e.find(C(tag)); return [] if x is None else list(x)

def text_rule(rule):
    d=rule.find(C('description')); return (d.text or '').replace('\n',' | ') if d is not None else ''

def constraints(e):
    return [(c.get('type'),c.get('value'),c.get('scope'),c.get('field'),c.get('childId')) for c in direct(e,'constraints')]

def costs(e):
    return [(c.get('name'),c.get('value'),c.get('typeId')) for c in direct(e,'costs')]

def dump_entry(e,indent=''):
    out=[]
    out.append(f"{indent}{e.tag.split('}')[-1]} id={e.get('id')} name={e.get('name')} type={e.get('type')} hidden={e.get('hidden')} default={e.get('defaultAmount')} costs={costs(e)} cons={constraints(e)}")
    for rr in direct(e,'rules'):
        out.append(f"{indent}  RULE {rr.get('name')}: {text_rule(rr)}")
    for g in direct(e,'selectionEntryGroups'):
        out.append(f"{indent}  GROUP id={g.get('id')} name={g.get('name')} cons={constraints(g)}")
        for x in direct(g,'selectionEntries'):
            out.extend(dump_entry(x,indent+'    '))
        for x in direct(g,'entryLinks'):
            out.append(f"{indent}    LINK id={x.get('id')} name={x.get('name')} target={x.get('targetId')} hidden={x.get('hidden')} costs={costs(x)} cons={constraints(x)}")
    for x in direct(e,'selectionEntries'):
        out.extend(dump_entry(x,indent+'  '))
    for x in direct(e,'entryLinks'):
        out.append(f"{indent}  LINK id={x.get('id')} name={x.get('name')} target={x.get('targetId')} hidden={x.get('hidden')} costs={costs(x)} cons={constraints(x)}")
    return out

entries=[]
for e in r.iter(C('selectionEntry')):
    i=e.get('id') or ''; n=(e.get('name') or '').upper()
    if i.startswith('r41-unit-xii-') or 'ANGRON' in n:
        # only top-level/canonical-ish WE entries, not nested clones unless Angron
        entries.append(e)

# dedupe by id
seen=set(); entries=[e for e in entries if not (e.get('id') in seen or seen.add(e.get('id')))]
lines=[f"CAT revision={r.get('revision')} GSTref={r.get('gameSystemRevision')}", f"WE/ANGRON entries={len(entries)}", '']
for e in entries:
    lines.append('='*100)
    lines.extend(dump_entry(e))
    lines.append('')
OUT.write_text('\n'.join(lines),encoding='utf-8')
print('\n'.join(lines[:400]))
