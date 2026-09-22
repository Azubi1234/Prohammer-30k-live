import xml.etree.ElementTree as ET
NS="http://www.battlescribe.net/schema/catalogueSchema"; C=lambda t:f"{{{NS}}}{t}"
r=ET.parse("Legiones Astartes.cat").getroot(); ids={x.get("id"):x for x in r.iter() if x.get("id")}
def cons(e):return [(x.get("id"),x.get("type"),x.get("value"),x.get("scope"),x.get("field")) for x in e.findall(f"./{C('constraints')}/{C('constraint')}")]
def mods(e):
 m=e.find(C("modifiers"));return ET.tostring(m,encoding="unicode") if m is not None else ""
for rid in ["veteran-unit","terminator-unit",
"r45-ts-veteran-brotherhood","r45-ts-terminator-brotherhood",
"r19-ts-veteran-unit-brotherhood-disciplines","r19-ts-veteran-unit-brotherhood-powers",
"r19-ts-terminator-unit-brotherhood-disciplines","r19-ts-terminator-unit-brotherhood-powers",
"r45-cult-veteran-unit","r45-cult-terminator-unit"]:
 e=ids.get(rid)
 print("\\n==",rid,"==",bool(e))
 if not e:continue
 print(e.tag.split("}")[-1],e.get("name"),"hidden",e.get("hidden"),"default",e.get("defaultAmount"),"cons",cons(e))
 print("MODS",mods(e))
 for s in e.findall(f"./{C('selectionEntries')}/{C('selectionEntry')}"):
  print(" SEL",s.get("id"),s.get("name"),"hidden",s.get("hidden"),"default",s.get("defaultAmount"),"cons",cons(s),"mods",mods(s)[:2500])
 for l in e.findall(f"./{C('entryLinks')}/{C('entryLink')}"):
  print(" LINK",l.get("id"),l.get("name"),"->",l.get("targetId"),"hidden",l.get("hidden"),"cons",cons(l),"mods",mods(l)[:2500])
 for g in e.findall(f"./{C('selectionEntryGroups')}/{C('selectionEntryGroup')}"):
  print(" GROUP",g.get("id"),g.get("name"),"hidden",g.get("hidden"),"cons",cons(g),"mods",mods(g)[:2500])
