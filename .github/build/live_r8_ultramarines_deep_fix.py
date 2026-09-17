from pathlib import Path
from copy import deepcopy
import re
import xml.etree.ElementTree as ET

CAT=Path('Legiones Astartes.cat'); IDX=Path('index.xml'); OUT=Path('inspection-live-r8-ultramarines-deep-fix.txt')
NS='http://www.battlescribe.net/schema/catalogueSchema'; ET.register_namespace('',NS); C=lambda t:f'{{{NS}}}{t}'
ct=ET.parse(CAT); root=ct.getroot()
if root.get('revision')!='7': raise RuntimeError(f'Expected CAT 7, got {root.get("revision")}')

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
    r=ET.SubElement(rs,C('rule'),{'id':id_,'name':name,'hidden':'false'})
    ET.SubElement(r,C('description')).text=text

def hide_source_entry(e):
    rs=e.find(C('rules'))
    if rs is not None:
        for r in rs:
            if (r.get('name') or '')=='Source Entry': r.set('hidden','true')

def set_max_constraint(e,val,id_,scope='parent'):
    cs=ensure(e,'constraints')
    for x in list(cs):
        if x.get('id')==id_: cs.remove(x)
    ET.SubElement(cs,C('constraint'),{'id':id_,'type':'max','value':str(val),'field':'selections','scope':scope,'shared':'true','includeChildSelections':'true','includeChildForces':'false'})

def add_roster_max1(e,id_):
    cs=ensure(e,'constraints')
    for x in list(cs):
        if x.get('id')==id_: cs.remove(x)
    ET.SubElement(cs,C('constraint'),{'id':id_,'type':'max','value':'1','field':'selections','scope':'roster','shared':'true','includeChildSelections':'true','includeChildForces':'true'})

def hide_unless_selection(e,child_id,id_,scope='parent'):
    ms=ensure(e,'modifiers')
    for x in list(ms):
        if x.get('id')==id_: ms.remove(x)
    m=ET.SubElement(ms,C('modifier'),{'id':id_,'type':'set','field':'hidden','value':'true'})
    cs=ET.SubElement(m,C('conditions'))
    ET.SubElement(cs,C('condition'),{'type':'lessThan','value':'1','field':'selections','scope':scope,'childId':child_id,'shared':'true','includeChildSelections':'true','includeChildForces':'false'})

def hide_if_selection(e,child_id,id_,scope='parent'):
    ms=ensure(e,'modifiers')
    for x in list(ms):
        if x.get('id')==id_: ms.remove(x)
    m=ET.SubElement(ms,C('modifier'),{'id':id_,'type':'set','field':'hidden','value':'true'})
    cs=ET.SubElement(m,C('conditions'))
    ET.SubElement(cs,C('condition'),{'type':'atLeast','value':'1','field':'selections','scope':scope,'childId':child_id,'shared':'true','includeChildSelections':'true','includeChildForces':'false'})

def clone_with_prefix(src,prefix):
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

def add_retinue_clone(host_group,src,prefix,label=None):
    se=ensure(host_group,'selectionEntries')
    for x in list(se):
        if (x.get('id') or '').startswith(prefix): se.remove(x)
    cl=clone_with_prefix(src,prefix)
    strip_categories(cl); strip_roster_constraints(cl)
    cl.set('hidden','false')
    if label: cl.set('name',label)
    set_max_constraint(cl,1,prefix+'max','parent')
    set_rule(cl,prefix+'retinue-rule','Retinue','This unit is selected as a retinue and does not occupy a separate Force Organisation slot.')
    se.append(cl)
    return cl

def clone_clean_armoury(src_group,prefix,base_prefix,new_name):
    cl=deepcopy(src_group)
    # Keep standard entries only; remove legion-specific additions grafted into generic armouries.
    for cn in ('selectionEntries','entryLinks'):
        cont=cl.find(C(cn))
        if cont is not None:
            for x in list(cont):
                if not (x.get('id') or '').startswith(base_prefix): cont.remove(x)
    cl=clone_with_prefix(cl,prefix)
    cl.set('name',new_name)
    return cl

def add_clean_armoury(host,template_id,prefix,base_prefix,name,gate_id=None):
    src=findid(template_id)
    if src is None: raise RuntimeError('Missing armoury template '+template_id)
    gs=ensure(host,'selectionEntryGroups')
    for x in list(gs):
        if x.get('id')==prefix+template_id: gs.remove(x)
    cl=clone_clean_armoury(src,prefix,base_prefix,name)
    gs.append(cl)
    if gate_id: hide_unless_selection(cl,gate_id,cl.get('id')+'-gate')
    return cl

def find_transport_group(unit_id):
    u=findid(unit_id)
    if u is None:return None
    return next((g for g in groups(u) if 'Dedicated Transport' in (g.get('name') or '')),None)

def add_filtered_transport(host,template_unit,prefix,allowed):
    src=find_transport_group(template_unit)
    if src is None: raise RuntimeError('Missing transport group for '+template_unit)
    cl=clone_with_prefix(src,prefix)
    cl.set('name','Dedicated Transport')
    for cn in ('selectionEntries','entryLinks'):
        cont=cl.find(C(cn))
        if cont is not None:
            for x in list(cont):
                n=(x.get('name') or '').lower()
                if not any(a.lower() in n for a in allowed): cont.remove(x)
    gs=ensure(host,'selectionEntryGroups')
    for x in list(gs):
        if x.get('id')==cl.get('id'): gs.remove(x)
    gs.append(cl)
    set_rule(host,prefix+'transport-rule','Dedicated Transport','This squad may select the listed Dedicated Transport where Transport Capacity permits.')
    return cl

def move_options_to_group(parent_group,option_names,gid,gname,maxval):
    se=parent_group.find(C('selectionEntries'))
    if se is None:return None,[]
    moved=[]
    for e in list(se):
        if (e.get('name') or '').lower() in [n.lower() for n in option_names]:
            se.remove(e); moved.append(e)
    sgs=ensure(parent_group,'selectionEntryGroups')
    for x in list(sgs):
        if x.get('id')==gid: sgs.remove(x)
    g=ET.SubElement(sgs,C('selectionEntryGroup'),{'id':gid,'name':gname,'hidden':'false'})
    cs=ET.SubElement(g,C('constraints'))
    cid=gid+'-max'; ET.SubElement(cs,C('constraint'),{'id':cid,'type':'max','value':str(maxval),'field':'selections','scope':'parent','shared':'true','includeChildSelections':'true','includeChildForces':'false'})
    dest=ET.SubElement(g,C('selectionEntries'))
    for e in moved: dest.append(e)
    return g,moved

def dynamic_group_max_by_model(g,model_id,base=0):
    cid=g.get('id')+'-max'
    c=next((x for x in (g.find(C('constraints')) or []) if x.get('id')==cid),None)
    if c is not None:c.set('value',str(base))
    ms=ensure(g,'modifiers')
    mid=g.get('id')+'-dynmax'
    for x in list(ms):
        if x.get('id')==mid: ms.remove(x)
    m=ET.SubElement(ms,C('modifier'),{'id':mid,'type':'increment','field':cid,'value':'1'})
    reps=ET.SubElement(m,C('repeats'))
    ET.SubElement(reps,C('repeat'),{'field':'selections','scope':'root-entry','value':'1','percentValue':'false','shared':'true','includeChildSelections':'true','includeChildForces':'false','childId':model_id,'repeats':'1','roundUp':'false'})

def add_choice_group(parent,name,gid,choices,minv=1,maxv=1):
    gs=ensure(parent,'selectionEntryGroups')
    for x in list(gs):
        if x.get('id')==gid: gs.remove(x)
    g=ET.SubElement(gs,C('selectionEntryGroup'),{'id':gid,'name':name,'hidden':'false'})
    cs=ET.SubElement(g,C('constraints'))
    ET.SubElement(cs,C('constraint'),{'id':gid+'-min','type':'min','value':str(minv),'field':'selections','scope':'parent','shared':'true','includeChildSelections':'true','includeChildForces':'false'})
    ET.SubElement(cs,C('constraint'),{'id':gid+'-max','type':'max','value':str(maxv),'field':'selections','scope':'parent','shared':'true','includeChildSelections':'true','includeChildForces':'false'})
    se=ET.SubElement(g,C('selectionEntries'))
    for i,(n,text) in enumerate(choices):
        e=ET.SubElement(se,C('selectionEntry'),{'id':f'{gid}-{i}','name':n,'type':'upgrade','hidden':'false','import':'true'})
        set_max_constraint(e,1,f'{gid}-{i}-max')
        set_rule(e,f'{gid}-{i}-rule',n,text)
    return g

log=[]
# A. Unit requirements: source-defined 0-1 units.
inv=findid('r41-unit-xiii-0-invictarus-suzerain-squad'); ful=findid('r41-unit-xiii-1-fulmentarus-terminator-squad')
if inv is None or ful is None: raise RuntimeError('Missing XIII unique units')
add_roster_max1(inv,'r8-um-invictarus-01'); add_roster_max1(ful,'r8-um-fulmentarus-01')
log += ['Invictarus Suzerain top-level entry set to 0-1','Fulmentarus Terminator Squad set to 0-1']

# B. Correct retinue permissions. Invictarus can replace the normal bodyguard for a UM Praetor or named UM IC allowed a Command Squad.
pra=findid('hq-praetor'); prg=group_by_name(pra,'Retinue (does not occupy a separate FOC slot)')
if prg is None: raise RuntimeError('Praetor retinue group missing')
pr_inv=add_retinue_clone(prg,inv,'r8-um-praetor-suz-','INVICTARUS SUZERAIN SQUAD')
# Generic Praetor option must only appear in XIII Legion rosters.
ms=ensure(pr_inv,'modifiers'); m=ET.SubElement(ms,C('modifier'),{'id':'r8-um-praetor-suz-show','type':'set','field':'hidden','value':'true'}); cs=ET.SubElement(m,C('conditions')); ET.SubElement(cs,C('condition'),{'type':'lessThan','value':'1','field':'selections','scope':'roster','childId':'legion-xiii','shared':'true','includeChildSelections':'true','includeChildForces':'false'})
log.append('Ultramarines Praetor now has Invictarus Suzerains as a functional retinue alternative')
for hid,label in [('r41-unit-xiii-5-remus-ventanus','Remus Ventanus'),('r41-unit-xiii-8-titus-prayto','Titus Prayto')]:
    h=findid(hid); rg=next((g for g in groups(h) if 'Retinue' in (g.get('name') or '')),None)
    if rg is None: raise RuntimeError('Retinue group missing for '+label)
    add_retinue_clone(rg,inv,'r8-um-'+hid.split('-')[-1]+'-suz-','INVICTARUS SUZERAIN SQUAD')
    log.append(label+' now has Invictarus Suzerains as allowed by Honour Guard')

# C. Make the 0-1 Invictarus limit functional across top-level and XIII retinue copies.
inv_copies=[]
for e in root.iter(C('selectionEntry')):
    if e.get('type')=='unit' and (e.get('name') or '').strip().upper()=='INVICTARUS SUZERAIN SQUAD':
        i=e.get('id') or ''
        if i=='r41-unit-xiii-0-invictarus-suzerain-squad' or any(k in i for k in ('xiii-4-marius','xiii-5-remus','xiii-8-titus','guilliman','r8-um-praetor','r8-um-ventanus','r8-um-prayto')):
            inv_copies.append(e)
for e in inv_copies:
    ms=ensure(e,'modifiers')
    for x in list(ms):
        if (x.get('id') or '').startswith('r8-um-invictarus-mutual-'): ms.remove(x)
    others=[o.get('id') for o in inv_copies if o is not e]
    if others:
        mod=ET.SubElement(ms,C('modifier'),{'id':'r8-um-invictarus-mutual-'+re.sub(r'[^a-zA-Z0-9-]','-',e.get('id')),'type':'set','field':'hidden','value':'true'})
        cgs=ET.SubElement(mod,C('conditionGroups')); cg=ET.SubElement(cgs,C('conditionGroup'),{'type':'or'}); conds=ET.SubElement(cg,C('conditions'))
        for oid in others:
            ET.SubElement(conds,C('condition'),{'type':'atLeast','value':'1','field':'selections','scope':'roster','childId':oid,'shared':'true','includeChildSelections':'true','includeChildForces':'false'})
log.append(f'Invictarus 0-1 mutual exclusion applied across {len(inv_copies)} XIII copies')

# D. Leader Armoury access becomes real selectors, not text only.
suz_opt=next((x for x in group_items(group_by_name(inv,'Options')) if 'Suzerain Legate' in (x.get('name') or '')),None)
add_clean_armoury(inv,'veteran-sgt-armoury','r8-um-suz-arm-','veteran-sgt-','Suzerain Legate — Space Marine Armoury (max 50 pts)',suz_opt.get('id'))
add_clean_armoury(ful,'terminator-sgt-armoury','r8-um-ful-arm-','terminator-sgt-','Fulmentarus Decurion — Terminator Armoury (max 50 pts)',next(x for x in group_items(group_by_name(ful,'Options')) if 'Fulmentarus Decurion' in (x.get('name') or '')).get('id'))
loc=findid('r41-unit-xiii-2-locutarus-storm-squad'); nem=findid('r41-unit-xiii-3-nemesis-destroyer-squad')
add_clean_armoury(loc,'veteran-sgt-armoury','r8-um-loc-arm-','veteran-sgt-','Locutarus Strike Leader — Space Marine Armoury (max 50 pts)')
add_clean_armoury(nem,'destroyer-sgt-armoury','r8-um-nem-arm-','destroyer-sgt-','Nemesis Destroyer Sergeant — Space Marine Armoury (max 50 pts)')
log.append('All four XIII unique squad leaders now have functional 50-point Armoury selectors')

# E. Exact replacement limits.
fg=group_by_name(ful,'Options'); chain=next((x for x in group_items(fg) if (x.get('name') or '')=='Chainfist'),None)
if chain is not None:
    g,_=move_options_to_group(fg,['Chainfist'],'r8-um-ful-chainfists','Power Fist Replacement — up to one per model',0)
    dynamic_group_max_by_model(g,'r41-unit-xiii-1-fulmentarus-terminator-squad-additional',0)
    log.append('Fulmentarus Chainfists dynamically limited to squad size')
lg=group_by_name(loc,'Options')
g,_=move_options_to_group(lg,['Hand Flamer','Plasma pistol'],'r8-um-loc-pistols','Bolt Pistol Replacements — up to two models total',2)
log.append('Locutarus Hand Flamer/Plasma pistol choices now share one total max-2 limit')
ng=group_by_name(nem,'Options')
miss=next((x for x in group_items(ng) if 'Rad Missiles' in (x.get('name') or '')),None)
if miss is not None: miss.set('name','Missile Launcher with Suspensor Web and Rad Missiles')
g,_=move_options_to_group(ng,['Heavy Flamer','Missile Launcher with Suspensor Web and Rad Missiles'],'r8-um-nem-special','Special Weapon Replacement — one per five models',1)
# At exactly 10 models, total allowance becomes 2.
ms=ensure(g,'modifiers'); mod=ET.SubElement(ms,C('modifier'),{'id':'r8-um-nem-special-10','type':'set','field':'r8-um-nem-special-max','value':'2'}); cs=ET.SubElement(mod,C('conditions')); ET.SubElement(cs,C('condition'),{'type':'atLeast','value':'10','field':'selections','scope':'root-entry','childId':'r41-unit-xiii-3-nemesis-destroyer-squad-additional','shared':'true','includeChildSelections':'true','includeChildForces':'false'})
log.append('Nemesis Heavy Flamer/Rad Missile options now share 1-per-5 dynamic allowance')

# F. Dedicated transports exactly as written.
add_filtered_transport(ful,'terminator-unit','r8-um-ful-dt-',['Land Raider','Dreadclaw','Spartan'])
add_filtered_transport(nem,'destroyer-unit','r8-um-nem-dt-',['Rhino','Drop Pod','Dreadclaw','Land Raider'])
log.append('Fulmentarus and Nemesis Dedicated Transport selectors added from their written entries')

# G. Thiel is a true replacement choice: one roster-wide across both hosts; no Sergeant Armoury while selected; choose one tactic.
thiel_ids=['r6-tactical-unit-aeonid-thiel','r6-veteran-unit-aeonid-thiel']
for tid,other,hostid in [(thiel_ids[0],thiel_ids[1],'tactical-unit'),(thiel_ids[1],thiel_ids[0],'veteran-unit')]:
    e=findid(tid); host=findid(hostid)
    if e is None: raise RuntimeError('Thiel option missing '+tid)
    hide_if_selection(e,other,tid+'-r8-other-thiel','roster')
    set_rule(e,tid+'-r8-fixed','Aeonid Thiel — Sergeant Replacement','Aeonid Thiel replaces this squad’s Sergeant for +80 points. He remains part of the squad for the entire battle, is a Character but not an Independent Character, and may not purchase the replaced Sergeant’s personal Armoury options.')
    add_choice_group(e,'Unorthodox Tactics — choose one','r8-'+hostid+'-thiel-tactic',[
        ('Counter-Attack','Thiel and every model in his squad gain Counter-Attack for the duration of the battle.'),
        ('Move Through Cover','Thiel and every model in his squad gain Move Through Cover for the duration of the battle.'),
        ('Night Vision','Thiel and every model in his squad gain Night Vision for the duration of the battle.'),
        ('Tank Hunters','Thiel and every model in his squad gain Tank Hunters for the duration of the battle.'),
    ])
    for hg in groups(host):
        n=(hg.get('name') or '').lower()
        if 'sergeant' in n and 'wargear & upgrades' not in n:
            hide_if_selection(hg,tid,hg.get('id')+'-r8-hide-thiel','parent')
log.append('Aeonid Thiel is mutually unique across Tactical/Veteran hosts and now has a mandatory Unorthodox Tactics selector')

# H. Guilliman's universal Primarch army-size requirement: 2000 normally, 1500 under Primarch's Chosen.
gui=findid('r41-unit-xiii-9-xiii-roboute-guilliman-the-avenging-son')
cs=ensure(gui,'constraints')
for x in list(cs):
    if x.get('id')=='r8-guilliman-min-points': cs.remove(x)
ET.SubElement(cs,C('constraint'),{'id':'r8-guilliman-min-points','type':'min','value':'2000','field':'limit::points','scope':'roster','shared':'true','includeChildSelections':'true','includeChildForces':'true','percentValue':'false'})
primrite=next((x for x in root.iter(C('selectionEntry')) if "PRIMARCH'S CHOSEN" in (x.get('name') or '').upper()),None)
if primrite is not None:
    ms=ensure(gui,'modifiers'); mod=ET.SubElement(ms,C('modifier'),{'id':'r8-guilliman-primarch-chosen-1500','type':'set','field':'r8-guilliman-min-points','value':'1500'}); conds=ET.SubElement(mod,C('conditions')); ET.SubElement(conds,C('condition'),{'type':'atLeast','value':'1','field':'selections','scope':'roster','childId':primrite.get('id'),'shared':'true','includeChildSelections':'true','includeChildForces':'true'})
    log.append("Guilliman requires 2000 points normally / 1500 with Primarch's Chosen")
else: log.append("Guilliman minimum set to 2000; WARNING Primarch's Chosen selector not found for 1500 exception")

# I. Replace giant copy-paste source blobs with real named rules while keeping profiles/options intact.
RULES={
'r41-unit-xiii-0-invictarus-suzerain-squad':[
 ('Legatine Axe','A Legatine Axe is a Power Weapon which grants +1 Strength. A model attacking with a Legatine Axe does not receive the bonus Attack for fighting with two close-combat weapons.'),
 ('Honour Guard','One Invictarus Suzerain Squad may be selected as the retinue of an Ultramarines Praetor or named Ultramarines Independent Character who is permitted to select a Command Squad. It does not occupy a separate Force Organisation slot; the character and Suzerains count as a single HQ selection.'),
 ('Wargear','Artificer Armour; Boarding Shield; Bolt pistol; Legatine Axe.')],
'r41-unit-xiii-1-fulmentarus-terminator-squad':[
 ('Guided Warheads','When firing Frag missiles from their Cyclone Missile Launchers, Fulmentarus Terminators may fire at an enemy unit they cannot see if that unit is visible to a friendly model equipped with a Nuncio Vox. The Nuncio Vox bearer may not be embarked, Falling Back, Pinned or engaged in close combat. These shots must use Frag missiles, count as Barrage and follow normal ProHammer Barrage rules. Krak missiles may not use Guided Warheads.'),
 ('Wargear','Cataphractii Terminator Armour; Storm bolter; Power fist; Cyclone Missile Launcher.')],
'r41-unit-xiii-2-locutarus-storm-squad':[
 ('Argean Power Sword','An Argean Power Sword is a Master-crafted Power Weapon.'),
 ('Coordinated Assault','If the Locutarus charge an enemy unit which suffered one or more hits from another friendly Ultramarines unit during the preceding Shooting phase, the Locutarus may re-roll To Hit rolls of 1 during that Assault phase.'),
 ('Wargear','Artificer Armour; Jump Pack; Bolt pistol; Argean Power Sword; Frag grenades.')],
'r41-unit-xiii-3-nemesis-destroyer-squad':[
 ('Mortifier Bolter','Mortifier Bolters are normal Bolters with the Poisoned (3+) and Pinning special rules.'),
 ('Wargear','Power Armour; Mortifier Bolter; Bolt pistol; Chainsword; Rad grenades.')],
'r41-unit-xiii-4-marius-gage-first-master':[
 ('First Master of the Legion','Friendly non-Vehicle Ultramarines units with at least one model within 12 inches of Marius Gage may use his Leadership for Morale or Pinning tests.'),
 ('Master of Organisation','After both armies deploy but before the first turn, select one Ultramarines Infantry unit which deployed normally. It may immediately redeploy wholly within the Ultramarines deployment zone, obeying all normal restrictions. It may not be placed into Reserve; joined Independent Characters redeploy with it.'),
 ('Calculated Response','Marius Gage and any Ultramarines unit he has joined have Counter-Attack.'),
 ('Wargear','Artificer Armour; Iron Halo; Master-crafted Power Weapon; Bolt pistol; Frag grenades.')],
'r41-unit-xiii-5-remus-ventanus':[
 ('The Saviour of Calth','Ventanus and any Ultramarines unit he has joined have Fearless while at least one model from the unit is within 6 inches of an objective.'),
 ('Practical Commander','After both armies deploy but before the first turn, nominate one Legion Tactical Squad in the army. That squad gains Counter-Attack for the duration of the battle.'),
 ('Wargear','Artificer Armour; Refractor Field; Power weapon; Bolt pistol; Nuncio Vox; Frag grenades; Legion Standard.')],
'r41-unit-xiii-7-honoured-telemechrus':[
 ('Wargear','Kheres Assault Cannon; Dreadnought Close Combat Weapon with built-in Twin-linked Bolter; Smoke Launchers; Searchlight.'),
 ('Loyalist Only','Honoured Telemechrus may only be selected in a Loyalist Ultramarines army.')],
'r41-unit-xiii-8-titus-prayto':[
 ('Psychic Powers','Titus Prayto selects two psychic powers from the normal Psychic Power list and follows the normal ProHammer rules for Psykers, Mastery Level 2 and Disturbance in the Warp.'),
 ('Psychic Savant','Once during each Ultramarines player turn, Prayto may re-roll one failed Psychic Test. The second result must be accepted.'),
 ('Wargear','Artificer Armour; Refractor Field; Force Weapon; Psychic Hood; Bolt pistol; Frag grenades.')],
'r41-unit-xiii-9-xiii-roboute-guilliman-the-avenging-son':[
 ('Armour of Reason','The Armour of Reason counts as Primarch Armour.'),
 ('Gladius Incandor','Gladius Incandor is a Master-crafted Power Weapon. Attacks are resolved at +1 Strength and have Shred.'),
 ('Hand of Dominion','The Hand of Dominion is a Master-crafted Power Fist with Armourbane.'),
 ('Arbitrator','Arbitrator: Range 18 inches, Strength 6, AP3, Assault 2, Rending, Master-crafted.'),
 ('Master Strategist','Unless a rule specifically states otherwise, the range of Roboute Guilliman’s special rules which affect friendly Ultramarines units is 18 inches.'),
 ('Preternatural Strategy','After both armies deploy but before the first turn, nominate one friendly Ultramarines unit. It may be redeployed anywhere it could legally have been deployed at the beginning of the battle, obeying all normal restrictions, and may not be placed into Reserve unless it was already eligible to begin there.'),
 ('Sire of Ultramar','Friendly Ultramarines units with at least one model within 12 inches of Guilliman may re-roll failed Morale tests. The second result must be accepted.'),
 ('Theoretical / Practical','At the beginning of each Ultramarines turn choose Advance, Fire or Assault. Until the next Ultramarines turn, friendly Ultramarines units within 18 inches gain respectively: +1 inch Movement; re-roll shooting To Hit rolls of 1; or re-roll close-combat To Hit rolls of 1.'),
 ('Wargear','Armour of Reason; Gladius Incandor; Hand of Dominion; Arbitrator; Frag Grenades.')],
}
for uid,rs in RULES.items():
    e=findid(uid)
    if e is None: continue
    hide_source_entry(e)
    for n,(rn,txt) in enumerate(rs): set_rule(e,f'r8-{uid}-rule-{n}',rn,txt)
# All Invictarus retinue clones also receive readable real rules and no giant Source Entry wall.
for e in inv_copies:
    hide_source_entry(e)
    if e is not inv:
        for n,(rn,txt) in enumerate(RULES['r41-unit-xiii-0-invictarus-suzerain-squad']): set_rule(e,f'r8-{e.get("id")}-rule-{n}',rn,txt)
log.append('Ultramarines source-entry text walls replaced by discrete named rules while preserving stat profiles and functional selectors')

root.set('revision','8'); ct.write(CAT,encoding='utf-8',xml_declaration=True)
idx=IDX.read_text(encoding='utf-8'); idx=re.sub(r'(filePath="Legiones Astartes\.cat"[^>]*dataRevision=")\d+("\s*/>)',r'\g<1>8\2',idx); IDX.write_text(idx,encoding='utf-8')
OUT.write_text('LIVE R8 — ULTRAMARINES DEEP FIX\nCAT=8 GSTref='+str(root.get('gameSystemRevision'))+'\n\n'+'\n'.join('• '+x for x in log),encoding='utf-8')
print(OUT.read_text(encoding='utf-8'))
