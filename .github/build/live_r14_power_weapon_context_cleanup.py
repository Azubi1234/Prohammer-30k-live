from pathlib import Path
import re
import xml.etree.ElementTree as ET

CAT=Path('Legiones Astartes.cat'); IDX=Path('index.xml'); OUT=Path('inspection-live-r14-power-weapon-cleanup.txt')
NS='http://www.battlescribe.net/schema/catalogueSchema'; ET.register_namespace('',NS); C=lambda t:f'{{{NS}}}{t}'
ct=ET.parse(CAT); root=ct.getroot()
if root.get('revision')!='13': raise RuntimeError(f'Expected CAT 13, got {root.get("revision")}')

changed=[]
for e in root.iter():
    if (e.get('name') or '').strip().lower() != 'power weapon':
        continue
    rs=e.find(C('rules'))
    if rs is None:
        continue
    rules=list(rs)
    keep=None
    for r in rules:
        d=r.find(C('description'))
        txt=(d.text or '').strip() if d is not None else ''
        if 'ignores armour saves' in txt.lower():
            keep=r
            break
    removed=0
    for r in rules:
        if r is not keep:
            rs.remove(r); removed+=1
    if removed:
        changed.append(f"{e.tag.split('}')[-1]} {e.get('id')} removed {removed} redundant rule(s)")
    if len(rs)==0:
        e.remove(rs)

root.set('revision','14')
ct.write(CAT,encoding='utf-8',xml_declaration=True)
idx=IDX.read_text(encoding='utf-8')
idx=re.sub(r'(filePath="Legiones Astartes\.cat"[^>]*dataRevision=")\d+("\s*/>)',r'\g<1>14\2',idx)
IDX.write_text(idx,encoding='utf-8')
OUT.write_text('LIVE R14 — POWER WEAPON RULE CONTEXT CLEANUP\nCAT=14 GSTref='+str(root.get('gameSystemRevision'))+'\n\n• Generic Power Weapon popups now keep only the actual Power Weapon rule: Ignores Armour Saves.\n• Replacement/context notes such as Rending Weapon, Grey Slayer weapon replacement, and “uses normal Power Weapon Rules” were removed from the popup.\n\nChanged entries: '+str(len(changed))+'\n'+'\n'.join('  + '+x for x in changed),encoding='utf-8')
print(OUT.read_text(encoding='utf-8'))