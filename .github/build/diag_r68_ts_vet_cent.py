import xml.etree.ElementTree as ET, collections
NS="http://www.battlescribe.net/schema/catalogueSchema"; C=lambda t:f"{{{NS}}}{t}"
r=ET.parse("Legiones Astartes.cat").getroot(); ids={x.get("id"):x for x in r.iter() if x.get("id")}; pm={c:p for p in r.iter() for c in p}
def cons(e): return [(x.get("id"),x.get("type"),x.get("value"),x.get("scope"),x.get("field"),x.get("includeChildSelections")) for x in e.findall(f"./{C('constraints')}/{C('constraint')}")]
def mods(e):
 m=e.find(C("modifiers")); return ET.tostring(m,encoding="unicode") if m is not None else ""
def costs(e): return [(x.get("typeId"),x.get("value")) for x in e.findall(f"./{C('costs')}/{C('cost')}")]
def children(e):
 for tag in ("selectionEntries","selectionEntryGroups","entryLinks"):
  p=e.find(C(tag))
  if p is not None:
   for x in list(p): yield x
def line(e,depth=0):
 return "  "*depth+f"{e.tag.split('}')[-1]} id={e.get('id')} name={e.get('name')} type={e.get('type')} hidden={e.get('hidden')} default={e.get('defaultAmount')} target={e.get('targetId')} cost={costs(e)} cons={cons(e)} mods={mods(e)}"
def dump(e,depth=0,maxd=8):
 print(line(e,depth))
 if depth>=maxd:return
 for x in children(e): dump(x,depth+1,maxd)

print("REV",r.get("revision"),"GST",r.get("gameSystemRevision"))

v=ids["veteran-unit"]
print("\\n==== VETERAN TOP CHILDREN ====")
for x in children(v): print(line(x,1))

print("\\n==== VETERAN MELEE-RELATED ====")
for e in v.iter():
 n=(e.get("name") or "").lower(); eid=e.get("id") or ""
 if any(k in n for k in ["melee","power weapon","power fist","thunder hammer","lightning claw","combat blade","chainsword","rending weapon"]) or "melee" in eid or "power-weapon" in eid:
  print(line(e,0))

print("\\n==== VETERAN SIZE SELECTORS ====")
for e in v.iter(C("selectionEntry")):
 n=(e.get("name") or "").lower();eid=e.get("id") or ""
 if any(k in n for k in ["veteran","squad models","additional"]) or "veteran-included" in eid:
  print(line(e,0))

print("\\n==== VETERAN PSYCHIC GROUPS ====")
for g in v.iter(C("selectionEntryGroup")):
 n=(g.get("name") or "").lower();gid=g.get("id") or ""
 if any(k in n for k in ["psychic","prosperine","cult","brotherhood"]) or any(k in gid for k in ["ts-","cult","psy"]):
  dump(g,0,5)

print("\\n==== CENTURION TS PACKAGES ====")
cent=ids["hq-centurion"]
for e in cent.iter():
 n=(e.get("name") or "").lower();eid=e.get("id") or ""
 if any(k in n for k in ["thousand sons","prosperine","cult","psychic","biomancy","telekinesis","divination","telepathy","pyromancy"]) or "ts-cent" in eid:
  print(line(e,0))

print("\\n==== CENTURION ASSIGNMENT ====")
for e in cent.iter():
 if e.get("id")=="r62-shat-assign-2a678f656c73" or (e.get("name") or "")=="Thousand Sons":
  dump(e,0,6)

print("\\n==== LEGION XV CONFIG ====")
for e in [ids.get("legion-xv")]:
 if e: dump(e,0,3)
