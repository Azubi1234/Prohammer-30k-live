from pathlib import Path
import re
import xml.etree.ElementTree as ET

CAT=Path('Legiones Astartes.cat'); IDX=Path('index.xml'); OUT=Path('inspection-live-r9-ultramarines-command-retinue-fix.txt')
NS='http://www.battlescribe.net/schema/catalogueSchema'; ET.register_namespace('',NS); C=lambda t:f'{{{NS}}}{t}'
ct=ET.parse(CAT); root=ct.getroot()
if root.get('revision')!='8': raise RuntimeError(f'Expected CAT 8, got {root.get("revision")}')
def findid(i): return next((x for x in root.iter() if x.get('id')==i),None)
def ensure(p,t):
 x=p.find(C(t))
 if x is None:x=ET.SubElement(p,C(t))
 return x

def hide_unless_any(e,ids,mid):
 ms=ensure(e,'modifiers')
 for x in list(ms):
  if x.get('id')==mid: ms.remove(x)
 m=ET.SubElement(ms,C('modifier'),{'id':mid,'type':'set','field':'hidden','value':'true'})
 cgs=ET.SubElement(m,C('conditionGroups')); cg=ET.SubElement(cgs,C('conditionGroup'),{'type':'and'}); cs=ET.SubElement(cg,C('conditions'))
 # hide only when ALL three armour choices are absent
 for i in ids:
  ET.SubElement(cs,C('condition'),{'type':'lessThan','value':'1','field':'selections','scope':'root-entry','childId':i,'shared':'true','includeChildSelections':'true','includeChildForces':'false'})

def replace_rule_text(e,rule_name,text):
 rs=e.find(C('rules'))
 if rs is None:return False
 hit=False
 for r in rs:
  if (r.get('name') or '')==rule_name:
   d=r.find(C('description'))
   if d is None:d=ET.SubElement(r,C('description'))
   d.text=text; hit=True
 return hit

log=[]
# Generic Praetor and Centurion: Terminator Command Squad exists only if the character actually wears Terminator armour.
pra_tc=findid('hq-praetor-ret-termcommand')
cen_tc=findid('hq-centurion-ret-termcommand')
if pra_tc is None or cen_tc is None: raise RuntimeError('Generic Terminator Command retinue source missing')
hide_unless_any(pra_tc,['hq-praetor-term','hq-praetor-tart','hq-praetor-cat'],'r9-praetor-termcommand-needs-term-armour')
hide_unless_any(cen_tc,['hq-centurion-term','hq-centurion-tart','hq-centurion-cat'],'r9-centurion-termcommand-needs-term-armour')
log.append('Generic Praetor Terminator Command Squad now appears only with Terminator/Tartaros/Cataphractii armour')
log.append('Generic Centurion Terminator Command Squad now appears only with Terminator/Tartaros/Cataphractii armour')

# Named XIII exceptions explicitly permitted by their own entries must NOT inherit the generic armour requirement in their explanatory rule.
for eid,label,text in [
 ('live-r2-r41-unit-xiii-4-marius-gage-first-master-retinue-1-hq-praetor-ret-termcommand','Marius Gage','Marius Gage may select this Legion Terminator Command Squad as his retinue. This explicit permission overrides the normal requirement for the selecting character to wear Terminator Armour. The squad occupies no separate Force Organisation slot.'),
 ('r6-guilliman-ret-1-hq-praetor-ret-termcommand','Roboute Guilliman','Roboute Guilliman may select this Legion Terminator Command Squad as his Primarch Retinue. This explicit permission overrides the normal requirement for the selecting character to wear Terminator Armour. The squad occupies no additional Force Organisation selection and otherwise follows the normal Primarch Retinue rules.'),
]:
 e=findid(eid)
 if e is None: raise RuntimeError('Missing XIII retinue clone '+eid)
 if not replace_rule_text(e,'Retinue',text):
  rs=ensure(e,'rules'); r=ET.SubElement(rs,C('rule'),{'id':'r9-'+eid+'-ret','name':'Retinue','hidden':'false'}); ET.SubElement(r,C('description')).text=text
 log.append(label+' Terminator Command retinue text corrected to its explicit source permission')

# Make the actual XIII named-character retinue group titles clearly alternative selections.
for hid in ('r41-unit-xiii-4-marius-gage-first-master','r41-unit-xiii-5-remus-ventanus','r41-unit-xiii-8-titus-prayto','r41-unit-xiii-9-xiii-roboute-guilliman-the-avenging-son'):
 h=findid(hid)
 if h is None: continue
 gs=h.find(C('selectionEntryGroups'))
 if gs is None: continue
 for g in gs:
  if 'retinue' in (g.get('name') or '').lower():
   g.set('name','Retinue — choose up to one (no separate FOC slot)' if 'guilliman' not in hid else 'Primarch Retinue — choose up to one (no additional FOC slot)')
log.append('XIII named-character retinue selectors relabelled as explicit choose-one functional selections')

root.set('revision','9'); ct.write(CAT,encoding='utf-8',xml_declaration=True)
idx=IDX.read_text(encoding='utf-8'); idx=re.sub(r'(filePath="Legiones Astartes\.cat"[^>]*dataRevision=")\d+("\s*/>)',r'\g<1>9\2',idx); IDX.write_text(idx,encoding='utf-8')
OUT.write_text('LIVE R9 — ULTRAMARINES COMMAND RETINUE FIX\nCAT=9 GSTref='+str(root.get('gameSystemRevision'))+'\n\n'+'\n'.join('• '+x for x in log),encoding='utf-8')
print(OUT.read_text(encoding='utf-8'))
