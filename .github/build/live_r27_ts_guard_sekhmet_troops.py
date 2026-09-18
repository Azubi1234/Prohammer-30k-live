from pathlib import Path
import os,re,xml.etree.ElementTree as ET

CAT=Path('Legiones Astartes.cat'); IDX=Path('index.xml')
OUT=Path('inspection-live-r27-ts-guard-sekhmet-troops.txt')
APPLY=os.environ.get('R27_APPLY','0')=='1'

cat=CAT.read_text(encoding='utf-8')
idx=IDX.read_text(encoding='utf-8')
if 'revision="26"' not in cat[:1200]: raise RuntimeError('R27 expects CAT 26')
if 'dataRevision="26"' not in idx: raise RuntimeError('R27 expects index 26')

SEK='r41-unit-xv-0-sekhmet-terminator-cabal'
GUARD='r25-rite-xv-1-the-guard-of-the-crimson-king'

def extract_selection_entry(text,eid):
    pos=text.find('id="'+eid+'"')
    if pos<0: raise RuntimeError('Entry id not found: '+eid)
    start=text.rfind('<selectionEntry',0,pos)
    if start<0: raise RuntimeError('Opening selectionEntry not found: '+eid)
    tok=re.compile(r'<selectionEntry\b|</selectionEntry>')
    depth=0
    for m in tok.finditer(text,start):
        if m.group(0).startswith('<selectionEntry'): depth+=1
        else:
            depth-=1
            if depth==0:
                end=m.end()
                return start,end,text[start:end]
    raise RuntimeError('Could not balance selectionEntry '+eid)

start,end,orig=extract_selection_entry(cat,SEK)

# Remove the misplaced R26 direct-limit modifier from the Elites category link.
orig2,n=re.subn(r'\s*<modifier id="r26-guard-sekhmet-direct-unlimited".*?</modifier>','',orig,count=1,flags=re.S)
if n not in (0,1): raise RuntimeError('Unexpected R26 direct modifier count')

# Add a ROOT-level hide under Guard to the ordinary Elites version.
root_mods_start=orig2.find('<modifiers>')
root_mods_end=orig2.find('</modifiers>',root_mods_start)
if root_mods_start<0 or root_mods_end<0: raise RuntimeError('Sekhmet root modifiers not found')
# The first modifiers block is inside category links, so find the one AFTER </categoryLinks>.
cats_end=orig2.find('</categoryLinks>')
root_mods_start=orig2.find('<modifiers>',cats_end)
root_mods_end=orig2.find('</modifiers>',root_mods_start)
if root_mods_start<0 or root_mods_end<0: raise RuntimeError('Sekhmet actual root modifiers not found')
if 'r27-guard-hide-normal-sekhmet' not in orig2[root_mods_start:root_mods_end]:
    add=f'''
        <modifier id="r27-guard-hide-normal-sekhmet" type="set" value="true" field="hidden">
          <conditions>
            <condition type="atLeast" value="1" field="selections" scope="roster" childId="{GUARD}" shared="true" includeChildSelections="true" includeChildForces="false" />
          </conditions>
        </modifier>'''
    orig2=orig2[:root_mods_end]+add+orig2[root_mods_end:]

# Replace the original block first.
cat=cat[:start]+orig2+cat[end:]

# Build Guard-specific Troops clone from the cleaned ordinary block.
clone=orig2

# Collect every local id and remap it to avoid global duplicate IDs.
ids=re.findall(r'\bid="([^"]+)"',clone)
mapping={old:'r27-guard-'+old for old in ids}
mapping[SEK]='r27-guard-sekhmet-terminator-cabal'
# Longest first to avoid partial accidental replacement inside attribute values.
for old,new in sorted(mapping.items(),key=lambda kv:len(kv[0]),reverse=True):
    clone=clone.replace('id="'+old+'"','id="'+new+'"')
    clone=clone.replace('childId="'+old+'"','childId="'+new+'"')

# Root name stays the same but mark source internally only via id.
clone=clone.replace('id="r27-guard-'+SEK+'"','id="r27-guard-sekhmet-terminator-cabal"',1)

# Replace all category links with a clean Troops primary + Brotherhood tag.
cs=clone.find('<categoryLinks>')
ce=clone.find('</categoryLinks>',cs)
if cs<0 or ce<0: raise RuntimeError('Clone categoryLinks not found')
newcats='''<categoryLinks>
        <categoryLink id="r27-guard-sekhmet-troops-primary" name="Troops — Guard of the Crimson King" hidden="false" targetId="cat-troops" primary="true" />
        <categoryLink id="r27-guard-sekhmet-brotherhood" name="Thousand Sons Psychic Brotherhood" hidden="false" targetId="r18-ts-cat-brotherhood" primary="false" />
      </categoryLinks>'''
clone=clone[:cs]+newcats+clone[ce+len('</categoryLinks>'):]

# Remove the ordinary Guard-hide modifier inherited from original and instead hide clone unless Guard.
clone=re.sub(r'\s*<modifier id="r27-guard-r27-guard-hide-normal-sekhmet".*?</modifier>','',clone,count=1,flags=re.S)
# Because ids were remapped, inherited hide id may have one prefix only depending replacement ordering.
clone=re.sub(r'\s*<modifier id="r27-guard-hide-normal-sekhmet".*?</modifier>','',clone,count=1,flags=re.S)

cats_end=clone.find('</categoryLinks>')
rms=clone.find('<modifiers>',cats_end); rme=clone.find('</modifiers>',rms)
if rms<0 or rme<0: raise RuntimeError('Clone root modifiers not found')
showguard=f'''
        <modifier id="r27-guard-sekhmet-hide-unless-rite" type="set" value="true" field="hidden">
          <conditions>
            <condition type="lessThan" value="1" field="selections" scope="roster" childId="{GUARD}" shared="true" includeChildSelections="true" includeChildForces="false" />
          </conditions>
        </modifier>'''
clone=clone[:rme]+showguard+clone[rme:]

# Remove every direct roster max=1 on the clone that came from Sekhmet's normal 0-1.
clone,n=re.subn(r'\s*<constraint id="r27-guard-r18-ts-r41-unit-xv-0-sekhmet-terminator-cabal-01"[^>]*/>','',clone,count=1)
if n!=1:
    # fallback: match the remapped original constraint id generically
    clone,n2=re.subn(r'\s*<constraint id="r27-guard-[^"]*sek[h]?met[^"]*-01"[^>]*scope="roster"[^>]*/>','',clone,count=1)
    if n2!=1: raise RuntimeError('Could not remove clone direct Sekhmet 0-1 constraint')

# Insert clone immediately after ordinary Sekhmet entry.
_,new_end,_=extract_selection_entry(cat,SEK)
cat=cat[:new_end]+'\n    '+clone+cat[new_end:]

# Bump raw revisions only.
cat,n=re.subn(r'(<catalogue\b[^>]*\brevision=")26(")',r'\g<1>27\2',cat,count=1)
if n!=1: raise RuntimeError('CAT revision bump failed')
idx,n=re.subn(r'(filePath="Legiones Astartes\.cat"[^>]*dataRevision=")26(")',r'\g<1>27\2',idx,count=1)
if n!=1: raise RuntimeError('index revision bump failed')

# Validation.
r=ET.fromstring(cat.encode('utf-8'))
ns=r.tag.split('}')[0].strip('{'); C=lambda x:f'{{{ns}}}{x}'
def f(eid): return next((e for e in r.iter() if e.get('id')==eid),None)
normal=f(SEK); guard=f('r27-guard-sekhmet-terminator-cabal')
if normal is None or guard is None: raise RuntimeError('Normal or Guard Sekhmet missing after patch')

# Normal entry hidden under Guard.
hm=f('r27-guard-hide-normal-sekhmet')
if hm is None: raise RuntimeError('Normal Sekhmet Guard hide missing')
hc=next(hm.iter(C('condition')),None)
if hc is None or hc.get('childId')!=GUARD or hc.get('type')!='atLeast':
    raise RuntimeError('Normal Sekhmet Guard hide condition wrong')

# Guard clone is a real Troops primary and not Elite.
links=guard.findall('./'+C('categoryLinks')+'/'+C('categoryLink'))
if not any(x.get('targetId')=='cat-troops' and x.get('primary')=='true' and x.get('hidden')=='false' for x in links):
    raise RuntimeError('Guard clone has no active primary Troops category')
if any(x.get('targetId')=='cat-elites' for x in links):
    raise RuntimeError('Guard clone still has Elites category')
if any(x.get('targetId') in ('r18-ts-cat-sekhmet-limit','r18-final-cat-sekhmet-01') for x in links):
    raise RuntimeError('Guard clone still carries 0-1 category tag')

# Clone hidden unless Guard.
gm=f('r27-guard-sekhmet-hide-unless-rite')
if gm is None: raise RuntimeError('Guard clone Rite gate missing')
gc=next(gm.iter(C('condition')),None)
if gc is None or gc.get('childId')!=GUARD or gc.get('type')!='lessThan':
    raise RuntimeError('Guard clone Rite gate wrong')

# No roster max=1 on Guard clone root.
for con in guard.findall('./'+C('constraints')+'/'+C('constraint')):
    if con.get('type')=='max' and con.get('field')=='selections' and con.get('scope')=='roster' and con.get('value')=='1':
        raise RuntimeError('Guard clone still has direct roster 0-1')

# The legacy catalogue already contains a handful of duplicate IDs from older passes.
# Ensure this patch introduces no duplicate IDs in its own R27 namespace.
from collections import Counter
r27ids=[e.get('id') for e in r.iter() if (e.get('id') or '').startswith('r27-guard-')]
dupes=[k for k,v in Counter(r27ids).items() if v>1]
if dupes:
    raise RuntimeError('Duplicate R27 Guard IDs after clone: '+str(dupes[:20]))
if len(r27ids)<20:
    raise RuntimeError('Unexpectedly few R27 Guard IDs; clone may be incomplete')

lines=[
 'LIVE R27 — GUARD OF THE CRIMSON KING SEKHMET TROOPS FIX',
 'MODE='+('APPLY' if APPLY else 'DRY RUN'),
 'CAT 26 -> 27',
 '',
 '• Ordinary Sekhmet remains the normal Elites 0-1 entry outside the Rite.',
 '• Under Guard of the Crimson King, the ordinary Elites entry is hidden and a dedicated Sekhmet Troops entry is exposed.',
 '• The Guard entry has Troops as its only primary FOC category, so it occupies and fulfils Troops slots in New Recruit.',
 '• The Guard entry carries no Sekhmet 0-1 tags or direct roster 0-1 constraint.',
 '• The Guard entry retains the full Sekhmet unit/options/rules and Psychic Brotherhood tag.',
 '• Raw catalogue editing only; the full catalogue is not re-serialized.',
 '',
 'VALIDATION: PASS'
]
OUT.write_text('\n'.join(lines),encoding='utf-8')
if APPLY:
    CAT.write_text(cat,encoding='utf-8',newline='')
    IDX.write_text(idx,encoding='utf-8',newline='')
print('\n'.join(lines))
