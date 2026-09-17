from pathlib import Path
import xml.etree.ElementTree as ET
P=Path('Legiones Astartes.cat'); O=Path('inspection-r17-ts-shared.txt')
NS='http://www.battlescribe.net/schema/catalogueSchema'; C=lambda t:f'{{{NS}}}{t}'
r=ET.parse(P).getroot()

def t(e): return ' '.join((e.text or '').split()) if e is not None else ''
def dump(e):
 out=[f"{e.tag.rsplit('}',1)[-1]} {e.get('id')} | {e.get('name')} | type={e.get('type')} hidden={e.get('hidden')}"]
 for key in ['costs','constraints','modifiers','rules','profiles','categoryLinks','entryLinks','selectionEntryGroups','selectionEntries']:
  c=e.find(C(key))
  if c is not None:
   out.append(key+': '+ET.tostring(c,encoding='unicode')[:12000])
 return out
lines=[f"CAT={r.get('revision')}"]
for e in r.iter():
 i=e.get('id') or ''; n=e.get('name') or ''
 if i.startswith('r45-ts-') or i.startswith('r45-cult-') and any(x in i for x in ['hq-praetor','hq-centurion','tactical-unit','veteran-unit','terminator-unit']) or 'Psychic Powers' in n or 'Psychic Discipline' in n:
  lines.append('\n=== ENTRY ==='); lines.extend(dump(e))
O.write_text('\n'.join(lines),encoding='utf-8'); print('bytes',O.stat().st_size)
