from pathlib import Path
import xml.etree.ElementTree as ET
CAT=Path('Legiones Astartes.cat'); OUT=Path('inspection-r15-top-level-infantry.txt')
NS='http://www.battlescribe.net/schema/catalogueSchema'; C=lambda t:f'{{{NS}}}{t}'
root=ET.parse(CAT).getroot(); lines=[f'CAT={root.get("revision")}']
shared=root.find(C('sharedSelectionEntries'))
if shared is None: raise RuntimeError('no sharedSelectionEntries')
for e in shared:
    if e.tag!=C('selectionEntry') or e.get('type')!='unit': continue
    models=[]
    se=e.find(C('selectionEntries'))
    if se is not None:
        models=[f"{x.get('id')}:{x.get('name')}" for x in se if x.get('type')=='model']
    nm=(e.get('name') or '')
    if any(k in nm.lower() for k in ['tactical','despoiler','assault','breacher','veteran','recon','seeker','destroyer','heavy support','support squad','command squad','honour guard','poisoner']):
        lines.append(f"{e.get('id')} | {nm} | direct_models={models}")
OUT.write_text('\n'.join(lines),encoding='utf-8'); print(OUT.read_text(encoding='utf-8'))