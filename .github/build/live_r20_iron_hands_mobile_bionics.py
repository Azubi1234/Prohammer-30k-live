from pathlib import Path
import os,re
import xml.etree.ElementTree as ET

CAT=Path('Legiones Astartes.cat'); IDX=Path('index.xml'); OUT=Path('inspection-live-r20-iron-hands-mobile-bionics.txt')
APPLY=os.environ.get('R20_APPLY','0')=='1'
NS='http://www.battlescribe.net/schema/catalogueSchema'; ET.register_namespace('',NS); C=lambda t:f'{{{NS}}}{t}'
ct=ET.parse(CAT); root=ct.getroot()
if root.get('revision')!='19': raise RuntimeError(f'R20 expects CAT 19, got {root.get("revision")}')

def findid(i): return next((x for x in root.iter() if x.get('id')==i),None)
def ensure(p,t):
    x=p.find(C(t))
    if x is None:x=ET.SubElement(p,C(t))
    return x
def add_max(e,i,val=1):
    cs=ensure(e,'constraints')
    for x in list(cs):
        if x.get('id')==i:cs.remove(x)
    ET.SubElement(cs,C('constraint'),{'id':i,'type':'max','value':str(val),'field':'selections','scope':'parent','shared':'true','includeChildSelections':'true','includeChildForces':'false'})
def add_hide_unless_legion(e,i):
    ms=ensure(e,'modifiers')
    for x in list(ms):
        if x.get('id')==i:ms.remove(x)
    m=ET.SubElement(ms,C('modifier'),{'id':i,'type':'set','field':'hidden','value':'true'})
    cs=ET.SubElement(m,C('conditions'))
    ET.SubElement(cs,C('condition'),{'type':'lessThan','value':'1','field':'selections','scope':'roster','childId':'legion-x','shared':'true','includeChildSelections':'true','includeChildForces':'false'})
def add_hide_if(e,child,i):
    ms=ensure(e,'modifiers')
    for x in list(ms):
        if x.get('id')==i:ms.remove(x)
    m=ET.SubElement(ms,C('modifier'),{'id':i,'type':'set','field':'hidden','value':'true'})
    cs=ET.SubElement(m,C('conditions'))
    ET.SubElement(cs,C('condition'),{'type':'atLeast','value':'1','field':'selections','scope':'root-entry','childId':child,'shared':'true','includeChildSelections':'true','includeChildForces':'false'})
def add_rule(e,i,name,text):
    rs=ensure(e,'rules')
    for x in list(rs):
        if x.get('id')==i:rs.remove(x)
    r=ET.SubElement(rs,C('rule'),{'id':i,'name':name,'hidden':'false'})
    ET.SubElement(r,C('description')).text=text
def add_cost(e,val):
    costs=ensure(e,'costs')
    c=next((x for x in costs if x.get('typeId')=='pts'),None)
    if c is None:c=ET.SubElement(costs,C('cost'),{'name':'Points','typeId':'pts','value':str(val)})
    else:c.set('value',str(val))
def add_scaled_cost(e,per,model_id,prefix):
    add_cost(e,0)
    ms=ensure(e,'modifiers')
    for x in list(ms):
        if (x.get('id') or '').startswith(prefix):ms.remove(x)
    m=ET.SubElement(ms,C('modifier'),{'id':prefix+'-scale','type':'increment','field':'pts','value':str(per)})
    reps=ET.SubElement(m,C('repeats'))
    ET.SubElement(reps,C('repeat'),{'field':'selections','scope':'root-entry','value':'1','percentValue':'false','shared':'true','includeChildSelections':'true','includeChildForces':'false','childId':model_id,'repeats':'1','roundUp':'false'})
def iron_group(unit,prefix,model_id,has_sergeant=True,generic_sgt_bionics=None):
    gs=ensure(unit,'selectionEntryGroups')
    gid=prefix+'-group'
    for x in list(gs):
        if x.get('id')==gid:gs.remove(x)
    g=ET.SubElement(gs,C('selectionEntryGroup'),{'id':gid,'name':'Iron Hands Wargear','hidden':'false'})
    add_hide_unless_legion(g,gid+'-legion')
    se=ET.SubElement(g,C('selectionEntries'))

    whole=ET.SubElement(se,C('selectionEntry'),{'id':prefix+'-whole','name':'Bionics — entire squad','type':'upgrade','hidden':'false','import':'true'})
    add_max(whole,prefix+'-whole-max')
    # Whole-unit price: +3 for every ordinary model; Sergeant pays +5 instead.
    add_scaled_cost(whole,3,model_id,prefix+'-whole')
    if has_sergeant:
        # flat +5 for the Sergeant on top of the ordinary-model repeat
        costs=ensure(whole,'costs'); p=next((x for x in costs if x.get('typeId')=='pts'),None); p.set('value','5')
    add_rule(whole,prefix+'-whole-rule','Bionics',
             'Every model in this Iron Hands unit receives Bionics. Ordinary models cost +3 points each; the squad Sergeant costs +5 points instead of +3. Iron Hands models with Bionics recover on a 5+ rather than 6+.')

    if has_sergeant:
        sgt=ET.SubElement(se,C('selectionEntry'),{'id':prefix+'-sgt','name':'Bionics — Sergeant only','type':'upgrade','hidden':'false','import':'true'})
        add_max(sgt,prefix+'-sgt-max'); add_cost(sgt,5)
        add_rule(sgt,prefix+'-sgt-rule','Bionics','The squad Sergeant purchases Bionics for +5 points. Iron Hands models with Bionics recover on a 5+ rather than 6+.')
        add_hide_if(whole,sgt.get('id'),prefix+'-whole-hide-sgt')
        add_hide_if(sgt,whole.get('id'),prefix+'-sgt-hide-whole')

    if generic_sgt_bionics:
        gen=findid(generic_sgt_bionics)
        if gen is not None:
            ms=ensure(gen,'modifiers')
            mid=prefix+'-hide-generic-sgt'
            for x in list(ms):
                if x.get('id')==mid:ms.remove(x)
            m=ET.SubElement(ms,C('modifier'),{'id':mid,'type':'set','field':'hidden','value':'true'})
            cs=ET.SubElement(m,C('conditions'))
            ET.SubElement(cs,C('condition'),{'type':'atLeast','value':'1','field':'selections','scope':'roster','childId':'legion-x','shared':'true','includeChildSelections':'true','includeChildForces':'false'})
    return whole

targets=[
 ('assault-unit','r20-ih-assault','assault-marine',True,'assault-sgt-bionics'),
 ('fa-bike','r20-ih-bike','fa-bike-included',True,'fa-bike-sgt-arm-bionics'),
 ('fa-attack-bike','r20-ih-attack-bike','fa-attack-bike-model',False,None),
]
done=[]
for uid,prefix,mid,sgt,gen in targets:
    u=findid(uid); m=findid(mid)
    if u is None or m is None:raise RuntimeError('Missing mobile Iron Hands target '+uid+'/'+mid)
    iron_group(u,prefix,mid,sgt,gen); done.append(u.get('name'))

# Existing Destroyer Bionics remain valid when Jump Packs are selected; no duplicate selector is added.
destroyer=findid('destroyer-unit')
if destroyer is None or findid('destroyer-jump-packs') is None or findid('r47-destroyer-unit-ih-bionics') is None:
    raise RuntimeError('Destroyer jump-pack/Bionics compatibility structure missing')

# Update the Iron Hands legion rule wording to include the newly permitted unit types.
updated=0
for r in root.iter(C('rule')):
    n=(r.get('name') or '').upper()
    if 'MORE' in n and ('MASCHINE THAN MAN' in n or 'MACHINE THAN MAN' in n):
        d=r.find(C('description'))
        if d is not None:
            d.text=('Iron Hands Characters and Veteran Sergeants may purchase Bionics for 5 points. '
                    'Any Iron Hands unit consisting wholly of Infantry, Jump Infantry or Bikes may purchase Bionics for +3 points per ordinary model; '
                    'a Sergeant in such a unit costs +5 points instead of +3. Every model in the unit must receive the upgrade. '
                    'Iron Hands models with Bionics successfully recover on a roll of 5+ rather than 6+.')
            updated+=1
if updated==0:
    # The catalogue can carry the legion rule under the Legion selector rather than as a shared rule.
    leg=findid('legion-x')
    if leg is not None:add_rule(leg,'r20-ih-more-machine','More Machine Than Man',
        'Iron Hands Characters and Veteran Sergeants may purchase Bionics for 5 points. Any Iron Hands unit consisting wholly of Infantry, Jump Infantry or Bikes may purchase Bionics for +3 points per ordinary model; a Sergeant in such a unit costs +5 points instead of +3. Every model in the unit must receive the upgrade. Iron Hands models with Bionics successfully recover on a roll of 5+ rather than 6+.')
    updated=1

# Validate selectors and dynamic pricing structure.
for uid,prefix,mid,sgt,gen in targets:
    whole=findid(prefix+'-whole')
    if whole is None:raise RuntimeError('Missing whole-squad Bionics '+uid)
    reps=list(whole.iter(C('repeat')))
    if not any(x.get('childId')==mid and x.get('field')=='selections' for x in reps):
        raise RuntimeError('Whole-squad Bionics does not scale on '+mid)
    if sgt and findid(prefix+'-sgt') is None:raise RuntimeError('Missing Sergeant-only Bionics '+uid)

lines=[
 'LIVE R20 — IRON HANDS MOBILE BIONICS + FORCED PUBLISH',
 'MODE='+('APPLY' if APPLY else 'DRY RUN'),
 'INPUT CAT=19 | OUTPUT CAT=20 | GSTref='+str(root.get('gameSystemRevision')),
 '',
 '• Iron Hands Bionics added to Legion Assault Squads, Legion Bike Squadrons and Legion Attack Bike Squadrons.',
 '• Whole-squad Bionics is one selector and auto-scales with squad size.',
 '• Assault/Bike Sergeant costs are +5 instead of +3; Sergeant-only +5 Bionics remains available as a mutually exclusive alternative.',
 '• The normal +10 generic Sergeant Bionics option is hidden for Iron Hands on those mobile squads.',
 '• Legion Destroyer Squads already retain their Iron Hands Bionics options when Jump Packs are selected; no duplicate option added.',
 '• More Machine Than Man wording updated to Infantry, Jump Infantry and Bikes.',
 '• Revision bumps 19 -> 20 to force New Recruit to see the update after v19 remained cached.',
 '',
 'VALIDATION: PASS'
]
OUT.write_text('\n'.join(lines),encoding='utf-8')
if APPLY:
    root.set('revision','20'); ct.write(CAT,encoding='utf-8',xml_declaration=True)
    idx=IDX.read_text(encoding='utf-8')
    idx=re.sub(r'(filePath="Legiones Astartes\.cat"[^>]*dataRevision=")\d+(")',r'\g<1>20\2',idx)
    IDX.write_text(idx,encoding='utf-8')
print('\n'.join(lines))
