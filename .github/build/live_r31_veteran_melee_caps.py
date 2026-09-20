from pathlib import Path
import os,re,xml.etree.ElementTree as ET

CAT=Path('Legiones Astartes.cat')
IDX=Path('index.xml')
OUT=Path('inspection-live-r31-veteran-melee-caps.txt')
APPLY=os.environ.get('R31_APPLY','0')=='1'

cat=CAT.read_text(encoding='utf-8')
idx=IDX.read_text(encoding='utf-8')
if 'revision="30"' not in cat[:1500]:
    raise RuntimeError('R31 expects CAT revision 30')
if 'dataRevision="30"' not in idx:
    raise RuntimeError('R31 expects index dataRevision 30')

def set_constraint_value(text,cid,value):
    pat=re.compile(r'(<constraint\b(?=[^>]*\bid="'+re.escape(cid)+r'")[^>]*\bvalue=")[^"]*(")')
    out,n=pat.subn(r'\g<1>'+str(value)+r'\2',text,count=1)
    if n!=1:
        raise RuntimeError(f'constraint {cid} not found/set ({n})')
    return out

# Any individual close-combat replacement option is capped at the unit's
# absolute maximum size of 10 models. The parent group still scales with the
# actual selected squad size (5-10), so the effective legal total remains correct.
for cid in (
    'veteran-melee-chainaxe-max',
    'veteran-melee-rending-max',
    'veteran-melee-power-max',
    'r40-da-warblade-veteran-melee-power-max',
):
    cat=set_constraint_value(cat,cid,10)

cat,n=re.subn(r'(<catalogue\b[^>]*\brevision=")30(")',r'\g<1>31\2',cat,count=1)
if n!=1: raise RuntimeError('CAT 30 -> 31 bump failed')
idx,n=re.subn(r'(filePath="Legiones Astartes\.cat"[^>]*dataRevision=")30(")',r'\g<1>31\2',idx,count=1)
if n!=1: raise RuntimeError('index 30 -> 31 bump failed')

NS='http://www.battlescribe.net/schema/catalogueSchema'
C=lambda t:f'{{{NS}}}{t}'
r=ET.fromstring(cat.encode('utf-8'))
def F(i): return next((x for x in r.iter() if x.get('id')==i),None)
def con(e,cid):
    cs=e.find(C('constraints'))
    return next((x for x in list(cs or []) if x.get('id')==cid),None)

for eid,cid in (
    ('veteran-melee-chainaxe','veteran-melee-chainaxe-max'),
    ('veteran-melee-rending','veteran-melee-rending-max'),
    ('veteran-melee-power','veteran-melee-power-max'),
    ('r40-da-warblade-veteran-melee-power','r40-da-warblade-veteran-melee-power-max'),
):
    e=F(eid)
    c=con(e,cid) if e is not None else None
    if c is None or c.get('value')!='10':
        raise RuntimeError(f'{eid} max is not 10')

# Preserve the correct Veteran size and dynamic parent-pool logic.
v=F('veteran-included')
if con(v,'veteran-included-min').get('value')!='4' or con(v,'veteran-included-max').get('value')!='9':
    raise RuntimeError('Veteran squad size changed unexpectedly')
g=F('veteran-melee')
if con(g,'veteran-melee-max').get('value')!='1':
    raise RuntimeError('Veteran melee dynamic base changed unexpectedly')
if F('r29-veteran-melee-per-model') is None:
    raise RuntimeError('Veteran melee per-model scaler missing')

lines=[
 'LIVE R31 — VETERAN MELEE INDIVIDUAL CAPS',
 'MODE='+('APPLY' if APPLY else 'DRY RUN'),
 'CAT 30 -> 31',
 '',
 '• Chainaxe maximum: 10.',
 '• Power Weapon maximum: 10.',
 '• Rending Weapon maximum: 10.',
 '• Calibanite Warblade maximum: 10.',
 '• The parent Close Combat Weapon Replacements pool still scales with the actual squad size, so a 5-model squad can only choose 5 total replacements and a 10-model squad can choose 10.',
 '• Veteran Squad remains 1 Sergeant + 4–9 Veterans (5–10 models total).',
 '',
 'VALIDATION: PASS'
]
OUT.write_text('\n'.join(lines),encoding='utf-8')
if APPLY:
    CAT.write_text(cat,encoding='utf-8',newline='')
    IDX.write_text(idx,encoding='utf-8',newline='')
print('\n'.join(lines))
