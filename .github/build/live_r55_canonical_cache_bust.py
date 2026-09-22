from pathlib import Path
import xml.etree.ElementTree as ET

CAT=Path("Legiones Astartes.cat"); GST=Path("Prohammer 30k.gst"); IDX=Path("index.xml")
OUT=Path("inspection-live-r55-canonical-cache-bust.txt")
CNS="http://www.battlescribe.net/schema/catalogueSchema"; GNS="http://www.battlescribe.net/schema/gameSystemSchema"; INS="http://www.battlescribe.net/schema/dataIndexSchema"
C=lambda t:f"{{{CNS}}}{t}"; G=lambda t:f"{{{GNS}}}{t}"; I=lambda t:f"{{{INS}}}{t}"

ct=ET.parse(CAT); cr=ct.getroot()
gt=ET.parse(GST); gr=gt.getroot()
if cr.get("revision")!="54": raise RuntimeError(f"R55 expected CAT54, got {cr.get('revision')}")
if gr.get("revision")!="12": raise RuntimeError(f"R55 expected GST12, got {gr.get('revision')}")

# Metadata-only second cache bust.
cr.set("revision","55"); cr.set("gameSystemRevision","13")
gr.set("revision","13")

# IMPORTANT: register each schema as the default immediately before writing that file.
ET.register_namespace("",CNS)
ct.write(CAT,encoding="utf-8",xml_declaration=True)

ET.register_namespace("",GNS)
gt.write(GST,encoding="utf-8",xml_declaration=True)

it=ET.parse(IDX); ir=it.getroot()
for x in ir.iter(I("dataIndexEntry")):
    if x.get("filePath")=="Legiones Astartes.cat": x.set("dataRevision","55")
    elif x.get("filePath")=="Prohammer 30k.gst": x.set("dataRevision","13")
ET.register_namespace("",INS)
it.write(IDX,encoding="utf-8",xml_declaration=True)

cat_text=CAT.read_text(encoding="utf-8")
gst_text=GST.read_text(encoding="utf-8")
idx_text=IDX.read_text(encoding="utf-8")
checks=[
 ("CAT revision 55",ET.parse(CAT).getroot().get("revision")=="55"),
 ("CAT points GST13",ET.parse(CAT).getroot().get("gameSystemRevision")=="13"),
 ("GST revision 13",ET.parse(GST).getroot().get("revision")=="13"),
 ("index advertises CAT55",'dataRevision="55"' in idx_text),
 ("index advertises GST13",'dataRevision="13"' in idx_text),
 ("CAT canonical default namespace",'<catalogue xmlns="http://www.battlescribe.net/schema/catalogueSchema"' in cat_text[:500]),
 ("GST canonical default namespace",'<gameSystem xmlns="http://www.battlescribe.net/schema/gameSystemSchema"' in gst_text[:500]),
 ("index canonical default namespace",'<dataIndex xmlns="http://www.battlescribe.net/schema/dataIndexSchema"' in idx_text[:500]),
 ("no ns0 in CAT",'ns0:' not in cat_text),
 ("no ns0 in GST",'ns0:' not in gst_text),
 ("no ns0 in index",'ns0:' not in idx_text),
]
for n,ok in checks:
    if not ok: raise RuntimeError("R55 validation failed: "+n)

OUT.write_text("\n".join([
 "Live R55 — canonical New Recruit cache-bust",
 "Input: CAT54/GST12 metadata-only cache bust",
 "Output: CAT55/GST13",
 "",
 "CONTENT:",
 "- No army-list/rule/wargear/profile/points/restriction content changed.",
 "- Still based on the last user-confirmed working R48 catalogue restored by R53.",
 "",
 "FIX:",
 "- Rewrote CAT, GST and index with canonical default BattleScribe namespaces.",
 "- Removed ns0 namespace prefixes introduced by the R54 metadata writer.",
 "- Bumped both CAT and GST again so New Recruit must see a fresh pair.",
 "",
 "VALIDATION:"
]+[f'- {"PASS" if ok else "FAIL"}: {n}' for n,ok in checks])+"\n",encoding="utf-8")
print(OUT.read_text())
