from pathlib import Path
import re, xml.etree.ElementTree as ET
CAT=Path('Legiones Astartes.cat'); IDX=Path('index.xml')
t=ET.parse(CAT); r=t.getroot()
if r.get('revision')!='21':
    raise RuntimeError(f'Expected catalogue revision 21, got {r.get("revision")}')
r.set('revision','22')
t.write(CAT,encoding='utf-8',xml_declaration=True)
s=IDX.read_text(encoding='utf-8')
s,n=re.subn(r'(filePath="Legiones Astartes\.cat"[^>]*dataRevision=")21(")',r'\g<1>22\2',s)
if n!=1: raise RuntimeError(f'Expected one index revision 21 entry, changed {n}')
IDX.write_text(s,encoding='utf-8')
Path('inspection-live-r22-force-refresh.txt').write_text(
    'LIVE R22 — FORCED NEW RECRUIT REFRESH\\n'
    'No rules content changed from R21.\\n'
    'Catalogue revision: 21 -> 22\\n'
    'index.xml dataRevision: 21 -> 22\\n'
    'Purpose: force New Recruit to invalidate the previous cached catalogue/index state.\\n',
    encoding='utf-8'
)
print('Forced publish bump complete: catalogue 22 / index 22')
