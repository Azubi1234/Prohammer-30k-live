from pathlib import Path
import xml.etree.ElementTree as ET

CAT = Path("Legiones Astartes.cat")
GST = Path("Prohammer 30k.gst")
IDX = Path("index.xml")
OUT = Path("inspection-live-r33-baseline-cleanup.txt")

CAT_NS = "http://www.battlescribe.net/schema/catalogueSchema"
GST_NS = "http://www.battlescribe.net/schema/gameSystemSchema"
IDX_NS = "http://www.battlescribe.net/schema/dataIndexSchema"

# --- Catalogue: R32 -> R33, preserving canonical default namespace ---
ET.register_namespace("", CAT_NS)
cat_tree = ET.parse(CAT)
cat_root = cat_tree.getroot()
if cat_root.get("revision") != "32":
    raise RuntimeError(f"R33 expected CAT revision 32, got {cat_root.get('revision')}")
cat_root.set("revision", "33")
cat_tree.write(CAT, encoding="utf-8", xml_declaration=True)

# --- GST: validation only; remains revision 1 ---
gst_tree = ET.parse(GST)
gst_root = gst_tree.getroot()
if gst_root.get("revision") != "1":
    raise RuntimeError(f"R33 expected GST revision 1, got {gst_root.get('revision')}")

# --- Index: advertise CAT 33 and rewrite with canonical default namespace ---
ET.register_namespace("", IDX_NS)
idx_tree = ET.parse(IDX)
idx_root = idx_tree.getroot()

cat_entry = None
gst_entry = None
for entry in idx_root.iter(f"{{{IDX_NS}}}dataIndexEntry"):
    if entry.get("filePath") == "Legiones Astartes.cat":
        cat_entry = entry
    elif entry.get("filePath") == "Prohammer 30k.gst":
        gst_entry = entry

if cat_entry is None:
    raise RuntimeError("index.xml is missing Legiones Astartes.cat")
if gst_entry is None:
    raise RuntimeError("index.xml is missing Prohammer 30k.gst")

cat_entry.set("dataRevision", "33")
gst_entry.set("dataRevision", "1")
idx_tree.write(IDX, encoding="utf-8", xml_declaration=True)

# --- Final validation ---
cat_check = ET.parse(CAT).getroot()
idx_text = IDX.read_text(encoding="utf-8")
idx_check = ET.parse(IDX).getroot()

checks = [
    ("Catalogue revision is 33", cat_check.get("revision") == "33"),
    ("GST revision remains 1", gst_root.get("revision") == "1"),
    ("Index advertises catalogue revision 33", 'filePath="Legiones Astartes.cat"' in idx_text and 'dataRevision="33"' in idx_text),
    ("Index advertises GST revision 1", 'filePath="Prohammer 30k.gst"' in idx_text and 'dataRevision="1"' in idx_text),
    ("index.xml has no ns0 prefix", "ns0:" not in idx_text and "xmlns:ns0" not in idx_text),
    ("index.xml root uses dataIndex namespace", idx_check.tag == f"{{{IDX_NS}}}dataIndex"),
]
failed = [name for name, ok in checks if not ok]
if failed:
    raise RuntimeError("R33 validation failed: " + "; ".join(failed))

lines = [
    "LIVE R33 — BASELINE CLEANUP",
    "Input CAT=32 -> target CAT=33",
    "GST remains revision 1",
    "",
    "CHANGES:",
    "- Bumped Legiones Astartes.cat revision from 32 to 33.",
    "- Updated index.xml catalogue dataRevision to 33.",
    "- Re-serialized index.xml with the canonical default BattleScribe data-index namespace.",
    "- Removed the ns0: namespace prefix from index.xml.",
    "- No army-list rules, costs, profiles, options or restrictions changed in this baseline pass.",
    "",
    "VALIDATION:",
]
lines += [f'- {"PASS" if ok else "FAIL"}: {name}' for name, ok in checks]
OUT.write_text("\n".join(lines) + "\n", encoding="utf-8")
print(OUT.read_text())
