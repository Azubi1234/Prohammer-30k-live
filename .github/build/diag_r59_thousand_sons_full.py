import xml.etree.ElementTree as ET, collections, re
CNS="http://www.battlescribe.net/schema/catalogueSchema"; C=lambda t:f"{{{CNS}}}{t}"
r=ET.parse("Legiones Astartes.cat").getroot(); ids={x.get("id"):x for x in r.iter() if x.get("id")}; pm={c:p for p in r.iter() for c in p}
def cost(e):return [(x.get("typeId"),x.get("value")) for x in e.findall(f"./{C('costs')}/{C('cost')}")]
def cons(e):return [(x.get("id"),x.get("type"),x.get("value"),x.get("scope"),x.get("field")) for x in e.findall(f"./{C('constraints')}/{C('constraint')}")]
def mods(e):
 m=e.find(C("modifiers"));return ET.tostring(m,encoding="unicode") if m is not None else ""
def chain(e,lim=8):
 out=[];p=e
 while p is not None and len(out)<lim:
  out.append(f"{p.tag.split('}')[-1]}:{p.get('id')}:{p.get('name')}");p=pm.get(p)
 return " > ".join(out)
def dump(e,depth=0,maxdepth=6):
 ind="  "*depth
 print(f"{ind}{e.tag.split('}')[-1]} id={e.get('id')} name={e.get('name')} type={e.get('type')} hidden={e.get('hidden')} default={e.get('defaultAmount')} cost={cost(e)} cons={cons(e)}")
 if mods(e):print(ind+" MODS "+mods(e)[:4500])
 for il in e.findall(f"./{C('infoLinks')}/{C('infoLink')}"): print(ind+" INFO",il.get("id"),il.get("name"),"->",il.get("targetId"),"hidden",il.get("hidden"))
 for rr in e.findall(f"./{C('rules')}/{C('rule')}"): print(ind+" RULE",rr.get("id"),rr.get("name"),":",(rr.findtext(C("description")) or "")[:450].replace("\\n"," | "))
 if depth>=maxdepth:return
 for tag in ["selectionEntries","selectionEntryGroups","entryLinks"]:
  p=e.find(C(tag))
  if p is not None:
   for x in list(p):dump(x,depth+1,maxdepth)

print("REV",r.get("revision"),"GST",r.get("gameSystemRevision"))
targets=["legion-xv","hq-praetor","hq-centurion","veteran-unit","terminator-unit"]
for eid in targets:
 e=ids.get(eid)
 if e:
  print("\\n====",eid,e.get("name"),"====");dump(e,0,7)

# Pride Veteran copy and all TS special roots
print("\\n==== PRIDE VETERAN COPIES ====")
for e in r.iter(C("selectionEntry")):
 if "Veteran" in (e.get("name") or "") and "Pride" in chain(e):
  dump(e,0,5)
print("\\n==== XV TOP ROOTS ====")
for e in r.findall(f"./{C('selectionEntries')}/{C('selectionEntry')}"):
 eid=e.get("id") or ""; n=(e.get("name") or "").lower()
 if eid.startswith("r41-unit-xv-") or any(k in n for k in ["ahriman","phosis","amon","hathor","sanakht","sekhemet","sekhemet","khenetai","ammitara","numerologist","osiron","magnus"]):
  print("\\nTOP",eid,e.get("name"));dump(e,0,5)

# Cult/power/brotherhood/TS hidden content anywhere
print("\\n==== TS CULT/PSYCHIC/BROTHERHOOD MATCHES ====")
for e in r.iter():
 n=(e.get("name") or "").lower(); eid=e.get("id") or ""
 if any(k in n for k in ["cult","pavoni","raptora","corvidae","athanaean","pyrae","brotherhood","psychic discipline","biomancy","divination","pyromancy","telekinesis","telepathy"]):
  ch=chain(e)
  if any(k in ch.lower() for k in ["thousand sons","legion-xv","hq-centurion","hq-praetor","veteran","terminator","r41-unit-xv"]):
   print(e.tag.split("}")[-1],eid,e.get("name"),"hidden",e.get("hidden"),"cons",cons(e),"mods",mods(e)[:2000],"chain",ch)

# Veteran melee option groups exact
for rootid in ["veteran-unit"]:
 e=ids[rootid]
 print("\\n==== VETERAN OPTION GROUPS ====")
 for g in e.iter(C("selectionEntryGroup")):
  n=(g.get("name") or "").lower()
  if any(k in n for k in ["melee","weapon","replacement","combat","veteran"]):
   print("GROUP",g.get("id"),g.get("name"),"cons",cons(g),"mods",mods(g)[:3000])
   for x in g.findall(f"./{C('entryLinks')}/{C('entryLink')}"):print(" LINK",x.get("id"),x.get("name"),x.get("targetId"),cost(x),cons(x),mods(x)[:1000])
   for x in g.findall(f"./{C('selectionEntries')}/{C('selectionEntry')}"):print(" OPT",x.get("id"),x.get("name"),cost(x),cons(x),mods(x)[:1000])
