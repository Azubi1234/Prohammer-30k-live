from pathlib import Path
import xml.etree.ElementTree as ET
CAT=Path('Legiones Astartes.cat'); OUT=Path('inspection-r8-command-retinues.txt')
NS='http://www.battlescribe.net/schema/catalogueSchema'; C=lambda t:f'{{{NS}}}{t}'
root=ET.parse(CAT).getroot(); lines=[]
def dump(e):
 lines.append(f'ENTRY {e.get("id")} {e.get("name")} type={e.get("type")}')
 for g in list(e.find(C('selectionEntryGroups')) or []):
  if 'retinue' in (g.get('name') or '').lower() or 'armour' in (g.get('name') or '').lower():
   lines.append(f' GROUP {g.get("id")} {g.get("name")}')
   m=g.find(C('modifiers'))
   if m is not None: lines.append('  GMODS '+ET.tostring(m,encoding='unicode'))
   for cn in ('selectionEntries','entryLinks'):
    c=g.find(C(cn))
    if c is not None:
     for x in c:
      lines.append(f'  OPT {x.get("id")} {x.get("name")} type={x.get("type")} target={x.get("targetId")} hidden={x.get("hidden")}')
      mm=x.find(C('modifiers'))
      if mm is not None: lines.append('   MODS '+ET.tostring(mm,encoding='unicode'))
for id_ in ('hq-praetor','hq-centurion'):
 e=next((x for x in root.iter(C('selectionEntry')) if x.get('id')==id_),None)
 lines.append('=== '+id_+' ===')
 if e is not None: dump(e)
for id_ in ('hq-praetor-ret-honour','hq-praetor-ret-termcommand','hq-centurion-ret-command','hq-centurion-ret-termcommand'):
 e=next((x for x in root.iter(C('selectionEntry')) if x.get('id')==id_),None)
 lines.append(f'RAW {id_}: '+(ET.tostring(e,encoding='unicode')[:5000] if e is not None else 'MISSING'))
OUT.write_text('\n'.join(lines),encoding='utf-8'); print('\n'.join(lines))
