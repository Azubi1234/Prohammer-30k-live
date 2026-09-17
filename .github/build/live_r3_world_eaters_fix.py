from pathlib import Path
from copy import deepcopy
import re
import xml.etree.ElementTree as ET

CAT=Path('Legiones Astartes.cat'); IDX=Path('index.xml'); OUT=Path('inspection-live-r3-world-eaters-fix.txt')
NS='http://www.battlescribe.net/schema/catalogueSchema'; ET.register_namespace('',NS); C=lambda t:f'{{{NS}}}{t}'
ct=ET.parse(CAT); root=ct.getroot()
if root.get('revision')!='2': raise RuntimeError(f'Expected CAT 2, got {root.get("revision")}')

def ensure(p,t):
    x=p.find(C(t))
    if x is None:x=ET.SubElement(p,C(t))
    return x

def byid(i): return next((e for e in root.iter() if e.get('id')==i),None)
def slug(s): return re.sub(r'[^a-z0-9]+','-',s.lower()).strip('-')
def pts(e):
    cs=e.find(C('costs'))
    if cs is not None:
        for x in cs.findall(C('cost')):
            if x.get('typeId')=='pts': return x
    return None

def setpts(e,v):
    cs=ensure(e,'costs'); p=pts(e)
    if p is None:p=ET.SubElement(cs,C('cost'),{'name':'Points','typeId':'pts','value':str(v)})
    else:p.set('value',str(v));p.set('name','Points')

def setmax(e,v,id_):
    cs=ensure(e,'constraints')
    for x in list(cs):
        if x.get('field')=='selections' and x.get('type')=='max':cs.remove(x)
    ET.SubElement(cs,C('constraint'),{'id':id_,'type':'max','value':str(v),'field':'selections','scope':'parent','shared':'true','includeChildSelections':'true','includeChildForces':'false'})

def add_rule(e,id_,name,text):
    rs=ensure(e,'rules'); r=ET.SubElement(rs,C('rule'),{'id':id_,'name':name,'hidden':'false'});ET.SubElement(r,C('description')).text=text

def rewrite_ids(node,prefix):
    mp={}
    for x in node.iter():
        if x.get('id'):mp[x.get('id')]=prefix+x.get('id')
    for x in node.iter():
        if x.get('id') in mp:x.set('id',mp[x.get('id')])
        for a in ('targetId','childId','field'):
            if x.get(a) in mp:x.set(a,mp[x.get(a)])

def clone_unit(src,prefix):
    c=deepcopy(src); rewrite_ids(c,prefix); c.set('id',prefix+src.get('id')); c.set('hidden','false')
    cl=c.find(C('categoryLinks'))
    if cl is not None:c.remove(cl)
    mods=c.find(C('modifiers'))
    if mods is not None:c.remove(mods)
    cs=c.find(C('constraints'))
    if cs is not None:
        for x in list(cs):
            if x.get('scope')=='roster':cs.remove(x)
    setmax(c,1,c.get('id')+'-ret-max')
    return c

def add_scaled(opt,per,model_id,label):
    setpts(opt,0)
    ms=ensure(opt,'modifiers')
    m=ET.SubElement(ms,C('modifier'),{'id':opt.get('id')+'-scaled','type':'increment','field':'pts','value':str(per)})
    reps=ET.SubElement(m,C('repeats'))
    ET.SubElement(reps,C('repeat'),{'field':'selections','scope':'root-entry','value':'1','percentValue':'false','shared':'true','includeChildSelections':'true','includeChildForces':'false','childId':model_id,'repeats':'1','roundUp':'false'})
    add_rule(opt,opt.get('id')+'-rule',label,f'This is a whole-squad upgrade and costs +{per} points for every model in the squad. New Recruit calculates the total automatically from the selected squad size.')

def new_opt(group,id_,name,per,model_id):
    es=ensure(group,'selectionEntries'); e=ET.SubElement(es,C('selectionEntry'),{'id':id_,'name':name,'type':'upgrade','hidden':'false','import':'true'})
    setmax(e,1,id_+'-max'); add_scaled(e,per,model_id,name); return e

def strip_legion_specific_extras(u):
    bad_prefixes=('r40-da-','da22-','r64-if-','r68-if-','r70-if-','r71-nl-','r74-ba-','r79-ih-','r83-ih-','live-r2-fabius-','live-r2-fulgrim-')
    for p in list(u.iter()):
        for x in list(p):
            xid=x.get('id') or ''
            if any(k in xid for k in bad_prefixes):p.remove(x)

tri_fixed=[]
for u in list(root.iter(C('selectionEntry'))):
    if u.get('type')!='unit':continue
    if 'TRIARII BREACHER SQUAD' not in (u.get('name') or '').upper():continue
    model=next((x for x in u.iter(C('selectionEntry')) if x.get('type')=='model' and 'triarii breacher' in (x.get('name') or '').lower()),None)
    if model is None:continue
    gs=ensure(u,'selectionEntryGroups')
    for g in list(gs):
        if (g.get('name') or '').strip().lower()=='options' and ('triarii-breacher-squad-options' in (g.get('id') or '')):gs.remove(g)
        if (g.get('id') or '').startswith('live-r3-triarii-'):gs.remove(g)
    for g in list(gs):
        if (g.get('name') or '').strip().lower()=='wargear':
            ses=g.find(C('selectionEntries'))
            if ses is not None:
                for x in list(ses):
                    if (x.get('name') or '').strip().lower()=='frag grenades':ses.remove(x)
    wg=ET.SubElement(gs,C('selectionEntryGroup'),{'id':'live-r3-triarii-weapons-'+slug(u.get('id')),'name':'Whole Squad Weapon Replacement','hidden':'false','collective':'false','import':'true'})
    setmax(wg,1,wg.get('id')+'-max')
    new_opt(wg,wg.get('id')+'-caedere','Caedere Weapons — entire squad',5,model.get('id'))
    new_opt(wg,wg.get('id')+'-power','Power Weapons — entire squad',10,model.get('id'))
    eq=ET.SubElement(gs,C('selectionEntryGroup'),{'id':'live-r3-triarii-equipment-'+slug(u.get('id')),'name':'Whole Squad Equipment','hidden':'false','collective':'false','import':'true'})
    new_opt(eq,eq.get('id')+'-frag','Frag grenades — entire squad',1,model.get('id'))
    new_opt(eq,eq.get('id')+'-krak','Krak grenades — entire squad',2,model.get('id'))
    tri_fixed.append(u.get('id'))

TARGETS={
 'KHÂRN THE BLOODY':['hq-centurion-ret-command','r41-unit-xii-0-rampager-squad'],
 'SHABRAN DARR':['r41-unit-xii-2-red-hand-destroyer-mortalis-squad','assault-unit'],
 'KARGOS, THE BLOODSPITTER':['hq-centurion-ret-command'],
 'CAPTAIN EHRLEN':['hq-centurion-ret-command'],
 'DELVARUS':['r41-unit-xii-5-triarii-breacher-squad'],
 'XII — ANGRON, THE RED ANGEL':['hq-praetor-ret-honour','hq-centurion-ret-termcommand','r41-unit-xii-4-devourer-terminator-squad'],
}
patched=[]
for ch in list(root.iter(C('selectionEntry'))):
    if ch.get('type')!='unit':continue
    nm=(ch.get('name') or '').strip().upper()
    key=next((k for k in TARGETS if nm==k.upper()),None)
    if key is None:continue
    gs=ensure(ch,'selectionEntryGroups')
    for g in list(gs):
        gn=(g.get('name') or '').lower(); gid=g.get('id') or ''
        if 'retinue' in gn and (gid.startswith('live-r2-') or gid.startswith('live-r3-we-')):gs.remove(g)
    gid='live-r3-we-'+slug(ch.get('id'))+'-retinue'
    g=ET.SubElement(gs,C('selectionEntryGroup'),{'id':gid,'name':'RETINUE — choose up to one (no separate FOC slot)','hidden':'false','collective':'false','import':'true'})
    setmax(g,1,gid+'-max')
    es=ensure(g,'selectionEntries')
    made=[]
    for i,tid in enumerate(TARGETS[key]):
        src=byid(tid)
        if src is None: raise RuntimeError(f'Missing retinue source {tid} for {key}')
        c=clone_unit(src,f'{gid}-{i}-')
        strip_legion_specific_extras(c)
        es.append(c);made.append(c.get('name'))
    add_rule(g,gid+'-rule','Retinue',f'{key.title()} may select one of the listed retinue units. The selected unit does not occupy a separate Force Organisation slot.')
    patched.append((ch.get('id'),key,made))

root.set('revision','3')
ct.write(CAT,encoding='utf-8',xml_declaration=True)
idx=IDX.read_text(encoding='utf-8')
idx=re.sub(r'(filePath="Legiones Astartes\.cat"[^>]*dataRevision=")\d+(" )',r'\g<1>3\2',idx)
idx=re.sub(r'(filePath="Legiones Astartes\.cat"[^>]*dataRevision=")\d+("\s*/>)',r'\g<1>3\2',idx)
IDX.write_text(idx,encoding='utf-8')

lines=['LIVE R3 — World Eaters repair','CAT=3 GSTref='+str(root.get('gameSystemRevision')),'',f'Triarii copies repaired: {len(tri_fixed)}']+[f'  + {x}' for x in tri_fixed]
lines += ['',f'World Eaters character/Primarch copies given functional retinue selectors: {len(patched)}']
for i,k,m in patched: lines.append(f'  + {i} | {k} -> '+', '.join(m))
lines += ['','Source-backed no-retinue character intentionally unchanged: GAHLAN SURLAK.','Daemon Angron intentionally receives no retinue; his entry says he may never join another unit and no model may join him.']
OUT.write_text('\n'.join(lines),encoding='utf-8')
print('\n'.join(lines))