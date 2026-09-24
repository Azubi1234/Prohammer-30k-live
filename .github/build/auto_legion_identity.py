from pathlib import Path
import re
import xml.etree.ElementTree as ET

LEGIONS = [
("Dark-Angels.cat","legion-i","auto-legion-marker-i"),("Emperor-s-Children.cat","legion-iii","auto-legion-marker-iii"),
("Iron-Warriors.cat","legion-iv","auto-legion-marker-iv"),("White-Scars.cat","legion-v","auto-legion-marker-v"),
("Space-Wolves.cat","legion-vi","auto-legion-marker-vi"),("Imperial-Fists.cat","legion-vii","auto-legion-marker-vii"),
("Night-Lords.cat","legion-viii","auto-legion-marker-viii"),("Blood-Angels.cat","legion-ix","auto-legion-marker-ix"),
("Iron-Hands.cat","legion-x","auto-legion-marker-x"),("World-Eaters.cat","legion-xii","auto-legion-marker-xii"),
("Ultramarines.cat","legion-xiii","auto-legion-marker-xiii"),("Death-Guard.cat","legion-xiv","auto-legion-marker-xiv"),
("Thousand-Sons.cat","legion-xv","auto-legion-marker-xv"),("Sons-of-Horus.cat","legion-xvi","auto-legion-marker-xvi"),
("Word-Bearers.cat","legion-xvii","auto-legion-marker-xvii"),("Salamanders.cat","legion-xviii","auto-legion-marker-xviii"),
("Raven-Guard.cat","legion-xix","auto-legion-marker-xix"),("Alpha-Legion.cat","legion-xx","auto-legion-marker-xx")]
NS="http://www.battlescribe.net/schema/catalogueSchema"
ET.register_namespace("",NS)
q=lambda x:f"{{{NS}}}{x}"

gpath=Path("Legiones-Astartes-Generic.cat")
tree=ET.parse(gpath); root=tree.getroot()
group=root.find(".//"+q("selectionEntryGroup")+"[@id='config-legion']")
assert group is not None
entries={e.get("id"):e for e in group.findall("./"+q("selectionEntries")+"/"+q("selectionEntry"))}
print("Selector IDs:", sorted(entries))
for _,lid,marker in LEGIONS:
    e=entries.get(lid)
    if e is None:
        print(f"WARNING: Generic selector has no {lid}; skipping auto-selection wiring for this ID")
        continue
    mods=e.find(q("modifiers"))
    if mods is None: mods=ET.Element(q("modifiers")); e.insert(0,mods)
    cons=e.find(q("constraints"))
    if cons is None:
        cons=ET.SubElement(e,q("constraints"))
    cid=lid+"-auto-min"
    if not any(x.get("id")==cid for x in cons):
        ET.SubElement(cons,q("constraint"),{"id":cid,"type":"min","value":"0","field":"selections","scope":"parent","shared":"true","includeChildSelections":"false","automatic":"true"})
    m=ET.SubElement(mods,q("modifier"),{"id":lid+"-auto-hide","type":"set","field":"hidden","value":"true"})
    cs=ET.SubElement(m,q("conditions")); ET.SubElement(cs,q("condition"),{"type":"lessThan","value":"1","field":"selections","scope":"roster","childId":marker,"shared":"true","includeChildSelections":"true","includeChildForces":"false"})
    m=ET.SubElement(mods,q("modifier"),{"id":lid+"-auto-min-on","type":"set","field":cid,"value":"1"})
    cs=ET.SubElement(m,q("conditions")); ET.SubElement(cs,q("condition"),{"type":"atLeast","value":"1","field":"selections","scope":"roster","childId":marker,"shared":"true","includeChildSelections":"true","includeChildForces":"false"})
root.set("revision","2")
tree.write(gpath,encoding="utf-8",xml_declaration=True)

for fn,lid,marker in LEGIONS:
    p=Path(fn)
    try:
        t=ET.parse(p); r=t.getroot()
    except ET.ParseError as exc:
        print(f"WARNING: {fn} is already malformed XML ({exc}); skipping it so healthy catalogues can still be patched")
        continue
    links=r.findall("./"+q("catalogueLinks")+"/"+q("catalogueLink"))
    if not any(x.get("importRootEntries")=="true" for x in links):
        print(f"WARNING: {fn} root import flag not found; continuing")
    ses=r.find("./"+q("selectionEntries"))
    if ses is None:
        ses=ET.SubElement(r,q("selectionEntries"))
    if not any(x.get("id")==marker for x in ses.findall("./"+q("selectionEntry"))):
        e=ET.Element(q("selectionEntry"),{"type":"upgrade","name":"Automatic Legion Identity","id":marker,"hidden":"true","import":"true"})
        cs=ET.SubElement(e,q("constraints"))
        ET.SubElement(cs,q("constraint"),{"id":marker+"-min","type":"min","value":"1","field":"selections","scope":"parent","shared":"true","includeChildSelections":"false","automatic":"true"})
        ET.SubElement(cs,q("constraint"),{"id":marker+"-max","type":"max","value":"1","field":"selections","scope":"parent","shared":"true","includeChildSelections":"false"})
        costs=ET.SubElement(e,q("costs")); ET.SubElement(costs,q("cost"),{"name":"Points","typeId":"51b2-306e-1021-d207","value":"0"})
        ses.insert(0,e)
    r.set("revision","4"); t.write(p,encoding="utf-8",xml_declaration=True)

ip=Path("index.xml")
try:
    it=ET.parse(ip); ir=it.getroot()
    ins=ir.tag.split("}")[0].lstrip("{") if "}" in ir.tag else ""
    for e in ir.iter():
        if e.tag.endswith("dataIndexEntry"):
            fp=e.get("filePath")
            if fp=="Legiones-Astartes-Generic.cat": e.set("dataRevision","2")
            elif any(fp==x[0] for x in LEGIONS): e.set("dataRevision","4")
    if ins: ET.register_namespace("",ins)
    it.write(ip,encoding="utf-8",xml_declaration=True)
except Exception as exc:
    print(f"WARNING: index revision update skipped: {exc}")
print("Patched Generic auto-Legion selection for all 18 Legion catalogues.")
