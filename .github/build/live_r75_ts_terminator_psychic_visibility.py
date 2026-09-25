from pathlib import Path
import xml.etree.ElementTree as ET

CAT=Path("Legiones-Astartes-Generic.cat")
IDX=Path("index.xml")
OUT=Path("inspection-r75-ts-terminator-psychic-visibility.txt")
NS="http://www.battlescribe.net/schema/catalogueSchema"
INS="http://www.battlescribe.net/schema/dataIndexSchema"
ET.register_namespace("",NS)
C=lambda t:f"{{{NS}}}{t}"
I=lambda t:f"{{{INS}}}{t}"

tree=ET.parse(CAT); root=tree.getroot()
parent={c:p for p in root.iter() for c in p}

def ancestors(x):
    out=[]
    while x in parent:
        x=parent[x]; out.append(x)
    return out

def cont(p,tag):
    x=p.find(C(tag))
    if x is None:x=ET.SubElement(p,C(tag))
    return x

TARGETS=[
    ("r45-ts-brotherhood","normal"),
    ("r45-ts-brotherhood-fellowship","fellow"),
]

patched_groups=0
patched_mastery=0

# Fix every Terminator Brotherhood power group, including copied/rite variants.
for g in list(root.iter(C("selectionEntryGroup"))):
    if (g.get("name") or "")!="Psychic Brotherhood Power — choose 1":
        continue
    an=ancestors(g)
    cult=next((x for x in an if x.tag==C("selectionEntry") and (x.get("name") or "") in {"Pavoni","Raptora","Corvidae","Athanaeans","Pyrae"}),None)
    if cult is None:continue
    # Only Terminator-derived Cult packages; leave working Veteran groups untouched.
    lineage=" ".join((x.get("id") or "") for x in an)
    if "terminator" not in lineage.lower():
        continue

    g.set("hidden","true")
    cons=cont(g,"constraints")
    mn=next((x for x in cons if x.get("type")=="min"),None)
    mx=next((x for x in cons if x.get("type")=="max"),None)
    if mn is None:
        mn=ET.SubElement(cons,C("constraint"),{"id":(g.get("id") or "r75-term")+"-min","type":"min","value":"0","field":"selections","scope":"parent","shared":"true","includeChildSelections":"true","includeChildForces":"false"})
    else:
        mn.set("value","0")
    if mx is None:
        mx=ET.SubElement(cons,C("constraint"),{"id":(g.get("id") or "r75-term")+"-max","type":"max","value":"1","field":"selections","scope":"parent","shared":"true","includeChildSelections":"true","includeChildForces":"false"})
    else:
        mx.set("value","1")

    mods=cont(g,"modifiers")
    # Remove only prior R75 target gates, making this rerunnable.
    for m in list(mods):
        if (m.get("id") or "").startswith("r75-term-target-"):
            mods.remove(m)

    for tid,label in TARGETS:
        m=ET.SubElement(mods,C("modifier"),{"id":f"r75-term-target-{g.get('id')}-{label}-show","type":"set","field":"hidden","value":"false"})
        cs=ET.SubElement(m,C("conditions"))
        ET.SubElement(cs,C("condition"),{"type":"atLeast","value":"1","field":"selections","scope":"root-entry","childId":tid,"shared":"true","includeChildSelections":"true","includeChildForces":"false"})

        m=ET.SubElement(mods,C("modifier"),{"id":f"r75-term-target-{g.get('id')}-{label}-min","type":"set","field":mn.get("id"),"value":"1"})
        cs=ET.SubElement(m,C("conditions"))
        ET.SubElement(cs,C("condition"),{"type":"atLeast","value":"1","field":"selections","scope":"root-entry","childId":tid,"shared":"true","includeChildSelections":"true","includeChildForces":"false"})
    patched_groups+=1

    # Cult Mastery on the same Cult should unlock from the same shared targets.
    for info in cult.findall(f"./{C('infoLinks')}/{C('infoLink')}"):
        if "Cult Mastery" not in (info.get("name") or ""):continue
        info.set("hidden","true")
        ims=cont(info,"modifiers")
        for m in list(ims):
            if (m.get("id") or "").startswith("r75-term-mastery-target-"):
                ims.remove(m)
        for tid,label in TARGETS:
            m=ET.SubElement(ims,C("modifier"),{"id":f"r75-term-mastery-target-{cult.get('id')}-{label}","type":"set","field":"hidden","value":"false"})
            cs=ET.SubElement(m,C("conditions"))
            ET.SubElement(cs,C("condition"),{"type":"atLeast","value":"1","field":"selections","scope":"root-entry","childId":tid,"shared":"true","includeChildSelections":"true","includeChildForces":"false"})
        patched_mastery+=1

if patched_groups<5:
    raise RuntimeError(f"Expected at least 5 Terminator Cult power groups, patched {patched_groups}")

oldrev=int(root.get("revision","0")); newrev=oldrev+1
root.set("revision",str(newrev))
tree.write(CAT,encoding="utf-8",xml_declaration=True)

ET.register_namespace("",INS)
it=ET.parse(IDX); ir=it.getroot(); hit=False
for x in ir.iter(I("dataIndexEntry")):
    if x.get("filePath")=="Legiones-Astartes-Generic.cat":
        x.set("dataRevision",str(newrev));hit=True
if not hit:raise RuntimeError("Generic index entry missing")
it.write(IDX,encoding="utf-8",xml_declaration=True)

# Round-trip validation.
rr=ET.parse(CAT).getroot()
checks=[]
for g in rr.iter(C("selectionEntryGroup")):
    if (g.get("name") or "")!="Psychic Brotherhood Power — choose 1":continue
    txt=ET.tostring(g,encoding="unicode")
    if "terminator" not in txt.lower() and "r74-term" not in (g.get("id") or ""):continue
    if (g.get("id") or "").startswith("r74-term") or "terminator" in (g.get("id") or "").lower():
        checks.append(
            'childId="r45-ts-brotherhood"' in txt and
            'childId="r45-ts-brotherhood-fellowship"' in txt and
            'field="hidden" value="false"' in txt
        )
if len(checks)<5 or not all(checks):
    raise RuntimeError(f"R75 validation failed: groups={len(checks)} pass={sum(checks)}")

OUT.write_text(
    "R75 Thousand Sons Terminator psychic visibility\n"
    f"Generic revision {oldrev} -> {newrev}\n"
    f"Patched Terminator Cult power groups: {patched_groups}\n"
    f"Patched Terminator Cult Mastery links: {patched_mastery}\n"
    "Each Terminator power group now listens to both the local Brotherhood link logic already present and the shared Brotherhood target IDs used successfully by Veterans.\n",
    encoding="utf-8"
)
print(OUT.read_text())
