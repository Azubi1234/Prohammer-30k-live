import xml.etree.ElementTree as ET
NS="http://www.battlescribe.net/schema/catalogueSchema"; C=lambda t:f"{{{NS}}}{t}"
r=ET.parse("Legiones Astartes.cat").getroot()
for needle in ["artificer armour","thunder hammer","rotor cannon"]:
    print("\\n===",needle,"===")
    for e in r.iter():
        if needle in (e.get("name") or "").lower():
            print(e.tag.split("}")[-1],e.get("id"),"|",e.get("name"),"| target",e.get("targetId"))
