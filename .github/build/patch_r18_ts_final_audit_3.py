from pathlib import Path
p=Path('.github/build/live_r18_thousand_sons_final_audit.py')
s=p.read_text(encoding='utf-8')
old="not any(n.lower().startswith('land raider ') for n in cloned_transport)"
new="not any(n.lower().startswith('land raider') for n in cloned_transport)"
if old not in s:
    raise RuntimeError('Expected Land Raider validator expression not found')
s=s.replace(old,new,1)
p.write_text(s,encoding='utf-8')
print('Patched R18 final audit validator to accept canonical Land Raider entry name.')
