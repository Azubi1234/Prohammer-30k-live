from pathlib import Path
import xml.etree.ElementTree as ET
CAT=Path('Legiones Astartes.cat'); OUT=Path('inspection-point-thresholds.txt')
NS='http://www.battlescribe.net/schema/catalogueSchema'; C=lambda t:f'{{{NS}}}{t}'
root=ET.parse(CAT).getroot(); lines=[]
parent={c:p for p in root.iter() for c in p}
def anc(e):
 x=e
 for _ in range(6):
  if x is None: break
  if x.get('name') or x.get('id'): return f"{x.tag.split('}')[-1]} {x.get('id')} {x.get('name')}"
  x=parent.get(x)
 return ''
for e in root.iter():
 if e.tag in (C('condition'),C('constraint'),C('repeat')):
  if e.get('scope')=='roster' and e.get('field') not in (None,'selections'):
   lines.append(anc(parent.get(e))+' :: '+ET.tostring(e,encoding='unicode'))
OUT.write_text('\n'.join(lines),encoding='utf-8'); print('\n'.join(lines))
