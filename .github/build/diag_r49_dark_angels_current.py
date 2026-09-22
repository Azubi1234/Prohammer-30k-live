import xml.etree.ElementTree as ET, collections
NS="http://www.battlescribe.net/schema/catalogueSchema"; C=lambda t:f"{{{NS}}}{t}"
r=ET.parse("Legiones Astartes.cat").getroot(); ids={x.get("id"):x for x in r.iter() if x.get("id")}
pm={c:p for p in r.iter() for c in p}
def cons(e):return [(x.get("id"),x.get("type"),x.get("value"),x.get("scope"),x.get("field")) for x in e.findall(f"./{C('constraints')}/{C('constraint')}")]
def mods(e):
 m=e.find(C("modifiers"));return ET.tostring(m,encoding="unicode") if m is not None else ""
def chain(e,lim=8):
 out=[];p=e
 while p is not None and len(out)<lim:
  out.append((p.tag.split("}")[-1],p.get("id"),p.get("name")));p=pm.get(p)
 return out

print("REV",r.get("revision"),"GSTDEP",r.get("gameSystemRevision"))
print("\\n==== HEXAGRAMMATON WING GROUPS ====")
bad=[]
for g in r.iter(C("selectionEntryGroup")):
 if (g.get("name") or "")!="Hexagrammaton Wing": continue
 links=g.findall(f"./{C('entryLinks')}/{C('entryLink')}")
 sels=g.findall(f"./{C('selectionEntries')}/{C('selectionEntry')}")
 names=[x.get("name") for x in links+sels]
 print(g.get("id"),"hidden",g.get("hidden"),"cons",cons(g),"links",len(links),"sels",len(sels),"names",names)
 print(" PATH",chain(g))
 print(" MOD",mods(g)[:2500])
 if set(names)!=set(["Stormwing","Deathwing","Dreadwing","Ironwing","Firewing","Ravenwing"]):bad.append((g.get("id"),names))
print("BAD_WING_GROUPS",bad)

print("\\n==== DARK ANGELS ARMOURY GROUPS ====")
for g in r.iter(C("selectionEntryGroup")):
 n=(g.get("name") or "")
 if "Dark Angels Armoury" not in n:continue
 links=g.findall(f"./{C('entryLinks')}/{C('entryLink')}")
 sels=g.findall(f"./{C('selectionEntries')}/{C('selectionEntry')}")
 print(g.get("id"),"|",n,"links",len(links),"sels",len(sels),"cons",cons(g),"path",chain(g))
 for x in links[:20]:print(" LINK",x.get("id"),x.get("name"),"->",x.get("targetId"),"hidden",x.get("hidden"))

print("\\n==== DA SPECIAL ROOTS ====")
for e in r.findall(f"./{C('selectionEntries')}/{C('selectionEntry')}"):
 direct_names=[x.get("name") or "" for x in e.findall(f"./{C('rules')}/{C('rule')}")]+[x.get("name") or "" for x in e.findall(f"./{C('infoLinks')}/{C('infoLink')}")]
 if any(x=="Legiones Astartes (Dark Angels)" for x in direct_names) or (e.get("id") or "").startswith("r41-unit-i-"):
  print(e.get("id"),"|",e.get("name"),"| hidden",e.get("hidden"),"| rules",direct_names)
  for g in e.findall(f"./{C('selectionEntryGroups')}/{C('selectionEntryGroup')}"):
   if (g.get("name") or "")=="Hexagrammaton Wing":
    print("  HAS SELECTABLE WING",g.get("id"))

print("\\n==== DA RITES ====")
for e in r.iter(C("selectionEntry")):
 if (e.get("id") or "").startswith("r25-rite-i-") or (e.get("id") or "").startswith("da22-rite-"):
  print(e.get("id"),"|",e.get("name"),"| hidden",e.get("hidden"),"| cons",cons(e),"| mods",mods(e)[:4000])

print("\\n==== BROKEN DA TARGETS ====")
allids=set(ids)
for e in r.iter():
 p=" ".join((x[2] or "") for x in chain(e)).lower()
 if "dark angels" not in p and "hexagrammaton" not in p and "da-" not in (e.get("id") or ""):continue
 for l in e.findall(f"./{C('entryLinks')}/{C('entryLink')}"):
  if l.get("targetId") not in allids: print("BROKEN",l.get("id"),l.get("targetId"),chain(l))

print("\\n==== MISPLACED LINKS GLOBAL ====")
badmis=[]
for box in r.iter(C("selectionEntries")):
 for x in list(box):
  if x.tag!=C("selectionEntry"):badmis.append((x.tag.split("}")[-1],x.get("id"),x.get("name")))
print("COUNT",len(badmis),badmis[:50])
