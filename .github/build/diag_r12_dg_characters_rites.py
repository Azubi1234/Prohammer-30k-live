from pathlib import Path
import xml.etree.ElementTree as ET
CAT=Path('Legiones Astartes.cat'); OUT=Path('inspection-r12-dg-characters-rites.txt')
NS='http://www.battlescribe.net/schema/catalogueSchema'; C=lambda t:f'{{{NS}}}{t}'
root=ET.parse(CAT).getroot()
ids=['r25-rite-xiv-0-the-reaping','r25-rite-xiv-1-creeping-death','r41-unit-xiv-3-calas-typhon-first-captain','r41-unit-xiv-4-crysos-morturg','r41-unit-xiv-5-durak-rask','r41-unit-xiv-6-ignatius-grulgor','r41-unit-xiv-7-nathaniel-garro','r41-unit-xiv-8-xiv-mortarion-the-reaper','r41-unit-xiv-9-mortarion-prince-of-decay']
lines=[f'CAT={root.get("revision")} GST={root.get("gameSystemRevision")}']
for id_ in ids:
 e=next((x for x in root.iter() if x.get('id')==id_),None)
 lines+=['',f'=== {id_} | {e.get("name") if e is not None else "MISSING"} ===']
 if e is None: continue
 for r in (e.find(C('rules')) or []):
  d=r.find(C('description')); lines.append(f'RULE {r.get("id")} | {r.get("name")} hidden={r.get("hidden")} :: {(d.text or "")[:700]}')
 for p in (e.find(C('profiles')) or []):
  lines.append(f'PROFILE {p.get("id")} | {p.get("name")} type={p.get("typeName")} typeId={p.get("typeId")}')
  for c in (p.find(C('characteristics')) or []): lines.append(f'  {c.get("name") or c.get("typeId")}: {c.text}')
 for g in (e.find(C('selectionEntryGroups')) or []):
  lines.append(f'GROUP {g.get("id")} | {g.get("name")} hidden={g.get("hidden")}')
  for cn in ('selectionEntries','entryLinks'):
   co=g.find(C(cn))
   if co is not None:
    for x in co: lines.append(f'  OPT {x.get("id")} | {x.get("name")} type={x.get("type")} target={x.get("targetId")} hidden={x.get("hidden")}')
 for cn in ('selectionEntries','entryLinks'):
  co=e.find(C(cn))
  if co is not None:
   for x in co: lines.append(f'DIRECT {x.get("id")} | {x.get("name")} type={x.get("type")} target={x.get("targetId")} hidden={x.get("hidden")}')
OUT.write_text('\n'.join(lines),encoding='utf-8'); print('\n'.join(lines))
