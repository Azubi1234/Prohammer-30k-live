from pathlib import Path
import xml.etree.ElementTree as ET

CAT=Path("Legiones Astartes.cat"); GST=Path("Prohammer 30k.gst"); IDX=Path("index.xml")
OUT=Path("inspection-live-r54-cache-bust.txt")
CNS="http://www.battlescribe.net/schema/catalogueSchema"; GNS="http://www.battlescribe.net/schema/gameSystemSchema"; INS="http://www.battlescribe.net/schema/dataIndexSchema"
ET.register_namespace("",CNS); ET.register_namespace("",GNS); ET.register_namespace("",INS)
C=lambda t:f"{{{CNS}}}{t}"; G=lambda t:f"{{{GNS}}}{t}"; I=lambda t:f"{{{INS}}}{t}"

ct=ET.parse(CAT); cr=ct.getroot()
gt=ET.parse(GST); gr=gt.getroot()
if cr.get("revision")!="53": raise RuntimeError(f"R54 cache-bust expected CAT53, got {cr.get('revision')}")
if gr.get("revision")!="11": raise RuntimeError(f"R54 cache-bust expected GST11, got {gr.get('revision')}")

# Metadata-only cache bust. Do not alter any army content.
cr.set("revision","54")
cr.set("gameSystemRevision","12")
gr.set("revision","12")

ct.write(CAT,encoding="utf-8",xml_declaration=True)
gt.write(GST,encoding="utf-8",xml_declaration=True)

it=ET.parse(IDX); ir=it.getroot()
for x in ir.iter(I("dataIndexEntry")):
    if x.get("filePath")=="Legiones Astartes.cat":
        x.set("dataRevision","54")
    elif x.get("filePath")=="Prohammer 30k.gst":
        x.set("dataRevision","12")
it.write(IDX,encoding="utf-8",xml_declaration=True)

# Re-parse to ensure the files themselves are sound.
c2=ET.parse(CAT).getroot(); g2=ET.parse(GST).getroot(); idx=IDX.read_text(encoding="utf-8")
checks=[
    ("CAT revision 54",c2.get("revision")=="54"),
    ("CAT points to GST 12",c2.get("gameSystemRevision")=="12"),
    ("GST revision 12",g2.get("revision")=="12"),
    ("index advertises CAT54",'filePath="Legiones Astartes.cat"' in idx and 'dataRevision="54"' in idx),
    ("index advertises GST12",'filePath="Prohammer 30k.gst"' in idx and 'dataRevision="12"' in idx),
    ("canonical index namespace",'ns0:' not in idx),
]
for n,ok in checks:
    if not ok: raise RuntimeError("R54 cache-bust validation failed: "+n)

OUT.write_text("\n".join([
    "Live R54 — New Recruit hard cache-bust",
    "Input: restored known-good CAT53 / GST11",
    "Output: CAT54 / GST12",
    "",
    "CONTENT:",
    "- No army-list, profile, option, rule, wargear, cost or restriction content changed.",
    "- Catalogue remains the exact known-good R48 content restored by R53.",
    "- Only catalogue/game-system/index revision metadata changed.",
    "",
    "PURPOSE:",
    "- Force New Recruit to refresh both the catalogue and its parent game system rather than reusing the cached GST11/CAT53 pair.",
    "",
    "VALIDATION:",
]+[f'- {"PASS" if ok else "FAIL"}: {n}' for n,ok in checks])+"\n",encoding="utf-8")
print(OUT.read_text())
