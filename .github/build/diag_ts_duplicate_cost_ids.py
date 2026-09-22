import xml.etree.ElementTree as ET
NS="http://www.battlescribe.net/schema/catalogueSchema"; C=lambda t:f"{{{NS}}}{t}"
r=ET.parse("Legiones Astartes.cat").getroot();pm={c:p for p in r.iter() for c in p}
for target in ["r18-ts-khenetai-scale--pts","r18-ts-ammitara-scale--pts"]:
 print("\\nTARGET",target)
 for e in r.iter():
  if e.get("id")==target or e.get("field")==target or e.get("childId")==target:
   p=pm.get(e)
   print(e.tag.split("}")[-1],e.attrib,"PARENT",p.tag.split("}")[-1] if p is not None else None,p.get("id") if p is not None else None,p.get("name") if p is not None else None)
