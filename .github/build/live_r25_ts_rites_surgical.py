from pathlib import Path
import os,re,xml.etree.ElementTree as ET,difflib

CAT=Path('Legiones Astartes.cat'); GST=Path('Prohammer 30k.gst'); IDX=Path('index.xml')
OUT=Path('inspection-live-r25-ts-rites-surgical.txt')
APPLY=os.environ.get('R25_APPLY','0')=='1'

cat=CAT.read_text(encoding='utf-8')
gst=GST.read_text(encoding='utf-8')
idx=IDX.read_text(encoding='utf-8')

# Safety: R25 must start from the byte-clean R24 restore.
if 'revision="24"' not in cat[:1000]:
    raise RuntimeError('R25 expects catalogue revision 24')
if 'dataRevision="24"' not in idx:
    raise RuntimeError('R25 expects index dataRevision 24')

changes=[]

def remove_modifier(text,mid):
    pat=re.compile(r'<modifier\b(?=[^>]*\bid="'+re.escape(mid)+r'")[^>]*>.*?</modifier>\s*',re.S)
    new,n=pat.subn('',text)
    if n!=1:
        raise RuntimeError(f'Expected exactly one modifier {mid}, found {n}')
    changes.append('removed stale modifier '+mid)
    return new

def attr_replace(text,eid,attr,old,new):
    # only within the opening tag that has the requested id
    pat=re.compile(r'(<(?:selectionEntry|selectionEntryGroup|entryLink|categoryLink)\b(?=[^>]*\bid="'+re.escape(eid)+r'")[^>]*\b'+re.escape(attr)+r'=)"'+re.escape(old)+r'"')
    out,n=pat.subn(r'\1"'+new+'"',text,count=1)
    if n!=1:
        raise RuntimeError(f'Expected one {eid} {attr}={old}, changed {n}')
    changes.append(f'{eid}: {attr} {old} -> {new}')
    return out

# -------------------------------------------------------------------
# FELLOWSHIPS: remove the old broken duplicate gates.
# The R18 roster-scope gates remain and are the single source of truth.
# -------------------------------------------------------------------
for mid in (
    'r48-vis-13', # obsolete scope=force Tactical Rite check
    'r48-vis-14', # impossible 20 Tactical Marines check (squad is 19 Marines + Sergeant)
    'r45-veteran-unit-ts-brother-hide-rite', # obsolete scope=force normal-price hide
    'r48-vis-78', # obsolete scope=force Fellowship-price show
    'r45-terminator-unit-ts-brother-hide-rite',
    'r48-vis-98',
):
    cat=remove_modifier(cat,mid)

# -------------------------------------------------------------------
# Tactical loadout error seen in New Recruit:
# mandatory auto-selected weapon links must not themselves be hidden.
# -------------------------------------------------------------------
for eid in ('load-standard-b','load-standard-p','load-add-b','load-add-p','load-add-c','load-ex-p','load-ex-c'):
    # Some already may be false; only change true if present.
    pat=re.compile(r'(<entryLink\b(?=[^>]*\bid="'+re.escape(eid)+r'")[^>]*\bhidden=)"true"')
    cat,n=pat.subn(r'\1"false"',cat,count=1)
    if n:
        changes.append(eid+': hidden true -> false')

# Guard: the alternate Magnus HQ category must be a primary category when visible.
cat=attr_replace(cat,'r18-ts-guard-magnus-hq','primary','false','true')

# Clarify the Tactical Brotherhood rule to match the actual UI and source.
old='Fellowships of Prospero only. A 20-model Tactical Squad may purchase Brotherhood of Psykers (ML1), choose a power from its Cult discipline and gain Cult Mastery.'
new='Fellowships of Prospero only. A full 20-model Legion Tactical Squad (19 Legion Tactical Marines and 1 Legion Tactical Sergeant) may purchase Brotherhood of Psykers (Mastery Level 1) for +25 points. Choose one normal Thousand Sons psychic discipline, then select one power from that discipline. The unit retains its chosen Prosperine Cult and receives that Cult Mastery.'
if old not in cat:
    raise RuntimeError('Expected Tactical Brotherhood rule text not found')
cat=cat.replace(old,new,1)
changes.append('clarified Fellowships Tactical Brotherhood rule and 20-model composition')

# Bump revision by raw text only; do NOT parse/re-serialize the catalogue.
cat,n=re.subn(r'(<catalogue\b[^>]*\brevision=")24(")',r'\g<1>25\2',cat,count=1)
if n!=1: raise RuntimeError('Could not bump CAT 24 -> 25')
idx,n=re.subn(r'(filePath="Legiones Astartes\.cat"[^>]*dataRevision=")24(")',r'\g<1>25\2',idx,count=1)
if n!=1: raise RuntimeError('Could not bump index 24 -> 25')

# -------------------------------------------------------------------
# STRUCTURAL VALIDATION: parse only after surgical editing.
# -------------------------------------------------------------------
r=ET.fromstring(cat.encode('utf-8'))
gr=ET.fromstring(gst.encode('utf-8'))
C=lambda t:'{http://www.battlescribe.net/schema/catalogueSchema}'+t
G=lambda t:'{http://www.battlescribe.net/schema/gameSystemSchema}'+t
def findid(root,i): return next((e for e in root.iter() if e.get('id')==i),None)

if r.get('revision')!='25': raise RuntimeError('Parsed CAT is not 25')

# Removed bad conditions really are gone.
for mid in ('r48-vis-13','r48-vis-14','r45-veteran-unit-ts-brother-hide-rite','r48-vis-78',
            'r45-terminator-unit-ts-brother-hide-rite','r48-vis-98'):
    if findid(r,mid) is not None: raise RuntimeError('Stale modifier survived: '+mid)

# Correct Fellowship gates must remain.
checks={
 'r18-ts-tactical-brotherhood-rite':('lessThan','1','roster','r25-rite-xv-2-the-fellowships-of-prospero'),
 'r18-ts-tactical-brotherhood-size':('lessThan','19','root-entry','tac-marine'),
 'r18-ts-veteran-unit-normal-hide-fellow':('atLeast','1','roster','r25-rite-xv-2-the-fellowships-of-prospero'),
 'r18-ts-veteran-unit-fellow-hide-normal':('lessThan','1','roster','r25-rite-xv-2-the-fellowships-of-prospero'),
 'r18-ts-terminator-unit-normal-hide-fellow':('atLeast','1','roster','r25-rite-xv-2-the-fellowships-of-prospero'),
 'r18-ts-terminator-unit-fellow-hide-normal':('lessThan','1','roster','r25-rite-xv-2-the-fellowships-of-prospero'),
}
for mid,(typ,val,scope,child) in checks.items():
    m=findid(r,mid)
    if m is None: raise RuntimeError('Required modifier missing: '+mid)
    c=next(iter(m.iter(C('condition'))),None)
    if c is None or (c.get('type'),c.get('value'),c.get('scope'),c.get('childId'))!=(typ,val,scope,child):
        raise RuntimeError('Wrong condition on '+mid)

# GST functional Rite restrictions must remain intact.
for mid,child,val in (
 ('r18-ts-fellowships-fast-max','r25-rite-xv-2-the-fellowships-of-prospero','1'),
 ('r18-ts-brotherhood-min-fellowships','r25-rite-xv-2-the-fellowships-of-prospero','2'),
):
    m=findid(gr,mid)
    if m is None: raise RuntimeError('GST Rite modifier missing: '+mid)
    c=next(iter(m.iter(G('condition'))),None)
    if c is None or c.get('scope')!='roster' or c.get('childId')!=child:
        raise RuntimeError('GST Rite modifier has wrong gate: '+mid)
    if m.get('value')!=val: raise RuntimeError('GST Rite modifier wrong value: '+mid)

# Guard functional pieces.
magnus=findid(r,'r18-ts-guard-magnus-hq')
if magnus is None or magnus.get('primary')!='true':
    raise RuntimeError('Magnus Guard HQ link not primary')
for mid in ('r19-guard-sekhmet-show-troops','r18-ts-guard-free-trans-unit','r18-ts-guard-praetor-ml3-hide'):
    if findid(r,mid) is None: raise RuntimeError('Guard functional piece missing: '+mid)

# Axis max-size enforcement must still exist.
axismods=[e for e in r.iter(C('modifier')) if (e.get('id') or '').startswith('r19-axis-max-')]
if len(axismods)<1: raise RuntimeError('Axis max-size modifiers missing')

# Mandatory Tactical weapon links must be visible in XML.
for eid in ('load-standard-b','load-standard-p'):
    e=findid(r,eid)
    if e is None or e.get('hidden')=='true':
        raise RuntimeError('Tactical mandatory weapon remains hidden: '+eid)

# Keep the edit intentionally tiny: no namespace/global reserialization.
orig=CAT.read_text(encoding='utf-8')
ratio=1.0-difflib.SequenceMatcher(None,orig,cat).ratio()
# SequenceMatcher on 18MB is expensive and not meaningful; report raw length delta instead.
delta=len(cat)-len(orig)

lines=[
 'LIVE R25 — THOUSAND SONS RITES SURGICAL FIX',
 'MODE='+('APPLY' if APPLY else 'DRY RUN'),
 'Input CAT=24 | Output CAT=25 | GST remains revision '+gr.get('revision'),
 '',
 'Fellowships of Prospero:',
 '• Removed the obsolete scope=force Rite gates that conflicted with the working roster-scope gates.',
 '• Removed the impossible 20 Tactical Marines check; a full squad is correctly 19 Tactical Marines + 1 Sergeant.',
 '• Veteran and Terminator Brotherhood pricing now relies on one clean roster-scope switch (+25 normal / +15 Fellowship).',
 '• GST checks retained and validated: maximum 1 Fast Attack and minimum 2 Psychic Brotherhoods.',
 '',
 'Guard of the Crimson King:',
 '• Magnus alternate HQ category is now primary when the Rite exposes it.',
 '• Existing Sekhmet-as-Troops, free Terminator Transponders and Praetor ML3 Rite gates were retained and validated.',
 '',
 'Axis of Dissolution:',
 f'• Existing maximum-size Troops enforcement retained and validated ({len(axismods)} active modifiers).',
 '',
 'General:',
 '• Fixed the hidden-but-mandatory Tactical Bolter/Bolt Pistol links that produced the New Recruit errors.',
 '• Catalogue was edited as raw XML text only; it was NOT re-serialized.',
 f'• Raw catalogue length delta before revision write: {delta} characters.',
 '',
 'VALIDATION: PASS'
]
OUT.write_text('\n'.join(lines),encoding='utf-8')

if APPLY:
    CAT.write_text(cat,encoding='utf-8',newline='')
    # GST intentionally unchanged.
    IDX.write_text(idx,encoding='utf-8',newline='')

print('\n'.join(lines))
