from pathlib import Path
import re
import xml.etree.ElementTree as ET

CAT=Path('Legiones Astartes.cat'); IDX=Path('index.xml'); OUT=Path('inspection-live-r10-ultramarines-mantle-fix.txt')
NS='http://www.battlescribe.net/schema/catalogueSchema'; ET.register_namespace('',NS); C=lambda t:f'{{{NS}}}{t}'
ct=ET.parse(CAT); root=ct.getroot()
if root.get('revision')!='9': raise RuntimeError(f'Expected CAT revision 9, got {root.get("revision")}')

def ensure(p,t):
    x=p.find(C(t))
    if x is None: x=ET.SubElement(p,C(t))
    return x

def groups(e):
    gs=e.find(C('selectionEntryGroups'))
    return list(gs) if gs is not None else []

def items(g):
    out=[]
    for cn in ('selectionEntries','entryLinks'):
        c=g.find(C(cn))
        if c is not None: out += list(c)
    return out

def add_hide_unless(e,child_id,mid):
    ms=ensure(e,'modifiers')
    for x in list(ms):
        if x.get('id')==mid: ms.remove(x)
    m=ET.SubElement(ms,C('modifier'),{'id':mid,'type':'set','field':'hidden','value':'true'})
    cs=ET.SubElement(m,C('conditions'))
    ET.SubElement(cs,C('condition'),{'type':'lessThan','value':'1','field':'selections','scope':'root-entry','childId':child_id,'shared':'true','includeChildSelections':'true','includeChildForces':'false'})

def add_rule(e,id_,name,text):
    rs=ensure(e,'rules')
    for x in list(rs):
        if x.get('id')==id_: rs.remove(x)
    r=ET.SubElement(rs,C('rule'),{'id':id_,'name':name,'hidden':'false'})
    ET.SubElement(r,C('description')).text=text

fixed=[]
for host in list(root.iter(C('selectionEntry'))):
    if host.get('type')!='unit': continue
    gs=host.find(C('selectionEntryGroups'))
    if gs is None: continue
    armour=None; mantle=None; mantle_container=None; mantle_tag=None; artificer=None
    for g in list(gs):
        for x in items(g):
            nm=(x.get('name') or '').strip().lower()
            if x.get('targetId')=='r45-um-mantle' or nm=='mantle of ultramar':
                armour=g; mantle=x
                for cn in ('selectionEntries','entryLinks'):
                    c=g.find(C(cn))
                    if c is not None and x in list(c): mantle_container=c; mantle_tag=cn
        for x in items(g):
            if (x.get('name') or '').strip().lower()=='artificer armour':
                # prefer artificer from same armour group as mantle
                if mantle is not None and g is armour: artificer=x
    if mantle is None: continue
    if artificer is None:
        for x in items(armour):
            if (x.get('name') or '').strip().lower()=='artificer armour': artificer=x; break
    if artificer is None:
        raise RuntimeError(f'Mantle found on {host.get("id")} but no local Artificer Armour selection found')

    # Move Mantle out of the mutually-exclusive armour replacement group.
    mantle_container.remove(mantle)
    gid=f'r10-{host.get("id")}-um-armour-upgrade'
    for old in list(gs):
        if old.get('id')==gid: gs.remove(old)
    ug=ET.SubElement(gs,C('selectionEntryGroup'),{'id':gid,'name':'Ultramarines Armour Upgrade','hidden':'false'})
    dest=ET.SubElement(ug,C(mantle_tag))
    mantle.set('name','Mantle of Ultramar — upgrade Artificer Armour')
    dest.append(mantle)
    add_hide_unless(mantle,artificer.get('id'),mantle.get('id')+'-r10-requires-artificer')
    add_rule(mantle,mantle.get('id')+'-r10-secondary','Secondary Armour Upgrade','Mantle of Ultramar is an upgrade to Artificer Armour. This option is available only while Artificer Armour is equipped and does not replace the Artificer Armour selection itself.')
    fixed.append(f'{host.get("id")} | {host.get("name")} | Artificer={artificer.get("id")} | Mantle={mantle.get("id")}')

if not fixed: raise RuntimeError('No Mantle of Ultramar selections found')
root.set('revision','10'); ct.write(CAT,encoding='utf-8',xml_declaration=True)
idx=IDX.read_text(encoding='utf-8')
idx,n=re.subn(r'(filePath="Legiones Astartes\.cat"[^>]*dataRevision=")9("\s*/>)',r'\g<1>10\2',idx,count=1)
if n!=1: raise RuntimeError(f'Expected index revision 9 once, changed {n}')
IDX.write_text(idx,encoding='utf-8')
OUT.write_text('LIVE R10 — ULTRAMARINES MANTLE FIX\nCAT=10 GSTref='+str(root.get('gameSystemRevision'))+'\n\n• Mantle of Ultramar moved out of the mutually-exclusive Armour Replacement group.\n• Mantle is now a secondary Artificer Armour upgrade and is hidden unless Artificer Armour is equipped.\n\nAffected entries:\n'+'\n'.join('  + '+x for x in fixed),encoding='utf-8')
print(OUT.read_text(encoding='utf-8'))
