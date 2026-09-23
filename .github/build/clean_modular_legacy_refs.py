from pathlib import Path
import xml.etree.ElementTree as ET
NS="http://www.battlescribe.net/schema/catalogueSchema";ET.register_namespace("",NS)
C=lambda t:f"{{{NS}}}{t}"
D=Path("modular-catalogues-generated")
fixes=0
# White Scars: remove inherited IF-only Hammerfall links from the two retinue copies.
p=D/"White-Scars.cat";t=ET.parse(p);r=t.getroot()
bad={"r60-ws-hibou-retinue-legion-veteran-squad-r44-veteran-unit-if-hammerfall-trans",
     "r60-ws-hasik-retinue-legion-veteran-squad-r44-veteran-unit-if-hammerfall-trans"}
for parent in r.iter():
    for x in list(parent):
        if x.get("id") in bad and x.tag==C("entryLink"):
            parent.remove(x);fixes+=1
t.write(p,encoding="utf-8",xml_declaration=True)

# Night Lords: the missing childIds are obsolete extra-model gates. Refractor Field
# already has the max-strength condition architecture elsewhere; drop dangling conditions.
for fn in ("Night-Lords.cat","Alpha-Legion.cat"):
    p=D/fn;t=ET.parse(p);r=t.getroot()
    for parent in r.iter():
        for x in list(parent):
            if x.tag==C("condition") and x.get("childId") in {"r71-nl-terror-extra","r71-nl-raptor-extra"}:
                parent.remove(x);fixes+=1
    t.write(p,encoding="utf-8",xml_declaration=True)

print("Applied generated staging cleanup fixes:",fixes)
for p in D.glob("*.cat"):ET.parse(p)
