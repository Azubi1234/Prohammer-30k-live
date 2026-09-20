from pathlib import Path
import os,re,xml.etree.ElementTree as ET

CAT=Path('Legiones Astartes.cat')
IDX=Path('index.xml')
OUT=Path('inspection-live-r28-ts-restrictions-veterans.txt')
APPLY=os.environ.get('R28_APPLY','0')=='1'

cat=CAT.read_text(encoding='utf-8')
idx=IDX.read_text(encoding='utf-8')
if 'revision="27"' not in cat[:1400]:
    raise RuntimeError('R28 expects CAT revision 27')
if 'dataRevision="27"' not in idx:
    raise RuntimeError('R28 expects index dataRevision 27')

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
    nb=fn(b)
    return text[:s]+nb+text[e:]

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

def set_cost(block,value):
    pat=re.compile(r'(<cost\b(?=[^>]*\bname="Points")[^>]*\bvalue=")[^"]*(")')
    out,n=pat.subn(r'\g<1>'+str(value)+r'\2',block,count=1)
    if n!=1: raise RuntimeError('Points cost not found/set')
    return out

def remove_modifier_id(block,mid):
    pat=re.compile(r'\s*<modifier\b(?=[^>]*\bid="'+re.escape(mid)+r'")[^>]*>.*?</modifier>',re.S)
    return pat.sub('',block)

def remove_modifiers_targeting(block,field):
    pat=re.compile(r'\s*<modifier\b(?=[^>]*\bfield="'+re.escape(field)+r'")[^>]*>.*?</modifier>',re.S)
    return pat.sub('',block)

def replace_direct_modifiers(block,newmods):
    # Direct container only: choose first modifiers container before first entryLinks/selectionEntries.
    cut_candidates=[x for x in (block.find('<entryLinks>'),block.find('<selectionEntries>'),block.find('<selectionEntryGroups>')) if x>=0]
    cut=min(cut_candidates) if cut_candidates else len(block)
    ms=block.find('<modifiers>',0,cut)
    if ms>=0:
        me=block.find('</modifiers>',ms,cut)
        if me<0: raise RuntimeError('direct modifiers not balanced')
        return block[:ms]+newmods+block[me+len('</modifiers>'):]
    ins=cut
    return block[:ins]+newmods+block[ins:]

def append_modifier_to_entry(text,eid,modifier_xml):
    def fn(b):
        # remove same modifier id if rerun
        m=re.search(r'\bid="([^"]+)"',modifier_xml)
        if m: b=remove_modifier_id(b,m.group(1))
        # direct modifiers container is before direct rules/costs/profile etc; if one exists anywhere
        # inside this choice, use the first modifiers block.
        ms=b.find('<modifiers>')
        if ms>=0:
            me=b.find('</modifiers>',ms)
            if me<0: raise RuntimeError('entry modifiers unbalanced '+eid)
            return b[:me]+modifier_xml+b[me:]
        close=b.rfind('</selectionEntry>')
        if close<0: raise RuntimeError('selectionEntry close missing '+eid)
        return b[:close]+'<modifiers>'+modifier_xml+'</modifiers>'+b[close:]
    return replace_block(text,'selectionEntry',eid,fn)

def set_choice_hidden(text,eid,hidden):
    return replace_block(text,'selectionEntry',eid,lambda b:set_open_attr(b,'selectionEntry',eid,'hidden','true' if hidden else 'false'))

# ---------------------------------------------------------------------------
# 1) THOUSAND SONS CORE WORDING — RESTRICTIONS ONLY
# ---------------------------------------------------------------------------
new_prefix = """SORCERERS OF PROSPERO
The Thousand Sons possess an unparalleled concentration of psychic talent amongst the Legiones Astartes, and the study of the Warp permeates every level of the Legion.

All Thousand Sons Independent Characters are Psykers. Unless they already possess a higher Psychic Mastery Level, they count as Psyker (Mastery Level 1). A Thousand Sons Praetor instead counts as Psyker (Mastery Level 2).

Thousand Sons Psykers that are permitted to select a Psychic Discipline may select their psychic powers from one of the following ProHammer Psychic Disciplines:
• Biomancy
• Divination
• Pyromancy
• Telekinesis
• Telepathy

Unless specifically stated otherwise in the model or unit's own entry, a Psyker may select powers from only one Psychic Discipline. A Psyker may not select powers from multiple Disciplines.

The number of powers known and which may be invoked is determined by the Psyker's Mastery Level and the normal ProHammer psychic rules.

A Thousand Sons Librarian Consul follows these rules normally. Activating a Force Weapon counts as the use of a psychic power. A Psyker may not use the same psychic power more than once during the same player turn.

THE PROSPERINE CULTS
The warriors of the Thousand Sons were organised according to the great psychic Cults of Prospero, each devoted to the mastery of a particular aspect of the psychic arts.

Any Thousand Sons Infantry, Jump Infantry, Bike, Jetbike unit or Independent Character that is permitted by its unit entry to select a Prosperine Cult must be assigned to one of the following Prosperine Cults when the army is selected:
• Pavoni
• Raptora
• Corvidae
• Athanaeans
• Pyrae

A model or unit that is not specifically permitted to select a Prosperine Cult does not gain one simply for being part of a Thousand Sons army.

The chosen Cult must be recorded on the army roster. A unit that has selected a Prosperine Cult receives the normal Cult Arcana of its chosen Cult.

A model or unit may normally belong to only one Prosperine Cult. It may not select or benefit from multiple Cults unless a rule in its own entry specifically states otherwise.

An Independent Character retains its own Cult when joining a unit belonging to another Cult. Cult Arcana and Cult Mastery are not conferred between the Independent Character and the unit unless specifically stated otherwise.

Selecting a Prosperine Cult does not by itself grant access to a Psychic Discipline or make a model a Psyker. Psychic Discipline access is determined separately by the model or unit's Psyker rules and its own army list entry.

"""

def patch_reference_rule(text):
    s,e,b=extract_block(text,'rule','r25-legion-xv-reference')
    dm=re.search(r'(<description>)(.*?)(</description>)',b,re.S)
    if not dm: raise RuntimeError('XV reference description missing')
    desc=dm.group(2)
    nd,n=re.subn(r'SORCERERS OF PROSPERO.*?(?=CULT MASTERY)',new_prefix,desc,count=1,flags=re.S)
    if n!=1: raise RuntimeError('Could not replace Sorcerers/Cults prefix')
    # Make Brotherhood unit-wide selection explicit without changing its actual mechanics.
    needle='A unit upgraded in this manner counts as a Brotherhood of Psykers (Mastery Level 1). The unit then selects one psychic power from the ProHammer Psychic Discipline associated with its chosen Prosperine Cult, as shown below:'
    repl='A unit upgraded in this manner counts as a Brotherhood of Psykers (Mastery Level 1). Its Prosperine Cult and Psychic Discipline are selected for the unit as a whole; individual models in the unit may not select different Cults or Disciplines. The unit then selects one psychic power from the ProHammer Psychic Discipline associated with its chosen Prosperine Cult, as shown below:'
    if needle in nd: nd=nd.replace(needle,repl,1)
    b=b[:dm.start(2)]+nd+b[dm.end(2):]
    return text[:s]+b+text[e:]

cat=patch_reference_rule(cat)

# Keep hidden helper rules consistent with the revised restriction.
def replace_rule_description(text,rid,newtext):
    def fn(b):
        pat=re.compile(r'(<description>)(.*?)(</description>)',re.S)
        out,n=pat.subn(lambda m:m.group(1)+newtext+m.group(3),b,count=1)
        if n!=1: raise RuntimeError('description missing '+rid)
        return out
    return replace_block(text,'rule',rid,fn)

cat=replace_rule_description(cat,'r18-ts-praetor-psyker-rule',
    'In a Thousand Sons Detachment, a Legion Praetor is a Psyker (Mastery Level 2) and selects two powers from one Psychic Discipline chosen from Biomancy, Divination, Pyromancy, Telekinesis or Telepathy, unless another rule explicitly states otherwise. Activating a Force Weapon counts as the use of a psychic power, and the same power may not be used more than once in the same player turn.')
cat=replace_rule_description(cat,'r18-ts-centurion-psyker-rule',
    'In a Thousand Sons Detachment, a Legion Centurion and its Consul variants are Psykers (Mastery Level 1) unless another rule grants a higher Mastery Level. Powers must normally be selected from one Psychic Discipline only. A Librarian Consul follows the normal Librarian upgrade rules; an Epistolary is Mastery Level 2.')

# ---------------------------------------------------------------------------
# 2) ONE DISCIPLINE MAXIMUM — EXCEPT EXPLICIT MAGNUS FORMS
# ---------------------------------------------------------------------------
disc_groups = [
 ('r19-ts-praetor-disciplines','r19-ts-praetor-disc-max'),
 ('r19-ts-centurion-disciplines','r19-ts-centurion-disc-max'),
 ('r19-ts-tactical-brotherhood-disciplines','r19-ts-tactical-brotherhood-disc-max'),
 ('r19-ts-veteran-unit-brotherhood-disciplines','r19-ts-veteran-unit-brotherhood-disc-max'),
 ('r19-ts-terminator-unit-brotherhood-disciplines','r19-ts-terminator-unit-brotherhood-disc-max'),
 ('r19-ts-sekhmet-disciplines','r19-ts-sekhmet-disc-max'),
 ('r27-guard-r19-ts-sekhmet-disciplines','r27-guard-r19-ts-sekhmet-disc-max'),
 ('r19-ts-ammitara-disciplines','r19-ts-ammitara-disc-max'),
 ('r19-ts-osiron-disciplines','r19-ts-osiron-disc-max'),
]
for gid,cid in disc_groups:
    def f(b,cid=cid):
        b=set_constraint_value(b,cid,1)
        b=remove_modifiers_targeting(b,cid)
        return b
    cat=replace_block(cat,'selectionEntryGroup',gid,f)

# ---------------------------------------------------------------------------
# 3) CULT -> DISCIPLINE GATES FOR PSYCHIC BROTHERHOODS
# ---------------------------------------------------------------------------
CULT_TO_DISC={'Pavoni':'Biomancy','Raptora':'Telekinesis','Corvidae':'Divination','Athanaeans':'Telepathy','Pyrae':'Pyromancy'}
DISC_TO_CULT={v:k for k,v in CULT_TO_DISC.items()}

# Parse interim XML only to discover current choice IDs.
r=ET.fromstring(cat.encode('utf-8'))
def fid(root,i): return next((x for x in root.iter() if x.get('id')==i),None)

def direct_choices(group):
    ses=group.find(C('selectionEntries'))
    return list(ses) if ses is not None else []

def add_mapping(cult_gid,disc_gid,prefix,allowed_cults=None):
    global cat,r
    cg=fid(r,cult_gid); dg=fid(r,disc_gid)
    if cg is None or dg is None: raise RuntimeError('Cult/discipline group missing '+cult_gid+' / '+disc_gid)
    cults={x.get('name'):x.get('id') for x in direct_choices(cg)}
    discs={x.get('name'):x.get('id') for x in direct_choices(dg)}
    allowed=set(allowed_cults or CULT_TO_DISC.keys())
    # Hide cults this unit is not allowed to select.
    for name,eid in cults.items():
        if name in CULT_TO_DISC:
            cat=set_choice_hidden(cat,eid,name not in allowed)
    # Each available discipline is visible only with its corresponding Cult.
    for d,deid in discs.items():
        cult=DISC_TO_CULT.get(d)
        if not cult or cult not in cults: continue
        mid=prefix+'-'+re.sub(r'[^a-z0-9]+','-',d.lower()).strip('-')
        mod=f'''<modifier id="{mid}" type="set" value="true" field="hidden"><conditions><condition type="lessThan" value="1" field="selections" scope="root-entry" childId="{cults[cult]}" shared="true" includeChildSelections="true" includeChildForces="false" /></conditions></modifier>'''
        cat=append_modifier_to_entry(cat,deid,mod)
    r=ET.fromstring(cat.encode('utf-8'))

# Generic Brotherhoods already had gates; add clean explicit R28 gates as a safety layer.
add_mapping('r45-cult-veteran-unit','r19-ts-veteran-unit-brotherhood-disciplines','r28-vet-cult-disc')
add_mapping('r45-cult-terminator-unit','r19-ts-terminator-unit-brotherhood-disciplines','r28-term-cult-disc')
add_mapping('r45-cult-r41-unit-xv-0-sekhmet-terminator-cabal','r19-ts-sekhmet-disciplines','r28-sekhmet-cult-disc')
add_mapping('r27-guard-r45-cult-r41-unit-xv-0-sekhmet-terminator-cabal','r27-guard-r19-ts-sekhmet-disciplines','r28-guard-sekhmet-cult-disc')
add_mapping('r45-cult-r41-unit-xv-2-ammitara-occult-intercession-cabal','r19-ts-ammitara-disciplines','r28-ammitara-cult-disc',
            allowed_cults={'Corvidae','Athanaeans'})

# Named-character Cult selectors: expose only the fixed Cult.
fixed = {
 'r45-cult-r41-unit-xv-6-ahzek-ahriman':'Corvidae',
 'r45-cult-r41-unit-xv-7-phosis-t-kar':'Raptora',
 'r45-cult-r41-unit-xv-8-magistus-amon-the-hidden':'Athanaeans',
 'r45-cult-r41-unit-xv-9-hathor-maat':'Pavoni',
 'r45-cult-r41-unit-xv-10-sanakht':'Athanaeans',
}
r=ET.fromstring(cat.encode('utf-8'))
for gid,wanted in fixed.items():
    g=fid(r,gid)
    if g is None: raise RuntimeError('fixed Cult group missing '+gid)
    for ch in direct_choices(g):
        if ch.get('name') in CULT_TO_DISC:
            cat=set_choice_hidden(cat,ch.get('id'),ch.get('name')!=wanted)
    r=ET.fromstring(cat.encode('utf-8'))

# ---------------------------------------------------------------------------
# 4) MAGNUS — REAL ROSTER POINT THRESHOLD, NOT A UNIT-POINT CONSTRAINT
# ---------------------------------------------------------------------------
MAG='r41-unit-xv-11-xv-magnus-the-red-the-crimson-king'
PRIM='da22-rite-primarchs-chosen'
def patch_magnus(b):
    b=re.sub(r'\s*<constraint\b(?=[^>]*\bid="r18-ts-magnus-min-points")[^>]*/>','',b,count=1)
    b=remove_modifier_id(b,'r18-ts-magnus-min-primarchs-chosen')
    b=remove_modifier_id(b,'r28-magnus-hide-under-2000')
    b=remove_modifier_id(b,'r28-magnus-hide-under-1500-primarchs-chosen')
    mods=b.find('<modifiers>')
    if mods<0: raise RuntimeError('Magnus modifiers container missing')
    me=b.find('</modifiers>',mods)
    if me<0: raise RuntimeError('Magnus modifiers close missing')
    add=f'''
        <modifier id="r28-magnus-hide-under-2000" type="set" value="true" field="hidden">
          <conditionGroups><conditionGroup type="and"><conditions>
            <condition type="greaterThan" value="0" field="limit::pts" scope="roster" childId="model" shared="true" includeChildSelections="true" includeChildForces="false" />
            <condition type="lessThan" value="2000" field="limit::pts" scope="roster" childId="model" shared="true" includeChildSelections="true" includeChildForces="false" />
            <condition type="lessThan" value="1" field="selections" scope="roster" childId="{PRIM}" shared="true" includeChildSelections="true" includeChildForces="false" />
          </conditions></conditionGroup></conditionGroups>
        </modifier>
        <modifier id="r28-magnus-hide-under-1500-primarchs-chosen" type="set" value="true" field="hidden">
          <conditionGroups><conditionGroup type="and"><conditions>
            <condition type="greaterThan" value="0" field="limit::pts" scope="roster" childId="model" shared="true" includeChildSelections="true" includeChildForces="false" />
            <condition type="lessThan" value="1500" field="limit::pts" scope="roster" childId="model" shared="true" includeChildSelections="true" includeChildForces="false" />
            <condition type="atLeast" value="1" field="selections" scope="roster" childId="{PRIM}" shared="true" includeChildSelections="true" includeChildForces="false" />
          </conditions></conditionGroup></conditionGroups>
        </modifier>'''
    return b[:me]+add+b[me:]
cat=replace_block(cat,'selectionEntry',MAG,patch_magnus)

# ---------------------------------------------------------------------------
# 5) LEGION VETERAN SQUAD — 10–20 + TRUE MODEL/WEAPON SCALING
# ---------------------------------------------------------------------------
def patch_vet_model(b):
    b=set_open_attr(b,'selectionEntry','veteran-included','defaultAmount',9)
    b=set_constraint_value(b,'veteran-included-min',9)
    b=set_constraint_value(b,'veteran-included-max',19)
    return b
cat=replace_block(cat,'selectionEntry','veteran-included',patch_vet_model)

# Close-combat replacements: one per actual squad model.
def patch_melee(b):
    b=set_constraint_value(b,'veteran-melee-max',1)
    newmods='''<modifiers>
            <modifier id="r28-veteran-melee-scale" type="increment" value="1" field="veteran-melee-max"><repeats><repeat value="1" repeats="1" field="selections" scope="root-entry" childId="veteran-included" shared="true" roundUp="false" includeChildSelections="false" /></repeats></modifier>
          </modifiers>'''
    b=replace_direct_modifiers(b,newmods)
    b=re.sub(r'(<constraint\b(?=[^>]*\bid="(?:veteran-melee-chainaxe-max|veteran-melee-rending-max|veteran-melee-power-max|r40-da-warblade-veteran-melee-power-max)")[^>]*\bvalue=")[^"]*(")',r'\g<1>20\2',b)
    return b
cat=replace_block(cat,'selectionEntryGroup','veteran-melee',patch_melee)

# Specialist weapons: 1 per 5 total models => 2 at 10, 3 at 15, 4 at 20.
def patch_specialists(b):
    b=set_constraint_value(b,'veteran-specialists-max',2)
    newmods='''<modifiers>
            <modifier id="r28-veteran-specialists-15" type="set" value="3" field="veteran-specialists-max"><conditions><condition type="atLeast" value="14" field="selections" scope="root-entry" childId="veteran-included" shared="true" includeChildSelections="false" includeChildForces="false" /></conditions></modifier>
            <modifier id="r28-veteran-specialists-20" type="set" value="4" field="veteran-specialists-max"><conditions><condition type="atLeast" value="19" field="selections" scope="root-entry" childId="veteran-included" shared="true" includeChildSelections="false" includeChildForces="false" /></conditions></modifier>
          </modifiers>'''
    b=replace_direct_modifiers(b,newmods)
    # Every specialist option may individually fill the whole allowance.
    b=re.sub(r'(<constraint\b(?=[^>]*\bid="[^"]*(?:veteran-sp-|da22-alt-)[^"]*-max|[^"]*da22-alt-[^"]*-2")[^>]*\bvalue=")[^"]*(")',r'\g<1>4\2',b)
    # Explicit fallback for all max constraints directly under specialist choices.
    b=re.sub(r'(<constraint\b[^>]*\btype="max"[^>]*\bfield="selections"[^>]*\bvalue=")(?:1|2)(")',r'\g<1>4\2',b)
    # restore group max itself after generic replacement
    b=set_constraint_value(b,'veteran-specialists-max',2)
    return b
cat=replace_block(cat,'selectionEntryGroup','veteran-specialists',patch_specialists)

# Discover every specialist selection ID after the previous edit for ranged-cap subtraction.
tmp=ET.fromstring(cat.encode('utf-8'))
sg=fid(tmp,'veteran-specialists')
spec_ids=[]
for key in (C('selectionEntries'),C('entryLinks')):
    box=sg.find(key)
    if box is not None:
        spec_ids += [x.get('id') for x in list(box) if x.get('id')]

def patch_ranged(b):
    b=set_constraint_value(b,'veteran-ranged-max',1)
    pieces=['''<modifiers>
            <modifier id="r28-veteran-ranged-scale" type="increment" value="1" field="veteran-ranged-max"><repeats><repeat value="1" repeats="1" field="selections" scope="root-entry" childId="veteran-included" shared="true" roundUp="false" includeChildSelections="false" /></repeats></modifier>''']
    for i,sid in enumerate(spec_ids):
        pieces.append(f'''<modifier id="r28-veteran-ranged-sp-{i}" type="increment" value="-1" field="veteran-ranged-max"><repeats><repeat value="1" repeats="1" field="selections" scope="root-entry" childId="{sid}" shared="true" roundUp="false" includeChildSelections="true" /></repeats></modifier>''')
    pieces.append('</modifiers>')
    b=replace_direct_modifiers(b,'\n            '.join(pieces))
    # Foeblaster/combis/sniper can fill any remaining bolter-replacement slot.
    b=re.sub(r'(<constraint\b(?=[^>]*\bid="(?:r35-recon-veteran-sniper-max|veteran-ranged-[^"]+-max)")[^>]*\bvalue=")[^"]*(")',r'\g<1>20\2',b)
    return b
cat=replace_block(cat,'selectionEntryGroup','veteran-ranged',patch_ranged)

# Per-model wargear caps and squad-wide costs.
def patch_simple_scaled_link(text,eid,cid):
    def fn(b):
        b=set_constraint_value(b,cid,1)
        # swap 5-model repeat for per-model repeat
        b=re.sub(r'(<repeat\b[^>]*\bchildId="veteran-included"[^>]*\bvalue=")5(")',r'\g<1>1\2',b)
        # attribute order fallback
        b=re.sub(r'(<repeat\b(?=[^>]*\bchildId="veteran-included")(?=[^>]*\bvalue=")5(")[^>]*>)',
                 lambda m:m.group(0).replace('value="5"','value="1"'),b)
        return b
    return replace_block(text,'entryLink',eid,fn)

cat=patch_simple_scaled_link(cat,'veteran-shields','veteran-shields-max')
cat=patch_simple_scaled_link(cat,'veteran-bombs','veteran-bombs-max')

def patch_squadwide_entry(text,eid,per_model):
    def fn(b):
        b=set_cost(b,per_model)
        b=re.sub(r'(<repeat\b(?=[^>]*\bchildId="veteran-included")[^>]*\bvalue=")5(")',r'\g<1>1\2',b)
        return b
    return replace_block(text,'selectionEntry',eid,fn)

def patch_squadwide_link(text,eid,per_model):
    def fn(b):
        b=set_cost(b,per_model)
        b=re.sub(r'(<repeat\b(?=[^>]*\bchildId="veteran-included")[^>]*\bvalue=")5(")',r'\g<1>1\2',b)
        return b
    return replace_block(text,'entryLink',eid,fn)

cat=patch_squadwide_link(cat,'veteran-krak',2)
cat=patch_squadwide_entry(cat,'veteran-jump-packs',15)
cat=patch_squadwide_entry(cat,'r35-assault-jp-veteran-jump-packs',10)

# ---------------------------------------------------------------------------
# 6) REVISION BUMP
# ---------------------------------------------------------------------------
cat,n=re.subn(r'(<catalogue\b[^>]*\brevision=")27(")',r'\g<1>28\2',cat,count=1)
if n!=1: raise RuntimeError('CAT revision bump failed')
idx,n=re.subn(r'(filePath="Legiones Astartes\.cat"[^>]*dataRevision=")27(")',r'\g<1>28\2',idx,count=1)
if n!=1: raise RuntimeError('index revision bump failed')

# ---------------------------------------------------------------------------
# 7) VALIDATION
# ---------------------------------------------------------------------------
r=ET.fromstring(cat.encode('utf-8'))
def F(i): return fid(r,i)
def constraint(e,cid):
    cs=e.find(C('constraints'))
    return next((x for x in list(cs or []) if x.get('id')==cid),None)

v=F('veteran-included')
assert v is not None and v.get('defaultAmount')=='9'
assert constraint(v,'veteran-included-min').get('value')=='9'
assert constraint(v,'veteran-included-max').get('value')=='19'

for gid,cid in [('veteran-melee','veteran-melee-max'),('veteran-ranged','veteran-ranged-max')]:
    g=F(gid); assert constraint(g,cid).get('value')=='1'
sp=F('veteran-specialists')
assert constraint(sp,'veteran-specialists-max').get('value')=='2'
assert F('r28-veteran-specialists-15') is not None and F('r28-veteran-specialists-20') is not None

# Squad-wide cost anchors are now one model + one increment per additional Veteran.
for eid,cost in [('veteran-krak','2'),('veteran-jump-packs','15'),('r35-assault-jp-veteran-jump-packs','10')]:
    e=F(eid)
    c=e.find(C('costs'))
    p=next(x for x in list(c or []) if x.get('name')=='Points')
    assert p.get('value')==cost, (eid,p.get('value'))

# Magnus remains unique, but the broken unit-points minimum is gone.
m=F(MAG)
assert constraint(m,'r41-unit-xv-11-xv-magnus-the-red-the-crimson-king-unique').get('value')=='1'
assert F('r18-ts-magnus-min-points') is None
assert F('r28-magnus-hide-under-2000') is not None
assert F('r28-magnus-hide-under-1500-primarchs-chosen') is not None

# All ordinary TS discipline selectors are capped at one discipline.
for gid,cid in disc_groups:
    g=F(gid); c=constraint(g,cid)
    assert c is not None and c.get('value')=='1', (gid,c.get('value') if c is not None else None)
    # no modifier may raise the discipline max again
    for mm in list(g.find(C('modifiers')) or []):
        assert mm.get('field')!=cid, (gid,mm.get('id'))

# Magnus keeps his explicit multi-discipline exception.
mg=F('r19-ts-magnus-disciplines')
assert constraint(mg,'r19-ts-magnus-disc-max').get('value')=='3'

# Castellax and Osiron cult eligibility remains intentionally distinct.
cast=F('r41-unit-xv-3-castellax-achea-maniple')
osi=F('r41-unit-xv-4-contemptor-osiron-dreadnought')
assert not any('Prosperine Cult' in (g.get('name') or '') for g in list(cast.find(C('selectionEntryGroups')) or []))
assert not any('Prosperine Cult' in (g.get('name') or '') for g in list(osi.find(C('selectionEntryGroups')) or []))

# Ammitara cult restriction.
ac=F('r45-cult-r41-unit-xv-2-ammitara-occult-intercession-cabal')
choices={x.get('name'):x.get('hidden') for x in direct_choices(ac)}
for nm in ('Pavoni','Raptora','Pyrae'): assert choices.get(nm)=='true', choices
for nm in ('Corvidae','Athanaeans'): assert choices.get(nm)!='true', choices

# Fixed named Cults expose only their assigned Cult.
for gid,wanted in fixed.items():
    g=F(gid)
    vis=[x.get('name') for x in direct_choices(g) if x.get('name') in CULT_TO_DISC and x.get('hidden')!='true']
    assert vis==[wanted], (gid,vis)

# Core wording actually updated.
ref=F('r25-legion-xv-reference')
d=ref.find(C('description'))
txt=d.text or ''
for phrase in (
    'may select powers from only one Psychic Discipline',
    'does not gain one simply for being part of a Thousand Sons army',
    'Selecting a Prosperine Cult does not by itself grant access to a Psychic Discipline',
):
    assert phrase in txt, phrase

lines=[
 'LIVE R28 — THOUSAND SONS RESTRICTIONS + VETERAN SCALING',
 'MODE='+('APPLY' if APPLY else 'DRY RUN'),
 'CAT 27 -> 28',
 '',
 'THOUSAND SONS',
 '• Replaced Sorcerers of Prospero / Prosperine Cults restriction wording with the approved version.',
 '• Ordinary XV Psykers are capped at one Psychic Discipline; Magnus keeps his explicit multi-discipline exception.',
 '• Veteran, Terminator, Sekhmet and Ammitara Brotherhood discipline choices are explicitly gated by the selected Cult.',
 '• Ammitara is restricted to Corvidae/Divination or Athanaeans/Telepathy.',
 '• Ahriman, Phosis T’Kar, Amon, Hathor Maat and Sanakht expose only their fixed Cult.',
 '• Osiron remains a Psyker with no Prosperine Cult; Castellax-Achea remains without Cult or Discipline access.',
 '• Magnus keeps 0–1 Unique. The broken min limit::points constraint is removed and replaced by roster-point visibility: 2000+ normally, 1500+ under Primarch’s Chosen.',
 '',
 'LEGION VETERAN SQUAD',
 '• Squad is now 1 Veteran Sergeant + 9–19 Legion Veterans = 10–20 models.',
 '• Bolter and close-combat replacements now scale to the actual model count instead of the old 5-model chunks.',
 '• Specialist weapons remain the established “1 per 5 models” system: 2 at 10 models, 3 at 15, 4 at 20.',
 '• Specialist weapons correctly consume Bolter-replacement capacity, including alternate specialist entries.',
 '• Combat Shields and Melta Bombs scale to actual model count.',
 '• Krak Grenades and both Jump Pack options now charge the correct per-model cost across 10–20 models.',
 '',
 'VALIDATION: PASS'
]
OUT.write_text('\n'.join(lines),encoding='utf-8')
if APPLY:
    CAT.write_text(cat,encoding='utf-8',newline='')
    IDX.write_text(idx,encoding='utf-8',newline='')
print('\n'.join(lines))
