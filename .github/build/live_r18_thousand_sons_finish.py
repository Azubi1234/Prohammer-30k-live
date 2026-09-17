from pathlib import Path
from copy import deepcopy
import importlib.util
import os
import re
import xml.etree.ElementTree as ET

# Always import the already-passing R18 core in dry-run mode so this file builds on
# exactly the same in-memory tree without touching the live catalogue first.
os.environ['TS_APPLY'] = '0'
spec = importlib.util.spec_from_file_location('r18core', '.github/build/live_r18_thousand_sons_core.py')
core = importlib.util.module_from_spec(spec)
spec.loader.exec_module(core)

root = core.root
groot = core.groot
C = core.C
G = core.G
CAT = core.CAT
GST = core.GST
IDX = core.IDX
APPLY = os.environ.get('TS_FINISH_APPLY', '0') == '1'
OUT = Path('inspection-r18-thousand-sons-finish-dry-run.txt')

findid = core.findid
ensure = core.ensure
add_constraint = core.add_constraint
remove_constraints = core.remove_constraints
add_modifier = core.add_modifier
cond = core.cond
prefix_clone = core.prefix_clone
strip_categories = core.strip_categories
set_group_minmax = core.set_group_minmax
setpts = core.setpts
add_power_group = core.add_power_group

log = []


def direct_groups(e):
    c = e.find(C('selectionEntryGroups'))
    return list(c) if c is not None else []


def direct_entries(e):
    c = e.find(C('selectionEntries'))
    return list(c) if c is not None else []


def add_rule(host, rid, name, text):
    rs = ensure(host, 'rules')
    for r in list(rs):
        if r.get('id') == rid:
            rs.remove(r)
    r = ET.SubElement(rs, C('rule'), {'id': rid, 'name': name, 'hidden': 'false'})
    d = ET.SubElement(r, C('description'))
    d.text = text
    return r


def add_link(host, lid, name, target, cost=None, hidden='false'):
    els = ensure(host, 'entryLinks')
    for x in list(els):
        if x.get('id') == lid:
            els.remove(x)
    e = ET.SubElement(els, C('entryLink'), {
        'id': lid, 'name': name, 'hidden': hidden, 'collective': 'false',
        'import': 'true', 'targetId': target, 'type': 'selectionEntry'
    })
    add_constraint(e, lid + '-max', 'max', 1, 'parent')
    if cost is not None:
        cs = ensure(e, 'costs')
        ET.SubElement(cs, C('cost'), {'name': 'Points', 'typeId': 'pts', 'value': str(cost)})
    return e


def gate_xv(e, prefix):
    add_modifier(e, prefix + '-xv-hide', 'set', 'hidden', 'true',
                 conditions=[cond('lessThan', 1, 'legion-xv', 'roster')])


def group_gate_min1(g, prefix, conditions):
    # Reset to optional at baseline; turn mandatory only when the gate is active.
    cs = ensure(g, 'constraints')
    minc = next((x for x in cs if x.get('type') == 'min'), None)
    maxc = next((x for x in cs if x.get('type') == 'max'), None)
    if minc is None:
        minc = add_constraint(g, prefix + '-min', 'min', 0, 'parent')
    else:
        minc.set('value', '0')
    if maxc is None:
        maxc = add_constraint(g, prefix + '-max', 'max', 1, 'parent')
    else:
        maxc.set('value', '1')
    add_modifier(g, prefix + '-hide', 'set', 'hidden', 'true',
                 condition_groups=[('or', [[].__class__ and []])]) if False else None
    # Separate hide modifiers are simpler and more reliable than nested NOT logic.
    add_modifier(g, prefix + '-hide-no-xv', 'set', 'hidden', 'true',
                 conditions=[cond('lessThan', 1, 'legion-xv', 'roster')])
    if conditions:
        # conditions are requirements which must all be true. Hide when any is false.
        for i, req in enumerate(conditions):
            inv = dict(req)
            inv['type'] = 'lessThan' if req['type'] in ('atLeast', 'greaterThan') else 'atLeast'
            inv['value'] = req['value']
            add_modifier(g, f'{prefix}-hide-req-{i}', 'set', 'hidden', 'true', conditions=[inv])
        allconds = [cond('atLeast', 1, 'legion-xv', 'roster')] + conditions
    else:
        allconds = [cond('atLeast', 1, 'legion-xv', 'roster')]
    add_modifier(g, prefix + '-min-on', 'set', minc.get('id'), '1',
                 condition_groups=[('and', allconds)])
    return g


def clone_psychic_group(host, gid, name, source='r61-librarian-power1', requirements=None, allowed=None):
    src = findid(root, source)
    if src is None:
        raise RuntimeError('Missing psychic source group ' + source)
    gs = ensure(host, 'selectionEntryGroups')
    for x in list(gs):
        if x.get('id') == gid:
            gs.remove(x)
    cl = prefix_clone(src, gid + '-clone-')
    cl.set('id', gid)
    cl.set('name', name)
    cl.set('hidden', 'false')
    strip_categories(cl)
    oldmods = cl.find(C('modifiers'))
    if oldmods is not None:
        cl.remove(oldmods)
    ses = cl.find(C('selectionEntries'))
    if allowed is not None:
        al = {x.lower() for x in allowed}
        for x in list(ses):
            disc = (x.get('name') or '').split('—', 1)[0].split('-', 1)[0].strip().lower()
            if disc not in al:
                ses.remove(x)
    group_gate_min1(cl, gid, requirements or [])
    gs.append(cl)
    return cl


def hide_group_under_xv(gid):
    g = findid(root, gid)
    if g is None:
        return False
    cs = g.find(C('constraints'))
    if cs is not None:
        for x in cs:
            if x.get('type') == 'min':
                add_modifier(g, 'r18-ts-hide-' + gid + '-min', 'set', x.get('id'), 0,
                             conditions=[cond('atLeast', 1, 'legion-xv', 'roster')])
    add_modifier(g, 'r18-ts-hide-' + gid, 'set', 'hidden', 'true',
                 conditions=[cond('atLeast', 1, 'legion-xv', 'roster')])
    return True


def source_wargear_text(host):
    for r in list(host.find(C('rules')) or []):
        if (r.get('name') or '') == 'Source Entry':
            d = r.find(C('description'))
            t = (d.text or '') if d is not None else ''
            m = re.search(r'Wargear:\s*(.*?)(?:Special Rules:|OPTIONS|Options)', t, flags=re.S)
            return m.group(1) if m else ''
    return ''


def named_armoury_group(host, prefix, guard_id):
    gs = ensure(host, 'selectionEntryGroups')
    gid = prefix + '-armoury'
    for x in list(gs):
        if x.get('id') == gid:
            gs.remove(x)
    g = ET.SubElement(gs, C('selectionEntryGroup'), {'id': gid, 'name': 'Thousand Sons Armoury', 'hidden': 'false'})
    wg = source_wargear_text(host).lower()
    options = [
        ('arcane-litanies', 'Arcane Litanies', 'r45-ts-arcane-litanies'),
        ('asphyx-shells', 'Asphyx Shells', 'r45-ts-asphyx-ic'),
        ('aether-disc', 'Prosperine Æther-Disc', 'r47-ts-prosperine-aether-disc'),
    ]
    for suffix, name, target in options:
        if name.lower() in wg:
            continue
        add_link(g, prefix + '-' + suffix, name, target)
    if 'teleportation transponders' not in wg:
        tr = add_link(g, prefix + '-guard-trans', 'Teleportation Transponders — Guard of the Crimson King', 'r45-ts-trans-ic')
        add_modifier(tr, prefix + '-guard-trans-hide', 'set', 'hidden', 'true',
                     conditions=[cond('lessThan', 1, guard_id, 'roster')])
    return g


def add_category_link(host, lid, name, target, primary='false', hidden='false'):
    cls = ensure(host, 'categoryLinks')
    for x in list(cls):
        if x.get('id') == lid:
            cls.remove(x)
    return ET.SubElement(cls, C('categoryLink'), {
        'id': lid, 'name': name, 'hidden': hidden, 'targetId': target, 'primary': primary
    })


def add_ranged_profile(host, pid, name, rng, s, ap, typ):
    ps = ensure(host, 'profiles')
    for p in list(ps):
        if p.get('id') == pid:
            ps.remove(p)
    p = ET.SubElement(ps, C('profile'), {
        'id': pid, 'name': name, 'hidden': 'false', 'typeId': 'prof-ranged', 'typeName': 'Ranged Weapon'
    })
    cs = ET.SubElement(p, C('characteristics'))
    for cid, cn, val in [('ranged-range','Range',rng),('ranged-s','S',s),('ranged-ap','AP',ap),('ranged-type','Type',typ)]:
        x = ET.SubElement(cs, C('characteristic'), {'name': cn, 'typeId': cid})
        x.text = val
    return p


# -----------------------------------------------------------------------------
# 1. GENERIC THOUSAND SONS HQ PSYCHICS
# -----------------------------------------------------------------------------
praetor = findid(root, 'hq-praetor')
centurion = findid(root, 'hq-centurion')
if praetor is None or centurion is None:
    raise RuntimeError('Missing generic HQ entries')

clone_psychic_group(praetor, 'r18-ts-praetor-power1', 'Thousand Sons Psychic Power 1 — Mastery Level 2')
clone_psychic_group(praetor, 'r18-ts-praetor-power2', 'Thousand Sons Psychic Power 2 — Mastery Level 2', source='r61-librarian-power2')
clone_psychic_group(centurion, 'r18-ts-centurion-power1', 'Thousand Sons Psychic Power — Mastery Level 1')
clone_psychic_group(
    centurion, 'r18-ts-centurion-power2', 'Thousand Sons Psychic Power 2 — Epistolary Mastery Level 2',
    source='r61-librarian-power2', requirements=[cond('atLeast', 1, 'hq-consul-librarian-epistolary', 'root-entry')]
)
for gid in ('r29-lib-discipline-group', 'r29-lib-power-group', 'r61-librarian-power1', 'r61-librarian-power2'):
    hide_group_under_xv(gid)

add_rule(praetor, 'r18-ts-praetor-psyker-rule', 'Sorcerers of Prospero — Praetor',
         'In a Thousand Sons Detachment, a Legion Praetor is a Psyker (Mastery Level 2) and selects two powers from Biomancy, Divination, Pyromancy, Telekinesis or Telepathy. Activating a Force Weapon counts as the use of a psychic power, and the same power may not be used more than once in the same player turn.').set('hidden','true')
add_rule(centurion, 'r18-ts-centurion-psyker-rule', 'Sorcerers of Prospero — Independent Character',
         'In a Thousand Sons Detachment, a Legion Centurion and its Consul variants are Psykers (Mastery Level 1) unless another rule grants a higher Mastery Level. A Librarian Consul follows the normal Librarian upgrade rules; an Epistolary is Mastery Level 2.').set('hidden','true')
log.append('Generic Praetor/Centurion psychic selectors added; normal Librarian selector duplication is suppressed for XV rosters')


# -----------------------------------------------------------------------------
# 2. PROSPERINE ARMOURY DEPENDENCIES
# -----------------------------------------------------------------------------
shared_xv = [
    'r45-ts-force-weapon','r45-ts-arcane-litanies','r45-ts-asphyx-ic','r45-ts-asphyx-unit',
    'r45-ts-trans-ic','r45-ts-trans-unit','r45-ts-aether-fire','r47-ts-prosperine-aether-disc',
    'r45-ts-brotherhood','r45-ts-brotherhood-fellowship','r45-ts-tactical-brotherhood'
]
for sid in shared_xv:
    s = findid(root, sid)
    if s is not None:
        gate_xv(s, 'r18-' + sid)

fw = findid(root, 'r45-ts-force-weapon')
if fw is not None:
    add_modifier(fw, 'r18-ts-force-needs-powerweapon', 'set', 'hidden', 'true',
                 conditions=[cond('lessThan', 1, 'gear-power-weapon', 'root-entry')])

# Prosperine Aether-Disc cannot coexist with Jump Pack, Bike, Jetbike or Terminator armour.
disc = findid(root, 'r47-ts-prosperine-aether-disc')
if disc is None:
    raise RuntimeError('Missing Prosperine Aether-Disc shared entry')
incompat = [
    'hq-praetor-jump','hq-praetor-bike','r37-praetor-jetbike','hq-praetor-term','hq-praetor-tart','hq-praetor-cat',
    'hq-centurion-jump','hq-centurion-bike','r37-centurion-jetbike','hq-centurion-term','hq-centurion-tart','hq-centurion-cat',
    'hq-consul-vigilator-scoutarmour'
]
for i, child in enumerate(incompat):
    if findid(root, child) is not None:
        add_modifier(disc, f'r18-ts-disc-incompat-{i}', 'set', 'hidden', 'true',
                     conditions=[cond('atLeast', 1, child, 'root-entry')])

# Generic IC Transponders: Terminator armour normally, any armour under Guard of the Crimson King.
guard = 'r25-rite-xv-1-the-guard-of-the-crimson-king'
for host, terms in [
    (praetor, ['hq-praetor-term','hq-praetor-tart','hq-praetor-cat']),
    (centurion, ['hq-centurion-term','hq-centurion-tart','hq-centurion-cat'])
]:
    for link in host.iter(C('entryLink')):
        if link.get('targetId') != 'r45-ts-trans-ic':
            continue
        add_modifier(link, 'r18-' + link.get('id') + '-hide-no-xv', 'set', 'hidden', 'true',
                     conditions=[cond('lessThan', 1, 'legion-xv', 'roster')])
        reqs = [cond('lessThan', 1, guard, 'roster')] + [cond('lessThan', 1, t, 'root-entry') for t in terms]
        add_modifier(link, 'r18-' + link.get('id') + '-hide-armour', 'set', 'hidden', 'true',
                     condition_groups=[('and', reqs)])

# Guard makes all Terminator-unit Transponders free.
trans_unit = findid(root, 'r45-ts-trans-unit')
if trans_unit is not None:
    add_modifier(trans_unit, 'r18-ts-guard-free-trans-unit', 'set', 'pts', 0,
                 conditions=[cond('atLeast', 1, guard, 'roster')])
    rr = next((r for r in list(trans_unit.find(C('rules')) or []) if r.get('name') == 'Teleportation Transponders'), None)
    if rr is not None:
        d = rr.find(C('description'))
        if d is not None:
            d.text = 'Thousand Sons unit composed entirely of models wearing Terminator Armour. Normally +15 points per unit; free while using The Guard of the Crimson King. Grants Deep Strike even if the mission would not normally permit it.'

# Every Terminator Command Squad is also eligible for the XV Transponder option.
termcmd_count = 0
for u in root.iter(C('selectionEntry')):
    if u.get('type') == 'unit' and (u.get('name') or '') == 'Legion Terminator Command Squad':
        if not any(x.get('targetId') == 'r45-ts-trans-unit' for x in u.iter(C('entryLink'))):
            lid = 'r18-ts-termcmd-trans-' + re.sub(r'[^A-Za-z0-9_-]', '-', u.get('id'))
            lnk = add_link(u, lid, 'Teleportation Transponders', 'r45-ts-trans-unit')
            add_modifier(lnk, lid + '-hide-no-xv', 'set', 'hidden', 'true',
                         conditions=[cond('lessThan', 1, 'legion-xv', 'roster')])
            termcmd_count += 1

# Named XV Independent Characters gain their general Legion Armoury options.
named_ids = [
    'r41-unit-xv-6-ahzek-ahriman','r41-unit-xv-7-phosis-t-kar','r41-unit-xv-8-magistus-amon-the-hidden',
    'r41-unit-xv-9-hathor-maat','r41-unit-xv-10-sanakht'
]
for nid in named_ids:
    h = findid(root, nid)
    if h is None:
        raise RuntimeError('Missing named Thousand Sons character ' + nid)
    named_armoury_group(h, 'r18-' + nid, guard)

# Osiron Plasma Cannon -> optional free Aether-fire Cannon upgrade.
osiron = findid(root, 'r41-unit-xv-4-contemptor-osiron-dreadnought')
plasma = findid(root, 'r41-unit-xv-4-contemptor-osiron-dreadnought-opt-7-plasma-cannon')
if osiron is None or plasma is None:
    raise RuntimeError('Missing Osiron / Plasma Cannon option')
osg = next((g for g in direct_groups(osiron) if (g.get('name') or '') == 'Options'), None)
if osg is None:
    raise RuntimeError('Missing Osiron options group')
aef = add_link(osg, 'r18-ts-osiron-aether-fire', 'Æther-fire Cannon upgrade', 'r45-ts-aether-fire')
add_modifier(aef, 'r18-ts-osiron-aether-hide', 'set', 'hidden', 'true',
             conditions=[cond('lessThan', 1, plasma.get('id'), 'root-entry')])

# Shared Aether-fire upgrade requires at least one selected Plasma Cannon in its root entry.
aef_shared = findid(root, 'r45-ts-aether-fire')
plasma_ids = set(['gear-plasma-cannon', plasma.get('id')])
for x in root.iter():
    if (x.get('name') or '').strip().lower() == 'plasma cannon':
        if x.get('id'): plasma_ids.add(x.get('id'))
        if x.get('targetId'): plasma_ids.add(x.get('targetId'))
plasma_ids = [x for x in plasma_ids if x]
add_modifier(aef_shared, 'r18-ts-aether-needs-plasma', 'set', 'hidden', 'true',
             condition_groups=[('and', [cond('lessThan', 1, x, 'root-entry') for x in plasma_ids])])

log.append(f'Prosperine Armoury gated and dependency-cleaned; added TS armoury to 5 named ICs and Transponders to {termcmd_count} Terminator Command copies')


# -----------------------------------------------------------------------------
# 3. RITE OF WAR FUNCTIONALITY
# -----------------------------------------------------------------------------
axis = 'r25-rite-xv-0-the-axis-of-dissolution'
# Axis: every normal Troops squad must be at maximum size.
axis_units = ['tactical-unit','assault-unit','breacher-unit','recon-unit']
axis_forced = []
for uid in axis_units:
    u = findid(root, uid)
    if u is None:
        continue
    for m in direct_entries(u):
        if m.get('type') != 'model':
            continue
        cs = m.find(C('constraints'))
        if cs is None:
            continue
        minc = next((x for x in cs if x.get('type') == 'min' and x.get('field') == 'selections'), None)
        maxc = next((x for x in cs if x.get('type') == 'max' and x.get('field') == 'selections'), None)
        if minc is None or maxc is None:
            continue
        try:
            if float(maxc.get('value')) <= float(minc.get('value')):
                continue
        except Exception:
            continue
        add_modifier(m, f'r18-ts-axis-max-{m.get("id")}', 'set', minc.get('id'), maxc.get('value'),
                     conditions=[cond('atLeast', 1, axis, 'roster')])
        axis_forced.append(f'{uid}:{m.get("name")}={maxc.get("value")}')

# Guard: free Sekhmet Transponders.
sek = findid(root, 'r41-unit-xv-0-sekhmet-terminator-cabal')
sek_trans = findid(root, 'r41-unit-xv-0-sekhmet-terminator-cabal-opt-7-teleportation-transponders')
if sek is None or sek_trans is None:
    raise RuntimeError('Missing Sekhmet Transponder option')
add_modifier(sek_trans, 'r18-ts-guard-sekhmet-free-trans', 'set', 'pts', 0,
             conditions=[cond('atLeast', 1, guard, 'roster')])

# Guard: Praetor may purchase ML3 for +25. Warlord status cannot presently be represented
# safely by the catalogue, so the selector is explicitly labelled with the source requirement.
pgs = ensure(praetor, 'selectionEntryGroups')
mlgid = 'r18-ts-guard-praetor-ml3-group'
for x in list(pgs):
    if x.get('id') == mlgid:
        pgs.remove(x)
mlg = ET.SubElement(pgs, C('selectionEntryGroup'), {'id': mlgid, 'name': 'Guard of the Crimson King', 'hidden': 'false'})
ml3 = ET.SubElement(ensure(mlg, 'selectionEntries'), C('selectionEntry'), {
    'id':'r18-ts-guard-praetor-ml3','name':'Mastery Level 3 — Warlord only','type':'upgrade','hidden':'false','import':'true'
})
add_constraint(ml3, 'r18-ts-guard-praetor-ml3-max', 'max', 1, 'parent')
setpts(ml3, 25)
add_modifier(mlg, 'r18-ts-guard-praetor-ml3-hide', 'set', 'hidden', 'true',
             conditions=[cond('lessThan', 1, guard, 'roster')])
add_rule(ml3, 'r18-ts-guard-praetor-ml3-rule', 'Mastery Level 3 — Guard Warlord',
         'The Guard of the Crimson King permits a Thousand Sons Praetor selected as the army Warlord to upgrade from Mastery Level 2 to Mastery Level 3 for +25 points.')
clone_psychic_group(
    praetor, 'r18-ts-praetor-power3', 'Thousand Sons Psychic Power 3 — Guard Warlord Mastery Level 3',
    requirements=[cond('atLeast', 1, 'r18-ts-guard-praetor-ml3', 'root-entry')]
)

# Guard: Magnus becomes HQ instead of Lord of War.
magnus = findid(root, 'r41-unit-xv-11-xv-magnus-the-red-the-crimson-king')
if magnus is None:
    raise RuntimeError('Missing Magnus')
low = next((x for x in list(magnus.find(C('categoryLinks')) or []) if x.get('targetId') == 'cat-low'), None)
if low is None:
    raise RuntimeError('Magnus lacks Lords of War category')
add_modifier(low, 'r18-ts-guard-magnus-hide-low', 'set', 'hidden', 'true',
             conditions=[cond('atLeast', 1, guard, 'roster')])
hqcat = add_category_link(magnus, 'r18-ts-guard-magnus-hq', 'HQ — Guard of the Crimson King', 'cat-hq', 'false', 'true')
add_modifier(hqcat, 'r18-ts-guard-magnus-show-hq', 'set', 'hidden', 'false',
             conditions=[cond('atLeast', 1, guard, 'roster')])

log.append('Rites: Axis normal Troops forced to maximum size; Guard free Terminator Transponders, Praetor ML3 selector and Magnus HQ relocation implemented')


# -----------------------------------------------------------------------------
# 4. MAGNUS — FULL PSYCHIC INTERFACE + RETINUE
# -----------------------------------------------------------------------------
# Standard Primarch points gate: 2,000 normally, 1,500 with Primarch's Chosen.
remove_constraints(magnus, lambda x: x.get('id') == 'r18-ts-magnus-min-points')
minpts = add_constraint(magnus, 'r18-ts-magnus-min-points', 'min', 2000, 'roster', field='limit::points')
add_modifier(magnus, 'r18-ts-magnus-min-primarchs-chosen', 'set', minpts.get('id'), 1500,
             conditions=[cond('atLeast', 1, 'da22-rite-primarchs-chosen', 'roster')])

# Hide the giant source wall but retain it in the data for auditability.
for r in list(magnus.find(C('rules')) or []):
    if (r.get('name') or '') == 'Source Entry':
        r.set('hidden', 'true')

add_rule(magnus, 'r18-ts-magnus-armour', 'Horned Raiment',
         'Counts as Primarch Armour. When an enemy unit shoots Magnus or a unit he has joined, To Hit rolls suffer -1; Blast weapons suffer -2 instead. These modifiers do not apply in close combat.')
add_rule(magnus, 'r18-ts-magnus-blade', 'Blade of Ahn-Nunurta',
         'Master-crafted, Two-Handed Force Weapon. It follows the normal ProHammer Force Weapon rules.')
add_rule(magnus, 'r18-ts-magnus-litanies', 'Arcane Litanies',
         'Once per battle, when Magnus suffers a Wound from Perils of the Warp, he may ignore that Wound. The Psychic Test and psychic power are otherwise resolved normally.')
add_rule(magnus, 'r18-ts-magnus-psyker', 'Psyker — Mastery Level 4',
         'Magnus knows five psychic powers in total. Infernal Phoenix and Strands of Fate are always known and count toward the five; the remaining three are selected from Biomancy, Divination, Pyromancy, Telekinesis and Telepathy, using at least two different disciplines. Magnus counts as belonging to all five Prosperine Cults for army selection/friendly abilities but gains no Cult Arcana or Cult Mastery from them.')
add_rule(magnus, 'r18-ts-magnus-supremacy', 'Psychic Supremacy',
         'Magnus may never have more than two Blessings affecting himself at the same time. If a new Blessing would exceed this limit, one existing Blessing affecting him immediately ends. He may never have more than two psychic powers with ongoing effects simultaneously affecting himself and/or the opposing Primarch.')
add_rule(magnus, 'r18-ts-magnus-ether', 'Lord of the Ether',
         'Magnus may invoke up to four psychic powers during each player turn and may invoke multiple Witchfire powers in the same Shooting phase. He may not successfully invoke the same power more than once in the same player turn. Activating the Blade of Ahn-Nunurta as a Force Weapon does not count against this limit.')
add_rule(magnus, 'r18-ts-magnus-crimson', 'The Crimson King',
         'Magnus may re-roll one failed Psychic Test during each player turn; the second result must be accepted. He may attempt to Deny the Witch against a power if either the invoking Psyker or the target is within 24 inches of Magnus, using his own Mastery Level. Each power may still only be the subject of one Deny the Witch attempt.')
add_rule(magnus, 'r18-ts-magnus-warp', 'The Warp Bends to Magnus',
         'Magnus ignores Leadership penalties caused by Disturbance in the Warp. Psychic powers successfully invoked by Magnus are ignored when determining Disturbance in the Warp penalties for other friendly Psykers; powers invoked by other friendly Psykers still contribute normally.')
add_rule(magnus, 'r18-ts-magnus-strands', 'Strands of Fate',
         'Malediction. Choose one enemy non-Vehicle unit within 18 inches and line of sight. Until the beginning of Magnus\' next turn, the unit must pass a Leadership Test each time it attempts to Move, Shoot or declare a Charge. If failed, that action is lost and the unit may not attempt that type of action again during that phase. Test separately for each different action attempted.')
add_rule(magnus, 'r18-ts-magnus-duellist', 'Sorcerous Duellist',
         'While Magnus is fighting a Primarch Duel, at the beginning of each Assault phase he may invoke one Blessing targeting only himself or one Malediction targeting only the opposing Primarch. This counts toward his normal maximum of four powers for that player turn and follows all normal Psychic Test, Deny the Witch and Perils rules.')
add_ranged_profile(magnus, 'r18-ts-magnus-infernal-profile', 'Infernal Phoenix', '24"', '8', '1', 'Witchfire, Beam, Melta')
add_rule(magnus, 'r18-ts-magnus-infernal-rule', 'Infernal Phoenix',
         'Witchfire — Beam. Resolve using the normal rules for Beam psychic powers.')

# Discipline anchors. This enforces at least two different disciplines while allowing
# the third selected power to come from either of those or a third discipline.
disciplines = ['Biomancy','Divination','Pyromancy','Telekinesis','Telepathy']
mgs = ensure(magnus, 'selectionEntryGroups')
for gid in ('r18-ts-magnus-primary-disc','r18-ts-magnus-secondary-disc','r18-ts-magnus-power1','r18-ts-magnus-power2','r18-ts-magnus-power3'):
    for x in list(mgs):
        if x.get('id') == gid:
            mgs.remove(x)

def discipline_group(gid, name, other=None):
    g = ET.SubElement(mgs, C('selectionEntryGroup'), {'id':gid,'name':name,'hidden':'false'})
    add_constraint(g, gid+'-min', 'min', 1, 'parent')
    add_constraint(g, gid+'-max', 'max', 1, 'parent')
    ses = ET.SubElement(g, C('selectionEntries'))
    out = {}
    for d in disciplines:
        sid = gid + '-' + d.lower()
        s = ET.SubElement(ses, C('selectionEntry'), {'id':sid,'name':d,'type':'upgrade','hidden':'false','import':'true'})
        add_constraint(s, sid+'-max', 'max', 1, 'parent')
        if other:
            add_modifier(s, sid+'-distinct', 'set', 'hidden', 'true',
                         conditions=[cond('atLeast',1,other[d],'root-entry')])
        out[d] = sid
    return g, out

_, primary_ids = discipline_group('r18-ts-magnus-primary-disc','Primary Psychic Discipline')
_, secondary_ids = discipline_group('r18-ts-magnus-secondary-disc','Secondary Psychic Discipline — must differ', primary_ids)

p1 = clone_psychic_group(magnus, 'r18-ts-magnus-power1','Selected Psychic Power 1 — Primary Discipline')
p2 = clone_psychic_group(magnus, 'r18-ts-magnus-power2','Selected Psychic Power 2 — Secondary Discipline')
p3 = clone_psychic_group(magnus, 'r18-ts-magnus-power3','Selected Psychic Power 3 — Any Thousand Sons Discipline')
# These groups are always mandatory on Magnus; remove the generic XV gate inserted by clone_psychic_group.
for g in (p1,p2,p3):
    ms = g.find(C('modifiers'))
    if ms is not None:
        for m in list(ms):
            if 'hide-no-xv' in (m.get('id') or '') or 'min-on' in (m.get('id') or ''):
                ms.remove(m)
    cs = g.find(C('constraints'))
    for c in list(cs) if cs is not None else []:
        if c.get('type') == 'min': c.set('value','1')
        if c.get('type') == 'max': c.set('value','1')

# Gate P1/P2 entries to the chosen discipline.
def gate_power_entries(g, anchors, prefix):
    ses = g.find(C('selectionEntries'))
    for x in list(ses):
        disc = (x.get('name') or '').split('—',1)[0].split('-',1)[0].strip()
        if disc in anchors:
            add_modifier(x, prefix + '-' + x.get('id') + '-disc', 'set', 'hidden', 'true',
                         conditions=[cond('lessThan',1,anchors[disc],'root-entry')])

gate_power_entries(p1, primary_ids, 'r18-mag-p1')
gate_power_entries(p2, secondary_ids, 'r18-mag-p2')

# The same normal psychic power may not be selected twice across the three chosen slots.
def entries_by_name(g):
    ses = g.find(C('selectionEntries'))
    return {(x.get('name') or ''): x for x in list(ses)}

maps = [entries_by_name(p1), entries_by_name(p2), entries_by_name(p3)]
for i, mp in enumerate(maps):
    for name, x in mp.items():
        for j, other in enumerate(maps):
            if i == j or name not in other:
                continue
            add_modifier(x, f'r18-mag-no-dup-{i}-{j}-{re.sub(r"[^A-Za-z0-9]", "-", name)}', 'set', 'hidden', 'true',
                         conditions=[cond('atLeast',1,other[name].get('id'),'root-entry')])

# Magnus retinue: add Sekhmet as the third source-permitted option and enforce the 0-1
# Sekhmet limit across the normal slot and the retinue copy.
retg = next((g for g in direct_groups(magnus) if (g.get('name') or '').startswith('Retinue')), None)
if retg is None:
    raise RuntimeError('Magnus retinue group missing')
ret_ses = ensure(retg, 'selectionEntries')
sekclone = next((x for x in list(ret_ses) if 'SEKHMET TERMINATOR CABAL' in (x.get('name') or '')), None)
if sekclone is None:
    sekclone = prefix_clone(sek, 'r18-mag-ret-sek-')
    sekclone.set('id', 'r18-ts-magnus-retinue-sekhmet')
    sekclone.set('name', 'SEKHMET TERMINATOR CABAL')
    strip_categories(sekclone)
    # Nested retinue itself is choose-one inside Magnus.
    cs = sekclone.find(C('constraints'))
    if cs is not None:
        for c in list(cs): cs.remove(c)
    add_constraint(sekclone, 'r18-ts-magnus-retinue-sekhmet-max', 'max', 1, 'parent')
    ret_ses.append(sekclone)

# Hidden Sekhmet category maximum 1 across top-level and Magnus retinue.
cats = ensure(groot, 'categoryEntries', G)
if findid(groot, 'r18-ts-cat-sekhmet-limit') is None:
    ET.SubElement(cats, G('categoryEntry'), {'id':'r18-ts-cat-sekhmet-limit','name':'Thousand Sons Sekhmet 0-1','hidden':'true'})
for host, lid in [(sek,'r18-ts-sekhmet-root-limit'),(sekclone,'r18-ts-sekhmet-ret-limit')]:
    add_category_link(host, lid, 'Thousand Sons Sekhmet 0-1', 'r18-ts-cat-sekhmet-limit')
force = findid(groot, 'force-standard')
fcls = ensure(force, 'categoryLinks', G)
old = next((x for x in fcls if x.get('id') == 'r18-ts-sekhmet-limit'), None)
if old is not None: fcls.remove(old)
sl = ET.SubElement(fcls, G('categoryLink'), {'id':'r18-ts-sekhmet-limit','name':'Sekhmet 0-1','hidden':'true','targetId':'r18-ts-cat-sekhmet-limit'})
add_constraint(sl, 'r18-ts-sekhmet-limit-max', 'max', 1, 'parent', ns=G)

# The Crimson King's Guard upgrade on Honour Guard / Terminator Command retinues.
def add_crimson_guard(unit, prefix):
    gs = ensure(unit, 'selectionEntryGroups')
    gid = prefix + '-crimson-guard'
    for x in list(gs):
        if x.get('id') == gid: gs.remove(x)
    g = ET.SubElement(gs, C('selectionEntryGroup'), {'id':gid,'name':'The Crimson King\'s Guard','hidden':'false'})
    up = ET.SubElement(ensure(g,'selectionEntries'), C('selectionEntry'), {
        'id':gid+'-upgrade','name':'Brotherhood of Psykers (Mastery Level 1)','type':'upgrade','hidden':'false','import':'true'
    })
    add_constraint(up, gid+'-upgrade-max','max',1,'parent')
    setpts(up,25)
    add_rule(up, gid+'-upgrade-rule','The Crimson King\'s Guard',
             'Magnus\' Legion Honour Guard or Legion Terminator Command retinue may be upgraded to Brotherhood of Psykers (Mastery Level 1) for +25 points. It selects one Prosperine Cult and one psychic power from any normal Thousand Sons discipline.')
    # Cult selector cloned from Veteran Squad so all five Cult rules remain identical.
    csrc = findid(root,'r45-cult-veteran-unit')
    if csrc is None: raise RuntimeError('Missing reusable XV Cult group')
    cg = prefix_clone(csrc, gid+'-cult-clone-')
    cg.set('id',gid+'-cult'); cg.set('name','Prosperine Cult — Brotherhood')
    oldm = cg.find(C('modifiers'))
    if oldm is not None: cg.remove(oldm)
    minid,maxid = set_group_minmax(cg,0,1,gid+'-cult')
    add_modifier(cg,gid+'-cult-hide','set','hidden','true',conditions=[cond('lessThan',1,up.get('id'),'root-entry')])
    add_modifier(cg,gid+'-cult-min-on','set',minid,1,conditions=[cond('atLeast',1,up.get('id'),'root-entry')])
    gs.append(cg)
    add_power_group(unit,gid+'-power','Psychic Power — Crimson King\'s Guard',gate_ids=[up.get('id')])

for u in list(ret_ses):
    n = (u.get('name') or '')
    if n in ('Legion Honour Guard Squad','Legion Terminator Command Squad'):
        add_crimson_guard(u, 'r18-ts-mag-' + re.sub(r'[^A-Za-z0-9_-]', '-', u.get('id')))

log.append('Magnus rebuilt with fixed Infernal Phoenix/Strands, three selectable powers from at least two disciplines, 2,000/1,500 point gate, Sekhmet retinue and Crimson King\'s Guard upgrades')


# -----------------------------------------------------------------------------
# 5. VALIDATIONS + OUTPUT
# -----------------------------------------------------------------------------
# Core structural checks.
for gid in ('r18-ts-praetor-power1','r18-ts-praetor-power2','r18-ts-centurion-power1','r18-ts-magnus-power1','r18-ts-magnus-power2','r18-ts-magnus-power3'):
    if findid(root,gid) is None:
        raise RuntimeError('Missing generated group ' + gid)
retcheck = next((x for x in list(ret_ses) if 'SEKHMET TERMINATOR CABAL' in (x.get('name') or '')), None)
if retcheck is None:
    raise RuntimeError('Missing Magnus Sekhmet retinue')

# Ensure dry-run never writes live files unless explicitly applied.
lines = [
    'R18 THOUSAND SONS FINISH — ' + ('APPLY' if APPLY else 'DRY RUN ONLY'),
    f'Input live CAT revision: 17 | Proposed CAT revision: 18 | GST revision remains {groot.get("revision")}',
    f'LIVE FILES WRITTEN: {"YES" if APPLY else "NO"}',
    '', 'CHANGES:'
]
lines += ['  + ' + x for x in log]
lines += [
    '', 'INTENTIONALLY PRESERVED / NOT INVENTED:',
    '  - Guard of the Crimson King still contains the written Sekhmet contradiction: the unit is 0-1, yet the Rite says Sekhmet must fill the compulsory Troops selections. No fake exception was invented.',
    '  - Axis and Guard vehicle-to-Infantry/Legiones ratios are retained as rule text because the current catalogue does not expose a reliable cross-force unit-type counter.',
    '  - Allied Detachment / Fortification prohibitions remain rule text because the present GST does not expose those force/category choices safely enough to automate.',
    '  - Warlord-only requirements remain explicit selector/rule text because the catalogue currently has no single trustworthy Warlord marker to validate against.',
    '  - Fellowships ORDER OF THE CULTS (each Brotherhood Cult must match at least one XV Independent Character Cult) is reserved for a dedicated hidden-category validator pass.',
    '', 'DRY-RUN RESULT: PASS' if not APPLY else 'APPLY RESULT: PASS'
]
OUT.write_text('\n'.join(lines), encoding='utf-8')

if APPLY:
    root.set('revision','18')
    core.ct.write(CAT, encoding='utf-8', xml_declaration=True)
    core.gt.write(GST, encoding='utf-8', xml_declaration=True)
    idx = IDX.read_text(encoding='utf-8')
    idx = re.sub(r'(filePath="Legiones Astartes\.cat"[^>]*dataRevision=")\d+(")', r'\g<1>18\2', idx)
    IDX.write_text(idx, encoding='utf-8')

print('\n'.join(lines))
