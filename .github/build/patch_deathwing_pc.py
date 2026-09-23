from pathlib import Path
import xml.etree.ElementTree as ET
NS="http://www.battlescribe.net/schema/catalogueSchema";ET.register_namespace("",NS);C=lambda t:f"{{{NS}}}{t}"
p=Path("modular-catalogues-generated/Dark-Angels.cat");t=ET.parse(p);r=t.getroot()
e=next(x for x in r.iter(C("selectionEntry")) if x.get("id")=="da22-deathwing-term-comp")
cls=e.find(C("categoryLinks"));eid=e.get("id")
if not any(x.get("id")==eid+"-primarchs-chosen-troops" for x in cls.findall(C("categoryLink"))):
 cl=ET.SubElement(cls,C("categoryLink"),{"targetId":"cat-troops","id":eid+"-primarchs-chosen-troops","primary":"true","name":"Troops — Primarch's Chosen","hidden":"true"})
 ms=ET.SubElement(cl,C("modifiers"));m=ET.SubElement(ms,C("modifier"),{"id":eid+"-pc-show-troops","type":"set","field":"hidden","value":"false"})
 cs=ET.SubElement(m,C("conditions"));ET.SubElement(cs,C("condition"),{"type":"atLeast","value":"1","field":"selections","scope":"force","childId":"da22-rite-primarchs-chosen","shared":"true","includeChildSelections":"true","includeChildForces":"false"})
t.write(p,encoding="utf-8",xml_declaration=True);ET.parse(p);print("Deathwing Terminator Companion Primarch's Chosen link present")
