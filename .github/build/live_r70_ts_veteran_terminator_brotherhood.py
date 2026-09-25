from pathlib import Path
import copy, collections, xml.etree.ElementTree as ET

CAT=Path("Legiones-Astartes-Generic.cat")
IDX=Path("index.xml")
OUT=Path("inspection-ts-veteran-terminator-brotherhood.txt")
NS="http://www.battlescribe.net/schema/catalogueSchema"
INS="http://www.battlescribe.net/schema/dataIndexSchema"
ET.register_namespace("",NS)
C=lambda t:f"{{{NS}}}{t}"
I=lambda t:f"{{{INS}}}{t}"

tree=ET.parse(CAT); root=tree.getroot()
ids={x.get("id"):x for x in root.iter() if x.get("id")}
VET="veteran-unit"; TERM="terminator-unit"
for req in [VET,TERM,"r45-cult-veteran-unit","r45-cult-terminator-unit"]:
    if req not in ids: raise RuntimeError("Missing "+req)

def cont(p,tag):
    q=C(tag); x=p.find(q)
    if x is None: x=ET.SubElement(p,q)
    return x

def add_show(link, prefix, evidence):
    link.set("hidden","true")
    ms=cont(link,"modifiers")
    for m in list(ms):
        if (m.get("id") or "").startswith(prefix): ms.remove(m)
    for i,bid in enumerate(evidence):
        m=ET.SubElement(ms,C("modifier"),{"id":f"{prefix}{i}","type":"set","field":"hidden","value":"false"})
        cs=ET.SubElement(m,C("conditions"))
        ET.SubElement(cs,C("condition"),{"type":"atLeast","value":"1","field":"selections","scope":"root-entry","childId":bid,
          "shared":"true","includeChildSelections":"true","includeChildForces":"false"})

def parent_of(target):
    for p in root.iter():
        if target in list(p): return p
    return None

cult_names=["Pavoni","Raptora","Corvidae","Athanaeans","Pyrae"]
evidence={
 VET:["r45-veteran-unit-ts-brother","r45-veteran-unit-ts-brother-fellow","r45-ts-brotherhood","r45-ts-brotherhood-fellowship"],
 TERM:["r45-terminator-unit-ts-brother","r45-terminator-unit-ts-brother-fellow","r45-ts-brotherhood","r45-ts-brotherhood-fellowship"]
}

# Cult Arcana remains baseline. Cult Mastery appears only after Brotherhood is purchased.
for unit,cgid in [(VET,"r45-cult-veteran-unit"),(TERM,"r45-cult-terminator-unit")]:
    cg=ids[cgid]
    cults=list(cg.findall(f"./{C('selectionEntries')}/{C('selectionEntry')}"))
    if len(cults)!=5: raise RuntimeError(f"{unit}: expected 5 Cults, got {len(cults)}")
    for cult in cults:
        mastery=[x for x in cult.findall(f"./{C('infoLinks')}/{C('infoLink')}") if "Cult Mastery" in (x.get("name") or "")]
        arcana=[x for x in cult.findall(f"./{C('infoLinks')}/{C('infoLink')}") if "Cult Arcana" in (x.get("name") or "")]
        if len(mastery)!=1 or len(arcana)!=1: raise RuntimeError(f"{unit} {cult.get('name')}: Arcana/Mastery mismatch")
        arcana[0].set("hidden","false")
        add_show(mastery[0],f"r70-{unit}-mastery-show-",evidence[unit])

# Veterans already have the correct nested correlated power groups from R68.
vcg=ids["r45-cult-veteran-unit"]
vmap={x.get("name"):x for x in vcg.findall(f"./{C('selectionEntries')}/{C('selectionEntry')}")}
for name in cult_names:
    if name not in vmap: raise RuntimeError("Veteran missing Cult "+name)
    pgs=vmap[name].findall(f"./{C('selectionEntryGroups')}/{C('selectionEntryGroup')}")
    pgs=[g for g in pgs if "Psychic Brotherhood Power" in (g.get("name") or "")]
    if len(pgs)!=1: raise RuntimeError(f"Veteran {name}: expected one Brotherhood power group")

# Rebuild Terminator psychic selection from the proven Veteran POWER CONTENT,
# but do not rely on hidden=true -> show modifiers. New Recruit was enforcing
# the MIN constraint while still hiding the group. Instead each Cult owns a
# visible structural group with baseline MIN0/MAX0; Brotherhood changes both
# limits to 1, making exactly one power selectable.
tcg=ids["r45-cult-terminator-unit"]
tmap={x.get("name"):x for x in tcg.findall(f"./{C('selectionEntries')}/{C('selectionEntry')}")}
disc_for={"Pavoni":"biomancy","Raptora":"telekinesis","Corvidae":"divination","Athanaeans":"telepathy","Pyrae":"pyromancy"}
for name in cult_names:
    if name not in tmap: raise RuntimeError("Terminator missing Cult "+name)
    t=tmap[name]
    gs=cont(t,"selectionEntryGroups")
    # Remove every prior Brotherhood power group in this Cult, regardless of revision.
    for g in list(gs):
        if "Psychic Brotherhood Power" in (g.get("name") or ""):
            gs.remove(g)

    src=[g for g in vmap[name].findall(f"./{C('selectionEntryGroups')}/{C('selectionEntryGroup')}") if "Psychic Brotherhood Power" in (g.get("name") or "")][0]
    disc=disc_for[name]
    gid="r71-term-"+disc+"-powers"
    pg=ET.SubElement(gs,C("selectionEntryGroup"),{"id":gid,"name":"Psychic Brotherhood Power — choose 1","hidden":"false"})

    links=ET.SubElement(pg,C("entryLinks"))
    for j,l in enumerate(src.findall(f"./{C('entryLinks')}/{C('entryLink')}")):
        cl=copy.deepcopy(l)
        cl.set("id",f"r71-term-{disc}-power-{j}")
        # keep canonical targetId/name but give constraints unique IDs
        for c in cl.iter(C("constraint")):
            c.set("id",f"r71-term-{disc}-power-{j}-max")
        links.append(cl)

    mods=ET.SubElement(pg,C("modifiers"))
    cs=ET.SubElement(pg,C("constraints"))
    mn=ET.SubElement(cs,C("constraint"),{"id":gid+"-min","type":"min","value":"0","field":"selections","scope":"parent","shared":"true","includeChildSelections":"true","includeChildForces":"false"})
    mx=ET.SubElement(cs,C("constraint"),{"id":gid+"-max","type":"max","value":"0","field":"selections","scope":"parent","shared":"true","includeChildSelections":"true","includeChildForces":"false"})

    for i,bid in enumerate(evidence[TERM]):
        for field,value,suffix in [(mn.get("id"),"1","min1"),(mx.get("id"),"1","max1")]:
            m=ET.SubElement(mods,C("modifier"),{"id":f"{gid}-{suffix}-{i}","type":"set","field":field,"value":value})
            conds=ET.SubElement(m,C("conditions"))
            ET.SubElement(conds,C("condition"),{"type":"atLeast","value":"1","field":"selections","scope":"root-entry","childId":bid,
                "shared":"true","includeChildSelections":"true","includeChildForces":"false"})

old=ids.get("r19-ts-terminator-unit-brotherhood-powers")
if old is not None:
    p=parent_of(old)
    if p is None: raise RuntimeError("Old Terminator power pool parent missing")
    p.remove(old)

# Bump generic library revision and index.
oldrev=int(root.get("revision","0"))
newrev=oldrev+1
root.set("revision",str(newrev))
tree.write(CAT,encoding="utf-8",xml_declaration=True)

ET.register_namespace("",INS)
it=ET.parse(IDX); ir=it.getroot(); hit=False
for x in ir.iter(I("dataIndexEntry")):
    if x.get("filePath")=="Legiones-Astartes-Generic.cat":
        x.set("dataRevision",str(newrev)); hit=True
if not hit: raise RuntimeError("Generic index entry missing")
it.write(IDX,encoding="utf-8",xml_declaration=True)

# Validation after round-trip.
rr=ET.parse(CAT).getroot(); rid={x.get("id"):x for x in rr.iter() if x.get("id")}
checks=[]
def ck(n,v):
    checks.append((n,bool(v)))
    if not v: raise RuntimeError("Validation failed: "+n)

ck("Veteran Cult remains selectable","r45-cult-veteran-unit" in rid)
ck("Terminator Cult remains selectable","r45-cult-terminator-unit" in rid)
ck("Old Terminator sibling power pool removed","r19-ts-terminator-unit-brotherhood-powers" not in rid)
for unit,cgid in [(VET,"r45-cult-veteran-unit"),(TERM,"r45-cult-terminator-unit")]:
    cg=rid[cgid]
    for cult in cg.findall(f"./{C('selectionEntries')}/{C('selectionEntry')}"):
        arc=[x for x in cult.findall(f"./{C('infoLinks')}/{C('infoLink')}") if "Cult Arcana" in (x.get("name") or "")]
        mas=[x for x in cult.findall(f"./{C('infoLinks')}/{C('infoLink')}") if "Cult Mastery" in (x.get("name") or "")]
        ck(f"{unit} {cult.get('name')} Arcana baseline",len(arc)==1 and arc[0].get("hidden")=="false")
        ck(f"{unit} {cult.get('name')} Mastery Brotherhood-gated",len(mas)==1 and mas[0].get("hidden")=="true" and len(mas[0].findall(f"./{C('modifiers')}/{C('modifier')}"))>=4)
        pgs=[g for g in cult.findall(f"./{C('selectionEntryGroups')}/{C('selectionEntryGroup')}") if "Psychic Brotherhood Power" in (g.get("name") or "")]
        ck(f"{unit} {cult.get('name')} has one correlated power group",len(pgs)==1)
        ck(f"{unit} {cult.get('name')} has seven powers",len(pgs[0].findall(f"./{C('entryLinks')}/{C('entryLink')}"))==7)
        if unit==VET:
            ck(f"{unit} {cult.get('name')} power group hidden until Brotherhood",pgs[0].get("hidden")=="true")
        else:
            cons=pgs[0].findall(f"./{C('constraints')}/{C('constraint')}")
            ck(f"{unit} {cult.get('name')} power group structurally visible",pgs[0].get("hidden")!="true")
            ck(f"{unit} {cult.get('name')} baseline max0",any(c.get("type")=="max" and c.get("value")=="0" for c in cons))
            txt=ET.tostring(pgs[0],encoding="unicode")
            ck(f"{unit} {cult.get('name')} Brotherhood sets max1","max1" in txt and 'value="1"' in txt)

OUT.write_text("\n".join([
 "Thousand Sons Veteran + Legion Terminator Brotherhood psychic fix",
 f"Generic catalogue revision {oldrev} -> {newrev}","",
 "BEHAVIOUR:",
 "- Prosperine Cult selection remains available normally.",
 "- Cult Arcana remains the baseline benefit of choosing that Cult.",
 "- Purchasing Brotherhood of Psykers unlocks Cult Mastery.",
 "- Purchasing Brotherhood also unlocks exactly one psychic power from the selected Cult's correlated discipline.",
 "- Veteran and Legion Terminator Squads now use the same nested five-Cult/five-discipline architecture.",
 "- Fellowships of Prospero discounted Brotherhood is supported by the same gates.","",
 "VALIDATION:"
]+[f'- {"PASS" if ok else "FAIL"}: {n}' for n,ok in checks])+"\n",encoding="utf-8")
print(OUT.read_text())
