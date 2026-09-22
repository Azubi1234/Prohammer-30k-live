import xml.etree.ElementTree as ET,re
NS="http://www.battlescribe.net/schema/catalogueSchema";C=lambda t:f"{{{NS}}}{t}"
r=ET.parse("Legiones Astartes.cat").getroot()
for e in r.findall(f"./{C('selectionEntries')}/{C('selectionEntry')}"):
  if not any(c.get("targetId")=="cat-hq" and c.get("primary")=="true" for c in e.findall(f"./{C('categoryLinks')}/{C('categoryLink')}")):continue
  names=[x.get("name") or "" for x in e.findall(f"./{C('rules')}/{C('rule')}")]+[x.get("name") or "" for x in e.findall(f"./{C('infoLinks')}/{C('infoLink')}")]
  la=[n for n in names if n.startswith("Legiones Astartes (")]
  if not la:continue
  maxr=[(x.get("value"),x.get("scope")) for x in e.findall(f"./{C('constraints')}/{C('constraint')}") if x.get("type")=="max"]
  print(e.get("id"),"|",e.get("name"),"| type",e.get("type"),"| LA",la,"| max",maxr)
