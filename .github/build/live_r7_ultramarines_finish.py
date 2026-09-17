from pathlib import Path
from copy import deepcopy
import re
import xml.etree.ElementTree as ET

CAT=Path('Legiones Astartes.cat'); IDX=Path('index.xml'); OUT=Path('inspection-live-r7-ultramarines-finish.txt')
NS='http://www.battlescribe.net/schema/catalogueSchema'; ET.register_namespace('',NS); C=lambda t:f'{{{NS}}}{t}'
ct=ET.parse(CAT); root=ct.getroot()
if root.get('revision')!='6': raise RuntimeError(f'Expected CAT revision 6, got {root.get("revision")}')

def findid(i): return next((x for x in root.iter() if x.get('id')==i),None)
def ensure(p,t):
    x=p.find(C(t))
    if x is None: x=ET.SubElement(p,C(t))
    return x

def add_hide_unless(e,child,scope,id_):
    ms=ensure(e,'modifiers')
    for x in list(ms):
        if x.get('id')==id_: ms.remove(x)
    m=ET.SubElement(ms,C('modifier'),{'id':id_,'type':'set','field':'hidden','value':'true'})
    cs=ET.SubElement(m,C('conditions'))
    ET.SubElement(cs,C('condition'),{'type':'lessThan','value':'1','field':'selections','scope':scope,'childId':child,'shared':'true','includeChildSelections':'true','includeChildForces':'false'})

def add_hide_if(e,child,scope,id_):
    ms=ensure(e,'modifiers')
    for x in list(ms):
        if x.get('id')==id_: ms.remove(x)
    m=ET.SubElement(ms,C('modifier'),{'id':id_,'type':'set','field':'hidden','value':'true'})
    cs=ET.SubElement(m,C('conditions'))
    ET.SubElement(cs,C('condition'),{'type':'atLeast','value':'1','field':'selections','scope':scope,'childId':child,'shared':'true','includeChildSelections':'true','includeChildForces':'false'})

def set_group_count(g,n):
    cs=ensure(g,'constraints')
    for x in list(cs):
        if x.get('field')=='selections' and x.get('type') in ('min','max'): cs.remove(x)
    for typ in ('min','max'):
        ET.SubElement(cs,C('constraint'),{'id':g.get('id')+'-'+typ,'type':typ,'value':str(n),'field':'selections','scope':'parent','shared':'true','includeChildSelections':'true','includeChildForces':'false'})

def remap_ids(cl,prefix):
    mp={}
    for x in cl.iter():
        if x.get('id'): mp[x.get('id')]=prefix+x.get('id')
    for x in cl.iter():
        old=x.get('id')
        if old in mp: x.set('id',mp[old])
        ch=x.get('childId')
        if ch in mp: x.set('childId',mp[ch])
    return cl

log=[]
# Titus Prayto — exactly two normal psychic powers, no text-only placeholder.
pray=findid('r41-unit-xiii-8-titus-prayto'); lib=findid('hq-consul-librarian')
if pray is None or lib is None: raise RuntimeError('Prayto or generic Librarian Consul missing')
pgs=ensure(pray,'selectionEntryGroups')
for x in list(pgs):
    if (x.get('id') or '').startswith('r7-prayto-powers'): pgs.remove(x)
libgs=lib.find(C('selectionEntryGroups'))
src=next((g for g in list(libgs or []) if g.get('id')=='r29-lib-power-group'),None)
if src is None: raise RuntimeError('Generic Librarian power group missing')
cl=remap_ids(deepcopy(src),'r7-prayto-')
cl.set('id','r7-prayto-powers'); cl.set('name','Psychic Powers — select 2')
set_group_count(cl,2)
# Prayto may select two powers from the normal list; remove discipline-only visibility filters on the cloned powers.
for e in cl.iter(C('selectionEntry')):
    ms=e.find(C('modifiers'))
    if ms is not None:
        for m in list(ms):
            # the generic power list's hidden modifiers only expose powers for a selected discipline
            if m.get('field')=='hidden': ms.remove(m)
pgs.append(cl)
log.append('Titus Prayto now has a functional Psychic Powers — select 2 group using the normal ProHammer power list')

# Loyalist restrictions that are explicit in the source.
for uid,label in [
 ('r41-unit-xiii-7-honoured-telemechrus','Honoured Telemechrus'),
 ('r41-unit-xiii-9-xiii-roboute-guilliman-the-avenging-son','Roboute Guilliman'),
 ('r25-rite-xiii-1-vigil-opertii-mission','Vigil Opertii Mission')]:
    e=findid(uid)
    if e is None: raise RuntimeError('Missing '+uid)
    add_hide_unless(e,'allegiance-loyalist','roster',uid+'-r7-loyalist')
    log.append(label+' hidden unless Allegiance: Loyalist is selected')

# Logos Lectora explicitly forbids units required to enter via Deep Strike; hide Drop Pod/Dreadclaw selectors while the Rite is active.
logos='r25-rite-xiii-0-the-logos-lectora'
count=0
for e in root.iter():
    if e.tag not in (C('selectionEntry'),C('entryLink')): continue
    n=(e.get('name') or '').lower()
    # dedicated transport selectors / unit selectors, but not descriptive rules/profiles
    if 'drop pod' in n or 'dreadclaw' in n:
        add_hide_if(e,logos,'force',e.get('id')+'-r7-hide-logos')
        count+=1
log.append(f'Logos Lectora now hides {count} Drop Pod/Dreadclaw selections that would require Deep Strike')

# Keep written Rite limitations visible, but make explicit what New Recruit is enforcing vs tabletop-only.
for uid,name in [(logos,'The Logos Lectora'),('r25-rite-xiii-1-vigil-opertii-mission','Vigil Opertii Mission')]:
    e=findid(uid); rs=ensure(e,'rules')
    rid=uid+'-r7-validation-note'
    for r in list(rs):
        if r.get('id')==rid: rs.remove(r)
    r=ET.SubElement(rs,C('rule'),{'id':rid,'name':'New Recruit validation','hidden':'false'})
    if uid==logos:
        txt='New Recruit enforces the Drop Pod/Dreadclaw prohibition from this Rite where those selections are represented in the catalogue. The additional compulsory HQ/Troops requirements and Tank/Flyer-to-Infantry ratio remain roster requirements to check when building the army.'
    else:
        txt='New Recruit enforces the Loyalist-only restriction. The required allied Imperialis Militia Detachment, Gene-crafted and Warrior Elite Provenances, exclusion of Inducted Levy Squads, and required Vigilator remain cross-detachment requirements to verify when building the army.'
    ET.SubElement(r,C('description')).text=txt

root.set('revision','7'); ct.write(CAT,encoding='utf-8',xml_declaration=True)
idx=IDX.read_text(encoding='utf-8'); idx=re.sub(r'(filePath="Legiones Astartes\.cat"[^>]*dataRevision=")\d+("\s*/>)',r'\g<1>7\2',idx); IDX.write_text(idx,encoding='utf-8')
OUT.write_text('LIVE R7 — ULTRAMARINES FINISH\nCAT=7 GSTref='+str(root.get('gameSystemRevision'))+'\n\n'+'\n'.join('• '+x for x in log),encoding='utf-8')
print(OUT.read_text())
