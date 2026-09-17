from pathlib import Path
p=Path('.github/build/live_r18_thousand_sons_finish.py')
s=p.read_text(encoding='utf-8')

old="""add_rule(praetor, 'r18-ts-praetor-psyker-rule', 'Sorcerers of Prospero — Praetor',
         'In a Thousand Sons Detachment, a Legion Praetor is a Psyker (Mastery Level 2) and selects two powers from Biomancy, Divination, Pyromancy, Telekinesis or Telepathy. Activating a Force Weapon counts as the use of a psychic power, and the same power may not be used more than once in the same player turn.')
add_rule(centurion, 'r18-ts-centurion-psyker-rule', 'Sorcerers of Prospero — Independent Character',
         'In a Thousand Sons Detachment, a Legion Centurion and its Consul variants are Psykers (Mastery Level 1) unless another rule grants a higher Mastery Level. A Librarian Consul follows the normal Librarian upgrade rules; an Epistolary is Mastery Level 2.')
"""
new="""add_rule(praetor, 'r18-ts-praetor-psyker-rule', 'Sorcerers of Prospero — Praetor',
         'In a Thousand Sons Detachment, a Legion Praetor is a Psyker (Mastery Level 2) and selects two powers from Biomancy, Divination, Pyromancy, Telekinesis or Telepathy. Activating a Force Weapon counts as the use of a psychic power, and the same power may not be used more than once in the same player turn.').set('hidden','true')
add_rule(centurion, 'r18-ts-centurion-psyker-rule', 'Sorcerers of Prospero — Independent Character',
         'In a Thousand Sons Detachment, a Legion Centurion and its Consul variants are Psykers (Mastery Level 1) unless another rule grants a higher Mastery Level. A Librarian Consul follows the normal Librarian upgrade rules; an Epistolary is Mastery Level 2.').set('hidden','true')
"""
if old not in s: raise SystemExit('generic HQ rules block not found')
s=s.replace(old,new,1)

old="""        if not any(x.get('targetId') == 'r45-ts-trans-unit' for x in u.iter(C('entryLink'))):
            add_link(u, 'r18-ts-termcmd-trans-' + re.sub(r'[^A-Za-z0-9_-]', '-', u.get('id')), 'Teleportation Transponders', 'r45-ts-trans-unit')
            termcmd_count += 1
"""
new="""        if not any(x.get('targetId') == 'r45-ts-trans-unit' for x in u.iter(C('entryLink'))):
            lid = 'r18-ts-termcmd-trans-' + re.sub(r'[^A-Za-z0-9_-]', '-', u.get('id'))
            lnk = add_link(u, lid, 'Teleportation Transponders', 'r45-ts-trans-unit')
            add_modifier(lnk, lid + '-hide-no-xv', 'set', 'hidden', 'true',
                         conditions=[cond('lessThan', 1, 'legion-xv', 'roster')])
            termcmd_count += 1
"""
if old not in s: raise SystemExit('term command block not found')
s=s.replace(old,new,1)

old="""if findid(root,'r18-ts-magnus-retinue-sekhmet') is None:
    raise RuntimeError('Missing Magnus Sekhmet retinue')
"""
new="""retcheck = next((x for x in list(ret_ses) if 'SEKHMET TERMINATOR CABAL' in (x.get('name') or '')), None)
if retcheck is None:
    raise RuntimeError('Missing Magnus Sekhmet retinue')
"""
if old not in s: raise SystemExit('retinue validation block not found')
s=s.replace(old,new,1)

p.write_text(s,encoding='utf-8')
print('patched',p)
