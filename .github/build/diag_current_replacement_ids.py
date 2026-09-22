import xml.etree.ElementTree as ET
NS="http://www.battlescribe.net/schema/catalogueSchema"; C=lambda t:f"{{{NS}}}{t}"
r=ET.parse("Legiones Astartes.cat").getroot()
needles=["Pair of Lightning Claws","Jetbike","Sanguine Pattern Jump Pack","Deathshroud Cataphractii","Terror Squad","Night Raptor","Plasma Cannon"]
for needle in needles:
 print("\\n==",needle,"==")
 n=0
 for e in r.iter():
  if needle.lower() in (e.get("name") or "").lower():
   print(e.tag.split("}")[-1],e.get("id"),"|",e.get("name"),"| target",e.get("targetId"))
   n+=1
   if n>=80:break
