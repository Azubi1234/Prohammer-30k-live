from pathlib import Path
import xml.etree.ElementTree as ET
CAT=Path('Legiones Astartes.cat'); OUT=Path('inspection-r28b-ts-vets-magnus.txt')
NS='http://www.battlescribe.net/schema/catalogueSchema'; C=lambda t:f'{{{NS}}}{t}'
r=ET.parse(CAT).getroot()
def fid(i): return next((x for x in r.iter() if x.get('id')==i),None)
def cons(e):
    cs=e.find(C('constraints')); return [(x.get('id'),x.get('type'),x.get('field'),x.get('value'),x.get('scope')) for x in list(cs or [])]
def mods(e):
    ms=e.find(C('modifiers')); out=[]
    for m in list(ms or []):
        qs=[]
        for q in m.iter(C('condition')):
            qs.append((q.get('type'),q.get('field'),q.get('value'),q.get('scope'),q.get('childId')))
        out.append((m.get('id'),m.get('type'),m.get('field'),m.get('value'),qs))
    return out
lines=[f'CAT={r.get("revision")}']
v=fid('veteran-unit'); lines.append('\n=== VETERAN MODELS ===')
for e in list(v.find(C('selectionEntries')) or []):
    if e.get('type')=='model':
        lines.append(f"{e.get('id')} | {e.get('name')} | cost={[(x.get('name'),x.get('value')) for x in list(e.find(C('costs')) or [])]} | cons={cons(e)} | mods={mods(e)}")
lines.append('\n=== VETERAN RELEVANT GROUPS RAW ===')
for gid in ('veteran-melee','veteran-ranged','veteran-individual','veteran-specialists','veteran-equipment'):
    g=fid(gid)
    lines.append(f"\nGROUP {gid} {g.get('name')} cons={cons(g)} mods={mods(g)}")
    for key in ('selectionEntries','entryLinks','selectionEntryGroups'):
        box=g.find(C(key))
        for x in list(box or []):
            lines.append(f" {x.tag.rsplit('}',1)[-1]} {x.get('id')} | {x.get('name')} target={x.get('targetId')} type={x.get('type')} cons={cons(x)} mods={mods(x)}")
            for key2 in ('selectionEntries','entryLinks','selectionEntryGroups'):
                b2=x.find(C(key2))
                for y in list(b2 or []):
                    lines.append(f"   {y.tag.rsplit('}',1)[-1]} {y.get('id')} | {y.get('name')} target={y.get('targetId')} type={y.get('type')} cons={cons(y)} mods={mods(y)}")
lines.append('\n=== MAGNUS CONSTRAINTS/MODIFIERS ===')
m=fid('r41-unit-xv-11-xv-magnus-the-red-the-crimson-king')
lines.append(f"root cons={cons(m)} mods={mods(m)}")
for e in m.iter():
    c=cons(e); md=mods(e)
    if any('2000' in str(z) or 'limit::' in str(z) for z in c+md):
        lines.append(f"{e.tag.rsplit('}',1)[-1]} {e.get('id')} {e.get('name')} cons={c} mods={md}")
lines.append('\n=== AHRIMAN / FIXED CULT PSYCHIC ===')
for e in r.iter(C('selectionEntry')):
    if 'AHRIMAN' in (e.get('name') or '').upper():
        lines.append(f"ENTRY {e.get('id')} {e.get('name')} cons={cons(e)} mods={mods(e)}")
        for g in list(e.find(C('selectionEntryGroups')) or []):
            if 'cult' in (g.get('name') or '').lower() or 'psychic' in (g.get('name') or '').lower() or 'power' in (g.get('name') or '').lower():
                lines.append(f" GROUP {g.get('id')} {g.get('name')} cons={cons(g)} mods={mods(g)}")
                for x in list(g.find(C('selectionEntries')) or []):
                    lines.append(f"  CHOICE {x.get('id')} {x.get('name')} cons={cons(x)} mods={mods(x)}")
OUT.write_text('\n'.join(lines),encoding='utf-8'); print('bytes',OUT.stat().st_size)
