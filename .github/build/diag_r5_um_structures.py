from pathlib import Path
import xml.etree.ElementTree as ET

CAT=Path('Legiones Astartes.cat'); OUT=Path('inspection-r5-um-structures.txt')
NS='http://www.battlescribe.net/schema/catalogueSchema'; C=lambda t:f'{{{NS}}}{t}'
root=ET.parse(CAT).getroot()

def byid(i): return next((x for x in root.iter() if x.get('id')==i),None)
def dump(i):
    e=byid(i); lines.append(f'=== {i} ==='); lines.append(ET.tostring(e,encoding='unicode') if e is not None else 'MISSING')

lines=[f'CAT={root.get("revision")} GST={root.get("gameSystemRevision")}']
for i in ('tactical-unit','veteran-unit','breacher-unit','terminator-unit','hq-praetor','hq-centurion','hq-master-signals','transport-damocles','r41-unit-xiii-0-invictarus-suzerain-squad','r41-unit-xiii-1-fulmentarus-terminator-squad','r41-unit-xiii-2-locutarus-storm-squad','r41-unit-xiii-3-nemesis-destroyer-squad','r41-unit-xiii-6-aeonid-thiel','r41-unit-xiii-7-honoured-telemechrus','r41-unit-xiii-8-titus-prayto','r41-unit-xiii-9-xiii-roboute-guilliman-the-avenging-son','r25-rite-xiii-0-the-logos-lectora','r25-rite-xiii-1-vigil-opertii-mission'):
    dump(i)
# allegiance selector candidates
for e in root.iter():
    nm=(e.get('name') or '').lower()
    if nm in ('loyalist','traitor') or 'allegiance' in nm:
        lines += [f'=== ALLEGIANCE {e.get("id")} {e.get("name")} {e.tag.split("}")[-1]} ===', ET.tostring(e,encoding='unicode')]
OUT.write_text('\n'.join(lines),encoding='utf-8')
print('wrote',OUT)
