from pathlib import Path
import os,re
import xml.etree.ElementTree as ET

CAT=Path('Legiones Astartes.cat'); GST=Path('Prohammer 30k.gst'); IDX=Path('index.xml')
OUT=Path('inspection-live-r21-ts-rite-hotfix.txt')
APPLY=os.environ.get('R21_APPLY','0')=='1'
NS='http://www.battlescribe.net/schema/catalogueSchema'; GNS='http://www.battlescribe.net/schema/gameSystemSchema'
ET.register_namespace('',NS); ET.register_namespace('',GNS)
C=lambda t:f'{{{NS}}}{t}'; G=lambda t:f'{{{GNS}}}{t}'
ct=ET.parse(CAT); root=ct.getroot(); gt=ET.parse(GST); groot=gt.getroot()
if root.get('revision')!='20': raise RuntimeError(f'R21 expects CAT 20, got {root.get("revision")}')

FEL='r25-rite-xv-2-the-fellowships-of-prospero'
GUARD='r25-rite-xv-1-the-guard-of-the-crimson-king'
AXIS='r25-rite-xv-0-the-axis-of-dissolution'

def findid(r,i): return next((x for x in r.iter() if x.get('id')==i),None)
def ensure(p,t,ns=C):
    x=p.find(ns(t))
    if x is None:x=ET.SubElement(p,ns(t))
    return x
def remove_mod(e,ids,ns=C):
    ms=e.find(ns('modifiers'))
    if ms is None:return 0
    n=0
    for x in list(ms):
        if x.get('id') in ids:
            ms.remove(x); n+=1
    return n
def add_hide_unless(e,mid,child,scope='roster',ns=C):
    ms=ensure(e,'modifiers',ns)
    for x in list(ms):
        if x.get('id')==mid:ms.remove(x)
    m=ET.SubElement(ms,ns('modifier'),{'id':mid,'type':'set','field':'hidden','value':'true'})
    cs=ET.SubElement(m,ns('conditions'))
    ET.SubElement(cs,ns('condition'),{'type':'lessThan','value':'1','field':'selections','scope':scope,'childId':child,'shared':'true','includeChildSelections':'true','includeChildForces':'false'})
def add_show_if(e,mid,child,scope='roster',ns=C):
    ms=ensure(e,'modifiers',ns)
    for x in list(ms):
        if x.get('id')==mid:ms.remove(x)
    m=ET.SubElement(ms,ns('modifier'),{'id':mid,'type':'set','field':'hidden','value':'false'})
    cs=ET.SubElement(m,ns('conditions'))
    ET.SubElement(cs,ns('condition'),{'type':'atLeast','value':'1','field':'selections','scope':scope,'childId':child,'shared':'true','includeChildSelections':'true','includeChildForces':'false'})
def add_hide_if(e,mid,child,scope='roster',ns=C):
    ms=ensure(e,'modifiers',ns)
    for x in list(ms):
        if x.get('id')==mid:ms.remove(x)
    m=ET.SubElement(ms,ns('modifier'),{'id':mid,'type':'set','field':'hidden','value':'true'})
    cs=ET.SubElement(m,ns('conditions'))
    ET.SubElement(cs,ns('condition'),{'type':'atLeast','value':'1','field':'selections','scope':scope,'childId':child,'shared':'true','includeChildSelections':'true','includeChildForces':'false'})
def set_rule_text(e,rid,text):
    rr=findid(e,rid)
    if rr is None: return False
    d=rr.find(C('description'))
    if d is None:d=ET.SubElement(rr,C('description'))
    d.text=text; return True
def add_category_link(host,i,name,target,primary='false',hidden='false'):
    cs=ensure(host,'categoryLinks')
    for x in list(cs):
        if x.get('id')==i:cs.remove(x)
    return ET.SubElement(cs,C('categoryLink'),{'id':i,'name':name,'targetId':target,'primary':primary,'hidden':hidden})
def add_set_pts(e,mid,val,child):
    ms=ensure(e,'modifiers')
    for x in list(ms):
        if x.get('id')==mid:ms.remove(x)
    m=ET.SubElement(ms,C('modifier'),{'id':mid,'type':'set','field':'pts','value':str(val)})
    cs=ET.SubElement(m,C('conditions'))
    ET.SubElement(cs,C('condition'),{'type':'atLeast','value':'1','field':'selections','scope':'roster','childId':child,'shared':'true','includeChildSelections':'true','includeChildForces':'false'})

log=[]

# 1) Exact error in screenshot: mandatory wargear inside Tactical loadouts was selected but marked hidden.
tac=findid(root,'tactical-unit')
load=findid(root,'tac-loadout')
if tac is None or load is None: raise RuntimeError('Tactical loadout missing')
fixed_hidden=[]
for opt in list(load.find(C('selectionEntries')) or []):
    for l in opt.iter(C('entryLink')):
        cs=l.find(C('constraints'))
        mandatory=cs is not None and any(c.get('type')=='min' and float(c.get('value','0'))>=1 for c in list(cs))
        if mandatory and l.get('hidden')=='true':
            l.set('hidden','false'); fixed_hidden.append(l.get('id'))
# Make the known automatic children visible even if they lack a min due older cloned construction.
for lid in ('load-standard-b','load-standard-p','load-add-b','load-add-p','load-add-c','load-ex-p','load-ex-c'):
    e=findid(root,lid)
    if e is not None and e.get('hidden')=='true':
        e.set('hidden','false')
        if lid not in fixed_hidden:fixed_hidden.append(lid)
log.append(f'Tactical automatic loadout wargear no longer remains selected while hidden ({len(fixed_hidden)} child links fixed)')

# 2) Fellowships Tactical Brotherhood had TWO stale blockers:
#    one force-scope rite check and one incorrect "20 Tactical Marines" check (there are 19 Marines + Sergeant).
tbl=findid(root,'r45-tactical-ts-brother')
if tbl is None: raise RuntimeError('Tactical Brotherhood link missing')
removed=remove_mod(tbl,['r48-vis-13','r48-vis-14'])
# Keep/rebuild only the correct roster Rite + 19 Tactical Marine checks.
add_hide_unless(tbl,'r21-ts-tactical-brotherhood-rite',FEL,'roster')
ms=ensure(tbl,'modifiers')
for x in list(ms):
    if x.get('id')=='r21-ts-tactical-brotherhood-size':ms.remove(x)
m=ET.SubElement(ms,C('modifier'),{'id':'r21-ts-tactical-brotherhood-size','type':'set','field':'hidden','value':'true'})
cs=ET.SubElement(m,C('conditions'))
ET.SubElement(cs,C('condition'),{'type':'lessThan','value':'19','field':'selections','scope':'root-entry','childId':'tac-marine','shared':'true','includeChildSelections':'true','includeChildForces':'false'})
# Remove older duplicate R18 versions to leave one source of truth.
remove_mod(tbl,['r18-ts-tactical-brotherhood-rite','r18-ts-tactical-brotherhood-size'])
log.append(f'Fellowships Tactical Brotherhood visibility rebuilt: Rite selected + exactly full 20-model squad (19 Marines + Sergeant); removed {removed} stale blockers')

# Shared Tactical Brotherhood rule: any normal TS discipline, Cult Mastery from chosen Cult.
shared_tac=findid(root,'r45-ts-tactical-brotherhood')
if shared_tac is not None:
    set_rule_text(shared_tac,'r45-ts-tactical-brotherhood-rule',
        'Fellowships of Prospero only. A full 20-model Legion Tactical Squad may purchase Brotherhood of Psykers (Mastery Level 1) for +25 points. Choose one normal Thousand Sons psychic discipline, then select one power from that discipline. The unit retains its chosen Prosperine Cult and receives that Cult’s Cult Mastery.')

# 3) Veterans/Terminators: remove stale force-scope Rite gates; roster gates from R18 were the reliable ones.
for base in ('veteran-unit','terminator-unit'):
    normal=findid(root,f'r45-{base}-ts-brother')
    fellow=findid(root,f'r45-{base}-ts-brother-fellow')
    if normal is None or fellow is None: raise RuntimeError('Missing '+base+' Brotherhood links')
    stale=[]
    # Normal +25 disappears during Fellowships.
    for x in list(normal.find(C('modifiers')) or []):
        if x.get('id') and (x.get('id').endswith('-hide-rite') or x.get('id') in ('r45-veteran-unit-ts-brother-hide-rite','r45-terminator-unit-ts-brother-hide-rite')):
            stale.append(x.get('id'))
    remove_mod(normal,stale)
    add_hide_if(normal,f'r21-ts-{base}-normal-hide-fellow',FEL,'roster')
    # +15 option appears only during Fellowships; remove the old scope=force gate by known IDs.
    old={'veteran-unit':'r48-vis-78','terminator-unit':'r48-vis-98'}[base]
    remove_mod(fellow,[old])
    add_hide_unless(fellow,f'r21-ts-{base}-fellow-show-only',FEL,'roster')
log.append('Veteran and Terminator Fellowship Brotherhood pricing now switches using roster-scope Rite checks only (+25 normally / +15 in Fellowships)')

# 4) Guard of the Crimson King: make the roster-changing parts genuinely functional.
magnus=findid(root,'r41-unit-xv-11-xv-magnus-the-red-the-crimson-king')
if magnus is None: raise RuntimeError('Magnus missing')
cls=ensure(magnus,'categoryLinks')
low=next((x for x in list(cls) if x.get('targetId')=='cat-low'),None)
if low is not None:add_hide_if(low,'r21-ts-guard-magnus-hide-low',GUARD,'roster')
hq=next((x for x in list(cls) if x.get('id')=='r21-ts-guard-magnus-hq'),None)
if hq is None:hq=add_category_link(magnus,'r21-ts-guard-magnus-hq','HQ — Guard of the Crimson King','cat-hq','true','true')
add_show_if(hq,'r21-ts-guard-magnus-show-hq',GUARD,'roster')

# Praetor ML3 option only in Guard (still labelled Warlord-only because New Recruit cannot infer Warlord marker).
ml3=findid(root,'r18-ts-guard-praetor-ml3')
if ml3 is not None:
    ml3.set('hidden','false')
    add_hide_unless(ml3,'r21-ts-guard-ml3-rite',GUARD,'roster')

# Free Terminator Transponders: set shared unit upgrade to 0 points under Guard.
trans=findid(root,'r45-ts-trans-unit')
if trans is not None:add_set_pts(trans,'r21-ts-guard-trans-free',0,GUARD)

# Ensure Sekhmet category conversion is roster-scope and unambiguous.
sek=findid(root,'r41-unit-xv-0-sekhmet-terminator-cabal')
if sek is None: raise RuntimeError('Sekhmet missing')
scls=ensure(sek,'categoryLinks')
selite=next((x for x in list(scls) if x.get('targetId')=='cat-elites'),None)
if selite is not None:add_hide_if(selite,'r21-ts-guard-sekhmet-hide-elite',GUARD,'roster')
st=next((x for x in list(scls) if x.get('id')=='r19-guard-sekhmet-troops'),None)
if st is None:st=add_category_link(sek,'r19-guard-sekhmet-troops','Troops — Guard of the Crimson King','cat-troops','true','true')
add_show_if(st,'r21-ts-guard-sekhmet-show-troops',GUARD,'roster')
log.append('Guard of the Crimson King now functionally shifts Magnus to HQ, Sekhmet to Troops, gates Praetor ML3 to the Rite and makes Terminator Transponders free')

# 5) Axis duplicate size modifiers: keep one clean R19/R21 rule, remove obsolete R18 duplicates.
axis_dupes=0
for e in root.iter(C('selectionEntry')):
    ms=e.find(C('modifiers'))
    if ms is None: continue
    for x in list(ms):
        if (x.get('id') or '').startswith('r18-ts-axis-max-'):
            ms.remove(x); axis_dupes+=1
log.append(f'Axis of Dissolution duplicate maximum-size modifiers cleaned ({axis_dupes} obsolete R18 modifiers removed; current max-size enforcement retained)')

# 6) Validate the GST restrictions still exist and target the right Rite.
force=findid(groot,'force-standard')
if force is None: raise RuntimeError('Standard force missing')
fast=findid(groot,'fl-fast')
if fast is None: raise RuntimeError('Fast Attack force link missing')
fm=findid(groot,'r18-ts-fellowships-fast-max')
if fm is None: raise RuntimeError('Fellowships Fast Attack max-1 modifier missing')
bro=findid(groot,'r18-ts-brotherhood-limit')
if bro is None: raise RuntimeError('Fellowships Brotherhood counter missing')
bmin=findid(groot,'r18-ts-brotherhood-min-fellowships')
if bmin is None: raise RuntimeError('Fellowships Brotherhood minimum modifier missing')

# Static validations for the exact screenshot bug and Fellowships visibility.
bad=[]
for lid in ('load-standard-b','load-standard-p'):
    e=findid(root,lid)
    if e is None or e.get('hidden')=='true':bad.append(lid)
if bad: raise RuntimeError('Tactical hidden-selected bug remains: '+','.join(bad))
for mid in ('r48-vis-13','r48-vis-14','r18-ts-tactical-brotherhood-rite','r18-ts-tactical-brotherhood-size'):
    if findid(root,mid) is not None: raise RuntimeError('Stale Tactical Brotherhood blocker remains '+mid)
if findid(root,'r21-ts-tactical-brotherhood-rite') is None or findid(root,'r21-ts-tactical-brotherhood-size') is None:
    raise RuntimeError('New Tactical Brotherhood gates missing')
if findid(root,'r21-ts-guard-magnus-hq') is None: raise RuntimeError('Magnus Guard HQ category missing')

lines=[
 'LIVE R21 — THOUSAND SONS RITE HOTFIX',
 'MODE='+('APPLY' if APPLY else 'DRY RUN'),
 'INPUT CAT=20 | OUTPUT CAT=21 | GSTref='+str(root.get('gameSystemRevision')),
 '',
]+['• '+x for x in log]+[
 '',
 'Still explicit text rather than unsafe automation:',
 '• Fellowships: Warlord must be a Thousand Sons Psyker; every Brotherhood must share a Cult with at least one Thousand Sons IC; no Allied Detachment.',
 '• Guard: Warlord identity and Vehicle-to-Legiones ratio; no Allied Detachment/Fortification.',
 '• Axis: Vehicle-to-Infantry ratio and Fortification ban where the GST exposes no reliable force slot.',
 '• Guard retains the written Sekhmet 0–1 vs compulsory-Troops contradiction; no invented override.',
 '',
 'VALIDATION: PASS'
]
OUT.write_text('\n'.join(lines),encoding='utf-8')

if APPLY:
    root.set('revision','21')
    ct.write(CAT,encoding='utf-8',xml_declaration=True)
    gt.write(GST,encoding='utf-8',xml_declaration=True)
    idx=IDX.read_text(encoding='utf-8')
    idx=re.sub(r'(filePath="Legiones Astartes\.cat"[^>]*dataRevision=")\d+(")',r'\g<1>21\2',idx)
    IDX.write_text(idx,encoding='utf-8')
print('\n'.join(lines))
