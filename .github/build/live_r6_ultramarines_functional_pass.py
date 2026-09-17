from pathlib import Path
from copy import deepcopy
import re
import xml.etree.ElementTree as ET

CAT=Path('Legiones Astartes.cat'); IDX=Path('index.xml'); OUT=Path('inspection-live-r6-ultramarines-functional-pass.txt')
NS='http://www.battlescribe.net/schema/catalogueSchema'; ET.register_namespace('',NS); C=lambda t:f'{{{NS}}}{t}'
ct=ET.parse(CAT); root=ct.getroot()
if root.get('revision')!='5': raise RuntimeError(f'Expected CAT revision 5, got {root.get("revision")}')

def findid(i): return next((x for x in root.iter() if x.get('id')==i),None)
def ensure(p,t):
    x=p.find(C(t))
    if x is None: x=ET.SubElement(p,C(t))
    return x

def pts(e):
    c=e.find(C('costs'))
    if c is not None:
        for x in c.findall(C('cost')):
            if x.get('typeId')=='pts': return float(x.get('value','0'))
    return 0.0

def setpts(e,v):
    cs=ensure(e,'costs'); p=next((x for x in cs.findall(C('cost')) if x.get('typeId')=='pts'),None)
    if p is None: p=ET.SubElement(cs,C('cost'),{'name':'Points','typeId':'pts','value':str(v)})
    else: p.set('value',str(v)); p.set('name','Points')

def rule(e,id_,name,text):
    rs=ensure(e,'rules')
    for x in list(rs):
        if x.get('id')==id_: rs.remove(x)
    r=ET.SubElement(rs,C('rule'),{'id':id_,'name':name,'hidden':'false'}); ET.SubElement(r,C('description')).text=text

def addmax(e,val,id_):
    cs=ensure(e,'constraints')
    for x in list(cs):
        if x.get('type')=='max' and x.get('field')=='selections': cs.remove(x)
    ET.SubElement(cs,C('constraint'),{'id':id_,'type':'max','value':str(val),'field':'selections','scope':'parent','shared':'true','includeChildSelections':'true','includeChildForces':'false'})

def direct_model_entries(u):
    se=u.find(C('selectionEntries'))
    return [x for x in list(se or []) if x.tag==C('selectionEntry') and x.get('type')=='model']

def add_scaled_cost(e,per,model_ids,prefix):
    setpts(e,0)
    ms=ensure(e,'modifiers')
    for x in list(ms):
        if (x.get('id') or '').startswith(prefix): ms.remove(x)
    for n,mid in enumerate(model_ids):
        m=ET.SubElement(ms,C('modifier'),{'id':f'{prefix}-{n}','type':'increment','field':'pts','value':str(per)})
        reps=ET.SubElement(m,C('repeats'))
        ET.SubElement(reps,C('repeat'),{'field':'selections','scope':'root-entry','value':'1','percentValue':'false','shared':'true','includeChildSelections':'true','includeChildForces':'false','childId':mid,'repeats':'1','roundUp':'false'})

def hide_unless_selected(e,child_id,id_):
    ms=ensure(e,'modifiers')
    for x in list(ms):
        if x.get('id')==id_: ms.remove(x)
    m=ET.SubElement(ms,C('modifier'),{'id':id_,'type':'set','field':'hidden','value':'true'})
    conds=ET.SubElement(m,C('conditions'))
    ET.SubElement(conds,C('condition'),{'type':'lessThan','value':'1','field':'selections','scope':'parent','childId':child_id,'shared':'true','includeChildSelections':'true','includeChildForces':'false'})

def hide_unless_legion(e,legion='legion-xiii',id_='r6-um-only'):
    ms=ensure(e,'modifiers')
    m=ET.SubElement(ms,C('modifier'),{'id':id_,'type':'set','field':'hidden','value':'true'})
    conds=ET.SubElement(m,C('conditions'))
    ET.SubElement(conds,C('condition'),{'type':'lessThan','value':'1','field':'selections','scope':'roster','childId':legion,'shared':'true','includeChildSelections':'true','includeChildForces':'false'})

def group(u,name):
    gs=u.find(C('selectionEntryGroups'))
    if gs is None: return None
    return next((g for g in gs if (g.get('name') or '')==name),None)

def all_group_items(g):
    out=[]
    for cn in ('selectionEntries','entryLinks'):
        c=g.find(C(cn))
        if c is not None: out += list(c)
    return out

def strip_old_cost_note(e):
    rs=e.find(C('rules'))
    if rs is not None:
        for r in list(rs):
            if r.get('name')=='Squad-wide cost note': rs.remove(r)

log=[]
# 1. Make every source-defined whole-squad XIII upgrade actually scale to selected squad size.
WHOLE={
 'r41-unit-xiii-0-invictarus-suzerain-squad': {'Frag grenades':1,'Krak grenades':2,'Melta bombs':5},
 'r41-unit-xiii-2-locutarus-storm-squad': {'Krak grenades':2,'Melta bombs':5},
 'r41-unit-xiii-3-nemesis-destroyer-squad': {'Frag grenades':1,'Krak grenades':2,'Melta bombs':5},
}
for uid,opts in WHOLE.items():
    u=findid(uid)
    if u is None: raise RuntimeError('Missing '+uid)
    mids=[m.get('id') for m in direct_model_entries(u)]
    g=group(u,'Options')
    if g is None: raise RuntimeError('Missing Options for '+uid)
    for e in all_group_items(g):
        nm=e.get('name') or ''
        for key,per in opts.items():
            if nm.lower().startswith(key.lower()):
                e.set('name',f'{key} — entire squad (+{per} pt'+('s' if per!=1 else '')+'/model)')
                add_scaled_cost(e,per,mids,e.get('id')+'-r6scale')
                strip_old_cost_note(e)
                rule(e,e.get('id')+'-r6whole','Whole-squad upgrade',f'The entire squad takes {key} for +{per} point'+('s' if per!=1 else '')+' per model. New Recruit calculates the cost from the selected squad size.')
                log.append(f'whole-squad {uid}: {key} +{per}/model')

# 2. Fulmentarus grenade harness only exists if a Decurion was selected.
fu=findid('r41-unit-xiii-1-fulmentarus-terminator-squad')
if fu is None: raise RuntimeError('Fulmentarus missing')
g=group(fu,'Options')
items=all_group_items(g)
dec=next(x for x in items if 'Fulmentarus Decurion' in (x.get('name') or ''))
har=next(x for x in items if 'Grenade Harness' in (x.get('name') or ''))
hide_unless_selected(har,dec.get('id'),har.get('id')+'-r6needs-decurion')
log.append('Fulmentarus grenade harness gated behind Decurion')

# 3. Nemesis Sergeant chainsword replacements are mutually exclusive.
ne=findid('r41-unit-xiii-3-nemesis-destroyer-squad'); og=group(ne,'Options')
oldse=og.find(C('selectionEntries'))
repl=[]
if oldse is not None:
    for e in list(oldse):
        if (e.get('name') or '').lower() in ('rending weapon','power weapon','power fist','thunder hammer'):
            oldse.remove(e); repl.append(e)
if repl:
    sgs=ensure(og,'selectionEntryGroups')
    gid='r6-um-nemesis-sergeant-weapon'
    for x in list(sgs):
        if x.get('id')==gid: sgs.remove(x)
    sg=ET.SubElement(sgs,C('selectionEntryGroup'),{'id':gid,'name':'Nemesis Destroyer Sergeant — Chainsword Replacement','hidden':'false'})
    cs=ET.SubElement(sg,C('constraints'))
    ET.SubElement(cs,C('constraint'),{'id':gid+'-max','type':'max','value':'1','field':'selections','scope':'parent','shared':'true','includeChildSelections':'true','includeChildForces':'false'})
    dest=ET.SubElement(sg,C('selectionEntries'))
    for e in repl: dest.append(e)
    log.append('Nemesis Sergeant weapon replacements made mutually exclusive')

# 4. Aeonid Thiel is a Sergeant replacement, not a standalone unit.
thiel=findid('r41-unit-xiii-6-aeonid-thiel')
if thiel is None: raise RuntimeError('Thiel missing')
thiel.set('hidden','true')
for uid in ('tactical-unit','veteran-unit'):
    u=findid(uid)
    if u is None: raise RuntimeError('missing host '+uid)
    gs=ensure(u,'selectionEntryGroups')
    war=next((x for x in gs if (x.get('name') or '')=='Legion Wargear & Upgrades'),None)
    if war is None:
        war=ET.SubElement(gs,C('selectionEntryGroup'),{'id':'r6-'+uid+'-um-special','name':'Legion Wargear & Upgrades','hidden':'false'})
    se=ensure(war,'selectionEntries')
    nid='r6-'+uid+'-aeonid-thiel'
    for x in list(se):
        if x.get('id')==nid: se.remove(x)
    e=ET.SubElement(se,C('selectionEntry'),{'id':nid,'name':'Replace Sergeant with Aeonid Thiel','type':'upgrade','hidden':'false','import':'true'})
    setpts(e,80); addmax(e,1,nid+'-max')
    # roster-wide uniqueness shared across both host squads
    cs=ensure(e,'constraints'); ET.SubElement(cs,C('constraint'),{'id':nid+'-uniq','type':'max','value':'1','field':'selections','scope':'roster','shared':'true','includeChildSelections':'true','includeChildForces':'false'})
    hide_unless_legion(e,id_=nid+'-um-only')
    # copy Thiel profiles and rules so the actual roster contains his information
    for tag in ('profiles','rules'):
        src=thiel.find(C(tag))
        if src is not None: e.append(deepcopy(src))
    rule(e,nid+'-replace','Sergeant Replacement','Aeonid Thiel replaces this squad’s Sergeant for +80 points. Thiel remains part of the squad for the entire battle, is a Character but not an Independent Character, and does not occupy a separate Force Organisation slot.')
    log.append('Aeonid Thiel added as functional Sergeant replacement to '+uid)

# 5. Titus Prayto: clone the normal Librarian discipline/power selectors and allow two powers.
pray=findid('r41-unit-xiii-8-titus-prayto')
lib=findid('hq-librarian')
if pray is not None and lib is not None:
    pgs=ensure(pray,'selectionEntryGroups')
    # remove prior generated psychic groups
    for x in list(pgs):
        if (x.get('id') or '').startswith('r6-prayto-psychic-'): pgs.remove(x)
    lgs=lib.find(C('selectionEntryGroups'))
    candidates=[]
    if lgs is not None:
        for x in lgs:
            n=(x.get('name') or '').lower(); i=(x.get('id') or '')
            if 'psych' in n or 'discipline' in n or 'power' in n or i.startswith('r29-lib-'):
                candidates.append(x)
    # clone with recursive ID remap so internal visibility references survive
    def clone_remap(src,prefix):
        cl=deepcopy(src); mp={}
        for x in cl.iter():
            if x.get('id'): mp[x.get('id')]=prefix+x.get('id')
        for x in cl.iter():
            if x.get('id') in mp: x.set('id',mp[x.get('id')])
            if x.get('childId') in mp: x.set('childId',mp[x.get('childId')])
        return cl,mp
    for c in candidates:
        cl,mp=clone_remap(c,'r6-prayto-psychic-')
        # power selector is identified by original r29-lib-power-group
        if c.get('id')=='r29-lib-power-group':
            cons=cl.find(C('constraints'))
            if cons is not None:
                for q in cons:
                    if q.get('type')=='max' and q.get('field')=='selections': q.set('value','2')
                    if q.get('type')=='min' and q.get('field')=='selections': q.set('value','2')
        pgs.append(cl)
    if candidates: log.append(f'Titus Prayto psychic selectors cloned from Librarian ({len(candidates)} groups), power count set to 2')
    else: log.append('WARNING: no Librarian psychic selector groups found for Prayto')
else:
    log.append('WARNING: Prayto or generic Librarian entry not found')

# 6. Guilliman Primarch Retinue: real selector, not text-only.
gui=findid('r41-unit-xiii-9-xiii-roboute-guilliman-the-avenging-son')
if gui is not None:
    gs=ensure(gui,'selectionEntryGroups'); gid='r6-guilliman-retinue'
    for x in list(gs):
        if x.get('id')==gid: gs.remove(x)
    rg=ET.SubElement(gs,C('selectionEntryGroup'),{'id':gid,'name':'Primarch Retinue (does not occupy a separate FOC slot)','hidden':'false'})
    cs=ET.SubElement(rg,C('constraints')); ET.SubElement(cs,C('constraint'),{'id':gid+'-max','type':'max','value':'1','field':'selections','scope':'parent','shared':'true','includeChildSelections':'true','includeChildForces':'false'})
    dest=ET.SubElement(rg,C('selectionEntries'))
    # Find reusable concrete unit definitions by name, favouring generic top-level units.
    wanted=['LEGION HONOUR GUARD SQUAD','Legion Terminator Command Squad','INVICTARUS SUZERAIN SQUAD']
    for n,w in enumerate(wanted):
        src=next((x for x in root.iter(C('selectionEntry')) if x.get('type')=='unit' and (x.get('name') or '').strip().upper()==w.upper() and not (x.get('id') or '').startswith('live-r')),None)
        if src is None:
            # fall back to any matching clone
            src=next((x for x in root.iter(C('selectionEntry')) if x.get('type')=='unit' and (x.get('name') or '').strip().upper()==w.upper()),None)
        if src is None:
            log.append('WARNING Guilliman retinue source missing: '+w); continue
        cl=deepcopy(src); prefix=f'r6-guilliman-ret-{n}-'
        idmap={}
        for x in cl.iter():
            if x.get('id'): idmap[x.get('id')]=prefix+x.get('id')
        for x in cl.iter():
            if x.get('id') in idmap: x.set('id',idmap[x.get('id')])
            if x.get('childId') in idmap: x.set('childId',idmap[x.get('childId')])
        addmax(cl,1,prefix+'max')
        rule(cl,prefix+'ret-rule','Primarch Retinue','Selected as Roboute Guilliman’s Primarch Retinue. It occupies no additional Force Organisation selection and otherwise follows the normal Primarch Retinue rules.')
        dest.append(cl); log.append('Guilliman retinue option added: '+w)

# 7. Combat Squads: add a real selectable reminder only for Ultramarines Tactical Squads; selection is hidden unless the squad is exactly 10 models.
tac=findid('tactical-unit')
if tac is not None:
    gs=ensure(tac,'selectionEntryGroups'); war=next((x for x in gs if (x.get('name') or '')=='Legion Wargear & Upgrades'),None)
    if war is None: war=ET.SubElement(gs,C('selectionEntryGroup'),{'id':'r6-tac-um-specials','name':'Legion Wargear & Upgrades','hidden':'false'})
    se=ensure(war,'selectionEntries'); nid='r6-um-combat-squads'
    for x in list(se):
        if x.get('id')==nid: se.remove(x)
    e=ET.SubElement(se,C('selectionEntry'),{'id':nid,'name':'Combat Squads — split 10 models into two squads of 5','type':'upgrade','hidden':'false','import':'true'})
    setpts(e,0); addmax(e,1,nid+'-max'); hide_unless_legion(e,id_=nid+'-um-only')
    # Hide unless total tactical models == 10; model ids are known from live catalogue.
    ms=ensure(e,'modifiers')
    for mode,val in [('lessThan','10'),('atLeast','11')]:
        m=ET.SubElement(ms,C('modifier'),{'id':nid+'-'+mode,'type':'set','field':'hidden','value':'true'})
        cgs=ET.SubElement(m,C('conditionGroups')); cg=ET.SubElement(cgs,C('conditionGroup'),{'type':'or'}); conds=ET.SubElement(cg,C('conditions'))
        # We need combined count. BattleScribe conditions cannot sum two child IDs directly, so use roster entry child counts via two model-specific tests.
        # Tactical squad always has exactly one Sergeant; therefore Marine count must be 9 for a ten-model squad.
        if mode=='lessThan':
            ET.SubElement(conds,C('condition'),{'type':'lessThan','value':'9','field':'selections','scope':'parent','childId':'tac-marine','shared':'true','includeChildSelections':'true','includeChildForces':'false'})
        else:
            ET.SubElement(conds,C('condition'),{'type':'atLeast','value':'10','field':'selections','scope':'parent','childId':'tac-marine','shared':'true','includeChildSelections':'true','includeChildForces':'false'})
    rule(e,nid+'-rule','Codex Astartes — Combat Squads','A Legion Tactical Squad consisting of exactly ten models may be divided into two Combat Squads of five models each before deployment. After division, each Combat Squad is treated as a separate unit for all game purposes. If the original squad has a Dedicated Transport, assign it to one Combat Squad; only that squad may begin embarked.')
    log.append('Codex Astartes Combat Squads selector added for exact 10-model Tactical Squads')

root.set('revision','6'); ct.write(CAT,encoding='utf-8',xml_declaration=True)
idx=IDX.read_text(encoding='utf-8'); idx=re.sub(r'(filePath="Legiones Astartes\.cat"[^>]*dataRevision=")\d+("\s*/>)',r'\g<1>6\2',idx); IDX.write_text(idx,encoding='utf-8')
OUT.write_text('LIVE R6 — ULTRAMARINES FUNCTIONAL PASS\nCAT=6 GSTref='+str(root.get('gameSystemRevision'))+'\n\n'+'\n'.join('• '+x for x in log),encoding='utf-8')
print(OUT.read_text())
