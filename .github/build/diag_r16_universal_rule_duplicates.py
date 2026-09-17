from pathlib import Path
from collections import defaultdict
import re
import xml.etree.ElementTree as ET

CAT=Path('Legiones Astartes.cat'); OUT=Path('inspection-r16-universal-rule-duplicates.txt')
NS='http://www.battlescribe.net/schema/catalogueSchema'; C=lambda t:f'{{{NS}}}{t}'
root=ET.parse(CAT).getroot()

# Rule names that are used as universal/shared special rules in the catalogue.
USR_NAMES={
    'Fearless','Counter-Attack','Fleet','Deep Strike','Infiltrate','Scout','Move Through Cover',
    'Night Vision','Tank Hunters','Furious Charge','Feel No Pain','Eternal Warrior','Adamantium Will',
    'Fear','Relentless','Slow and Purposeful','Stealth','Shrouded','Rending','Poisoned','Preferred Enemy',
    'Hit and Run','Acute Senses','Outflank','Interceptor','Skyfire','Blind','Concussive','Armourbane',
    'Melta','Gets Hot','Instant Death','Pinning','Sniper','Torrent','Twin-linked','Ignores Cover',
    'And They Shall Know No Fear','Master of the Legion'
}

def norm(s): return re.sub(r'\s+',' ',(s or '').strip())

def label(e): return f"{e.tag.split('}')[-1]} {e.get('id')} | {e.get('name')}"

# direct duplicate rule-name groups on one element
rows=[]
for e in root.iter():
    rs=e.find(C('rules'))
    if rs is None: continue
    by=defaultdict(list)
    for r in rs:
        n=norm(r.get('name'))
        if n in USR_NAMES:
            d=norm((r.find(C('description')).text if r.find(C('description')) is not None else ''))
            by[n].append((r.get('id'),d,r.get('hidden')))
    for n, vals in by.items():
        if len(vals)>1:
            rows.append((label(e),n,vals))

# all repeated description variants by rule name, useful for global cleanup.
variants=defaultdict(lambda: defaultdict(int))
locations=defaultdict(list)
for e in root.iter():
    rs=e.find(C('rules'))
    if rs is None: continue
    for r in rs:
        n=norm(r.get('name'))
        if n in USR_NAMES:
            d=norm((r.find(C('description')).text if r.find(C('description')) is not None else ''))
            if d:
                variants[n][d]+=1
                if len(locations[(n,d)])<6: locations[(n,d)].append(label(e))

lines=[f'CAT={root.get("revision")}', '', f'DIRECT DUPLICATE GROUPS={len(rows)}']
for owner,n,vals in rows[:500]:
    lines.append(f'\n{owner}\n  {n} x{len(vals)}')
    for rid,d,h in vals: lines.append(f'    {rid} hidden={h} | {d}')

lines.append('\n\n=== UNIVERSAL RULE DESCRIPTION VARIANTS ===')
for n in sorted(variants):
    lines.append(f'\n## {n}')
    for d,c in sorted(variants[n].items(), key=lambda kv:(-kv[1],kv[0])):
        lines.append(f'  x{c} | {d}')
        for loc in locations[(n,d)]: lines.append(f'      {loc}')

OUT.write_text('\n'.join(lines), encoding='utf-8')
print(OUT)
