import xml.etree.ElementTree as ET,re
NS="http://www.battlescribe.net/schema/catalogueSchema";C=lambda t:f"{{{NS}}}{t}"
r=ET.parse("Legiones Astartes.cat").getroot()
for e in r.findall(f"./{C('selectionEntries')}/{C('selectionEntry')}"):
 if e.get("type") not in ("unit","model"):continue
 names=[x.get("name") or "" for x in e.findall(f"./{C('rules')}/{C('rule')}")]+[x.get("name") or "" for x in e.findall(f"./{C('infoLinks')}/{C('infoLink')}")]
 la=[n for n in names if n.startswith("Legiones Astartes (")]
 if la and not (e.get("id") or "").startswith("r41-unit-"):
  print(e.get("id"),"|",e.get("name"),"|",la)
