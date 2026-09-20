from pathlib import Path
import xml.etree.ElementTree as ET

CAT=Path('Legiones Astartes.cat')
GST=Path('Prohammer 30k.gst')
OUT=Path('inspection-r32-sons-of-horus-audit.txt')

CNS='http://www.battlescribe.net/schema/catalogueSchema'
GNS='http://www.battlescribe.net/schema/gameSystemSchema'
C=lambda t:f'{{{CNS}}}{t}'
G=lambda t:f'{{{GNS}}}{t}'
root=ET.parse(CAT).getroot()
groot=ET.parse(GST).getroot()

def txt(e):
    return ' '.join((e.text or '').split()) if e is not None else ''

def costs(e):
    box=e.find(C('costs'))
    return [(x.get('name'),x.get('value')) for x in list(box or [])]

def cons(e,ns=C):
    box=e.find(ns('constraints'))
    return [(x.get('id'),x.get('type'),x.get('field'),x.get('value'),x.get('scope')) for x in list(box or [])]

def mods(e,ns=C):
    out=[]
    box=e.find(ns('modifiers'))
    for m in list(box or []):
        qs=[]
        for q in m.iter(ns('condition')):
            qs.append((q.get('type'),q.get('field'),q.get('value'),q.get('scope'),q.get('childId')))
        out.append((m.get('id'),m.get('type'),m.get('field'),m.get('value'),qs))
    return out

def cats(e):
    box=e.find(C('categoryLinks'))
    return [(x.get('id'),x.get('name'),x.get('targetId'),x.get('primary'),x.get('hidden')) for x in list(box or [])]

def walk(e,depth=0,maxdepth=4):
    ind='  '*depth
    tag=e.tag.rsplit('}',1)[-1]
    lines=[f"{ind}{tag} {e.get('id')} | {e.get('name')} | type={e.get('type')} hidden={e.get('hidden')} costs={costs(e)} cons={cons(e)} cats={cats(e)}"]
    for m in mods(e): lines.append(ind+'  MOD '+repr(m))
    rs=e.find(C('rules'))
    for r in list(rs or []):
        d=r.find(C('description'))
        lines.append(f"{ind}  RULE {r.get('id')} | {r.get('name')} | hidden={r.get('hidden')} | {txt(d)[:2000]}")
    ps=e.find(C('profiles'))
    for p in list(ps or []):
        vals=[]
        ch=p.find(C('characteristics'))
        for x in list(ch or []): vals.append(f"{x.get('name')}={txt(x)}")
        lines.append(f"{ind}  PROFILE {p.get('id')} | {p.get('name')} | {' '.join(vals)}")
    if depth < maxdepth:
        for key in ('selectionEntries','selectionEntryGroups','entryLinks'):
            box=e.find(C(key))
            for x in list(box or []):
                if x.tag==C('entryLink'):
                    lines.append(f"{ind}  LINK {x.get('id')} | {x.get('name')} -> {x.get('targetId')} hidden={x.get('hidden')} costs={costs(x)} cons={cons(x)}")
                    for m in mods(x): lines.append(ind+'    MOD '+repr(m))
                else:
                    lines.extend(walk(x,depth+1,maxdepth))
    return lines

lines=[f"CAT revision={root.get('revision')} GST revision={groot.get('revision')}"]

# Legion selector/reference.
lines.append('\n=== LEGION XVI ROOT / REFERENCE ===')
for e in root.iter():
    if e.get('id')=='legion-xvi' or e.get('id')=='r25-legion-xvi-reference':
        lines += walk(e,0,2)

# All named XVI unique units / characters / rites / Horus forms.
terms=[
 'JUSTAERIN','REAVER ATTACK','CHIEFTAIN SQUAD','LUPERCI',
 'ABADDON','LOKEN','MALOGHURST','AXIMAND','TYBALT MARR','FALKUS KIBRE','TARIK TORGADDON','ASHURHADDON',
 'HORUS LUPERCAL','HORUS ASCENDED','THE LONG MARCH','THE BLACK REAVING'
]
seen=set()
lines.append('\n=== SONS OF HORUS NAMED ENTRIES ===')
for e in root.iter(C('selectionEntry')):
    name=(e.get('name') or '').upper()
    if any(t in name for t in terms):
        # only top-level-ish unique entries; still include upgrades.
        key=e.get('id')
        if key in seen: continue
        seen.add(key)
        lines.append('\n--- MATCH ---')
        lines += walk(e,0,5)

# All groups/options/rules with explicit Sons of Horus markers.
lines.append('\n=== GENERIC UNIT SONS OF HORUS INJECTIONS ===')
for uid in ('hq-praetor','hq-centurion','tactical-unit','veteran-unit','terminator-unit','fa-seeker','assault-unit','breacher-unit','destroyer-unit','command-unit','term-command-unit'):
    u=next((e for e in root.iter(C('selectionEntry')) if e.get('id')==uid),None)
    if u is None: continue
    blob=ET.tostring(u,encoding='unicode').lower()
    if 'legion-xvi' not in blob and 'sons of horus' not in blob and 'banestrike' not in blob and 'cthonian' not in blob:
        continue
    lines.append(f"\n--- GENERIC {uid} {u.get('name')} ---")
    for g in list(u.find(C('selectionEntryGroups')) or []):
        gb=ET.tostring(g,encoding='unicode').lower()
        if 'legion-xvi' in gb or 'sons of horus' in gb or 'banestrike' in gb or 'cthonian' in gb or 'transponder' in gb:
            lines += walk(g,0,3)
    for x in list(u.find(C('selectionEntries')) or []):
        xb=ET.tostring(x,encoding='unicode').lower()
        if 'legion-xvi' in xb or 'sons of horus' in xb or 'banestrike' in xb or 'cthonian' in xb or 'transponder' in xb:
            lines += walk(x,0,2)
    for x in list(u.find(C('entryLinks')) or []):
        xb=ET.tostring(x,encoding='unicode').lower()
        if 'legion-xvi' in xb or 'sons of horus' in xb or 'banestrike' in xb or 'cthonian' in xb or 'transponder' in xb:
            lines.append(f"LINK {x.get('id')} | {x.get('name')} -> {x.get('targetId')} hidden={x.get('hidden')} costs={costs(x)} cons={cons(x)} mods={mods(x)}")

# Shared entries that are explicitly SoH armoury/wargear.
lines.append('\n=== SONS OF HORUS ARMOURY / SHARED ENTRIES ===')
for e in root.iter():
    name=(e.get('name') or '')
    blob=(name+' '+(e.get('id') or '')).lower()
    if any(k in blob for k in ('banestrike','cthonian culling','sons of horus armoury','xvi armoury','xvi-trans','soh-')):
        if e.tag in (C('selectionEntry'),C('selectionEntryGroup'),C('profile'),C('rule')):
            lines.append(ET.tostring(e,encoding='unicode')[:12000])

# GST force category modifiers that reference legion-xvi, SoH rites or unique units.
lines.append('\n=== GST / FOC SONS OF HORUS CONDITIONS ===')
for fe in groot.iter(G('forceEntry')):
    for cl in fe.iter(G('categoryLink')):
        blob=ET.tostring(cl,encoding='unicode').lower()
        if any(k in blob for k in ('legion-xvi','sons of horus','reaver','justaerin','long march','black reaving','horus')):
            lines.append(f"FORCE {fe.get('id')} {fe.get('name')} :: {cl.get('id')} {cl.get('name')} target={cl.get('targetId')} cons={cons(cl,G)} mods={mods(cl,G)}")

OUT.write_text('\n'.join(lines),encoding='utf-8')
print('wrote',OUT,'lines',len(lines),'bytes',OUT.stat().st_size)
