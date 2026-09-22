import xml.etree.ElementTree as ET, collections, re
NS="http://www.battlescribe.net/schema/catalogueSchema"; C=lambda t:f"{{{NS}}}{t}"
r=ET.parse("Legiones Astartes.cat").getroot(); pm={c:p for p in r.iter() for c in p}; ids={x.get("id"):x for x in r.iter() if x.get("id")}
def cons(e): return [(x.get("id"),x.get("type"),x.get("value"),x.get("scope"),x.get("field")) for x in e.findall(f"./{C('constraints')}/{C('constraint')}")]
def cats(e): return [(x.get("id"),x.get("name"),x.get("targetId"),x.get("primary")) for x in e.findall(f"./{C('categoryLinks')}/{C('categoryLink')}")]
def mods(e):
 m=e.find(C("modifiers"));return ET.tostring(m,encoding="unicode") if m is not None else ""
def info(e): return [(x.get("id"),x.get("name"),x.get("targetId"),x.get("type"),x.get("hidden")) for x in e.findall(f"./{C('infoLinks')}/{C('infoLink')}")]
def rules(e): return [(x.get("id"),x.get("name"),(x.findtext(C("description")) or "")[:220]) for x in e.findall(f"./{C('rules')}/{C('rule')}")]
print("REV",r.get("revision"),"GST",r.get("gameSystemRevision"))
for gid in ["config-legion","config-allegiance","config-rites"]:
 g=ids.get(gid)
 print("\\nGROUP/ID",gid, "exists", bool(g))
 if g:
  print(g.tag.split("}")[-1],g.get("id"),g.get("name"),"hidden",g.get("hidden"),"cons",cons(g),"mods",mods(g)[:4000])
  for ch in list(g):
   if ch.tag in (C("selectionEntry"),C("entryLink"),C("selectionEntryGroup")):
    print(" CHILD",ch.tag.split("}")[-1],ch.get("id"),ch.get("name"),ch.get("targetId"),"hidden",ch.get("hidden"),"cons",cons(ch),"mods",mods(ch)[:1200])
print("\\nLEGION ENTRIES")
for i in ["i","ii","iii","iv","v","vi","vii","viii","ix","x","xi","xii","xiii","xiv","xv","xvi","xvii","xviii","xix","xx"]:
 e=ids.get("legion-"+i)
 if e: print(e.get("id"),e.get("name"),"hidden",e.get("hidden"),"cons",cons(e),"info",info(e),"rules",rules(e))
print("\\nROOT ENTRY EXAMPLES")
for eid in ["hq-praetor","hq-centurion","tactical-unit","veteran-unit","recon-unit","transport-rhino","hs-predator"]:
 e=ids.get(eid)
 print("\\n",eid, bool(e))
 if e:
  print("name",e.get("name"),"type",e.get("type"),"hidden",e.get("hidden"),"cats",cats(e),"cons",cons(e),"mods",mods(e)[:4000])
  print("info",info(e)); print("rules",rules(e))
  for g in e.findall(f"./{C('selectionEntryGroups')}/{C('selectionEntryGroup')}"):
   print(" GROUP",g.get("id"),g.get("name"),"hidden",g.get("hidden"),"cons",cons(g),"mods",mods(g)[:1200])
print("\\nLEGION SPECIFIC ROOT COUNTS")
co=collections.Counter()
examples=collections.defaultdict(list)
for e in r.findall(f"./{C('selectionEntries')}/{C('selectionEntry')}"):
 eid=e.get("id") or ""
 m=re.match(r"r41-unit-([ivxlcdm]+)-",eid)
 if m:
  co[m.group(1)]+=1;examples[m.group(1)].append((eid,e.get("name")))
for k,v in sorted(co.items()):print(k,v,examples[k][:20])
