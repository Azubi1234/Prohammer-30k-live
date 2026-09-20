from pathlib import Path
import xml.etree.ElementTree as ET
CAT=Path('Legiones Astartes.cat'); OUT=Path('inspection-r28c-veteran-raw.txt')
NS='http://www.battlescribe.net/schema/catalogueSchema'; C=lambda t:f'{{{NS}}}{t}'
r=ET.parse(CAT).getroot()
def fid(i): return next((x for x in r.iter() if x.get('id')==i),None)
ids=['veteran-included','veteran-melee','veteran-ranged','veteran-individual','veteran-specialists','tac-heavy-weapons','tac-special-weapons']
lines=[f'CAT={r.get("revision")}']
for i in ids:
    e=fid(i)
    lines.append('\n=== '+i+' ===')
    lines.append(ET.tostring(e,encoding='unicode') if e is not None else 'MISSING')
OUT.write_text('\n'.join(lines),encoding='utf-8'); print('bytes',OUT.stat().st_size)
