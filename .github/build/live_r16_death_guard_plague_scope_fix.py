from pathlib import Path
import re
import xml.etree.ElementTree as ET

CAT=Path('Legiones Astartes.cat'); IDX=Path('index.xml'); OUT=Path('inspection-live-r16-death-guard-plague-scope-fix.txt')
NS='http://www.battlescribe.net/schema/catalogueSchema'; ET.register_namespace('',NS); C=lambda t:f'{{{NS}}}{t}'
ct=ET.parse(CAT); root=ct.getroot()
if root.get('revision')!='15': raise RuntimeError(f'Expected CAT 15, got {root.get("revision")}')

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
def setmax(e,val,id_):
    cs=ensure(e,'constraints')
    for x in list(cs):
        if x.get('id')==id_: cs.remove(x)
    ET.SubElement(cs,C('constraint'),{'id':id_,'type':'max','value':str(val),'field':'selections','scope':'parent','shared':'true','includeChildSelections':'true','includeChildForces':'false'})
def hide_unless_roster(e,child_id,id_):
    ms=ensure(e,'modifiers')
    m=ET.SubElement(ms,C('modifier'),{'id':id_,'type':'set','field':'hidden','value':'true'})
    cs=ET.SubElement(m,C('conditions'))
    ET.SubElement(cs,C('condition'),{'type':'lessThan','value':'1','field':'selections','scope':'roster','childId':child_id,'shared':'true','includeChildSelections':'true','includeChildForces':'true'})
def hide_if_root_selection(e,child_id,id_):
    ms=ensure(e,'modifiers')
    m=ET.SubElement(ms,C('modifier'),{'id':id_,'type':'set','field':'hidden','value':'true'})
    cs=ET.SubElement(m,C('conditions'))
    ET.SubElement(cs,C('condition'),{'type':'atLeast','value':'1','field':'selections','scope':'root-entry','childId':child_id,'shared':'true','includeChildSelections':'true','includeChildForces':'false'})
def direct_models(unit):
    se=unit.find(C('selectionEntries'))
    if se is None:return []
    return [x for x in se if x.get('type')=='model']
def set_points(e,val):
    costs=ensure(e,'costs'); p=next((x for x in costs if x.get('typeId')=='pts'),None)
    if p is None: ET.SubElement(costs,C('cost'),{'name':'Points','typeId':'pts','value':str(val)})
    else: p.set('value',str(val))
def add_scaled(e,per,models,prefix):
    set_points(e,0); ms=ensure(e,'modifiers')
    for i,m in enumerate(models):
        mod=ET.SubElement(ms,C('modifier'),{'id':f'{prefix}-{i}','type':'increment','field':'pts','value':str(per)})
        reps=ET.SubElement(mod,C('repeats'))
        ET.SubElement(reps,C('repeat'),{'field':'selections','scope':'root-entry','value':'1','percentValue':'false','shared':'true','includeChildSelections':'true','includeChildForces':'false','childId':m.get('id'),'repeats':'1','roundUp':'false'})
def remove_r15_groups():
    removed=0
    for p in root.iter():
        gs=p.find(C('selectionEntryGroups'))
        if gs is None: continue
        for g in list(gs):
            if (g.get('id') or '').startswith('r15-dg-plague-group-'):
                gs.remove(g); removed+=1
    return removed

def disqualifier_ids(unit):
    ids=[]
    needles=('terminator armour','cataphractii','tartaros','recon armour','jump pack','space marine bike','jetbike')
    for x in unit.iter():
        if x is unit: continue
        nm=(x.get('name') or '').lower()
        if x.get('id') and any(n in nm for n in needles): ids.append(x.get('id'))
    return list(dict.fromkeys(ids))

def add_plague(unit,fixed_character=False):
    uid=unit.get('id'); gs=ensure(unit,'selectionEntryGroups'); gid='r16-dg-plague-group-'+uid
    g=ET.SubElement(gs,C('selectionEntryGroup'),{'id':gid,'name':'Sons of the Plague Father','hidden':'false'})
    se=ET.SubElement(g,C('selectionEntries'))
    eid='r16-dg-plague-'+uid
    up=ET.SubElement(se,C('selectionEntry'),{'id':eid,'name':'Upgrade to Plague Marines (+7 pts/model)','type':'upgrade','hidden':'false','import':'true'})
    setmax(up,1,eid+'-max'); hide_unless_roster(up,DAEMON,eid+'-mortarion')
    for j,did in enumerate(disqualifier_ids(unit)): hide_if_root_selection(up,did,f'{eid}-disq-{j}')
    models=direct_models(unit)
    if models: add_scaled(up,7,models,eid+'-cost')
    elif fixed_character: set_points(up,7)
    else: return False,0
    set_rule(up,eid+'-rule','Plague Marines','Every model in this unit is upgraded for +7 points per model. Models gain +1 Toughness, Feel No Pain (5+) and Slow and Purposeful. They may not benefit from Move Through Cover, their normal maximum charge distance is 5 inches, and they may not benefit from rules that increase their Movement or charge distance. The Relentless component of Slow and Purposeful applies normally.')
    return True,len(models)

DAEMON='r41-unit-xiv-9-mortarion-prince-of-decay'
removed=remove_r15_groups(); log=[f'Removed {removed} over-broad R15 Plague Marine selector groups before rebuilding the rule with proper scope.']

# Base Legion squads that are Infantry and wear Power/Artificer Armour in their normal configuration.
base_ids=[
 'tactical-unit','assault-unit','breacher-unit','recon-unit','veteran-unit','destroyer-unit','fa-seeker','hs-heavy-support-squad',
 'hq-praetor-ret-honour','hq-centurion-ret-command',
 'r41-unit-xiv-2-mortus-poisoner-squad',
 'r42-role-xiv-0-effects-superior-firepower-legion-veteran-squads-veteran-unit',
 'r42-role-xiv-0-legion-heavy-support-squads-hs-heavy-support-squad'
]
patched=[]
for i in base_ids:
    u=findid(i)
    if u is None: continue
    ok,c=add_plague(u,False)
    if ok: patched.append((i,u.get('name') or '',c))

# Death Guard-specific retinue copies of otherwise eligible Power/Artificer-armoured squads.
for u in root.iter(C('selectionEntry')):
    i=u.get('id') or ''; nm=(u.get('name') or '')
    if u.get('type')!='unit' or i in base_ids: continue
    if 'r41-unit-xiv-' not in i and 'dg-' not in i: continue
    if nm not in ('Legion Command Squad','Legion Honour Guard Squad','MORTUS POISONER SQUAD'): continue
    if direct_models(u):
        ok,c=add_plague(u,False)
        if ok: patched.append((i,nm,c))

# Infantry characters are also units under the literal Sons of the Plague Father wording; add a fixed +7 option.
# Terminator/Recon/Jump/Bike armour or movement choices dynamically hide the upgrade.
character_ids=['hq-praetor','hq-centurion','r41-unit-xiv-4-crysos-morturg','r41-unit-xiv-5-durak-rask','r41-unit-xiv-6-ignatius-grulgor','r41-unit-xiv-7-nathaniel-garro']
for i in character_ids:
    u=findid(i)
    if u is None: continue
    ok,c=add_plague(u,True)
    if ok: patched.append((i,u.get('name') or '',c))

log.append('Rebuilt Sons of the Plague Father only on Death Guard-accessible Power/Artificer-armoured Infantry units and characters.')
log.append('Recon Armour, Terminator Armour, Jump Pack, Bike and Jetbike choices dynamically hide the upgrade because the model/unit is no longer eligible under the written rule.')
log.append('Squad costs use only the unit’s direct squad-member model selections, so retinues/transports are never accidentally counted.')
log.append(f'Patched entries: {len(patched)}')
for i,n,c in patched: log.append(f'  + {i} | {n} | direct squad model entries={c}' if c else f'  + {i} | {n} | single-character +7 upgrade')

root.set('revision','16'); ct.write(CAT,encoding='utf-8',xml_declaration=True)
idx=IDX.read_text(encoding='utf-8'); idx=re.sub(r'(filePath="Legiones Astartes\.cat"[^>]*dataRevision=")\d+("\s*/>)',r'\g<1>16\2',idx); IDX.write_text(idx,encoding='utf-8')
OUT.write_text('LIVE R16 — DEATH GUARD PLAGUE MARINE SCOPE FIX\nCAT=16 GSTref='+str(root.get('gameSystemRevision'))+'\n\n'+'\n'.join('• '+x for x in log),encoding='utf-8')
print(OUT.read_text(encoding='utf-8'))