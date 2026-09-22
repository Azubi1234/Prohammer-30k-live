from pathlib import Path
import xml.etree.ElementTree as ET

CAT=Path("Legiones Astartes.cat")
IDX=Path("index.xml")
OUT=Path("inspection-live-r53-known-good-restore.txt")
CNS="http://www.battlescribe.net/schema/catalogueSchema"
INS="http://www.battlescribe.net/schema/dataIndexSchema"
ET.register_namespace("",CNS); ET.register_namespace("",INS)
C=lambda t:f"{{{CNS}}}{t}"; I=lambda t:f"{{{INS}}}{t}"

tree=ET.parse(CAT); root=tree.getroot()
# The file has already been replaced by the workflow with the exact known-good R48 catalogue.
if root.get("revision")!="48":
    raise RuntimeError(f"Expected historical R48 catalogue after restore, got {root.get('revision')}")
if root.get("gameSystemRevision")!="11":
    raise RuntimeError(f"Historical R48 GST dependency changed unexpectedly: {root.get('gameSystemRevision')}")

# Bump only the catalogue revision so New Recruit cannot reuse the broken cached R52.
root.set("revision","53")
tree.write(CAT,encoding="utf-8",xml_declaration=True)

it=ET.parse(IDX); ir=it.getroot()
for x in ir.iter(I("dataIndexEntry")):
    if x.get("filePath")=="Legiones Astartes.cat":
        x.set("dataRevision","53")
    if x.get("filePath")=="Prohammer 30k.gst":
        x.set("dataRevision","11")
it.write(IDX,encoding="utf-8",xml_declaration=True)

# Sanity checks: exact R48 content architecture, only revision metadata changed.
rr=ET.parse(CAT).getroot()
checks=[
    ("CAT revision 53",rr.get("revision")=="53"),
    ("GST dependency remains 11",rr.get("gameSystemRevision")=="11"),
    ("index advertises CAT53",'dataRevision="53"' in IDX.read_text(encoding="utf-8")),
    ("index advertises GST11",'dataRevision="11"' in IDX.read_text(encoding="utf-8")),
    ("Army Configuration exists",any(x.get("id")=="config-army" for x in rr.iter(C("selectionEntry")))),
    ("Legion selector exists",any(x.get("id")=="config-legion" for x in rr.iter(C("selectionEntryGroup")))),
    ("Moritat exists",any(x.get("id")=="hq-consul-moritat" for x in rr.iter(C("selectionEntry")))),
]
for n,ok in checks:
    if not ok: raise RuntimeError("R53 validation failed: "+n)

OUT.write_text("\n".join([
"Live R53 — restore last confirmed-working New Recruit catalogue",
"Base: exact Legiones Astartes.cat from live R48 commit 51d32130622bb8ebfa8a6ee49cbf1e7c4623be59",
"Output: CAT53 / GST11","",
"WHY:",
"- R52 still failed the official catalogue validator and New Recruit continued to reject the army book.",
"- R48 is the last catalogue the user personally confirmed loaded and functioned before Shattered-Legions work began.",
"- R53 therefore restores that exact catalogue content and only changes revision metadata so New Recruit redownloads it.","",
"IMPORTANT:",
"- No Shattered Legions content is included in R53 yet.",
"- No R49/R50/R51/R52 catalogue mutations are retained.",
"- This recovery intentionally prioritises restoring a loadable army book before re-applying Shattered Legions on a known-good base.","",
"VALIDATION:"
]+[f"- PASS: {n}" for n,ok in checks])+"\n",encoding="utf-8")
print(OUT.read_text())
