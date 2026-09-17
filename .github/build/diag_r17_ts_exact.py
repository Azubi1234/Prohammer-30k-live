from pathlib import Path
import xml.etree.ElementTree as ET
P=Path('Legiones Astartes.cat'); O=Path('inspection-r17-ts-exact.txt')
NS='http://www.battlescribe.net/schema/catalogueSchema'; C=lambda t:f'{{{NS}}}{t}'
r=ET.parse(P).getroot()
def norm(s): return ' '.join((s or '').split())
def costs(e):
 c=e.find(C('costs')); return [(x.get('name'),x.get('value')) for x in c] if c is not None else []
def constraints(e):
 c=e.find(C('constraints')); return [(x.get('id'),x.get('type'),x.get('value'),x.get('field'),x.get('scope')) for x in c] if c is not None else []
lines=[f"CAT={r.get('revision')}"]
for e in r.iter(C('selectionEntry')):
 i=e.get('id') or ''
 if not (i.startswith('r41-unit-xv-') and i.count('-')==4): continue
 lines += [f"\n=== {i} | {e.get('name')} ===",f"COSTS {costs(e)}",f"CONSTRAINTS {constraints(e)}"]
 rs=e.find(C('rules'))
 if rs is not None:
  for x in rs:
   d=x.find(C('description')); lines.append(f"RULE {x.get('id')} | {x.get('name')} | hidden={x.get('hidden')}\n{norm(d.text if d is not None else '')}")
 # direct groups and entries, including modifiers/constraints
 for g in list(e.find(C('selectionEntryGroups')) or []):
  lines.append(f"GROUP {g.get('id')} | {g.get('name')} | cons={constraints(g)}")
  for cn in ('selectionEntries','entryLinks','selectionEntryGroups'):
   cont=g.find(C(cn))
   if cont is None: continue
   for x in cont:
    lines.append(f"  {x.tag.rsplit('}',1)[-1]} {x.get('id')} | {x.get('name')} | target={x.get('targetId')} | costs={costs(x)} | cons={constraints(x)}")
 for x in list(e.find(C('selectionEntries')) or []):
  lines.append(f"ENTRY {x.get('id')} | {x.get('name')} | costs={costs(x)} | cons={constraints(x)}")
O.write_text('\n'.join(lines),encoding='utf-8'); print('bytes',O.stat().st_size)
