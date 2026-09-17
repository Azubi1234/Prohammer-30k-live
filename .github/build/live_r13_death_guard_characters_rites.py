from pathlib import Path
import re, xml.etree.ElementTree as ET
CAT=Path('Legiones Astartes.cat'); IDX=Path('index.xml'); OUT=Path('inspection-live-r13-death-guard-characters-rites.txt')
NS='http://www.battlescribe.net/schema/catalogueSchema'; ET.register_namespace('',NS); C=lambda t:f'{{{NS}}}{t}'
ct=ET.parse(CAT); root=ct.getroot()
if root.get('revision')!='12': raise RuntimeError(f'Expected CAT 12, got {root.get("revision")}')
def findid(i): return next((x for x in root.iter() if x.get('id')==i),None)
def ensure(p,t):
 x=p.find(C(t))
 if x is None: x=ET.SubElement(p,C(t))
 return x
def set_rule(e,id_,name,text):
 rs=ensure(e,'rules')
 for x in list(rs):
  if x.get('id')==id_: rs.remove(x)
 r=ET.SubElement(rs,C('rule'),{'id':id_,'name':name,'hidden':'false'}); ET.SubElement(r,C('description')).text=text
def hide_rule_named(e,name):
 rs=e.find(C('rules'))
 if rs is not None:
  for r in rs:
   if (r.get('name') or '')==name: r.set('hidden','true')
def add_ranged(e,id_,name,rng,s,ap,typ):
 ps=ensure(e,'profiles')
 for x in list(ps):
  if x.get('id')==id_: ps.remove(x)
 p=ET.SubElement(ps,C('profile'),{'id':id_,'name':name,'hidden':'false','typeId':'prof-ranged','typeName':'Ranged Weapon'})
 cs=ET.SubElement(p,C('characteristics'))
 for tid,n,v in [('ranged-range','Range',rng),('ranged-s','S',s),('ranged-ap','AP',ap),('ranged-type','Type',typ)]:
  c=ET.SubElement(cs,C('characteristic'),{'name':n,'typeId':tid}); c.text=v
def add_conditional_upgrade(e,id_,name,pts,rite_id):
 gs=ensure(e,'selectionEntryGroups')
 g=next((x for x in gs if x.get('id')=='r13-dg-reaping-upgrades'),None)
 if g is None:
  g=ET.SubElement(gs,C('selectionEntryGroup'),{'id':'r13-dg-reaping-upgrades','name':'The Reaping — Character Upgrades','hidden':'false'})
  ms=ET.SubElement(g,C('modifiers')); m=ET.SubElement(ms,C('modifier'),{'id':'r13-dg-reaping-upgrades-hide','type':'set','field':'hidden','value':'true'}); conds=ET.SubElement(m,C('conditions')); ET.SubElement(conds,C('condition'),{'type':'lessThan','value':'1','field':'selections','scope':'roster','childId':rite_id,'shared':'true','includeChildSelections':'true','includeChildForces':'false'})
 se=ensure(g,'selectionEntries')
 if any(x.get('id')==id_ for x in se): return
 u=ET.SubElement(se,C('selectionEntry'),{'id':id_,'name':name,'type':'upgrade','hidden':'false','import':'true'}); cs=ET.SubElement(u,C('constraints')); ET.SubElement(cs,C('constraint'),{'id':id_+'-max','type':'max','value':'1','field':'selections','scope':'parent','shared':'true','includeChildSelections':'true','includeChildForces':'false'}); costs=ET.SubElement(u,C('costs')); ET.SubElement(costs,C('cost'),{'name':'Points','typeId':'pts','value':str(pts)})
 set_rule(u,id_+'-rule','Rad Grenades','Rad Grenades follow the normal rules in the Legiones Astartes Army List.')

# Rites: replace giant copy-paste paragraphs with discrete rules.
reaping=findid('r25-rite-xiv-0-the-reaping'); creeping=findid('r25-rite-xiv-1-creeping-death')
for e in (reaping,creeping): hide_rule_named(e, (e.get('name') or '').split('—')[-1].strip())
set_rule(reaping,'r13-dg-reaping-superior','Superior Firepower','Legion Veteran Squads and Legion Heavy Support Squads may be selected as non-compulsory Troops choices. They may not fulfil compulsory Troops selections unless another rule specifically permits them to do so.')
set_rule(reaping,'r13-dg-reaping-implacable','Implacable','All Death Guard Infantry units gain Move Through Cover, including models wearing any form of Terminator Armour.')
set_rule(reaping,'r13-dg-reaping-dark-arsenal','Dark Arsenal','Any Death Guard Character or Independent Character may purchase Rad Grenades for +10 points.')
set_rule(reaping,'r13-dg-reaping-limitations','Limitations','Units in the Detachment may not make Advance Moves. Vehicles may not move Flat Out. Units may not deploy using Deep Strike, and units which are required to deploy using Deep Strike may not be selected. Footslogging Killers continues to apply.')
set_rule(creeping,'r13-dg-creeping-mist','Mist-Clad','Death Guard Infantry models in open ground receive a 5+ Cover Save against shooting attacks provided there is no enemy model within 12 inches. This does not improve an existing Cover Save.')
set_rule(creeping,'r13-dg-creeping-biophage','Bio-Phage Bombardment','After both armies have deployed, including Scouts and Infiltrators, roll a D6 for every wood or jungle terrain piece. On a 4+, its Cover Save is worsened by 1 and it counts as Dangerous Terrain to all models except models with Legiones Astartes (Death Guard).')
set_rule(creeping,'r13-dg-creeping-traitor','Traitor Only','Creeping Death may only be selected by a Traitor Death Guard army.')

# Character entries
chars={
'r41-unit-xiv-3-calas-typhon-first-captain':[
 ('Wargear','Cataphractii Terminator Armour; Manreaper; Alchem Flamer.'),('Manreaper','A Two-Handed Power Weapon. At the beginning of each Assault phase in which the bearer is engaged, roll a D3; the bearer gains that many additional Attacks until the end of the phase. If all attacks are directed against a single separately targetable enemy model, the bonus is only +1 Attack. No bonus Attack is gained for a second close-combat weapon.'),('Latent Psyker','Typhon is treated as Psyker (Mastery Level 1) solely for Aura of Pestilence and Perils of the Warp. He knows no other psychic powers and tests for Aura using Leadership 7.'),('Aura of Pestilence','At the beginning of either player’s Assault phase Typhon may take a Psychic Test. If passed, every enemy model within 2 inches suffers -1 Attack, minimum 1, until the end of the phase. If failed, every friendly model within 2 inches suffers the penalty instead. Typhon may fight normally.')],
'r41-unit-xiv-4-crysos-morturg':[
 ('Wargear','Power Armour; Refractor Field; Power weapon; Combi-Alchem Flamer; Bolt pistol; Frag grenades; Rad grenades.'),('Psychic Powers','Morturg selects one psychic power from the normal Legion Librarian Psychic Power list and follows the normal ProHammer rules for Psykers and Mastery Level 1.'),('Master of Ambush','Morturg and one Death Guard Infantry unit he has joined before deployment may deploy using Infiltrate. Morturg must remain joined to that unit when it is deployed.'),('Destroyer Officer','Morturg may join a Legion Destroyer Squad or Mortus Poisoner Squad despite the normal restrictions imposed by Destroyer Cadre.')],
'r41-unit-xiv-5-durak-rask':[
 ('Wargear','Artificer Armour; Refractor Field; Thunder hammer; Volkite Serpenta; Nuncio Vox; Phosphex Bomb; Frag grenades.'),('Art of Destruction','Durak Rask and any Death Guard Infantry unit he has joined have the Tank Hunters special rule.')],
'r41-unit-xiv-6-ignatius-grulgor':[
 ('Wargear','Power Armour; Refractor Field; Power weapon; Bolter; Bolt pistol; Frag grenades.'),('The Eater of Lives','The first time Grulgor is reduced to 0 Wounds, roll a D6 before removing him. On 1–4 he is removed normally. On 5+, he remains with 1 Wound and gains Daemon, Fearless and Feel No Pain (5+) for the rest of the battle. This may only occur once per battle.')],
'r41-unit-xiv-7-nathaniel-garro':[
 ('Wargear','Artificer Armour; Aquila Imperator; Libertas; Bolt pistol; Frag grenades.'),('Libertas','Libertas is a Two-Handed, Master-crafted Power Weapon which grants Garro +2 Strength. Garro receives no additional Attack for fighting with a second close-combat weapon while using Libertas.'),('Aquila Imperator','The Aquila Imperator grants Garro a 4+ Invulnerable Save. Whenever Garro or a unit he has joined would be affected by an enemy psychic power, roll a D6. On a 5+, that psychic power is nullified and has no effect upon Garro or his unit. Only one nullification roll may be attempted against each psychic power.')],
}
for uid,rs in chars.items():
 e=findid(uid); hide_rule_named(e,'Source Entry')
 for i,(n,t) in enumerate(rs): set_rule(e,f'r13-dg-{uid}-rule-{i}',n,t)
# Custom ranged profiles that were absent from character entries.
add_ranged(findid('r41-unit-xiv-3-calas-typhon-first-captain'),'r13-typhon-alchem','Alchem Flamer','Template','2','5','Assault 1, Poisoned (3+)')
add_ranged(findid('r41-unit-xiv-4-crysos-morturg'),'r13-morturg-combi-alchem','Combi-Alchem Flamer — Alchem shot','Template','2','5','Assault 1, Poisoned (3+), Combi-weapon')
add_ranged(findid('r41-unit-xiv-5-durak-rask'),'r13-rask-phosphex','Phosphex Bomb','6\"','5','2','Assault 1, Blast, One Use, Poisoned (3+), Lingering Death')

# Reaping Rad Grenades as real selectable upgrades for generic and named DG Characters that do not already carry them.
for uid in ['hq-praetor','hq-centurion','r41-unit-xiv-3-calas-typhon-first-captain','r41-unit-xiv-5-durak-rask','r41-unit-xiv-6-ignatius-grulgor','r41-unit-xiv-7-nathaniel-garro']:
 e=findid(uid)
 if e is not None: add_conditional_upgrade(e,'r13-'+uid+'-rad','Rad Grenades',10,'r25-rite-xiv-0-the-reaping')

# Mortal Mortarion: replace source block with a clean proper entry.
mort=findid('r41-unit-xiv-8-xiv-mortarion-the-reaper'); hide_rule_named(mort,'Source Entry')
M=[
('Wargear','Barbaran Plate; Silence; Lantern; Phosphex Bomb; Frag Grenades.'),
('Barbaran Plate','Barbaran Plate counts as Primarch Armour.'),
('Silence','Silence is a Two-Handed Power Weapon. Attacks are resolved at +1 Strength and have Rampage. Any unsaved Wound inflicted against a model without the Primarch special rule becomes a Massive Wound and inflicts D3 Wounds instead of one.'),
('Barbaran Endurance','Mortarion has Feel No Pain (5+).'),
('Witch-Spite','Whenever Mortarion or a unit he has joined makes a Deny the Witch roll, a failed roll may be re-rolled. Mortarion’s Adamantium Will grants +2 to Deny the Witch rolls instead of the normal +1.'),
("The Reaper's Advance",'Friendly Death Guard Infantry within 12 inches of Mortarion may fire Rapid Fire weapons as though they had remained stationary and may re-roll failed Pinning tests.'),
('Toxic Miasma','Enemy non-Vehicle models in base contact with Mortarion suffer -1 Toughness while they remain in base contact with him.'),
('Poison Cannot Kill Death','Poisoned attacks against Mortarion do not use their fixed To Wound value. Resolve them using Strength against Toughness normally. A Poisoned attack with no Strength characteristic wounds Mortarion only on an unmodified 6.'),
('Primarch Retinue','Mortarion may select one Deathshroud Terminator Squad as his Primarch Retinue. He may not select a Legion Honour Guard Squad or Legion Terminator Command Squad as his Primarch Retinue.')]
for i,(n,t) in enumerate(M): set_rule(mort,f'r13-mortarion-{i}',n,t)
add_ranged(mort,'r13-mortarion-lantern','Lantern','18\"','8','2','Assault 1, Armourbane, Master-crafted')
add_ranged(mort,'r13-mortarion-phosphex','Phosphex Bomb','6\"','5','2','Assault 1, Blast, One Use, Poisoned (3+), Lingering Death')

root.set('revision','13'); ct.write(CAT,encoding='utf-8',xml_declaration=True)
idx=IDX.read_text(encoding='utf-8'); idx=re.sub(r'(filePath="Legiones Astartes\.cat"[^>]*dataRevision=")\d+("\s*/>)',r'\g<1>13\2',idx); IDX.write_text(idx,encoding='utf-8')
OUT.write_text('LIVE R13 — DEATH GUARD CHARACTERS & RITES\nCAT=13 GSTref='+str(root.get('gameSystemRevision'))+'\n\n• Character wargear/special rules rebuilt as discrete New Recruit rules\n• Typhon Alchem Flamer, Morturg Combi-Alchem profile and Rask Phosphex profile added\n• Mortarion rebuilt as a proper discrete entry with Silence, Lantern, Phosphex and all named rules\n• The Reaping split into functional/readable effects and conditional +10 Rad Grenade character upgrades\n• Creeping Death split into readable effects while preserving its Traitor-only selector gate\n',encoding='utf-8')
print(OUT.read_text())
