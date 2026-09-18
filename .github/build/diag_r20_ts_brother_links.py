from pathlib import Path
import xml.etree.ElementTree as ET
t=ET.parse('Legiones Astartes.cat');r=t.getroot();ns=r.tag.split('}')[0].strip('{');C=lambda x:f'{{{ns}}}{x}'
def line(e):
 return e.tag.rsplit('}',1)[-1]+' | '+' | '.join(f'{k}={e.get(k)}' for k in ('id','name','type','hidden','targetId','field','value','scope','childId') if e.get(k)!=None)
pm={c:p for p in r.iter() for c in p}
out=[]
for target in ['r45-ts-brotherhood','r45-ts-brotherhood-fellowship','r45-ts-tactical-brotherhood']:
 out.append('\\n=== LINKS TO '+target+' ===')
 for e in r.iter(C('entryLink')):
  if e.get('targetId')==target:
   out.append(line(e))
   for m in e.iter(C('modifier')):
    out.append('  '+line(m))
    for c in m.iter(C('condition')):out.append('    '+line(c))
   p=pm.get(e)
   for i in range(4):
    if p is None:break
    out.append('  P'+str(i+1)+' '+line(p)); p=pm.get(p)
Path('inspection-r20-ts-brother-links.txt').write_text('\\n'.join(out),encoding='utf-8')
print('\\n'.join(out))
