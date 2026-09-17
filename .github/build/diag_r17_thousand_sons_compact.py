from pathlib import Path
import xml.etree.ElementTree as ET
CAT=Path('Legiones Astartes.cat'); GST=Path('Prohammer 30k.gst'); OUT=Path('inspection-r17-thousand-sons-compact.txt')
NS='http://www.battlescribe.net/schema/catalogueSchema'; GNS='http://www.battlescribe.net/schema/gameSystemSchema'
C=lambda t:f'{{{NS}}}{t}'; G=lambda t:f'{{{GNS}}}{t}'
root=ET.parse(CAT).getroot(); groot=ET.parse(GST).getroot()

def text(d): return ' '.join((d.text or '').split()) if d is not None else ''
def cost(e):
 c=e.find(C('costs'))
 return ','.join(f"{x.get('name')}={x.get('value')}" for x in c) if c is not None else ''
def constraints(e):
 c=e.find(C('constraints'))
 return ';'.join(f"{x.get('type')}:{x.get('value')}:{x.get('field')}:{x.get('scope')}" for x in c) if c is not None else ''
def cats(e):
 c=e.find(C('categoryLinks'))
 return ','.join(f"{x.get('name')}->{x.get('targetId')}" for x in c) if c is not None else ''
def walk(e,depth=0,maxdepth=3):
 lines=[]; ind='  '*depth; tag=e.tag.rsplit('}',1)[-1]
 lines.append(f"{ind}{tag} {e.get('id')} | {e.get('name')} | type={e.get('type')} pts={cost(e)} cons={constraints(e)} cats={cats(e)} hidden={e.get('hidden')}")
 rs=e.find(C('rules'))
 if rs is not None:
  for r in rs:
   d=r.find(C('description')); lines.append(f"{ind} RULE {r.get('id')} | {r.get('name')} | hidden={r.get('hidden')} | {text(d)[:500]}")
 ps=e.find(C('profiles'))
 if ps is not None:
  for p in ps:
   vals=[]; ch=p.find(C('characteristics'))
   if ch is not None:
    vals=[f"{x.get('name')}={text(x)}" for x in ch]
   lines.append(f"{ind} PROFILE {p.get('id')} | {p.get('name')} | {' '.join(vals)}")
 if depth<maxdepth:
  for key in ('selectionEntryGroups','selectionEntries','entryLinks'):
   cont=e.find(C(key))
   if cont is None: continue
   for x in cont:
    if x.tag==C('entryLink'):
     lines.append(f"{ind} LINK {x.get('id')} | {x.get('name')} -> {x.get('targetId')} pts={cost(x)} cons={constraints(x)} hidden={x.get('hidden')}")
    else: lines.extend(walk(x,depth+1,maxdepth))
 return lines

lines=[f"CAT={root.get('revision')} GSTref={root.get('gameSystemRevision')}"]
for e in root.iter(C('selectionEntry')):
 i=e.get('id') or ''
 if i.startswith('r41-unit-xv-') or i.startswith('r25-rite-xv-') or i=='legion-xv':
  lines.append('\n=== ROOT XV ==='); lines.extend(walk(e,0,3))
for e in root.iter(C('selectionEntry')):
 if e.get('id') in ['hq-praetor','hq-centurion','tactical-unit','veteran-unit','terminator-unit','assault-unit','breacher-unit','recon-unit','destroyer-unit','fa-seeker','hs-heavy-support-squad']:
  blob=ET.tostring(e,encoding='unicode')
  if any(k in blob for k in ['legion-xv','r25-rite-xv','Thousand Sons','Prosperine','Brotherhood of Psykers']):
   lines.append(f"\n=== CORE {e.get('id')} ==="); lines.extend(walk(e,0,3))
lines.append('\n=== GST XV MODIFIERS ===')
for fe in groot.iter(G('forceEntry')):
 for cl in fe.iter(G('categoryLink')):
  blob=ET.tostring(cl,encoding='unicode')
  if any(k in blob for k in ['legion-xv','r25-rite-xv']):
   lines.append(f"FORCE {fe.get('id')} {fe.get('name')} / {cl.get('id')} {cl.get('name')} target={cl.get('targetId')}")
   cons=cl.find(G('constraints'))
   if cons is not None:
    for c in cons: lines.append(f"  CON {c.get('id')} {c.get('type')}={c.get('value')} field={c.get('field')}")
   mods=cl.find(G('modifiers'))
   if mods is not None:
    for m in mods: lines.append('  MOD '+ET.tostring(m,encoding='unicode')[:1000])
OUT.write_text('\n'.join(lines),encoding='utf-8')
print('lines',len(lines),'bytes',OUT.stat().st_size)
