from pathlib import Path
import xml.etree.ElementTree as ET
t=ET.parse('Legiones Astartes.cat');r=t.getroot();ns=r.tag.split('}')[0].strip('{');C=lambda x:f'{{{ns}}}{x}'
def line(e):
 return e.tag.rsplit('}',1)[-1]+' | '+' | '.join(f'{k}={e.get(k)}' for k in ('id','name','type','hidden','targetId','field','value','scope','childId') if e.get(k)!=None)
def pts(e):
 return [(x.get('name'),x.get('value')) for x in e.iter(C('cost'))]
out=[f'CAT={r.get("revision")}']
for u in r.iter(C('selectionEntry')):
 if u.get('type')!='unit': continue
 n=(u.get('name') or '').lower()
 if any(k in n for k in ['assault squad','bike squadron','attack bike','sky hunter','destroyer squad','destroyer']):
  # only generic-ish and visible copies
  out.append('\nUNIT '+line(u)+' costs='+str(pts(u)[:3]))
  # model direct children
  ses=u.find(C('selectionEntries'))
  for e in list(ses) if ses is not None else []:
   if e.get('type')=='model':
    out.append('  MODEL '+line(e)+' costs='+str(pts(e)[:3]))
    for c in e.iter(C('constraint')): out.append('    '+line(c))
  for l in u.iter(C('entryLink')):
   if 'bionic' in (l.get('name') or '').lower() or 'jump' in (l.get('name') or '').lower():
    out.append('  LINK '+line(l)+' costs='+str(pts(l)[:3]))
  for e in u.iter(C('selectionEntry')):
   if e is not u and ('jump' in (e.get('name') or '').lower() or 'bike' in (e.get('name') or '').lower()):
    out.append('  OPT '+line(e)+' costs='+str(pts(e)[:3]))
Path('inspection-r19-ih-mobile-units.txt').write_text('\n'.join(out),encoding='utf-8')
print('\n'.join(out[:1000]))
