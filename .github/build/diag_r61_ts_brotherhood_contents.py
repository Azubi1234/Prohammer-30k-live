import xml.etree.ElementTree as ET
NS="http://www.battlescribe.net/schema/catalogueSchema"; C=lambda t:f"{{{NS}}}{t}"
r=ET.parse("Legiones Astartes.cat").getroot(); ids={x.get("id"):x for x in r.iter() if x.get("id")}
for rid in ["r19-ts-veteran-unit-brotherhood-disciplines","r19-ts-veteran-unit-brotherhood-powers","r19-ts-terminator-unit-brotherhood-disciplines","r19-ts-terminator-unit-brotherhood-powers"]:
 e=ids[rid];print("\\n==",rid,e.get("name"),"==")
 for tag in ["selectionEntries","entryLinks","selectionEntryGroups"]:
  p=e.find(C(tag))
  if p is None:continue
  for x in list(p):
   print(tag,x.tag.split("}")[-1],x.get("id"),x.get("name"),"->",x.get("targetId"),"hidden",x.get("hidden"))
   m=x.find(C("modifiers"))
   if m is not None:print(" MODS",ET.tostring(m,encoding="unicode")[:5000])
