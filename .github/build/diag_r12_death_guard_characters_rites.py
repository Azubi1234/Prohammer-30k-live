from pathlib import Path
import xml.etree.ElementTree as ET
CAT=Path('Legiones Astartes.cat'); OUT=Path('inspection-r12-death-guard-characters-rites.txt')
NS='http://www.battlescribe.net/schema/catalogueSchema'; C=lambda t:f'{{{NS}}}{t}'
root=ET.parse(CAT).getroot(); lines=[f'CAT revision={root.get("revision")} GSTref={root.get("gameSystemRevision")}']

wanted_ids=['r25-rite-xiv-0-the-reaping','r25-rite-xiv-1-creeping-death','r41-unit-xiv-3-calas-typhon-first-captain','r41-unit-xiv-4-crysos-morturg','r41-unit-xiv-5-durak-rask','r41-unit-xiv-6-ignatius-grulgor','r41-unit-xiv-7-nathaniel-garro','r41-unit-xiv-8-xiv-mortarion-the-reaper','r41-unit-xiv-9-mortarion-prince-of-decay']

def cost(e):
    c=e.find(C('costs'))
    if c is not None:
        for x in c:
            if x.get('typeId')=='pts': return x.get('value')
    return ''
def cons(e):
    c=e.find(C('constraints')); out=[]
    if c is not None:
        for x in c: out.append(f'{x.get("type")}={x.get("value")} field={x.get("field")} scope={x.get("scope")} id={x.get("id")}')
    return '; '.join(out)
def rules(e):
    r=e.find(C('rules')); out=[]
    if r is not None:
        for x in r: out.append(f'{x.get("id")} | {x.get("name")} | hidden={x.get("hidden")} | {(x.findtext(C("description")) or "")[:400]}')
    return out

def profiles(e):
    p=e.find(C('profiles')); out=[]
    if p is not None:
        for x in p:
            chars=[]; cc=x.find(C('characteristics'))
            if cc is not None:
                for y in cc: chars.append(f'{y.get("name")}={y.text}')
            out.append(f'{x.get("id")} | {x.get("name")} | {x.get("typeName")} | '+', '.join(chars))
    return out

def walk_shallow(e,depth=0,maxd=3):
    if depth>maxd:return
    for cn in ('selectionEntryGroups','selectionEntries','entryLinks'):
        cont=e.find(C(cn))
        if cont is None: continue
        for x in cont:
            lines.append('  '*depth+f'{x.tag.split("}")[-1]} {x.get("id")} | {x.get("name")} | type={x.get("type")} target={x.get("targetId")} hidden={x.get("hidden")} pts={cost(x)} cons={cons(x)}')
            for rr in rules(x): lines.append('  '*(depth+1)+'RULE '+rr)
            for pp in profiles(x): lines.append('  '*(depth+1)+'PROFILE '+pp)
            walk_shallow(x,depth+1,maxd)

for wid in wanted_ids:
    e=next((x for x in root.iter() if x.get('id')==wid),None)
    lines += ['',f'=== {wid} ===']
    if e is None: lines.append('MISSING'); continue
    lines.append(f'{e.tag.split("}")[-1]} {e.get("name")} type={e.get("type")} hidden={e.get("hidden")} pts={cost(e)} cons={cons(e)}')
    for rr in rules(e): lines.append('RULE '+rr)
    for pp in profiles(e): lines.append('PROFILE '+pp)
    mods=e.find(C('modifiers'))
    if mods is not None: lines.append('MODIFIERS '+ET.tostring(mods,encoding='unicode')[:6000])
    walk_shallow(e)

names=['Manreaper','Alchem Flamer','Combi-Alchem Flamer','Power weapon','Thunder hammer','Volkite Serpenta','Nuncio Vox','Phosphex Bomb','Libertas','Aquila Imperator','Bolt pistol','Bolter','Rad grenades','Frag grenades','Artificer Armour','Power Armour','Cataphractii Terminator Armour','Refractor Field','Silence','Lantern','Barbaran Plate']
lines += ['','=== MATCHING REUSABLE ELEMENTS ===']
for name in names:
    lines.append(f'-- {name} --'); n=0
    for x in root.iter():
        if (x.get('name') or '').strip().lower()==name.lower():
            lines.append(f'{x.tag.split("}")[-1]} {x.get("id")} type={x.get("type")} target={x.get("targetId")} hidden={x.get("hidden")} pts={cost(x)}')
            for pp in profiles(x): lines.append('  PROFILE '+pp)
            for rr in rules(x): lines.append('  RULE '+rr)
            n+=1
            if n>=12: break

OUT.write_text('\n'.join(lines),encoding='utf-8'); print('\n'.join(lines))
