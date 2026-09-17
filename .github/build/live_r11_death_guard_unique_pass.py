from pathlib import Path
from copy import deepcopy
import re
import xml.etree.ElementTree as ET

CAT=Path('Legiones Astartes.cat'); IDX=Path('index.xml'); OUT=Path('inspection-live-r11-death-guard-unique-pass.txt')
NS='http://www.battlescribe.net/schema/catalogueSchema'; ET.register_namespace('',NS); C=lambda t:f'{{{NS}}}{t}'
ct=ET.parse(CAT); root=ct.getroot()
if root.get('revision')!='10': raise RuntimeError(f'Expected CAT 10, got {root.get("revision")}')

def findid(i): return next((x for x in root.iter() if x.get('id')==i),None)
def ensure(p,t):
    x=p.find(C(t))
    if x is None: x=ET.SubElement(p,C(t))
    return x

def groups(e): return list(e.find(C('selectionEntryGroups')) or [])
def group_by_name(e,name): return next((x for x in groups(e) if (x.get('name') or '')==name),None)
def group_items(g):
    out=[]
    for cn in ('selectionEntries','entryLinks'):
        c=g.find(C(cn))
        if c is not None: out += list(c)
    return out

def set_rule(e,id_,name,text):
    rs=ensure(e,'rules')
    for x in list(rs):
        if x.get('id')==id_: rs.remove(x)
    r=ET.SubElement(rs,C('rule'),{'id':id_,'name':name,'hidden':'false'}); ET.SubElement(r,C('description')).text=text

def hide_source_entry(e):
    rs=e.find(C('rules'))
    if rs is not None:
        for r in rs:
            if (r.get('name') or '')=='Source Entry': r.set('hidden','true')

def set_max(e,val,id_,scope='parent'):
    cs=ensure(e,'constraints')
    for x in list(cs):
        if x.get('id')==id_: cs.remove(x)
    ET.SubElement(cs,C('constraint'),{'id':id_,'type':'max','value':str(val),'field':'selections','scope':scope,'shared':'true','includeChildSelections':'true','includeChildForces':'false'})

def set_min_points(e,val,id_):
    cs=ensure(e,'constraints')
    for x in list(cs):
        if x.get('id')==id_: cs.remove(x)
    ET.SubElement(cs,C('constraint'),{'id':id_,'type':'min','value':str(val),'field':'limit::points','scope':'roster','shared':'true','includeChildSelections':'true','includeChildForces':'true','percentValue':'false'})

def hide_unless(e,child,id_,scope='roster'):
    ms=ensure(e,'modifiers');
    for x in list(ms):
        if x.get('id')==id_: ms.remove(x)
    m=ET.SubElement(ms,C('modifier'),{'id':id_,'type':'set','field':'hidden','value':'true'}); cs=ET.SubElement(m,C('conditions'))
    ET.SubElement(cs,C('condition'),{'type':'lessThan','value':'1','field':'selections','scope':scope,'childId':child,'shared':'true','includeChildSelections':'true','includeChildForces':'false'})

def hide_if(e,child,id_,scope='roster'):
    ms=ensure(e,'modifiers');
    for x in list(ms):
        if x.get('id')==id_: ms.remove(x)
    m=ET.SubElement(ms,C('modifier'),{'id':id_,'type':'set','field':'hidden','value':'true'}); cs=ET.SubElement(m,C('conditions'))
    ET.SubElement(cs,C('condition'),{'type':'atLeast','value':'1','field':'selections','scope':scope,'childId':child,'shared':'true','includeChildSelections':'true','includeChildForces':'false'})

def hide_unless_any(e,children,id_,scope='root-entry'):
    ms=ensure(e,'modifiers');
    for x in list(ms):
        if x.get('id')==id_: ms.remove(x)
    m=ET.SubElement(ms,C('modifier'),{'id':id_,'type':'set','field':'hidden','value':'true'})
    cgs=ET.SubElement(m,C('conditionGroups')); cg=ET.SubElement(cgs,C('conditionGroup'),{'type':'and'}); cs=ET.SubElement(cg,C('conditions'))
    for child in children:
        ET.SubElement(cs,C('condition'),{'type':'lessThan','value':'1','field':'selections','scope':scope,'childId':child,'shared':'true','includeChildSelections':'true','includeChildForces':'false'})

def clone_prefix(src,prefix):
    cl=deepcopy(src); mp={}
    for x in cl.iter():
        if x.get('id'): mp[x.get('id')]=prefix+x.get('id')
    for x in cl.iter():
        if x.get('id') in mp: x.set('id',mp[x.get('id')])
        if x.get('childId') in mp: x.set('childId',mp[x.get('childId')])
        if x.get('field') in mp: x.set('field',mp[x.get('field')])
    return cl

def strip_categories(e):
    c=e.find(C('categoryLinks'))
    if c is not None: e.remove(c)

def strip_roster_constraints(e):
    for x in e.iter():
        cs=x.find(C('constraints'))
        if cs is not None:
            for q in list(cs):
                if q.get('scope')=='roster': cs.remove(q)

def retinue_clone(group,src,prefix,label=None):
    se=ensure(group,'selectionEntries')
    for x in list(se):
        if (x.get('id') or '').startswith(prefix): se.remove(x)
    cl=clone_prefix(src,prefix); strip_categories(cl); strip_roster_constraints(cl); cl.set('hidden','false')
    if label: cl.set('name',label)
    set_max(cl,1,prefix+'max')
    set_rule(cl,prefix+'rule','Retinue','Selected as this character’s retinue. It occupies no separate Force Organisation slot.')
    se.append(cl); return cl

def clean_armoury(template_id,prefix,base_prefix,name):
    src=findid(template_id)
    if src is None: raise RuntimeError('Missing armoury '+template_id)
    cl=deepcopy(src)
    for cn in ('selectionEntries','entryLinks'):
        c=cl.find(C(cn))
        if c is not None:
            for x in list(c):
                if not (x.get('id') or '').startswith(base_prefix): c.remove(x)
    cl=clone_prefix(cl,prefix); cl.set('name',name); return cl

def add_armoury(host,template_id,prefix,base_prefix,name):
    gs=ensure(host,'selectionEntryGroups'); cl=clean_armoury(template_id,prefix,base_prefix,name)
    for x in list(gs):
        if x.get('id')==cl.get('id'): gs.remove(x)
    gs.append(cl); return cl

def transport_group(unit_id):
    u=findid(unit_id)
    return next((g for g in groups(u) if 'Dedicated Transport' in (g.get('name') or '')),None) if u is not None else None

def add_transport(host,template_unit,prefix,allowed):
    src=transport_group(template_unit)
    if src is None: raise RuntimeError('Missing transport template '+template_unit)
    cl=clone_prefix(src,prefix); cl.set('name','Dedicated Transport')
    for cn in ('selectionEntries','entryLinks'):
        c=cl.find(C(cn))
        if c is not None:
            for x in list(c):
                n=(x.get('name') or '').lower()
                if not any(a.lower() in n for a in allowed): c.remove(x)
    gs=ensure(host,'selectionEntryGroups')
    for x in list(gs):
        if x.get('id')==cl.get('id'): gs.remove(x)
    gs.append(cl); return cl

def set_scaled(e,per,model_id,prefix):
    costs=ensure(e,'costs'); p=next((x for x in costs if x.get('typeId')=='pts'),None)
    if p is None: p=ET.SubElement(costs,C('cost'),{'name':'Points','typeId':'pts','value':'0'})
    p.set('value','0')
    ms=ensure(e,'modifiers')
    for x in list(ms):
        if (x.get('id') or '').startswith(prefix): ms.remove(x)
    m=ET.SubElement(ms,C('modifier'),{'id':prefix+'-scale','type':'increment','field':'pts','value':str(per)})
    reps=ET.SubElement(m,C('repeats'))
    ET.SubElement(reps,C('repeat'),{'field':'selections','scope':'root-entry','value':'1','percentValue':'false','shared':'true','includeChildSelections':'true','includeChildForces':'false','childId':model_id,'repeats':'1','roundUp':'false'})

def move_to_group(parent,names,gid,gname,maxv):
    se=parent.find(C('selectionEntries')); moved=[]
    if se is not None:
        for x in list(se):
            if (x.get('name') or '').lower() in [n.lower() for n in names]: se.remove(x); moved.append(x)
    sgs=ensure(parent,'selectionEntryGroups')
    for x in list(sgs):
        if x.get('id')==gid: sgs.remove(x)
    g=ET.SubElement(sgs,C('selectionEntryGroup'),{'id':gid,'name':gname,'hidden':'false'}); set_max(g,maxv,gid+'-max')
    dst=ET.SubElement(g,C('selectionEntries'))
    for x in moved: dst.append(x)
    return g,moved

log=[]
DS=findid('r41-unit-xiv-0-deathshroud-terminators'); GW=findid('r41-unit-xiv-1-grave-warden-terminator-squad'); MP=findid('r41-unit-xiv-2-mortus-poisoner-squad')
if not all((DS,GW,MP)): raise RuntimeError('Missing Death Guard unique squads')

# Deathshroud: actual whole-squad options and transports.
dsg=group_by_name(DS,'Options'); dsmodels='r41-unit-xiv-0-deathshroud-terminators-additional'
mb=next((x for x in group_items(dsg) if 'melta bombs' in (x.get('name') or '').lower()),None)
if mb is not None:
    mb.set('name','Melta bombs — entire squad (+5 pts/model)'); set_scaled(mb,5,dsmodels,'r11-dg-ds-melta'); set_rule(mb,'r11-dg-ds-melta-rule','Whole-squad Melta Bombs','Every Deathshroud Terminator takes Melta Bombs for +5 points per model. The cost scales with the selected squad size.')
se=ensure(dsg,'selectionEntries')
catid='r11-dg-deathshroud-cataphractii'
for x in list(se):
    if x.get('id')==catid: se.remove(x)
cat=ET.SubElement(se,C('selectionEntry'),{'id':catid,'name':'Exchange entire squad’s Terminator Armour for Cataphractii Terminator Armour — Free','type':'upgrade','hidden':'false','import':'true'}); set_max(cat,1,catid+'-max')
set_rule(cat,catid+'-rule','Cataphractii Armour Exchange','The entire squad exchanges its Terminator Armour for Cataphractii Terminator Armour at no additional cost. The squad instead has a 2+/4+ Save and follows all normal Cataphractii Terminator Armour rules and restrictions.')
add_transport(DS,'terminator-unit','r11-dg-ds-dt-',['Land Raider','Dreadclaw','Spartan'])
hide_source_entry(DS); set_rule(DS,'r11-dg-ds-silent','Silent Retinue','A Death Guard character who would normally be permitted to select a Legion Terminator Command Squad may instead select one Deathshroud Terminator Squad as his retinue. It occupies no separate Force Organisation slot.'); set_rule(DS,'r11-dg-ds-wargear','Wargear','Terminator Armour; Manreaper; Alchem Flamer.')
log.append('Deathshroud whole-squad armour/melta-bomb options and Dedicated Transports made functional')

# Grave Wardens: chainfists tied to actual model count, Chem-master armoury, transports.
gwg=group_by_name(GW,'Options'); chain=next((x for x in group_items(gwg) if (x.get('name') or '')=='Chainfist'),None)
if chain is not None:
    g,m=move_to_group(gwg,['Chainfist'],'r11-dg-gw-chain','Power Fist Replacement — up to one per model',10)
    # dynamic max equals selected model count (5-10)
    cid='r11-dg-gw-chain-max'; c=next((x for x in ensure(g,'constraints') if x.get('id')==cid),None)
    if c is not None: c.set('value','0')
    ms=ensure(g,'modifiers'); mod=ET.SubElement(ms,C('modifier'),{'id':'r11-dg-gw-chain-dyn','type':'increment','field':cid,'value':'1'}); reps=ET.SubElement(mod,C('repeats')); ET.SubElement(reps,C('repeat'),{'field':'selections','scope':'root-entry','value':'1','percentValue':'false','shared':'true','includeChildSelections':'true','includeChildForces':'false','childId':'r41-unit-xiv-1-grave-warden-terminator-squad-additional','repeats':'1','roundUp':'false'})
add_armoury(GW,'terminator-sgt-armoury','r11-dg-gw-chem-','terminator-sgt-armoury','Chem-master — Terminator Armoury (max 50 pts)')
add_transport(GW,'terminator-unit','r11-dg-gw-dt-',['Land Raider','Dreadclaw','Spartan'])
hide_source_entry(GW); set_rule(GW,'r11-dg-gw-shroud','Shrouded in Death','A Grave Warden Terminator Squad counts as being equipped with Defensive Grenades. All normal ProHammer rules for Defensive Grenades apply.'); set_rule(GW,'r11-dg-gw-wargear','Wargear','Cataphractii Terminator Armour; Assault Grenade Launcher; Death Cloud Projector; Power fist.')
log.append('Grave Warden chainfist limit, Chem-master Armoury and Dedicated Transports made functional')

# Mortus Poisoners: whole-squad costs, one-per-five phosphex, separate Poison-master options/armoury.
mpg=group_by_name(MP,'Options'); mid='r41-unit-xiv-2-mortus-poisoner-squad-additional'
for key,per in [('Krak grenades',2),('Melta bombs',5)]:
    e=next((x for x in group_items(mpg) if (x.get('name') or '').lower().startswith(key.lower())),None)
    if e is not None:
        e.set('name',f'{key} — entire squad (+{per} pts/model)'); set_scaled(e,per,mid,'r11-dg-mp-'+key.split()[0].lower()); set_rule(e,'r11-dg-mp-'+key.split()[0].lower()+'-rule','Whole-squad upgrade',f'Every model in the squad takes {key} for +{per} points per model. The cost scales with squad size.')
ph=next((x for x in group_items(mpg) if (x.get('name') or '')=='Phosphex Bomb'),None)
if ph is not None:
    g,m=move_to_group(mpg,['Phosphex Bomb'],'r11-dg-mp-line-phosphex','Mortus Poisoners — Phosphex Bombs (one per five models)',1)
    cid='r11-dg-mp-line-phosphex-max'; ms=ensure(g,'modifiers'); mod=ET.SubElement(ms,C('modifier'),{'id':'r11-dg-mp-line-phosphex-10','type':'set','field':cid,'value':'2'}); cs=ET.SubElement(mod,C('conditions')); ET.SubElement(cs,C('condition'),{'type':'atLeast','value':'10','field':'selections','scope':'root-entry','childId':mid,'shared':'true','includeChildSelections':'true','includeChildForces':'false'})
# Poison-master chainsword replacement choices are one-of.
move_to_group(mpg,['Rending Weapon','Power weapon','Power fist'],'r11-dg-mp-master-weapon','Poison-master — Chainsword Replacement',1)
# explicit Poison-master phosphex bombs, up to 3
sgs=ensure(mpg,'selectionEntryGroups'); gid='r11-dg-mp-master-phosphex'
for x in list(sgs):
    if x.get('id')==gid: sgs.remove(x)
g=ET.SubElement(sgs,C('selectionEntryGroup'),{'id':gid,'name':'Poison-master — Phosphex Bombs','hidden':'false'}); set_max(g,3,gid+'-max'); s=ET.SubElement(g,C('selectionEntries')); e=ET.SubElement(s,C('selectionEntry'),{'id':gid+'-bomb','name':'Phosphex Bomb','type':'upgrade','hidden':'false','import':'true'}); set_max(e,3,gid+'-bomb-max'); costs=ET.SubElement(e,C('costs')); ET.SubElement(costs,C('cost'),{'name':'Points','typeId':'pts','value':'10'})
add_armoury(MP,'destroyer-sgt-armoury','r11-dg-mp-master-','destroyer-sgt-armoury','Poison-master — Additional Armoury (max 50 pts)')
hide_source_entry(MP); set_rule(MP,'r11-dg-mp-destroyer','Destroyer Cadre','The Mortus Poisoners use the normal Destroyer Cadre rule from the Legiones Astartes Army List.'); set_rule(MP,'r11-dg-mp-wargear','Wargear','Power Armour; Alchem Flamer; Bolt pistol; Chainsword; Frag grenades; Rad grenades.')
log.append('Mortus Poisoner whole-squad costs, one-per-five Phosphex and Poison-master selections made functional')

# Named characters: allegiance, Typhon threshold, readable rules/retinues.
chars={
'r41-unit-xiv-3-calas-typhon-first-captain':('traitor',[('Latent Psyker','Typhon is treated as a Psyker (Mastery Level 1) solely for Aura of Pestilence and Perils of the Warp. He knows no other psychic powers and tests for Aura of Pestilence using Leadership 7.'),('Aura of Pestilence','At the beginning of either player’s Assault phase Typhon may take a Psychic Test. If passed, enemy models within 2 inches suffer -1 Attack (minimum 1) until the end of the phase. If failed, friendly models within 2 inches suffer the penalty instead. Typhon fights normally.')]),
'r41-unit-xiv-4-crysos-morturg':('loyalist',[('Psychic Powers','Morturg selects one psychic power from the normal Legion Librarian Psychic Power list and follows the normal ProHammer rules for Psykers and Mastery Level 1.'),('Master of Ambush','Morturg and one Death Guard Infantry unit he has joined before deployment may deploy using Infiltrate. He must remain joined to that unit when it deploys.'),('Destroyer Officer','Morturg may join a Legion Destroyer Squad or Mortus Poisoner Squad despite the normal restrictions imposed by Destroyer Cadre.')]),
'r41-unit-xiv-5-durak-rask':('traitor',[('Art of Destruction','Durak Rask and any Death Guard Infantry unit he has joined have Tank Hunters.')]),
'r41-unit-xiv-6-ignatius-grulgor':('traitor',[('The Eater of Lives','The first time Grulgor is reduced to 0 Wounds, roll a D6 before removing him. On 1–4 remove him normally. On 5+ he remains with 1 Wound and gains Daemon, Fearless and Feel No Pain (5+) for the rest of the battle. This may only occur once.')]),
'r41-unit-xiv-7-nathaniel-garro':('loyalist',[('Libertas','Libertas is a Two-Handed, Master-crafted Power Weapon which grants Garro +2 Strength. He receives no additional Attack for a second close-combat weapon while using it.'),('Aquila Imperator','The Aquila Imperator grants Garro a 4+ Invulnerable Save. Whenever Garro or a unit he has joined would be affected by an enemy psychic power, roll a D6. On 5+ that power is nullified against Garro and his unit. Only one such roll may be made per psychic power.')]),
}
for uid,(al,rules) in chars.items():
    e=findid(uid)
    if e is None: raise RuntimeError('Missing '+uid)
    hide_unless(e,'allegiance-'+al,'r11-dg-'+uid.split('-')[-1]+'-'+al)
    hide_source_entry(e)
    for n,(rn,txt) in enumerate(rules): set_rule(e,f'r11-dg-{uid}-rule-{n}',rn,txt)
# Typhon threshold exactly as source.
ty=findid('r41-unit-xiv-3-calas-typhon-first-captain'); set_min_points(ty,1500,'r11-dg-typhon-1500')
# Relabel existing named retinue selectors as functional choose-one.
for uid in chars:
    e=findid(uid)
    for g in groups(e):
        if 'Retinue' in (g.get('name') or ''): g.set('name','RETINUE — choose up to one (no separate FOC slot)')
log.append('Named-character allegiance, Typhon 1500-point gate, named rules and retinue selectors audited')

# Morturg chooses one normal Librarian psychic power.
mort=findid('r41-unit-xiv-4-crysos-morturg'); lib=findid('hq-librarian')
if mort is not None and lib is not None:
    pgs=ensure(mort,'selectionEntryGroups')
    for x in list(pgs):
        if (x.get('id') or '').startswith('r11-dg-morturg-psychic-'): pgs.remove(x)
    for src in groups(lib):
        sid=src.get('id') or ''; nm=(src.get('name') or '').lower()
        if sid.startswith('r29-lib-') or 'psych' in nm or 'discipline' in nm or 'power' in nm:
            cl=clone_prefix(src,'r11-dg-morturg-psychic-')
            if sid=='r29-lib-power-group':
                c=cl.find(C('constraints'))
                if c is not None:
                    for q in c:
                        if q.get('field')=='selections' and q.get('type') in ('min','max'): q.set('value','1')
            pgs.append(cl)
    log.append('Crysos Morturg given a functional one-power Librarian selector')

# Generic Death Guard Praetor/Centurion may replace their Terminator Command Squad with Deathshroud when actually wearing Terminator armour.
for hid,terms in [('hq-praetor',['hq-praetor-term','hq-praetor-tart','hq-praetor-cat']),('hq-centurion',['hq-centurion-term','hq-centurion-tart','hq-centurion-cat'])]:
    h=findid(hid); rg=next((g for g in groups(h) if 'Retinue' in (g.get('name') or '')),None)
    if h is None or rg is None: continue
    cl=retinue_clone(rg,DS,'r11-dg-'+hid+'-deathshroud-','DEATHSHROUD TERMINATORS')
    hide_unless(cl,'legion-xiv','r11-dg-'+hid+'-deathshroud-legion','roster'); hide_unless_any(cl,terms,'r11-dg-'+hid+'-deathshroud-armour','root-entry')
log.append('Deathshroud added as a functional Terminator-command replacement for eligible Death Guard Praetors/Centurions')

# Mortarion: Primarch points gate, exclusive mortal/daemon forms, Deathshroud-only Primarch Retinue.
mo=findid('r41-unit-xiv-8-xiv-mortarion-the-reaper'); dm=findid('r41-unit-xiv-9-mortarion-prince-of-decay')
if mo is None or dm is None: raise RuntimeError('Mortarion entries missing')
set_min_points(mo,2000,'r11-dg-mortarion-min-points')
prim=next((x for x in root.iter(C('selectionEntry')) if "PRIMARCH'S CHOSEN" in (x.get('name') or '').upper()),None)
if prim is not None:
    ms=ensure(mo,'modifiers'); mod=ET.SubElement(ms,C('modifier'),{'id':'r11-dg-mortarion-pc-1500','type':'set','field':'r11-dg-mortarion-min-points','value':'1500'}); cs=ET.SubElement(mod,C('conditions')); ET.SubElement(cs,C('condition'),{'type':'atLeast','value':'1','field':'selections','scope':'roster','childId':prim.get('id'),'shared':'true','includeChildSelections':'true','includeChildForces':'true'})
hide_if(mo,dm.get('id'),'r11-dg-mortarion-hide-daemon'); hide_if(dm,mo.get('id'),'r11-dg-daemon-mortarion-hide-mortal')
# Primarch Retinue, Deathshroud only.
gs=ensure(mo,'selectionEntryGroups'); gid='r11-dg-mortarion-retinue'
for x in list(gs):
    if x.get('id')==gid: gs.remove(x)
rg=ET.SubElement(gs,C('selectionEntryGroup'),{'id':gid,'name':'PRIMARCH RETINUE — Deathshroud only','hidden':'false'}); set_max(rg,1,gid+'-max'); retinue_clone(rg,DS,'r11-dg-mortarion-deathshroud-','DEATHSHROUD TERMINATORS')
hide_source_entry(mo)
for n,(rn,txt) in enumerate([
('Barbaran Plate','Barbaran Plate counts as Primarch Armour.'),
('Silence','Silence is a Two-Handed Power Weapon. Attacks are resolved at +1 Strength and have Rampage. Any unsaved Wound inflicted against a model without the Primarch rule becomes a Massive Wound and inflicts D3 Wounds instead of one.'),
('Barbaran Endurance','Mortarion has Feel No Pain (5+).'),
('Witch-Spite','Whenever Mortarion or a unit he has joined makes a Deny the Witch roll, a failed roll may be re-rolled. Mortarion’s Adamantium Will grants +2 to Deny the Witch rather than +1.'),
('The Reaper’s Advance','Friendly Death Guard Infantry within 12 inches of Mortarion may fire Rapid Fire weapons as though stationary and may re-roll failed Pinning tests.'),
('Toxic Miasma','Enemy non-Vehicle models in base contact with Mortarion suffer -1 Toughness while they remain in base contact.'),
('Poison Cannot Kill Death','Poisoned attacks against Mortarion do not use their fixed To Wound value. Resolve them using Strength versus Toughness; a Poisoned attack with no Strength wounds only on an unmodified 6.'),
('Primarch Retinue','Mortarion may select one Deathshroud Terminator Squad as his Primarch Retinue. He may not select Legion Honour Guard or Legion Terminator Command Squad as his Primarch Retinue.')]): set_rule(mo,f'r11-dg-mortarion-rule-{n}',rn,txt)
log.append('Mortarion gains functional 2000/1500 point gate, mutual-form exclusion and Deathshroud-only Primarch Retinue')

root.set('revision','11'); ct.write(CAT,encoding='utf-8',xml_declaration=True)
idx=IDX.read_text(encoding='utf-8'); idx=re.sub(r'(filePath="Legiones Astartes\.cat"[^>]*dataRevision=")\d+("\s*/>)',r'\g<1>11\2',idx); IDX.write_text(idx,encoding='utf-8')
OUT.write_text('LIVE R11 — DEATH GUARD UNIQUE PASS\nCAT=11 GSTref='+str(root.get('gameSystemRevision'))+'\n\n'+'\n'.join('• '+x for x in log),encoding='utf-8')
print(OUT.read_text(encoding='utf-8'))
