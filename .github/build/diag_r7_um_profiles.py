from pathlib import Path
import xml.etree.ElementTree as ET
CAT=Path('Legiones Astartes.cat'); OUT=Path('inspection-r7-um-profiles.txt')
NS='http://www.battlescribe.net/schema/catalogueSchema'; C=lambda t:f'{{{NS}}}{t}'
root=ET.parse(CAT).getroot(); lines=[]
ids=['r41-unit-xiii-0-invictarus-suzerain-squad','r41-unit-xiii-1-fulmentarus-terminator-squad','r41-unit-xiii-2-locutarus-storm-squad','r41-unit-xiii-3-nemesis-destroyer-squad','r41-unit-xiii-4-marius-gage-first-master','r41-unit-xiii-5-remus-ventanus','r41-unit-xiii-7-honoured-telemechrus','r41-unit-xiii-8-titus-prayto','r41-unit-xiii-9-xiii-roboute-guilliman-the-avenging-son','tac-marine','tac-sergeant','veteran-sergeant']
for id_ in ids:
 e=next((x for x in root.iter() if x.get('id')==id_),None); lines.append(f'=== {id_} {e.get("name") if e is not None else "MISSING"} ===')
 if e is None:continue
 for x in e.iter():
  if x.tag==C('profile'):
   lines.append(ET.tostring(x,encoding='unicode'))
 for x in list(e.find(C('selectionEntries')) or []):
  lines.append(f'CHILD {x.get("id")} {x.get("name")} type={x.get("type")} default={x.get("defaultAmount")}')
  for p in x.iter(C('profile')): lines.append(ET.tostring(p,encoding='unicode'))
OUT.write_text('\n'.join(lines),encoding='utf-8'); print('\n'.join(lines))
