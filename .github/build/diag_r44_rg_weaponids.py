import xml.etree.ElementTree as ET
NS="http://www.battlescribe.net/schema/catalogueSchema"; C=lambda t:f"{{{NS}}}{t}"
r=ET.parse("Legiones Astartes.cat").getroot()
for needle in ["combi-meltagun","missile launcher"]:
    print("\\n===",needle,"===")
    seen=set()
    for e in r.iter():
        n=(e.get("name") or "").lower()
        if needle in n:
            print(e.tag.split("}")[-1],e.get("id"),"|",e.get("name"),"| target",e.get("targetId"))
            seen.add(e.get("targetId"))
            if len(seen)>30:break
