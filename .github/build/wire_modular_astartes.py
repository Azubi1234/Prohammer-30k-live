from pathlib import Path
import glob,xml.etree.ElementTree as ET
NS="http://www.battlescribe.net/schema/catalogueSchema"
ET.register_namespace("",NS)
C=lambda t:f"{{{NS}}}{t}"
DIR=Path("modular-catalogues-generated")
generic=ET.parse(DIR/"Legiones-Astartes-Generic.cat").getroot()
gid=generic.get("id")
if not gid:raise RuntimeError("Generic library has no id")
changed=0
for p in sorted(DIR.glob("*.cat")):
    if p.name=="Legiones-Astartes-Generic.cat":continue
    t=ET.parse(p);r=t.getroot()
    links=r.find(C("catalogueLinks"))
    if links is None:links=ET.SubElement(r,C("catalogueLinks"))
    found=False
    for l in links.findall(C("catalogueLink")):
        if (l.get("name") or "").startswith("Legiones Astartes"):
            l.set("targetId",gid);l.set("name","Legiones Astartes — Generic Library");l.set("type","catalogue");found=True
    if not found:
        ET.SubElement(links,C("catalogueLink"),{"id":"link-generic-"+r.get("id","x")[-12:],"name":"Legiones Astartes — Generic Library","targetId":gid,"type":"catalogue"})
    t.write(p,encoding="utf-8",xml_declaration=True);ET.parse(p);changed+=1
print("Generic id:",gid,"repointed:",changed)
