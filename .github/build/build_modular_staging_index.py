from pathlib import Path
import xml.etree.ElementTree as ET
IDXNS="http://www.battlescribe.net/schema/dataIndexSchema"
CATNS="http://www.battlescribe.net/schema/catalogueSchema"
ET.register_namespace("",IDXNS)
I=lambda t:f"{{{IDXNS}}}{t}"
D=Path("modular-catalogues-generated")
old=ET.parse("index.xml").getroot()
out=ET.Element(I("dataIndex"),dict(old.attrib))
out.set("name","Prohammer 30k Modular Staging")
entries=ET.SubElement(out,I("dataIndexEntries"))
# Keep game system and non-Astartes catalogues from live index.
old_entries=old.find(I("dataIndexEntries"))
for e in old_entries:
    if e.get("filePath")=="Legiones Astartes.cat":continue
    entries.append(e)
# Index only player-selectable Legion catalogues. Generic Astartes remains a linked
# repository dependency and is deliberately not exposed as an army choice.
files=sorted(p for p in D.glob("*.cat") if p.name!="Legiones-Astartes-Generic.cat")
assert len(files)==18
for p in files:
    r=ET.parse(p).getroot()
    ET.SubElement(entries,I("dataIndexEntry"),{
      "filePath":str(p).replace("\\","/"),
      "dataType":"catalogue",
      "dataId":r.get("id"),
      "dataName":r.get("name"),
      "dataBattleScribeVersion":r.get("battleScribeVersion","2.03"),
      "dataRevision":r.get("revision","1")
    })
ET.ElementTree(out).write("index-modular-staging.xml",encoding="utf-8",xml_declaration=True)
ET.parse("index-modular-staging.xml")
# consistency checks
seen=set()
for e in entries:
    key=(e.get("dataType"),e.get("dataId"))
    if key in seen:raise RuntimeError("Duplicate index ID "+str(key))
    seen.add(key)
    fp=e.get("filePath")
    if fp and fp.startswith("modular-catalogues-generated/"):
        r=ET.parse(fp).getroot()
        assert e.get("dataId")==r.get("id")
        assert e.get("dataName")==r.get("name")
        assert e.get("dataRevision")==r.get("revision")
print("Staging entries:",len(entries),"selectable Legion catalogues:",len(files),"generic library indexed: no")
