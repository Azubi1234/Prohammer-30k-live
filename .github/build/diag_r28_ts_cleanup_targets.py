from pathlib import Path
import xml.etree.ElementTree as ET

CAT=Path('Legiones Astartes.cat')
OUT=Path('inspection-r28-ts-cleanup-targets.txt')
NS='http://www.battlescribe.net/schema/catalogueSchema'
C=lambda t:f'{{{NS}}}{t}'
root=ET.parse(CAT).getroot()
pm={c:p for p in root.iter() for c in p}

def host(e):
    cur=e
    while cur is not None:
        if cur.tag==C('selectionEntry') and cur.get('type')=='unit':
            return cur
        cur=pm.get(cur)
    return None

def cons(e):
    out=[]
    cs=e.find(C('constraints'))
    if cs is not None:
        for x in cs:
            out.append(f"{x.get('id')}:{x.get('type')}:{x.get('field')}:{x.get('value')}:{x.get('scope')}")
    return out

def mods(e):
    out=[]
    ms=e.find(C('modifiers'))
    if ms is not None:
        for m in ms:
            s=f"{m.get('id')}:{m.get('type')}:{m.get('field')}={m.get('value')}"
            for q in m.iter():
                if q.tag==C('condition'):
                    s+=f" | COND {q.get('type')} {q.get('field')} {q.get('value')} scope={q.get('scope')} child={q.get('childId')}"
            out.append(s)
    return out

def dump_tree(e,depth=0,maxdepth=4):
    lines=[]
    ind='  '*depth
    tag=e.tag.rsplit('}',1)[-1]
    lines.append(f"{ind}{tag} id={e.get('id')} name={e.get('name')} type={e.get('type')} hidden={e.get('hidden')} target={e.get('targetId')} cons={cons(e)}")
    for m in mods(e): lines.append(ind+'  MOD '+m)
    if depth<maxdepth:
        for key in ('selectionEntries','selectionEntryGroups','entryLinks','categoryLinks'):
            box=e.find(C(key))
            if box is not None:
                for x in box:
                    lines.extend(dump_tree(x,depth+1,maxdepth))
    return lines

lines=[f"CAT revision={root.get('revision')}"]

lines.append('\n=== UNIVERSAL THOUSAND SONS RULE TEXT TARGETS ===')
for r in root.iter(C('rule')):
    n=(r.get('name') or '')
    d=r.find(C('description'))
    tx=' '.join((d.text or '').split()) if d is not None else ''
    blob=(n+' '+tx).lower()
    if 'sorcerers of prospero' in blob or 'prosperine cults' in blob or n.lower() in ('prosperine cults','the prosperine cults'):
        h=host(r)
        lines.append(f"RULE id={r.get('id')} name={n} host={(h.get('id') if h is not None else 'NONE')} hidden={r.get('hidden')}\n{tx}")

lines.append('\n=== VETERAN UNIT FULL DIRECT STRUCTURE ===')
v=next((e for e in root.iter(C('selectionEntry')) if e.get('id')=='veteran-unit'),None)
if v is None: raise RuntimeError('veteran-unit missing')
lines += dump_tree(v,0,5)

lines.append('\n=== MAGNUS ROOT + THRESHOLD ELEMENTS ===')
mag=next((e for e in root.iter(C('selectionEntry')) if e.get('id')=='r41-unit-xv-11-xv-magnus-the-red-the-crimson-king'),None)
if mag is None: raise RuntimeError('Magnus missing')
lines += dump_tree(mag,0,2)
for e in mag.iter():
    blob=ET.tostring(e,encoding='unicode')
    if 'limit::' in blob or '2000' in blob:
        lines.append('THRESHOLD '+ET.tostring(e,encoding='unicode'))

lines.append('\n=== PROSPERINE CULT GROUPS ===')
for g in root.iter(C('selectionEntryGroup')):
    if 'prosperine cult' in (g.get('name') or '').lower():
        h=host(g)
        lines.append(f"GROUP {g.get('id')} | {g.get('name')} | HOST={(h.get('id') if h is not None else 'NONE')} {(h.get('name') if h is not None else '')} | cons={cons(g)}")
        for m in mods(g): lines.append('  MOD '+m)
        ses=g.find(C('selectionEntries'))
        if ses is not None:
            for x in ses:
                lines.append(f"  CHOICE {x.get('id')} | {x.get('name')} | hidden={x.get('hidden')} | cons={cons(x)}")
                for m in mods(x): lines.append('    MOD '+m)

lines.append('\n=== PSYCHIC DISCIPLINE/POWER GROUPS ON RELEVANT HOSTS ===')
relevant={'hq-praetor','hq-centurion','tactical-unit','veteran-unit','terminator-unit',
'r41-unit-xv-0-sekhmet-terminator-cabal','r27-guard-sekhmet-terminator-cabal',
'r41-unit-xv-2-ammitara-occult-intercession-cabal','r41-unit-xv-3-castellax-achea-maniple',
'r41-unit-xv-4-contemptor-osiron-dreadnought','r41-unit-xv-7-phosis-t-kar',
'r41-unit-xv-8-magistus-amon-the-hidden','r41-unit-xv-9-hathor-maat','r41-unit-xv-10-sanakht',
'r41-unit-xv-11-xv-magnus-the-red-the-crimson-king'}
for g in root.iter(C('selectionEntryGroup')):
    h=host(g)
    if h is None or h.get('id') not in relevant: continue
    nm=(g.get('name') or '').lower()
    if 'psychic' in nm or 'discipline' in nm or 'prosperine cult' in nm:
        lines.append(f"HOST {h.get('id')} {h.get('name')} :: GROUP {g.get('id')} {g.get('name')} cons={cons(g)}")
        for m in mods(g): lines.append('  MOD '+m)

lines.append('\n=== TS SPECIAL UNIT DIRECT GROUP SUMMARY ===')
for uid in sorted(relevant):
    h=next((e for e in root.iter(C('selectionEntry')) if e.get('id')==uid),None)
    if h is None: continue
    lines.append(f"\nUNIT {uid} | {h.get('name')}")
    for g in list(h.find(C('selectionEntryGroups')) or []):
        lines.append(f"  GROUP {g.get('id')} | {g.get('name')} | cons={cons(g)}")
    for e in list(h.find(C('selectionEntries')) or []):
        n=(e.get('name') or '')
        if 'brother' in n.lower() or 'mastery' in n.lower() or 'cult' in n.lower():
            lines.append(f"  ENTRY {e.get('id')} | {n} | cons={cons(e)}")
            for m in mods(e): lines.append('    MOD '+m)

OUT.write_text('\n'.join(lines),encoding='utf-8')
print('wrote',OUT,'lines',len(lines),'bytes',OUT.stat().st_size)
