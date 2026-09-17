from pathlib import Path
import xml.etree.ElementTree as ET
CAT=Path('Legiones Astartes.cat'); OUT=Path('inspection-r6-ultramarines-remaining.txt')
NS='http://www.battlescribe.net/schema/catalogueSchema'; C=lambda t:f'{{{NS}}}{t}'
root=ET.parse(CAT).getroot(); lines=[f'CAT={root.get("revision")} GST={root.get("gameSystemRevision")}']
for e in root.iter(C('selectionEntry')):
    n=(e.get('name') or '')
    if 'librarian' in n.lower() or 'vigilator' in n.lower() or 'damocles' in n.lower() or 'master of signals' in n.lower():
        lines += ['',f'ENTRY {e.get("id")} | {n} | type={e.get("type")} hidden={e.get("hidden")}']
        gs=e.find(C('selectionEntryGroups'))
        if gs is not None:
            for g in gs:
                lines.append(f' GROUP {g.get("id")} | {g.get("name")}')
for e in root.iter():
    n=(e.get('name') or '').lower(); i=(e.get('id') or '').lower()
    if 'loyalist' in n or 'traitor' in n or 'allegiance' in n or 'loyalist' in i or 'traitor' in i or 'allegiance' in i:
        lines.append(f'ALLEGIANCE? {e.tag.split("}")[-1]} id={e.get("id")} name={e.get("name")} type={e.get("type")}')
OUT.write_text('\n'.join(lines),encoding='utf-8'); print('\n'.join(lines))
