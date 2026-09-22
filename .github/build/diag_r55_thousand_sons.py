import xml.etree.ElementTree as ET, re
NS="http://www.battlescribe.net/schema/catalogueSchema"; C=lambda t:f"{{{NS}}}{t}"
r=ET.parse("Legiones Astartes.cat").getroot(); ids={x.get("id"):x for x in r.iter() if x.get("id")}; pm={c:p for p in r.iter() for c in p}
def cons(e):return [(x.get("id"),x.get("type"),x.get("value"),x.get("scope"),x.get("field")) for x in e.findall(f"./{C('constraints')}/{C('constraint')}")]
def cats(e):return [(x.get("id"),x.get("name"),x.get("targetId"),x.get("primary")) for x in e.findall(f"./{C('categoryLinks')}/{C('categoryLink')}")]
def mods(e):
 m=e.find(C("modifiers"));return ET.tostring(m,encoding="unicode") if m is not None else ""
def infos(e):return [(x.get("id"),x.get("name"),x.get("targetId"),x.get("type"),x.get("hidden")) for x in e.findall(f"./{C('infoLinks')}/{C('infoLink')}")]
def rules(e):return [(x.get("id"),x.get("name"),(x.findtext(C("description")) or "")[:250]) for x in e.findall(f"./{C('rules')}/{C('rule')}")]
print("REV",r.get("revision"),"GST",r.get("gameSystemRevision"))
for eid in ["legion-xv","config-legion","allegiance-loyalist","allegiance-traitor"]:
 e=ids.get(eid); print("\\n====",eid,"====",bool(e))
 if e:
  print("name",e.get("name"),"type",e.get("type"),"hidden",e.get("hidden"),"cons",cons(e),"cats",cats(e),"mods",mods(e)[:5000],"infos",infos(e),"rules",rules(e))
  if e.tag==C("selectionEntryGroup"):
   for x in e.findall(f"./{C('selectionEntries')}/{C('selectionEntry')}"):print(" child",x.get("id"),x.get("name"),x.get("hidden"),cons(x),mods(x)[:1000])
print("\\n=== TOP-LEVEL TS MATCHES ===")
for e in r.findall(f"./{C('selectionEntries')}/{C('selectionEntry')}"):
 eid=e.get("id") or ""; n=(e.get("name") or "").lower()
 if "xv" in eid and "xviii" not in eid or any(k in n for k in ["khenetai","sekmet","ammitara","osiron","magnus","ahriman","phosis","hathor","sanakht","thousand sons"]):
  print(eid,"|",e.get("name"),"| hidden",e.get("hidden"),"| cons",cons(e),"| cats",cats(e),"| mods",mods(e)[:7000])
print("\\n=== TS RITES ===")
for e in r.iter(C("selectionEntry")):
 n=(e.get("name") or "").lower(); eid=e.get("id") or ""
 if ("thousand sons rite" in n or "guard of the crimson king" in n or "axis of dissolution" in n or ("rite" in eid and "xv" in eid and "xviii" not in eid)):
  print(eid,e.get("name"),"hidden",e.get("hidden"),cons(e),mods(e)[:5000])
print("\\n=== TS SHARED/ARMOURY ===")
for e in r.iter(C("selectionEntry")):
 eid=e.get("id") or ""
 if eid.startswith(("r46-ts-","r18-ts-","r41-unit-xv-")):
  print(eid,e.get("name"),"type",e.get("type"),"hidden",e.get("hidden"),"cons",cons(e),"mods",mods(e)[:2500])
