from pathlib import Path
import subprocess

BASE='41c7755e59b6db0b38e2a426e0f7cb8e6189c110'  # Live R20 known-good
CAT='Legiones Astartes.cat'
GST='Prohammer 30k.gst'
IDX='index.xml'

def show(path):
    return subprocess.check_output(['git','show',f'{BASE}:{path}'])

base_cat=show(CAT)
base_gst=show(GST)
base_idx=show(IDX)

# Preserve the exact known-good BattleScribe XML serialization.
# Only alter the top-level catalogue revision and the index revision.
old=b'revision="20"'
new=b'revision="24"'
if base_cat.count(old)!=1:
    raise RuntimeError(f'Expected exactly one catalogue revision="20"; found {base_cat.count(old)}')
new_cat=base_cat.replace(old,new,1)

old_idx=b'dataRevision="20"'
new_idx=b'dataRevision="24"'
if base_idx.count(old_idx)!=1:
    raise RuntimeError(f'Expected exactly one index dataRevision="20"; found {base_idx.count(old_idx)}')
new_index=base_idx.replace(old_idx,new_idx,1)

Path(CAT).write_bytes(new_cat)
Path(GST).write_bytes(base_gst)
Path(IDX).write_bytes(new_index)

# Byte-for-byte validation against R20 after normalizing only the revision number.
assert new_cat.replace(new,old,1)==base_cat
assert new_index.replace(new_idx,old_idx,1)==base_idx
assert Path(GST).read_bytes()==base_gst

Path('inspection-live-r24-byte-clean-restore.txt').write_text(
    'LIVE R24 — BYTE-CLEAN RESTORE OF KNOWN-GOOD R20\\n'
    'Root cause found: the R23 rollback parsed and re-serialized the 18MB catalogue with Python ElementTree, changing the namespace serialization of the entire file.\\n'
    'R24 restores the exact known-good R20 catalogue bytes and changes ONLY catalogue revision 20 -> 24.\\n'
    'The exact known-good R20 game system is restored byte-for-byte.\\n'
    'The exact known-good R20 index is restored and changes ONLY dataRevision 20 -> 24.\\n'
    'Validation confirms normalized R24 catalogue/index are byte-for-byte identical to Live R20.\\n'
    'This retains all content present in Live R20: Thousand Sons through R20 and Iron Hands mobile Bionics.\\n',
    encoding='utf-8'
)
print('R24 byte-clean restore prepared and validated')
