from pathlib import Path
import xml.etree.ElementTree as ET
CAT=Path('Legiones Astartes.cat'); OUT=Path('inspection-r15-root-units.txt')
NS='http://www.battlescribe.net/schema/catalogueSchema'; C=lambda t:f'{{{NS}}}{t}'
root=ET.parse(CAT).getroot(); parent={c:p for p in root.iter() for c in p}
lines=[f'CAT={root.get("revision")}']
for e in root.iter(C('selectionEntry')):
    if e.get('type')!='unit': continue
    cur=parent.get(e); nested=False
    while cur is not None and cur is not root:
        if cur.tag==C('selectionEntry') and cur.get('type')=='unit': nested=True; break
        cur=parent.get(cur)
    if nested: continue
    nm=(e.get('name') or '')
    if any(k in nm.lower() for k in ['tactical','despoiler','assault','breacher','veteran','recon','seeker','destroyer','heavy support','support squad','command squad','honour guard','poisoner']):
        se=e.find(C('selectionEntries')); models=[]
        if se is not None: models=[f"{x.get('id')}:{x.get('name')}" for x in se if x.get('type')=='model']
        lines.append(f"{e.get('id')} | {nm} | direct_models={models}")
OUT.write_text('\n'.join(lines),encoding='utf-8'); print(OUT.read_text(encoding='utf-8'))