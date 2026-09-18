import xml.etree.ElementTree as ET
from pathlib import Path
t=ET.parse('Legiones Astartes.cat');r=t.getroot();ns=r.tag.split('}')[0].strip('{');C=lambda x:f'{{{ns}}}{x}'
o=[]
for rule in r.iter(C('rule')):
 m=rule.find(C('modifiers'))
 if m is not None and len(m):
  o.append(f"{rule.get('id')} | {rule.get('name')} | mods={len(m)}")
  if len(o)>=50: break
Path('inspection-rule-modifiers.txt').write_text('\n'.join(o) if o else 'NONE')
print('\n'.join(o) if o else 'NONE')
