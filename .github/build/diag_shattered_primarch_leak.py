import xml.etree.ElementTree as ET
NS="http://www.battlescribe.net/schema/catalogueSchema"; C=lambda t:f"{{{NS}}}{t}"
r=ET.parse("Legiones Astartes.cat").getroot()
THEME="r62-shattered-theme"
for e in r.iter(C("selectionEntry")):
    names=[x.get("name") or "" for x in e.findall(f"./{C('rules')}/{C('rule')}")]+[x.get("name") or "" for x in e.findall(f"./{C('infoLinks')}/{C('infoLink')}")]
    if any(n=="Primarch" for n in names):
        txt=ET.tostring(e,encoding="unicode")
        print(e.get("id"),"|",e.get("name"),"| blocked=",THEME in txt)
