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

BROTHERHOOD_TARGETS=[
    ("r45-ts-brotherhood","normal"),
    ("r45-ts-brotherhood-fellowship","fellow"),
]

patched_groups=0
patched_links=0
patched_mastery=0

for g in list(root.iter(C("selectionEntryGroup"))):
    if (g.get("name") or "")!="Psychic Brotherhood Power — choose 1":
        continue
    an=ancestors(g)
    cult=next((x for x in an if x.tag==C("selectionEntry") and (x.get("name") or "") in {"Pavoni","Raptora","Corvidae","Athanaeans","Pyrae"}),None)
    if cult is None:
        continue
    lineage=" ".join((x.get("id") or "") for x in an)
    if "terminator" not in lineage.lower():
        continue

    # New Recruit reliably enforces the min modifier, but on these nested
    # Terminator groups it does not reliably honor hidden=true -> visible.
    # Keep the GROUP structurally visible and gate the individual spell links.
    g.set("hidden","false")

    cons=cont(g,"constraints")
    mn=next((x for x in cons if x.get("type")=="min"),None)
    mx=next((x for x in cons if x.get("type")=="max"),None)
    if mn is None:
        mn=ET.SubElement(cons,C("constraint"),{
            "id":(g.get("id") or "r76-term")+"-min","type":"min","value":"0",
            "field":"selections","scope":"parent","shared":"true",
            "includeChildSelections":"true","includeChildForces":"false"})
    else:
        mn.set("value","0")
    if mx is None:
        mx=ET.SubElement(cons,C("constraint"),{
            "id":(g.get("id") or "r76-term")+"-max","type":"max","value":"1",
            "field":"selections","scope":"parent","shared":"true",
            "includeChildSelections":"true","includeChildForces":"false"})
    else:
        mx.set("value","1")

    # Remove every modifier that tries to control the GROUP's hidden state.
    # Those are the exact modifiers New Recruit is failing to render.
    mods=cont(g,"modifiers")
    for m in list(mods):
        if m.get("field")=="hidden" or (m.get("id") or "").startswith("r76-term-min-"):
            mods.remove(m)

    # Rebuild only the mandatory-selection trigger. These shared target IDs
    # are already proven to fire because they are what produced the user's
    # visible "requires 1 selection" error.
    for tid,label in BROTHERHOOD_TARGETS:
        m=ET.SubElement(mods,C("modifier"),{
            "id":f"r76-term-min-{g.get('id')}-{label}",
            "type":"set","field":mn.get("id"),"value":"1"})
        cs=ET.SubElement(m,C("conditions"))
        ET.SubElement(cs,C("condition"),{
            "type":"atLeast","value":"1","field":"selections","scope":"root-entry",
            "childId":tid,"shared":"true","includeChildSelections":"true",
            "includeChildForces":"false"})

    links=cont(g,"entryLinks")
    power_links=list(links.findall(C("entryLink")))
    if len(power_links)!=7:
        raise RuntimeError(f"{g.get('id')}: expected 7 powers, found {len(power_links)}")

    for link in power_links:
        link.set("hidden","true")
        lmods=cont(link,"modifiers")
        for m in list(lmods):
            if (m.get("id") or "").startswith("r76-term-power-show-"):
                lmods.remove(m)
        for tid,label in BROTHERHOOD_TARGETS:
            m=ET.SubElement(lmods,C("modifier"),{
                "id":f"r76-term-power-show-{link.get('id')}-{label}",
                "type":"set","field":"hidden","value":"false"})
            cs=ET.SubElement(m,C("conditions"))
            ET.SubElement(cs,C("condition"),{
                "type":"atLeast","value":"1","field":"selections","scope":"root-entry",
                "childId":tid,"shared":"true","includeChildSelections":"true",
                "includeChildForces":"false"})
        patched_links+=1

    # Cult Mastery uses the same Brotherhood trigger.
    for info in cult.findall(f"./{C('infoLinks')}/{C('infoLink')}"):
        if "Cult Mastery" not in (info.get("name") or ""):
            continue
        info.set("hidden","true")
        ims=cont(info,"modifiers")
        for m in list(ims):
            if (m.get("id") or "").startswith("r76-term-mastery-"):
                ims.remove(m)
        for tid,label in BROTHERHOOD_TARGETS:
            m=ET.SubElement(ims,C("modifier"),{
                "id":f"r76-term-mastery-{cult.get('id')}-{label}",
                "type":"set","field":"hidden","value":"false"})
            cs=ET.SubElement(m,C("conditions"))
            ET.SubElement(cs,C("condition"),{
                "type":"atLeast","value":"1","field":"selections","scope":"root-entry",
                "childId":tid,"shared":"true","includeChildSelections":"true",
                "includeChildForces":"false"})
        patched_mastery+=1

    patched_groups+=1

if patched_groups<5:
    raise RuntimeError(f"Expected at least 5 Terminator Cult power groups, patched {patched_groups}")

oldrev=int(root.get("revision","0")); newrev=oldrev+1
root.set("revision",str(newrev))
tree.write(CAT,encoding="utf-8",xml_declaration=True)

ET.register_namespace("",INS)
it=ET.parse(IDX); ir=it.getroot(); hit=False
for x in ir.iter(I("dataIndexEntry")):
    if x.get("filePath")=="Legiones-Astartes-Generic.cat":
        x.set("dataRevision",str(newrev)); hit=True
if not hit:
    raise RuntimeError("Generic index entry missing")
it.write(IDX,encoding="utf-8",xml_declaration=True)

# Round-trip validation of the canonical Terminator Cult package.
rr=ET.parse(CAT).getroot()
rid={x.get("id"):x for x in rr.iter() if x.get("id")}
tcg=rid["r45-cult-terminator-unit"]
cults=tcg.findall(f"./{C('selectionEntries')}/{C('selectionEntry')}")
if len(cults)!=5:
    raise RuntimeError(f"Canonical Terminator Cult count {len(cults)}")
for cult in cults:
    groups=[g for g in cult.findall(f"./{C('selectionEntryGroups')}/{C('selectionEntryGroup')}") if (g.get("name") or "")=="Psychic Brotherhood Power — choose 1"]
    if len(groups)!=1:
        raise RuntimeError(f"{cult.get('name')}: power group count {len(groups)}")
    g=groups[0]
    if g.get("hidden")=="true":
        raise RuntimeError(f"{cult.get('name')}: group still hidden")
    powers=g.findall(f"./{C('entryLinks')}/{C('entryLink')}")
    if len(powers)!=7:
        raise RuntimeError(f"{cult.get('name')}: power count {len(powers)}")
    for link in powers:
        if link.get("hidden")!="true":
            raise RuntimeError(f"{cult.get('name')} {link.get('name')}: power not Brotherhood-gated")
        txt=ET.tostring(link,encoding="unicode")
        if 'childId="r45-ts-brotherhood"' not in txt or 'field="hidden" value="false"' not in txt:
            raise RuntimeError(f"{cult.get('name')} {link.get('name')}: normal Brotherhood reveal missing")
    gtxt=ET.tostring(g,encoding="unicode")
    if 'field="'+next(c.get("id") for c in g.findall(f"./{C('constraints')}/{C('constraint')}") if c.get("type")=="min")+'" value="1"' not in gtxt:
        raise RuntimeError(f"{cult.get('name')}: Brotherhood min1 trigger missing")

OUT.write_text(
    "R76-style TS Terminator psychic rendering fix\n"
    f"Generic revision {oldrev} -> {newrev}\n"
    f"Patched Terminator power groups: {patched_groups}\n"
    f"Brotherhood-gated power links: {patched_links}\n"
    f"Brotherhood-gated Cult Mastery links: {patched_mastery}\n"
    "Architecture: power group is structurally visible; each of its seven spell links is hidden until Brotherhood. Brotherhood also turns MIN 0 into MIN 1.\n",
    encoding="utf-8"
)
print(OUT.read_text())
