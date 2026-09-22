import xml.etree.ElementTree as ET
NS="http://www.battlescribe.net/schema/catalogueSchema"; C=lambda t:f"{{{NS}}}{t}"
r=ET.parse("Legiones Astartes.cat").getroot(); ids={x.get("id"):x for x in r.iter() if x.get("id")}; pm={c:p for p in r.iter() for c in p}
def cons(e):return [(x.get("id"),x.get("type"),x.get("value"),x.get("scope"),x.get("field")) for x in e.findall(f"./{C('constraints')}/{C('constraint')}")]
def mods(e):
 m=e.find(C("modifiers"));return ET.tostring(m,encoding="unicode") if m is not None else ""
def dump(e,depth=0,maxdepth=8):
 ind="  "*depth
 print(f"{ind}{e.tag.split('}')[-1]} id={e.get('id')} name={e.get('name')} type={e.get('type')} hidden={e.get('hidden')} default={e.get('defaultAmount')} target={e.get('targetId')} cons={cons(e)}")
 if mods(e):print(ind+" MODS "+mods(e))
 for il in e.findall(f"./{C('infoLinks')}/{C('infoLink')}"):print(ind+" INFO",il.get("id"),il.get("name"),"->",il.get("targetId"),"hidden",il.get("hidden"),"mods",mods(il))
 if depth>=maxdepth:return
 for tag in ("selectionEntries","selectionEntryGroups","entryLinks"):
  p=e.find(C(tag))
  if p is not None:
   for x in list(p):dump(x,depth+1,maxdepth)

v=ids["veteran-unit"]
print("REV",r.get("revision"),"GST",r.get("gameSystemRevision"))
print("\\n==== VETERAN FULL PSYCHIC-RELATED ====")
for g in v.findall(f"./{C('selectionEntryGroups')}/{C('selectionEntryGroup')}"):
 n=(g.get("name") or "").lower(); gid=g.get("id") or ""
 if any(k in n for k in ["prosperine","psychic","cult","brotherhood"]) or "ts-" in gid:
  dump(g,0,8)

print("\\n==== VETERAN TS ASSIGNMENTS / BROTHERHOOD SELECTORS ====")
for e in v.iter():
 n=(e.get("name") or "").lower(); eid=e.get("id") or ""
 if "thousand sons" in n or "brotherhood" in n or eid.startswith("r62-shat-assign-") or "prosperine" in n:
  dump(e,0,3)

print("\\n==== XV ASSIGNMENT ANCESTRY ====")
for e in v.iter(C("selectionEntry")):
 if e.get("id")=="r62-shat-assign-2a678f656c73" or (e.get("name") or "")=="Thousand Sons":
  p=e
  while p is not None:
   print(p.tag.split("}")[-1],p.get("id"),p.get("name"),p.get("hidden"),cons(p),mods(p))
   p=pm.get(p)

print("\\n==== CURRENT POWER TARGET NAMES ====")
for g in v.iter(C("selectionEntryGroup")):
 if "Psychic Brotherhood" in (g.get("name") or ""):
  for l in g.iter(C("entryLink")):
   t=ids.get(l.get("targetId"))
   print(l.get("id"),l.get("name"),"->",l.get("targetId"),"targetname",t.get("name") if t is not None else None,"hidden",l.get("hidden"),"mods",mods(l))
