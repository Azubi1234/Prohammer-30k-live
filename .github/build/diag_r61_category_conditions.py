import xml.etree.ElementTree as ET
NS="http://www.battlescribe.net/schema/catalogueSchema";C=lambda t:f"{{{NS}}}{t}"
r=ET.parse("Legiones Astartes.cat").getroot()
n=0
for x in r.iter(C("condition")):
 c=x.get("childId") or ""
 if c.startswith("cat-") or "-cat-" in c:
  print(ET.tostring(x,encoding="unicode"));n+=1
  if n>=100:break
print("COUNT_SHOWN",n)
