import xml.etree.ElementTree as ET
NS="http://www.battlescribe.net/schema/catalogueSchema"; C=lambda t:f"{{{NS}}}{t}"
r=ET.parse("Legiones Astartes.cat").getroot(); ids={x.get("id"):x for x in r.iter() if x.get("id")}; pm={c:p for p in r.iter() for c in p}
for eid in ["r57-ts-centurion-psychic-package","r45-cult-hq-praetor","r19-ts-praetor-disciplines","r19-ts-praetor-powers"]:
 e=ids[eid];print("\\n",eid,e.get("name"))
 p=e
 while p is not None:
  print(" ",p.tag.split("}")[-1],p.get("id"),p.get("name"),"hidden",p.get("hidden"))
  p=pm.get(p)
cent=ids["hq-centurion"]
print("\\nCENT DIRECT GROUPS")
for g in cent.findall(f"./{C('selectionEntryGroups')}/{C('selectionEntryGroup')}"):print(g.get("id"),g.get("name"),"hidden",g.get("hidden"))
