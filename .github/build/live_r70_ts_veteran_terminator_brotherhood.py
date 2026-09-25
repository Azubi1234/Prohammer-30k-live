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

# Rebuild EVERY Legion Terminator Squad copy using the exact proven Veteran UI
# mechanism. New Recruit reliably renders this pattern:
# - group hidden by default
# - group MIN0 / MAX1
# - Brotherhood separately SHOWS the group and changes MIN to 1
# - individual powers stay ordinary visible MAX1 links (no per-power MAX0 locks)
disc_for={"Pavoni":"biomancy","Raptora":"telekinesis","Corvidae":"divination","Athanaeans":"telepathy","Pyrae":"pyromancy"}
shared_brother_targets={"r45-ts-brotherhood","r45-ts-brotherhood-fellowship"}

def direct_group(unit,name):
    return next((g for g in unit.findall(f"./{C('selectionEntryGroups')}/{C('selectionEntryGroup')}") if (g.get("name") or "")==name),None)

def rewrite_ids(node,prefix):
    # Give the cloned Veteran subtree unique Terminator IDs without changing
    # canonical power targetIds.
    for x in node.iter():
        xid=x.get("id")
        if xid:
            x.set("id",prefix+xid.replace("r68-vet-",""))
        field=x.get("field")
        if field and field.startswith("r68-vet-"):
            x.set("field",prefix+field.replace("r68-vet-",""))

def wire_terminator_copy(unit,serial):
    cg=direct_group(unit,"Prosperine Cult")
    if cg is None:
        return False

    cults={x.get("name"):x for x in cg.findall(f"./{C('selectionEntries')}/{C('selectionEntry')}")}
    if not all(n in cults for n in cult_names):
        raise RuntimeError(f"{unit.get('id')}: incomplete Prosperine Cult choices")

    local_brothers=[
        x for x in unit.iter(C("entryLink"))
        if x.get("targetId") in shared_brother_targets and x.get("id")
    ]
    if not local_brothers:
        raise RuntimeError(f"{unit.get('id')}: no Brotherhood entryLinks found")
    gate_evidence=[x.get("id") for x in local_brothers]

    # Delete every obsolete direct Terminator psychic selector. Cult choice itself
    # determines discipline, so no sibling Discipline/Cult Power selector belongs here.
    direct=cont(unit,"selectionEntryGroups")
    for g in list(direct):
        if "Psychic Brotherhood" in (g.get("name") or ""):
            direct.remove(g)

    for name in cult_names:
        cult=cults[name]
        disc=disc_for[name]

        # Arcana is baseline; Mastery is Brotherhood-gated.
        infos=cont(cult,"infoLinks")
        arc=[x for x in infos.findall(C("infoLink")) if "Cult Arcana" in (x.get("name") or "")]
        mas=[x for x in infos.findall(C("infoLink")) if "Cult Mastery" in (x.get("name") or "")]
        if len(arc)!=1 or len(mas)!=1:
            raise RuntimeError(f"{unit.get('id')} {name}: Arcana/Mastery mismatch")
        arc[0].set("hidden","false")
        add_show(mas[0],f"r74-term-{serial}-{disc}-mastery-show-",gate_evidence)

        gs=cont(cult,"selectionEntryGroups")
        for g in list(gs):
            if "Psychic Brotherhood Power" in (g.get("name") or ""):
                gs.remove(g)

        # Start from the working Veteran power content, but rebuild the group's
        # gating modifiers for this Terminator copy.
        src=[g for g in vmap[name].findall(f"./{C('selectionEntryGroups')}/{C('selectionEntryGroup')}") if "Psychic Brotherhood Power" in (g.get("name") or "")][0]
        pg=copy.deepcopy(src)
        prefix=f"r74-term-{serial}-{disc}-"
        rewrite_ids(pg,prefix)
        pg.set("id",prefix+"powers")
        pg.set("name","Psychic Brotherhood Power — choose 1")
        pg.set("hidden","true")

        # Power entries remain plain visible MAX1 choices.
        for j,power in enumerate(pg.findall(f"./{C('entryLinks')}/{C('entryLink')}")):
            power.set("id",prefix+f"power-{j}")
            power.set("hidden","false")
            pmods=power.find(C("modifiers"))
            if pmods is not None:
                power.remove(pmods)
            pcs=cont(power,"constraints")
            maxes=[c for c in pcs.findall(C("constraint")) if c.get("type")=="max"]
            if maxes:
                maxc=maxes[0]
                maxc.set("id",prefix+f"power-{j}-max")
                maxc.set("value","1")
                for extra in maxes[1:]:
                    pcs.remove(extra)
            else:
                ET.SubElement(pcs,C("constraint"),{
                    "id":prefix+f"power-{j}-max","type":"max","value":"1",
                    "field":"selections","scope":"parent","shared":"true",
                    "includeChildSelections":"true","includeChildForces":"false"
                })

        # Replace inherited Veteran group modifiers/constraints with the exact
        # simple show + min1 pattern, keyed only to this unit's Brotherhood links.
        oldmods=pg.find(C("modifiers"))
        if oldmods is not None:
            pg.remove(oldmods)
        oldcons=pg.find(C("constraints"))
        if oldcons is not None:
            pg.remove(oldcons)

        mods=ET.SubElement(pg,C("modifiers"))
        cons=ET.SubElement(pg,C("constraints"))
        mn=ET.SubElement(cons,C("constraint"),{
            "id":prefix+"min","type":"min","value":"0","field":"selections",
            "scope":"parent","shared":"true","includeChildSelections":"true","includeChildForces":"false"
        })
        ET.SubElement(cons,C("constraint"),{
            "id":prefix+"max","type":"max","value":"1","field":"selections",
            "scope":"parent","shared":"true","includeChildSelections":"true","includeChildForces":"false"
        })
        for i,bid in enumerate(gate_evidence):
            show=ET.SubElement(mods,C("modifier"),{
                "id":prefix+f"show-{i}","type":"set","field":"hidden","value":"false"
            })
            sc=ET.SubElement(show,C("conditions"))
            ET.SubElement(sc,C("condition"),{
                "type":"atLeast","value":"1","field":"selections","scope":"root-entry",
                "childId":bid,"shared":"true","includeChildSelections":"true","includeChildForces":"false"
            })
            req=ET.SubElement(mods,C("modifier"),{
                "id":prefix+f"min1-{i}","type":"set","field":mn.get("id"),"value":"1"
            })
            rc=ET.SubElement(req,C("conditions"))
            ET.SubElement(rc,C("condition"),{
                "type":"atLeast","value":"1","field":"selections","scope":"root-entry",
                "childId":bid,"shared":"true","includeChildSelections":"true","includeChildForces":"false"
            })

        gs.append(pg)
    return True

term_copies=[
    e for e in root.iter(C("selectionEntry"))
    if (e.get("name") or "")=="Legion Terminator Squad"
    and direct_group(e,"Prosperine Cult") is not None
]
if not term_copies:
    raise RuntimeError("No Legion Terminator Squad copies with Prosperine Cult found")

wired=[]
for i,unit in enumerate(term_copies):
    serial=f"{i}-{(unit.get('id') or 'term').replace(' ','-')[:40]}"
    if wire_terminator_copy(unit,serial):
        wired.append(unit.get("id"))

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
ck("Old Terminator sibling power pools removed",not any((g.get("name") or "")=="Psychic Brotherhood — Cult Power (requires Brotherhood; choose 1)" for g in rr.iter(C("selectionEntryGroup"))))

# Veterans remain unchanged and continue to use their known-good R68 pattern.
vcg2=rid["r45-cult-veteran-unit"]
for cult in vcg2.findall(f"./{C('selectionEntries')}/{C('selectionEntry')}"):
    pgs=[g for g in cult.findall(f"./{C('selectionEntryGroups')}/{C('selectionEntryGroup')}") if "Psychic Brotherhood Power" in (g.get("name") or "")]
    ck(f"veteran {cult.get('name')} has one power group",len(pgs)==1)
    ck(f"veteran {cult.get('name')} has seven powers",len(pgs[0].findall(f"./{C('entryLinks')}/{C('entryLink')}"))==7)

# Every live Legion Terminator Squad copy with a Prosperine Cult must now use
# the same hidden/show + MIN gating pattern as working Veterans.
validated_terms=0
for unit in rr.iter(C("selectionEntry")):
    if (unit.get("name") or "")!="Legion Terminator Squad":
        continue
    cg=next((g for g in unit.findall(f"./{C('selectionEntryGroups')}/{C('selectionEntryGroup')}") if (g.get("name") or "")=="Prosperine Cult"),None)
    if cg is None:
        continue
    validated_terms+=1
    direct=unit.findall(f"./{C('selectionEntryGroups')}/{C('selectionEntryGroup')}")
    ck(f"{unit.get('id')} no sibling Brotherhood selectors",not any("Psychic Brotherhood" in (g.get("name") or "") for g in direct))
    for cult in cg.findall(f"./{C('selectionEntries')}/{C('selectionEntry')}"):
        mas=[x for x in cult.findall(f"./{C('infoLinks')}/{C('infoLink')}") if "Cult Mastery" in (x.get("name") or "")]
        ck(f"{unit.get('id')} {cult.get('name')} mastery gated",len(mas)==1 and mas[0].get("hidden")=="true")
        pgs=[g for g in cult.findall(f"./{C('selectionEntryGroups')}/{C('selectionEntryGroup')}") if "Psychic Brotherhood Power" in (g.get("name") or "")]
        ck(f"{unit.get('id')} {cult.get('name')} one nested power group",len(pgs)==1)
        if len(pgs)==1:
            pg=pgs[0]
            cons=pg.findall(f"./{C('constraints')}/{C('constraint')}")
            powers=pg.findall(f"./{C('entryLinks')}/{C('entryLink')}")
            mods=pg.findall(f"./{C('modifiers')}/{C('modifier')}")
            ck(f"{unit.get('id')} {cult.get('name')} seven powers",len(powers)==7)
            ck(f"{unit.get('id')} {cult.get('name')} hidden baseline",pg.get("hidden")=="true")
            ck(f"{unit.get('id')} {cult.get('name')} min0",any(c.get("type")=="min" and c.get("value")=="0" for c in cons))
            ck(f"{unit.get('id')} {cult.get('name')} max1",any(c.get("type")=="max" and c.get("value")=="1" for c in cons))
            ck(f"{unit.get('id')} {cult.get('name')} has show gate",any(m.get("field")=="hidden" and m.get("value")=="false" for m in mods))
            ck(f"{unit.get('id')} {cult.get('name')} has min1 gate",any(m.get("value")=="1" and (m.get("field") or "").endswith("-min") for m in mods))
            for power in powers:
                pmax=next((c for c in power.findall(f"./{C('constraints')}/{C('constraint')}") if c.get("type")=="max"),None)
                ck(f"{power.get('id')} plain max1",pmax is not None and pmax.get("value")=="1")
                ck(f"{power.get('id')} no lock modifiers",not power.findall(f"./{C('modifiers')}/{C('modifier')}"))
ck("At least one Terminator copy validated",validated_terms>0)

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
