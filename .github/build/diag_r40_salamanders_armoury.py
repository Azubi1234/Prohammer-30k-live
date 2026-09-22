from pathlib import Path
import xml.etree.ElementTree as ET
CAT=Path("Legiones Astartes.cat"); OUT=Path("inspection-r40-salamanders-armoury.txt")
NS="http://www.battlescribe.net/schema/catalogueSchema"; C=lambda t:f"{{{NS}}}{t}"
r=ET.parse(CAT).getroot()
lines=[]
for e in r.iter(C("selectionEntry")):
    if (e.get("id") or "").startswith("r46-sal"):
        lines.append("==== "+e.get("id")+" / "+(e.get("name") or "")+" ====")
        lines.append(ET.tostring(e,encoding="unicode")[:15000])
OUT.write_text("\n".join(lines),encoding="utf-8");print(OUT.read_text())
