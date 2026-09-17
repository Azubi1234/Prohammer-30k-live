from pathlib import Path
import xml.etree.ElementTree as ET

CAT=Path('Legiones Astartes.cat')
OUT=Path('inspection-r4-tactical-chainaxe.txt')
NS='http://www.battlescribe.net/schema/catalogueSchema'
C=lambda t:f'{{{NS}}}{t}'
root=ET.parse(CAT).getroot()

lines=[f'CAT revision={root.get("revision")} GSTref={root.get("gameSystemRevision")}']

def constraints(e):
    out=[]
    cs=e.find(C('constraints'))
    if cs is not None:
        for x in cs:
            out.append(f'{x.get("type")}:{x.get("value")} scope={x.get("scope")} field={x.get("field")} child={x.get("childId")}')
    return '; '.join(out)

def cost(e):
    cs=e.find(C('costs'))
    if cs is not None:
        for x in cs:
            if x.get('typeId')=='pts': return x.get('value')
    return ''

def immediate_models(u):
    out=[]
    for container_name in ('selectionEntries','entryLinks'):
        cont=u.find(C(container_name))
        if cont is None: continue
        for x in cont:
            if x.tag==C('selectionEntry') and x.get('type')=='model':
                out.append(x)
    return out

for u in root.iter(C('selectionEntry')):
    if u.get('type')!='unit': continue
    nm=(u.get('name') or '')
    if nm.strip().upper()=='LEGION TACTICAL SQUAD':
        lines += ['',f'=== TACTICAL {u.get("id")} | {nm} | pts={cost(u)} ===']
        for m in immediate_models(u):
            lines.append(f'MODEL id={m.get("id")} name={m.get("name")} pts={cost(m)} constraints={constraints(m)}')
        gs=u.find(C('selectionEntryGroups'))
        if gs is not None:
            for g in gs:
                lines.append(f'GROUP id={g.get("id")} name={g.get("name")} constraints={constraints(g)}')
                for cont_name in ('selectionEntries','entryLinks'):
                    cont=g.find(C(cont_name))
                    if cont is not None:
                        for x in cont:
                            lines.append(f'  {x.tag.split("}")[-1]} id={x.get("id")} name={x.get("name")} type={x.get("type")} target={x.get("targetId")} pts={cost(x)} constraints={constraints(x)}')

for u in root.iter(C('selectionEntry')):
    if u.get('type')!='unit': continue
    gs=u.find(C('selectionEntryGroups'))
    if gs is None: continue
    for g in gs:
        if (g.get('name') or '').strip()!='Legion Wargear & Upgrades': continue
        hits=[]
        for cont_name in ('selectionEntries','entryLinks'):
            cont=g.find(C(cont_name))
            if cont is None: continue
            for x in cont:
                if 'chainaxe' in (x.get('name') or '').lower(): hits.append(x)
        if hits:
            lines += ['',f'=== CHAINAXE UNIT {u.get("id")} | {u.get("name")} | pts={cost(u)} ===']
            ims=immediate_models(u)
            for m in ims:
                lines.append(f'MODEL id={m.get("id")} name={m.get("name")} pts={cost(m)} constraints={constraints(m)}')
            for x in hits:
                lines.append(f'CHAIN id={x.get("id")} name={x.get("name")} tag={x.tag.split("}")[-1]} target={x.get("targetId")} pts={cost(x)} constraints={constraints(x)}')

OUT.write_text('\n'.join(lines),encoding='utf-8')
print('\n'.join(lines))
