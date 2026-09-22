import xml.etree.ElementTree as ET
NS="http://www.battlescribe.net/schema/catalogueSchema"; C=lambda t:f"{{{NS}}}{t}"
r=ET.parse("Legiones Astartes.cat").getroot(); pm={c:p for p in r.iter() for c in p}; ids={x.get("id"):x for x in r.iter() if x.get("id")}
def cons(e):return [(x.get("id"),x.get("type"),x.get("value"),x.get("scope"),x.get("field")) for x in e.findall(f"./{C('constraints')}/{C('constraint')}")]
def mods(e):
 m=e.find(C("modifiers"));return ET.tostring(m,encoding="unicode") if m is not None else ""
for eid in ["legion-i","legion-ii","legion-xx","allegiance-loyalist","allegiance-traitor","rite-tactical","r25-rite-xix-0-decapitation-strike"]:
 e=ids.get(eid); print("\\nID",eid, "EXISTS",bool(e))
 if not e:continue
 print("SELF",e.tag.split("}")[-1],e.get("id"),e.get("name"),e.get("type"),e.get("hidden"),cons(e),mods(e)[:2500])
 p=pm.get(e)
 while p is not None:
  print(" PARENT",p.tag.split("}")[-1],p.get("id"),p.get("name"),"hidden",p.get("hidden"),"cons",cons(p),"mods",mods(p)[:1800])
  p=pm.get(p)
print("\\nROOT GROUPS")
for g in r.findall(f"./{C('selectionEntryGroups')}/{C('selectionEntryGroup')}"):
 print(g.get("id"),g.get("name"),g.get("hidden"),cons(g),mods(g)[:3000])
 for ch in list(g):
  if ch.tag in [C("selectionEntry"),C("entryLink"),C("selectionEntryGroup")]:
   print("  ",ch.tag.split("}")[-1],ch.get("id"),ch.get("name"),ch.get("targetId"),ch.get("hidden"),cons(ch))
print("\\nROOT CONFIG ENTRIES")
for e in r.findall(f"./{C('selectionEntries')}/{C('selectionEntry')}"):
 if e.get("type")=="upgrade" and any(x in (e.get("id") or "") for x in ["legion","allegiance","rite"]):
  print(e.get("id"),e.get("name"),e.get("hidden"),cons(e))
