from pathlib import Path
from copy import deepcopy
import os
import re
import xml.etree.ElementTree as ET

CAT=Path('Legiones Astartes.cat')
GST=Path('Prohammer 30k.gst')
IDX=Path('index.xml')
OUT=Path('inspection-r18-thousand-sons-core-dry-run.txt')
APPLY=os.environ.get('TS_APPLY','0')=='1'

CNS='http://www.battlescribe.net/schema/catalogueSchema'
GNS='http://www.battlescribe.net/schema/gameSystemSchema'
ET.register_namespace('',CNS)
C=lambda t:f'{{{CNS}}}{t}'
G=lambda t:f'{{{GNS}}}{t}'

ct=ET.parse(CAT); root=ct.getroot()
gt=ET.parse(GST); groot=gt.getroot()
if root.get('revision')!='17':
    raise RuntimeError(f'Expected live catalogue revision 17, got {root.get("revision")}')

def findid(r,id_):
    return next((x for x in r.iter() if x.get('id')==id_),None)

def ensure(p,tag,ns=C):
    x=p.find(ns(tag))
    if x is None: x=ET.SubElement(p,ns(tag))
    return x

def setpts(e,v):
    cs=ensure(e,'costs')
    p=next((x for x in cs.findall(C('cost')) if x.get('typeId')=='pts'),None)
    if p is None:
        p=ET.SubElement(cs,C('cost'),{'name':'Points','typeId':'pts','value':str(v)})
    else:
        p.set('name','Points'); p.set('value',str(v))

def remove_constraints(e, pred):
    cs=e.find(C('constraints'))
    if cs is not None:
        for x in list(cs):
            if pred(x): cs.remove(x)

def add_constraint(e,id_,typ,val,scope='parent',field='selections',ns=C):
    cs=ensure(e,'constraints',ns)
    for x in list(cs):
        if x.get('id')==id_: cs.remove(x)
    return ET.SubElement(cs,ns('constraint'),{
        'id':id_,'type':typ,'value':str(val),'field':field,'scope':scope,
        'shared':'true','includeChildSelections':'true','includeChildForces':'false'
    })

def roster_max1(e,id_):
    remove_constraints(e,lambda x:x.get('id')==id_)
    add_constraint(e,id_,'max',1,'roster')

def add_modifier(e,id_,typ,field,value,conditions=None,condition_groups=None,ns=C):
    ms=ensure(e,'modifiers',ns)
    for x in list(ms):
        if x.get('id')==id_: ms.remove(x)
    m=ET.SubElement(ms,ns('modifier'),{'id':id_,'type':typ,'field':field,'value':str(value)})
    if conditions:
        cs=ET.SubElement(m,ns('conditions'))
        for c in conditions: ET.SubElement(cs,ns('condition'),c)
    if condition_groups:
        cgs=ET.SubElement(m,ns('conditionGroups'))
        for gtyp,conds in condition_groups:
            cg=ET.SubElement(cgs,ns('conditionGroup'),{'type':gtyp})
            cs=ET.SubElement(cg,ns('conditions'))
            for c in conds: ET.SubElement(cs,ns('condition'),c)
    return m

def cond(typ,val,child,scope='roster',field='selections'):
    return {'type':typ,'value':str(val),'field':field,'scope':scope,'childId':child,
            'shared':'true','includeChildSelections':'true','includeChildForces':'false'}

def direct_groups(e):
    c=e.find(C('selectionEntryGroups'))
    return list(c) if c is not None else []

def group_named(e,name):
    return next((g for g in direct_groups(e) if (g.get('name') or '')==name),None)

def direct_entries(e):
    c=e.find(C('selectionEntries'))
    return list(c) if c is not None else []

def find_link_to(e,target):
    return next((x for x in e.iter(C('entryLink')) if x.get('targetId')==target),None)

def prefix_clone(src,prefix):
    cl=deepcopy(src); mp={}
    for x in cl.iter():
        if x.get('id'): mp[x.get('id')]=prefix+x.get('id')
    for x in cl.iter():
        if x.get('id') in mp: x.set('id',mp[x.get('id')])
        if x.get('childId') in mp: x.set('childId',mp[x.get('childId')])
        if x.get('field') in mp: x.set('field',mp[x.get('field')])
    return cl

def strip_categories(e):
    for x in e.iter():
        c=x.find(C('categoryLinks'))
        if c is not None: x.remove(c)

def set_group_minmax(g,minv,maxv,prefix):
    cs=g.find(C('constraints'))
    if cs is not None: g.remove(cs)
    cs=ET.SubElement(g,C('constraints'))
    ET.SubElement(cs,C('constraint'),{
        'id':prefix+'-min','type':'min','value':str(minv),'field':'selections','scope':'parent',
        'shared':'true','includeChildSelections':'true','includeChildForces':'false'})
    ET.SubElement(cs,C('constraint'),{
        'id':prefix+'-max','type':'max','value':str(maxv),'field':'selections','scope':'parent',
        'shared':'true','includeChildSelections':'true','includeChildForces':'false'})
    return prefix+'-min',prefix+'-max'

def add_power_group(host,gid,name,allowed=None,gate_ids=None,cult_map=None,source_group_id='r61-librarian-power1'):
    src=findid(root,source_group_id)
    if src is None: raise RuntimeError('Missing psychic source group '+source_group_id)
    gs=ensure(host,'selectionEntryGroups')
    for x in list(gs):
        if x.get('id')==gid: gs.remove(x)
    cl=prefix_clone(src,gid+'-clone-')
    cl.set('id',gid); cl.set('name',name); cl.set('hidden','false')
    strip_categories(cl)
    ses=cl.find(C('selectionEntries'))
    if ses is None: raise RuntimeError('Psychic source has no entries')
    if allowed:
        allowed_lower=[a.lower() for a in allowed]
        for x in list(ses):
            n=(x.get('name') or '').lower()
            if not any(n.startswith(a+' —') or n.startswith(a+' -') for a in allowed_lower):
                ses.remove(x)
    minid,maxid=set_group_minmax(cl,0 if gate_ids else 1,1,gid)
    oldmods=cl.find(C('modifiers'))
    if oldmods is not None: cl.remove(oldmods)
    if gate_ids:
        add_modifier(cl,gid+'-hide','set','hidden','true',
                     condition_groups=[('and',[cond('lessThan',1,i,'root-entry') for i in gate_ids])])
        add_modifier(cl,gid+'-min-on','set',minid,'1',
                     condition_groups=[('or',[cond('atLeast',1,i,'root-entry') for i in gate_ids])])
    if cult_map:
        for x in list(ses):
            n=(x.get('name') or '')
            disc=n.split('—',1)[0].split('-',1)[0].strip()
            cult_id=cult_map.get(disc)
            if cult_id:
                add_modifier(x,x.get('id')+'-cult-gate','set','hidden','true',
                             conditions=[cond('lessThan',1,cult_id,'root-entry')])
    gs.append(cl)
    return cl

def make_subgroup(parent,entry_ids,gid,name,base_max,model_id=None,at10_max=None):
    ses=parent.find(C('selectionEntries'))
    if ses is None: raise RuntimeError(f'{parent.get("id")} lacks selectionEntries')
    moved=[]
    for x in list(ses):
        if x.get('id') in entry_ids:
            ses.remove(x); moved.append(x)
    if len(moved)!=len(entry_ids):
        got={x.get('id') for x in moved}; missing=[i for i in entry_ids if i not in got]
        raise RuntimeError(f'Missing entries for subgroup {gid}: {missing}')
    sgs=ensure(parent,'selectionEntryGroups')
    for x in list(sgs):
        if x.get('id')==gid: sgs.remove(x)
    g=ET.SubElement(sgs,C('selectionEntryGroup'),{'id':gid,'name':name,'hidden':'false'})
    maxid=gid+'-max'
    add_constraint(g,maxid,'max',base_max,'parent')
    if model_id and at10_max is not None:
        add_modifier(g,gid+'-max10','set',maxid,str(at10_max),
                     conditions=[cond('atLeast',10,model_id,'root-entry')])
    dest=ET.SubElement(g,C('selectionEntries'))
    for x in moved: dest.append(x)
    return g

def add_scaled_option(e,per,model_id,prefix,label=None):
    if label: e.set('name',label)
    setpts(e,0)
    ms=ensure(e,'modifiers')
    for x in list(ms):
        if (x.get('id') or '').startswith(prefix): ms.remove(x)
    m=ET.SubElement(ms,C('modifier'),{'id':prefix+'-pts','type':'increment','field':'pts','value':str(per)})
    reps=ET.SubElement(m,C('repeats'))
    ET.SubElement(reps,C('repeat'),{
        'field':'selections','scope':'root-entry','value':'1','percentValue':'false',
        'shared':'true','includeChildSelections':'true','includeChildForces':'false',
        'childId':model_id,'repeats':'1','roundUp':'false'
    })

def fix_cult(host,cult):
    g=next((x for x in direct_groups(host) if (x.get('name') or '')=='Prosperine Cult'),None)
    if g is None: raise RuntimeError('Missing Prosperine Cult group on '+host.get('id'))
    g.set('name','Prosperine Cult — fixed')
    chosen=None
    ses=g.find(C('selectionEntries'))
    for x in list(ses) if ses is not None else []:
        remove_constraints(x,lambda c:c.get('type')=='min')
        if (x.get('name') or '').lower()==cult.lower():
            x.set('hidden','false'); chosen=x
            add_constraint(x,x.get('id')+'-r18-fixed-min','min',1,'parent')
        else:
            x.set('hidden','true')
    if chosen is None: raise RuntimeError(f'Cult {cult} not found on {host.get("id")}')
    return chosen.get('id')

def add_min_points_gate(e,points,prefix):
    add_modifier(e,prefix+'-hide-under','set','hidden','true',
                 condition_groups=[('and',[
                     cond('greaterThan',0,'model','roster','limit::pts'),
                     cond('lessThan',points,'model','roster','limit::pts')
                 ])])

def add_gst_set_modifier(link,id_,field,value,child):
    return add_modifier(link,id_,'set',field,value,
                        conditions=[cond('atLeast',1,child,'roster')],ns=G)

log=[]

# 1. PRICE OF KNOWLEDGE + FELLOWSHIPS force chart
force=findid(groot,'force-standard')
if force is None: raise RuntimeError('Missing Standard Age of Darkness Detachment')
for lid,value in [('fl-hq',3),('fl-elites',4),('fl-fast',2)]:
    link=findid(groot,lid)
    if link is None: raise RuntimeError('Missing FOC link '+lid)
    field={'fl-hq':'fl-hq-max','fl-elites':'fl-elites-max','fl-fast':'fl-fast-max'}[lid]
    add_gst_set_modifier(link,'r18-ts-'+lid+'-max',field,value,'legion-xv')
flfast=findid(groot,'fl-fast')
add_gst_set_modifier(flfast,'r18-ts-fellowships-fast-max','fl-fast-max',1,'r25-rite-xv-2-the-fellowships-of-prospero')
log.append('FOC: Price of Knowledge = HQ 1-3, Elites 0-4, Fast Attack 0-2; Fellowships Fast Attack max 1')

# Hidden Brotherhood count category for Fellowships' at-least-two requirement.
cats=ensure(groot,'categoryEntries',G)
if findid(groot,'r18-ts-cat-brotherhood') is None:
    ET.SubElement(cats,G('categoryEntry'),{'id':'r18-ts-cat-brotherhood','name':'Thousand Sons Psychic Brotherhood','hidden':'true'})
for sid in ('r45-ts-brotherhood','r45-ts-brotherhood-fellowship','r45-ts-tactical-brotherhood'):
    s=findid(root,sid)
    if s is None: raise RuntimeError('Missing Brotherhood shared entry '+sid)
    cls=ensure(s,'categoryLinks')
    for old in list(cls):
        if old.get('id')=='r18-ts-brotherhood-cat-'+sid: cls.remove(old)
    ET.SubElement(cls,C('categoryLink'),{
        'id':'r18-ts-brotherhood-cat-'+sid,'name':'Thousand Sons Psychic Brotherhood',
        'hidden':'false','targetId':'r18-ts-cat-brotherhood','primary':'false'})
fcls=ensure(force,'categoryLinks',G)
old=next((x for x in fcls if x.get('id')=='r18-ts-brotherhood-limit'),None)
if old is not None: fcls.remove(old)
bcl=ET.SubElement(fcls,G('categoryLink'),{
    'id':'r18-ts-brotherhood-limit','name':'Fellowships — Psychic Brotherhoods',
    'hidden':'true','targetId':'r18-ts-cat-brotherhood'})
add_constraint(bcl,'r18-ts-brotherhood-min','min',0,'parent',field='selections',ns=G)
add_modifier(bcl,'r18-ts-brotherhood-min-fellowships','set','r18-ts-brotherhood-min',2,
             conditions=[cond('atLeast',1,'r25-rite-xv-2-the-fellowships-of-prospero','roster')],ns=G)
log.append('Fellowships: hidden roster validator requires at least 2 Psychic Brotherhood selections')

# 2. Generic Veteran / Terminator / Tactical Brotherhoods + powers
cult_disc={'Biomancy':'Pavoni','Telekinesis':'Raptora','Divination':'Corvidae','Telepathy':'Athanaeans','Pyromancy':'Pyrae'}
for uid in ('veteran-unit','terminator-unit'):
    u=findid(root,uid)
    normal=find_link_to(u,'r45-ts-brotherhood')
    fellow=find_link_to(u,'r45-ts-brotherhood-fellowship')
    if normal is None or fellow is None: raise RuntimeError('Missing Brotherhood links on '+uid)
    add_modifier(normal,'r18-ts-'+uid+'-normal-hide-fellow','set','hidden','true',
                 conditions=[cond('atLeast',1,'r25-rite-xv-2-the-fellowships-of-prospero','roster')])
    add_modifier(fellow,'r18-ts-'+uid+'-fellow-hide-normal','set','hidden','true',
                 conditions=[cond('lessThan',1,'r25-rite-xv-2-the-fellowships-of-prospero','roster')])
    cultg=findid(root,'r45-cult-'+uid)
    if cultg is None: raise RuntimeError('Missing cult group on '+uid)
    cs=cultg.find(C('selectionEntries'))
    choices={x.get('name'):x.get('id') for x in list(cs) if cs is not None}
    cmap={d:choices[c] for d,c in cult_disc.items()}
    add_power_group(u,'r18-ts-'+uid+'-brotherhood-power',
                    'Psychic Power — selected Prosperine Cult discipline',
                    gate_ids=[normal.get('id'),fellow.get('id')],cult_map=cmap)
    log.append(uid+': normal/Fellowships Brotherhood pricing gated; one Cult-linked power selector added')

tac=findid(root,'tactical-unit')
tlink=find_link_to(tac,'r45-ts-tactical-brotherhood')
if tlink is None: raise RuntimeError('Missing Tactical Brotherhood link')
add_modifier(tlink,'r18-ts-tactical-brotherhood-rite','set','hidden','true',
             conditions=[cond('lessThan',1,'r25-rite-xv-2-the-fellowships-of-prospero','roster')])
tm=None; tmmax=-1
for m in direct_entries(tac):
    if m.get('type')!='model': continue
    cons=m.find(C('constraints'))
    for c in list(cons) if cons is not None else []:
        if c.get('type')=='max':
            try: v=int(float(c.get('value')))
            except: continue
            if v>tmmax: tm=m; tmmax=v
if tm is None: raise RuntimeError('Could not identify Tactical scalable model')
add_modifier(tlink,'r18-ts-tactical-brotherhood-size','set','hidden','true',
             conditions=[cond('lessThan',tmmax,tm.get('id'),'root-entry')])
cultg=findid(root,'r45-cult-tactical-unit')
cs=cultg.find(C('selectionEntries'))
choices={x.get('name'):x.get('id') for x in list(cs) if cs is not None}
cmap={d:choices[c] for d,c in cult_disc.items()}
add_power_group(tac,'r18-ts-tactical-brotherhood-power',
                'Psychic Power — selected Prosperine Cult discipline',
                gate_ids=[tlink.get('id')],cult_map=cmap)
log.append(f'Tactical: Brotherhood gated to Fellowships + maximum 20-model squad ({tm.get("id")}={tmmax}); Cult-linked power selector added')

# 3. Unique XV formations: 0-1, shared weapon caps, whole-squad costs
unique_ids=[
 'r41-unit-xv-0-sekhmet-terminator-cabal',
 'r41-unit-xv-1-khenetai-occult-blade-cabal',
 'r41-unit-xv-2-ammitara-occult-intercession-cabal',
 'r41-unit-xv-3-castellax-achea-maniple',
 'r41-unit-xv-4-contemptor-osiron-dreadnought',
 'r41-unit-xv-5-numerologist-cabal',
]
for uid in unique_ids:
    u=findid(root,uid)
    if u is None: raise RuntimeError('Missing XV unique unit '+uid)
    roster_max1(u,'r18-ts-'+uid+'-01')
log.append('Unique formations: Sekhmet, Khenetai, Ammitara, Castellax-Achea, Osiron and Numerologist all enforced 0-1')

sek=findid(root,'r41-unit-xv-0-sekhmet-terminator-cabal')
sekopt=group_named(sek,'Options'); sekmodel=findid(root,'r41-unit-xv-0-sekhmet-terminator-cabal-additional')
make_subgroup(sekopt,[
 'r41-unit-xv-0-sekhmet-terminator-cabal-opt-0-power-fist',
 'r41-unit-xv-0-sekhmet-terminator-cabal-opt-1-chainfist'],
 'r18-ts-sekhmet-force-replacements','Prosperine Force Weapon replacements — any model',5,sekmodel.get('id'),10)
make_subgroup(sekopt,[
 'r41-unit-xv-0-sekhmet-terminator-cabal-opt-2-heavy-flamer',
 'r41-unit-xv-0-sekhmet-terminator-cabal-opt-3-plasma-blaster',
 'r41-unit-xv-0-sekhmet-terminator-cabal-opt-4-reaper-autocannon'],
 'r18-ts-sekhmet-heavy-replacements','Foeblaster replacements — up to 2 per 5 models',2,sekmodel.get('id'),4)
add_power_group(sek,'r18-ts-sekhmet-power','Psychic Power — select 1',
                allowed=['Biomancy','Divination','Pyromancy','Telekinesis','Telepathy'])
log.append('Sekhmet: combined Force-weapon replacement cap = squad size; combined heavy-weapon cap = 2/5 or 4/10; one psychic power selector')

khe=findid(root,'r41-unit-xv-1-khenetai-occult-blade-cabal')
kopt=group_named(khe,'Options'); kmodel=findid(root,'r41-unit-xv-1-khenetai-occult-blade-cabal-additional')
make_subgroup(kopt,[
 'r41-unit-xv-1-khenetai-occult-blade-cabal-opt-1-hand-flamer',
 'r41-unit-xv-1-khenetai-occult-blade-cabal-opt-2-plasma-pistol'],
 'r18-ts-khenetai-sidearms','Sidearms — 1 per 5 models',1,kmodel.get('id'),2)
for oid,per,label in [
 ('r41-unit-xv-1-khenetai-occult-blade-cabal-opt-3-krak-grenades',2,'Krak grenades — entire Cabal (+2 pts/model)'),
 ('r41-unit-xv-1-khenetai-occult-blade-cabal-opt-4-melta-bombs',5,'Melta bombs — entire Cabal (+5 pts/model)')]:
    add_scaled_option(findid(root,oid),per,kmodel.get('id'),'r18-ts-khenetai-scale-',label)
log.append('Khenetai: Hand Flamer/Plasma Pistol share 1-per-5 cap; Krak/Melta Bomb whole-Cabal costs scale with 5-10 models')

amm=findid(root,'r41-unit-xv-2-ammitara-occult-intercession-cabal')
aopt=group_named(amm,'Options'); amodel=findid(root,'r41-unit-xv-2-ammitara-occult-intercession-cabal-additional')
repids=[f'r41-unit-xv-2-ammitara-occult-intercession-cabal-opt-{i}-'+s for i,s in [
 (0,'combi-flamer'),(1,'combi-volkite-charger'),(2,'combi-meltagun'),(3,'combi-plasma-gun'),(4,'meltagun'),(5,'plasma-gun')]]
repg=make_subgroup(aopt,repids,'r18-ts-ammitara-sniper-replacements','Sniper Rifle replacements — one per model',5,amodel.get('id'),10)
make_subgroup(repg,[
 'r41-unit-xv-2-ammitara-occult-intercession-cabal-opt-4-meltagun',
 'r41-unit-xv-2-ammitara-occult-intercession-cabal-opt-5-plasma-gun'],
 'r18-ts-ammitara-specials','Special Weapons — up to 2 models',2)
for oid,per,label in [
 ('r41-unit-xv-2-ammitara-occult-intercession-cabal-opt-7-krak-grenades',2,'Krak grenades — entire Cabal (+2 pts/model)'),
 ('r41-unit-xv-2-ammitara-occult-intercession-cabal-opt-8-melta-bombs',5,'Melta bombs — entire Cabal (+5 pts/model)')]:
    add_scaled_option(findid(root,oid),per,amodel.get('id'),'r18-ts-ammitara-scale-',label)
add_power_group(amm,'r18-ts-ammitara-power','Psychic Power — select 1',
                allowed=['Divination','Telepathy'])
log.append('Ammitara: all Sniper replacements share squad-size cap; Meltagun/Plasma Gun share max 2; whole-Cabal costs scale; power restricted to Divination/Telepathy')

num=findid(root,'r41-unit-xv-5-numerologist-cabal')
nopt=group_named(num,'Options'); nmodel=findid(root,'r41-unit-xv-5-numerologist-cabal-additional')
nes=nopt.find(C('selectionEntries'))
rot=next((x for x in list(nes) if (x.get('name') or '')=='Rotor Cannon'),None) if nes is not None else None
vol=next((x for x in list(nes) if (x.get('name') or '')=='Volkite Caliver'),None) if nes is not None else None
if rot is None or vol is None: raise RuntimeError('Missing Numerologist Life Ward weapon options')
make_subgroup(nopt,[rot.get('id'),vol.get('id')],'r18-ts-numerologist-life-ward-guns','Life Ward weapons — 1 per 5 models',1,nmodel.get('id'),2)
nes=nopt.find(C('selectionEntries'))
nk=next((x for x in list(nes) if 'Krak' in (x.get('name') or '')),None) if nes is not None else None
if nk is None: raise RuntimeError('Missing Numerologist Krak grenades')
add_scaled_option(nk,2,nmodel.get('id'),'r18-ts-numerologist-scale-','Krak grenades — entire Cabal (+2 pts/model)')
log.append('Numerologist: Rotor/Volkite share 1-per-5 cap; whole-Cabal Krak cost scales; fixed Psy-Synchronicity remains source-defined')

osi=findid(root,'r41-unit-xv-4-contemptor-osiron-dreadnought')
oopt=group_named(osi,'Options')
oes=oopt.find(C('selectionEntries'))
ml2=next((x for x in list(oes) if 'Mastery Level 2' in (x.get('name') or '')),None) if oes is not None else None
if ml2 is None: raise RuntimeError('Missing Osiron ML2 upgrade')
add_power_group(osi,'r18-ts-osiron-power1','Psychic Power — select 1',
                allowed=['Biomancy','Divination','Pyromancy','Telekinesis','Telepathy'])
add_power_group(osi,'r18-ts-osiron-power2','Additional Psychic Power — Mastery Level 2',
                allowed=['Biomancy','Divination','Pyromancy','Telekinesis','Telepathy'],gate_ids=[ml2.get('id')],
                source_group_id='r61-librarian-power2')
log.append('Osiron: 0-1; one mandatory power, second power appears and becomes mandatory only with ML2; no Prosperine Cult added')

# 4. Named cults + named psychic disciplines
named=[
 ('r41-unit-xv-6-ahzek-ahriman','Corvidae',None,None),
 ('r41-unit-xv-7-phosis-t-kar','Raptora',['Telekinesis'],2),
 ('r41-unit-xv-8-magistus-amon-the-hidden','Athanaeans',['Telepathy'],2),
 ('r41-unit-xv-9-hathor-maat','Pavoni',['Biomancy'],2),
 ('r41-unit-xv-10-sanakht','Athanaeans',None,None),
]
for uid,cult,powers,count in named:
    h=findid(root,uid)
    if h is None: raise RuntimeError('Missing named XV character '+uid)
    roster_max1(h,'r18-ts-'+uid+'-01')
    fix_cult(h,cult)
    if powers and count:
        add_power_group(h,'r18-ts-'+uid+'-power1',f'Psychic Power 1 — {powers[0]}',allowed=powers)
        add_power_group(h,'r18-ts-'+uid+'-power2',f'Psychic Power 2 — {powers[0]}',allowed=powers,source_group_id='r61-librarian-power2')
    log.append(f'{h.get("name")}: fixed Cult = {cult}'+(f'; {count} powers restricted to {powers[0]}' if powers else '; fixed/source psychic rules retained'))

for uid,pts in [('r41-unit-xv-6-ahzek-ahriman',1500),('r41-unit-xv-8-magistus-amon-the-hidden',1500)]:
    add_min_points_gate(findid(root,uid),pts,'r18-ts-'+uid)
log.append('Ahriman and Amon: 0-1 plus minimum 1,500-point roster visibility gates')

# 5. Dry-run validations
for gid in ('r18-ts-veteran-unit-brotherhood-power','r18-ts-terminator-unit-brotherhood-power','r18-ts-tactical-brotherhood-power'):
    if findid(root,gid) is None: raise RuntimeError('Missing generated Brotherhood power group '+gid)

if APPLY:
    root.set('revision','18')
    ct.write(CAT,encoding='utf-8',xml_declaration=True)
    gt.write(GST,encoding='utf-8',xml_declaration=True)
    idx=IDX.read_text(encoding='utf-8')
    idx=re.sub(r'(filePath="Legiones Astartes\.cat"[^>]*dataRevision=")\d+(")',r'\g<1>18\2',idx)
    IDX.write_text(idx,encoding='utf-8')

lines=[
 'R18 THOUSAND SONS CORE — '+('APPLY' if APPLY else 'DRY RUN ONLY'),
 f'Input CAT revision: 17 | Proposed CAT revision: 18 | GST revision remains {groot.get("revision")}',
 'LIVE FILES WRITTEN: '+('YES' if APPLY else 'NO'),
 '',
 'SOURCE-LOCKED CULT / DISCIPLINE MAP:',
 '  Pavoni -> Biomancy',
 '  Raptora -> Telekinesis',
 '  Corvidae -> Divination',
 '  Athanaeans -> Telepathy',
 '  Pyrae -> Pyromancy',
 '',
 'CHANGES:'
]
lines += ['  + '+x for x in log]
lines += [
 '',
 'INTENTIONALLY NOT RESOLVED IN THIS CORE PASS:',
 '  - Guard of the Crimson King: source contradiction between Sekhmet 0-1 and Sekhmet fulfilling two compulsory Troops slots is preserved, not invented around.',
 '  - Axis of Dissolution: maximum-size-all-Troops and vehicle/Infantry ratio need a dedicated roster-validator pass.',
 '  - Guard of the Crimson King: Warlord qualification, Magnus HQ relocation, free Transponders and vehicle/Legion ratio need the Rite-specific pass.',
 '  - Magnus: five-power/two-discipline/fixed Infernal Phoenix + Strands of Fate logic is reserved for the Primarch psychic pass.',
 '  - Generic Thousand Sons Praetor/Centurion Psyker selectors and Prosperine Armoury dependency cleanup are reserved for the next core pass.',
 '',
 'DRY-RUN RESULT: PASS'
]
OUT.write_text('\n'.join(lines),encoding='utf-8')
print('\n'.join(lines))
