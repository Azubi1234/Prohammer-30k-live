from pathlib import Path
import re, subprocess, xml.etree.ElementTree as ET

BASE='41c7755e59b6db0b38e2a426e0f7cb8e6189c110'  # known-good Live R20
for path in ('Legiones Astartes.cat','Prohammer 30k.gst','index.xml'):
    data=subprocess.check_output(['git','show',f'{BASE}:{path}'])
    Path(path).write_bytes(data)

cat=Path('Legiones Astartes.cat')
idx=Path('index.xml')
t=ET.parse(cat); r=t.getroot()
if r.get('revision')!='20':
    raise RuntimeError(f'Expected rollback base revision 20, got {r.get("revision")}')
r.set('revision','23')
t.write(cat,encoding='utf-8',xml_declaration=True)

s=idx.read_text(encoding='utf-8')
s,n=re.subn(r'(filePath="Legiones Astartes\.cat"[^>]*dataRevision=")20(")',r'\g<1>23\2',s)
if n!=1:
    raise RuntimeError(f'Expected exactly one index rev20 entry, changed {n}')
idx.write_text(s,encoding='utf-8')

Path('inspection-live-r23-emergency-rollback.txt').write_text(
    'LIVE R23 — EMERGENCY ROLLBACK\\n'
    'Restored known-good Live R20 catalogue/game-system/index content from commit '+BASE+'.\\n'
    'Re-published the restored catalogue as revision 23 so New Recruit treats it as a new update.\\n'
    'This retains the R20 Thousand Sons state and Iron Hands mobile Bionics, while removing the R21/R22 hotfix layer that caused the fresh-source install to stop working.\\n'
    'R21 changes will be repaired offline before being reintroduced.\\n',
    encoding='utf-8'
)
print('Rollback restored R20 content and republished as R23')
