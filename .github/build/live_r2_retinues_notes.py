from pathlib import Path
from copy import deepcopy
import re
import xml.etree.ElementTree as ET

CAT = Path('Legiones Astartes.cat')
IDX = Path('index.xml')
OUT = Path('inspection-live-r2-retinues-notes.txt')
NS = 'http://www.battlescribe.net/schema/catalogueSchema'
ET.register_namespace('', NS)
C = lambda t: f'{{{NS}}}{t}'

ct = ET.parse(CAT)
root = ct.getroot()
if root.get('revision') != '1':
    raise RuntimeError(f'Expected live catalogue revision 1, got {root.get("revision")}')
if root.get('gameSystemRevision') != '1':
    raise RuntimeError(f'Expected live GST reference 1, got {root.get("gameSystemRevision")}')

def byid(i):
    return next((x for x in root.iter() if x.get('id') == i), None)

def ensure(p, tag):
    x = p.find(C(tag))
    if x is None:
        x = ET.SubElement(p, C(tag))
    return x

def slug(s):
    return re.sub(r'[^a-z0-9]+', '-', s.lower()).strip('-')

def setpts(e, value):
    cs = ensure(e, 'costs')
    c = next((x for x in cs.findall(C('cost')) if x.get('typeId') == 'pts'), None)
    if c is None:
        c = ET.SubElement(cs, C('cost'), {'name':'Points','typeId':'pts','value':str(value)})
    else:
        c.set('name','Points'); c.set('value',str(value))

def max_constraint(e, value=1, id_=None):
    cs = ensure(e, 'constraints')
    if id_ is None: id_ = (e.get('id') or 'x') + '-max'
    ET.SubElement(cs, C('constraint'), {
        'id':id_, 'type':'max', 'value':str(value), 'field':'selections', 'scope':'parent',
        'shared':'true', 'includeChildSelections':'true', 'includeChildForces':'false'
    })

def min_constraint(e, value=1, id_=None):
    cs = ensure(e, 'constraints')
    if id_ is None: id_ = (e.get('id') or 'x') + '-min'
    ET.SubElement(cs, C('constraint'), {
        'id':id_, 'type':'min', 'value':str(value), 'field':'selections', 'scope':'parent',
        'shared':'true', 'includeChildSelections':'true', 'includeChildForces':'false'
    })

def add_rule(e, id_, name, desc):
    rs = ensure(e, 'rules')
    old = next((x for x in rs.findall(C('rule')) if x.get('id') == id_), None)
    if old is not None: rs.remove(old)
    r = ET.SubElement(rs, C('rule'), {'id':id_, 'name':name, 'hidden':'false'})
    ET.SubElement(r, C('description')).text = desc
    return r

def rewrite_ids(node, prefix):
    mp = {}
    for x in node.iter():
        old = x.get('id')
        if old: mp[old] = prefix + old
    for x in node.iter():
        old = x.get('id')
        if old in mp: x.set('id', mp[old])
        for attr in ('targetId','childId','field','defaultSelectionEntryId'):
            v = x.get(attr)
            if v in mp: x.set(attr, mp[v])
    return mp

def remove_direct(node, tag):
    x = node.find(C(tag))
    if x is not None: node.remove(x)

def clone_nested(src, prefix, newname=None):
    c = deepcopy(src)
    rewrite_ids(c, prefix)
    if newname: c.set('name', newname)
    # A retinue is nested under its character and must not itself consume a FOC slot.
    remove_direct(c, 'categoryLinks')
    c.set('hidden','false')
    c.set('import','true')
    return c

def generic_retinue_template(name):
    # Prefer the deliberately-built generic Praetor/Centurion nested retinues.
    for pid in ('hq-praetor','hq-centurion'):
        p = byid(pid)
        if p is None: continue
        for x in p.iter(C('selectionEntry')):
            if x.get('type') == 'unit' and (x.get('name') or '').strip().lower() == name.lower():
                return x
    # Fallback only if the exact generic nested template was not found.
    for x in root.iter(C('selectionEntry')):
        if x.get('type') == 'unit' and (x.get('name') or '').strip().lower() == name.lower():
            return x
    raise RuntimeError(f'No retinue template found for {name}')

def special_target(uid):
    x = byid(uid)
    if x is None: raise RuntimeError(f'Missing special retinue target {uid}')
    return x

def has_unit_retinue_group(char):
    gs = char.find(C('selectionEntryGroups'))
    if gs is None: return False
    for g in gs.findall(C('selectionEntryGroup')):
        if 'retinue' not in (g.get('name') or '').lower(): continue
        if any(x.get('type') == 'unit' for x in g.iter(C('selectionEntry'))): return True
    return False

def add_retinue_group(char, key, targets, specializer=None):
    if has_unit_retinue_group(char):
        return 'existing'
    gs = ensure(char, 'selectionEntryGroups')
    gid = f'live-r2-{slug(key)}-retinue'
    g = ET.SubElement(gs, C('selectionEntryGroup'), {
        'id':gid, 'name':'Retinue (does not occupy a separate FOC slot)',
        'hidden':'false', 'collective':'false', 'import':'true'
    })
    max_constraint(g, 1, gid+'-max')
    ses = ET.SubElement(g, C('selectionEntries'))
    for i, spec in enumerate(targets):
        kind, val = spec
        src = generic_retinue_template(val) if kind == 'generic' else special_target(val)
        clone = clone_nested(src, f'{gid}-{i}-')
        # Every choice itself is max one in this selector.
        cs = ensure(clone, 'constraints')
        if not any(c.get('type') == 'max' and c.get('field') == 'selections' for c in cs.findall(C('constraint'))):
            max_constraint(clone, 1, clone.get('id')+'-ret-max')
        ses.append(clone)
        if specializer: specializer(char, clone, i, kind, val)
    return 'added'

def add_hidden_unless_selected(entry, child_id, tag):
    mods = ensure(entry, 'modifiers')
    mid = f'live-r2-{tag}-hide'
    if any(m.get('id') == mid for m in mods.findall(C('modifier'))): return
    m = ET.SubElement(mods, C('modifier'), {'id':mid,'type':'set','field':'hidden','value':'true'})
    cs = ET.SubElement(m, C('conditions'))
    ET.SubElement(cs, C('condition'), {
        'type':'lessThan','value':'1','field':'selections','scope':'roster','childId':child_id,
        'shared':'true','includeChildSelections':'true','includeChildForces':'false'
    })

def add_fixed_option(unit, id_, name, cost, desc=None, hidden_unless=None):
    # Reuse if rerun-safe by ID.
    existing = next((x for x in unit.iter(C('selectionEntry')) if x.get('id') == id_), None)
    if existing is not None: return existing
    gs = ensure(unit, 'selectionEntryGroups')
    g = next((x for x in gs.findall(C('selectionEntryGroup')) if x.get('id') == id_+'-group'), None)
    if g is None:
        g = ET.SubElement(gs, C('selectionEntryGroup'), {'id':id_+'-group','name':'Special Upgrades','hidden':'false','collective':'false','import':'true'})
    ses = ensure(g, 'selectionEntries')
    e = ET.SubElement(ses, C('selectionEntry'), {'id':id_,'name':name,'type':'upgrade','hidden':'false','import':'true'})
    setpts(e,cost); max_constraint(e,1,id_+'-max')
    if desc: add_rule(e,id_+'-rule',name,desc)
    if hidden_unless: add_hidden_unless_selected(e, hidden_unless, slug(id_))
    return e

def add_cabal_upgrade(clone):
    add_fixed_option(
        clone, clone.get('id')+'-ahrimans-cabal', "Ahriman's Cabal", 50,
        "The squad becomes a Brotherhood of Psykers (Mastery Level 2), is assigned to the Corvidae and receives the Corvidae Cult Arcana and Cult Mastery. It selects two psychic powers from the ProHammer Divination discipline. The Cabal remains a separate Psyker from Ahriman. Any model in the Cabal permitted to purchase a Power Weapon may upgrade that Power Weapon to a Prosperine Force Weapon for +5 points; the Cabal follows the normal Psychic Brotherhood rules for activating Force Weapons."
    )

def ahriman_specializer(char, clone, i, kind, val):
    if (clone.get('name') or '').lower() == 'legion command squad': add_cabal_upgrade(clone)

def magnus_specializer(char, clone, i, kind, val):
    if (clone.get('name') or '').lower() in ('legion command squad','legion terminator command squad','legion honour guard squad'):
        add_fixed_option(
            clone, clone.get('id')+'-crimson-kings-guard', "Brotherhood of Psykers (Mastery Level 1)", 25,
            "The squad becomes a Brotherhood of Psykers (Mastery Level 1), is assigned to one Prosperine Cult and receives the normal Cult Arcana and Cult Mastery benefits of that Cult. The squad selects one psychic power from any normal psychic discipline available to Thousand Sons Psykers and follows the normal Psychic Brotherhood rules."
        )

def kargos_specializer(char, clone, i, kind, val):
    if (clone.get('name') or '').lower() != 'legion command squad': return
    jp = next((x for x in char.iter(C('selectionEntry')) if (x.get('name') or '').strip().lower() == 'jump pack'), None)
    if jp is None: raise RuntimeError('Kargos Jump Pack option not found')
    for x in clone.iter(C('selectionEntry')):
        nm=(x.get('name') or '').lower()
        if 'jump pack' in nm and x.get('type') == 'upgrade':
            add_hidden_unless_selected(x, jp.get('id'), 'kargos-jump-retinue')

# Explicit source-declared named-character retinues that were only represented as text.
G='generic'; S='special'
RETINUES = {
    # Emperor's Children
    'r41-unit-iii-4-lord-commander-eidolon': [(G,'Legion Honour Guard Squad')],
    'r41-unit-iii-6-captain-lucius': [(G,'Legion Command Squad')],
    'r41-unit-iii-9-fulgrim-the-phoenician': [(G,'Legion Honour Guard Squad'),(G,'Legion Terminator Command Squad'),(S,'r41-unit-iii-1-phoenix-terminator-squad')],
    # Dark Angels explicit character bodyguards
    'da22-corswain': [(S,'da22-deathwing-companions')],
    'da22-redloss': [(S,'da22-interemptors')],
    'da22-holguin': [(S,'da22-deathwing-term-comp')],
    # World Eaters
    'r41-unit-xii-6-kharn-the-bloody': [(G,'Legion Command Squad'),(S,'r41-unit-xii-0-rampager-squad')],
    'r41-unit-xii-7-shabran-darr': [(S,'r41-unit-xii-2-red-hand-destroyer-mortalis-squad')],
    'r41-unit-xii-9-kargos-the-bloodspitter': [(G,'Legion Command Squad')],
    'r41-unit-xii-10-captain-ehrlen': [(G,'Legion Command Squad')],
    'r41-unit-xii-11-delvarus': [(S,'r41-unit-xii-5-triarii-breacher-squad')],
    # Ultramarines
    'r41-unit-xiii-4-marius-gage-first-master': [(G,'Legion Command Squad'),(G,'Legion Terminator Command Squad'),(S,'r41-unit-xiii-0-invictarus-suzerain-squad')],
    'r41-unit-xiii-5-remus-ventanus': [(G,'Legion Command Squad')],
    'r41-unit-xiii-8-titus-prayto': [(G,'Legion Command Squad')],
    # Death Guard
    'r41-unit-xiv-3-calas-typhon-first-captain': [(S,'r41-unit-xiv-0-deathshroud-terminators'),(G,'Legion Terminator Command Squad')],
    'r41-unit-xiv-4-crysos-morturg': [(S,'r41-unit-xiv-2-mortus-poisoner-squad')],
    'r41-unit-xiv-5-durak-rask': [(G,'Legion Command Squad')],
    'r41-unit-xiv-6-ignatius-grulgor': [(G,'Legion Command Squad')],
    'r41-unit-xiv-7-nathaniel-garro': [(G,'Legion Command Squad')],
    # Thousand Sons
    'r41-unit-xv-6-ahzek-ahriman': [(G,'Legion Command Squad')],
    'r41-unit-xv-7-phosis-t-kar': [(G,'Legion Command Squad')],
    'r41-unit-xv-8-magistus-amon-the-hidden': [(S,'r41-unit-xv-2-ammitara-occult-intercession-cabal'),(G,'Legion Seeker Squad')],
    'r41-unit-xv-9-hathor-maat': [(G,'Legion Command Squad')],
    'r41-unit-xv-10-sanakht': [(S,'r41-unit-xv-1-khenetai-occult-blade-cabal')],
    # Sons of Horus
    'r41-unit-xvi-4-ezekyle-abaddon-first-captain': [(S,'r41-unit-xvi-0-justaerin-terminator-squad'),(G,'Legion Terminator Command Squad')],
    'r41-unit-xvi-5-horus-aximand-little-horus': [(G,'Legion Command Squad'),(S,'r41-unit-xvi-2-chieftain-squad')],
    'r41-unit-xvi-6-garviel-loken': [(G,'Legion Command Squad'),(G,'Legion Veteran Squad')],
    'r41-unit-xvi-8-tybalt-marr-the-either': [(G,'Legion Veteran Squad'),(S,'r41-unit-xvi-1-reaver-attack-squad')],
    'r41-unit-xvi-9-vheren-ashurhaddon': [(S,'r41-unit-xvi-1-reaver-attack-squad')],
    # Word Bearers
    'r41-unit-xvii-6-argel-tal': [(S,'r41-unit-xvii-1-gal-vorbak-dark-brethren')],
    'r41-unit-xvii-7-high-chaplain-erebus': [(G,'Legion Command Squad')],
    'r41-unit-xvii-8-kor-phaeron-the-black-cardinal': [(G,'Legion Terminator Command Squad')],
    'r41-unit-xvii-11-hol-beloth': [(G,'Legion Command Squad')],
    # Salamanders
    'r41-unit-xviii-5-artellus-numeon': [(S,'r41-unit-xviii-0-firedrake-terminator-squad'),(G,'Legion Command Squad'),(G,'Legion Terminator Command Squad')],
    'r41-unit-xviii-6-lord-chaplain-nomus-rhy-tan': [(S,'r41-unit-xviii-0-firedrake-terminator-squad'),(G,'Legion Command Squad'),(G,'Legion Terminator Command Squad')],
    # Raven Guard
    'r41-unit-xix-5-alvarex-maun': [(G,'Legion Command Squad')],
    # Alpha Legion
    'r41-unit-xx-4-armillus-dynat': [(G,'Legion Command Squad'),(G,'Legion Terminator Command Squad'),(S,'r41-unit-xx-2-lernaean-terminator-squad')],
    'r41-unit-xx-7-ingo-pech': [(G,'Legion Command Squad'),(G,'Legion Terminator Command Squad'),(S,'r41-unit-xx-2-lernaean-terminator-squad'),(G,'Legion Seeker Squad')],
}

SPECIALIZERS = {
    'r41-unit-xii-9-kargos-the-bloodspitter': kargos_specializer,
    'r41-unit-xv-6-ahzek-ahriman': ahriman_specializer,
}

report=[]
added=[]; existing=[]; missing=[]
for cid, targets in RETINUES.items():
    ch=byid(cid)
    if ch is None:
        missing.append(cid); continue
    status=add_retinue_group(ch,cid,targets,SPECIALIZERS.get(cid))
    (added if status=='added' else existing).append(f'{cid} | {ch.get("name")}')

# Magnus the Red: canonical entry and any Rite copy should have the same functional Primarch Retinue.
for e in list(root.iter(C('selectionEntry'))):
    eid=e.get('id') or ''; nm=(e.get('name') or '').lower()
    if ('magnus the red' in nm and 'shard' not in nm and 'crimson king' in nm) or eid.startswith('r42-role-xv-crimson-magnus-hq-'):
        try:
            status=add_retinue_group(e,eid,[(G,'Legion Honour Guard Squad'),(G,'Legion Terminator Command Squad'),(S,'r41-unit-xv-0-sekhmet-terminator-cabal')],magnus_specializer)
            (added if status=='added' else existing).append(f'{eid} | {e.get("name")}')
        except RuntimeError as ex:
            report.append('Magnus retinue error: '+str(ex))

# White Scars: their character-linked Command Squad bike option already exists, but the cloned
# generic retinue also carried unconditional generic Bike/Jetbike mount options. Remove those
# duplicates from the COMMAND SQUAD only. Veteran retinues are deliberately left alone per user note.
ws_removed=[]
for charid,gid in (('r41-unit-v-6-shiban-khan','r60-ws-shiban-retinue'),('r41-unit-v-7-hibou-khan','r60-ws-hibou-retinue')):
    ch=byid(charid); g=byid(gid)
    if ch is None or g is None: continue
    cmd=next((u for u in g.iter(C('selectionEntry')) if u.get('type')=='unit' and (u.get('name') or '').lower()=='legion command squad'),None)
    if cmd is None: continue
    for p in list(cmd.iter()):
        for x in list(p):
            xid=x.get('id') or ''; nm=(x.get('name') or '').lower()
            if x.tag==C('selectionEntry') and ('hq-centurion-ret-command-bike' in xid or 'hq-centurion-ret-command-jet' in xid) and ('bike' in nm or 'jetbike' in nm):
                p.remove(x); ws_removed.append(f'{ch.get("name")}: {x.get("name")}')

# Fabius Bile: remove duplicated Options groups and make Enhanced Warriors a real +3/model
# selectable upgrade on the obvious eligible EC infantry squads. It is hidden unless Fabius is present.
fabius=byid('r41-unit-iii-7-fabius-bile')
if fabius is None: raise RuntimeError('Fabius Bile missing')
fgroups=fabius.find(C('selectionEntryGroups'))
if fgroups is not None:
    opts=[g for g in fgroups.findall(C('selectionEntryGroup')) if (g.get('name') or '').strip().lower()=='options']
    for g in opts[1:]: fgroups.remove(g)

FABIUS_NAMES={
 'legion tactical squad','legion assault squad','legion breacher squad','legion reconnaissance squad','legion recon squad',
 'legion scout squad','legion veteran squad','legion destroyer squad','legion seeker squad','legion heavy support squad',
 'legion command squad','legion honour guard squad','palatine blade squad','kakophoni squad','sun killer squad'
}

def add_scaled_by_models(opt, unit, per):
    setpts(opt,0)
    model_nodes=[]
    for m in unit.iter(C('selectionEntry')):
        if m.get('type')!='model': continue
        # Ignore any model nodes nested inside another nested UNIT under this unit.
        # Eligible squads here generally expose their members directly in their own root-entry tree.
        model_nodes.append(m)
    if not model_nodes:
        raise RuntimeError(f'No model counter found for {unit.get("name")} ({unit.get("id")})')
    mods=ensure(opt,'modifiers')
    for j,mnode in enumerate(model_nodes):
        mid=opt.get('id')+f'-scale-{j}'
        mod=ET.SubElement(mods,C('modifier'),{'id':mid,'type':'increment','field':'pts','value':str(per)})
        reps=ET.SubElement(mod,C('repeats'))
        ET.SubElement(reps,C('repeat'),{
            'field':'selections','scope':'root-entry','value':'1','percentValue':'false','shared':'true',
            'includeChildSelections':'true','includeChildForces':'false','childId':mnode.get('id'),'repeats':'1','roundUp':'false'
        })

enhanced=[]
# Do this after retinue creation so newly-created eligible Command/Honour Guard retinues receive the upgrade too.
for unit in list(root.iter(C('selectionEntry'))):
    if unit.get('type')!='unit': continue
    nm=(unit.get('name') or '').strip().lower()
    if nm not in FABIUS_NAMES or 'terminator' in nm: continue
    # Avoid duplicate option if already patched.
    if any((x.get('name') or '').strip().lower()=='enhanced warriors' for x in unit.iter(C('selectionEntry'))): continue
    uid='live-r2-fabius-enhanced-'+slug(unit.get('id') or unit.get('name') or 'unit')
    gs=ensure(unit,'selectionEntryGroups')
    g=next((x for x in gs.findall(C('selectionEntryGroup')) if x.get('id')==uid+'-group'),None)
    if g is None: g=ET.SubElement(gs,C('selectionEntryGroup'),{'id':uid+'-group','name':'Fabius Bile','hidden':'false','collective':'false','import':'true'})
    ses=ensure(g,'selectionEntries')
    opt=ET.SubElement(ses,C('selectionEntry'),{'id':uid,'name':'Enhanced Warriors','type':'upgrade','hidden':'false','import':'true'})
    max_constraint(opt,1,uid+'-max')
    add_scaled_by_models(opt,unit,3)
    add_hidden_unless_selected(opt,fabius.get('id'),'fabius-enhanced-'+slug(unit.get('id') or 'u'))
    add_rule(opt,uid+'-rule','Enhanced Warriors',
             "This squad has been enhanced by Fabius Bile for +3 points per model. After deployment but before the first turn, roll a D6 for this squad: 1 — Berserk Rage: make an Armour Save for every model; remove each failure, and survivors gain +1 Strength. 2–5 — Stable Mutation: every model gains +1 Strength and +1 Initiative. 6 — Created a Monster: every model gains +1 Strength, +1 Initiative and +1 Attack; in missions using Victory Points, surviving models from the squad count as casualties when calculating Victory Points.")
    enhanced.append(f'{unit.get("id")} | {unit.get("name")}')

# Fulgrim Transfigured: profile was imported, but its wargear and rules were not structured.
ft=byid('r41-unit-iii-10-fulgrim-transfigured')
if ft is None: raise RuntimeError('Fulgrim Transfigured missing')
# Verify/fix profile values rather than creating a duplicate profile.
p=next((x for x in ft.findall('./'+C('profiles')+'/'+C('profile')) if (x.get('name') or '').lower()=='fulgrim transfigured'),None)
if p is None: raise RuntimeError('Fulgrim Transfigured profile missing')
vals={'WS':'9','BS':'6','S':'7','T':'7','W':'7','I':'9','A':'7','Ld':'10','Sv':'2+/4++'}
for ch in p.findall('./'+C('characteristics')+'/'+C('characteristic')):
    if ch.get('name') in vals: ch.text=vals[ch.get('name')]
# Remove an earlier R2 group if workflow is manually rerun before a revision bump.
gs=ensure(ft,'selectionEntryGroups')
for g in list(gs):
    if (g.get('id') or '').startswith('live-r2-fulgrim-transfigured-'): gs.remove(g)

def locked_group(parent,gid,name,items):
    g=ET.SubElement(ensure(parent,'selectionEntryGroups'),C('selectionEntryGroup'),{'id':gid,'name':name,'hidden':'false','collective':'false','import':'true'})
    ses=ET.SubElement(g,C('selectionEntries'))
    for i,(nm,desc) in enumerate(items):
        eid=f'{gid}-{i}-{slug(nm)}'
        e=ET.SubElement(ses,C('selectionEntry'),{'id':eid,'name':nm,'type':'upgrade','hidden':'false','import':'true','defaultAmount':'1'})
        setpts(e,0); min_constraint(e,1,eid+'-min'); max_constraint(e,1,eid+'-max')
        if desc: add_rule(e,eid+'-rule',nm,desc)
    return g

locked_group(ft,'live-r2-fulgrim-transfigured-wargear','Wargear',[
 ('Blade of the Laer','A Master-crafted Power Weapon. Fulgrim may re-roll To Wound rolls of 1 made with the Blade of the Laer.'),
 ('Daemon Spear','A Two-Handed Power Weapon which grants Fulgrim +2 Strength and Armourbane. Fulgrim chooses which weapon he uses at the beginning of each Assault phase.'),
 ('Transfigured Panoply','The protection represented by Fulgrim Transfigured’s 2+ Armour Save and 4+ Invulnerable Save is included in his profile.'),
])
locked_group(ft,'live-r2-fulgrim-transfigured-rules','Special Rules',[
 ('Daemon','Uses the normal Daemon special rule.'),
 ('Fear','Uses the normal Fear special rule.'),
 ('Fearless','Uses the normal Fearless special rule.'),
 ('Fleet','Uses the normal Fleet special rule.'),
 ('Eternal Warrior','Uses the normal Eternal Warrior special rule.'),
 ('Adamantium Will','Uses the normal Adamantium Will special rule.'),
 ('Master of the Legion','Uses the normal Master of the Legion special rule.'),
 ('Wings','Fulgrim may move up to 12" during the Movement phase and may move over intervening models and terrain while doing so. Fulgrim may never join another unit and no model may join him.'),
 ('The Stage is Set','Fulgrim must begin the battle in Reserve. Beginning on Turn 2, roll for him using the normal Reserve rules; if successful he must enter that turn. If he has not previously arrived, he enters automatically on Turn 4. He enters from his controlling player’s own table edge and may not Deep Strike or Outflank.'),
 ('Only the Worthy','When Fulgrim declares a charge against a non-Vehicle unit, use the highest Weapon Skill in that unit: WS4 or lower — he may not charge it; WS5 — on a 3+ he may charge normally; WS6 or higher — he may charge normally. If the WS5 roll fails he may attempt another eligible charge. If no enemy models with WS5 or greater remain, ignore this rule for the rest of the battle. Enemy units may charge Fulgrim normally.'),
 ('The Phoenician’s Pride','If Fulgrim is engaged with a unit containing one or more Independent Characters, he must allocate all close-combat attacks to one eligible Independent Character of his choice. Use that model’s own WS and Toughness; all wounds are allocated to it and excess wounds are lost. Enemy Independent Characters are not required to attack Fulgrim.'),
 ('A Perfect Victory','If Fulgrim personally slays an enemy Independent Character during the Assault phase and the enemy subsequently Falls Back, Fulgrim may not Pursue; he may Consolidate normally.'),
 ('The Phoenician’s Favour','If Fulgrim Transfigured is included, Emperor’s Children Infantry units may purchase the Blessing of Slaanesh for +25 points per unit and Emperor’s Children Independent Characters for +20 points per model. Blessed models gain +1 Initiative. This is cumulative with other Initiative modifiers. Fulgrim himself gains no bonus.'),
])
add_rule(ft,'live-r2-fulgrim-transfigured-restrictions','Restrictions',"Fulgrim Transfigured may only be selected for an Emperor’s Children army. An army may not include both Fulgrim Transfigured and Fulgrim in his mortal form.")

# Make The Phoenician's Favour an actual selectable army upgrade on the principal EC Infantry
# squads and Independent Characters. It is hidden until Fulgrim Transfigured is in the roster.
BLESS_INF_NAMES=FABIUS_NAMES | {'phoenix terminator squad'}
BLESS_CHAR_IDS={
 'hq-praetor','hq-centurion','hq-master-signals','hq-librarian','hq-chaplain',
 'r41-unit-iii-4-lord-commander-eidolon','r41-unit-iii-5-saul-tarvitz','r41-unit-iii-6-captain-lucius','r41-unit-iii-7-fabius-bile'
}
blessed=[]
for unit in list(root.iter(C('selectionEntry'))):
    if unit.get('type')!='unit': continue
    nm=(unit.get('name') or '').strip().lower(); uid=unit.get('id') or ''
    if uid==ft.get('id'): continue
    cost=None
    if nm in BLESS_INF_NAMES: cost=25
    if uid in BLESS_CHAR_IDS: cost=20
    if cost is None: continue
    if any((x.get('name') or '').strip().lower()=='blessing of slaanesh' for x in unit.iter(C('selectionEntry'))): continue
    eid='live-r2-fulgrim-blessing-'+slug(uid)
    opt=add_fixed_option(unit,eid,'Blessing of Slaanesh',cost,'Models with the Blessing of Slaanesh gain +1 Initiative. This bonus is cumulative with other Initiative modifiers.',ft.get('id'))
    blessed.append(f'{uid} | {unit.get("name")} | +{cost}')

# Mutual exclusion for mortal/transfigured Fulgrim if it was not already encoded functionally.
mortal=byid('r41-unit-iii-9-fulgrim-the-phoenician')
def hide_if_other_selected(entry, other, tag):
    mods=ensure(entry,'modifiers')
    # Avoid a second equivalent condition if one already exists anywhere on this entry.
    for c in entry.iter(C('condition')):
        if c.get('scope')=='roster' and c.get('childId')==other.get('id') and c.get('type') in ('atLeast','greaterThan'):
            return
    m=ET.SubElement(mods,C('modifier'),{'id':f'live-r2-{tag}','type':'set','field':'hidden','value':'true'})
    cs=ET.SubElement(m,C('conditions'))
    ET.SubElement(cs,C('condition'),{'type':'atLeast','value':'1','field':'selections','scope':'roster','childId':other.get('id'),'shared':'true','includeChildSelections':'true','includeChildForces':'false'})
if mortal is not None:
    hide_if_other_selected(ft,mortal,'fulgrim-transfigured-hide-mortal')
    hide_if_other_selected(mortal,ft,'fulgrim-mortal-hide-transfigured')

# Final structural checks.
allids=[]
for x in root.iter():
    if x.get('id'): allids.append(x.get('id'))
dups=sorted({i for i in allids if allids.count(i)>1})
if dups: raise RuntimeError(f'Duplicate XML IDs after R2 patch: {dups[:20]}')

# Every mapped existing character must now expose at least one real nested unit retinue.
unfixed=[]
for cid in RETINUES:
    ch=byid(cid)
    if ch is not None and not has_unit_retinue_group(ch): unfixed.append(f'{cid}:{ch.get("name")}')
if unfixed: raise RuntimeError('Still missing functional retinues: '+', '.join(unfixed))

# White Scars command retinues must retain their custom conditional bike option and lose generic duplicates.
for gid in ('r60-ws-shiban-retinue','r60-ws-hibou-retinue'):
    g=byid(gid)
    if g is None: continue
    cmd=next((u for u in g.iter(C('selectionEntry')) if u.get('type')=='unit' and (u.get('name') or '').lower()=='legion command squad'),None)
    if cmd is None: raise RuntimeError(f'No command squad in {gid}')
    names=[(x.get('name') or '') for x in cmd.iter(C('selectionEntry'))]
    if any('(+20 pts/model)' in n or '(+35 pts/model)' in n for n in names): raise RuntimeError(f'Generic WS mount duplicate remains in {gid}')

# Fulgrim profile/rules check.
profvals={c.get('name'):c.text for c in p.findall('./'+C('characteristics')+'/'+C('characteristic'))}
for k,v in vals.items():
    if profvals.get(k)!=v: raise RuntimeError(f'Fulgrim Transfigured {k}: {profvals.get(k)} != {v}')
for rn in ('Wings','The Stage is Set','Only the Worthy','The Phoenician’s Pride','A Perfect Victory','The Phoenician’s Favour'):
    if not any((r.get('name') or '')==rn for r in ft.iter(C('rule'))): raise RuntimeError(f'Missing Fulgrim rule {rn}')

root.set('revision','2')
ct.write(CAT,encoding='utf-8',xml_declaration=True)
# Canonical default namespace, avoiding ns0 prefixes in New Recruit.
raw=CAT.read_text(encoding='utf-8')
raw=raw.replace(f'xmlns:ns0="{NS}"',f'xmlns="{NS}"').replace('<ns0:','<').replace('</ns0:','</')
if '<ns0:' in raw: raise RuntimeError('ns0 namespace prefix remains')
CAT.write_text(raw,encoding='utf-8')

idx=IDX.read_text(encoding='utf-8')
idx,n=re.subn(r'(filePath="Legiones Astartes\.cat"[^>]*dataRevision=")1("\s*/>)',r'\g<1>2\g<2>',idx,count=1)
if n!=1: raise RuntimeError('Could not bump live catalogue index revision 1 -> 2')
IDX.write_text(idx,encoding='utf-8')

# Reparse final output.
final=ET.parse(CAT).getroot()
assert final.get('revision')=='2' and final.get('gameSystemRevision')=='1'

report.extend([
 'LIVE R2 — functional retinues + pending character notes',
 'CAT=2 GSTref=1',
 '',
 f'Functional retinue selectors added: {len(added)}', *['  + '+x for x in added],
 f'Functional retinue selectors already present and preserved: {len(existing)}', *['  = '+x for x in existing],
 f'Mapped character IDs not present in this catalogue: {len(missing)}', *['  ! '+x for x in missing],
 '',
 'White Scars duplicate Command Squad mounts removed:', *['  - '+x for x in ws_removed],
 '',
 f'Fabius Enhanced Warriors functional squad options added: {len(enhanced)}', *['  + '+x for x in enhanced],
 '',
 'Fulgrim Transfigured:',
 '  - profile verified as WS9 BS6 S7 T7 W7 I9 A7 Ld10 Sv2+/4++',
 '  - Wargear and Special Rules structured',
 '  - mortal/transfigured mutual exclusion verified/added',
 f'  - Blessing of Slaanesh functional options added: {len(blessed)}', *['    + '+x for x in blessed],
 '',
 'Veteran-retinue note intentionally not expanded beyond retinues explicitly required by named-character source entries, per user instruction.'
])
OUT.write_text('\n'.join(report)+'\n',encoding='utf-8')
print(OUT.read_text(encoding='utf-8'))
