import xml.etree.ElementTree as ET
NS="http://www.battlescribe.net/schema/catalogueSchema"; C=lambda t:f"{{{NS}}}{t}"
r=ET.parse("Legiones Astartes.cat").getroot(); ids={x.get("id"):x for x in r.iter() if x.get("id")}
for eid in ["hq-consul-moritat","r29-mor-pair-group","r29-mor-bolt","r29-mor-hand","r29-mor-plasma","r29-mor-calibanite","r47-rg-mor-fulcrum-pair","r74-ba-moritat-two-inferno"]:
 e=ids.get(eid); print("\\n",eid, bool(e))
 if not e:continue
 print(ET.tostring(e,encoding="unicode")[:12000])
