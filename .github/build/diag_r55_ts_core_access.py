import xml.etree.ElementTree as ET,re
NS="http://www.battlescribe.net/schema/catalogueSchema";C=lambda t:f"{{{NS}}}{t}"
r=ET.parse("Legiones Astartes.cat").getroot(); ids={x.get("id"):x for x in r.iter() if x.get("id")}
def cons(e):return [(x.get("id"),x.get("type"),x.get("value"),x.get("scope"),x.get("field")) for x in e.findall(f"./{C('constraints')}/{C('constraint')}")]
def mods(e):
 m=e.find(C("modifiers"));return ET.tostring(m,encoding="unicode") if m is not None else ""
for eid in ["hq-praetor","hq-centurion","veteran-unit","terminator-unit","tactical-unit","assault-unit","breacher-unit","recon-unit"]:
 e=ids[eid]
 print("\\n====",eid,e.get("name"),"====")
 for g in e.findall(f"./{C('selectionEntryGroups')}/{C('selectionEntryGroup')}"):
  if any(k in (g.get("name") or "").lower() for k in ["prosperine","psychic","discipline","cult","legion wargear"] ) or "r45" in (g.get("id") or "") or "r19-ts" in (g.get("id") or ""):
   print("GROUP",g.get("id"),g.get("name"),"hidden",g.get("hidden"),"cons",cons(g),"mods",mods(g)[:4000])
   for x in list(g):
    if x.tag in [C("selectionEntry"),C("entryLink")]:
     print(" ",x.tag.split("}")[-1],x.get("id"),x.get("name"),"target",x.get("targetId"),"hidden",x.get("hidden"),"cons",cons(x),"mods",mods(x)[:2500])
 print("DIRECT ENTRYLINKS TS")
 for l in e.findall(f"./{C('entryLinks')}/{C('entryLink')}"):
  if "ts" in (l.get("id") or "") or any(k in (l.get("name") or "").lower() for k in ["brotherhood","arcane","asphyx","transponder","aether"]):
   print(" LINK",l.get("id"),l.get("name"),l.get("targetId"),l.get("hidden"),cons(l),mods(l)[:2500])
