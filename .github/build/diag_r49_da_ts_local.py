import xml.etree.ElementTree as ET
NS="http://www.battlescribe.net/schema/catalogueSchema"; C=lambda t:f"{{{NS}}}{t}"
r=ET.parse("Legiones Astartes.cat").getroot(); pm={c:p for p in r.iter() for c in p}; ids={x.get("id"):x for x in r.iter() if x.get("id")}
def cons(e):return [(x.get("id"),x.get("type"),x.get("value"),x.get("scope"),x.get("field")) for x in e.findall(f"./{C('constraints')}/{C('constraint')}")]
def mods(e):
 m=e.find(C("modifiers"));return ET.tostring(m,encoding="unicode") if m is not None else ""
def chain(e):
 out=[];p=e
 while p is not None and len(out)<12:
  out.append((p.tag.split('}')[-1],p.get("id"),p.get("name")));p=pm.get(p)
 return out
for legid in ["legion-i","legion-xv"]:
 print("\\n====",legid,ids[legid].get("name"),"====")
 for e in r.iter():
  txt=(e.get("name") or "").lower()+" "+mods(e).lower()
  if legid in txt or any(c.get("childId")==legid for c in e.iter(C("condition"))):
   if e.tag in [C("selectionEntryGroup"),C("selectionEntry"),C("entryLink")]:
    print(e.tag.split("}")[-1],e.get("id"),e.get("name"),"hidden",e.get("hidden"),"cons",cons(e))
    print(" CHAIN",chain(e))
    if mods(e):print(" MOD",mods(e)[:4500])
