from pathlib import Path
import xml.etree.ElementTree as ET
g=ET.parse('Prohammer 30k.gst').getroot(); ns=g.tag.split('}')[0].strip('{'); G=lambda x:f'{{{ns}}}{x}'
def f(i):return next((e for e in g.iter() if e.get('id')==i),None)
def line(e):
 return e.tag.rsplit('}',1)[-1]+' | '+' | '.join(f'{k}={e.get(k)}' for k in ('id','name','type','hidden','targetId','field','value','scope','childId') if e.get(k)!=None)
out=[]
for i in ['r18-ts-fl-hq-max','r18-ts-fl-elites-max','r18-ts-fl-fast-max','r18-ts-fellowships-fast-max','r18-ts-brotherhood-min-fellowships','r19-ts-rite-limit-max']:
 e=f(i);out+=['=== '+i+' ===',line(e)]
 if e:
  for x in e.iter():
   if x is e:continue
   if x.tag.rsplit('}',1)[-1] in ('condition','conditionGroup','constraint','modifier'):
    out.append('  '+line(x))
Path('inspection-r24-ts-gst-rite-conditions.txt').write_text('\n'.join(out),encoding='utf-8')
print('\n'.join(out))
