from pathlib import Path
import collections, xml.etree.ElementTree as ET

CAT=Path("Legiones Astartes.cat"); IDX=Path("index.xml")
OUT=Path("inspection-live-r50-moritat-default-swap.txt")
NS="http://www.battlescribe.net/schema/catalogueSchema"; INS="http://www.battlescribe.net/schema/dataIndexSchema"
ET.register_namespace("",NS)
C=lambda t:f"{{{NS}}}{t}"; I=lambda t:f"{{{INS}}}{t}"

tree=ET.parse(CAT); root=tree.getroot()
if root.get("revision")!="49": raise RuntimeError(f"R50 expected CAT49, got {root.get('revision')}")
if root.get("gameSystemRevision")!="11": raise RuntimeError(f"R50 expected GST dependency 11, got {root.get('gameSystemRevision')}")
baseline=collections.Counter(x.get("id") for x in root.iter() if x.get("id"))
ids={x.get("id"):x for x in root.iter() if x.get("id")}

mor=ids["hq-consul-moritat"]
pair=ids["r29-mor-pair-group"]
bolt=ids["r29-mor-bolt"]

# Correct BattleScribe/New Recruit default-replacement architecture:
# the group chooses the default selection; the child itself is not permanently defaulted.
pair.set("defaultSelectionEntryId","r29-mor-bolt")
if "defaultAmount" in bolt.attrib: del bolt.attrib["defaultAmount"]

# Ensure exactly one pistol-pair loadout must be selected.
pcs=pair.find(C("constraints"))
if pcs is None: pcs=ET.SubElement(pair,C("constraints"))
mins=[x for x in pcs.findall(C("constraint")) if x.get("type")=="min"]
maxs=[x for x in pcs.findall(C("constraint")) if x.get("type")=="max"]
if not mins:
    mins=[ET.SubElement(pcs,C("constraint"),{"id":"r29-mor-pair-min","type":"min","value":"1","field":"selections","scope":"parent","shared":"true","includeChildSelections":"false","includeChildForces":"false"})]
if not maxs:
    maxs=[ET.SubElement(pcs,C("constraint"),{"id":"r29-mor-pair-max","type":"max","value":"1","field":"selections","scope":"parent","shared":"true","includeChildSelections":"false","includeChildForces":"false"})]
for x in mins:x.set("value","1")
for x in maxs:x.set("value","1")

# No individual loadout may carry its own minimum/default.
loadouts=["r29-mor-bolt","r29-mor-hand","r29-mor-plasma","r29-mor-calibanite","r47-rg-mor-fulcrum-pair","r74-ba-moritat-two-inferno"]
removed_child_mins=0
for rid in loadouts:
    e=ids.get(rid)
    if e is None:continue
    if rid!="r29-mor-bolt" and "defaultAmount" in e.attrib:del e.attrib["defaultAmount"]
    cs=e.find(C("constraints"))
    if cs is not None:
        for x in list(cs):
            if x.get("type")=="min":
                cs.remove(x);removed_child_mins+=1

# Verify all whole-pair options sit directly in the same group.
box=pair.find(C("selectionEntries"))
if box is None:raise RuntimeError("Pistol Pair selectionEntries missing")
direct={x.get("id") for x in box.findall(C("selectionEntry"))}
for rid in loadouts:
    if rid in ids and rid not in direct:
        raise RuntimeError(f"{rid} is not directly inside Pistol Pair")

root.set("revision","50")
tree.write(CAT,encoding="utf-8",xml_declaration=True)

ET.register_namespace("",INS)
it=ET.parse(IDX);ir=it.getroot()
for x in ir.iter(I("dataIndexEntry")):
    if x.get("filePath")=="Legiones Astartes.cat":x.set("dataRevision","50")
it.write(IDX,encoding="utf-8",xml_declaration=True)

# Validate serialized file.
rr=ET.parse(CAT).getroot();rids={x.get("id"):x for x in rr.iter() if x.get("id")};checks=[]
def ck(name,ok):
    checks.append((name,bool(ok)))
    if not ok:raise RuntimeError("R50 validation failed: "+name)

ck("CAT50",rr.get("revision")=="50")
ck("GST dependency 11",rr.get("gameSystemRevision")=="11")
ck("Index50",'dataRevision="50"' in IDX.read_text(encoding="utf-8"))
rp=rids["r29-mor-pair-group"]; rb=rids["r29-mor-bolt"]
ck("Pistol Pair default is Two Bolt Pistols",rp.get("defaultSelectionEntryId")=="r29-mor-bolt")
ck("Bolt Pistols have no defaultAmount","defaultAmount" not in rb.attrib)
pcons=rp.find(C("constraints"))
ck("Pistol Pair min1",any(x.get("type")=="min" and x.get("value")=="1" for x in pcons.findall(C("constraint"))))
ck("Pistol Pair max1",any(x.get("type")=="max" and x.get("value")=="1" for x in pcons.findall(C("constraint"))))
for rid in loadouts:
    if rid not in rids:continue
    e=rids[rid];cs=e.find(C("constraints"))
    ck(rid+" no child minimum",cs is None or not any(x.get("type")=="min" for x in cs.findall(C("constraint"))))
ck("Fulcrums remain +20",any(x.get("typeId")=="pts" and x.get("value")=="20" for x in rids["r47-rg-mor-fulcrum-pair"].findall(f"./{C('costs')}/{C('cost')}")))
ck("Fulcrums remain Raven Guard-only","legion-xix" in ET.tostring(rids["r47-rg-mor-fulcrum-pair"],encoding="unicode"))

new=collections.Counter(x.get("id") for x in rr.iter() if x.get("id"))
worse={k:v for k,v in new.items() if v>max(1,baseline.get(k,0))}
ck("No new/worsened duplicate IDs",not worse)

OUT.write_text("\n".join([
"Live R50 — Moritat default pistol-pair swap",
"Input CAT=49/GST=11 -> CAT=50/GST remains 11","",
"FIX:",
"- Pistol Pair now uses selectionEntryGroup.defaultSelectionEntryId = Two Bolt Pistols.",
"- Removed defaultAmount=1 from the Two Bolt Pistols child entry.",
"- Pistol Pair remains min 1 / max 1.",
"- Therefore New Recruit treats Two Bolt Pistols as the default member of the one-of group and swaps it when another pair is chosen.",
"- Fulcrum Hand Cannons remain Raven Guard-only at +20 points.",
f"- Removed {removed_child_mins} stray child-level minimum constraint(s) from pistol-pair alternatives.","",
"VALIDATION:"
]+[f'- {"PASS" if ok else "FAIL"}: {name}' for name,ok in checks])+"\n",encoding="utf-8")
print(OUT.read_text())
