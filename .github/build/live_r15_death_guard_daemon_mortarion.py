from pathlib import Path
import re
import xml.etree.ElementTree as ET

CAT=Path('Legiones Astartes.cat'); IDX=Path('index.xml'); OUT=Path('inspection-live-r15-death-guard-daemon-mortarion.txt')
NS='http://www.battlescribe.net/schema/catalogueSchema'; ET.register_namespace('',NS); C=lambda t:f'{{{NS}}}{t}'
ct=ET.parse(CAT); root=ct.getroot()
if root.get('revision')!='14': raise RuntimeError(f'Expected CAT 14, got {root.get("revision")}')

def findid(i): return next((x for x in root.iter() if x.get('id')==i),None)
def ensure(p,t):
    x=p.find(C(t))
    if x is None: x=ET.SubElement(p,C(t))
    return x
def set_rule(e,id_,name,text):
    rs=ensure(e,'rules')
    for x in list(rs):
        if x.get('id')==id_: rs.remove(x)
    r=ET.SubElement(rs,C('rule'),{'id':id_,'name':name,'hidden':'false'})
    ET.SubElement(r,C('description')).text=text
    return r
def hide_source(e):
    rs=e.find(C('rules'))
    n=0
    if rs is not None:
        for r in rs:
            if (r.get('name') or '')=='Source Entry' and r.get('hidden')!='true':
                r.set('hidden','true'); n+=1
    return n
def setmax(e,val,id_):
    cs=ensure(e,'constraints')
    for x in list(cs):
        if x.get('id')==id_: cs.remove(x)
    ET.SubElement(cs,C('constraint'),{'id':id_,'type':'max','value':str(val),'field':'selections','scope':'parent','shared':'true','includeChildSelections':'true','includeChildForces':'false'})
def add_ranged_profile(e,id_,name,rng,s,ap,typ):
    ps=ensure(e,'profiles')
    for p in list(ps):
        if p.get('id')==id_: ps.remove(p)
    p=ET.SubElement(ps,C('profile'),{'id':id_,'name':name,'hidden':'false','typeId':'prof-ranged','typeName':'Ranged Weapon'})
    ch=ET.SubElement(p,C('characteristics'))
    for cid,n,v in [('ranged-range','Range',rng),('ranged-s','S',s),('ranged-ap','AP',ap),('ranged-type','Type',typ)]:
        q=ET.SubElement(ch,C('characteristic'),{'name':n,'typeId':cid}); q.text=v

def direct_or_desc_member_models(unit):
    # Count model selections belonging to the squad, but never models inside transport groups.
    parent={c:p for p in unit.iter() for c in p}
    out=[]
    for m in unit.iter(C('selectionEntry')):
        if m is unit or m.get('type')!='model': continue
        cur=m; blocked=False
        while cur is not unit:
            cur=parent.get(cur)
            if cur is None: break
            nm=(cur.get('name') or '').lower()
            if 'dedicated transport' in nm or 'transport choice' in nm:
                blocked=True; break
        if not blocked: out.append(m)
    # entryLinks to shared model selections are not used for ordinary squad member counts in this catalogue.
    return out

def add_scaled_cost(e,per,models,prefix):
    costs=ensure(e,'costs')
    # reset direct Points cost to 0
    pt=next((x for x in costs if x.get('typeId')=='pts'),None)
    if pt is None: pt=ET.SubElement(costs,C('cost'),{'name':'Points','typeId':'pts','value':'0'})
    else: pt.set('value','0')
    ms=ensure(e,'modifiers')
    # clear previous modifiers with our prefix
    for x in list(ms):
        if (x.get('id') or '').startswith(prefix): ms.remove(x)
    for i,m in enumerate(models):
        mod=ET.SubElement(ms,C('modifier'),{'id':f'{prefix}-{i}','type':'increment','field':'pts','value':str(per)})
        reps=ET.SubElement(mod,C('repeats'))
        ET.SubElement(reps,C('repeat'),{'field':'selections','scope':'root-entry','value':'1','percentValue':'false','shared':'true','includeChildSelections':'true','includeChildForces':'false','childId':m.get('id'),'repeats':'1','roundUp':'false'})

def hide_unless_roster_selection(e,child_id,id_):
    ms=ensure(e,'modifiers')
    for x in list(ms):
        if x.get('id')==id_: ms.remove(x)
    m=ET.SubElement(ms,C('modifier'),{'id':id_,'type':'set','field':'hidden','value':'true'})
    cs=ET.SubElement(m,C('conditions'))
    ET.SubElement(cs,C('condition'),{'type':'lessThan','value':'1','field':'selections','scope':'roster','childId':child_id,'shared':'true','includeChildSelections':'true','includeChildForces':'true'})

def source_text(e):
    rs=e.find(C('rules'))
    if rs is None:return ''
    for r in rs:
        if (r.get('name') or '')=='Source Entry':
            d=r.find(C('description')); return (d.text or '') if d is not None else ''
    return ''
def base_wargear_text(e):
    txt=source_text(e)
    if txt:
        m=re.search(r'Wargear:\s*(.*?)(?:Special Rules:|OPTIONS|DEDICATED TRANSPORT|$)',txt,re.S|re.I)
        if m:return m.group(1)
    rs=e.find(C('rules'))
    if rs is not None:
        for r in rs:
            if (r.get('name') or '').lower() in ('wargear','standard wargear'):
                d=r.find(C('description')); return (d.text or '') if d is not None else ''
    return ''
def is_infantry(e):
    txt=source_text(e)
    if txt:
        m=re.search(r'Unit Type:\s*(.*?)(?:Wargear:|Special Rules:|OPTIONS|$)',txt,re.S|re.I)
        if m:return 'infantry' in m.group(1).lower()
    # fallback for core infantry squads lacking a Source Entry type block
    nm=(e.get('name') or '').lower()
    bad=('dreadnought','land raider','rhino','predator','sicaran','spartan','drop pod','dreadclaw','speeder','jetbike','bike','flyer','tank')
    return not any(b in nm for b in bad)

def eligible_plague_unit(e):
    if e.get('type')!='unit': return False
    if not direct_or_desc_member_models(e): return False
    if not is_infantry(e): return False
    wg=base_wargear_text(e).lower()
    if 'terminator armour' in wg or 'cataphractii' in wg or 'tartaros' in wg: return False
    return ('power armour' in wg or 'artificer armour' in wg)

log=[]
daemon_id='r41-unit-xiv-9-mortarion-prince-of-decay'; daemon=findid(daemon_id)
if daemon is None: raise RuntimeError('Daemon Mortarion missing')

# 1) Daemon Mortarion becomes a proper readable entry.
hide_source(daemon)
# remove earlier R15 rules if rerun
for rid,name,text in [
 ('r15-dg-dm-wargear','Wargear','Silence; Lantern; Daemonic Barbaran Plate.'),
 ('r15-dg-dm-special','Special Rules','Daemon; Fear; Fearless; Eternal Warrior; Feel No Pain (5+); Poison Resistance; Adamantium Will; Master of the Legion; Psyker (Mastery Level 2).'),
 ('r15-dg-dm-restrict','Restrictions','Mortarion, Prince of Decay may only be selected for a Death Guard army. An army may not include both Mortarion, Prince of Decay and Mortarion in his mortal form.'),
 ('r15-dg-dm-wings','Burdened Wings','Mortarion may move over intervening models and terrain as though using a Jump Pack, but may never move more than 9 inches during the Movement phase. Mortarion may never join another unit and no model may join him.'),
 ('r15-dg-dm-silence','Silence','Silence is a Two-Handed, Master-crafted Power Weapon which grants Mortarion +2 Strength. Instead of making his normal close-combat attacks, Mortarion may make one attack against every enemy model in base contact with him.'),
 ('r15-dg-dm-miasma','The Reaper’s Miasma','At the beginning of each enemy turn, every enemy unit within 18 inches of Mortarion suffers: within 6 inches, D3 S5 AP4 hits, Poisoned (3+); 6–12 inches, D3 S4 AP4 hits, Poisoned (3+); 12–18 inches, 1 S4 AP4 hit, Poisoned (3+). Death Guard models and Daemons of Nurgle are immune.'),
 ('r15-dg-dm-sorcerer','Reluctant Sorcerer','Mortarion is a Mastery Level 2 Psyker, but always takes Psychic Tests using Leadership 8, regardless of his normal Leadership or modifiers which would increase it. He knows Miasma of Pestilence, Curse of Decay and Nurgle’s Rot.'),
 ('r15-dg-dm-p1','Miasma of Pestilence','Beginning of the enemy Assault phase; Range 12 inches. Choose one enemy unit within range and take a Psychic Test. If successful, the unit suffers -1 Initiative and -1 Attack, to a minimum of 1, until the end of the Assault phase.'),
 ('r15-dg-dm-p2','Curse of Decay','Mortarion’s Shooting phase; Range 18 inches. Choose one enemy unit within range and take a Psychic Test. If successful, the unit treats all terrain, including open ground, as Difficult Terrain until the beginning of Mortarion’s next turn.'),
 ('r15-dg-dm-p3','Nurgle’s Rot','Mortarion’s Shooting phase; Range 12 inches. Choose one enemy unit within range and take a Psychic Test. If successful, the target suffers D6 Strength 4 AP4 hits with Poisoned (3+).'),
 ('r15-dg-dm-sons','Sons of the Plague Father','While Mortarion, Prince of Decay is included, eligible Death Guard Infantry units composed entirely of models in Power Armour or Artificer Armour may buy the Plague Marines upgrade for +7 points per model. Upgraded models gain +1 Toughness, Feel No Pain (5+) and Slow and Purposeful. They may not benefit from Move Through Cover, their normal maximum charge distance is 5 inches, and they may not benefit from rules that increase Movement or charge distance. The Relentless component of Slow and Purposeful applies normally.')]:
    set_rule(daemon,rid,name,text)
add_ranged_profile(daemon,'r15-dg-dm-lantern','Lantern','18"','8','2','Assault 1, Master-crafted')
add_ranged_profile(daemon,'r15-dg-dm-nurgles-rot','Nurgle’s Rot','12"','4','4','Psychic; D6 hits, Poisoned (3+)')
log.append('Daemon Mortarion Source Entry hidden and replaced with discrete wargear, restriction, unique-rule and psychic-power entries plus Lantern/Nurgle’s Rot profiles')

# 2) Remove remaining visible Death Guard copy-paste Source Entry walls and give the known retinue clones concise proper rules.
hidden_sources=0
for e in root.iter():
    i=(e.get('id') or '').lower()
    if 'xiv' in i or 'dg' in i:
        hidden_sources += hide_source(e)
# Specific old retinue clones that previously depended on their Source Entry walls.
for e in root.iter(C('selectionEntry')):
    i=e.get('id') or ''
    nm=(e.get('name') or '').strip().upper()
    if 'live-r2-r41-unit-xiv-3-calas-typhon' in i and nm=='DEATHSHROUD TERMINATORS':
        set_rule(e,'r15-dg-typhon-ret-ds-silent','Silent Retinue','Selected as Typhon’s retinue; this unit occupies no separate Force Organisation slot.')
        set_rule(e,'r15-dg-typhon-ret-ds-wargear','Wargear','Terminator Armour; Manreaper; Alchem Flamer.')
    if 'live-r2-r41-unit-xiv-4-crysos-morturg' in i and nm=='MORTUS POISONER SQUAD':
        set_rule(e,'r15-dg-morturg-ret-mp-destroyer','Destroyer Cadre','The Mortus Poisoners use the normal Destroyer Cadre rule from the Legiones Astartes Army List.')
        set_rule(e,'r15-dg-morturg-ret-mp-wargear','Wargear','Power Armour; Alchem Flamer; Bolt pistol; Chainsword; Frag grenades; Rad grenades.')
log.append(f'Hidden {hidden_sources} remaining visible Death Guard Source Entry wall(s), including old retinue clones')

# 3) Sons of the Plague Father becomes a real per-unit roster upgrade.
# Add a local selector to every squad whose source explicitly says Infantry and whose BASE wargear is entirely Power/Artificer armour.
plague_units=[]
for e in list(root.iter(C('selectionEntry'))):
    if not eligible_plague_unit(e): continue
    # avoid adding inside Daemon Mortarion itself or an already-generated plague selector
    if (e.get('id') or '').startswith('r15-dg-plague-'): continue
    gs=ensure(e,'selectionEntryGroups')
    gid='r15-dg-plague-group-'+(e.get('id') or 'unit')
    # ids can be long but remain deterministic; remove old group if any
    for g in list(gs):
        if g.get('id')==gid: gs.remove(g)
    g=ET.SubElement(gs,C('selectionEntryGroup'),{'id':gid,'name':'Sons of the Plague Father','hidden':'false'})
    se=ET.SubElement(g,C('selectionEntries'))
    uid='r15-dg-plague-'+(e.get('id') or 'unit')
    up=ET.SubElement(se,C('selectionEntry'),{'id':uid,'name':'Upgrade unit to Plague Marines (+7 pts/model)','type':'upgrade','hidden':'false','import':'true'})
    setmax(up,1,uid+'-max')
    hide_unless_roster_selection(up,daemon_id,uid+'-gate')
    models=direct_or_desc_member_models(e)
    add_scaled_cost(up,7,models,uid+'-cost')
    set_rule(up,uid+'-rule','Plague Marines','Every model in this unit is upgraded for +7 points per model. Models gain +1 Toughness, Feel No Pain (5+) and Slow and Purposeful. They may not benefit from Move Through Cover, their normal maximum charge distance is 5 inches, and they may not benefit from rules that increase their Movement or charge distance. The Relentless component of Slow and Purposeful applies normally.')
    plague_units.append((e.get('id') or '',e.get('name') or '',len(models)))
log.append('Sons of the Plague Father now exposes an automatically scaling +7/model Plague Marines selector only while Daemon Mortarion is in the roster')
log.append('Eligible squad entries patched: '+str(len(plague_units)))
for i,n,c in plague_units: log.append(f'  + {i} | {n} | counted member model entries={c}')

root.set('revision','15'); ct.write(CAT,encoding='utf-8',xml_declaration=True)
idx=IDX.read_text(encoding='utf-8'); idx=re.sub(r'(filePath="Legiones Astartes\.cat"[^>]*dataRevision=")\d+("\s*/>)',r'\g<1>15\2',idx); IDX.write_text(idx,encoding='utf-8')
OUT.write_text('LIVE R15 — DEATH GUARD DAEMON MORTARION + PLAGUE MARINES\nCAT=15 GSTref='+str(root.get('gameSystemRevision'))+'\n\n'+'\n'.join('• '+x for x in log),encoding='utf-8')
print(OUT.read_text(encoding='utf-8'))