import xml.etree.ElementTree as ET
NS="http://www.battlescribe.net/schema/catalogueSchema"; C=lambda t:f"{{{NS}}}{t}"
r=ET.parse("Legiones Astartes.cat").getroot()
def cost(e):return [(x.get("typeId"),x.get("value")) for x in e.findall(f"./{C('costs')}/{C('cost')}")]
def con(e):return [(x.get("id"),x.get("type"),x.get("value"),x.get("scope"),x.get("field")) for x in e.findall(f"./{C('constraints')}/{C('constraint')}")]
def prof(e):
 return [(p.get("id"),p.get("name"),[(x.get("name"),x.text,x.get("typeId")) for x in p.findall(f"./{C('characteristics')}/{C('characteristic')}")]) for p in e.findall(f"./{C('profiles')}/{C('profile')}")]
ids={x.get("id"):x for x in r.iter() if x.get("id")}
for i in range(11):
 arr=[e for e in r.findall(f"./{C('selectionEntries')}/{C('selectionEntry')}") if (e.get("id") or "").startswith(f"r41-unit-xx-{i}-")]
 for e in arr:
  print("\\nROOT",e.get("id"),e.get("name"),"hidden",e.get("hidden"),"cost",cost(e),"cons",con(e),"profiles",prof(e))
  for x in e.findall(f"./{C('selectionEntries')}/{C('selectionEntry')}"):
   print(" CHILD",x.get("id"),x.get("name"),"type",x.get("type"),"default",x.get("defaultAmount"),"cost",cost(x),"cons",con(x),"profiles",prof(x))
  for g in e.findall(f"./{C('selectionEntryGroups')}/{C('selectionEntryGroup')}"):
   print(" GROUP",g.get("id"),g.get("name"),"cons",con(g))
