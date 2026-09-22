from pathlib import Path
import xml.etree.ElementTree as ET, collections

CAT=Path("Legiones Astartes.cat"); IDX=Path("index.xml")
OUT=Path("inspection-live-veteran-melee-scaling.txt")
NS="http://www.battlescribe.net/schema/catalogueSchema"; INS="http://www.battlescribe.net/schema/dataIndexSchema"
ET.register_namespace("",NS)
C=lambda t:f"{{{NS}}}{t}"; I=lambda t:f"{{{INS}}}{t}"

tree=ET.parse(CAT); root=tree.getroot()
oldrev=int(root.get("revision"))
ids={x.get("id"):x for x in root.iter() if x.get("id")}
v=ids["veteran-unit"]
g=next(x for x in v.findall(f"./{C('selectionEntryGroups')}/{C('selectionEntryGroup')}") if x.get("id")=="veteran-melee")
cs=g.find(C("constraints"))
mx=next(x for x in cs.findall(C("constraint")) if x.get("type")=="max")
mx.set("value","5")

# Remove the old repeat-based scaler.
ms=g.find(C("modifiers"))
removed=0
if ms is not None:
    for m in list(ms):
        if m.get("id")=="r29-veteran-melee-per-model":
            ms.remove(m); removed+=1
else:
    ms=ET.SubElement(g,C("modifiers"))

# Explicit total squad thresholds.
# veteran-included excludes the Sergeant, so 4 included = 5 total.
for included,total in [(5,6),(6,7),(7,8),(8,9),(9,10)]:
    mid=f"r59-veteran-melee-total-{total}"
    m=ET.SubElement(ms,C("modifier"),{"id":mid,"type":"set","field":"veteran-melee-max","value":str(total)})
    conds=ET.SubElement(m,C("conditions"))
    ET.SubElement(conds,C("condition"),{
        "type":"atLeast","value":str(included),"field":"selections","scope":"root-entry",
        "childId":"veteran-included","shared":"true","includeChildSelections":"false","includeChildForces":"false"
    })

newrev=oldrev+1
root.set("revision",str(newrev))
tree.write(CAT,encoding="utf-8",xml_declaration=True)

ET.register_namespace("",INS)
it=ET.parse(IDX); ir=it.getroot()
for x in ir.iter(I("dataIndexEntry")):
    if x.get("filePath")=="Legiones Astartes.cat":
        x.set("dataRevision",str(newrev))
it.write(IDX,encoding="utf-8",xml_declaration=True)

# Validate
rr=ET.parse(CAT).getroot(); rids={x.get("id"):x for x in rr.iter() if x.get("id")}
vg=next(x for x in rids["veteran-unit"].findall(f"./{C('selectionEntryGroups')}/{C('selectionEntryGroup')}") if x.get("id")=="veteran-melee")
vmx=next(x for x in vg.find(f"./{C('constraints')}").findall(C("constraint")) if x.get("type")=="max")
mods=vg.find(C("modifiers"))
checks=[
    ("revision bumped", rr.get("revision")==str(newrev)),
    ("base 5-man cap", vmx.get("value")=="5"),
    ("old repeat scaler removed", not any(x.get("id")=="r29-veteran-melee-per-model" for x in mods.findall(C("modifier")))),
    ("6-man threshold", any(x.get("id")=="r59-veteran-melee-total-6" and x.get("value")=="6" for x in mods.findall(C("modifier")))),
    ("10-man threshold", any(x.get("id")=="r59-veteran-melee-total-10" and x.get("value")=="10" for x in mods.findall(C("modifier")))),
]
for n,ok in checks:
    if not ok: raise RuntimeError("Validation failed: "+n)

OUT.write_text("\n".join([
    f"Veteran melee scaling fix: CAT {oldrev} -> {newrev}",
    f"- Removed old repeat-based scaler: {removed}",
    "- Close Combat Weapon Replacements now cap at total squad size:",
    "  5 models -> 5 replacements",
    "  6 models -> 6 replacements",
    "  7 models -> 7 replacements",
    "  8 models -> 8 replacements",
    "  9 models -> 9 replacements",
    "  10 models -> 10 replacements",
    "- Veteran Sergeant is correctly included in the allowance.",
    "",
    "VALIDATION:"
]+[f"- PASS: {n}" for n,_ in checks])+"\n",encoding="utf-8")
print(OUT.read_text())
