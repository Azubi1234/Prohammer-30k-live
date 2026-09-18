from pathlib import Path
import os,re,xml.etree.ElementTree as ET

CAT=Path('Legiones Astartes.cat'); GST=Path('Prohammer 30k.gst'); IDX=Path('index.xml')
OUT=Path('inspection-live-r26-ts-discipline-guard.txt')
APPLY=os.environ.get('R26_APPLY','0')=='1'

cat=CAT.read_text(encoding='utf-8')
gst=GST.read_text(encoding='utf-8')
idx=IDX.read_text(encoding='utf-8')

if 'revision="25"' not in cat[:1200]:
    raise RuntimeError('R26 expects CAT revision 25')
if 'dataRevision="25"' not in idx:
    raise RuntimeError('R26 expects index dataRevision 25')

GUARD='r25-rite-xv-1-the-guard-of-the-crimson-king'
BRO_TARGET='r45-ts-tactical-brotherhood'

def replace_condition_child(text,mid,old,new):
    pat=re.compile(r'(<modifier\b(?=[^>]*\bid="'+re.escape(mid)+r'")[^>]*>.*?<condition\b[^>]*\bchildId=")'+re.escape(old)+r'("[^>]*/>.*?</modifier>)',re.S)
    out,n=pat.subn(r'\1'+new+r'\2',text,count=1)
    if n!=1: raise RuntimeError(f'Could not retarget {mid}; found {n}')
    return out

# Tactical Brotherhood UI: the selected roster object is the shared target, not the entryLink id.
for mid in (
    'r19-ts-tactical-brotherhood-disc-hide-0',
    'r19-ts-tactical-brotherhood-disc-min-on',
    'r19-ts-tactical-brotherhood-pow-hide-0',
    'r19-ts-tactical-brotherhood-pow-min-on',
):
    cat=replace_condition_child(cat,mid,'r45-tactical-ts-brother',BRO_TARGET)

# Clearer labels for the actual two-step UI.
cat=cat.replace(
    'name="Fellowships Psychic Brotherhood — Psychic Discipline(s)"',
    'name="Psychic Discipline — choose 1"',
    1
)
cat=cat.replace(
    'name="Fellowships Psychic Brotherhood — Psychic Powers"',
    'name="Psychic Power — choose 1 from selected discipline"',
    1
)

# Guard Praetor ML3: hide it unless Guard is selected.
ml3_pat=re.compile(r'(<selectionEntry\b(?=[^>]*\bid="r18-ts-guard-praetor-ml3")[^>]*>)(.*?)(</selectionEntry>)',re.S)
m=ml3_pat.search(cat)
if not m: raise RuntimeError('Praetor ML3 entry not found')
body=m.group(2)
# Remove any prior R26 modifier if rerun.
body=re.sub(r'<modifiers>\s*<modifier id="r26-ts-guard-ml3-hide".*?</modifiers>\s*','',body,flags=re.S)
mod=f'''<modifiers>
          <modifier id="r26-ts-guard-ml3-hide" type="set" value="true" field="hidden">
            <conditions>
              <condition type="lessThan" value="1" field="selections" scope="roster" childId="{GUARD}" shared="true" includeChildSelections="true" includeChildForces="false" />
            </conditions>
          </modifier>
        </modifiers>'''
body=body+mod
cat=cat[:m.start()]+m.group(1)+body+m.group(3)+cat[m.end():]

# Guard explicitly overrides the main Sekhmet roster 0-1 constraint.
sek_id='r41-unit-xv-0-sekhmet-terminator-cabal'
idpos=cat.find('id="'+sek_id+'"')
unit_start=cat.rfind('<selectionEntry',0,idpos)
if idpos<0 or unit_start<0: raise RuntimeError('Sekhmet root entry not found')
first_children=cat.find('<selectionEntries>',unit_start)
mods_start=cat.find('<modifiers>',unit_start,first_children)
mods_end=cat.find('</modifiers>',mods_start,first_children)
if mods_start<0 or mods_end<0: raise RuntimeError('Sekhmet direct modifiers container not found')
direct_block=cat[mods_start:mods_end+len('</modifiers>')]
if 'r26-guard-sekhmet-direct-unlimited' not in direct_block:
    extra=f'''
        <modifier id="r26-guard-sekhmet-direct-unlimited" type="set" value="99" field="r18-ts-r41-unit-xv-0-sekhmet-terminator-cabal-01">
          <conditions>
            <condition type="atLeast" value="1" field="selections" scope="roster" childId="{GUARD}" shared="true" includeChildSelections="true" includeChildForces="false" />
          </conditions>
        </modifier>'''
    cat=cat[:mods_end]+extra+cat[mods_end:]

# Update Guard rule wording: requested interpretation overrides Sekhmet's normal 0-1.
old_note='Sekhmet Terminator Cabals are Troops choices and must fulfil the compulsory Troops selections. Note: the Sekhmet entry is also explicitly 0–1; that written source contradiction is preserved rather than silently overridden.'
new_note='Sekhmet Terminator Cabals are Troops choices and must fulfil the compulsory Troops selections. While using The Guard of the Crimson King, ignore the normal 0–1 restriction on Sekhmet Terminator Cabals.'
if old_note in cat:
    cat=cat.replace(old_note,new_note,1)
else:
    # tolerate older wording but insist rule exists
    if 'id="r19-guard-scarab"' not in cat:
        raise RuntimeError('Guard Sekhmet rule not found')

# GST: both independent hidden 0-1 category caps must be disabled under Guard.
def add_guard_override_to_catlink(text,link_id,constraint_id,mod_id):
    pat=re.compile(r'(<categoryLink\b(?=[^>]*\bid="'+re.escape(link_id)+r'")[^>]*>)(.*?)(</categoryLink>)',re.S)
    m=pat.search(text)
    if not m: raise RuntimeError('GST categoryLink missing '+link_id)
    body=m.group(2)
    # idempotence
    body=re.sub(r'<modifiers>\s*<modifier id="'+re.escape(mod_id)+r'".*?</modifiers>\s*','',body,flags=re.S)
    add=f'''<modifiers>
        <modifier id="{mod_id}" type="set" value="99" field="{constraint_id}">
          <conditions>
            <condition type="atLeast" value="1" field="selections" scope="roster" childId="{GUARD}" shared="true" includeChildSelections="true" includeChildForces="false" />
          </conditions>
        </modifier>
      </modifiers>'''
    body=body+add
    return text[:m.start()]+m.group(1)+body+m.group(3)+text[m.end():]

gst=add_guard_override_to_catlink(gst,'r18-ts-sekhmet-limit','r18-ts-sekhmet-limit-max','r26-guard-sekhmet-limit-unlimited')
gst=add_guard_override_to_catlink(gst,'r18-final-cat-sekhmet-01-force','r18-final-cat-sekhmet-01-max','r26-guard-sekhmet-final-unlimited')

# Revision bump by text only.
cat,n=re.subn(r'(<catalogue\b[^>]*\brevision=")25(")',r'\g<1>26\2',cat,count=1)
if n!=1: raise RuntimeError('Could not bump CAT 25 -> 26')
idx,n=re.subn(r'(filePath="Legiones Astartes\.cat"[^>]*dataRevision=")25(")',r'\g<1>26\2',idx,count=1)
if n!=1: raise RuntimeError('Could not bump index 25 -> 26')

# Parse edited text for validation only.
r=ET.fromstring(cat.encode())
gr=ET.fromstring(gst.encode())
C=lambda t:'{http://www.battlescribe.net/schema/catalogueSchema}'+t
G=lambda t:'{http://www.battlescribe.net/schema/gameSystemSchema}'+t
def f(root,i): return next((e for e in root.iter() if e.get('id')==i),None)

# Discipline UI now keys off actual shared Brotherhood selection target.
for mid in (
    'r19-ts-tactical-brotherhood-disc-hide-0','r19-ts-tactical-brotherhood-disc-min-on',
    'r19-ts-tactical-brotherhood-pow-hide-0','r19-ts-tactical-brotherhood-pow-min-on'):
    mm=f(r,mid)
    if mm is None: raise RuntimeError('Missing tactical psychic UI modifier '+mid)
    cc=next(mm.iter(C('condition')),None)
    if cc is None or cc.get('childId')!=BRO_TARGET:
        raise RuntimeError('Tactical psychic UI still keyed to wrong id: '+mid)

# Guard Sekhmet direct and both force caps all change to 99 under the Rite.
dm=f(r,'r26-guard-sekhmet-direct-unlimited')
if dm is None or dm.get('field')!='r18-ts-r41-unit-xv-0-sekhmet-terminator-cabal-01':
    raise RuntimeError('Direct Sekhmet 0-1 override missing')
for mid,cid in (
    ('r26-guard-sekhmet-limit-unlimited','r18-ts-sekhmet-limit-max'),
    ('r26-guard-sekhmet-final-unlimited','r18-final-cat-sekhmet-01-max')):
    mm=f(gr,mid)
    if mm is None or mm.get('field')!=cid or mm.get('value')!='99':
        raise RuntimeError('GST Sekhmet cap override missing '+mid)
    cc=next(mm.iter(G('condition')),None)
    if cc is None or cc.get('childId')!=GUARD or cc.get('scope')!='roster':
        raise RuntimeError('GST Sekhmet cap override gate wrong '+mid)

# Guard role changes still present.
for rid in ('r19-guard-sekhmet-show-troops','r18-ts-guard-magnus-show-hq','r18-ts-guard-free-trans-unit','r26-ts-guard-ml3-hide'):
    if f(r,rid) is None: raise RuntimeError('Guard functional piece missing '+rid)

lines=[
 'LIVE R26 — THOUSAND SONS DISCIPLINE + GUARD FIX',
 'MODE='+('APPLY' if APPLY else 'DRY RUN'),
 'CAT 25 -> 26 | GST revision remains '+gr.get('revision'),
 '',
 '• Fellowships Tactical Brotherhood now keys its Discipline/Power UI to the actual selected shared Brotherhood upgrade, so the discipline selector appears after the +25 Brotherhood upgrade is chosen.',
 '• UI is explicitly two-step: Psychic Discipline (choose 1) -> Psychic Power (choose 1 from selected discipline).',
 '• Guard Praetor Mastery Level 3 upgrade is now hidden unless Guard of the Crimson King is selected.',
 '• Guard of the Crimson King now explicitly ignores Sekhmet 0-1 as requested.',
 '• All three Sekhmet 0-1 enforcement layers are overridden under Guard: direct roster max + both hidden force-category max constraints.',
 '• Existing Sekhmet -> Troops, Magnus -> HQ and free Terminator Transponder logic remains in place.',
 '• Raw XML text editing only; no catalogue re-serialization.',
 '',
 'VALIDATION: PASS'
]
OUT.write_text('\n'.join(lines),encoding='utf-8')

if APPLY:
    CAT.write_text(cat,encoding='utf-8',newline='')
    GST.write_text(gst,encoding='utf-8',newline='')
    IDX.write_text(idx,encoding='utf-8',newline='')

print('\n'.join(lines))
