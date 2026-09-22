import xml.etree.ElementTree as ET
NS="http://www.battlescribe.net/schema/catalogueSchema"; C=lambda t:f"{{{NS}}}{t}"
r=ET.parse("Legiones Astartes.cat").getroot(); ids={x.get("id"):x for x in r.iter() if x.get("id")}
def con(e): return [(x.get("id"),x.get("type"),x.get("value"),x.get("scope"),x.get("field")) for x in e.findall(f"./{C('constraints')}/{C('constraint')}")]
def mods(e):
 m=e.find(C("modifiers")); return ET.tostring(m,encoding="unicode") if m is not None else ""
for gid in ["r45-cult-hq-centurion","r19-ts-centurion-disciplines","r19-ts-centurion-powers"]:
 g=ids.get(gid)
 print("\\nGROUP",gid,g.get("name") if g is not None else "MISSING","hidden",g.get("hidden") if g is not None else None,"cons",con(g) if g is not None else None,"mods",mods(g) if g is not None else None)
 if g is None: continue
 for tag in ["selectionEntries","entryLinks","selectionEntryGroups"]:
  p=g.find(C(tag))
  if p is not None:
   for x in list(p):
    print(" ",x.tag.split("}")[-1],x.get("id"),"|",x.get("name"),"| target",x.get("targetId"),"| hidden",x.get("hidden"),"| cons",con(x),"| mods",mods(x))
    if x.get("targetId") in ids:
      t=ids[x.get("targetId")]
      print("    TARGET",t.get("id"),t.get("name"))
      for il in t.findall(f"./{C('infoLinks')}/{C('infoLink')}"): print("      INFO",il.get("name"),"->",il.get("targetId"),il.get("type"))
      for rr in t.findall(f"./{C('rules')}/{C('rule')}"): print("      RULE",rr.get("name"),":",(rr.findtext(C("description")) or "")[:250])
# print shared psychic power-ish selection entries
print("\\nSHARED PSYCHIC SELECTIONS")
for e in r.findall(f"./{C('sharedSelectionEntries')}/{C('selectionEntry')}"):
 n=(e.get("name") or "").lower()
 if any(k in n for k in ["biomancy","divination","pyromancy","telekinesis","telepathy","pavoni","raptora","corvidae","athanae","pyrae"]):
  print(e.get("id"),"|",e.get("name"))
  for il in e.findall(f"./{C('infoLinks')}/{C('infoLink')}"): print(" INFO",il.get("name"),"->",il.get("targetId"),il.get("type"))
