from pathlib import Path
import xml.etree.ElementTree as ET
ct=ET.parse('Legiones Astartes.cat');r=ct.getroot();ns=r.tag.split('}')[0].strip('{');C=lambda t:f'{{{ns}}}{t}'
def f(i):return next((e for e in r.iter() if e.get('id')==i),None)
def dump(e,d=0):
 o=[]
 def rec(x,n):
  if n<=6:
   tag=x.tag.rsplit('}',1)[-1]
   if tag in ('selectionEntryGroup','selectionEntry','entryLink','modifier','condition','constraint','rule'):
    o.append('  '*n+tag+' | '+' | '.join(f'{k}={x.get(k)}' for k in ('id','name','type','hidden','targetId','field','value','scope','childId') if x.get(k)!=None))
  if n<6:
   for c in list(x):rec(c,n+1)
 if e is not None:rec(e,0)
 else:o.append('MISSING')
 return o
out=[]
for i in ['r29-lib-discipline-group','r29-lib-power-group','hq-consul-librarian','hq-consul-librarian-epistolary']:
 out+=['=== '+i+' ===']+dump(f(i))
Path('inspection-r18-librarian-hierarchy.txt').write_text('\n'.join(out))
print('\n'.join(out))
