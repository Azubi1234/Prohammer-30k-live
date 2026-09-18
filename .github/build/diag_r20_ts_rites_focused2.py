from pathlib import Path
import xml.etree.ElementTree as ET
t=ET.parse('Legiones Astartes.cat');r=t.getroot();ns=r.tag.split('}')[0].strip('{');C=lambda x:f'{{{ns}}}{x}'
def f(i): return next((e for e in r.iter() if e.get('id')==i),None)
def line(e):
 if e is None:return 'MISSING'
 return e.tag.rsplit('}',1)[-1]+' | '+' | '.join(f'{k}={e.get(k)}' for k in ('id','name','type','hidden','targetId','field','value','scope','childId','primary') if e.get(k)!=None)
def desc(e):
 d=e.find(C('description'));return (d.text or '') if d is not None else ''
out=[f'CAT={r.get("revision")}']
for i in ['r45-tactical-ts-brother','r45-ts-tactical-brotherhood','r45-ts-brotherhood','r45-ts-brotherhood-fellowship',
          'r45-veteran-ts-brother','r45-terminator-ts-brother']:
 e=f(i);out+=['\\n=== '+i+' ===',line(e)]
 if e:
  for x in e.iter():
   tag=x.tag.rsplit('}',1)[-1]
   if tag in ('categoryLink','constraint','modifier','condition','cost','rule'):
    out.append('  '+line(x)+((' DESC='+desc(x)[:600]) if tag=='rule' else ''))

out.append('\\n=== ALL BROTHERHOOD CATEGORY LINKS ===')
for x in r.iter(C('categoryLink')):
 if x.get('targetId')=='r18-ts-cat-brotherhood':
  out.append(line(x))
  # parents
  pm={c:p for p in r.iter() for c in p};p=pm.get(x)
  for n in range(5):
   if p is None:break
   out.append('  P'+str(n+1)+' '+line(p));p=pm.get(p)

out.append('\\n=== ALL TACTICAL TS/FELLOWS MODIFIERS ===')
tac=f('tactical-unit')
if tac:
 for x in tac.iter():
  eid=x.get('id') or ''
  if 'ts' in eid.lower() or 'fellow' in eid.lower() or 'brother' in (x.get('name') or '').lower():
   tag=x.tag.rsplit('}',1)[-1]
   if tag in ('selectionEntry','selectionEntryGroup','entryLink','modifier','condition','categoryLink','constraint','cost','rule'):
    out.append(line(x)+((' DESC='+desc(x)[:700]) if tag=='rule' else ''))

out.append('\\n=== GUARD SEKHMET CATEGORY / TRANSPONDER ===')
for sid in ['r41-unit-xv-0-sekhmet-terminator-cabal','r41-unit-xv-11-xv-magnus-the-red-the-crimson-king','r18-ts-guard-praetor-ml3']:
 e=f(sid);out+=['\\n'+line(e)]
 if e:
  for x in e.iter():
   tag=x.tag.rsplit('}',1)[-1]
   if tag in ('categoryLink','constraint','modifier','condition','entryLink','selectionEntry'):
    if tag in ('categoryLink','constraint','modifier','condition') or 'transponder' in (x.get('name') or '').lower() or 'Mastery Level 3' in (x.get('name') or ''):
     out.append('  '+line(x))

Path('inspection-r20-ts-rites-focused2.txt').write_text('\\n'.join(out),encoding='utf-8')
print('\\n'.join(out[:2200]))
