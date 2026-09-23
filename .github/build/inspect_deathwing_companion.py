from pathlib import Path
import xml.etree.ElementTree as ET
NS="http://www.battlescribe.net/schema/catalogueSchema";C=lambda t:f"{{{NS}}}{t}"
p=Path("modular-catalogues-generated/Dark-Angels.cat");r=ET.parse(p).getroot()
for e in r.iter(C("selectionEntry")):
 if e.get("id")=="da22-deathwing-term-comp":
  print(ET.tostring(e,encoding="unicode"))
