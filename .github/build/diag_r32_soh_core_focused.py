from pathlib import Path
import xml.etree.ElementTree as ET
CAT=Path('Legiones Astartes.cat'); GST=Path('Prohammer 30k.gst'); OUT=Path('inspection-r32-soh-core-focused.txt')
CNS='http://www.battlescribe.net/schema/catalogueSchema'; GNS='http://www.battlescribe.net/schema/gameSystemSchema'
C=lambda t:f'{{{CNS}}}{t}'; G=lambda t:f'{{{GNS}}}{t}'
r=ET.parse(CAT).getroot(); gr=ET.parse(GST).getroot()
pm={c:p for p in r.iter() for c in p}
def fid(root,i): return next((x for x in root.iter() if x.get('id')==i),None)
def host(e):
    cur=e
    while cur is not None:
        if cur.tag==C('selectionEntry') and cur.get('type')=='unit': return cur
        cur=pm.get(cur)
    return None
def cons(e,ns=C):
    box=e.find(ns('constraints')); return [(x.get('id'),x.get('type'),x.get('field'),x.get('value'),x.get('scope')) for x in list(box or [])]
def mods(e,ns=C):
    out=[]; box=e.find(ns('modifiers'))
    for m in list(box or []):
        qs=[(q.get('type'),q.get('field'),q.get('value'),q.get('scope'),q.get('childId')) for q in m.iter(ns('condition'))]
        out.append((m.get('id'),m.get('type'),m.get('field'),m.get('value'),qs))
    return out
lines=[f'CAT={r.get("revision")} GST={gr.get("revision")}']

lines.append('\n=== XVI ARMOURY LINKS BY HOST ===')
for e in r.iter():
    blob=ET.tostring(e,encoding='unicode').lower()
    if e.tag in (C('entryLink'),C('selectionEntry'),C('selectionEntryGroup')) and any(k in blob for k in ('r46-soh-','legion-xvi')):
        h=host(e)
        if e.tag==C('entryLink') or (e.tag==C('selectionEntryGroup') and 'sons of horus' in (e.get('name') or '').lower()):
            lines.append(f"{e.tag.rsplit('}',1)[-1]} {e.get('id')} {e.get('name')} target={e.get('targetId')} host={(h.get('id') if h is not None else 'NONE')} {(h.get('name') if h is not None else '')} cons={cons(e)} mods={mods(e)}")

lines.append('\n=== RITES RAW ===')
for rid in ('r25-rite-xvi-0-the-long-march','r25-rite-xvi-1-the-black-reaving'):
    e=fid(r,rid)
    lines.append(ET.tostring(e,encoding='unicode') if e is not None else 'MISSING '+rid)

lines.append('\n=== XVI UNIQUE ROOT SUMMARIES ===')
for e in r.iter(C('selectionEntry')):
    name=(e.get('name') or '').upper()
    if e.get('type')=='unit' and any(k in name for k in ('JUSTAERIN','REAVER ATTACK','CHIEFTAIN SQUAD','LUPERCI')):
        lines.append(f"{e.get('id')} {e.get('name')} costs={[(x.get('name'),x.get('value')) for x in list(e.find(C('costs')) or [])]} cats={[(x.get('name'),x.get('targetId'),x.get('primary'),x.get('hidden')) for x in list(e.find(C('categoryLinks')) or [])]} cons={cons(e)} mods={mods(e)}")
        for x in list(e.find(C('selectionEntries')) or []):
            lines.append(f"  ENTRY {x.get('id')} {x.get('name')} type={x.get('type')} costs={[(c.get('name'),c.get('value')) for c in list(x.find(C('costs')) or [])]} cons={cons(x)} mods={mods(x)}")
        for g in list(e.find(C('selectionEntryGroups')) or []):
            lines.append(f"  GROUP {g.get('id')} {g.get('name')} cons={cons(g)} mods={mods(g)}")

lines.append('\n=== ANALOGUES: NON-COMPULSORY TROOPS TEXT ===')
for rule in r.iter(C('rule')):
    d=rule.find(C('description')); t=(d.text or '') if d is not None else ''
    if 'non-compulsory Troops' in t or 'may not fulfil compulsory Troops' in t:
        # nearest selection entry ancestor
        cur=pm.get(rule)
        while cur is not None and cur.tag!=C('selectionEntry'): cur=pm.get(cur)
        lines.append(f"RULE {rule.get('id')} {rule.get('name')} host={(cur.get('id') if cur is not None else 'NONE')} {(cur.get('name') if cur is not None else '')} :: {' '.join(t.split())[:1000]}")

lines.append('\n=== GST CATEGORY LINKS / XVI / ANALOGUE TROOPS ===')
for fe in gr.iter(G('forceEntry')):
    for cl in fe.iter(G('categoryLink')):
        blob=ET.tostring(cl,encoding='unicode').lower()
        if 'xvi' in blob or 'non-compulsory' in blob or 'reaver' in blob or 'justaerin' in blob:
            lines.append(f"{fe.get('id')} {fe.get('name')} :: {cl.get('id')} {cl.get('name')} target={cl.get('targetId')} cons={cons(cl,G)} mods={mods(cl,G)}")

OUT.write_text('\n'.join(lines),encoding='utf-8'); print('bytes',OUT.stat().st_size)
