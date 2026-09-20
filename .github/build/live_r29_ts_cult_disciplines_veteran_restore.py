from pathlib import Path
import os,re,xml.etree.ElementTree as ET

CAT=Path('Legiones Astartes.cat')
IDX=Path('index.xml')
OUT=Path('inspection-live-r29-ts-cult-disciplines-veteran-restore.txt')
APPLY=os.environ.get('R29_APPLY','0')=='1'

cat=CAT.read_text(encoding='utf-8')
idx=IDX.read_text(encoding='utf-8')
if 'revision="28"' not in cat[:1500]:
    raise RuntimeError('R29 expects CAT revision 28')
if 'dataRevision="28"' not in idx:
    raise RuntimeError('R29 expects index dataRevision 28')

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
        if depth==0: return start,m.end(),text[start:m.end()]
    raise RuntimeError(f'unbalanced {tag}: {eid}')

def replace_block(text,tag,eid,fn):
    s,e,b=extract_block(text,tag,eid)
    return text[:s]+fn(b)+text[e:]

def set_open_attr(block,tag,eid,attr,value):
    pat=re.compile(r'(<'+re.escape(tag)+r'\b(?=[^>]*\bid="'+re.escape(eid)+r'")[^>]*\b'+re.escape(attr)+r'=")[^"]*(")')
    out,n=pat.subn(r'\g<1>'+str(value)+r'\2',block,count=1)
    if n==0:
        pat2=re.compile(r'(<'+re.escape(tag)+r'\b(?=[^>]*\bid="'+re.escape(eid)+r'")[^>]*)(/?>)')
        out,n=pat2.subn(r'\1 '+attr+'="'+str(value)+r'"\2',block,count=1)
    if n!=1: raise RuntimeError(f'could not set {attr} on {eid}: {n}')
    return out

def set_constraint_value(block,cid,value):
    pat=re.compile(r'(<constraint\b(?=[^>]*\bid="'+re.escape(cid)+r'")[^>]*\bvalue=")[^"]*(")')
    out,n=pat.subn(r'\g<1>'+str(value)+r'\2',block,count=1)
    if n!=1: raise RuntimeError(f'constraint {cid} not found/set ({n})')
    return out

def replace_direct_modifiers(block,newmods):
    cut_candidates=[x for x in (block.find('<entryLinks>'),block.find('<selectionEntries>'),block.find('<selectionEntryGroups>')) if x>=0]
    cut=min(cut_candidates) if cut_candidates else len(block)
    ms=block.find('<modifiers>',0,cut)
    if ms>=0:
        me=block.find('</modifiers>',ms,cut)
        if me<0: raise RuntimeError('direct modifiers not balanced')
        return block[:ms]+newmods+block[me+len('</modifiers>'):]
    return block[:cut]+newmods+block[cut:]

def remove_modifier_id(block,mid):
    pat=re.compile(r'\s*<modifier\b(?=[^>]*\bid="'+re.escape(mid)+r'")[^>]*>.*?</modifier>',re.S)
    return pat.sub('',block)

def append_modifier_to_entry(text,eid,modifier_xml,mid):
    def fn(b):
        b=remove_modifier_id(b,mid)
        ms=b.find('<modifiers>')
        if ms>=0:
            me=b.find('</modifiers>',ms)
            if me<0: raise RuntimeError('entry modifiers unbalanced '+eid)
            return b[:me]+modifier_xml+b[me:]
        close=b.rfind('</selectionEntry>')
        if close<0: raise RuntimeError('selectionEntry close missing '+eid)
        return b[:close]+'<modifiers>'+modifier_xml+'</modifiers>'+b[close:]
    return replace_block(text,'selectionEntry',eid,fn)

def replace_rule_desc(text,rid,newtext):
    def fn(b):
        pat=re.compile(r'(<description>)(.*?)(</description>)',re.S)
        out,n=pat.subn(lambda m:m.group(1)+newtext+m.group(3),b,count=1)
        if n!=1: raise RuntimeError('description missing '+rid)
        return out
    return replace_block(text,'rule',rid,fn)

# ---------------------------------------------------------------------------
# 1. CULT -> DISCIPLINE FOR EVERY CULT-ASSIGNED TS PSYKER/BROTHERHOOD
# ---------------------------------------------------------------------------
CULT_TO_DISC={'Pavoni':'Biomancy','Raptora':'Telekinesis','Corvidae':'Divination','Athanaeans':'Telepathy','Pyrae':'Pyromancy'}
DISC_TO_CULT={v:k for k,v in CULT_TO_DISC.items()}

def parse():
    return ET.fromstring(cat.encode('utf-8'))

def fid(root,i):
    return next((x for x in root.iter() if x.get('id')==i),None)

def choices(g):
    ses=g.find(C('selectionEntries'))
    return list(ses) if ses is not None else []

def gate_pair(cult_gid,disc_gid,prefix):
    global cat
    r=parse()
    cg=fid(r,cult_gid); dg=fid(r,disc_gid)
    if cg is None or dg is None:
        raise RuntimeError('Missing Cult/Discipline pair '+cult_gid+' / '+disc_gid)
    cults={x.get('name'):x.get('id') for x in choices(cg)}
    discs={x.get('name'):x.get('id') for x in choices(dg)}
    for d,deid in discs.items():
        cult=DISC_TO_CULT.get(d)
        if cult not in cults: continue
        mid=prefix+'-'+re.sub(r'[^a-z0-9]+','-',d.lower()).strip('-')
        mod=f'''<modifier id="{mid}" type="set" value="true" field="hidden"><conditions><condition type="lessThan" value="1" field="selections" scope="root-entry" childId="{cults[cult]}" shared="true" includeChildSelections="true" includeChildForces="false" /></conditions></modifier>'''
        cat=append_modifier_to_entry(cat,deid,mod,mid)

# Generic XV characters.
gate_pair('r45-cult-hq-praetor','r19-ts-praetor-disciplines','r29-praetor-cult-disc')
gate_pair('r45-cult-hq-centurion','r19-ts-centurion-disciplines','r29-centurion-cult-disc')

# Fellowships Tactical Brotherhood.
gate_pair('r45-cult-tactical-unit','r19-ts-tactical-brotherhood-disciplines','r29-tactical-cult-disc')

# Reassert all Brotherhood mappings so the catalogue has one consistent rule.
gate_pair('r45-cult-veteran-unit','r19-ts-veteran-unit-brotherhood-disciplines','r29-veteran-cult-disc')
gate_pair('r45-cult-terminator-unit','r19-ts-terminator-unit-brotherhood-disciplines','r29-terminator-cult-disc')
gate_pair('r45-cult-r41-unit-xv-0-sekhmet-terminator-cabal','r19-ts-sekhmet-disciplines','r29-sekhmet-cult-disc')
gate_pair('r27-guard-r45-cult-r41-unit-xv-0-sekhmet-terminator-cabal','r27-guard-r19-ts-sekhmet-disciplines','r29-guard-sekhmet-cult-disc')
gate_pair('r45-cult-r41-unit-xv-2-ammitara-occult-intercession-cabal','r19-ts-ammitara-disciplines','r29-ammitara-cult-disc')

# Make the universal rule explicit.
r=parse()
ref=fid(r,'r25-legion-xv-reference')
d=ref.find(C('description'))
old=d.text or ''
needle="Unless specifically stated otherwise in the model or unit's own entry, a Psyker may select powers from only one Psychic Discipline. A Psyker may not select powers from multiple Disciplines."
repl=needle+" If the Psyker is assigned to a Prosperine Cult, that Psychic Discipline must correspond to its Cult: Pavoni — Biomancy; Raptora — Telekinesis; Corvidae — Divination; Athanaeans — Telepathy; Pyrae — Pyromancy. A unit or model whose own entry specifically states that it is not assigned to a Prosperine Cult follows the discipline access written in its own entry instead."
if needle not in old:
    raise RuntimeError('Approved one-discipline wording not found in reference rule')
new=old.replace(needle,repl,1)
# Fellowships text must not contradict the Cult mapping.
new=new.replace(
    'A Tactical Squad upgraded in this manner selects one psychic power from the normal Psychic Disciplines available to Thousand Sons Psykers and gains the Cult Mastery benefit of its chosen Prosperine Cult.',
    'A Tactical Squad upgraded in this manner selects one psychic power from the Psychic Discipline associated with its chosen Prosperine Cult and gains the Cult Mastery benefit of that Cult.',
    1
)
def patch_ref(b):
    pat=re.compile(r'(<description>)(.*?)(</description>)',re.S)
    out,n=pat.subn(lambda m:m.group(1)+new+m.group(3),b,count=1)
    if n!=1: raise RuntimeError('reference description replacement failed')
    return out
cat=replace_block(cat,'rule','r25-legion-xv-reference',patch_ref)

cat=replace_rule_desc(cat,'r18-ts-praetor-psyker-rule',
    'In a Thousand Sons Detachment, a Legion Praetor is a Psyker (Mastery Level 2). It selects its psychic powers from the single Psychic Discipline associated with its chosen Prosperine Cult: Pavoni — Biomancy; Raptora — Telekinesis; Corvidae — Divination; Athanaeans — Telepathy; Pyrae — Pyromancy, unless another rule explicitly states otherwise. Activating a Force Weapon counts as the use of a psychic power, and the same power may not be used more than once in the same player turn.')
cat=replace_rule_desc(cat,'r18-ts-centurion-psyker-rule',
    'In a Thousand Sons Detachment, a Legion Centurion and its Consul variants are Psykers (Mastery Level 1) unless another rule grants a higher Mastery Level. Its psychic powers are selected from the single Psychic Discipline associated with its chosen Prosperine Cult: Pavoni — Biomancy; Raptora — Telekinesis; Corvidae — Divination; Athanaeans — Telepathy; Pyrae — Pyromancy. A Librarian Consul follows the normal Librarian upgrade rules; an Epistolary is Mastery Level 2.')

# Discrete Fellowships rule.
cat=replace_rule_desc(cat,'r19-fellows-circles',
    'A 20-model Legion Tactical Squad may purchase Brotherhood of Psykers (Mastery Level 1) for +25 points. It selects one power from the Psychic Discipline associated with its chosen Prosperine Cult, gains that Cult Mastery and follows the normal Psychic Brotherhood rules.')

# ---------------------------------------------------------------------------
# 2. RESTORE VETERANS TO SOURCE 5–10 MODELS AND CORRECT INDIVIDUAL CAPS
# ---------------------------------------------------------------------------
def patch_vet_count(b):
    b=set_open_attr(b,'selectionEntry','veteran-included','defaultAmount',4)
    b=set_constraint_value(b,'veteran-included-min',4)
    b=set_constraint_value(b,'veteran-included-max',9)
    return b
cat=replace_block(cat,'selectionEntry','veteran-included',patch_vet_count)

# Any model = Sergeant + Veterans, so root option pools are 5–10 actual models.
# Base 1 (Sergeant) + one for each selected Veteran.
def patch_any_model_group(b,gid,cid,prefix):
    b=set_constraint_value(b,cid,1)
    mods=f'''<modifiers>
            <modifier id="{prefix}" type="increment" value="1" field="{cid}">
              <repeats><repeat value="1" repeats="1" field="selections" scope="root-entry" childId="veteran-included" shared="true" roundUp="false" includeChildSelections="false" /></repeats>
            </modifier>
          </modifiers>'''
    return replace_direct_modifiers(b,mods)

cat=replace_block(cat,'selectionEntryGroup','veteran-melee',
                  lambda b:patch_any_model_group(b,'veteran-melee','veteran-melee-max','r29-veteran-melee-per-model'))

# Bolter replacements = one per actual model, minus Veterans already using a Specialist weapon.
r=parse()
sg=fid(r,'veteran-specialists')
spec_ids=[]
for tag in (C('selectionEntries'),C('entryLinks')):
    box=sg.find(tag)
    if box is not None:
        spec_ids += [x.get('id') for x in list(box) if x.get('id')]

def patch_ranged(b):
    b=set_constraint_value(b,'veteran-ranged-max',1)
    mods=[f'''<modifier id="r29-veteran-ranged-per-model" type="increment" value="1" field="veteran-ranged-max"><repeats><repeat value="1" repeats="1" field="selections" scope="root-entry" childId="veteran-included" shared="true" roundUp="false" includeChildSelections="false" /></repeats></modifier>''']
    for i,sid in enumerate(spec_ids):
        mods.append(f'''<modifier id="r29-veteran-ranged-specialist-{i}" type="increment" value="-1" field="veteran-ranged-max"><repeats><repeat value="1" repeats="1" field="selections" scope="root-entry" childId="{sid}" shared="true" roundUp="false" includeChildSelections="true" /></repeats></modifier>''')
    return replace_direct_modifiers(b,'<modifiers>'+''.join(mods)+'</modifiers>')
cat=replace_block(cat,'selectionEntryGroup','veteran-ranged',patch_ranged)

# Individual Wargear: any model may take each item, so 5–10 selections per option.
def patch_per_model_link(text,eid,cid):
    def fn(b):
        b=set_constraint_value(b,cid,1)
        # Replace the direct modifiers with clean per-model cap logic.
        cut_candidates=[x for x in (b.find('<costs>'),b.find('<rules>'),b.find('<profiles>')) if x>=0]
        # Keep costs/rules; replace existing modifiers container wherever it is.
        ms=b.find('<modifiers>')
        new=f'''<modifiers><modifier id="r29-{eid}-per-model" type="increment" value="1" field="{cid}"><repeats><repeat value="1" repeats="1" field="selections" scope="root-entry" childId="veteran-included" shared="true" roundUp="false" includeChildSelections="false" /></repeats></modifier></modifiers>'''
        if ms>=0:
            me=b.find('</modifiers>',ms)
            if me<0: raise RuntimeError('bad modifiers '+eid)
            b=b[:ms]+new+b[me+len('</modifiers>'):]
        else:
            close=b.rfind('</entryLink>')
            b=b[:close]+new+b[close:]
        return b
    return replace_block(text,'entryLink',eid,fn)

cat=patch_per_model_link(cat,'veteran-shields','veteran-shields-max')
cat=patch_per_model_link(cat,'veteran-bombs','veteran-bombs-max')

# Specialist weapons: 1 per five TOTAL models = 1 at 5–9, 2 at 10.
def patch_specialists(b):
    b=set_constraint_value(b,'veteran-specialists-max',1)
    mods='''<modifiers>
            <modifier id="r29-veteran-specialists-ten-models" type="set" value="2" field="veteran-specialists-max">
              <conditions><condition type="atLeast" value="9" field="selections" scope="root-entry" childId="veteran-included" shared="true" includeChildSelections="false" includeChildForces="false" /></conditions>
            </modifier>
          </modifiers>'''
    return replace_direct_modifiers(b,mods)
cat=replace_block(cat,'selectionEntryGroup','veteran-specialists',patch_specialists)

# ---------------------------------------------------------------------------
# 3. REVISION
# ---------------------------------------------------------------------------
cat,n=re.subn(r'(<catalogue\b[^>]*\brevision=")28(")',r'\g<1>29\2',cat,count=1)
if n!=1: raise RuntimeError('CAT 28 -> 29 bump failed')
idx,n=re.subn(r'(filePath="Legiones Astartes\.cat"[^>]*dataRevision=")28(")',r'\g<1>29\2',idx,count=1)
if n!=1: raise RuntimeError('index 28 -> 29 bump failed')

# ---------------------------------------------------------------------------
# 4. VALIDATION
# ---------------------------------------------------------------------------
r=ET.fromstring(cat.encode('utf-8'))
def F(i): return fid(r,i)
def con(e,cid):
    cs=e.find(C('constraints'))
    return next((x for x in list(cs or []) if x.get('id')==cid),None)

v=F('veteran-included')
assert v.get('defaultAmount')=='4'
assert con(v,'veteran-included-min').get('value')=='4'
assert con(v,'veteran-included-max').get('value')=='9'

# Pools: base constraint 1 + per Veteran = 5 to 10.
for gid,cid,mid in (
    ('veteran-melee','veteran-melee-max','r29-veteran-melee-per-model'),
    ('veteran-ranged','veteran-ranged-max','r29-veteran-ranged-per-model'),
):
    g=F(gid)
    assert con(g,cid).get('value')=='1'
    m=F(mid); assert m is not None
    rep=next(m.iter(C('repeat')),None)
    assert rep is not None and rep.get('value')=='1' and rep.get('childId')=='veteran-included'

for eid,cid in [('veteran-shields','veteran-shields-max'),('veteran-bombs','veteran-bombs-max')]:
    e=F(eid)
    assert con(e,cid).get('value')=='1'
    m=F('r29-'+eid+'-per-model')
    assert m is not None
    rep=next(m.iter(C('repeat')),None)
    assert rep is not None and rep.get('value')=='1'

sp=F('veteran-specialists')
assert con(sp,'veteran-specialists-max').get('value')=='1'
m=F('r29-veteran-specialists-ten-models')
assert m is not None
q=next(m.iter(C('condition')),None)
assert q is not None and q.get('value')=='9' and q.get('childId')=='veteran-included'

# Cult discipline gating exists for Praetor, Centurion and Tactical Brotherhood.
for mid in ('r29-praetor-cult-disc-biomancy','r29-centurion-cult-disc-biomancy','r29-tactical-cult-disc-biomancy'):
    assert F(mid) is not None, mid

# Every mapped generic Brotherhood selector has all 5 discipline gates where applicable.
for pref in ('r29-veteran-cult-disc','r29-terminator-cult-disc','r29-sekhmet-cult-disc','r29-guard-sekhmet-cult-disc'):
    for d in ('biomancy','divination','pyromancy','telekinesis','telepathy'):
        assert F(pref+'-'+d) is not None, pref+'-'+d
# Ammitara has only its two legal disciplines in the UI.
for d in ('divination','telepathy'):
    assert F('r29-ammitara-cult-disc-'+d) is not None

ref=F('r25-legion-xv-reference')
txt=ref.find(C('description')).text or ''
assert 'Pavoni — Biomancy; Raptora — Telekinesis; Corvidae — Divination; Athanaeans — Telepathy; Pyrae — Pyromancy' in txt
assert 'associated with its chosen Prosperine Cult' in txt

# Osiron remains explicit no-Cult exception and still has its discipline selector.
osi=F('r41-unit-xv-4-contemptor-osiron-dreadnought')
assert not any('Prosperine Cult' in (g.get('name') or '') for g in list(osi.find(C('selectionEntryGroups')) or []))
assert F('r19-ts-osiron-disciplines') is not None

lines=[
 'LIVE R29 — THOUSAND SONS CULT DISCIPLINES + VETERAN RESTORE',
 'MODE='+('APPLY' if APPLY else 'DRY RUN'),
 'CAT 28 -> 29',
 '',
 'THOUSAND SONS',
 '• Every Cult-assigned generic XV Psyker/Brotherhood now sees only the discipline matching its selected Prosperine Cult.',
 '• Mapping: Pavoni→Biomancy, Raptora→Telekinesis, Corvidae→Divination, Athanaeans→Telepathy, Pyrae→Pyromancy.',
 '• This is enforced for Praetors, Centurions/Consuls, Fellowships Tactical Brotherhoods, Veteran Brotherhoods, Terminator Brotherhoods, Sekhmet and Ammitara.',
 '• Named characters retain their fixed Cult/power access.',
 '• Osiron remains the explicit no-Cult exception and follows its own Psychic Dreadnought access.',
 '• Magnus remains the explicit multi-discipline exception.',
 '',
 'LEGION VETERAN SQUAD',
 '• Restored correct source size: 4 Legion Veterans + 1 Veteran Sergeant, with up to 5 additional Veterans (5–10 total).',
 '• Any-model melee, bolter replacement, Combat Shield and Melta Bomb pools now scale to the actual 5–10 models.',
 '• Specialist Weapons are restored to 1 per 5 total models: 1 at 5–9, 2 at 10.',
 '• Bolter replacement capacity is reduced by each Specialist Weapon selected so one model cannot replace the same bolter twice.',
 '',
 'VALIDATION: PASS'
]
OUT.write_text('\n'.join(lines),encoding='utf-8')
if APPLY:
    CAT.write_text(cat,encoding='utf-8',newline='')
    IDX.write_text(idx,encoding='utf-8',newline='')
print('\n'.join(lines))
