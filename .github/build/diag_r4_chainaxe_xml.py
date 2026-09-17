from pathlib import Path
import xml.etree.ElementTree as ET
CAT=Path('Legiones Astartes.cat'); OUT=Path('inspection-r4-chainaxe-xml.txt')
NS='http://www.battlescribe.net/schema/catalogueSchema'; C=lambda t:f'{{{NS}}}{t}'
root=ET.parse(CAT).getroot(); lines=[]
for wanted in ('r45-tactical-unit-we-chain','r45-assault-unit-we-chain','r45-assault-unit-we-chain-discount','r45-r41-unit-xii-0-rampager-squad-we-chain','r45-r41-unit-xii-0-rampager-squad-we-chain-discount'):
    e=next((x for x in root.iter() if x.get('id')==wanted),None)
    lines.append(f'=== {wanted} ===')
    lines.append(ET.tostring(e,encoding='unicode') if e is not None else 'MISSING')
for wanted in ('r45-we-chainaxe','r45-we-chainaxe-berserker'):
    e=next((x for x in root.iter() if x.get('id')==wanted),None)
    lines.append(f'=== TARGET {wanted} ===')
    lines.append(ET.tostring(e,encoding='unicode') if e is not None else 'MISSING')
OUT.write_text('\n'.join(lines),encoding='utf-8')
print('\n'.join(lines))
