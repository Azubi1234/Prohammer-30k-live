from pathlib import Path
import xml.etree.ElementTree as ET

CAT=Path("Legiones-Astartes-Generic.cat")
IDX=Path("index.xml")
OUT=Path("inspection-r77-ts-terminator-local-brotherhood.txt")
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

cg=next((g for g in root.iter(C("selectionEntryGroup")) if g.get("id")=="r45-cult-terminator-unit"),None)
if cg is None:
    raise RuntimeError("Canonical Terminator Cult group missing")

unit=next((a for a in ancestors(cg) if a.tag==C("selectionEntry") and a.get("type") in ("unit","model")),None)
if unit is None:
    raise RuntimeError("Canonical Terminator containing unit missing")

local=[]
for e in unit.iter(C("entryLink")):
    if e.get("targetId") in ("r45-ts-brotherhood","r45-ts-brotherhood-fellowship"):
        local.append(e.get("id"))
local=[x for x in local if x]
if set(local)!={"r45-terminator-unit-ts-brother","r45-terminator-unit-ts-brother-fellow"}:
    raise RuntimeError("Unexpected canonical Terminator Brotherhood IDs: "+repr(local))

patched_powers=0
patched_mastery=0
patched_groups=0

for cult in cg.findall(f"./{C('selectionEntries')}/{C('selectionEntry')}"):
    groups=[g for g in cult.findall(f"./{C('selectionEntryGroups')}/{C('selectionEntryGroup')}") if (g.get("name") or "")=="Psychic Brotherhood Power — choose 1"]
    if len(groups)!=1:
        raise RuntimeError(f"{cult.get('name')}: expected one power group, got {len(groups)}")
    g=groups[0]
    g.set("hidden","false")

    cons=cont(g,"constraints")
    mn=next((c for c in cons if c.get("type")=="min"),None)
    mx=next((c for c in cons if c.get("type")=="max"),None)
    if mn is None or mx is None:
        raise RuntimeError(f"{cult.get('name')}: min/max constraints missing")
    mn.set("value","0"); mx.set("value","1")

    gmods=cont(g,"modifiers")
    for m in list(gmods):
        if (m.get("id") or "").startswith("r77-term-local-min-"):
            gmods.remove(m)
    for bid in local:
        m=ET.SubElement(gmods,C("modifier"),{
            "id":f"r77-term-local-min-{g.get('id')}-{bid}",
            "type":"set","field":mn.get("id"),"value":"1"})
        cs=ET.SubElement(m,C("conditions"))
        ET.SubElement(cs,C("condition"),{
            "type":"atLeast","value":"1","field":"selections","scope":"root-entry",
            "childId":bid,"shared":"true","includeChildSelections":"true","includeChildForces":"false"})
    patched_groups+=1

    powers=g.findall(f"./{C('entryLinks')}/{C('entryLink')}")
    if len(powers)!=7:
        raise RuntimeError(f"{cult.get('name')}: expected 7 powers, got {len(powers)}")
    for link in powers:
        link.set("hidden","true")
        mods=cont(link,"modifiers")
        for m in list(mods):
            if (m.get("id") or "").startswith("r77-term-local-show-"):
                mods.remove(m)
        for bid in local:
            m=ET.SubElement(mods,C("modifier"),{
                "id":f"r77-term-local-show-{link.get('id')}-{bid}",
                "type":"set","field":"hidden","value":"false"})
            cs=ET.SubElement(m,C("conditions"))
            ET.SubElement(cs,C("condition"),{
                "type":"atLeast","value":"1","field":"selections","scope":"root-entry",
                "childId":bid,"shared":"true","includeChildSelections":"true","includeChildForces":"false"})
        patched_powers+=1

    mastery=[x for x in cult.findall(f"./{C('infoLinks')}/{C('infoLink')}") if "Cult Mastery" in (x.get("name") or "")]
    if len(mastery)!=1:
        raise RuntimeError(f"{cult.get('name')}: expected one Cult Mastery")
    info=mastery[0]
    info.set("hidden","true")
    mods=cont(info,"modifiers")
    for m in list(mods):
        if (m.get("id") or "").startswith("r77-term-local-mastery-"):
            mods.remove(m)
    for bid in local:
        m=ET.SubElement(mods,C("modifier"),{
            "id":f"r77-term-local-mastery-{cult.get('id')}-{bid}",
            "type":"set","field":"hidden","value":"false"})
        cs=ET.SubElement(m,C("conditions"))
        ET.SubElement(cs,C("condition"),{
            "type":"atLeast","value":"1","field":"selections","scope":"root-entry",
            "childId":bid,"shared":"true","includeChildSelections":"true","includeChildForces":"false"})
    patched_mastery+=1

oldrev=int(root.get("revision","0")); newrev=oldrev+1
root.set("revision",str(newrev))
tree.write(CAT,encoding="utf-8",xml_declaration=True)

ET.register_namespace("",INS)
it=ET.parse(IDX); ir=it.getroot(); hit=False
for x in ir.iter(I("dataIndexEntry")):
    if x.get("filePath")=="Legiones-Astartes-Generic.cat":
        x.set("dataRevision",str(newrev)); hit=True
if not hit: raise RuntimeError("Generic index entry missing")
it.write(IDX,encoding="utf-8",xml_declaration=True)

OUT.write_text(
    "R77 TS canonical Legion Terminator Brotherhood local-ID fix\n"
    f"Generic revision {oldrev} -> {newrev}\n"
    f"Power groups patched: {patched_groups}\n"
    f"Power links patched: {patched_powers}\n"
    f"Cult Mastery links patched: {patched_mastery}\n"
    "Only canonical r45-cult-terminator-unit was changed; other Legion-specific Terminator copies were left untouched.\n",
    encoding="utf-8")
print(OUT.read_text())
