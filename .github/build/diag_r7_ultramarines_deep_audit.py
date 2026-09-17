from pathlib import Path
import xml.etree.ElementTree as ET
CAT=Path('Legiones Astartes.cat'); OUT=Path('inspection-r7-ultramarines-deep-audit.txt')
NS='http://www.battlescribe.net/schema/catalogueSchema'; C=lambda t:f'{{{NS}}}{t}'
root=ET.parse(CAT).getroot()

def pts(e):
    cs=e.find(C('costs'))
    if cs is not None:
        for x in cs:
            if x.get('typeId')=='pts': return x.get('value')
    return ''
def cons(e):
    cs=e.find(C('constraints')); out=[]
    if cs is not None:
        for x in cs: out.append(f"{x.get('type')}={x.get('value')} scope={x.get('scope')} child={x.get('childId')} field={x.get('field')}")
    return '; '.join(out)
def cats(e):
    c=e.find(C('categoryLinks')); return ', '.join(f"{x.get('name')}->{x.get('targetId')} primary={x.get('primary')}" for x in list(c or []))
def mods(e):
    m=e.find(C('modifiers')); return ET.tostring(m,encoding='unicode') if m is not None else ''
def groups(e):
    gs=e.find(C('selectionEntryGroups'))
    if gs is None:return []
    return list(gs)
def kids(g):
    out=[]
    for cn in ('selectionEntries','entryLinks'):
        c=g.find(C(cn))
        if c is not None: out += list(c)
    return out

def dump_entry(e,deep=True):
    lines=[f"ENTRY {e.get('id')} | {e.get('name')} | type={e.get('type')} hidden={e.get('hidden')} pts={pts(e)} cons={cons(e)} cats={cats(e)}"]
    if mods(e): lines.append(' MODS '+mods(e))
    for g in groups(e):
        lines.append(f" GROUP {g.get('id')} | {g.get('name')} | cons={cons(g)}")
        if mods(g): lines.append('  GMODS '+mods(g))
        for x in kids(g):
            lines.append(f"   OPT {x.get('id')} | {x.get('name')} | tag={x.tag.split('}')[-1]} type={x.get('type')} target={x.get('targetId')} pts={pts(x)} cons={cons(x)} hidden={x.get('hidden')}")
            if mods(x): lines.append('    MODS '+mods(x))
            if deep and x.get('type')=='unit':
                for gg in groups(x): lines.append(f"     SUBGROUP {gg.get('id')} | {gg.get('name')} | cons={cons(gg)}")
    return lines

lines=[f"CAT={root.get('revision')} GST={root.get('gameSystemRevision')}"]
for uid in [
'r41-unit-xiii-0-invictarus-suzerain-squad','r41-unit-xiii-1-fulmentarus-terminator-squad','r41-unit-xiii-2-locutarus-storm-squad','r41-unit-xiii-3-nemesis-destroyer-squad',
'r41-unit-xiii-4-marius-gage-first-master','r41-unit-xiii-5-remus-ventanus','r41-unit-xiii-6-aeonid-thiel','r41-unit-xiii-7-honoured-telemechrus','r41-unit-xiii-8-titus-prayto','r41-unit-xiii-9-xiii-roboute-guilliman-the-avenging-son',
'hq-praetor','hq-centurion-ret-command','hq-praetor-ret-termcommand','hq-praetor-ret-honour','tactical-unit','veteran-unit']:
    e=next((x for x in root.iter() if x.get('id')==uid),None)
    lines += ['',f'=== {uid} ===']
    if e is None: lines.append('MISSING')
    else: lines += dump_entry(e)

# locate armoury-ish reusable groups/entries
lines += ['','=== ARMOURY-LIKE GROUPS ===']
for e in root.iter(C('selectionEntryGroup')):
    n=(e.get('name') or '').lower(); eid=e.get('id') or ''
    if any(k in n for k in ('armoury','sergeant','terminator weapons','wargear')) and ('r41-unit-xiii' not in eid):
        if any(k in n for k in ('armoury','sergeant armoury','terminator weapons')):
            lines.append(f"{eid} | {e.get('name')} | cons={cons(e)}")

OUT.write_text('\n'.join(lines),encoding='utf-8')
print('\n'.join(lines))
