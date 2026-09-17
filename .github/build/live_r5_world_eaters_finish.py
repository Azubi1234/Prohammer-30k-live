from pathlib import Path
from copy import deepcopy
import re
import xml.etree.ElementTree as ET

CAT=Path('Legiones Astartes.cat'); IDX=Path('index.xml'); OUT=Path('inspection-live-r5-world-eaters-finish.txt')
NS='http://www.battlescribe.net/schema/catalogueSchema'; ET.register_namespace('',NS); C=lambda t:f'{{{NS}}}{t}'
ct=ET.parse(CAT); root=ct.getroot()
if root.get('revision')!='4': raise RuntimeError(f'Expected CAT 4, got {root.get("revision")}')

def ensure(p,t):
    x=p.find(C(t))
    if x is None: x=ET.SubElement(p,C(t))
    return x

def setpts(e,v):
    cs=ensure(e,'costs')
    p=next((x for x in cs.findall(C('cost')) if x.get('typeId')=='pts'),None)
    if p is None: p=ET.SubElement(cs,C('cost'),{'name':'Points','typeId':'pts','value':str(v)})
    else: p.set('name','Points'); p.set('value',str(v))

def setmax(e,v,id_):
    cs=ensure(e,'constraints')
    for x in list(cs):
        if x.get('field')=='selections' and x.get('type')=='max': cs.remove(x)
    ET.SubElement(cs,C('constraint'),{'id':id_,'type':'max','value':str(v),'field':'selections','scope':'parent','shared':'true','includeChildSelections':'true','includeChildForces':'false'})

def add_rule(e,id_,name,text):
    rs=ensure(e,'rules')
    for old in list(rs):
        if old.get('id')==id_: rs.remove(old)
    r=ET.SubElement(rs,C('rule'),{'id':id_,'name':name,'hidden':'false'})
    ET.SubElement(r,C('description')).text=text

def slug(s): return re.sub(r'[^a-z0-9]+','-',(s or '').lower()).strip('-')

def direct_models(u):
    cont=u.find(C('selectionEntries'))
    if cont is None: return []
    return [x for x in cont if x.tag==C('selectionEntry') and x.get('type')=='model']

def clear_our_scalers(e,prefix):
    ms=e.find(C('modifiers'))
    if ms is not None:
        for x in list(ms):
            if (x.get('id') or '').startswith(prefix): ms.remove(x)

def add_scaled(e,per,models,prefix):
    setpts(e,0); clear_our_scalers(e,prefix)
    ms=ensure(e,'modifiers')
    for i,m in enumerate(models):
        mod=ET.SubElement(ms,C('modifier'),{'id':f'{prefix}-{i}','type':'increment','field':'pts','value':str(per)})
        reps=ET.SubElement(mod,C('repeats'))
        ET.SubElement(reps,C('repeat'),{'field':'selections','scope':'root-entry','value':'1','percentValue':'false','shared':'true','includeChildSelections':'true','includeChildForces':'false','childId':m.get('id'),'repeats':'1','roundUp':'false'})

def hide_descendants(e):
    for x in e.iter():
        if x is e: continue
        if x.tag in (C('selectionEntry'),C('entryLink')): x.set('hidden','true')

def hide_group_when_selected(group,child_id,prefix):
    ms=ensure(group,'modifiers')
    for x in list(ms):
        if (x.get('id') or '')==prefix: ms.remove(x)
    mod=ET.SubElement(ms,C('modifier'),{'id':prefix,'type':'set','field':'hidden','value':'true'})
    conds=ET.SubElement(mod,C('conditions'))
    ET.SubElement(conds,C('condition'),{'type':'atLeast','value':'1','field':'selections','scope':'parent','childId':child_id,'shared':'true','includeChildSelections':'true','includeChildForces':'false'})

def add_tactical_chainaxe_gate(e,add_id,exchange_id):
    ms=ensure(e,'modifiers')
    gate=e.get('id')+'-needs-chainsword'
    for x in list(ms):
        if x.get('id')==gate: ms.remove(x)
    mod=ET.SubElement(ms,C('modifier'),{'id':gate,'type':'set','field':'hidden','value':'true'})
    cgs=ET.SubElement(mod,C('conditionGroups')); cg=ET.SubElement(cgs,C('conditionGroup'),{'type':'and'}); conds=ET.SubElement(cg,C('conditions'))
    for cid in (add_id,exchange_id):
        ET.SubElement(conds,C('condition'),{'type':'lessThan','value':'1','field':'selections','scope':'parent','childId':cid,'shared':'true','includeChildSelections':'true','includeChildForces':'false'})

tactical_fixed=[]; grenade_fixed=[]
for u in list(root.iter(C('selectionEntry'))):
    if u.get('type')!='unit' or 'LEGION TACTICAL SQUAD' not in (u.get('name') or '').upper(): continue
    models=direct_models(u)
    gs=u.find(C('selectionEntryGroups'))
    if gs is None: continue
    load=next((g for g in gs if (g.get('name') or '').strip()=='Squad Weapons'),None)
    if load is None: continue
    opts=[]
    se=load.find(C('selectionEntries'))
    if se is not None: opts=list(se)
    std=next((x for x in opts if (x.get('name') or '').startswith('Bolters + Bolt Pistols') and 'Chainswords' not in (x.get('name') or '')),None)
    add=next((x for x in opts if 'Bolters + Bolt Pistols + Chainswords' in (x.get('name') or '')),None)
    exch=next((x for x in opts if 'Exchange Bolters for Chainswords' in (x.get('name') or '')),None)
    if not all((std,add,exch)): raise RuntimeError(f'Could not identify tactical loadout options in {u.get("id")}')
    std.set('name','Bolters + Bolt Pistols')
    add.set('name','Bolters + Bolt Pistols + Chainswords — entire squad (+2 pts/model)')
    exch.set('name','Exchange Bolters for Chainswords — entire squad (Free)')
    setpts(std,0); setpts(exch,0); add_scaled(add,2,models,add.get('id')+'-r5scale')
    for x in (std,add,exch): hide_descendants(x)
    add_rule(add,add.get('id')+'-r5rule','Whole-squad Chainswords','The entire squad retains its Bolters and Bolt pistols and also takes Chainswords for +2 points per model. New Recruit calculates the total from the selected squad size.')
    add_rule(exch,exch.get('id')+'-r5rule','Exchange Bolters for Chainswords','The entire squad exchanges its Bolters for Chainswords at no additional cost. Because the squad no longer has Bolters to replace, Special Weapon and Heavy Weapon selections are unavailable while this option is selected.')
    for g in gs:
        if (g.get('name') or '').strip() in ('Heavy Weapons','Special Weapons'): hide_group_when_selected(g,exch.get('id'),g.get('id')+'-r5-hide-no-bolters')
    gren=next((g for g in gs if (g.get('name') or '').strip()=='Squad Grenades'),None)
    if gren is not None:
        links=gren.find(C('entryLinks'))
        old=next((x for x in list(links) if 'krak' in (x.get('name') or '').lower()),None) if links is not None else None
        if old is not None:
            mods=deepcopy(old.find(C('modifiers'))) if old.find(C('modifiers')) is not None else None
            links.remove(old)
            ses=ensure(gren,'selectionEntries')
            kid=gren.get('id')+'-r5-krak-whole-squad'
            for x in list(ses):
                if x.get('id')==kid: ses.remove(x)
            k=ET.SubElement(ses,C('selectionEntry'),{'id':kid,'name':'Krak Grenades — entire squad (+2 pts/model)','type':'upgrade','hidden':'false','import':'true'})
            setmax(k,1,kid+'-max')
            if mods is not None: k.append(mods)
            add_scaled(k,2,models,kid+'-scale')
            add_rule(k,kid+'-rule','Whole-squad Krak Grenades','The entire squad takes Krak Grenades for +2 points per model. New Recruit calculates the total from the selected squad size.')
            grenade_fixed.append(u.get('id'))
    tactical_fixed.append((u.get('id'),add.get('id'),exch.get('id')))

chainaxe_fixed=[]; rampager_removed=[]
for u in list(root.iter(C('selectionEntry'))):
    if u.get('type')!='unit': continue
    gs=u.find(C('selectionEntryGroups'))
    if gs is None: continue
    models=direct_models(u)
    for g in gs:
        if (g.get('name') or '').strip()!='Legion Wargear & Upgrades': continue
        links=g.find(C('entryLinks'))
        if links is None: continue
        oldlinks=[x for x in list(links) if 'chainaxe' in (x.get('name') or '').lower()]
        if not oldlinks: continue
        if 'RAMPAGER SQUAD' in (u.get('name') or '').upper():
            for old in oldlinks: links.remove(old)
            rampager_removed.append(u.get('id'))
            continue
        ses=ensure(g,'selectionEntries')
        # remove any earlier local R5 chainaxe entries, if present
        for x in list(ses):
            if (x.get('id') or '').startswith('live-r5-chainaxe-'+slug(u.get('id'))): ses.remove(x)
        load=next((gg for gg in gs if (gg.get('name') or '').strip()=='Squad Weapons'),None)
        add_id=exchange_id=None
        if load is not None:
            le=load.find(C('selectionEntries'))
            if le is not None:
                addx=next((x for x in le if 'Bolters + Bolt Pistols + Chainswords' in (x.get('name') or '')),None)
                exchx=next((x for x in le if 'Exchange Bolters for Chainswords' in (x.get('name') or '')),None)
                add_id=addx.get('id') if addx is not None else None; exchange_id=exchx.get('id') if exchx is not None else None
        for n,old in enumerate(oldlinks):
            per=2 if 'berserker assault' in (old.get('name') or '').lower() else 4
            mods=deepcopy(old.find(C('modifiers'))) if old.find(C('modifiers')) is not None else None
            oid=old.get('id'); links.remove(old)
            nid='live-r5-chainaxe-'+slug(u.get('id'))+('-berserker' if per==2 else '-normal')
            e=ET.SubElement(ses,C('selectionEntry'),{'id':nid,'name':f'Chainaxes — entire squad (+{per} pts/model)'+(' — Berserker Assault' if per==2 else ''),'type':'upgrade','hidden':'false','import':'true'})
            setmax(e,1,nid+'-max')
            if mods is not None: e.append(mods)
            add_scaled(e,per,models,nid+'-scale')
            add_rule(e,nid+'-rule','Chainaxe',f'Whole-squad shortcut: every eligible model in the squad replaces its Close Combat Weapon with a Chainaxe for +{per} points per model. Armour Saves better than 4+ are reduced to 4+ against wounds caused by a Chainaxe; 4+ or worse and Invulnerable Saves are unaffected.')
            if add_id and exchange_id: add_tactical_chainaxe_gate(e,add_id,exchange_id)
            chainaxe_fixed.append((u.get('id'),oid,nid,per))

root.set('revision','5')
ct.write(CAT,encoding='utf-8',xml_declaration=True)
idx=IDX.read_text(encoding='utf-8')
idx=re.sub(r'(filePath="Legiones Astartes\.cat"[^>]*dataRevision=")\d+("\s*/>)',r'\g<1>5\2',idx)
IDX.write_text(idx,encoding='utf-8')

lines=['LIVE R5 — World Eaters finish','CAT=5 GSTref='+str(root.get('gameSystemRevision')),'',f'Tactical squad copies cleaned: {len(tactical_fixed)}']
for i,a,e in tactical_fixed: lines.append(f'  + {i}: whole-squad Chainswords={a}; free Bolter exchange={e}; free exchange hides special/heavy weapons')
lines += ['',f'Tactical Krak whole-squad upgrades fixed: {len(grenade_fixed)}']+[f'  + {x}' for x in grenade_fixed]
lines += ['',f'Chainaxe squad selectors converted to whole-squad scaling: {len(chainaxe_fixed)}']
for u,old,new,per in chainaxe_fixed: lines.append(f'  + {u}: {old} -> {new} @ +{per}/model')
lines += ['',f'Redundant Rampager Chainaxe purchase selectors removed: {len(rampager_removed)}']+[f'  + {x}' for x in rampager_removed]
lines += ['','Personal character/Sergeant Armoury Chainaxe options are unchanged. Existing World Eaters retinues and R3 fixes are preserved.']
OUT.write_text('\n'.join(lines),encoding='utf-8')
print('\n'.join(lines))
