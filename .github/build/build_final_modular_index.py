from pathlib import Path
import xml.etree.ElementTree as ET
IDX="http://www.battlescribe.net/schema/dataIndexSchema"; ET.register_namespace("",IDX); I=lambda t:f"{{{IDX}}}{t}"
D=Path("modular-catalogues-generated"); old=ET.parse("index.xml").getroot()
out=ET.Element(I("dataIndex"),dict(old.attrib));out.set("name","Prohammer 30k Live");entries=ET.SubElement(out,I("dataIndexEntries"))
for e in old.find(I("dataIndexEntries")):
 if e.get("filePath")!="Legiones Astartes.cat": entries.append(e)
files=sorted(D.glob("*.cat")); assert len(files)==19,(len(files),[p.name for p in files])
for p in files:
 r=ET.parse(p).getroot()
 ET.SubElement(entries,I("dataIndexEntry"),{"filePath":str(p).replace("\\","/"),"dataType":"catalogue","dataId":r.get("id"),"dataName":r.get("name"),"dataBattleScribeVersion":r.get("battleScribeVersion","2.03"),"dataRevision":r.get("revision","1")})
ET.ElementTree(out).write("index-modular-staging.xml",encoding="utf-8",xml_declaration=True)
ids={e.get("dataId") for e in entries}; assert "cat-7b24-e6f1-83a9-4c50" in ids
print("FINAL INDEX:",len(entries),"entries; 19 modular catalogues; Generic ID present")
