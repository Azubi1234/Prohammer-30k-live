from pathlib import Path
import xml.etree.ElementTree as ET
ct=ET.parse('Legiones Astartes.cat');r=ct.getroot();ns=r.tag.split('}')[0].strip('{');C=lambda x:f'{{{ns}}}{x}'
gt=ET.parse('Prohammer 30k.gst');gr=gt.getroot();gns=gr.tag.split('}')[0].strip('{');G=lambda x:f'{{{gns}}}{x}'
def f(root,i):return next((e for e in root.iter() if e.get('id')==i),None)
def line(e):
 if e is None:return 'MISSING'
 return e.tag.rsplit('}',1)[-1]+' | '+' | '.join(f'{k}={e.get(k)}' for k in ('id','name','type','hidden','targetId','field','value','scope','childId','primary') if e.get(k)!=None)
out=[]
for i in ['r18-ts-cat-sekhmet-limit','r18-final-cat-sekhmet-01']:
 out+=['=== CAT '+i+' ===',line(f(gr,i))]
for e in gr.iter(G('categoryLink')):
 if e.get('targetId') in ('r18-ts-cat-sekhmet-limit','r18-final-cat-sekhmet-01'):
  out.append('LINK '+line(e))
  for x in e.iter():
   if x is e:continue
   if x.tag.rsplit('}',1)[-1] in ('constraint','modifier','condition'):
    out.append('  '+line(x))
Path('inspection-r25-sekhmet-limits.txt').write_text('\n'.join(out),encoding='utf-8')
print('\n'.join(out))
