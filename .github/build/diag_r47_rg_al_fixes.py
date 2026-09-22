import xml.etree.ElementTree as ET, collections
CNS="http://www.battlescribe.net/schema/catalogueSchema"; C=lambda t:f"{{{CNS}}}{t}"
r=ET.parse("Legiones Astartes.cat").getroot(); ids={x.get("id"):x for x in r.iter() if x.get("id")}
def cost(e):return [(x.get("typeId"),x.get("value")) for x in e.findall(f"./{C('costs')}/{C('cost')}")]
def con(e):return [(x.get("id"),x.get("type"),x.get("value"),x.get("scope"),x.get("field")) for x in e.findall(f"./{C('constraints')}/{C('constraint')}")]
def mods(e):
 m=e.find(C("modifiers")); return ET.tostring(m,encoding="unicode") if m is not None else ""
def dump(e,depth=0,maxdepth=5):
 ind="  "*depth
 print(f"{ind}{e.tag.split('}')[-1]} id={e.get('id')} name={e.get('name')} type={e.get('type')} hidden={e.get('hidden')} default={e.get('defaultAmount')} cost={cost(e)} cons={con(e)}")
 for il in e.findall(f"./{C('infoLinks')}/{C('infoLink')}"): print(f"{ind}  INFO {il.get('id')} {il.get('name')} -> {il.get('targetId')}")
 for rr in e.findall(f"./{C('rules')}/{C('rule')}"): print(f"{ind}  RULE {rr.get('id')} {rr.get('name')}: {(rr.findtext(C('description')) or '')[:300]}")
 if mods(e): print(f"{ind}  MODS {mods(e)[:1200]}")
 if depth>=maxdepth:return
 for tag in ["selectionEntries","selectionEntryGroups","entryLinks"]:
  p=e.find(C(tag))
  if p is not None:
   for x in list(p):dump(x,depth+1,maxdepth)

print("REV",r.get("revision"),"GST",r.get("gameSystemRevision"))
# Locate moritat and RG gear
for e in r.iter(C("selectionEntry")):
 n=(e.get("name") or "").lower(); eid=e.get("id") or ""
 if "moritat" in n or "fulcrum" in n:
  print("\\n==== MOR/FULCRUM ROOT/PATH ===="); dump(e,0,5)
# key Raven units
for e in r.iter(C("selectionEntry")):
 n=(e.get("name") or "").lower(); eid=e.get("id") or ""
 if n=="raptor squad" or ("corvus corax" in n and e in r.findall(f"./{C('selectionEntries')}/{C('selectionEntry')}")):
  print("\\n==== RG KEY ===="); dump(e,0,7)
# exact Corax nested Raptor / Alpharius nested Lernaean by ancestry text
pm={c:p for p in r.iter() for c in p}
def chain(e):
 a=[];p=e
 while p is not None and len(a)<10:
  a.append((p.get("id"),p.get("name")));p=pm.get(p)
 return a
for e in r.iter(C("selectionEntry")):
 n=(e.get("name") or "").lower()
 ch=chain(e)
 txt=" ".join((n or "")+" "+(name or "") for _,name in ch).lower()
 if ("corvus corax" in txt and "raptor squad" in txt) or ("alpharius" in txt and "lernaean" in txt) or ("alpharius" in txt and "sheed ranko" in txt):
  print("\\n==== NESTED TARGET ====",chain(e)); dump(e,0,8)
