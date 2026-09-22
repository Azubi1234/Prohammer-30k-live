from pathlib import Path
import collections, xml.etree.ElementTree as ET

CAT=Path("Legiones Astartes.cat"); IDX=Path("index.xml")
OUT=Path("inspection-live-r50-moritat-pistol-selector.txt")
NS="http://www.battlescribe.net/schema/catalogueSchema"; INS="http://www.battlescribe.net/schema/dataIndexSchema"
ET.register_namespace("",NS)
C=lambda t:f"{{{NS}}}{t}"; I=lambda t:f"{{{INS}}}{t}"

tree=ET.parse(CAT); root=tree.getroot()
if root.get("revision")!="49": raise RuntimeError(f"R50 expected CAT49, got {root.get('revision')}")
if root.get("gameSystemRevision")!="11": raise RuntimeError(f"R50 expected GST11 dependency, got {root.get('gameSystemRevision')}")
baseline=collections.Counter(x.get("id") for x in root.iter() if x.get("id"))
ids={x.get("id"):x for x in root.iter() if x.get("id")}

mor=ids["hq-consul-moritat"]
pair=ids["r29-mor-pair-group"]
bolt=ids["r29-mor-bolt"]

# Robust New Recruit replacement semantics:
# the group itself enforces exactly one choice; no child is hard-defaulted/mandatory.
pair_cs=pair.find(C("constraints"))
if pair_cs is None: pair_cs=ET.SubElement(pair,C("constraints"))
mins=[x for x in pair_cs.findall(C("constraint")) if x.get("type")=="min"]
maxs=[x for x in pair_cs.findall(C("constraint")) if x.get("type")=="max"]
if not mins:
    mins=[ET.SubElement(pair_cs,C("constraint"),{"id":"r29-mor-pair-min","type":"min","value":"1","field":"selections","scope":"parent","shared":"true","includeChildSelections":"false","includeChildForces":"false"})]
if not maxs:
    maxs=[ET.SubElement(pair_cs,C("constraint"),{"id":"r29-mor-pair-max","type":"max","value":"1","field":"selections","scope":"parent","shared":"true","includeChildSelections":"false","includeChildForces":"false"})]
for x in mins:x.set("value","1")
for x in maxs:x.set("value","1")

# Remove hard default from Bolt Pistols. A defaultAmount behaves as a locked/default
# selection in New Recruit and does not automatically swap out when another child is picked.
removed_default=bolt.attrib.pop("defaultAmount",None)

# No child-level minimums anywhere in the pair group.
removed_mins=[]
for e in pair.findall(f"./{C('selectionEntries')}/{C('selectionEntry')}"):
    cs=e.find(C("constraints"))
    if cs is None: continue
    for c in list(cs):
        if c.get("type")=="min":
            removed_mins.append((e.get("id"),c.get("id")))
            cs.remove(c)

# Ensure the known pair options are all direct children of the one-of group.
direct={e.get("id"):e for e in pair.findall(f"./{C('selectionEntries')}/{C('selectionEntry')}")}
expected=["r29-mor-bolt","r29-mor-hand","r29-mor-plasma","r29-mor-calibanite","r47-rg-mor-fulcrum-pair","r74-ba-moritat-two-inferno"]
missing=[x for x in expected if x not in direct]
if missing: raise RuntimeError("Moritat pair options missing from group: "+repr(missing))

root.set("revision","50")
tree.write(CAT,encoding="utf-8",xml_declaration=True)

ET.register_namespace("",INS)
it=ET.parse(IDX); ir=it.getroot()
for x in ir.iter(I("dataIndexEntry")):
    if x.get("filePath")=="Legiones Astartes.cat":x.set("dataRevision","50")
it.write(IDX,encoding="utf-8",xml_declaration=True)

rr=ET.parse(CAT).getroot(); rids={x.get("id"):x for x in rr.iter() if x.get("id")}; checks=[]
def ck(name,ok):
    checks.append((name,bool(ok)))
    if not ok:raise RuntimeError("R50 validation failed: "+name)

ck("CAT50",rr.get("revision")=="50")
ck("GST dependency remains 11",rr.get("gameSystemRevision")=="11")
ck("Index50",'dataRevision="50"' in IDX.read_text(encoding="utf-8"))
rp=rids["r29-mor-pair-group"]
rc=rp.find(C("constraints"))
ck("Pistol Pair min1",any(x.get("type")=="min" and x.get("value")=="1" for x in rc.findall(C("constraint"))))
ck("Pistol Pair max1",any(x.get("type")=="max" and x.get("value")=="1" for x in rc.findall(C("constraint"))))
rb=rids["r29-mor-bolt"]
ck("Bolt Pistols no hard default","defaultAmount" not in rb.attrib)
for eid in expected:
    e=rids[eid]; cs=e.find(C("constraints"))
    ck(eid+" has no child min",cs is None or not any(x.get("type")=="min" for x in cs.findall(C("constraint"))))
ck("Fulcrum remains +20",any(c.get("typeId")=="pts" and c.get("value")=="20" for c in rids["r47-rg-mor-fulcrum-pair"].findall(f"./{C('costs')}/{C('cost')}")))
ck("Fulcrum remains RG-gated","legion-xix" in ET.tostring(rids["r47-rg-mor-fulcrum-pair"],encoding="unicode"))
new=collections.Counter(x.get("id") for x in rr.iter() if x.get("id"))
worse={k:v for k,v in new.items() if v>max(1,baseline.get(k,0))}
ck("No new/worsened duplicate IDs",not worse)

OUT.write_text("\n".join([
"Live R50 — Moritat pistol selector final replacement semantics",
"Input CAT=49/GST=11 -> CAT=50/GST remains 11","",
"FIX:",
"- Pistol Pair is the only mandatory constraint: exactly one child must be chosen.",
"- Removed the hard defaultAmount from Two Bolt Pistols; this was what caused New Recruit to keep the Bolt Pistols selected when a replacement pair was chosen.",
"- No pistol-pair child has a minimum constraint.",
"- Player now explicitly chooses one legal pair: Bolt Pistols, Hand Flamers, Plasma Pistols, Calibanite Plasma Pistols, Raven Guard Fulcrum Hand Cannons, or Blood Angels Inferno Pistols where available.",
"- Raven Guard Fulcrum Hand Cannons remain +20 points and Raven Guard-only.",
f"- Previous Bolt default removed: {removed_default!r}.",
f"- Child minimums removed in this pass: {removed_mins}.","",
"VALIDATION:"
]+[f'- {"PASS" if ok else "FAIL"}: {n}' for n,ok in checks])+"\n",encoding="utf-8")
print(OUT.read_text())
