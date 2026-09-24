from pathlib import Path
import re, sys
root=Path("modular-catalogues-generated")
files=sorted(root.glob("*.cat"))
assert len(files)==19, f"expected 19 modular catalogues, found {len(files)}"
for p in files:
    s=p.read_text(encoding="utf-8")
    s2=re.sub(r'gameSystemRevision="(?:15|16)"', 'gameSystemRevision="16"', s, count=1)
    if s2==s and 'gameSystemRevision="16"' not in s:
        raise SystemExit(f"missing gameSystemRevision in {p}")
    p.write_text(s2, encoding="utf-8")
print(f"Aligned {len(files)} modular catalogues to game system revision 16")
