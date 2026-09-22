import xml.etree.ElementTree as ET
NS="http://www.battlescribe.net/schema/catalogueSchema";C=lambda t:f"{{{NS}}}{t}"
r=ET.parse("Legiones Astartes.cat").getroot();ids={x.get("id"):x for x in r.iter() if x.get("id")}
def mods(e):
 m=e.find(C("modifiers"));return ET.tostring(m,encoding="unicode") if m is not None else ""
def show(rootid,gids):
 root=ids[rootid]; print("\\nROOT",rootid)
 for gid in gids:
  g=next((x for x in root.iter(C("selectionEntryGroup")) if x.get("id")==gid),None);print("\\nGROUP",gid,"exists",bool(g))
  if not g:continue
  for conttag in ["selectionEntries","entryLinks"]:
   c=g.find(C(conttag))
   if c is None:continue
   for x in list(c):print(x.tag.split("}")[-1],x.get("id"),x.get("name"),"target",x.get("targetId"),"hidden",x.get("hidden"),"mods",mods(x))
show("hq-praetor",["r45-cult-hq-praetor","r19-ts-praetor-disciplines","r19-ts-praetor-powers"])
show("veteran-unit",["r45-cult-veteran-unit","r19-ts-veteran-unit-brotherhood-disciplines","r19-ts-veteran-unit-brotherhood-powers"])
