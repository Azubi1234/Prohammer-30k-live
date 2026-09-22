import xml.etree.ElementTree as ET, re
NS="http://www.battlescribe.net/schema/catalogueSchema"; C=lambda t:f"{{{NS}}}{t}"
r=ET.parse("Legiones Astartes.cat").getroot(); ids={x.get("id"):x for x in r.iter() if x.get("id")}
def cons(e):return [(x.get("id"),x.get("type"),x.get("value"),x.get("scope"),x.get("field")) for x in e.findall(f"./{C('constraints')}/{C('constraint')}")]
def costs(e):return [(x.get("typeId"),x.get("value")) for x in e.findall(f"./{C('costs')}/{C('cost')}")]
def mods(e):
 m=e.find(C("modifiers"));return ET.tostring(m,encoding="unicode") if m is not None else ""
def small(e):
 return f"{e.tag.split('}')[-1]} id={e.get('id')} name={e.get('name')} type={e.get('type')} hidden={e.get('hidden')} default={e.get('defaultAmount')} cost={costs(e)} cons={cons(e)} mods={mods(e)[:5000]}"
def direct_groups(e):
 for g in e.findall(f"./{C('selectionEntryGroups')}/{C('selectionEntryGroup')}"):
  print("GROUP",small(g))
  for tag in ("selectionEntries","entryLinks"):
   cc=g.find(C(tag))
   if cc is not None:
    for x in list(cc): print(" OPT",small(x),"target",x.get("targetId"))
def psychic_named(e):
 s=" ".join([(x.get("name") or "") for x in e.iter()]).lower()
 return any(k in s for k in ["prosperine cult","psychic","psyker","brotherhood"])

print("REV",r.get("revision"),"GST",r.get("gameSystemRevision"))
for eid in ["hq-centurion","hq-praetor","veteran-unit","terminator-unit"]:
 print("\\n====",eid,ids[eid].get("name"),"====")
 direct_groups(ids[eid])
 print("DIRECT RULES",[(x.get("name"),(x.findtext(C("description")) or "")[:300]) for x in ids[eid].findall(f"./{C('rules')}/{C('rule')}")])
 print("DIRECT INFOS",[(x.get("name"),x.get("targetId"),x.get("hidden")) for x in ids[eid].findall(f"./{C('infoLinks')}/{C('infoLink')}")])

print("\\n==== VETERAN MODELS ====")
v=ids["veteran-unit"]
for x in v.iter(C("selectionEntry")):
 if x.get("type")=="model": print(small(x))
print("\\n==== VETERAN RELEVANT GROUPS ====")
for g in v.iter(C("selectionEntryGroup")):
 n=(g.get("name") or "").lower()
 if any(k in n for k in ["melee","combat","weapon","specialist","armoury","veteran"]):
  print("G",small(g))
  for x in list(g):
   if x.tag in (C("selectionEntry"),C("entryLink")): print(" O",small(x),"target",x.get("targetId"))

print("\\n==== ALL TS PSYCHIC/CULT ROOTS ====")
for e in r.iter(C("selectionEntry")):
 gs=e.findall(f"./{C('selectionEntryGroups')}/{C('selectionEntryGroup')}")
 gn=[g.get("name") or "" for g in gs]
 if any("Prosperine Cult" in n or "Psychic" in n for n in gn):
  print(e.get("id"),"|",e.get("name"),"|",gn)

print("\\n==== XV ROOTS MISSING CULT/POWER DIRECT GROUPS ====")
for e in r.findall(f"./{C('selectionEntries')}/{C('selectionEntry')}"):
 txt=" ".join([(x.get("name") or "") for x in e.iter(C("rule"))]+[(x.get("name") or "") for x in e.iter(C("infoLink"))])
 if "Legiones Astartes (Thousand Sons)" not in txt:continue
 gs=[g.get("name") or "" for g in e.findall(f"./{C('selectionEntryGroups')}/{C('selectionEntryGroup')}")]
 is_psy=("Psyker" in txt or "Mastery Level" in txt or e.get("id") in ("hq-centurion","hq-praetor"))
 if is_psy:
  print(e.get("id"),e.get("name"),"cult",any("Prosperine Cult" in x for x in gs),"power",any("Psychic" in x and "Power" in x for x in gs),"groups",gs)
