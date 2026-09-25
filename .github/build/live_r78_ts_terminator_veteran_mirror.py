from pathlib import Path
import copy, xml.etree.ElementTree as ET

CAT=Path("Legiones-Astartes-Generic.cat")
IDX=Path("index.xml")
OUT=Path("inspection-r78-ts-terminator-veteran-mirror.txt")
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

vet=next((g for g in root.iter(C("selectionEntryGroup")) if g.get("id")=="r45-cult-veteran-unit"),None)
term=next((g for g in root.iter(C("selectionEntryGroup")) if g.get("id")=="r45-cult-terminator-unit"),None)
if vet is None or term is None:
    raise RuntimeError("Canonical Veteran/Terminator Prosperine Cult group missing")

term_unit=next((a for a in ancestors(term) if a.tag==C("selectionEntry") and a.get("type") in ("unit","model")),None)
if term_unit is None:
    raise RuntimeError("Canonical Terminator unit missing")

brother_ids=[]
for e in term_unit.iter(C("entryLink")):
    if e.get("targetId") in ("r45-ts-brotherhood","r45-ts-brotherhood-fellowship"):
        brother_ids.append(e.get("id"))
brother_ids=[x for x in brother_ids if x]
expected={"r45-terminator-unit-ts-brother","r45-terminator-unit-ts-brother-fellow"}
if set(brother_ids)!=expected:
    raise RuntimeError("Unexpected Terminator Brotherhood IDs: "+repr(brother_ids))

disc={"Pavoni":"biomancy","Raptora":"telekinesis","Corvidae":"divination","Athanaeans":"telepathy","Pyrae":"pyromancy"}
vm={c.get("name"):c for c in vet.findall(f"./{C('selectionEntries')}/{C('selectionEntry')}")}
tm={c.get("name"):c for c in term.findall(f"./{C('selectionEntries')}/{C('selectionEntry')}")}

patched=0
for cname,d in disc.items():
    if cname not in vm or cname not in tm:
        raise RuntimeError("Missing Cult "+cname)
    vc=vm[cname]; tc=tm[cname]
    vgroups=[g for g in vc.findall(f"./{C('selectionEntryGroups')}/{C('selectionEntryGroup')}") if (g.get("name") or "")=="Psychic Brotherhood Power — choose 1"]
    if len(vgroups)!=1:
        raise RuntimeError(f"Veteran {cname}: expected one working power group, got {len(vgroups)}")
    src=vgroups[0]
    src_links=src.findall(f"./{C('entryLinks')}/{C('entryLink')}")
    if len(src_links)!=7:
        raise RuntimeError(f"Veteran {cname}: expected seven power links")

    gs=cont(tc,"selectionEntryGroups")
    # Remove every older Terminator psychic power group, regardless of revision/name.
    for g in list(gs):
        n=(g.get("name") or "").lower()
        gid=(g.get("id") or "").lower()
        if "psychic brotherhood" in n or ("term" in gid and "power" in gid):
            gs.remove(g)

    gid=f"r78-term-{d}-powers"
    g=ET.SubElement(gs,C("selectionEntryGroup"),{
        "id":gid,"name":"Psychic Brotherhood Power — choose 1","hidden":"true"
    })

    links=ET.SubElement(g,C("entryLinks"))
    for j,vl in enumerate(src_links):
        l=copy.deepcopy(vl)
        l.set("id",f"r78-term-{d}-power-{j}")
        # The working Veteran pattern has visible child links. Keep them visible;
        # Brotherhood gates the parent group, not every child independently.
        l.set("hidden","false")
        lm=l.find(C("modifiers"))
        if lm is not None:
            l.remove(lm)
        cs=l.find(C("constraints"))
        if cs is None:cs=ET.SubElement(l,C("constraints"))
        maxs=[c for c in cs.findall(C("constraint")) if c.get("type")=="max"]
        if maxs:
            maxs[0].set("id",f"r78-term-{d}-power-{j}-max")
            maxs[0].set("value","1")
            for extra in maxs[1:]:cs.remove(extra)
        else:
            ET.SubElement(cs,C("constraint"),{
                "id":f"r78-term-{d}-power-{j}-max","type":"max","value":"1",
                "field":"selections","scope":"parent","shared":"true",
                "includeChildSelections":"true","includeChildForces":"false"
            })
        links.append(l)

    mods=ET.SubElement(g,C("modifiers"))
    cons=ET.SubElement(g,C("constraints"))
    mn=ET.SubElement(cons,C("constraint"),{
        "id":gid+"-min","type":"min","value":"0","field":"selections","scope":"parent",
        "shared":"true","includeChildSelections":"true","includeChildForces":"false"
    })
    ET.SubElement(cons,C("constraint"),{
        "id":gid+"-max","type":"max","value":"1","field":"selections","scope":"parent",
        "shared":"true","includeChildSelections":"true","includeChildForces":"false"
    })

    for i,bid in enumerate(brother_ids):
        show=ET.SubElement(mods,C("modifier"),{
            "id":f"{gid}-show-{i}","type":"set","field":"hidden","value":"false"
        })
        sc=ET.SubElement(show,C("conditions"))
        ET.SubElement(sc,C("condition"),{
            "type":"atLeast","value":"1","field":"selections","scope":"root-entry",
            "childId":bid,"shared":"true","includeChildSelections":"true","includeChildForces":"false"
        })
        req=ET.SubElement(mods,C("modifier"),{
            "id":f"{gid}-min1-{i}","type":"set","field":mn.get("id"),"value":"1"
        })
        rc=ET.SubElement(req,C("conditions"))
        ET.SubElement(rc,C("condition"),{
            "type":"atLeast","value":"1","field":"selections","scope":"root-entry",
            "childId":bid,"shared":"true","includeChildSelections":"true","includeChildForces":"false"
        })

    # Clean Cult Mastery to the same local Brotherhood IDs only.
    mastery=[x for x in tc.findall(f"./{C('infoLinks')}/{C('infoLink')}") if "Cult Mastery" in (x.get("name") or "")]
    if len(mastery)!=1:
        raise RuntimeError(f"{cname}: expected one Cult Mastery")
    info=mastery[0]; info.set("hidden","true")
    ims=cont(info,"modifiers")
    for m in list(ims): ims.remove(m)
    for i,bid in enumerate(brother_ids):
        m=ET.SubElement(ims,C("modifier"),{
            "id":f"r78-term-{d}-mastery-show-{i}","type":"set","field":"hidden","value":"false"
        })
        cs=ET.SubElement(m,C("conditions"))
        ET.SubElement(cs,C("condition"),{
            "type":"atLeast","value":"1","field":"selections","scope":"root-entry",
            "childId":bid,"shared":"true","includeChildSelections":"true","includeChildForces":"false"
        })
    patched+=1

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

# Renderability validation: exact working Veteran architecture.
rr=ET.parse(CAT).getroot()
rid={x.get("id"):x for x in rr.iter() if x.get("id")}
tcg=rid["r45-cult-terminator-unit"]
for cult in tcg.findall(f"./{C('selectionEntries')}/{C('selectionEntry')}"):
    cname=cult.get("name")
    if cname not in disc: continue
    groups=[g for g in cult.findall(f"./{C('selectionEntryGroups')}/{C('selectionEntryGroup')}") if (g.get("name") or "")=="Psychic Brotherhood Power — choose 1"]
    if len(groups)!=1: raise RuntimeError(f"{cname}: expected exactly one R78 power group")
    g=groups[0]
    if g.get("hidden")!="true": raise RuntimeError(f"{cname}: parent must be hidden before Brotherhood")
    powers=g.findall(f"./{C('entryLinks')}/{C('entryLink')}")
    if len(powers)!=7: raise RuntimeError(f"{cname}: expected seven powers")
    if any(p.get("hidden")=="true" for p in powers):
        raise RuntimeError(f"{cname}: child power link still hidden")
    txt=ET.tostring(g,encoding="unicode")
    for bid in brother_ids:
        if bid not in txt: raise RuntimeError(f"{cname}: missing Brotherhood gate {bid}")
    if 'field="hidden" value="false"' not in txt:
        raise RuntimeError(f"{cname}: parent reveal modifier missing")
    if f'field="{g.get("id")}-min" value="1"' not in txt:
        raise RuntimeError(f"{cname}: mandatory power trigger missing")

OUT.write_text(
    "R78 TS Legion Terminator exact Veteran-pattern psychic fix\n"
    f"Generic revision {oldrev} -> {newrev}\n"
    f"Cults rebuilt: {patched}\n"
    "Architecture: parent power group hidden until local Brotherhood; seven child power links are always visible inside the revealed parent; MIN becomes 1 after Brotherhood.\n"
    "Removed accumulated child-link visibility modifiers from earlier Terminator attempts.\n",
    encoding="utf-8"
)
print(OUT.read_text())
