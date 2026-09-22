import xml.etree.ElementTree as ET
NS="http://www.battlescribe.net/schema/catalogueSchema";C=lambda t:f"{{{NS}}}{t}"
r=ET.parse("Legiones Astartes.cat").getroot();ids={x.get("id"):x for x in r.iter() if x.get("id")};pm={c:p for p in r.iter() for c in p}
def cost(e):return [(x.get("typeId"),x.get("value")) for x in e.findall(f"./{C('costs')}/{C('cost')}")]
def cons(e):return [(x.get("id"),x.get("type"),x.get("value"),x.get("scope"),x.get("field")) for x in e.findall(f"./{C('constraints')}/{C('constraint')}")]
def mods(e):
 m=e.find(C("modifiers"));return ET.tostring(m,encoding="unicode") if m is not None else ""
def chain(e):
 out=[];p=e
 while p is not None and len(out)<9:
  out.append((p.tag.split("}")[-1],p.get("id"),p.get("name")));p=pm.get(p)
 return out
for eid in ["r45-ts-brotherhood","r45-ts-brotherhood-fellowship","r45-veteran-unit-ts-brother","r45-veteran-unit-ts-brother-fellow"]:
 e=ids.get(eid);print("\\n",eid,"exists",bool(e))
 if e:
  print(e.tag.split("}")[-1],e.get("name"),"hidden",e.get("hidden"),"cost",cost(e),"cons",cons(e),"mods",mods(e)[:5000],"chain",chain(e))
  for rr in e.findall(f"./{C('rules')}/{C('rule')}"):print(" RULE",rr.get("name"),(rr.findtext(C("description")) or "")[:800])
  for il in e.findall(f"./{C('infoLinks')}/{C('infoLink')}"):print(" INFO",il.get("name"),il.get("targetId"),il.get("type"))
v=ids["veteran-unit"]
for gid in ["r49-legion-upgrades-veteran-unit","r45-cult-veteran-unit","r19-ts-veteran-unit-brotherhood-disciplines","r19-ts-veteran-unit-brotherhood-powers"]:
 g=next((x for x in v.iter(C("selectionEntryGroup")) if x.get("id")==gid),None)
 print("\\nGROUP",gid,"exists",bool(g))
 if g:
  print("hidden",g.get("hidden"),"cons",cons(g),"mods",mods(g)[:12000],"chain",chain(g))
  for x in list(g):
   if x.tag in (C("selectionEntry"),C("entryLink")): print(" OPT",x.get("id"),x.get("name"),"hidden",x.get("hidden"),"cost",cost(x),"cons",cons(x),"mods",mods(x)[:3500])
