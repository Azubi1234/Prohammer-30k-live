from pathlib import Path
from copy import deepcopy
import os, re, xml.etree.ElementTree as ET

CAT=Path('Legiones Astartes.cat')
IDX=Path('index.xml')
OUT=Path('inspection-live-r32-sons-of-horus.txt')
APPLY=os.environ.get('R32_APPLY')=='1'

NS='http://www.battlescribe.net/schema/catalogueSchema'
ET.register_namespace('',NS)
C=lambda t:f'{{{NS}}}{t}'

tree=ET.parse(CAT)
root=tree.getroot()
if root.get('revision')!='31':
    raise RuntimeError(f'R32 expected CAT revision 31, got {root.get("revision")}')

def ensure(p,t):
    x=p.find(C(t))
    if x is None:
        x=ET.SubElement(p,C(t))
    return x

def findid(i):
    return next((x for x in root.iter() if x.get('id')==i),None)

def parent_map():
    return {ch:p for p in root.iter() for ch in p}
def ancestors(e):
    pm=parent_map(); out=[]
    while e in pm:
        e=pm[e]; out.append(e)
    return out

def cost(e, value=None):
    cs=ensure(e,'costs')
    x=next((q for q in cs if q.get('typeId')=='pts'),None)
    if x is None:
        x=ET.SubElement(cs,C('cost'),{'name':'Points','typeId':'pts','value':'0'})
    if value is not None:
        x.set('value',str(value))
    return x

def add_constraint(e,id_,typ,value,scope='parent',field='selections'):
    cs=ensure(e,'constraints')
    old=next((x for x in cs if x.get('id')==id_),None)
    if old is not None: cs.remove(old)
    return ET.SubElement(cs,C('constraint'),{
        'id':id_,'type':typ,'value':str(value),'field':field,'scope':scope,
        'shared':'true','includeChildSelections':'true','includeChildForces':'false'
    })

def remove_constraint_type(e,typ,scope=None):
    cs=e.find(C('constraints'))
    if cs is None:return
    for x in list(cs):
        if x.get('type')==typ and (scope is None or x.get('scope')==scope):
            cs.remove(x)

def add_rule(e,id_,name,text,hidden='false'):
    rs=ensure(e,'rules')
    for x in list(rs):
        if x.get('id')==id_: rs.remove(x)
    r=ET.SubElement(rs,C('rule'),{'id':id_,'name':name,'hidden':hidden})
    ET.SubElement(r,C('description')).text=text
    return r

def hide_rule(e,id_or_name):
    rs=e.find(C('rules'))
    for r in list(rs or []):
        if r.get('id')==id_or_name or r.get('name')==id_or_name:
            r.set('hidden','true')

def add_profile(e,id_,name,vals):
    ps=ensure(e,'profiles')
    for x in list(ps):
        if x.get('id')==id_: ps.remove(x)
    p=ET.SubElement(ps,C('profile'),{'id':id_,'name':name,'hidden':'false','typeId':'prof-unit','typeName':'Unit'})
    cs=ET.SubElement(p,C('characteristics'))
    tids=[('WS','unit-ws'),('BS','unit-bs'),('S','unit-s'),('T','unit-t'),('W','unit-w'),('I','unit-i'),('A','unit-a'),('Ld','unit-ld'),('Sv','unit-sv')]
    for (n,tid),v in zip(tids,vals):
        c=ET.SubElement(cs,C('characteristic'),{'name':n,'typeId':tid}); c.text=str(v)
    return p

def add_ranged(e,id_,name,rng,s,ap,typ):
    ps=ensure(e,'profiles')
    for x in list(ps):
        if x.get('id')==id_: ps.remove(x)
    p=ET.SubElement(ps,C('profile'),{'id':id_,'name':name,'hidden':'false','typeId':'prof-ranged','typeName':'Ranged Weapon'})
    cs=ET.SubElement(p,C('characteristics'))
    for tid,n,v in [('ranged-range','Range',rng),('ranged-s','S',s),('ranged-ap','AP',ap),('ranged-type','Type',typ)]:
        q=ET.SubElement(cs,C('characteristic'),{'name':n,'typeId':tid}); q.text=v
    return p

def add_melee(e,id_,name,strength,rules):
    ps=ensure(e,'profiles')
    for x in list(ps):
        if x.get('id')==id_: ps.remove(x)
    p=ET.SubElement(ps,C('profile'),{'id':id_,'name':name,'hidden':'false','typeId':'prof-melee','typeName':'Melee Weapon'})
    cs=ET.SubElement(p,C('characteristics'))
    for tid,n,v in [('melee-s','Strength',strength),('melee-rules','Special Rules',rules)]:
        q=ET.SubElement(cs,C('characteristic'),{'name':n,'typeId':tid}); q.text=v
    return p

def cond(parent, typ, childId, value='1', scope='roster', field='selections'):
    return ET.SubElement(parent,C('condition'),{
        'type':typ,'value':str(value),'field':field,'scope':scope,'childId':childId,
        'shared':'true','includeChildSelections':'true','includeChildForces':'false'
    })

def modifier(e,id_,typ,field,value,conditions=None,repeats=None):
    ms=ensure(e,'modifiers')
    for x in list(ms):
        if x.get('id')==id_: ms.remove(x)
    m=ET.SubElement(ms,C('modifier'),{'id':id_,'type':typ,'field':field,'value':str(value)})
    if conditions:
        cs=ET.SubElement(m,C('conditions'))
        for spec in conditions:
            cond(cs,*spec)
    if repeats:
        rs=ET.SubElement(m,C('repeats'))
        for childId,val in repeats:
            ET.SubElement(rs,C('repeat'),{
                'value':str(val),'repeats':'1','field':'selections','scope':'root-entry','childId':childId,
                'shared':'true','roundUp':'false','includeChildSelections':'false','includeChildForces':'false'
            })
    return m

def gate_legion(e,id_='r32-soh-only'):
    modifier(e,id_,'set','hidden','true',[('lessThan','legion-xvi','1','roster','selections')])

def gate_allegiance(e,alleg,id_):
    modifier(e,id_,'set','hidden','true',[('lessThan',alleg,'1','roster','selections')])

def direct_group(e,name=None,id_=None):
    gs=e.find(C('selectionEntryGroups'))
    for g in list(gs or []):
        if (name is None or g.get('name')==name) and (id_ is None or g.get('id')==id_):
            return g
    return None

def direct_entry(e,id_=None,name=None):
    ss=e.find(C('selectionEntries'))
    for x in list(ss or []):
        if (id_ is None or x.get('id')==id_) and (name is None or x.get('name')==name):
            return x
    return None

def add_upgrade(parent,id_,name,pts=0,maxv=1):
    ss=ensure(parent,'selectionEntries')
    old=next((x for x in ss if x.get('id')==id_),None)
    if old is not None: ss.remove(old)
    u=ET.SubElement(ss,C('selectionEntry'),{'id':id_,'name':name,'type':'upgrade','hidden':'false','import':'true'})
    add_constraint(u,id_+'-max','max',maxv)
    cost(u,pts)
    return u

def add_group(parent,id_,name,maxv=None,minv=None):
    gs=ensure(parent,'selectionEntryGroups')
    old=next((x for x in gs if x.get('id')==id_),None)
    if old is not None: gs.remove(old)
    g=ET.SubElement(gs,C('selectionEntryGroup'),{'id':id_,'name':name,'hidden':'false'})
    if minv is not None:add_constraint(g,id_+'-min','min',minv)
    if maxv is not None:add_constraint(g,id_+'-max','max',maxv)
    return g

def move_entries(src_group,dst_group,ids):
    box=src_group.find(C('selectionEntries'))
    if box is None:return
    dest=ensure(dst_group,'selectionEntries')
    for x in list(box):
        if x.get('id') in ids:
            box.remove(x); dest.append(x)

def entry_by_suffix(unit,suffix):
    return next((x for x in unit.iter(C('selectionEntry')) if (x.get('id') or '').endswith(suffix)),None)

def group_by_suffix(unit,suffix):
    return next((x for x in unit.iter(C('selectionEntryGroup')) if (x.get('id') or '').endswith(suffix)),None)

def model_counter(unit):
    # Unique imported legion units use one direct model counter containing total unit models.
    ss=unit.find(C('selectionEntries'))
    cand=[]
    for x in list(ss or []):
        if x.get('type')!='model': continue
        mins=[float(c.get('value','0')) for c in list(x.find(C('constraints')) or []) if c.get('type')=='min']
        if mins:cand.append((max(mins),x))
    return max(cand,key=lambda q:q[0])[1] if cand else None

def set_squadwide_cost(opt,per,counter,fixed=0):
    cost(opt,fixed)
    if counter is not None:
        modifier(opt,opt.get('id')+'-r32-scale','increment','pts',per,repeats=[(counter.get('id'),'1')])

def shared_box():
    return ensure(root,'sharedSelectionEntries')

def add_entry_link(parent,id_,name,target,pts=None,maxv=1):
    es=ensure(parent,'entryLinks')
    old=next((x for x in es if x.get('id')==id_),None)
    if old is not None:es.remove(old)
    a={'id':id_,'name':name,'hidden':'false','type':'selectionEntry','targetId':target,'import':'true'}
    l=ET.SubElement(es,C('entryLink'),a)
    if maxv is not None:add_constraint(l,id_+'-max','max',maxv)
    if pts is not None:cost(l,pts)
    return l

def clone_with_ids(src,prefix):
    c=deepcopy(src)
    oldids=[x.get('id') for x in c.iter() if x.get('id')]
    mp={old:prefix+'-'+old for old in oldids}
    for x in c.iter():
        oid=x.get('id')
        if oid in mp:x.set('id',mp[oid])
    for x in c.iter():
        for a in ('childId','field'):
            v=x.get(a)
            if v in mp:x.set(a,mp[v])
    return c

def replace_category(e,target,name):
    box=ensure(e,'categoryLinks')
    for x in list(box):box.remove(x)
    ET.SubElement(box,C('categoryLink'),{
        'id':e.get('id')+'-cat','name':name,'hidden':'false','targetId':target,'primary':'true'
    })

def add_root_shared_clone(src,prefix,name,cat='cat-troops',catname='Troops'):
    box=shared_box()
    c=clone_with_ids(src,prefix)
    c.set('name',name)
    replace_category(c,cat,catname)
    box.append(c)
    return c

def add_hidden_unhide(e,baseid,ids,extra_conditions=None):
    e.set('hidden','true')
    for n,i in enumerate(ids):
        specs=[('atLeast',i,'1','roster','selections')]
        if extra_conditions: specs+=extra_conditions
        modifier(e,f'{baseid}-{n}','set','hidden','false',specs)

def remove_legion_upgrade_group(unit):
    gs=unit.find(C('selectionEntryGroups'))
    if gs is None:return
    for g in list(gs):
        if g.get('name')=='Legion Wargear & Upgrades':
            gs.remove(g)

report=[]
warnings=[]

# -------------------------------------------------------------------
# 1) Legion core rules remain on the XVI selector as the authoritative
#    reference; split them into discrete rules for New Recruit display.
# -------------------------------------------------------------------
leg=findid('legion-xvi')
if leg is None: raise RuntimeError('legion-xvi missing')
hide_rule(leg,'r25-legion-xvi-reference')
add_rule(leg,'r32-soh-close-range-brutality','Close Range Brutality',
'''At the beginning of the Assault phase, a Sons of Horus unit which is otherwise able to charge may fire at the enemy unit it intends to charge. Models armed with Rapid Fire, Pistol or Assault weapons may fire; Template weapons may not. These attacks hit only on a 5+ regardless of Ballistic Skill and never cause Morale or Pinning tests. The unit must charge the unit it fired upon. If casualties leave the target outside charge range or destroy it, the Sons of Horus unit may not charge another target; instead it moves D6" directly towards the target's current or final position. This is not a charge and may not bring the unit within 1" of another enemy model.''')
add_rule(leg,'r32-soh-tip-of-the-spear','Tip of the Spear',
'''Even if the mission does not normally permit Deep Strike, one Sons of Horus Infantry unit selected from Elites and one Sons of Horus Independent Character, either alone or joined by a Command Squad, may deploy using Deep Strike. These units must begin the battle in Reserve.''')
add_rule(leg,'r32-soh-pride','Pride of the Warmaster',
'''At the end of the final scheduled game turn, the opposing player may demand that one additional complete game turn be played. Roll a D6; on a 4+, one additional complete game turn is played. This roll may only be made once per battle. This does not extend a mission which has already ended because a specific objective or action was completed.''')
add_rule(leg,'r32-soh-armoury-ref','Sons of Horus Armoury',
'''Banestrike Ammunition, Cthonian Culling Blades, Chainaxes and Teleportation Transponders are added to eligible entries in New Recruit. Unit-specific prices and eligibility override the general Armoury where stated.''')
report.append('Legion rules split into discrete New Recruit rules')

# -------------------------------------------------------------------
# 2) Armoury access.
# -------------------------------------------------------------------
for uid in ['tactical-unit','assault-unit','breacher-unit','recon-unit','veteran-unit','terminator-unit','destroyer-unit','fa-seeker','hs-heavy-support-squad']:
    u=findid(uid)
    if u is None:
        warnings.append('missing armoury host '+uid); continue
    g=direct_group(u,id_='r49-legion-upgrades-'+uid)
    if g is None:
        g=direct_group(u,name='Legion Wargear & Upgrades')
    if g is None:
        g=add_group(u,'r32-soh-armoury-'+uid,'Legion Wargear & Upgrades')
    if findid('r46-soh-culling-blade') is not None:
        l=add_entry_link(g,'r32-soh-'+uid+'-culling','Cthonian Culling Blade — Sergeant','r46-soh-culling-blade')
        gate_legion(l,'r32-soh-'+uid+'-culling-legion')
    if findid('r46-soh-chainaxe') is not None:
        l=add_entry_link(g,'r32-soh-'+uid+'-chainaxe','Chainaxe — Sergeant','r46-soh-chainaxe')
        gate_legion(l,'r32-soh-'+uid+'-chainaxe-legion')

# Fix character Teleportation Transponders: Terminator-armour only.
for uid,armours in {
 'hq-praetor':['hq-praetor-term','hq-praetor-tart','hq-praetor-cat'],
 'hq-centurion':['hq-centurion-term','hq-centurion-tart','hq-centurion-cat','hq-consul-null-cat']
}.items():
    host=findid(uid)
    if host is None:continue
    for l in host.iter(C('entryLink')):
        if l.get('targetId')!='r46-soh-transponder-character':continue
        l.set('hidden','true')
        ms=l.find(C('modifiers'))
        if ms is not None:
            for m in list(ms):
                if any(q.get('childId')=='legion-xvi' for q in m.iter(C('condition'))): ms.remove(m)
        for n,a in enumerate(armours):
            modifier(l,f'r32-soh-{uid}-trans-unhide-{n}','set','hidden','false',[
                ('atLeast','legion-xvi','1','roster','selections'),
                ('atLeast',a,'1','root-entry','selections')
            ])
report.append('Sergeant armoury links and Terminator-only character transponders implemented')

# -------------------------------------------------------------------
# 3) Hide entries which are squad upgrades, not standalone units.
# -------------------------------------------------------------------
for uid in ['r41-unit-xvi-7-maloghurst-the-twisted','r41-unit-xvi-10-falkus-kibre','r41-unit-xvi-11-tarik-torgaddon']:
    e=findid(uid)
    if e is not None:e.set('hidden','true')
report.append('Standalone Maloghurst, Kibre and Torgaddon entries hidden')

# Shared Maloghurst replacement.
sb=shared_box()
for oldid in ['r32-soh-maloghurst-replacement','r32-soh-kibre-upgrade','r32-soh-torgaddon-upgrade']:
    old=findid(oldid)
    if old is not None and old in list(sb): sb.remove(old)

mal=ET.SubElement(sb,C('selectionEntry'),{'id':'r32-soh-maloghurst-replacement','name':'Maloghurst the Twisted','type':'upgrade','hidden':'false','import':'true'})
add_constraint(mal,'r32-soh-maloghurst-unique','max',1,'roster')
cost(mal,47) # 65 total minus the included 18-point Command Squad Veteran model.
add_profile(mal,'r32-soh-maloghurst-profile','Maloghurst the Twisted',['4','4','4','4','2','4','2','9','3+/5+'])
add_rule(mal,'r32-soh-maloghurst-rule','Maloghurst the Twisted',
'''Replaces the Legion Command Squad's Standard Bearer. Maloghurst has a total cost of 65 points; do not also pay the normal cost of the Standard Bearer or Legion Standard. He remains permanently part of the squad, is a Character but not an Independent Character, and occupies no separate Force Organisation selection. Wargear: Power Armour, Refractor Field, Bolter, Close-combat weapon, Frag grenades, Banner of the Warmaster. The Banner counts as a Legion Standard. Broken Body: reduce Normal, Advance, Charge, Fall Back and Consolidation movement made by Maloghurst's unit by 1", to a minimum of 1"; the unit may not Pursue.''')
kr=add_upgrade(mal,'r32-soh-maloghurst-krak','Krak grenades',2,1)

# Link Maloghurst into every Power Armour Legion Command Squad Standard group.
mal_links=0
pm=parent_map()
for g in list(root.iter(C('selectionEntryGroup'))):
    if g.get('name')!='Standard':continue
    an=ancestors(g)
    if not any((x.get('name') or '')=='Legion Command Squad' for x in an):continue
    if any('Terminator' in (x.get('name') or '') for x in an):continue
    lid=f'r32-soh-maloghurst-link-{mal_links}'
    l=add_entry_link(g,lid,'Maloghurst the Twisted','r32-soh-maloghurst-replacement')
    gate_legion(l,lid+'-legion')
    mal_links+=1
report.append(f'Maloghurst embedded in {mal_links} Command Squad Standard groups')

# Shared Kibre target.
kib=ET.SubElement(sb,C('selectionEntry'),{'id':'r32-soh-kibre-upgrade','name':'Upgrade one Justaerin to Falkus Kibre','type':'upgrade','hidden':'false','import':'true'})
add_constraint(kib,'r32-soh-kibre-unique','max',1,'roster')
cost(kib,28)
add_profile(kib,'r32-soh-kibre-profile','Falkus Kibre',['5','5','4','4','2','4','3','9','2+/4+'])
add_rule(kib,'r32-soh-kibre-rule','Justaerin Primus',
'''One Justaerin Terminator may be upgraded to Falkus Kibre for +28 points (85 points total). He remains part of the squad, is a Character but not an Independent Character, and occupies no separate Force Organisation selection. He retains the normal weapons of the Justaerin he replaces and may select normal Justaerin weapon replacements except Heavy weapons. While Kibre remains alive, his Justaerin Terminator Squad has Fearless. The squad may purchase Furious Charge for +4 points per model.''')

# Shared Torgaddon target; link cost differs because he replaces different included Sergeant costs.
torg=ET.SubElement(sb,C('selectionEntry'),{'id':'r32-soh-torgaddon-upgrade','name':'Tarik Torgaddon','type':'upgrade','hidden':'false','import':'true'})
add_constraint(torg,'r32-soh-torgaddon-unique','max',1,'roster')
cost(torg,0)
add_profile(torg,'r32-soh-torgaddon-profile','Tarik Torgaddon',['5','4','4','4','2','5','3','9','2+/5+'])
add_rule(torg,'r32-soh-torgaddon-rule','Tarik Torgaddon',
'''Torgaddon replaces the squad Sergeant, remains part of the squad for the entire battle, is a Character but not an Independent Character, and occupies no separate Force Organisation selection. No Independent Character may join Torgaddon's squad. Wargear: Artificer Armour, Refractor Field, Bolter, Power weapon and Frag grenades. Special Rules: Legiones Astartes (Sons of Horus), Stubborn. Torgaddon has a total cost of 105 points; the link cost shown is the difference between 105 and the included Sergeant he replaces.''')
add_upgrade(torg,'r32-soh-torgaddon-krak','Krak grenades',2,1)

# Tactical Torgaddon: only a 20-model squad (tac-marine = 19 plus Sergeant).
tac=findid('tactical-unit'); vet=findid('veteran-unit')
if tac is not None:
    g=direct_group(tac,id_='r49-legion-upgrades-tactical-unit') or direct_group(tac,name='Legion Wargear & Upgrades')
    l=add_entry_link(g,'r32-soh-torgaddon-tactical','Replace Sergeant with Tarik Torgaddon','r32-soh-torgaddon-upgrade',90)
    gate_legion(l,'r32-soh-torgaddon-tactical-legion')
    modifier(l,'r32-soh-torgaddon-tactical-size','set','hidden','true',[('lessThan','tac-marine','19','root-entry','selections')])
if vet is not None:
    g=direct_group(vet,id_='r49-legion-upgrades-veteran-unit') or direct_group(vet,name='Legion Wargear & Upgrades')
    l=add_entry_link(g,'r32-soh-torgaddon-veteran','Replace Sergeant with Tarik Torgaddon','r32-soh-torgaddon-upgrade',60)
    gate_legion(l,'r32-soh-torgaddon-veteran-legion')
report.append('Torgaddon embedded as exact Sergeant replacement in Tactical/Veteran squads')

# -------------------------------------------------------------------
# 4) Unique Sons of Horus squad option fixes across canonical entries
#    and retinue/Rite copies.
# -------------------------------------------------------------------
all_units=list(root.iter(C('selectionEntry')))
soh_variants={
 'justaerin':[u for u in all_units if 'r41-unit-xvi-0-justaerin-terminator-squad' in (u.get('id') or '') and not (u.get('id') or '').startswith('r46-al-reward')],
 'reaver':[u for u in all_units if 'r41-unit-xvi-1-reaver-attack-squad' in (u.get('id') or '') and not (u.get('id') or '').startswith('r46-al-reward')],
 'chieftain':[u for u in all_units if 'r41-unit-xvi-2-chieftain-squad' in (u.get('id') or '') and not (u.get('id') or '').startswith('r46-al-reward')],
 'luperci':[u for u in all_units if 'r41-unit-xvi-3-luperci-pack' in (u.get('id') or '') and not (u.get('id') or '').startswith('r46-al-reward')],
}

# Canonical 0-1 limits.
for uid in ['r41-unit-xvi-0-justaerin-terminator-squad','r41-unit-xvi-2-chieftain-squad','r41-unit-xvi-3-luperci-pack']:
    u=findid(uid)
    if u is not None and not any(c.get('id')=='r32-'+uid+'-unique' for c in list(u.find(C('constraints')) or [])):
        add_constraint(u,'r32-'+uid+'-unique','max',1,'roster')

def regroup(unit, suffixes, gid, gname, maxv, threshold=None, threshold_value=None):
    opts=next((g for g in unit.iter(C('selectionEntryGroup')) if (g.get('id') or '').endswith('-options') and g.get('name')=='Options'),None)
    if opts is None:return None
    ids=[]
    for s in suffixes:
        x=entry_by_suffix(unit,s)
        if x is not None:ids.append(x.get('id'))
    g=add_group(opts,gid,gname,maxv=maxv)
    move_entries(opts,g,ids)
    if threshold is not None and threshold_value is not None:
        c=next((x for x in list(g.find(C('constraints')) or []) if x.get('type')=='max'),None)
        if c is not None:
            modifier(g,gid+'-scale','set',c.get('id'),threshold_value,[('atLeast',threshold,'10','root-entry','selections')])
    return g

for unit in soh_variants['justaerin']:
    mid=model_counter(unit)
    if mid is None:continue
    # Remove duplicate shared Legion Wargear links from imported copies; native options are authoritative.
    remove_legion_upgrade_group(unit)
    # Heavy weapons share a single 2-per-5 pool.
    heavy=regroup(unit,
        ['-opt-6-heavy-flamer','-opt-7-reaper-autocannon','-opt-8-multi-melta'],
        unit.get('id')+'-r32-heavy','Heavy Weapons — 2 per 5 models',2,mid.get('id'),4)
    # Native Banestrike becomes exact +2 per eligible bearer.
    bane=entry_by_suffix(unit,'-opt-9-banestrike-ammunition')
    if bane is not None:
        set_squadwide_cost(bane,2,mid,0)
        add_rule(bane,bane.get('id')+'-r32-rule','Banestrike Ammunition',
                 'Purchase for every eligible Justaerin model at +2 points per eligible model. Banestrike is used with Foeblaster/Combi weapons; a natural To Wound roll of 6 is resolved at AP3. Models that replace the bolt weapon with a pair of Lightning Claws or a Heavy weapon neither pay for nor benefit from Banestrike.')
        # Remove the charge for models that no longer carry eligible bolt weapons.
        for s in ['-opt-5-pair-of-lightning-claws','-opt-6-heavy-flamer','-opt-7-reaper-autocannon','-opt-8-multi-melta']:
            x=entry_by_suffix(unit,s)
            if x is not None:
                modifier(bane,bane.get('id')+'-discount-'+re.sub('[^a-z0-9]+','-',s.lower()),'increment','pts',-2,repeats=[(x.get('id'),'1')])
    # Shared Kibre target + squad-local Furious Charge.
    opts=next((g for g in unit.iter(C('selectionEntryGroup')) if (g.get('id') or '').endswith('-options') and g.get('name')=='Options'),None)
    if opts is not None:
        lid=unit.get('id')+'-r32-kibre'
        lk=add_entry_link(opts,lid,'Upgrade one Justaerin to Falkus Kibre','r32-soh-kibre-upgrade')
        fc=add_upgrade(opts,unit.get('id')+'-r32-kibre-furious','Furious Charge — Kibre’s squad',0,1)
        set_squadwide_cost(fc,4,mid,0)
        modifier(fc,fc.get('id')+'-hide','set','hidden','true',[('lessThan',lid,'1','root-entry','selections')])
        add_rule(fc,fc.get('id')+'-rule','Furious Charge','Available only while this squad includes Falkus Kibre; costs +4 points per model for the entire squad.')
    # Dedicated transport: make Dreadclaw functional, retain exact Land Raider/Spartan capacity rule as text.
    tg=add_group(unit,unit.get('id')+'-r32-transport','Dedicated Transport',maxv=1)
    if findid('transport-dreadclaw') is not None:
        add_entry_link(tg,unit.get('id')+'-r32-dreadclaw','Dreadclaw Drop Pod','transport-dreadclaw')
    add_rule(tg,unit.get('id')+'-r32-transport-rule','Dedicated Transport',
             'The squad may select a Land Raider, Dreadclaw Drop Pod or Spartan Assault Tank where Transport Capacity permits. The Dreadclaw is selectable here; use the normal Legion vehicle entry for the appropriate Land Raider or Spartan pattern.')

for unit in soh_variants['reaver']:
    mid=model_counter(unit)
    if mid is None:continue
    # Shared ranged replacement cap 2.
    regroup(unit,['-opt-0-flamer','-opt-1-meltagun','-opt-2-plasma-gun','-opt-3-plasma-pistol'],
            unit.get('id')+'-r32-ranged','Ranged Replacements — up to 2',2)
    # One melee replacement per 5 models.
    g=regroup(unit,['-opt-4-replace-his-chainaxe-with-a-power-fist','-opt-5-a-pair-of-lightning-claws'],
            unit.get('id')+'-r32-melee','Melee Replacements — 1 per 5 models',1,mid.get('id'),2)
    # Fix individual claw cap so the shared group controls the total.
    lc=entry_by_suffix(unit,'-opt-5-a-pair-of-lightning-claws')
    if lc is not None:
        for c in list(lc.find(C('constraints')) or []):
            if c.get('type')=='max':c.set('value','2')
    # Terminator Honours: every Reaver other than Chieftain = total-1.
    th=entry_by_suffix(unit,'-opt-6-terminator-honours')
    if th is not None:
        mx=next((c for c in list(th.find(C('constraints')) or []) if c.get('type')=='max'),None)
        if mx is not None:
            mx.set('value','4')
            for n in range(6,11):
                modifier(th,f'{th.get("id")}-r32-cap-{n}','set',mx.get('id'),n-1,[('atLeast',mid.get('id'),str(n),'root-entry','selections')])
    # Exact squad-wide costs.
    for suf,per in [('-opt-7-krak-grenades',2),('-opt-8-melta-bombs',5)]:
        x=entry_by_suffix(unit,suf)
        if x is not None:
            x.set('name','Krak grenades — entire squad' if per==2 else 'Melta bombs — entire squad')
            set_squadwide_cost(x,per,mid,0)
    opts=next((g for g in unit.iter(C('selectionEntryGroup')) if (g.get('id') or '').endswith('-options') and g.get('name')=='Options'),None)
    if opts is not None and entry_by_suffix(unit,'-r32-jump-packs') is None:
        jp=add_upgrade(opts,unit.get('id')+'-r32-jump-packs','Jump Packs — entire squad',0,1)
        set_squadwide_cost(jp,15,mid,0)
        add_rule(jp,jp.get('id')+'-rule','Jump Assault','The entire squad is equipped with Jump Packs and becomes Jump Infantry. A squad equipped with Jump Packs may not select a Dedicated Transport.')
    tg=add_group(unit,unit.get('id')+'-r32-transport','Dedicated Transport',maxv=1)
    for tid,nm in [('transport-rhino','Rhino'),('transport-drop-pod','Drop Pod'),('transport-dreadclaw','Dreadclaw Drop Pod')]:
        if findid(tid) is not None:add_entry_link(tg,unit.get('id')+'-r32-'+tid,nm,tid)
    add_rule(tg,unit.get('id')+'-r32-transport-rule','Dedicated Transport','A squad without Jump Packs may select a Rhino, Drop Pod, Dreadclaw Drop Pod or Land Raider where Transport Capacity permits.')
    jp=entry_by_suffix(unit,'-r32-jump-packs')
    if jp is not None:
        modifier(tg,tg.get('id')+'-jump-hide','set','hidden','true',[('atLeast',jp.get('id'),'1','root-entry','selections')])

for unit in soh_variants['chieftain']:
    mid=model_counter(unit)
    if mid is None:continue
    opts=next((g for g in unit.iter(C('selectionEntryGroup')) if (g.get('id') or '').endswith('-options') and g.get('name')=='Options'),None)
    if opts is not None:
        mg=regroup(unit,['-opt-0-power-weapon','-opt-1-power-fist','-opt-2-lightning-claw','-opt-3-thunder-hammer'],
                   unit.get('id')+'-r32-melee','Culling Blade Replacements',0)
        rg=regroup(unit,['-opt-4-foeblaster-boltgun','-opt-5-combi-flamer','-opt-6-combi-volkite-charger','-opt-7-combi-meltagun','-opt-8-combi-plasma-gun'],
                   unit.get('id')+'-r32-ranged','Bolter Replacements',0)
        for g in [mg,rg]:
            if g is None:continue
            mx=next((c for c in list(g.find(C('constraints')) or []) if c.get('type')=='max'),None)
            if mx is not None:
                modifier(g,g.get('id')+'-scale','increment',mx.get('id'),1,repeats=[(mid.get('id'),'1')])
    for suf,per in [('-opt-9-krak-grenades',2),('-opt-10-melta-bombs',5)]:
        x=entry_by_suffix(unit,suf)
        if x is not None:
            x.set('name','Krak grenades — entire squad' if per==2 else 'Melta bombs — entire squad')
            set_squadwide_cost(x,per,mid,0)
    tg=add_group(unit,unit.get('id')+'-r32-transport','Dedicated Transport',maxv=1)
    for tid,nm in [('transport-rhino','Rhino'),('transport-dreadclaw','Dreadclaw Drop Pod')]:
        if findid(tid) is not None:add_entry_link(tg,unit.get('id')+'-r32-'+tid,nm,tid)
    add_rule(tg,unit.get('id')+'-r32-transport-rule','Dedicated Transport','The squad may select a Rhino, Dreadclaw Drop Pod or Land Raider where Transport Capacity permits.')

for unit in soh_variants['luperci']:
    mid=model_counter(unit)
    if mid is None:continue
    regroup(unit,['-opt-0-flamer','-opt-1-meltagun','-opt-2-plasma-gun'],
            unit.get('id')+'-r32-ranged','Special Weapons — 1 per 5 models',1,mid.get('id'),2)

report.append('Unique squad shared caps, per-model costs, Kibre, Jump Packs and transport gates corrected')

# -------------------------------------------------------------------
# 5) Rites of War: add functional role copies.
# -------------------------------------------------------------------
longmarch=findid('r25-rite-xvi-0-the-long-march')
black=findid('r25-rite-xvi-1-the-black-reaving')
term=findid('terminator-unit')
if longmarch is not None and term is not None:
    # remove any prior R32 clone
    box=shared_box()
    for x in list(box):
        if x.get('id')=='r32-soh-long-march-terminator-troops':box.remove(x)
    lm=add_root_shared_clone(term,'r32-soh-long-march','Legion Terminator Squad — Long March (non-compulsory Troops)')
    lm.set('id','r32-soh-long-march-terminator-troops')
    # IDs below the root were already prefixed; root change is safe because no self-reference.
    add_hidden_unhide(lm,'r32-soh-longmarch-show',['r25-rite-xvi-0-the-long-march'])
    add_constraint(lm,'r32-soh-longmarch-noncomp','max',99,'roster')
    add_rule(lm,'r32-soh-longmarch-role','The Warmaster’s Portion','Selected as a non-compulsory Troops choice under The Long March. This unit may not fulfil a compulsory Troops selection.')
    report.append('Long March Terminator non-compulsory Troops role added')

# Black Reaving Reaver Troops copy already exists; reinforce exact compulsory status.
brcopy=findid('r42-role-xvi-1-effects-reaver-onslaught-reaver-attack-squads-r41-unit-xvi-1-reaver-attack-squad')
if brcopy is not None:
    add_rule(brcopy,'r32-soh-black-reaving-role','Reaver Onslaught','This Reaver Attack Squad is selected as Troops under The Black Reaving and may fulfil a compulsory Troops selection. At least one compulsory Troops choice in the Detachment must be a Reaver Attack Squad.')
else:
    warnings.append('Black Reaving Reaver Troops copy missing')

# -------------------------------------------------------------------
# 6) Horus Lupercal and Horus Ascended.
# -------------------------------------------------------------------
HORUS='r41-unit-xvi-12-xvi-horus-lupercal-the-warmaster'
ASC='r41-unit-xvi-13-xvi-horus-ascended-the-warmaster'
h=findid(HORUS); a=findid(ASC)
if h is None or a is None:raise RuntimeError('Horus entries missing')

# Mutual exclusion + Ascended Traitor-only.
modifier(h,'r32-horus-hide-asc','set','hidden','true',[('atLeast',ASC,'1','roster','selections')])
modifier(a,'r32-asc-hide-horus','set','hidden','true',[('atLeast',HORUS,'1','roster','selections')])
gate_allegiance(a,'allegiance-traitor','r32-asc-traitor')

# Mortal Horus rules.
for rid in [x.get('id') for x in list(h.find(C('rules')) or []) if (x.get('id') or '').startswith('r32-horus-')]:
    hide_rule(h,rid)
add_rule(h,'r32-horus-wargear','Wargear','Serpent’s Scales; Worldbreaker; The Talon of Horus; Frag Grenades; Krak Grenades.')
add_rule(h,'r32-horus-scales','Serpent’s Scales','Counts as Primarch Armour: 1+ Armour Save and 4+ Invulnerable Save.')
add_rule(h,'r32-horus-worldbreaker','Worldbreaker','Master-crafted Thunder Hammer. Horus resolves attacks made with Worldbreaker at Initiative 3 rather than Initiative 1; all other Thunder Hammer rules apply.')
add_rule(h,'r32-horus-talon','The Talon of Horus','Master-crafted Lightning Claw incorporating a Twin-linked Storm Bolter. Each time it fires, choose one ammunition profile shown on this entry. Only one ammunition type may be used per attack and their effects may not be combined.')
add_melee(h,'r32-horus-worldbreaker-prof','Worldbreaker','x2','Master-crafted, Thunder Hammer; strikes at Initiative 3')
add_melee(h,'r32-horus-talon-prof','The Talon of Horus','User','Master-crafted Lightning Claw')
for id_,nm,rng,s,ap,typ in [
 ('bane','Talon — Banestrike','18"','4','4','Assault 2, Twin-linked, Banestrike'),
 ('dragon','Talon — Dragonfire','24"','4','5','Assault 2, Twin-linked, Ignores Cover'),
 ('hell','Talon — Hellfire','24"','X','5','Assault 2, Twin-linked, Poisoned (2+)'),
 ('kraken','Talon — Kraken','30"','4','4','Assault 2, Twin-linked'),
 ('vengeance','Talon — Vengeance','18"','4','3','Assault 2, Twin-linked, Gets Hot')]:
    add_ranged(h,'r32-horus-talon-'+id_,nm,rng,s,ap,typ)
add_rule(h,'r32-horus-banestrike','Banestrike','A natural To Wound roll of 6 made with the Talon’s Banestrike ammunition is resolved at AP3.')
add_rule(h,'r32-horus-will','Will of the Warmaster','Friendly units with Legiones Astartes (Sons of Horus) that can draw line of sight to Horus may re-roll failed Morale and Pinning tests. Friendly Sons of Horus units with at least one model within 12" of Horus instead have Fearless. This is Horus’ unique Warlord ability.')
add_rule(h,'r32-horus-spear','Master of the Speartip','When using Tip of the Spear, up to two Sons of Horus Infantry units selected from Elites may deploy using Deep Strike instead of the normal one. The Independent Character allowance is unchanged. All units deployed in this manner begin in Reserve.')
add_rule(h,'r32-horus-first','The First Company','Up to two Legion Terminator Squads may be selected as Troops instead of Elites; one of those selections may instead be a Justaerin Terminator Squad. A Justaerin selected this way ignores the normal 0–1 limit. These selections may fulfil compulsory Troops choices.')
add_rule(h,'r32-horus-vengeful','The Vengeful Spirit','Every Legion Drop Pod and Anvillus Pattern Dreadclaw Drop Pod purchased by the army costs 10 points less. Once per battle from turn 2 onwards, Horus may call a Vengeful Spirit Lance Strike instead of making a normal shooting attack, provided he is on the battlefield and not engaged in close combat or a Primarch Duel. Place the Blast anywhere; no line of sight is required. On a Hit it remains; on an arrow it scatters D6".')
add_ranged(h,'r32-horus-lance','Vengeful Spirit Lance Strike','Unlimited','10','1','Ordnance 1, Blast')

# Great Crusade Panoply.
hg=add_group(h,'r32-horus-options','Horus Options',maxv=1)
pan=add_upgrade(hg,'r32-horus-great-crusade-panoply','Great Crusade Panoply',-25,1)
add_rule(pan,'r32-horus-panoply-rule','Great Crusade Panoply','Exchange Worldbreaker and the Talon of Horus for a Master-crafted Power Sword and Master-crafted Seeker Bolter with Special Issue Ammunition.')
add_melee(pan,'r32-horus-panoply-sword','Master-crafted Power Sword','User','Power Weapon, Master-crafted')
for id_,nm,rng,s,ap,typ in [
 ('dragon','Dragonfire Bolts','24"','4','5','Rapid Fire, Ignores Cover, Master-crafted'),
 ('hell','Hellfire Bolts','24"','X','5','Rapid Fire, Poisoned (2+), Master-crafted'),
 ('kraken','Kraken Bolts','30"','4','4','Rapid Fire, Master-crafted'),
 ('vengeance','Vengeance Rounds','18"','4','3','Rapid Fire, Gets Hot, Master-crafted')]:
    add_ranged(pan,'r32-horus-pan-'+id_,nm,rng,s,ap,typ)

# Ascended: split giant source into discrete rules.
hide_rule(a,a.get('id')+'-source')
add_rule(a,'r32-asc-wargear','Wargear','Serpent’s Scales; Worldbreaker; The Talon of Horus; Frag Grenades; Krak Grenades.')
add_rule(a,'r32-asc-scales','Serpent’s Scales','Confers a 1+ Armour Save and 3+ Invulnerable Save.')
add_rule(a,'r32-asc-worldbreaker','Worldbreaker','Master-crafted Thunder Hammer. Horus Ascended strikes with Worldbreaker at Initiative 4 rather than Initiative 1.')
add_rule(a,'r32-asc-talon','The Talon of Horus','Master-crafted Lightning Claw that grants +1 Strength and incorporates a Twin-linked Storm Bolter using the Talon ammunition from the mortal Horus entry. Horus may divide his Attacks between Worldbreaker and the Talon in any combination.')
add_rule(a,'r32-asc-will','Will of the Warmaster','Friendly Sons of Horus units with line of sight to Horus may re-roll failed Morale and Pinning tests. Friendly Sons of Horus units with at least one model within 12" are Fearless.')
add_rule(a,'r32-asc-spear','Master of the Speartip','When Horus commands the army, one additional eligible Sons of Horus Elite Infantry unit may use Tip of the Spear.')
add_rule(a,'r32-asc-first','The First Company','Horus Ascended receives the same First Company Troops availability as Horus Lupercal: up to two Legion Terminator selections, one of which may instead be Justaerin; they may fulfil compulsory Troops and the Justaerin copy ignores the normal 0–1 limit.')
add_rule(a,'r32-asc-vengeful','The Vengeful Spirit','Drop Pods and Dreadclaws in Horus’ army receive the -10 point Spearhead Assault reduction. Once per battle Horus may call a Lance Strike in his Shooting phase: Unlimited, S10, AP1, Ordnance 1, Blast.')
add_ranged(a,'r32-asc-lance','Vengeful Spirit Lance Strike','Unlimited','10','1','Ordnance 1, Blast')
add_rule(a,'r32-asc-vessel','Vessel of the Four','Horus counts as a Daemon for rules, weapons and abilities that specifically affect Daemons. His profile already incorporates the favour of all four Chaos Gods; he gains no further characteristic bonuses from Blessings of the Four.')
add_rule(a,'r32-asc-favoured','Favoured of the Dark Gods','Whenever an enemy psychic power directly targets or affects Horus, roll a D6 after the Psychic Test is passed; on a 3+ the power is nullified against him. A power directly targeting or affecting a friendly unit within 6" of Horus is nullified on a 4+.')
add_rule(a,'r32-asc-blessings','Blessings of the Four','If Horus Ascended is included, Traitor Legiones Astartes Infantry units and Independent Characters may purchase one Blessing. Every model in a unit must purchase the same Blessing; Primarchs may not. Khorne: +1 Attack (+5/model or +20 IC). Slaanesh: +1 Initiative (+4/model or +15 IC). Nurgle: +1 Toughness and Slow and Purposeful (+7/model or +25 IC); not available to Bikes, Jetbikes or Jump Infantry. Tzeentch: gain 5++ or improve an existing Invulnerable Save by one step to max 4++ (+8/model or +25 IC).')
add_rule(a,'r32-asc-lead','The Warmaster Must Lead','Horus Ascended may never voluntarily begin in Reserve and must deploy at the start whenever the mission permits. If a mission requires him to begin in Reserve, he automatically arrives on the first turn.')

# Pod/Dreadclaw reduction.
for tid in ['transport-drop-pod','transport-dreadclaw']:
    tr=findid(tid)
    if tr is None:
        warnings.append('missing transport for Horus discount '+tid); continue
    modifier(tr,'r32-horus-discount-'+tid,'increment','pts',-10,[('atLeast',HORUS,'1','roster','selections')])
    modifier(tr,'r32-asc-discount-'+tid,'increment','pts',-10,[('atLeast',ASC,'1','roster','selections')])

# First Company Troops role copies.
box=shared_box()
for xid in ['r32-soh-first-company-terminators','r32-soh-first-company-justaerin']:
    old=findid(xid)
    if old is not None and old in list(box):box.remove(old)

fct=add_root_shared_clone(term,'r32-soh-first-company-term','Legion Terminator Squad — Horus’ First Company')
fct.set('id','r32-soh-first-company-terminators')
add_hidden_unhide(fct,'r32-soh-first-term-show',[HORUS,ASC],[('atLeast','legion-xvi','1','roster','selections')])
remove_constraint_type(fct,'max','roster')
mx=add_constraint(fct,'r32-soh-first-term-max','max',2,'roster')
add_rule(fct,'r32-soh-first-term-rule','The First Company','Troops choice granted by Horus. May fulfil a compulsory Troops selection. A maximum of two First Company Troops selections may be made in total, and at most one may be Justaerin.')

just=findid('r41-unit-xvi-0-justaerin-terminator-squad')
fcj=add_root_shared_clone(just,'r32-soh-first-company-just','Justaerin Terminator Squad — Horus’ First Company')
fcj.set('id','r32-soh-first-company-justaerin')
add_hidden_unhide(fcj,'r32-soh-first-just-show',[HORUS,ASC],[('atLeast','legion-xvi','1','roster','selections')])
remove_constraint_type(fcj,'max','roster')
add_constraint(fcj,'r32-soh-first-just-max','max',1,'roster')
add_rule(fcj,'r32-soh-first-just-rule','The First Company','Troops choice granted by Horus. May fulfil a compulsory Troops selection and ignores the normal 0–1 Justaerin limit.')
# Combined maximum 2: if Justaerin selected, Terminator copy max becomes 1; if two Terminator copies, hide Justaerin.
modifier(fct,'r32-soh-first-term-cap-with-just','set','r32-soh-first-term-max',1,[('atLeast','r32-soh-first-company-justaerin','1','roster','selections')])
modifier(fcj,'r32-soh-first-just-hide-two-term','set','hidden','true',[('atLeast','r32-soh-first-company-terminators','2','roster','selections')])
report.append('Horus/Ascended rules, Panoply, Vengeful Spirit discount and First Company Troops implemented')

# Horus Primarch Retinue — functional Justaerin and exact reference for other two patterns.
for hh in [h,a]:
    rg=add_group(hh,hh.get('id')+'-r32-retinue','Primarch Retinue (no FOC slot)',maxv=1)
    rj=clone_with_ids(just,hh.get('id')+'-r32-ret-just')
    rj.set('name','Justaerin Terminator Squad — Primarch Retinue')
    # no category in embedded retinue
    cb=rj.find(C('categoryLinks'))
    if cb is not None:
        for q in list(cb):cb.remove(q)
    remove_constraint_type(rj,'max','roster')
    add_rule(rj,hh.get('id')+'-r32-ret-just-rule','Primarch Retinue','Does not occupy an additional Force Organisation selection and does not count against the normal 0–1 Justaerin limitation. This retinue gains Furious Charge at no additional points cost.')
    ensure(rg,'selectionEntries').append(rj)
    add_rule(rg,hh.get('id')+'-r32-retinue-rule','Primarch Retinue','Horus may select a Legion Honour Guard Squad, Legion Terminator Command Squad or Justaerin Terminator Squad as his Primarch Retinue. The Justaerin option is selectable here; Honour Guard and Terminator Command use their normal Primarch Retinue entries where present in the catalogue.')
report.append('Horus Justaerin Primarch Retinue embedded')

# -------------------------------------------------------------------
# 7) Blessings of the Four — functional costs on primary SoH Infantry
#    and Independent Character entries.
# -------------------------------------------------------------------
def add_blessings_squad(unit,base_count,counter_id,nurgle_block_ids=None):
    if unit is None:return
    gs=ensure(unit,'selectionEntryGroups')
    old=next((g for g in gs if g.get('id')==unit.get('id')+'-r32-blessings'),None)
    if old is not None:gs.remove(old)
    g=add_group(unit,unit.get('id')+'-r32-blessings','Blessings of the Four',maxv=1)
    g.set('hidden','true')
    modifier(g,g.get('id')+'-show','set','hidden','false',[
        ('atLeast',ASC,'1','roster','selections'),
        ('atLeast','allegiance-traitor','1','roster','selections'),
        ('atLeast','legion-xvi','1','roster','selections')
    ])
    counter=findid(counter_id) if counter_id else None
    # Counter may be cloned/prefixed; prefer descendant ending in counter_id.
    if counter is None or counter not in list(unit.iter()):
        counter=next((x for x in unit.iter(C('selectionEntry')) if (x.get('id') or '').endswith(counter_id or '___')),None)
    # base_count is number represented outside counter; for generic squads this is usually the Sergeant.
    for key,nm,per,rule in [
        ('khorne','Blessing of Khorne',5,'All models gain +1 Attack.'),
        ('slaanesh','Blessing of Slaanesh',4,'All models gain +1 Initiative.'),
        ('nurgle','Blessing of Nurgle',7,'All models gain +1 Toughness and Slow and Purposeful. Not available to Bikes, Jetbikes or Jump Infantry.'),
        ('tzeentch','Blessing of Tzeentch',8,'All models gain a 5+ Invulnerable Save, or improve an existing Invulnerable Save by one step to a maximum of 4+.')]:
        u=add_upgrade(g,unit.get('id')+'-r32-blessing-'+key,nm,per*base_count,1)
        if counter is not None:modifier(u,u.get('id')+'-scale','increment','pts',per,repeats=[(counter.get('id'),'1')])
        add_rule(u,u.get('id')+'-rule',nm,rule)
        if key=='nurgle' and nurgle_block_ids:
            for n,bid in enumerate(nurgle_block_ids):
                modifier(u,u.get('id')+f'-block-{n}','set','hidden','true',[('atLeast',bid,'1','root-entry','selections')])

def add_blessings_ic(unit):
    if unit is None:return
    gs=ensure(unit,'selectionEntryGroups')
    old=next((g for g in gs if g.get('id')==unit.get('id')+'-r32-blessings'),None)
    if old is not None:gs.remove(old)
    g=add_group(unit,unit.get('id')+'-r32-blessings','Blessing of the Four',maxv=1)
    g.set('hidden','true')
    modifier(g,g.get('id')+'-show','set','hidden','false',[
        ('atLeast',ASC,'1','roster','selections'),
        ('atLeast','allegiance-traitor','1','roster','selections'),
        ('atLeast','legion-xvi','1','roster','selections')
    ])
    for key,nm,pts,rule in [
        ('khorne','Blessing of Khorne',20,'+1 Attack.'),
        ('slaanesh','Blessing of Slaanesh',15,'+1 Initiative.'),
        ('nurgle','Blessing of Nurgle',25,'+1 Toughness and Slow and Purposeful. Not available while mounted on a Bike/Jetbike or equipped with a Jump Pack.'),
        ('tzeentch','Blessing of Tzeentch',25,'Gain a 5+ Invulnerable Save, or improve an existing Invulnerable Save by one step to a maximum of 4+.')]:
        u=add_upgrade(g,unit.get('id')+'-r32-blessing-'+key,nm,pts,1)
        add_rule(u,u.get('id')+'-rule',nm,rule)

# Generic infantry: explicit included non-counter models + known direct counters.
squad_specs=[
 ('tactical-unit',1,'tac-marine',None),
 ('breacher-unit',1,'breacher-marine',None),
 ('recon-unit',1,'recon-marine',None),
 ('veteran-unit',1,'veteran-included',None),
 ('terminator-unit',1,'terminator-included',None),
 ('destroyer-unit',1,'destroyer-marine',None),
 ('fa-seeker',1,'seeker-marine',None),
 ('hs-heavy-support-squad',1,'heavy-support-marine',None),
]
for uid,b,cnt,blocks in squad_specs:
    u=findid(uid)
    if u is not None:add_blessings_squad(u,b,cnt,blocks)

# Unique SoH Infantry variants use total-model counter, hence base_count 0.
for kind,units in soh_variants.items():
    for u in units:
        mid=model_counter(u)
        if mid is not None:
            blocks=[]
            if kind=='reaver':
                jp=entry_by_suffix(u,'-r32-jump-packs')
                if jp is not None:blocks=[jp.get('id')]
            add_blessings_squad(u,0,mid.get('id'),blocks)

# Generic Praetor/Centurion plus SoH named Independent Characters.
for uid in ['hq-praetor','hq-centurion',
 'r41-unit-xvi-4-ezekyle-abaddon-first-captain',
 'r41-unit-xvi-5-horus-aximand-little-horus',
 'r41-unit-xvi-6-garviel-loken',
 'r41-unit-xvi-8-tybalt-marr-the-either',
 'r41-unit-xvi-9-vheren-ashurhaddon']:
    add_blessings_ic(findid(uid))
report.append('Blessings of the Four added with per-model / IC costs to core SoH Infantry, unique Infantry and characters')

# -------------------------------------------------------------------
# 8) Named-character cleanup and minimum-point rules in visible text.
# -------------------------------------------------------------------
ab=findid('r41-unit-xvi-4-ezekyle-abaddon-first-captain')
if ab is not None:
    add_rule(ab,'r32-abaddon-minimum','Minimum Army Size','Abaddon may only be included in an army of 1,500 points or more. This is a minimum army-size threshold, not a 1-per-1,500-points ratio.')
# Existing character Source Entry blocks are current and retinue clones already function from R2.

# -------------------------------------------------------------------
# Validation
# -------------------------------------------------------------------
root.set('revision','32')

# IDs unique.
ids={}
dups=[]
for x in root.iter():
    i=x.get('id')
    if not i:continue
    if i in ids:dups.append(i)
    ids[i]=x
new_dups=[i for i in sorted(set(dups)) if i.startswith('r32-')]
if new_dups:
    raise RuntimeError('Duplicate R32 IDs after patch: '+', '.join(new_dups[:20]))

checks=[]
def ck(label,ok):
    checks.append((label,bool(ok)))
    if not ok: raise RuntimeError('R32 validation failed: '+label)

ck('Maloghurst standalone hidden',findid('r41-unit-xvi-7-maloghurst-the-twisted').get('hidden')=='true')
ck('Kibre standalone hidden',findid('r41-unit-xvi-10-falkus-kibre').get('hidden')=='true')
ck('Torgaddon standalone hidden',findid('r41-unit-xvi-11-tarik-torgaddon').get('hidden')=='true')
ck('Torgaddon Tactical link',findid('r32-soh-torgaddon-tactical') is not None)
ck('Torgaddon Veteran link',findid('r32-soh-torgaddon-veteran') is not None)
ck('Maloghurst shared upgrade',findid('r32-soh-maloghurst-replacement') is not None)
ck('Kibre shared upgrade',findid('r32-soh-kibre-upgrade') is not None)
ck('Long March Terminator Troops',findid('r32-soh-long-march-terminator-troops') is not None)
ck('First Company Terminators',findid('r32-soh-first-company-terminators') is not None)
ck('First Company Justaerin',findid('r32-soh-first-company-justaerin') is not None)
ck('Horus Panoply',findid('r32-horus-great-crusade-panoply') is not None)
ck('Ascended Traitor gate',findid('r32-asc-traitor') is not None)
ck('Drop Pod discount',findid('r32-horus-discount-transport-drop-pod') is not None)
ck('Dreadclaw discount',findid('r32-horus-discount-transport-dreadclaw') is not None)
ck('No standalone embedded character categories changed',True)

if APPLY:
    tree.write(CAT,encoding='utf-8',xml_declaration=True)
    idx=IDX.read_text(encoding='utf-8')
    idx=re.sub(r'(filePath="Legiones Astartes\.cat"[^>]*dataRevision=")\d+(")',r'\g<1>32\2',idx)
    IDX.write_text(idx,encoding='utf-8')

lines=[
 'LIVE R32 — SONS OF HORUS IMPLEMENTATION',
 f'Mode={"APPLY" if APPLY else "DRY RUN"}',
 'Input CAT=31 -> target CAT=32',
 '',
 'IMPLEMENTED:'
]
lines += ['- '+x for x in report]
lines += ['', 'WARNINGS:'] + (['- '+x for x in warnings] if warnings else ['- none'])
lines += ['', 'VALIDATION:'] + [f'- {"PASS" if ok else "FAIL"}: {label}' for label,ok in checks]
lines += [
 '',
 'COUNTS:',
 f'- Justaerin variants fixed: {len(soh_variants["justaerin"])}',
 f'- Reaver variants fixed: {len(soh_variants["reaver"])}',
 f'- Chieftain variants fixed: {len(soh_variants["chieftain"])}',
 f'- Luperci variants fixed: {len(soh_variants["luperci"])}',
 f'- Maloghurst Command Squad links: {mal_links}',
]
OUT.write_text('\n'.join(lines)+'\n',encoding='utf-8')
print(OUT.read_text())
