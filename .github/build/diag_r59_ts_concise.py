from pathlib import Path
import xml.etree.ElementTree as ET, collections, re
NS="http://www.battlescribe.net/schema/catalogueSchema"; C=lambda t:f"{{{NS}}}{t}"
r=ET.parse("Legiones Astartes.cat").getroot(); ids={x.get("id"):x for x in r.iter() if x.get("id")}; pm={c:p for p in r.iter() for c in p}
def cost(e):return [(x.get("typeId"),x.get("value")) for x in e.findall(f"./{C('costs')}/{C('cost')}")]
def cons(e):return [(x.get("id"),x.get("type"),x.get("value"),x.get("scope"),x.get("field")) for x in e.findall(f"./{C('constraints')}/{C('constraint')}")]
def mods(e):
 m=e.find(C("modifiers"));return ET.tostring(m,encoding="unicode") if m is not None else ""
def anc(e,lim=7):
 out=[];p=e
 while p is not None and len(out)<lim:
  out.append(f"{p.tag.split('}')[-1]}:{p.get('id')}:{p.get('name')}");p=pm.get(p)
 return " > ".join(out)
lines=[f"REV={r.get('revision')} GST={r.get('gameSystemRevision')}"]
# exact TS cult groups and Brotherhood groups anywhere
patterns=["r45-cult-","r19-ts-","r45-ts-brother","r45-ts-powers","r45-ts-discipline","r45-ts-cult","r56-ts","r57-ts","r58-ts"]
for p in patterns:
 arr=[e for e in r.iter() if p in (e.get("id") or "")]
 lines+=["",f"== PATTERN {p} count={len(arr)} =="]
 for e in arr[:250]:
  lines.append(f"{e.tag.split('}')[-1]} {e.get('id')} | {e.get('name')} | hidden={e.get('hidden')} default={e.get('defaultAmount')} cost={cost(e)} cons={cons(e)} mods={mods(e)[:2500]} | {anc(e)}")

# Centurion/Praetor direct TS-related descendants
for rid in ["hq-praetor","hq-centurion","veteran-unit","terminator-unit","r35-pride-veteran-veteran-unit"]:
 root=ids[rid];lines+=["",f"== ROOT {rid} {root.get('name')} =="]
 for e in root.iter():
  n=(e.get("name") or "").lower(); eid=e.get("id") or ""
  if any(k in n for k in ["prosperine","cult","brotherhood","biomancy","divination","pyromancy","telekinesis","telepathy","psychic","mastery"]) or any(p in eid for p in patterns):
   lines.append(f"{e.tag.split('}')[-1]} {eid} | {e.get('name')} | hidden={e.get('hidden')} default={e.get('defaultAmount')} cost={cost(e)} cons={cons(e)} mods={mods(e)[:3500]}")

# Veteran melee group + model selector
v=ids["veteran-unit"];lines+=["","== VETERAN MELEE =="]
for e in v.findall(f"./{C('selectionEntries')}/{C('selectionEntry')}"):
 lines.append(f"MODEL/UPG {e.get('id')} {e.get('name')} default={e.get('defaultAmount')} cost={cost(e)} cons={cons(e)}")
for g in v.iter(C("selectionEntryGroup")):
 if "close combat weapon replacements" in (g.get("name") or "").lower() or "melee" in (g.get("name") or "").lower():
  lines.append(f"GROUP {g.get('id')} {g.get('name')} cons={cons(g)} mods={mods(g)}")
  for x in list(g):
   if x.tag in (C("entryLink"),C("selectionEntry")): lines.append(f"  OPT {x.tag.split('}')[-1]} {x.get('id')} {x.get('name')} target={x.get('targetId')} cost={cost(x)} cons={cons(x)} mods={mods(x)[:1000]}")

# TS special unit cult/powers visibility
lines+=["","== XV ROOT CULT/POWER PRESENCE =="]
for e in r.findall(f"./{C('selectionEntries')}/{C('selectionEntry')}"):
 if (e.get("id") or "").startswith("r41-unit-xv-"):
  matches=[x for x in e.iter() if any(k in (x.get("name") or "").lower() for k in ["cult","pavoni","raptora","corvidae","athanaean","pyrae","psychic","biomancy","divination","pyromancy","telekinesis","telepathy","brotherhood"])]
  lines.append(f"{e.get('id')} {e.get('name')} MATCHES={len(matches)}")
  for x in matches[:80]:lines.append(f"  {x.tag.split('}')[-1]} {x.get('id')} | {x.get('name')} hidden={x.get('hidden')} cons={cons(x)} mods={mods(x)[:1800]}")
Path("inspection-r59-ts-concise.txt").write_text("\n".join(lines)+"\n",encoding="utf-8")
print("\n".join(lines))
