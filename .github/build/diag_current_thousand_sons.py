from pathlib import Path
import xml.etree.ElementTree as ET, collections
CAT=Path("Legiones Astartes.cat"); GST=Path("Prohammer 30k.gst")
CNS="http://www.battlescribe.net/schema/catalogueSchema"; GNS="http://www.battlescribe.net/schema/gameSystemSchema"
C=lambda t:f"{{{CNS}}}{t}"; G=lambda t:f"{{{GNS}}}{t}"
r=ET.parse(CAT).getroot(); g=ET.parse(GST).getroot(); ids={x.get("id"):x for x in r.iter() if x.get("id")}
pm={c:p for p in r.iter() for c in p}
def cons(e): return [(x.get("id"),x.get("type"),x.get("value"),x.get("scope"),x.get("field")) for x in e.findall(f"./{C('constraints')}/{C('constraint')}")]
def mods(e):
 m=e.find(C("modifiers")); return ET.tostring(m,encoding="unicode") if m is not None else ""
def path(e):
 out=[];p=e
 while p is not None and len(out)<8:
  out.append(f"{p.tag.split('}')[-1]}:{p.get('id')}:{p.get('name')}");p=pm.get(p)
 return " > ".join(out)
def dump(i):
 e=ids.get(i); print("\\n====",i,"====")
 if e is None: print("MISSING"); return
 print(e.tag.split("}")[-1],e.get("id"),e.get("name"),"hidden",e.get("hidden"),"default",e.get("defaultAmount"),"cons",cons(e))
 print("PATH",path(e))
 print("MODS",mods(e)[:12000])
 if e.tag==C("selectionEntryGroup"):
  ses=e.find(C("selectionEntries"))
  if ses is not None:
   for x in ses.findall(C("selectionEntry")):
    print(" CHOICE",x.get("id"),x.get("name"),"hidden",x.get("hidden"),"default",x.get("defaultAmount"),"cons",cons(x),"mods",mods(x)[:3000])
 if e.tag==C("selectionEntry"):
  for sg in e.findall(f"./{C('selectionEntryGroups')}/{C('selectionEntryGroup')}"):
   if any(k in (sg.get("name") or "").lower() for k in ["cult","discipline","psychic","brotherhood"]):
    print(" GROUP",sg.get("id"),sg.get("name"),"hidden",sg.get("hidden"),"cons",cons(sg),"mods",mods(sg)[:6000])
    ses=sg.find(C("selectionEntries"))
    if ses is not None:
     for x in ses.findall(C("selectionEntry")):
      print("   CHOICE",x.get("id"),x.get("name"),"hidden",x.get("hidden"),"cons",cons(x),"mods",mods(x)[:2500])

print("CAT",r.get("revision"),"GSTDEP",r.get("gameSystemRevision"),"GST",g.get("revision"))
for i in [
"legion-xv",
"r45-cult-hq-praetor","r19-ts-praetor-disciplines",
"r45-cult-hq-centurion","r19-ts-centurion-disciplines",
"r45-cult-tactical-unit","r19-ts-tactical-brotherhood-disciplines","r19-ts-tactical-brotherhood-powers","r45-tactical-ts-brother",
"r45-cult-veteran-unit","r19-ts-veteran-unit-brotherhood-disciplines",
"r45-cult-terminator-unit","r19-ts-terminator-unit-brotherhood-disciplines",
"r45-cult-r41-unit-xv-0-sekhmet-terminator-cabal","r19-ts-sekhmet-disciplines",
"r45-cult-r41-unit-xv-2-ammitara-occult-intercession-cabal","r19-ts-ammitara-disciplines"
]: dump(i)

# Find all cult/discipline groups current.
print("\\n==== ALL CULT/DISCIPLINE GROUPS ====")
for e in r.iter(C("selectionEntryGroup")):
 n=(e.get("name") or "").lower()
 if "cult" in n or "discipline" in n or "psychic power" in n:
  print(e.get("id"),"|",e.get("name"),"| hidden",e.get("hidden"),"| cons",cons(e),"| path",path(e))

# Find broken childIds in TS-related modifiers.
print("\\n==== BROKEN TS CONDITION CHILD IDS ====")
allids=set(ids)
for e in r.iter():
 eid=e.get("id") or ""
 ptxt=path(e).lower()
 if "thousand sons" not in ptxt and "r19-ts" not in eid and "r29-" not in eid and "r45-cult" not in eid: continue
 for c in e.iter(C("condition")):
  cid=c.get("childId")
  if cid and cid not in allids:
   print("BROKEN",eid,cid,path(e))

# shared psychic power group existence in GST/CAT
print("\\n==== GST PSYCHIC ====")
for e in g.iter():
 n=(e.get("name") or "").lower()
 if any(k in n for k in ["biomancy","divination","pyromancy","telekinesis","telepathy"]):
  print(e.tag.split("}")[-1],e.get("id"),e.get("name"),e.get("hidden"))
