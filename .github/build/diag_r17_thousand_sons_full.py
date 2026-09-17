from pathlib import Path
import xml.etree.ElementTree as ET

CAT=Path('Legiones Astartes.cat'); GST=Path('Prohammer 30k.gst'); OUT=Path('inspection-r17-thousand-sons-full.txt')
NS='http://www.battlescribe.net/schema/catalogueSchema'; GNS='http://www.battlescribe.net/schema/gameSystemSchema'
C=lambda t:f'{{{NS}}}{t}'; G=lambda t:f'{{{GNS}}}{t}'
ct=ET.parse(CAT); root=ct.getroot(); gt=ET.parse(GST); groot=gt.getroot()

def txt(e):
    return ' '.join((e.text or '').split()) if e is not None else ''
def costs(e):
    out=[]
    cs=e.find(C('costs'))
    if cs is not None:
        for c in cs: out.append((c.get('name'),c.get('value')))
    return out

def cons(e):
    out=[]
    cs=e.find(C('constraints'))
    if cs is not None:
        for c in cs: out.append(f"{c.get('type')}={c.get('value')} field={c.get('field')} scope={c.get('scope')} id={c.get('id')}")
    return '; '.join(out)

def dump(e,depth=0,maxdepth=4):
    ind='  '*depth
    lines=[]
    tag=e.tag.rsplit('}',1)[-1]
    lines.append(f"{ind}{tag} {e.get('id')} | {e.get('name')} | type={e.get('type')} hidden={e.get('hidden')} pts={costs(e)} cons={cons(e)}")
    rs=e.find(C('rules'))
    if rs is not None:
        for r in rs:
            d=r.find(C('description'))
            lines.append(f"{ind}  RULE {r.get('id')} | {r.get('name')} | hidden={r.get('hidden')} | {txt(d)[:1400]}")
    ps=e.find(C('profiles'))
    if ps is not None:
        for p in ps:
            chars=[]; ch=p.find(C('characteristics'))
            if ch is not None:
                for x in ch: chars.append(f"{x.get('name')}={txt(x)}")
            lines.append(f"{ind}  PROFILE {p.get('id')} | {p.get('name')} | {'; '.join(chars)}")
    for key in ('modifiers','categoryLinks','entryLinks','selectionEntryGroups','selectionEntries'):
        cont=e.find(C(key))
        if cont is None: continue
        for ch in cont:
            ctag=ch.tag.rsplit('}',1)[-1]
            if ctag in ('selectionEntry','selectionEntryGroup') and depth<maxdepth:
                lines.extend(dump(ch,depth+1,maxdepth))
            else:
                lines.append(f"{ind}  {ctag} {ch.get('id')} | {ch.get('name')} target={ch.get('targetId')} hidden={ch.get('hidden')} pts={costs(ch)} cons={cons(ch)} xml={ET.tostring(ch,encoding='unicode')[:1200]}")
    return lines

lines=[f"CAT={root.get('revision')} GSTref={root.get('gameSystemRevision')}"]

# root XV Legion entries and rites
wanted=[]
for e in root.iter():
    tag=e.tag.rsplit('}',1)[-1]
    if tag not in ('selectionEntry','selectionEntryGroup','entryLink'): continue
    i=(e.get('id') or '').lower(); n=(e.get('name') or '').lower()
    if ('r41-unit-xv-' in i or 'r25-rite-xv-' in i or i=='legion-xv' or 'thousand sons' in n or 'sek hmet' in n):
        wanted.append(e)
# avoid nested duplicate flood: only dump matches whose ancestors not available in ET; dedupe ids and prioritize root-ish IDs
seen=set()
for e in wanted:
    if e.get('id') in seen: continue
    seen.add(e.get('id'))
    lines.append('\n=== XV ENTRY ==='); lines.extend(dump(e,0,3))

# Generic/core entries carrying Thousand Sons/XV links, upgrades or rules
for name_id in ['hq-praetor','hq-centurion','tactical-unit','veteran-unit','terminator-unit','assault-unit','breacher-unit','recon-unit','destroyer-unit','fa-seeker','hs-heavy-support-squad']:
    found=None
    for e in root.iter(C('selectionEntry')):
        if e.get('id')==name_id: found=e; break
    if found is not None:
        s=ET.tostring(found,encoding='unicode')
        if 'legion-xv' in s or 'Thousand Sons' in s or 'r25-rite-xv' in s or 'Brotherhood' in s or 'Prosperine' in s:
            lines.append(f'\n=== CORE {name_id} ==='); lines.extend(dump(found,0,4))

# Shared entries/rules mentioning key TS concepts
terms=['Prosperine','Brotherhood of Psykers','Arcane Litanies','Asphyx','Aether','Æther','Corvidae','Raptora','Pavoni','Pyrae','Athanae','Teleportation Transponders']
for e in root.iter(C('selectionEntry')):
    blob=ET.tostring(e,encoding='unicode')
    if any(t in blob for t in terms):
        if e.get('id') not in seen:
            lines.append('\n=== TS RELATED ==='); lines.extend(dump(e,0,2)); seen.add(e.get('id'))

# GST force chart modifiers relevant to XV
lines.append('\n=== GST XV FORCE CHART ===')
for fe in groot.iter(G('forceEntry')):
    blob=ET.tostring(fe,encoding='unicode')
    if 'legion-xv' in blob or 'r25-rite-xv' in blob or 'Thousand Sons' in blob:
        lines.append(ET.tostring(fe,encoding='unicode')[:20000])

OUT.write_text('\n'.join(lines),encoding='utf-8')
print(f'wrote {OUT} with {len(lines)} lines')
