from pathlib import Path
import xml.etree.ElementTree as ET
t=ET.parse('Legiones Astartes.cat');r=t.getroot();ns=r.tag.split('}')[0].strip('{');C=lambda x:f'{{{ns}}}{x}'
def f(i):return next((e for e in r.iter() if e.get('id')==i),None)
def line(e):
 return e.tag.rsplit('}',1)[-1]+' | '+' | '.join(f'{k}={e.get(k)}' for k in ('id','name','type','hidden','targetId','field','value','scope','childId','primary') if e.get(k)!=None)
out=[]
for i in ['r45-ts-trans-unit','r45-ts-trans-char','r18-ts-guard-praetor-ml3','r41-unit-xv-11-xv-magnus-the-red-the-crimson-king','r41-unit-xv-0-sekhmet-terminator-cabal']:
 e=f(i);out+=['\\n=== '+i+' ===',line(e)]
 if e:
  for x in e.iter():
   tag=x.tag.rsplit('}',1)[-1]
   if tag in ('cost','constraint','modifier','condition','categoryLink','entryLink','selectionEntry') and (x is not e):
    if tag in ('cost','constraint','modifier','condition','categoryLink') or 'transponder' in (x.get('name') or '').lower() or 'Mastery Level 3' in (x.get('name') or ''):
     out.append('  '+line(x))
Path('inspection-r20-ts-guard-details.txt').write_text('\\n'.join(out),encoding='utf-8')
print('\\n'.join(out))
