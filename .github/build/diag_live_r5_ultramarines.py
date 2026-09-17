from pathlib import Path
import xml.etree.ElementTree as ET

CAT=Path('Legiones Astartes.cat'); OUT=Path('inspection-live-r5-ultramarines.txt')
NS='http://www.battlescribe.net/schema/catalogueSchema'; C=lambda t:f'{{{NS}}}{t}'
root=ET.parse(CAT).getroot()

def pts(e):
    cs=e.find(C('costs'))
    if cs is not None:
        p=next((x for x in cs.findall(C('cost')) if x.get('typeId')=='pts'),None)
        if p is not None:return p.get('value')
    return ''

def constraints(e):
    cs=e.find(C('constraints')); out=[]
    if cs is not None:
        for x in cs:
            out.append(f'{x.get("type")}={x.get("value")} scope={x.get("scope")} child={x.get("childId")} field={x.get("field")}')
    return '; '.join(out)

def ruletexts(e):
    rs=e.find(C('rules')); out=[]
    if rs is not None:
        for r in rs:
            d=r.find(C('description'))
            out.append((r.get('name') or '')+': '+((d.text or '') if d is not None else ''))
    return out

def direct_children(parent,tagcontainer):
    c=parent.find(C(tagcontainer)); return list(c) if c is not None else []

lines=[f'CAT={root.get("revision")} GST={root.get("gameSystemRevision")}']
# XIII Legion selector and rites
for xid in ('legion-xiii','r25-rite-xiii-0-the-logos-lectora','r25-rite-xiii-1-vigil-opertii-mission'):
    e=next((x for x in root.iter() if x.get('id')==xid),None)
    lines+=['',f'=== {xid} | {(e.get("name") if e is not None else "MISSING")} ===']
    if e is not None:
        lines.append('constraints='+constraints(e))
        lines += ruletexts(e)

# Direct top-level XIII units only
se=root.find(C('sharedSelectionEntries'))
if se is None: se=root.find(C('selectionEntries'))
# robust: all units whose IDs begin with exact XIII prefix, excluding cloned prefixed copies
for u in root.iter(C('selectionEntry')):
    uid=u.get('id') or ''
    if not uid.startswith('r41-unit-xiii-') or u.get('type')!='unit': continue
    lines+=['',f'=== UNIT {uid} | {u.get("name")} | pts={pts(u)} | constraints={constraints(u)} ===']
    for r in ruletexts(u): lines.append('RULE '+r)
    for m in direct_children(u,'selectionEntries'):
        lines.append(f'CHILD id={m.get("id")} name={m.get("name")} type={m.get("type")} pts={pts(m)} constraints={constraints(m)} default={m.get("defaultAmount")}')
    for g in direct_children(u,'selectionEntryGroups'):
        lines.append(f'GROUP id={g.get("id")} name={g.get("name")} constraints={constraints(g)}')
        for cont in ('selectionEntries','entryLinks'):
            for x in direct_children(g,cont):
                lines.append(f'  {cont[:-1]} id={x.get("id")} name={x.get("name")} type={x.get("type")} target={x.get("targetId")} pts={pts(x)} constraints={constraints(x)} default={x.get("defaultAmount")}')
                for rr in ruletexts(x): lines.append('    RULE '+rr)

# Any UM-specific r45/r46 entries
for e in root.iter():
    eid=e.get('id') or ''
    if eid.startswith(('r45-um-','r45-praetor-um-','r45-hq-praetor-um-','r45-hq-centurion-um-','r45-tactical-unit-um-','r45-breacher-unit-um-','r45-veteran-unit-um-')):
        lines += ['',f'=== UM EXTRA {eid} | {e.get("name")} | tag={e.tag.split("}")[-1]} pts={pts(e)} constraints={constraints(e)} ===']
        for rr in ruletexts(e): lines.append('RULE '+rr)

# Generic librarian power group for reuse
lib=next((x for x in root.iter(C('selectionEntryGroup')) if x.get('id')=='r29-lib-power-group'),None)
if lib is not None:
    lines += ['',f'=== GENERIC LIB POWER GROUP constraints={constraints(lib)} ===']
    for x in direct_children(lib,'selectionEntries'):
        lines.append(f'POWER id={x.get("id")} name={x.get("name")} pts={pts(x)} constraints={constraints(x)}')
        # only list modifiers shallowly
        ms=x.find(C('modifiers'))
        if ms is not None:
            lines.append('  MODIFIERS '+ET.tostring(ms,encoding='unicode'))

OUT.write_text('\n'.join(lines),encoding='utf-8')
print('\n'.join(lines))
