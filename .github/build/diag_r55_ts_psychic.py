import xml.etree.ElementTree as ET,re,collections
NS="http://www.battlescribe.net/schema/catalogueSchema";C=lambda t:f"{{{NS}}}{t}"
r=ET.parse("Legiones Astartes.cat").getroot(); ids={x.get("id"):x for x in r.iter() if x.get("id")}; pm={c:p for p in r.iter() for c in p}
def con(e):return [(x.get("id"),x.get("type"),x.get("value"),x.get("scope"),x.get("field")) for x in e.findall(f"./{C('constraints')}/{C('constraint')}")]
def mods(e):
 m=e.find(C("modifiers"));return ET.tostring(m,encoding="unicode") if m is not None else ""
def chain(e,lim=8):
 a=[];p=e
 while p is not None and len(a)<lim:
  a.append((p.tag.split("}")[-1],p.get("id"),p.get("name")));p=pm.get(p)
 return a
print("LEGION XV")
e=ids["legion-xv"]
print("name",e.get("name"),"hidden",e.get("hidden"),"cons",con(e),"mods",mods(e))
for tag in ["rules","infoLinks","selectionEntries","selectionEntryGroups","entryLinks"]:
 p=e.find(C(tag))
 if p is not None:
  print("\\n",tag.upper())
  for x in list(p):
   print(x.tag.split("}")[-1],x.get("id"),x.get("name"),x.get("targetId"),x.get("hidden"),con(x),mods(x)[:2000])
   if x.tag==C("selectionEntryGroup"):
    for y in list(x):
     if y.tag in [C("selectionEntry"),C("entryLink"),C("selectionEntryGroup")]:
      print("  ",y.tag.split("}")[-1],y.get("id"),y.get("name"),y.get("targetId"),y.get("hidden"),con(y),mods(y)[:1500])
print("\\nPSYCH/CULT MATCHES")
for x in r.iter():
 n=(x.get("name") or "")
 if any(k in n.lower() for k in ["corvidae","raptora","pavoni","pyrae","athanaean","psychic discipline","biomancy","divination","pyromancy","telekinesis","telepathy","cult arcana","psyker"]):
  print(x.tag.split("}")[-1],x.get("id"),"|",n,"| hidden",x.get("hidden"),"| target",x.get("targetId"),"| cons",con(x),"| chain",chain(x,6))
