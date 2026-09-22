import xml.etree.ElementTree as ET
NS="http://www.battlescribe.net/schema/catalogueSchema"; C=lambda t:f"{{{NS}}}{t}"
r=ET.parse("Legiones Astartes.cat").getroot(); ids={x.get("id"):x for x in r.iter() if x.get("id")}
for eid in ["legion-i","legion-x","legion-xviii","legion-xix","legion-xx","legion-xv","legion-xvii"]:
 e=ids[eid]
 print("\\n==",eid,e.get("name"),"==")
 print("RULES")
 for x in e.findall(f"./{C('rules')}/{C('rule')}"): print(x.get("id"),x.get("name"),":",(x.findtext(C("description")) or "")[:500])
 print("INFOS")
 for x in e.findall(f"./{C('infoLinks')}/{C('infoLink')}"): print(x.get("id"),x.get("name"),"->",x.get("targetId"),x.get("type"),"hidden",x.get("hidden"))
 print("GROUPS")
 for g in e.findall(f"./{C('selectionEntryGroups')}/{C('selectionEntryGroup')}"): print(g.get("id"),g.get("name"))
