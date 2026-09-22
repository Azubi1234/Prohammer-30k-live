import xml.etree.ElementTree as ET
NS="http://www.battlescribe.net/schema/catalogueSchema";C=lambda t:f"{{{NS}}}{t}"
r=ET.parse("Legiones Astartes.cat").getroot();ids={x.get("id"):x for x in r.iter() if x.get("id")}
def cons(e):return [(x.get("id"),x.get("type"),x.get("value"),x.get("scope"),x.get("field")) for x in e.findall(f"./{C('constraints')}/{C('constraint')}")]
for eid in ["hq-consul-moritat","r29-mor-pair-group","r29-mor-bolt","r47-rg-mor-fulcrum-pair","r74-ba-moritat-two-inferno"]:
 e=ids.get(eid);print("\\n",eid,"exists",bool(e))
 if e is not None:
  print(e.tag.split("}")[-1],e.get("name"),"hidden",e.get("hidden"),"default",e.get("defaultAmount"),"cons",cons(e))
  if e.tag==C("selectionEntryGroup"):
   for box in ["selectionEntries","entryLinks"]:
    b=e.find(C(box));print(box,[(x.get("id"),x.get("name"),x.get("defaultAmount"),cons(x)) for x in list(b)] if b is not None else [])
