from pathlib import Path
import re

cat = Path('Legiones Astartes.cat')
idx = Path('index.xml')
out = Path('inspection-live-r12-publish.txt')

cat_text = cat.read_text(encoding='utf-8')
new_cat, n_cat = re.subn(
    r'(<catalogue\b[^>]*\brevision=")11("[^>]*>)',
    r'\g<1>12\2',
    cat_text,
    count=1,
    flags=re.S,
)
if n_cat != 1:
    raise RuntimeError(f'Expected exactly one catalogue revision 11 root attribute, changed {n_cat}')
cat.write_text(new_cat, encoding='utf-8')

idx_text = idx.read_text(encoding='utf-8')
new_idx, n_idx = re.subn(
    r'(filePath="Legiones Astartes\.cat"[^>]*dataRevision=")11(")',
    r'\g<1>12\2',
    idx_text,
    count=1,
)
if n_idx != 1:
    raise RuntimeError(f'Expected exactly one index dataRevision 11 entry, changed {n_idx}')
idx.write_text(new_idx, encoding='utf-8')

out.write_text(
    'LIVE R12 PUBLISH\n'
    'Catalogue revision bumped 11 -> 12 to force New Recruit to fetch the current Death Guard changes.\n'
    'No rules content changed in this publish step.\n',
    encoding='utf-8',
)
print(out.read_text(encoding='utf-8'))
