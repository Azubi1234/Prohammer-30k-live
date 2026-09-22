import xml.etree.ElementTree as ET
NS="http://www.battlescribe.net/schema/catalogueSchema"; C=lambda t:f"{{{NS}}}{t}"
r=ET.parse("Legiones Astartes.cat").getroot(); ids={x.get("id"):x for x in r.iter() if x.get("id")}
def cst(e):
 return [(x.get("id"),x.get("type"),x.get("value"),x.get("scope"),x.get("field")) for x in e.findall(f"./{C('constraints')}/{C('constraint')}")]
def cost(e):
 return [(x.get("typeId"),x.get("value")) for x in e.findall(f"./{C('costs')}/{C('cost')}")]
def mods(e):
 m=e.find(C("modifiers"));return ET.tostring(m,encoding="unicode") if m is not None else ""
def show(e,depth=0):
 print("  "*depth,e.tag.split("}")[-1],e.get("id"),"|",e.get("name"),"| target",e.get("targetId"),"| hidden",e.get("hidden"),"|",cost(e),"|",cst(e),"| mods",mods(e)[:1300])
 for tag in ["entryLinks","selectionEntries","selectionEntryGroups","infoLinks","rules"]:
  p=e.find(C(tag))
  if p is not None:
   for x in list(p): show(x,depth+1)
for eid in ["legion-xx","r46-al-mutable-tactics","r25-rite-xx-0-the-coils-of-the-hydra","r25-rite-xx-1-headhunter-leviathal","fa-seeker"]:
 print("\\n====",eid,"====")
 if eid in ids:show(ids[eid])
 else:
  for x in r.iter():
   if x.get("id")==eid:show(x);break
print("\\n==== AL SHARED ====")
for x in r.iter(C("selectionEntry")):
 if (x.get("id") or "").startswith("r46-al-") and not (x.get("id") or "").startswith("r46-al-reward-"):
  print(x.get("id"),"|",x.get("name"),"| hidden",x.get("hidden"),"|",cost(x),"|",cst(x))
