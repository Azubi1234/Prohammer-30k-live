from pathlib import Path
import xml.etree.ElementTree as ET
CAT=Path("Legiones Astartes.cat"); OUT=Path("inspection-r37-wb-lookup.txt")
NS="http://www.battlescribe.net/schema/catalogueSchema"; C=lambda t:f"{{{NS}}}{t}"
r=ET.parse(CAT).getroot()
lines=[]
for e in r.iter(C("selectionEntry")):
    n=(e.get("name") or "").lower()
    if any(k in n for k in ["land raider","spartan","drop pod","dreadclaw","narthecium","reductor","axe-rake","custodian spear","illuminarium","hand flamer","plasma blaster","twin-linked autocannon","twin-linked lascannon","multi-melta"]):
        lines.append(f"{e.get('id')} | {e.get('name')} | type={e.get('type')}")
OUT.write_text("\n".join(lines),encoding="utf-8")
print(OUT.read_text())
