import xml.etree.ElementTree as ET
NS="http://www.battlescribe.net/schema/catalogueSchema"; C=lambda t:f"{{{NS}}}{t}"
r=ET.parse("Legiones Astartes.cat").getroot(); ids={x.get("id"):x for x in r.iter() if x.get("id")}
v=ids["veteran-unit"]
def con(e): return [(x.get("id"),x.get("type"),x.get("value"),x.get("scope"),x.get("field")) for x in e.findall(f"./{C('constraints')}/{C('constraint')}")]
def mods(e):
 m=e.find(C("modifiers")); return ET.tostring(m,encoding="unicode") if m is not None else ""
print("ROOT CHILD MODELS")
for x in v.findall(f"./{C('selectionEntries')}/{C('selectionEntry')}"):
 print(x.get("id"),x.get("name"),"default",x.get("defaultAmount"),"cons",con(x),"mods",mods(x))
print("\\nGROUPS")
for g in v.findall(f"./{C('selectionEntryGroups')}/{C('selectionEntryGroup')}"):
 n=(g.get("name") or "").lower()
 if any(k in n for k in ["melee","weapon","close","veteran"]):
  print("\\nGROUP",g.get("id"),g.get("name"),"cons",con(g),"mods",mods(g))
  for x in g:
   if x.tag in [C("selectionEntry"),C("entryLink"),C("selectionEntryGroup")]:
    print(" ",x.tag.split("}")[-1],x.get("id"),x.get("name"),"target",x.get("targetId"),"default",x.get("defaultAmount"),"cons",con(x),"mods",mods(x))
