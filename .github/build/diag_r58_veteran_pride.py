import xml.etree.ElementTree as ET, collections
NS="http://www.battlescribe.net/schema/catalogueSchema"; C=lambda t:f"{{{NS}}}{t}"
r=ET.parse("Legiones Astartes.cat").getroot(); pm={c:p for p in r.iter() for c in p}; ids={x.get("id"):x for x in r.iter() if x.get("id")}
def cost(e):return [(x.get("typeId"),x.get("value")) for x in e.findall(f"./{C('costs')}/{C('cost')}")]
def con(e):return [(x.get("id"),x.get("type"),x.get("value"),x.get("scope"),x.get("field")) for x in e.findall(f"./{C('constraints')}/{C('constraint')}")]
def mods(e):
 m=e.find(C("modifiers"));return ET.tostring(m,encoding="unicode") if m is not None else ""
def chain(e):
 out=[];p=e
 while p is not None and len(out)<10:
  out.append((p.tag.split("}")[-1],p.get("id"),p.get("name")));p=pm.get(p)
 return out
print("REV",r.get("revision"))
for e in r.iter(C("selectionEntry")):
 n=(e.get("name") or "").lower(); eid=e.get("id") or ""
 if "pride of the legion" in n or ("pride" in eid.lower() and "rite" in eid.lower()):
  print("\\nPRIDE",eid,e.get("name"),"hidden",e.get("hidden"),"cats",[(c.get("targetId"),c.get("primary")) for c in e.findall(f"./{C('categoryLinks')}/{C('categoryLink')}")],"mods",mods(e)[:5000])
print("\\nALL VETERAN SQUAD ENTRIES")
for e in r.iter(C("selectionEntry")):
 if (e.get("name") or "").strip().lower().startswith("legion veteran squad"):
  print("\\nVET",e.get("id"),e.get("name"),"hidden",e.get("hidden"),"cost",cost(e),"cons",con(e),"chain",chain(e))
  for g in e.findall(f"./{C('selectionEntryGroups')}/{C('selectionEntryGroup')}"):
   if "melee" in (g.get("name") or "").lower() or "close combat" in (g.get("name") or "").lower() or "brother" in (g.get("name") or "").lower() or "cult" in (g.get("name") or "").lower():
    print(" GROUP",g.get("id"),g.get("name"),"cons",con(g),"mods",mods(g)[:9000])
    for x in list(g):
     if x.tag in [C("selectionEntry"),C("entryLink")]:
      print("   ",x.tag.split("}")[-1],x.get("id"),x.get("name"),"hidden",x.get("hidden"),"cost",cost(x),"cons",con(x),"mods",mods(x)[:3000])
  for x in e.findall(f"./{C('selectionEntries')}/{C('selectionEntry')}"):
   if "brother" in (x.get("name") or "").lower() or "cult" in (x.get("name") or "").lower():
    print(" CHILD",x.get("id"),x.get("name"),cost(x),con(x),mods(x)[:3000])
print("\\nTS RELATED UNDER VETERAN ROOT")
v=ids.get("veteran-unit")
if v:
 for e in v.iter():
  n=(e.get("name") or "").lower()
  if any(k in n for k in ["thousand","brotherhood","pavoni","raptora","corvidae","athanaean","pyrae","psychic"]):
   print(e.tag.split("}")[-1],e.get("id"),e.get("name"),"hidden",e.get("hidden"),"cost",cost(e),"cons",con(e),"mods",mods(e)[:4000],"chain",chain(e))
