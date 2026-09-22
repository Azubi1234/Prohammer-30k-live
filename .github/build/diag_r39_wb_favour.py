from pathlib import Path
import xml.etree.ElementTree as ET
CAT=Path("Legiones Astartes.cat"); OUT=Path("inspection-r39-wb-favour-duplicates.txt")
NS="http://www.battlescribe.net/schema/catalogueSchema"; C=lambda t:f"{{{NS}}}{t}"
r=ET.parse(CAT).getroot(); pm={c:p for p in r.iter() for c in p}
def anc(e,lim=8):
    out=[]; p=pm.get(e)
    while p is not None and len(out)<lim:
        out.append(f"{p.tag.split('}')[-1]}:{p.get('id')}:{p.get('name')}")
        p=pm.get(p)
    return " > ".join(out)
terms={"Daemonic Aura","Daemonic Mutation","Daemonic Strength","Daemonic Wings","Daemonic Visage"}
lines=[f"CAT={r.get('revision')}"]
for e in r.iter():
    if (e.get("name") or "") in terms:
        lines.append(f"{e.tag.split('}')[-1]} id={e.get('id')} name={e.get('name')} type={e.get('type')} hidden={e.get('hidden')} anc={anc(e)}")
OUT.write_text("\n".join(lines)+"\n",encoding="utf-8")
print(OUT.read_text())
