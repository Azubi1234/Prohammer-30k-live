from pathlib import Path
import os,re,xml.etree.ElementTree as ET

CAT=Path('Legiones Astartes.cat')
IDX=Path('index.xml')
OUT=Path('inspection-live-r30-veteran-bolter-replacements.txt')
APPLY=os.environ.get('R30_APPLY','0')=='1'

cat=CAT.read_text(encoding='utf-8')
idx=IDX.read_text(encoding='utf-8')
if 'revision="29"' not in cat[:1500]:
    raise RuntimeError('R30 expects CAT revision 29')
if 'dataRevision="29"' not in idx:
    raise RuntimeError('R30 expects index dataRevision 29')

NS='http://www.battlescribe.net/schema/catalogueSchema'
C=lambda t:f'{{{NS}}}{t}'

def extract_block(text,tag,eid):
    pos=text.find('id="'+eid+'"')
    if pos<0: raise RuntimeError(f'{tag} id not found: {eid}')
    start=text.rfind('<'+tag,0,pos)
    if start<0: raise RuntimeError(f'opening {tag} not found: {eid}')
    tok=re.compile(r'<'+re.escape(tag)+r'\b|</'+re.escape(tag)+r'>')
    depth=0
    for m in tok.finditer(text,start):
        if m.group(0).startswith('</'): depth-=1
        else: depth+=1
        if depth==0:
            return start,m.end(),text[start:m.end()]
    raise RuntimeError(f'unbalanced {tag}: {eid}')

def replace_block(text,tag,eid,fn):
    s,e,b=extract_block(text,tag,eid)
    return text[:s]+fn(b)+text[e:]

def set_constraint_value(block,cid,value):
    pat=re.compile(r'(<constraint\b(?=[^>]*\bid="'+re.escape(cid)+r'")[^>]*\bvalue=")[^"]*(")')
    out,n=pat.subn(r'\g<1>'+str(value)+r'\2',block,count=1)
    if n!=1: raise RuntimeError(f'constraint {cid} not found/set ({n})')
    return out

def remove_ranged_modifier_containers(block):
    # Remove only modifier containers that directly/indirectly target the veteran-ranged-max field.
    # This cleans the duplicate modifier-container situation left by older passes without touching
    # the Recon Company visibility modifier on the Sniper Rifle.
    pat=re.compile(r'\s*<modifiers>.*?</modifiers>',re.S)
    def repl(m):
        return '' if 'field="veteran-ranged-max"' in m.group(0) else m.group(0)
    out=pat.sub(repl,block)
    return out

# Specialist selections that consume one bolter replacement slot.
root=ET.fromstring(cat.encode('utf-8'))
def fid(i): return next((x for x in root.iter() if x.get('id')==i),None)
sg=fid('veteran-specialists')
if sg is None: raise RuntimeError('veteran-specialists missing')
spec_ids=[]
for tag in (C('selectionEntries'),C('entryLinks')):
    box=sg.find(tag)
    if box is not None:
        spec_ids += [x.get('id') for x in list(box) if x.get('id')]

def patch_ranged(b):
    b=set_constraint_value(b,'veteran-ranged-max',1)
    b=remove_ranged_modifier_containers(b)

    mods=[f'''<modifier id="r30-veteran-ranged-per-model" type="increment" value="1" field="veteran-ranged-max">
              <repeats><repeat value="1" repeats="1" field="selections" scope="root-entry" childId="veteran-included" shared="true" roundUp="false" includeChildSelections="false" /></repeats>
            </modifier>''']
    for i,sid in enumerate(spec_ids):
        mods.append(f'''<modifier id="r30-veteran-ranged-specialist-{i}" type="increment" value="-1" field="veteran-ranged-max">
              <repeats><repeat value="1" repeats="1" field="selections" scope="root-entry" childId="{sid}" shared="true" roundUp="false" includeChildSelections="true" /></repeats>
            </modifier>''')
    newmods='<modifiers>\n            '+'\n            '.join(mods)+'\n          </modifiers>'

    # Put modifiers in the same working structural position as the existing ranged group:
    # after the local selectionEntries (Recon sniper entry), before entryLinks.
    if '</selectionEntries>' in b:
        p=b.find('</selectionEntries>')+len('</selectionEntries>')
        b=b[:p]+newmods+b[p:]
    else:
        p=b.find('<entryLinks>')
        if p<0: raise RuntimeError('veteran-ranged has no insertion point')
        b=b[:p]+newmods+b[p:]

    # Each individual bolter-replacement option must be numeric rather than checkbox-only.
    for cid in (
        'r35-recon-veteran-sniper-max',
        'veteran-ranged-foe-max',
        'veteran-ranged-cf-max',
        'veteran-ranged-cv-max',
        'veteran-ranged-cm-max',
        'veteran-ranged-cp-max',
    ):
        b=set_constraint_value(b,cid,10)
    return b

cat=replace_block(cat,'selectionEntryGroup','veteran-ranged',patch_ranged)

# Revision bump.
cat,n=re.subn(r'(<catalogue\b[^>]*\brevision=")29(")',r'\g<1>30\2',cat,count=1)
if n!=1: raise RuntimeError('CAT 29 -> 30 bump failed')
idx,n=re.subn(r'(filePath="Legiones Astartes\.cat"[^>]*dataRevision=")29(")',r'\g<1>30\2',idx,count=1)
if n!=1: raise RuntimeError('index 29 -> 30 bump failed')

# Validation.
r=ET.fromstring(cat.encode('utf-8'))
def F(i): return next((x for x in r.iter() if x.get('id')==i),None)
def con(e,cid):
    cs=e.find(C('constraints'))
    return next((x for x in list(cs or []) if x.get('id')==cid),None)

g=F('veteran-ranged')
if g is None: raise RuntimeError('veteran-ranged missing after patch')
if con(g,'veteran-ranged-max').get('value')!='1':
    raise RuntimeError('veteran-ranged base max is not 1')

# Exactly one direct modifiers container on the group, with the per-model scaler.
dmods=g.findall('./'+C('modifiers'))
if len(dmods)!=1:
    raise RuntimeError(f'veteran-ranged direct modifier containers={len(dmods)}, expected 1')
if F('r30-veteran-ranged-per-model') is None:
    raise RuntimeError('new per-model ranged scaler missing')
rep=next(F('r30-veteran-ranged-per-model').iter(C('repeat')),None)
if rep is None or rep.get('value')!='1' or rep.get('childId')!='veteran-included':
    raise RuntimeError('new ranged per-model repeat wrong')

for eid,cid in (
    ('r35-recon-veteran-sniper','r35-recon-veteran-sniper-max'),
    ('veteran-ranged-foe','veteran-ranged-foe-max'),
    ('veteran-ranged-cf','veteran-ranged-cf-max'),
    ('veteran-ranged-cv','veteran-ranged-cv-max'),
    ('veteran-ranged-cm','veteran-ranged-cm-max'),
    ('veteran-ranged-cp','veteran-ranged-cp-max'),
):
    e=F(eid)
    c=con(e,cid)
    if c is None or c.get('value')!='10':
        raise RuntimeError(f'{eid} individual numeric cap wrong')

# Veteran squad source size from R29 must remain untouched: 5–10 total.
v=F('veteran-included')
if con(v,'veteran-included-min').get('value')!='4' or con(v,'veteran-included-max').get('value')!='9':
    raise RuntimeError('Veteran size changed unexpectedly')

lines=[
 'LIVE R30 — VETERAN BOLTER REPLACEMENT UI FIX',
 'MODE='+('APPLY' if APPLY else 'DRY RUN'),
 'CAT 29 -> 30',
 '',
 '• Bolter Replacements now use one clean direct modifier container, matching the working Close Combat Weapon replacement structure.',
 '• The pool scales to the actual Veteran Squad size: Sergeant + selected Veterans.',
 '• Specialist Weapons still consume one Bolter replacement slot each.',
 '• Foeblaster Boltgun, all Combi-Weapon choices and Recon Sniper Rifle have numeric max 10, so New Recruit shows quantity controls rather than checkbox-only choices.',
 '• Veteran Squad size remains 5–10 models total (1 Sergeant + 4–9 Veterans).',
 '',
 'VALIDATION: PASS'
]
OUT.write_text('\n'.join(lines),encoding='utf-8')

if APPLY:
    CAT.write_text(cat,encoding='utf-8',newline='')
    IDX.write_text(idx,encoding='utf-8',newline='')

print('\n'.join(lines))
