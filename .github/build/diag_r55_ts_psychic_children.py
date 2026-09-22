import xml.etree.ElementTree as ET
NS="http://www.battlescribe.net/schema/catalogueSchema";C=lambda t:f"{{{NS}}}{t}"
r=ET.parse("Legiones Astartes.cat").getroot(); ids={x.get("id"):x for x in r.iter() if x.get("id")}
def con(e):return [(x.get("id"),x.get("type"),x.get("value"),x.get("scope"),x.get("field")) for x in e.findall(f"./{C('constraints')}/{C('constraint')}")]
def mods(e):
 m=e.find(C("modifiers"));return ET.tostring(m,encoding="unicode") if m is not None else ""
def print_group(gid):
 g=ids.get(gid);print("\\nGROUP",gid,bool(g))
 if not g:return
 print("name",g.get("name"),"hidden",g.get("hidden"),"cons",con(g),"mods",mods(g))
 for contname in ["selectionEntries","entryLinks"]:
  p=g.find(C(contname))
  if p is not None:
   for x in list(p):
    print(" ",x.tag.split("}")[-1],x.get("id"),x.get("name"),"target",x.get("targetId"),"hidden",x.get("hidden"),"cons",con(x),"mods",mods(x))
for gid in [
"r45-cult-hq-praetor","r19-ts-praetor-disciplines","r19-ts-praetor-powers",
"r45-cult-hq-centurion","r19-ts-centurion-disciplines","r19-ts-centurion-powers",
"r45-cult-veteran-unit","r19-ts-veteran-unit-brotherhood-disciplines","r19-ts-veteran-unit-brotherhood-powers",
"r45-cult-terminator-unit","r19-ts-terminator-unit-brotherhood-disciplines","r19-ts-terminator-unit-brotherhood-powers",
"r45-cult-tactical-unit","r19-ts-tactical-brotherhood-disciplines","r19-ts-tactical-brotherhood-powers"
]:print_group(gid)
