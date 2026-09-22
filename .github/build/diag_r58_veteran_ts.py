import xml.etree.ElementTree as ET
NS="http://www.battlescribe.net/schema/catalogueSchema"; C=lambda t:f"{{{NS}}}{t}"
r=ET.parse("Legiones Astartes.cat").getroot(); ids={x.get("id"):x for x in r.iter() if x.get("id")}
def cost(e):return [(x.get("typeId"),x.get("value")) for x in e.findall(f"./{C('costs')}/{C('cost')}")]
def con(e):return [(x.get("id"),x.get("type"),x.get("value"),x.get("scope"),x.get("field")) for x in e.findall(f"./{C('constraints')}/{C('constraint')}")]
def mods(e):
 m=e.find(C("modifiers"));return ET.tostring(m,encoding="unicode") if m is not None else ""
def dump(e,depth=0,maxdepth=7):
 ind="  "*depth
 print(f"{ind}{e.tag.split('}')[-1]} id={e.get('id')} name={e.get('name')} type={e.get('type')} hidden={e.get('hidden')} default={e.get('defaultAmount')} cost={cost(e)} cons={con(e)}")
 if mods(e): print(ind+" MODS "+mods(e)[:7000])
 for il in e.findall(f"./{C('infoLinks')}/{C('infoLink')}"):print(ind+" INFO",il.get("id"),il.get("name"),"->",il.get("targetId"),il.get("type"),"hidden",il.get("hidden"))
 for rr in e.findall(f"./{C('rules')}/{C('rule')}"):print(ind+" RULE",rr.get("id"),rr.get("name"),":",(rr.findtext(C("description")) or "")[:500].replace("\\n"," | "))
 if depth>=maxdepth:return
 for tag in ["selectionEntries","selectionEntryGroups","entryLinks"]:
  p=e.find(C(tag))
  if p is not None:
   for x in list(p):dump(x,depth+1,maxdepth)

print("REV",r.get("revision"),"GST",r.get("gameSystemRevision"))
for eid in ["veteran-unit","legion-xv","r25-rite-xv-1-the-fellowships-of-prospero","hq-centurion","terminator-unit"]:
 e=ids.get(eid)
 print("\\n====",eid,"exists",bool(e),"====")
 if e: dump(e,0,8)

# Any Brotherhood/Cult entries anywhere under veterans or TS configuration.
print("\\n==== BROTHERHOOD/CULT MATCHES ====")
for e in r.iter():
 n=(e.get("name") or "").lower(); eid=e.get("id") or ""
 if any(k in n for k in ["brotherhood of psykers","prosperine cult","pavoni","raptora","corvidae","athanaean","pyrae"]) and ("veteran" in n or "veteran" in " ".join((p.get("name") or "") for p in [])):
  print(e.tag.split("}")[-1],eid,e.get("name"))
# Print all entries with Brotherhood name and ancestry.
pm={c:p for p in r.iter() for c in p}
def chain(e):
 a=[];p=e
 while p is not None and len(a)<10:
  a.append((p.get("id"),p.get("name")));p=pm.get(p)
 return a
for e in r.iter():
 if "brotherhood of psykers" in (e.get("name") or "").lower():
  print("BROTHER",e.tag.split("}")[-1],e.get("id"),e.get("name"),"chain",chain(e),"cost",cost(e),"cons",con(e),"mods",mods(e)[:2500])
