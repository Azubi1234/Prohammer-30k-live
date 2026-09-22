import xml.etree.ElementTree as ET
NS="http://www.battlescribe.net/schema/catalogueSchema"; C=lambda t:f"{{{NS}}}{t}"
r=ET.parse("Legiones Astartes.cat").getroot(); ids={x.get("id"):x for x in r.iter() if x.get("id")}
def cons(e): return [(x.get("id"),x.get("type"),x.get("value"),x.get("scope")) for x in e.findall(f"./{C('constraints')}/{C('constraint')}")]
def modrows(e):
 out=[]
 ms=e.find(C("modifiers"))
 if ms is None:return out
 for m in ms.findall(C("modifier")):
  conds=[(x.get("type"),x.get("value"),x.get("scope"),x.get("childId")) for x in m.iter(C("condition"))]
  reps=[(x.get("value"),x.get("scope"),x.get("childId"),x.get("roundUp")) for x in m.iter(C("repeat"))]
  out.append((m.get("id"),m.get("type"),m.get("field"),m.get("value"),conds,reps))
 return out
def kids(g):
 out=[]
 for tag in ("selectionEntries","entryLinks","selectionEntryGroups"):
  cc=g.find(C(tag))
  if cc is not None:
   for x in list(cc): out.append((tag,x.get("id"),x.get("name"),x.get("targetId"),x.get("hidden"),cons(x),modrows(x)))
 return out
print("REV",r.get("revision"))
for eid in ["hq-centurion","hq-praetor","veteran-unit","terminator-unit"]:
 e=ids[eid];print("\\nROOT",eid,e.get("name"))
 for g in e.findall(f"./{C('selectionEntryGroups')}/{C('selectionEntryGroup')}"):
  n=(g.get("name") or "");gid=g.get("id") or ""
  if any(k in n.lower() for k in ["prosperine","psychic","melee","combat","specialist"]) or "ts-" in gid:
   print(" G",g.get("id"),g.get("name"),"hidden",g.get("hidden"),"cons",cons(g),"mods",modrows(g))
   for row in kids(g):
    print("  K",row[:6])
    # if local cult option, show nested groups beneath it
    xid=row[1]
    if xid in ids:
      x=ids[xid]
      for ng in x.findall(f"./{C('selectionEntryGroups')}/{C('selectionEntryGroup')}"):
       print("   NG",ng.get("id"),ng.get("name"),"hidden",ng.get("hidden"),"cons",cons(ng),"mods",modrows(ng))
       for q in kids(ng)[:20]: print("    NK",q[:6])
print("\\nPSYKER SHARED")
for x in r.iter(C("rule")):
 if "Psyker" in (x.get("name") or "") or "Mastery Level" in (x.get("name") or ""):
  print(x.get("id"),x.get("name"),(x.findtext(C("description")) or "")[:250])
