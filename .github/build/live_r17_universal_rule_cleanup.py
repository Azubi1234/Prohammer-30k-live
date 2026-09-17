from pathlib import Path
import re
import xml.etree.ElementTree as ET

CAT=Path('Legiones Astartes.cat'); IDX=Path('index.xml'); OUT=Path('inspection-live-r17-universal-rule-cleanup.txt')
NS='http://www.battlescribe.net/schema/catalogueSchema'; ET.register_namespace('',NS); C=lambda t:f'{{{NS}}}{t}'
ct=ET.parse(CAT); root=ct.getroot()
if root.get('revision')!='16': raise RuntimeError(f'Expected CAT 16, got {root.get("revision")}')

def norm(s): return re.sub(r'\s+',' ',(s or '').strip())

# One canonical reminder for ordinary universal rules.  Contextual/modified versions are deliberately left alone.
CANON={
 'Fearless':'This unit is Fearless.',
 'Fear':'This unit has Fear.',
 'Fleet':'This unit has Fleet.',
 'Counter-Attack':'This unit has Counter-Attack.',
 'Adamantium Will':'This unit has Adamantium Will.',
 'Eternal Warrior':'This unit has Eternal Warrior.',
 'Furious Charge':'This unit has Furious Charge.',
 'Scout':'This unit has Scout.',
 'Infiltrate':'This unit has Infiltrate.',
 'Move Through Cover':'This unit has Move Through Cover.',
 'Acute Senses':'This unit has Acute Senses.',
 'Stealth':'This unit has Stealth.',
 'Deep Strike':'This unit has Deep Strike.',
}
MASTER='A Detachment containing a model with this rule may select one Rite of War for which it qualifies. An army may include no more than one model with Master of the Legion for every full 1,000 points. A model with this rule may select an eligible retinue as described by its entry.'

# Phrases which are merely local reminders of a universal rule and therefore create duplicate New Recruit popup lines.
def is_plain_reminder(name, desc):
    d=norm(desc); l=d.lower(); n=name.lower()
    if not d: return False
    if name=='Master of the Legion':
        # All current Master of the Legion local descriptions only restate the shared rule; use the complete Praetor wording.
        return True
    if name not in CANON: return False
    if l==CANON[name].lower(): return False
    # Keep genuinely modified/contextual versions (Drop Pod Deep Strike, Mutable Tactics, Thiel duration, etc.).
    contextual=('except as modified','drop pod assault','mutable tactic','for the duration','thiel and','orth’s vehicle','orth\'s vehicle')
    if any(x in l for x in contextual): return False
    # Standard reminder phrasings generated throughout the catalogue.
    if 'uses the normal' in l: return True
    if 'uses the prohammer' in l: return True
    if 'using the normal prohammer' in l: return True
    if l.startswith('this unit is '+n): return True
    if l.startswith('this unit has '+n): return True
    if l.startswith('the unit has '+n): return True
    if l.startswith('the squad has '+n): return True
    if l.startswith('the squadron has '+n): return True
    if l.startswith('rylanor has '+n): return True
    if name=='Stealth' and ('has the stealth special rule' in l or 'stealth special rule' in l): return True
    return False

changed=[]
for owner in root.iter():
    rs=owner.find(C('rules'))
    if rs is None: continue
    for r in rs:
        name=norm(r.get('name'))
        d=r.find(C('description'))
        if d is None: continue
        old=norm(d.text)
        if name=='Master of the Legion':
            new=MASTER
            if old!=new:
                d.text=new; changed.append((owner.get('id'),owner.get('name'),name,old,new))
        elif is_plain_reminder(name,old):
            new=CANON[name]
            if old!=new:
                d.text=new; changed.append((owner.get('id'),owner.get('name'),name,old,new))

root.set('revision','17')
ct.write(CAT,encoding='utf-8',xml_declaration=True)

# index revision bump
it=ET.parse(IDX); ir=it.getroot()
for e in ir.iter():
    if e.get('filePath')=='Legiones Astartes.cat': e.set('dataRevision','17')
it.write(IDX,encoding='utf-8',xml_declaration=True)

# Verify that the exact Fearless variants from the reported popup are gone.
ct2=ET.parse(CAT); rr=ct2.getroot(); bad=[]
for r in rr.iter(C('rule')):
    n=norm(r.get('name')); d=r.find(C('description')); txt=norm(d.text if d is not None else '')
    if n in CANON and any(x in txt.lower() for x in ('uses the normal prohammer','uses the normal fearless','uses the prohammer fearless','normal fearless special rule')):
        bad.append((r.get('id'),n,txt))
if bad: raise RuntimeError('Generic reminder variants remain: '+repr(bad[:10]))

lines=['LIVE R17 — UNIVERSAL SPECIAL-RULE POPUP CLEANUP',f'CAT=17 GSTref={root.get("gameSystemRevision")}', '',
       'Standard universal-rule reminder text is now canonicalised so New Recruit merges identical rules instead of showing several near-identical lines.',
       'Contextual rules that genuinely change how a universal rule is gained or used are preserved.', '',f'Changed rule descriptions: {len(changed)}']
from collections import Counter
cnt=Counter(x[2] for x in changed)
for n,c in sorted(cnt.items()): lines.append(f'• {n}: {c}')
lines.append('\nExamples:')
for owner_id,owner_name,n,old,new in changed[:40]: lines.append(f'• {owner_name or owner_id} — {n}: {old} -> {new}')
OUT.write_text('\n'.join(lines),encoding='utf-8')
print('\n'.join(lines[:40]))
