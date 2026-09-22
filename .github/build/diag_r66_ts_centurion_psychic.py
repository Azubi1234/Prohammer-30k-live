import xml.etree.ElementTree as ET
NS="http://www.battlescribe.net/schema/catalogueSchema"; C=lambda t:f"{{{NS}}}{t}"
r=ET.parse("Legiones Astartes.cat").getroot(); ids={x.get("id"):x for x in r.iter() if x.get("id")}; pm={c:p for p in r.iter() for c in p}
def cons(e):return [(x.get("id"),x.get("type"),x.get("value"),x.get("scope"),x.get("field")) for x in e.findall(f"./{C('constraints')}/{C('constraint')}")]
def costs(e):return [(x.get("typeId"),x.get("value")) for x in e.findall(f"./{C('costs')}/{C('cost')}")]
def mods(e):
 m=e.find(C("modifiers"));return ET.tostring(m,encoding="unicode") if m is not None else ""
def dump(e,depth=0,maxdepth=6):
 ind="  "*depth
 print(f"{ind}{e.tag.split('}')[-1]} id={e.get('id')} name={e.get('name')} type={e.get('type')} hidden={e.get('hidden')} default={e.get('defaultAmount')} cost={costs(e)} cons={cons(e)}")
 if mods(e):print(ind+" MODS "+mods(e)[:6000])
 for il in e.findall(f"./{C('infoLinks')}/{C('infoLink')}"):print(ind+" INFO",il.get("id"),il.get("name"),"->",il.get("targetId"),il.get("type"),"hidden",il.get("hidden"),"mods",mods(il)[:2500])
 if depth>=maxdepth:return
 for tag in ["selectionEntries","selectionEntryGroups","entryLinks"]:
  p=e.find(C(tag))
  if p is not None:
   for x in list(p):
    if x.tag in [C("selectionEntry"),C("selectionEntryGroup"),C("entryLink")]:dump(x,depth+1,maxdepth)
print("REV",r.get("revision"),"GST",r.get("gameSystemRevision"))
for eid in ["hq-centurion","hq-praetor"]:
 print("\\n====",eid,"====");dump(ids[eid],0,8)
# Find all TS/cult/psychic objects under centurion by name/id
cent=ids["hq-centurion"]
print("\\n==== MATCHES UNDER CENTURION ====")
for e in cent.iter():
 n=(e.get("name") or "").lower(); i=e.get("id") or ""
 if any(k in n for k in ["cult","pavoni","raptora","corvid","athanae","pyrae","psychic","biomancy","telekinesis","divination","telepathy","pyromancy","psyker"]) or "ts-" in i or "r64" in i:
  print(e.tag.split("}")[-1],i,e.get("name"),"hidden",e.get("hidden"),"cons",cons(e),"mods",mods(e)[:4000])
# find shattered XV assignment IDs and references
print("\\n==== SHATTERED XV ====")
for e in r.iter():
 n=(e.get("name") or "").lower(); i=e.get("id") or ""
 if ("thousand sons" in n or "legion xv" in n) and ("shattered" in n or "r62" in i or "assign" in n):
  print(e.tag.split("}")[-1],i,e.get("name"),"hidden",e.get("hidden"),"cons",cons(e),"mods",mods(e)[:2500])
