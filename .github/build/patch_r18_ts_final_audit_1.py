from pathlib import Path
p=Path('.github/build/live_r18_thousand_sons_final_audit.py')
s=p.read_text(encoding='utf-8')
old="""combi_src = next((g for g in term.iter(C('selectionEntryGroup'))
                  if 'Combi-Bolter Replacements' in (g.get('name') or '')), None)
if combi_src is None:
    raise RuntimeError('Generic Terminator Combi-Bolter replacement group missing')
"""
new="""combi_src = next((g for g in term.iter(C('selectionEntryGroup'))
                  if (g.get('name') or '') == 'Ranged Weapon Replacements'), None)
if combi_src is None:
    raise RuntimeError('Generic Terminator Ranged Weapon Replacements group missing')
"""
if old not in s:
    raise SystemExit('target block not found')
p.write_text(s.replace(old,new,1),encoding='utf-8')
print('patched',p)
