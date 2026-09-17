from pathlib import Path
from copy import deepcopy
import importlib.util
import os
import re
import xml.etree.ElementTree as ET

# Build on the already-passing R18 core + finish passes, but force both to remain
# in-memory only. This final audit is the only stage allowed to publish revision 18.
os.environ['TS_APPLY'] = '0'
os.environ['TS_FINISH_APPLY'] = '0'
spec = importlib.util.spec_from_file_location('r18finish', '.github/build/live_r18_thousand_sons_finish.py')
finish = importlib.util.module_from_spec(spec)
spec.loader.exec_module(finish)

core = finish.core
root = finish.root
groot = finish.groot
C = finish.C
G = finish.G
CAT = finish.CAT
GST = finish.GST
IDX = finish.IDX
APPLY = os.environ.get('TS_FINAL_APPLY', '0') == '1'
OUT = Path('inspection-r18-thousand-sons-final-audit-dry-run.txt')

findid = core.findid
ensure = core.ensure
add_constraint = core.add_constraint
add_modifier = core.add_modifier
cond = core.cond
setpts = core.setpts
prefix_clone = core.prefix_clone
strip_categories = core.strip_categories
make_subgroup = core.make_subgroup
add_power_group = core.add_power_group
remove_constraints = core.remove_constraints

log = []


def direct_groups(e):
    c = e.find(C('selectionEntryGroups'))
    return list(c) if c is not None else []


def direct_entries(e):
    c = e.find(C('selectionEntries'))
    return list(c) if c is not None else []


def rule(host, rid, name, text, hidden='false'):
    rs = ensure(host, 'rules')
    for x in list(rs):
        if x.get('id') == rid:
            rs.remove(x)
    r = ET.SubElement(rs, C('rule'), {'id': rid, 'name': name, 'hidden': hidden})
    d = ET.SubElement(r, C('description'))
    d.text = text
    return r


def catlink(host, lid, name, target, hidden='false', primary='false'):
    cs = ensure(host, 'categoryLinks')
    for x in list(cs):
        if x.get('id') == lid:
            cs.remove(x)
    return ET.SubElement(cs, C('categoryLink'), {
        'id': lid, 'name': name, 'targetId': target, 'hidden': hidden, 'primary': primary
    })


def add_entry(host_group, eid, name, pts=0, maxv=1):
    ses = ensure(host_group, 'selectionEntries')
    for x in list(ses):
        if x.get('id') == eid:
            ses.remove(x)
    e = ET.SubElement(ses, C('selectionEntry'), {
        'id': eid, 'name': name, 'type': 'upgrade', 'hidden': 'false', 'import': 'true'
    })
    add_constraint(e, eid + '-max', 'max', maxv, 'parent')
    setpts(e, pts)
    return e


def set_selection_max(e, value):
    cs = ensure(e, 'constraints')
    m = next((x for x in cs if x.get('type') == 'max' and x.get('field') == 'selections'), None)
    if m is None:
        m = add_constraint(e, (e.get('id') or 'entry') + '-r18-final-max', 'max', value, 'parent')
    else:
        m.set('value', str(value))
    return m.get('id')


def group_max(g, value, prefix):
    cs = ensure(g, 'constraints')
    for x in list(cs):
        if x.get('type') == 'max' and x.get('field') == 'selections':
            x.set('value', str(value))
            return x.get('id')
    return add_constraint(g, prefix + '-max', 'max', value, 'parent').get('id')


def hide_if_less(host, mid, child, value=1, scope='root-entry'):
    return add_modifier(host, mid, 'set', 'hidden', 'true',
                        conditions=[cond('lessThan', value, child, scope)])


def prevent_duplicate_groups(groups, prefix):
    groups = [g for g in groups if g is not None]
    maps = []
    for g in groups:
        ses = g.find(C('selectionEntries'))
        maps.append({(x.get('name') or ''): x for x in list(ses) if ses is not None})
    count = 0
    for i, mp in enumerate(maps):
        for name, entry in mp.items():
            for j, other in enumerate(maps):
                if i == j or name not in other:
                    continue
                sid = re.sub(r'[^A-Za-z0-9_-]', '-', name)
                add_modifier(entry, f'{prefix}-{i}-{j}-{sid}', 'set', 'hidden', 'true',
                             conditions=[cond('atLeast', 1, other[name].get('id'), 'root-entry')])
                count += 1
    return count


def ensure_hidden_category_limit(cat_id, cat_name, unit_name, limit=1):
    cats = ensure(groot, 'categoryEntries', G)
    if findid(groot, cat_id) is None:
        ET.SubElement(cats, G('categoryEntry'), {'id': cat_id, 'name': cat_name, 'hidden': 'true'})
    tagged = 0
    for u in root.iter(C('selectionEntry')):
        if u.get('type') == 'unit' and (u.get('name') or '') == unit_name:
            catlink(u, f'{cat_id}-tag-{tagged}', cat_name, cat_id)
            tagged += 1
    force = findid(groot, 'force-standard')
    fcls = ensure(force, 'categoryLinks', G)
    old = next((x for x in fcls if x.get('id') == cat_id + '-force'), None)
    if old is not None:
        fcls.remove(old)
    fl = ET.SubElement(fcls, G('categoryLink'), {
        'id': cat_id + '-force', 'name': cat_name, 'hidden': 'true', 'targetId': cat_id
    })
    add_constraint(fl, cat_id + '-max', 'max', limit, 'parent', ns=G)
    return tagged


def clone_sergeant_armoury(host, gid, name, gate_id=None, note=None):
    src = findid(root, 'hs-hss-armoury')
    if src is None:
        # Fallback: find any 50-point Armoury group containing a Power Weapon.
        src = next((g for g in root.iter(C('selectionEntryGroup'))
                    if 'Armoury' in (g.get('name') or '')
                    and any(x.get('targetId') == 'gear-power-weapon' for x in g.iter(C('entryLink')))), None)
    if src is None:
        raise RuntimeError('Could not find reusable 50-point Space Marine Armoury group')
    gs = ensure(host, 'selectionEntryGroups')
    for x in list(gs):
        if x.get('id') == gid:
            gs.remove(x)
    cl = prefix_clone(src, gid + '-clone-')
    cl.set('id', gid)
    cl.set('name', name)
    cl.set('hidden', 'false')
    strip_categories(cl)
    if gate_id:
        add_modifier(cl, gid + '-hide', 'set', 'hidden', 'true',
                     conditions=[cond('lessThan', 1, gate_id, 'root-entry')])
    if note:
        rule(cl, gid + '-rule', name, note)
    gs.append(cl)
    return cl


def add_repeat_increment(host, mid, field_id, child_id, value=1):
    ms = ensure(host, 'modifiers')
    for x in list(ms):
        if x.get('id') == mid:
            ms.remove(x)
    m = ET.SubElement(ms, C('modifier'), {
        'id': mid, 'type': 'increment', 'field': field_id, 'value': str(value)
    })
    reps = ET.SubElement(m, C('repeats'))
    ET.SubElement(reps, C('repeat'), {
        'field': 'selections', 'scope': 'root-entry', 'value': '1', 'percentValue': 'false',
        'shared': 'true', 'includeChildSelections': 'true', 'includeChildForces': 'false',
        'childId': child_id, 'repeats': '1', 'roundUp': 'false'
    })
    return m


def copy_known_discipline_profiles(host, discipline, prefix):
    src = findid(root, 'r61-librarian-power1')
    if src is None:
        raise RuntimeError('Missing reusable psychic power source')
    hps = ensure(host, 'profiles')
    hrs = ensure(host, 'rules')
    copied = 0
    ses = src.find(C('selectionEntries'))
    for e in list(ses) if ses is not None else []:
        if not (e.get('name') or '').lower().startswith(discipline.lower() + ' '):
            continue
        ps = e.find(C('profiles'))
        if ps is not None:
            for p in list(ps):
                cp = prefix_clone(p, prefix + '-profile-')
                hps.append(cp)
        rs = e.find(C('rules'))
        if rs is not None:
            for r in list(rs):
                cr = prefix_clone(r, prefix + '-rule-')
                hrs.append(cr)
        copied += 1
    return copied


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
        c = ET.SubElement(cs, C('characteristic'), {'name': cn, 'typeId': cid})
        c.text = val
    return p


# -----------------------------------------------------------------------------
# 1. CORRECT THE FELLOWSHIPS TACTICAL POWER RULE + BROTHERHOOD COUNTING
# -----------------------------------------------------------------------------
# The base Veteran/Terminator Brotherhood is Cult-discipline locked. The Fellowships
# Tactical Brotherhood is not: its source explicitly allows any normal XV discipline.
tpg = findid(root, 'r18-ts-tactical-brotherhood-power')
if tpg is None:
    raise RuntimeError('Missing Tactical Brotherhood psychic group from R18 core')
for e in list(tpg.find(C('selectionEntries')) or []):
    ms = e.find(C('modifiers'))
    if ms is not None:
        for m in list(ms):
            if 'cult-gate' in (m.get('id') or ''):
                ms.remove(m)
log.append('Fellowships Tactical Brotherhood corrected to choose from any normal Thousand Sons discipline (not Cult-locked)')

# Inherent Brotherhood units must count toward the Fellowships minimum-two validator.
bro_cat = 'r18-ts-cat-brotherhood'
if findid(groot, bro_cat) is None:
    raise RuntimeError('R18 Brotherhood hidden category missing')
bro_tagged = 0
for uname in ('SEKHMET TERMINATOR CABAL','KHENETAI OCCULT BLADE CABAL','AMMITARA OCCULT INTERCESSION CABAL'):
    for u in root.iter(C('selectionEntry')):
        if u.get('type') == 'unit' and (u.get('name') or '') == uname:
            catlink(u, f'r18-final-bro-{bro_tagged}', 'Thousand Sons Psychic Brotherhood', bro_cat)
            bro_tagged += 1
log.append(f'Fellowships Brotherhood minimum now counts {bro_tagged} inherent Brotherhood root/retinue copies')

# -----------------------------------------------------------------------------
# 2. PROSPERINE FORCE WEAPON ACCESS FOR 50-POINT SERGEANT/CHARACTER ARMOURIES
# -----------------------------------------------------------------------------
fw_added = 0
for g in root.iter(C('selectionEntryGroup')):
    n = g.get('name') or ''
    if 'Armoury' not in n:
        continue
    # Restrict this sweep to 50-point character/sergeant armouries.
    has50 = any(c.get('type') == 'max' and c.get('field') == 'pts' and float(c.get('value','0')) == 50
                for c in list(g.find(C('constraints')) or []))
    if not has50:
        continue
    if not any(x.get('targetId') == 'gear-power-weapon' for x in g.iter(C('entryLink'))):
        continue
    if any(x.get('targetId') == 'r45-ts-force-weapon' for x in g.iter(C('entryLink'))):
        continue
    finish.add_link(g, f'r18-final-ts-force-{fw_added}', 'Prosperine Force Weapon upgrade', 'r45-ts-force-weapon')
    fw_added += 1
log.append(f'Prosperine Force Weapon upgrade added to {fw_added} eligible 50-point Space Marine Armoury selectors')

# -----------------------------------------------------------------------------
# 3. SEKHMET COMPLETE FUNCTIONAL PASS
# -----------------------------------------------------------------------------
sek = findid(root, 'r41-unit-xv-0-sekhmet-terminator-cabal')
sekopt = next((g for g in direct_groups(sek) if (g.get('name') or '') == 'Options'), None)
sekmodel = findid(root, 'r41-unit-xv-0-sekhmet-terminator-cabal-additional')
if sek is None or sekopt is None or sekmodel is None:
    raise RuntimeError('Sekhmet structure missing')

# Existing R18 heavy group: permit up to four of one weapon at ten models while the
# shared subgroup still enforces 2/5 or 4/10 total.
heavy = findid(root, 'r18-ts-sekhmet-heavy-replacements')
if heavy is None:
    raise RuntimeError('Sekhmet heavy replacement subgroup missing')
for x in list(heavy.find(C('selectionEntries')) or []):
    set_selection_max(x, 4)

# All Foeblaster replacements, including Combi-weapons, share the one-per-model cap.
foe_groups = ensure(sekopt, 'selectionEntryGroups')
foe = ET.SubElement(foe_groups, C('selectionEntryGroup'), {
    'id':'r18-final-sekhmet-foeblaster','name':'Foeblaster Boltgun replacements — one per model','hidden':'false'
})
foemax = add_constraint(foe, 'r18-final-sekhmet-foeblaster-max', 'max', 5, 'parent').get('id')
add_modifier(foe, 'r18-final-sekhmet-foeblaster-max10', 'set', foemax, 10,
             conditions=[cond('atLeast', 10, sekmodel.get('id'), 'root-entry')])
# Move the existing heavy subgroup under this overall replacement cap.
for p in root.iter(C('selectionEntryGroups')):
    if heavy in list(p):
        p.remove(heavy)
        ensure(foe, 'selectionEntryGroups').append(heavy)
        break

term = findid(root, 'terminator-unit')
combi_src = next((g for g in term.iter(C('selectionEntryGroup'))
                  if (g.get('name') or '') == 'Ranged Weapon Replacements'), None)
if combi_src is None:
    raise RuntimeError('Generic Terminator Ranged Weapon Replacements group missing')
combids = []
els = ensure(foe, 'entryLinks')
for src in combi_src.iter(C('entryLink')):
    nm = (src.get('name') or '')
    if not nm.lower().startswith('combi-'):
        continue
    cl = prefix_clone(src, 'r18-final-sekhmet-combi-')
    cl.set('hidden','false')
    strip_categories(cl)
    set_selection_max(cl, 10)
    els.append(cl)
    combids.append(nm)
if not combids:
    raise RuntimeError('No generic Combi-weapon links found for Sekhmet')

inceptor = findid(root, 'r41-unit-xv-0-sekhmet-terminator-cabal-opt-5-sekhmet-inceptor')
harness = findid(root, 'r41-unit-xv-0-sekhmet-terminator-cabal-opt-6-grenade-harness')
if inceptor is None or harness is None:
    raise RuntimeError('Sekhmet Inceptor/Harness missing')
hide_if_less(harness, 'r18-final-sekhmet-harness-inceptor', inceptor.get('id'))
sp2 = add_power_group(sek, 'r18-final-sekhmet-power2', 'Additional Psychic Power — Sekhmet Inceptor (Mastery Level 2)',
                      allowed=['Biomancy','Divination','Pyromancy','Telekinesis','Telepathy'],
                      gate_ids=[inceptor.get('id')], source_group_id='r61-librarian-power2')
sp1 = findid(root, 'r18-ts-sekhmet-power')
prevent_duplicate_groups([sp1, sp2], 'r18-final-sekhmet-power-nodup')

# Dedicated Transport: clone the normal Terminator transport choices, preserving
# their own child rules/profiles and rewriting generic Terminator model references.
trans_src = next((g for g in direct_groups(term) if (g.get('name') or '') == 'Dedicated Transport'), None)
if trans_src is None:
    raise RuntimeError('Generic Terminator Dedicated Transport group missing')
sgs = ensure(sek, 'selectionEntryGroups')
trans = ET.SubElement(sgs, C('selectionEntryGroup'), {
    'id':'r18-final-sekhmet-transport','name':'Dedicated Transport','hidden':'false'
})
add_constraint(trans, 'r18-final-sekhmet-transport-max', 'max', 1, 'parent')
term_model_ids = {x.get('id') for x in term.iter(C('selectionEntry')) if x.get('type') == 'model' and x.get('id')}
seen_names = set()
cloned_transport = []
for src in list(trans_src.iter()):
    tag = src.tag.rsplit('}',1)[-1]
    if tag not in ('selectionEntry','entryLink'):
        continue
    nm = (src.get('name') or '').strip()
    low = nm.lower()
    if not (low.startswith('land raider ') or 'dreadclaw' in low or 'spartan' in low):
        continue
    # Avoid rite-specific duplicates and hidden shadow entries.
    if src.get('hidden') == 'true' or nm in seen_names or '(' in nm:
        continue
    seen_names.add(nm)
    cl = prefix_clone(src, 'r18-final-sekhmet-trans-')
    cl.set('hidden','false')
    strip_categories(cl)
    for z in cl.iter():
        if z.get('childId') in term_model_ids:
            z.set('childId', sekmodel.get('id'))
    if tag == 'entryLink':
        ensure(trans, 'entryLinks').append(cl)
    else:
        ensure(trans, 'selectionEntries').append(cl)
    if 'dreadclaw' in low:
        add_modifier(cl, 'r18-final-sekhmet-dreadclaw-size', 'set', 'hidden', 'true',
                     conditions=[cond('atLeast', 6, sekmodel.get('id'), 'root-entry')])
    cloned_transport.append(nm)

# The generic Terminator entry only exposes the Dreadclaw directly. The catalogue
# already contains shared Heavy Support entries used elsewhere as Dedicated
# Transports, so add clean links to those source entries rather than borrowing
# Rite-specific Armoured Spearhead / Steel Fist copies.
def add_shared_transport(target_id, eid, name, hide_at_six=False):
    if findid(root, target_id) is None:
        raise RuntimeError('Missing shared transport source '+target_id)
    if any((n or '').lower().startswith(name.lower()) for n in cloned_transport):
        return
    el = ET.SubElement(ensure(trans, 'entryLinks'), C('entryLink'), {
        'id': eid, 'name': name, 'hidden': 'false', 'type': 'selectionEntry',
        'targetId': target_id, 'import': 'true'
    })
    add_constraint(el, eid+'-max', 'max', 1, 'parent')
    if hide_at_six:
        add_modifier(el, eid+'-size', 'set', 'hidden', 'true',
                     conditions=[cond('atLeast', 6, sekmodel.get('id'), 'root-entry')])
    cloned_transport.append(name)

add_shared_transport('hs-land-raider', 'r18-final-sekhmet-land-raider', 'Land Raider', hide_at_six=True)
add_shared_transport('hs-spartan', 'r18-final-sekhmet-spartan', 'Legion Spartan Assault Tank')

rule(trans, 'r18-final-sekhmet-transport-rule', 'Dedicated Transport',
     'The Cabal may select a Land Raider, Dreadclaw Drop Pod or Spartan Assault Tank where Transport Capacity permits. Land Raider patterns must have sufficient capacity for the selected Cabal size.')
if not any('dreadclaw' in n.lower() for n in cloned_transport) or not any('spartan' in n.lower() for n in cloned_transport) or not any(n.lower().startswith('land raider ') for n in cloned_transport):
    raise RuntimeError('Sekhmet transport cloning missed one or more required transport families: '+repr(cloned_transport))
log.append(f'Sekhmet completed: {len(combids)} Combi-weapon choices, shared Foeblaster cap, Inceptor ML2 power/Harness gate, {len(cloned_transport)} transport choices')

# -----------------------------------------------------------------------------
# 4. KHENETAI / AMMITARA LEADER ARMOURIES
# -----------------------------------------------------------------------------
khe = findid(root, 'r41-unit-xv-1-khenetai-occult-blade-cabal')
blade = findid(root, 'r41-unit-xv-1-khenetai-occult-blade-cabal-opt-0-khenetai-blademaster')
amm = findid(root, 'r41-unit-xv-2-ammitara-occult-intercession-cabal')
if khe is None or blade is None or amm is None:
    raise RuntimeError('Khenetai/Ammitara leader structure missing')
clone_sergeant_armoury(
    khe, 'r18-final-khenetai-blademaster-armoury', 'Khenetai Blademaster — Space Marine Armoury (max 50 pts)', blade.get('id'),
    'The Blademaster may select up to 50 points of permitted Space Marine Armoury weapons and wargear. His Paired Prosperine Force Blades are retained and may not be replaced.'
)
clone_sergeant_armoury(
    amm, 'r18-final-ammitara-fate-armoury', 'Ammitara Fate — Space Marine Armoury (max 50 pts)', None,
    'The Ammitara Fate may select up to 50 points of permitted weapons and wargear from the Space Marine Armoury.'
)
log.append('Khenetai Blademaster and Ammitara Fate now have functional 50-point Space Marine Armoury selectors')

# -----------------------------------------------------------------------------
# 5. CASTELLAX-ACHEA / OSIRON / NUMEROLOGIST REPLACEMENT FAMILIES
# -----------------------------------------------------------------------------
cast = findid(root, 'r41-unit-xv-3-castellax-achea-maniple')
copt = next((g for g in direct_groups(cast) if (g.get('name') or '') == 'Options'), None)
cmodel = findid(root, 'r41-unit-xv-3-castellax-achea-maniple-additional')
chf = findid(root, 'r41-unit-xv-3-castellax-achea-maniple-opt-0-heavy-flamer')
if not all((cast,copt,cmodel,chf)):
    raise RuntimeError('Castellax-Achea structure missing')
set_selection_max(chf, 3)
cg = make_subgroup(copt, [chf.get('id')], 'r18-final-castellax-bolter-repl', 'Twin-linked Bolter replacement — any Castellax-Achea', 1)
cmax = group_max(cg, 1, 'r18-final-castellax-bolter-repl')
add_modifier(cg, 'r18-final-castellax-bolter-max2', 'set', cmax, 2,
             conditions=[cond('atLeast',2,cmodel.get('id'),'root-entry')])
add_modifier(cg, 'r18-final-castellax-bolter-max3', 'set', cmax, 3,
             conditions=[cond('atLeast',3,cmodel.get('id'),'root-entry')])

osi = findid(root, 'r41-unit-xv-4-contemptor-osiron-dreadnought')
oopt = next((g for g in direct_groups(osi) if (g.get('name') or '') == 'Options'), None)
if osi is None or oopt is None:
    raise RuntimeError('Osiron options missing')
make_subgroup(oopt, [f'r41-unit-xv-4-contemptor-osiron-dreadnought-opt-{i}-{s}' for i,s in [
    (1,'heavy-flamer'),(2,'graviton-gun'),(3,'meltagun')]],
    'r18-final-osiron-built-in-bolter', 'Built-in Twin-linked Bolter replacement — choose up to one', 1)
make_subgroup(oopt, [f'r41-unit-xv-4-contemptor-osiron-dreadnought-opt-{i}-{s}' for i,s in [
    (4,'twin-linked-heavy-bolter'),(5,'multi-melta'),(6,'twin-linked-autocannon'),(7,'plasma-cannon'),
    (8,'twin-linked-volkite-culverin'),(9,'kheres-assault-cannon'),(10,'twin-linked-lascannon')]],
    'r18-final-osiron-dccw-replacement', 'Dreadnought Close Combat Weapon replacement — choose up to one', 1)
prevent_duplicate_groups([findid(root,'r18-ts-osiron-power1'), findid(root,'r18-ts-osiron-power2')], 'r18-final-osiron-power-nodup')

num = findid(root, 'r41-unit-xv-5-numerologist-cabal')
nopt = next((g for g in direct_groups(num) if (g.get('name') or '') == 'Options'), None)
if num is None or nopt is None:
    raise RuntimeError('Numerologist options missing')
make_subgroup(nopt, [f'r41-unit-xv-5-numerologist-cabal-opt-{i}-{s}' for i,s in [
    (0,'power-weapon'),(1,'prosperine-force-weapon'),(2,'thunder-hammer')]],
    'r18-final-numerologist-melee', 'Numerologist Chainsword replacement — choose up to one', 1)
make_subgroup(nopt, [f'r41-unit-xv-5-numerologist-cabal-opt-{i}-{s}' for i,s in [
    (3,'volkite-charger'),(4,'flamer'),(5,'plasma-gun'),(6,'meltagun'),(7,'graviton-gun')]],
    'r18-final-numerologist-pistol', 'Numerologist Bolt Pistol replacement — choose up to one', 1)
log.append('Castellax-Achea, Osiron and Numerologist replacement families made mutually exclusive with source-correct dynamic quantities')

# -----------------------------------------------------------------------------
# 6. UNIQUE UNIT 0-1 ACROSS NORMAL + RETINUE COPIES
# -----------------------------------------------------------------------------
copy_limits = []
for cid,cname,uname in [
    ('r18-final-cat-sekhmet-01','Sekhmet Cabal 0-1','SEKHMET TERMINATOR CABAL'),
    ('r18-final-cat-khenetai-01','Khenetai Cabal 0-1','KHENETAI OCCULT BLADE CABAL'),
    ('r18-final-cat-ammitara-01','Ammitara Cabal 0-1','AMMITARA OCCULT INTERCESSION CABAL')
]:
    copy_limits.append((uname, ensure_hidden_category_limit(cid,cname,uname,1)))
log.append('Cross-copy 0-1 limits applied across normal and retinue copies: '+', '.join(f'{n}={c} copies' for n,c in copy_limits))

# -----------------------------------------------------------------------------
# 7. AHRIMAN — ALL DIVINATION + FUNCTIONAL AHRIMAN'S CABAL
# -----------------------------------------------------------------------------
ahr = findid(root, 'r41-unit-xv-6-ahzek-ahriman')
if ahr is None:
    raise RuntimeError('Ahriman missing')
for r in list(ahr.find(C('rules')) or []):
    if (r.get('name') or '') == 'Source Entry':
        r.set('hidden','true')
rule(ahr, 'r18-final-ahriman-corvidae', 'Corvidae',
     'Ahriman always belongs to the Corvidae and may not select another Prosperine Cult. He receives both the Corvidae Cult Arcana and Cult Mastery benefits.')
rule(ahr, 'r18-final-ahriman-chief', 'Chief Librarian',
     'Ahriman knows every psychic power in the ProHammer Divination discipline. He does not randomly select or choose a limited number of Divination powers before the battle, but still follows the normal ProHammer limit on powers successfully invoked during a player turn.')
rule(ahr, 'r18-final-ahriman-staff', 'Black Staff of Ahriman',
     'Master-crafted Prosperine Force Weapon. Once during each player turn Ahriman may re-roll one failed Psychic Test; the second result must be accepted. If the re-rolled test also fails, he suffers Perils of the Warp in addition to the normal consequences. Activating the Black Staff as a Force Weapon does not count as invoking a psychic power.')
div_count = copy_known_discipline_profiles(ahr, 'Divination', 'r18-final-ahriman-div')
if div_count < 1:
    raise RuntimeError('Failed to surface Ahriman Divination powers')

retg = next((g for g in direct_groups(ahr) if (g.get('name') or '').startswith('Retinue')), None)
cmd = next((u for u in list(retg.find(C('selectionEntries')) or []) if (u.get('name') or '') == 'Legion Command Squad'), None) if retg is not None else None
if cmd is None:
    raise RuntimeError('Ahriman Legion Command Squad retinue missing')
cmdgs = ensure(cmd, 'selectionEntryGroups')
for g in list(cmdgs):
    if 'ahrimans-cabal-group' in (g.get('id') or '') or (g.get('name') or '') == "Ahriman's Cabal":
        cmdgs.remove(g)
acg = ET.SubElement(cmdgs, C('selectionEntryGroup'), {'id':'r18-final-ahriman-cabal-group','name':"Ahriman's Cabal",'hidden':'false'})
acu = add_entry(acg, 'r18-final-ahriman-cabal-upgrade', "Ahriman's Cabal", 50, 1)
rule(acu, 'r18-final-ahriman-cabal-rule', "Ahriman's Cabal",
     'The Command Squad becomes Brotherhood of Psykers (Mastery Level 2), is fixed to the Corvidae, receives Corvidae Cult Arcana and Cult Mastery, and selects two Divination powers. It remains a separate Psyker from Ahriman.')
catlink(acu, 'r18-final-ahriman-cabal-brotherhood', 'Thousand Sons Psychic Brotherhood', bro_cat)
acp1 = add_power_group(cmd, 'r18-final-ahriman-cabal-power1', "Ahriman's Cabal — Divination Power 1",
                       allowed=['Divination'], gate_ids=[acu.get('id')])
acp2 = add_power_group(cmd, 'r18-final-ahriman-cabal-power2', "Ahriman's Cabal — Divination Power 2",
                       allowed=['Divination'], gate_ids=[acu.get('id')], source_group_id='r61-librarian-power2')
prevent_duplicate_groups([acp1,acp2], 'r18-final-ahriman-cabal-nodup')

# +5 per selected Power Weapon, dynamically capped to the number of Power Weapons
# actually purchased in this Command Squad.
fg = ET.SubElement(cmdgs, C('selectionEntryGroup'), {
    'id':'r18-final-ahriman-cabal-force-group','name':"Ahriman's Cabal — Prosperine Force Weapon upgrades",'hidden':'false'
})
fmax = add_constraint(fg, 'r18-final-ahriman-cabal-force-max', 'max', 0, 'parent').get('id')
hide_if_less(fg, 'r18-final-ahriman-cabal-force-hide', acu.get('id'))
fu = add_entry(fg, 'r18-final-ahriman-cabal-force', 'Upgrade a selected Power Weapon to a Prosperine Force Weapon (+5)', 5, 5)
rule(fu, 'r18-final-ahriman-cabal-force-rule', 'Prosperine Force Weapon — Ahriman’s Cabal',
     'Each selection upgrades one model in Ahriman’s Cabal which has purchased a Power Weapon. The model retains all other wargear normally.')
pw_links = [x for x in cmd.iter(C('entryLink')) if x.get('targetId') == 'gear-power-weapon']
for i,x in enumerate(pw_links):
    add_repeat_increment(fg, f'r18-final-ahriman-cabal-force-cap-{i}', fmax, x.get('id'), 1)
if not pw_links:
    raise RuntimeError('Ahriman Command Squad exposes no Power Weapon selections to key the +5 Force upgrades from')
# Suppress the generic +10 version when this Command Squad has purchased the Cabal upgrade.
fw = findid(root, 'r45-ts-force-weapon')
if fw is not None:
    add_modifier(fw, 'r18-final-ahriman-cabal-hide-generic-force', 'set', 'hidden', 'true',
                 conditions=[cond('atLeast',1,acu.get('id'),'root-entry')])
log.append(f'Ahriman completed: all {div_count} Divination powers surfaced; Cabal +50 gives fixed Corvidae ML2, two Divination powers and dynamic +5 Force-weapon upgrades')

# -----------------------------------------------------------------------------
# 8. NO DUPLICATE PSYCHIC POWERS ON MULTI-POWER XV PSYKERS
# -----------------------------------------------------------------------------
multis = [
    ['r18-ts-praetor-power1','r18-ts-praetor-power2','r18-ts-praetor-power3'],
    ['r18-ts-centurion-power1','r18-ts-centurion-power2'],
    ['r18-ts-r41-unit-xv-7-phosis-t-kar-power1','r18-ts-r41-unit-xv-7-phosis-t-kar-power2'],
    ['r18-ts-r41-unit-xv-8-magistus-amon-the-hidden-power1','r18-ts-r41-unit-xv-8-magistus-amon-the-hidden-power2'],
    ['r18-ts-r41-unit-xv-9-hathor-maat-power1','r18-ts-r41-unit-xv-9-hathor-maat-power2'],
]
ndup_mods = 0
for k,ids in enumerate(multis):
    ndup_mods += prevent_duplicate_groups([findid(root,i) for i in ids], f'r18-final-nodup-{k}')
log.append(f'Duplicate psychic-power choices blocked across generic/named multi-power Thousand Sons Psykers ({ndup_mods} cross-slot gates)')

# -----------------------------------------------------------------------------
# 9. MAGNUS, SHARD OF THE CRIMSON KING
# -----------------------------------------------------------------------------
mortal = findid(root, 'r41-unit-xv-11-xv-magnus-the-red-the-crimson-king')
shard = findid(root, 'r41-unit-xv-12-magnus-shard-of-the-crimson-king')
if mortal is None or shard is None:
    raise RuntimeError('Mortal Magnus or Magnus Shard missing')
# Mutual exclusion between the two forms exactly as the Shard source requires.
mcats = ensure(groot, 'categoryEntries', G)
if findid(groot, 'r18-final-cat-magnus-form') is None:
    ET.SubElement(mcats, G('categoryEntry'), {'id':'r18-final-cat-magnus-form','name':'Magnus form 0-1','hidden':'true'})
catlink(mortal, 'r18-final-magnus-mortal-form', 'Magnus form 0-1', 'r18-final-cat-magnus-form')
catlink(shard, 'r18-final-magnus-shard-form', 'Magnus form 0-1', 'r18-final-cat-magnus-form')
force = findid(groot, 'force-standard')
fcls = ensure(force, 'categoryLinks', G)
old = next((x for x in fcls if x.get('id') == 'r18-final-magnus-form-force'), None)
if old is not None: fcls.remove(old)
mfl = ET.SubElement(fcls, G('categoryLink'), {'id':'r18-final-magnus-form-force','name':'Magnus form 0-1','hidden':'true','targetId':'r18-final-cat-magnus-form'})
add_constraint(mfl, 'r18-final-magnus-form-max', 'max', 1, 'parent', ns=G)

# Ensure the Shard remains XV-only.
add_modifier(shard, 'r18-final-shard-xv-only', 'set', 'hidden', 'true',
             conditions=[cond('lessThan',1,'legion-xv','roster')])
for r in list(shard.find(C('rules')) or []):
    if (r.get('name') or '') == 'Source Entry':
        r.set('hidden','true')
# Repair the markdown-imported starred profile values.
prof = next(iter(shard.find(C('profiles')) or []), None)
if prof is not None:
    ch = prof.find(C('characteristics'))
    for c in list(ch) if ch is not None else []:
        if c.get('name') == 'T': c.text = '*'
        if c.get('name') == 'W': c.text = '7*'
        if c.get('name') == 'Sv': c.text = '–'

rule(shard, 'r18-final-shard-blade', 'Aetheric Blade', 'Master-crafted Force Weapon. Magnus resolves attacks made with it at Strength 7.')
rule(shard, 'r18-final-shard-ethereal', 'Ethereal',
     'Magnus has seven Wounds but no conventional Toughness and no Armour or Invulnerable Save. Non-psychic shooting hits only on an unmodified 6 and successful hits wound only on an unmodified 6; automatic-hit weapons still need a 6 to wound. Non-psychic Blast weapons cannot directly strike him and are moved the minimum distance away after scatter. In close combat, normal weapons wound on 6+, Power Weapons/Power Fists/Thunder Hammers or equivalent on 5+, and Force Weapons on 2+. Psychic attacks ignore the normal shooting restrictions and treat him as Toughness 7 only when a Toughness value is required. He is immune to Instant Death; Massive Wounds affect him normally only from an activated Force Weapon or a psychic effect which specifically inflicts Massive Wounds, otherwise such effects inflict one Wound.')
rule(shard, 'r18-final-shard-will', 'Incorporeal Will',
     'Magnus may never declare a charge or make a Pursuit move. He may fight normally if charged and Consolidate normally after combat. Magnus may never join another unit and no model may join him.')
rule(shard, 'r18-final-shard-unbound', 'The Crimson King Unbound',
     'Magnus is a Mastery Level 5 Psyker. Before deployment choose six powers from Biomancy, Divination, Pyromancy, Telekinesis and Telepathy. He also always knows Infernal Phoenix and Strands of Fate; these do not count toward the six selected powers. He may invoke up to five powers per player turn, may successfully manifest each individual power no more than once in that player turn, and may invoke up to two Witchfire powers in the same Shooting phase.')
add_ranged_profile(shard, 'r18-final-shard-infernal-profile', 'Infernal Phoenix', '24"', '8', '1', 'Witchfire, Beam, Melta')
rule(shard, 'r18-final-shard-infernal', 'Infernal Phoenix', 'Witchfire — Beam. Resolve using the normal rules for a Beam psychic power.')
rule(shard, 'r18-final-shard-strands', 'Strands of Fate',
     'Malediction, 18 inches. Choose one enemy non-Vehicle unit in range and line of sight. Until the beginning of Magnus’ next turn, the affected unit must pass a Leadership Test each time it wishes to Move, Shoot or Charge; a failed test loses that action for the phase.')
rule(shard, 'r18-final-shard-cults', 'Beyond the Prosperine Cults',
     'Magnus is not assigned to a Prosperine Cult and gains no Cult Arcana or Cult Mastery benefit. He counts as Thousand Sons for army selection and rules referring to friendly Thousand Sons models.')
rule(shard, 'r18-final-shard-blessing', 'Nothing to Bless',
     'Magnus may never be the target of a Blessing, whether manifested by himself or another Psyker. Any Blessing manifested by Magnus must target another eligible friendly unit.')
rule(shard, 'r18-final-shard-ocean', 'Master of the Great Ocean',
     'Magnus ignores Leadership penalties from Disturbance in the Warp. Powers successfully invoked by Magnus do not count when determining Disturbance penalties for other Psykers. He may attempt to Deny the Witch if either the invoking Psyker or the target is within 24 inches, using his own Mastery Level; each power may still only be the subject of one Deny attempt.')
rule(shard, 'r18-final-shard-perils', 'Beyond the Perils of the Warp',
     'Whenever Magnus would suffer Perils of the Warp, ignore the normal result and place one Instability Counter beside him instead. Each counter imposes a cumulative -1 on his next Warp Breath roll; remove all Instability Counters after that roll. There is no maximum number of counters.')
rule(shard, 'r18-final-shard-breathes', 'The Warp Breathes',
     'At the beginning of each Thousand Sons turn while Magnus is on the battlefield, roll D6 and apply Instability Counter modifiers. 1 or less: The Crimson King Fades — Magnus enters Reserve without being destroyed and, from the following Thousand Sons turn, returns by normal Reserve roll using Deep Strike; if still in Reserve at battle end he counts as destroyed for Victory Points. 2–5: Reality Holds — no additional effect. 6+: The Warp Ascendant — until the next Thousand Sons turn every Psyker may re-roll failed Psychic Tests, but any Psychic Test containing a double causes Perils even if successful and even if that double is subsequently re-rolled. Magnus converts his Perils into Instability Counters normally.')
rule(shard, 'r18-final-shard-shattered', 'The Crimson King Shattered',
     'If Magnus actually loses his final Wound and is destroyed, every friendly non-Vehicle unit with Legiones Astartes (Thousand Sons) immediately suffers D3 Strength 4 AP– hits. Then every friendly Thousand Sons Psyker or Brotherhood suffers Perils of the Warp; a Thousand Sons Independent Character with Psyker suffers Perils twice. These effects ignore range and line of sight. For Signs and Portents, all Perils caused by this rule count as one triggering event, applied after all resulting Perils and casualties are resolved.')

shard_groups = []
for i in range(1,7):
    shard_groups.append(add_power_group(shard, f'r18-final-shard-power{i}', f'Selected Psychic Power {i} — The Crimson King Unbound',
                                        allowed=['Biomancy','Divination','Pyromancy','Telekinesis','Telepathy'],
                                        source_group_id='r61-librarian-power1' if i == 1 else 'r61-librarian-power2'))
prevent_duplicate_groups(shard_groups, 'r18-final-shard-power-nodup')
log.append('Magnus Shard completed: repaired starred profile, mortal/Shard mutual exclusion, six unique selectable normal powers plus fixed Infernal Phoenix/Strands, and discrete battlefield rules')

# -----------------------------------------------------------------------------
# 10. BROTHERHOOD COUNT: CABAL / CRIMSON KING GUARD UPGRADES
# -----------------------------------------------------------------------------
# Ahriman's Cabal was tagged above. Tag Magnus' Crimson King's Guard upgrades too.
ckg = 0
for e in root.iter(C('selectionEntry')):
    if (e.get('name') or '') == 'Brotherhood of Psykers (Mastery Level 1)':
        # Restrict to the two Magnus retinue upgrades generated by the R18 finish pass.
        if 'crimson-guard' in (e.get('id') or ''):
            catlink(e, f'r18-final-ckg-bro-{ckg}', 'Thousand Sons Psychic Brotherhood', bro_cat)
            ckg += 1
log.append(f'Fellowships Brotherhood validator also counts Ahriman’s Cabal and {ckg} Crimson King’s Guard upgrade selections')

# -----------------------------------------------------------------------------
# 11. FINAL VALIDATIONS + PUBLISH SWITCH
# -----------------------------------------------------------------------------
checks = {
    'Sekhmet second power': findid(root,'r18-final-sekhmet-power2'),
    'Sekhmet transport': findid(root,'r18-final-sekhmet-transport'),
    'Khenetai armoury': findid(root,'r18-final-khenetai-blademaster-armoury'),
    'Ammitara armoury': findid(root,'r18-final-ammitara-fate-armoury'),
    'Ahriman Cabal': findid(root,'r18-final-ahriman-cabal-upgrade'),
    'Shard power six': findid(root,'r18-final-shard-power6'),
    'Magnus form category': findid(groot,'r18-final-cat-magnus-form'),
}
missing = [n for n,e in checks.items() if e is None]
if missing:
    raise RuntimeError('Final audit missing: '+', '.join(missing))

# Validate that all three inherent Brotherhood names have at least one hidden category tag.
for uname in ('SEKHMET TERMINATOR CABAL','KHENETAI OCCULT BLADE CABAL','AMMITARA OCCULT INTERCESSION CABAL'):
    matches = [u for u in root.iter(C('selectionEntry')) if u.get('type') == 'unit' and (u.get('name') or '') == uname]
    if not matches or any(not any(c.get('targetId') == bro_cat for c in list(u.find(C('categoryLinks')) or [])) for u in matches):
        raise RuntimeError('Brotherhood category tagging incomplete for '+uname)

lines = [
    'R18 THOUSAND SONS FINAL AUDIT — ' + ('APPLY' if APPLY else 'DRY RUN ONLY'),
    f'Input live CAT revision: 17 | Proposed CAT revision: 18 | GST revision remains {groot.get("revision")}',
    f'LIVE FILES WRITTEN: {"YES" if APPLY else "NO"}',
    '', 'FINAL CHANGES:'
]
lines += ['  + ' + x for x in log]
lines += [
    '', 'PRESERVED AS TEXT / NOT FAKED:',
    '  - Guard of the Crimson King: written Sekhmet 0-1 versus compulsory-Sekhmet-Troops contradiction remains unresolved rather than inventing an exception.',
    '  - Axis and Guard cross-unit vehicle ratios remain source rule text because the current catalogue has no reliable unit-type counter across all nested/linked units.',
    '  - Allied Detachment / Fortification bans remain source rule text because those force choices are not exposed safely enough in the current GST for dependable automation.',
    '  - Warlord-only requirements remain explicit rule/selector text because there is no single trustworthy Warlord selection marker in the current catalogue.',
    '  - Fellowships ORDER OF THE CULTS remains source rule text; a cross-unit hidden validator could falsely match a Brotherhood in one root entry to a Cult selected by another root entry.',
    '', 'FINAL AUDIT RESULT: PASS'
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
