from pathlib import Path
import xml.etree.ElementTree as ET, collections
NS="http://www.battlescribe.net/schema/catalogueSchema"; C=lambda t:f"{{{NS}}}{t}"
r=ET.parse("Legiones Astartes.cat").getroot(); ids={x.get("id"):x for x in r.iter() if x.get("id")}; pm={c:p for p in r.iter() for c in p}
def cons(e):return [(x.get("id"),x.get("type"),x.get("value"),x.get("scope"),x.get("field")) for x in e.findall(f"./{C('constraints')}/{C('constraint')}")]
def mods(e):
 m=e.find(C("modifiers"));return ET.tostring(m,encoding="unicode") if m is not None else ""
def cost(e):return [(x.get("typeId"),x.get("value")) for x in e.findall(f"./{C('costs')}/{C('cost')}")]
def report_root(rid):
 e=ids[rid]; out=[f"ROOT {rid} {e.get('name')} hidden={e.get('hidden')}"]
 for g in e.iter(C("selectionEntryGroup")):
  n=(g.get("name") or "").lower(); gid=g.get("id") or ""
  if any(k in n for k in ["cult","psychic","brotherhood","discipline","power","close combat weapon replacements"]) or "ts-" in gid or "cult-" in gid:
   out.append(f" GROUP {gid} | {g.get('name')} hidden={g.get('hidden')} cons={cons(g)} mods={mods(g)}")
   for x in list(g):
    if x.tag not in (C("selectionEntry"),C("entryLink")):continue
    out.append(f"   {x.tag.split('}')[-1]} {x.get('id')} | {x.get('name')} -> {x.get('targetId')} hidden={x.get('hidden')} default={x.get('defaultAmount')} cost={cost(x)} cons={cons(x)} mods={mods(x)} target_exists={x.get('targetId') in ids if x.get('targetId') else ''}")
 return out
lines=[f"REV {r.get('revision')}"]
for rid in ["legion-xv","hq-praetor","hq-centurion","veteran-unit","terminator-unit","r35-pride-veteran-veteran-unit"]:
 lines+=[""]+report_root(rid)
# shared cult targets
lines+=["","SHARED CULT TARGETS"]
for e in r.iter(C("selectionEntry")):
 n=(e.get("name") or "")
 if n in ["Pavoni","Raptora","Corvidae","Athanaeans","Pyrae"]:
  lines.append(f" {e.get('id')} {n} type={e.get('type')} hidden={e.get('hidden')} cons={cons(e)} mods={mods(e)}")
# veteran model selector and melee constraint math
v=ids["veteran-unit"]
lines+=["","VETERAN MODELS"]
for e in v.findall(f"./{C('selectionEntries')}/{C('selectionEntry')}"):
 lines.append(f" {e.get('id')} {e.get('name')} default={e.get('defaultAmount')} cost={cost(e)} cons={cons(e)}")
g=next(g for g in v.iter(C("selectionEntryGroup")) if g.get("name")=="Close Combat Weapon Replacements")
lines+=["MELEE GROUP",f" {g.get('id')} cons={cons(g)} mods={mods(g)}"]
Path("inspection-r59-ts-critical.txt").write_text("\n".join(lines)+"\n",encoding="utf-8")
print("\n".join(lines))
