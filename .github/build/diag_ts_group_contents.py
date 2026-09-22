import xml.etree.ElementTree as ET
NS="http://www.battlescribe.net/schema/catalogueSchema"; C=lambda t:f"{{{NS}}}{t}"
r=ET.parse("Legiones Astartes.cat").getroot(); ids={x.get("id"):x for x in r.iter() if x.get("id")}
def cons(e):return [(x.get("id"),x.get("type"),x.get("value"),x.get("scope"),x.get("field")) for x in e.findall(f"./{C('constraints')}/{C('constraint')}")]
def mods(e):
 m=e.find(C("modifiers"));return ET.tostring(m,encoding="unicode") if m is not None else ""
for gid in [
"r45-cult-hq-praetor","r19-ts-praetor-disciplines","r19-ts-praetor-powers",
"r45-cult-hq-centurion","r19-ts-centurion-disciplines","r19-ts-centurion-powers",
"r45-cult-veteran-unit","r19-ts-veteran-unit-brotherhood-disciplines","r19-ts-veteran-unit-brotherhood-powers",
"r45-cult-r41-unit-xv-0-sekhmet-terminator-cabal","r19-ts-sekhmet-disciplines","r19-ts-sekhmet-powers"
]:
 g=ids.get(gid);print("\\n====",gid,"====")
 if g is None:print("MISSING");continue
 for boxname in ["selectionEntries","entryLinks","selectionEntryGroups"]:
  box=g.find(C(boxname)); ch=list(box) if box is not None else []
  print(boxname,"count",len(ch))
  for x in ch:
   print(" ",x.tag.split("}")[-1],x.get("id"),x.get("name"),"target",x.get("targetId"),"hidden",x.get("hidden"),"cons",cons(x),"mods",mods(x)[:3500])
   t=ids.get(x.get("targetId"))
   if t is not None:print("   TARGET",t.tag.split("}")[-1],t.get("id"),t.get("name"),"hidden",t.get("hidden"),"cons",cons(t))
