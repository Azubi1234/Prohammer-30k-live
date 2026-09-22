import xml.etree.ElementTree as ET, collections
NS="http://www.battlescribe.net/schema/catalogueSchema"; C=lambda t:f"{{{NS}}}{t}"
r=ET.parse("Legiones Astartes.cat").getroot(); ids={x.get("id"):x for x in r.iter() if x.get("id")}; pm={c:p for p in r.iter() for c in p}
def direct_names(e):
 return [x.get("name") or "" for x in e.findall(f"./{C('rules')}/{C('rule')}")]+[x.get("name") or "" for x in e.findall(f"./{C('infoLinks')}/{C('infoLink')}")]
def cons(e):return [(x.get("id"),x.get("type"),x.get("value"),x.get("scope"),x.get("field")) for x in e.findall(f"./{C('constraints')}/{C('constraint')}")]
def mods(e):
 m=e.find(C("modifiers"));return ET.tostring(m,encoding="unicode") if m is not None else ""
def chain(e):
 out=[];p=e
 while p is not None and len(out)<8:
  out.append((p.tag.split("}")[-1],p.get("id"),p.get("name")));p=pm.get(p)
 return out
print("REV",r.get("revision"))
print("\\nDA ROOT PREFIX")
for e in r.findall(f"./{C('selectionEntries')}/{C('selectionEntry')}"):
 eid=e.get("id") or ""
 if eid.startswith("r41-unit-i-"):
  print(eid,"|",e.get("name"),"| hidden",e.get("hidden"),"| direct",direct_names(e),"| mods",mods(e)[:2200])
  for g in e.iter(C("selectionEntryGroup")):
   n=(g.get("name") or "")
   if n in ["Hexagrammaton Wing","Order Exemplars"] or "Dark Angels Armoury" in n:
    links=g.findall(f"./{C('entryLinks')}/{C('entryLink')}")
    sels=g.findall(f"./{C('selectionEntries')}/{C('selectionEntry')}")
    print(" GROUP",g.get("id"),"|",n,"| links",len(links),"sels",len(sels),"|",[(x.get("name"),x.get("targetId")) for x in links+sels])
print("\\nORDER EXEMPLAR GROUPS")
for g in r.iter(C("selectionEntryGroup")):
 n=(g.get("name") or "")
 if "Order Exemplar" in n or "Order Exemplars" in n:
  links=g.findall(f"./{C('entryLinks')}/{C('entryLink')}");sels=g.findall(f"./{C('selectionEntries')}/{C('selectionEntry')}")
  print(g.get("id"),n,"links",len(links),"sels",len(sels),[(x.get("name"),x.get("targetId")) for x in links+sels],"path",chain(g))
print("\\nWING SUMMARY")
gs=[g for g in r.iter(C("selectionEntryGroup")) if (g.get("name") or "")=="Hexagrammaton Wing"]
print("groups",len(gs),"bad",[(g.get("id"),len(g.findall(f'./{C("entryLinks")}/{C("entryLink")}'))) for g in gs if len(g.findall(f'./{C("entryLinks")}/{C("entryLink")}'))!=6])
print("\\nDA-GATED ROOTS")
for e in r.findall(f"./{C('selectionEntries')}/{C('selectionEntry')}"):
 t=ET.tostring(e,encoding="unicode")
 if "legion-i" in t and ("r41-unit-i-" in (e.get("id") or "") or any(x in (e.get("name") or "").lower() for x in ["deathwing","dreadwing","firewing","dark angels","lion el'jonson","corswain","redloss","sedras","holguin"])):
  print(e.get("id"),e.get("name"),"hidden",e.get("hidden"),"mods",mods(e)[:1800])
