from pathlib import Path
import xml.etree.ElementTree as ET
CAT=Path("Legiones Astartes.cat"); OUT=Path("inspection-r37-transport-patterns.txt")
NS="http://www.battlescribe.net/schema/catalogueSchema"; C=lambda t:f"{{{NS}}}{t}"
r=ET.parse(CAT).getroot(); ids={e.get("id"):e for e in r.iter() if e.get("id")}
lines=[]
for id_ in ["tactical-unit","veteran-unit","terminator-unit","breacher-unit","assault-unit","hq-praetor","hq-centurion"]:
    e=ids.get(id_); lines.append("==== "+id_+" ====")
    if e is None: continue
    for g in e.iter(C("selectionEntryGroup")):
        if "transport" in (g.get("name") or "").lower() or "armoury" in (g.get("name") or "").lower() or "consul" in (g.get("name") or "").lower():
            lines.append(ET.tostring(g,encoding="unicode")[:12000])
OUT.write_text("\n".join(lines),encoding="utf-8")
print(OUT.read_text())
