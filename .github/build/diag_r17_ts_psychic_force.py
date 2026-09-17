from pathlib import Path
import xml.etree.ElementTree as ET
CAT=Path('Legiones Astartes.cat'); GST=Path('Prohammer 30k.gst'); OUT=Path('inspection-r17-ts-psychic-force.txt')
NS='http://www.battlescribe.net/schema/catalogueSchema'; GNS='http://www.battlescribe.net/schema/gameSystemSchema'; C=lambda t:f'{{{NS}}}{t}'; G=lambda t:f'{{{GNS}}}{t}'
r=ET.parse(CAT).getroot(); g=ET.parse(GST).getroot()
lines=[f"CAT={r.get('revision')} GST={g.get('revision')}"]
terms=['psychic','biomancy','divination','pyromancy','telekinesis','telepathy','smite','force dome','null zone','gate of infinity','vortex of doom']
for e in r.iter():
 n=(e.get('name') or '').lower(); i=(e.get('id') or '').lower()
 if any(x in n for x in terms) or ('psych' in i and e.tag in (C('selectionEntry'),C('selectionEntryGroup'),C('entryLink'))):
  tag=e.tag.rsplit('}',1)[-1]
  if tag not in ['selectionEntry','selectionEntryGroup','entryLink']: continue
  lines.append(f"\n{tag} {e.get('id')} | {e.get('name')} | type={e.get('type')} target={e.get('targetId')}")
  for k in ['costs','constraints','modifiers','rules','entryLinks','selectionEntries','selectionEntryGroups']:
   x=e.find(C(k))
   if x is not None: lines.append(k+': '+ET.tostring(x,encoding='unicode')[:8000])
lines.append('\n=== ALL FORCE ENTRIES ===')
for fe in g.iter(G('forceEntry')):
 lines.append(f"FORCE {fe.get('id')} | {fe.get('name')}")
 cls=fe.find(G('categoryLinks'))
 if cls is None: continue
 for cl in cls:
  lines.append(f"  CATLINK {cl.get('id')} | {cl.get('name')} -> {cl.get('targetId')}")
  co=cl.find(G('constraints'))
  if co is not None:
   for c in co: lines.append(f"    CON id={c.get('id')} type={c.get('type')} value={c.get('value')} field={c.get('field')} scope={c.get('scope')}")
  mo=cl.find(G('modifiers'))
  if mo is not None:
   for m in mo: lines.append('    MOD '+ET.tostring(m,encoding='unicode')[:2500])
OUT.write_text('\n'.join(lines),encoding='utf-8'); print('bytes',OUT.stat().st_size)
