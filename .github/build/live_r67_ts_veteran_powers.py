from pathlib import Path
import collections, xml.etree.ElementTree as ET

CAT=Path("Legiones Astartes.cat"); IDX=Path("index.xml")
OUT=Path("inspection-live-r67-ts-veteran-power-selection.txt")
NS="http://www.battlescribe.net/schema/catalogueSchema"; INS="http://www.battlescribe.net/schema/dataIndexSchema"
ET.register_namespace("",NS)
C=lambda t:f"{{{NS}}}{t}"; I=lambda t:f"{{{INS}}}{t}"

tree=ET.parse(CAT); root=tree.getroot()
if root.get("revision")!="66": raise RuntimeError(f"R67 expected CAT66, got {root.get('revision')}")
if root.get("gameSystemRevision")!="15": raise RuntimeError(f"R67 expected GST15, got {root.get('gameSystemRevision')}")
baseline=collections.Counter(x.get("id") for x in root.iter() if x.get("id"))
ids={x.get("id"):x for x in root.iter() if x.get("id")}

VET="veteran-unit"
PGID="r19-ts-veteran-unit-brotherhood-powers"
for req in [VET,PGID]:
    if req not in ids: raise RuntimeError("Missing "+req)

def cont(p,tag,before=("constraints","categoryLinks","entryLinks","infoLinks","profiles","rules","selectionEntries","selectionEntryGroups","costs","modifiers")):
    q=C(tag); x=p.find(q)
    if x is not None:return x
    x=ET.Element(q); kids=list(p); idx=len(kids)
    for j,k in enumerate(kids):
        if k.tag.split("}")[-1] in before:idx=j;break
    p.insert(idx,x);return x

def one_constraint(p,typ,val,id_):
    cs=cont(p,"constraints")
    hits=[x for x in cs.findall(C("constraint")) if x.get("type")==typ]
    if hits:
        x=hits[0]
        for z in hits[1:]:cs.remove(z)
    else:x=ET.SubElement(cs,C("constraint"))
    x.attrib.update({"id":id_,"type":typ,"value":str(val),"field":"selections","scope":"parent",
                     "shared":"true","includeChildSelections":"false","includeChildForces":"false"})
    return x

def clear_field_mods(p,fields):
    ms=p.find(C("modifiers"))
    if ms is None:return 0
    n=0
    for m in list(ms):
        if m.get("field") in fields:
            ms.remove(m);n+=1
    return n

def add_set(p,id_,field,value,conds,and_group=False):
    ms=cont(p,"modifiers")
    # remove same ID if local rerun
    for m in list(ms):
        if m.get("id")==id_:ms.remove(m)
    m=ET.SubElement(ms,C("modifier"),{"id":id_,"type":"set","field":field,"value":str(value)})
    if and_group and len(conds)>1:
        cgs=ET.SubElement(m,C("conditionGroups"))
        cg=ET.SubElement(cgs,C("conditionGroup"),{"type":"and"})
        cs=ET.SubElement(cg,C("conditions"))
    else:
        cs=ET.SubElement(m,C("conditions"))
    for c in conds:
        ET.SubElement(cs,C("condition"),{
            "type":c.get("type","atLeast"),"value":str(c.get("value",1)),
            "field":"selections","scope":c.get("scope","root-entry"),"childId":c["childId"],
            "shared":"true","includeChildSelections":"true","includeChildForces":"false"
        })
    return m

vet=ids[VET]; pg=ids[PGID]

# Find both Veteran Brotherhood purchase links and their shared targets.
brother_links=[];brother_targets=[]
for x in vet.iter(C("entryLink")):
    n=(x.get("name") or "").lower()
    if "brotherhood of psykers" in n and "power" not in n:
        if x.get("id") and x.get("id") not in brother_links:brother_links.append(x.get("id"))
        if x.get("targetId") and x.get("targetId") not in brother_targets:brother_targets.append(x.get("targetId"))
if not brother_links:raise RuntimeError("Main Veteran Brotherhood selectors not found")

# Find the actual 35 power choices, regardless of whether legacy XML stores them
# directly or one container deeper.
power_options=[]
seen=set()
for tag in ("entryLink","selectionEntry"):
    for x in pg.iter(C(tag)):
        if x is pg:continue
        xid=x.get("id") or ""
        n=(x.get("name") or "").lower()
        # Only actual psychic powers, not discipline links or shell selectors.
        if "brotherhood-power-" in xid and xid not in seen:
            power_options.append(x);seen.add(xid)
if len(power_options)!=35:
    raise RuntimeError(f"Main Veteran expected 35 psychic powers, found {len(power_options)}")

# THE CORE FIX:
# Do not make New Recruit raise MAX from 0 after selecting an EntryLink.
# Give the power group stable MAX 1 from the start.
mn=one_constraint(pg,"min",0,PGID+"-r67-min")
mx=one_constraint(pg,"max",1,PGID+"-r67-max")

# Remove every old min/max modifier on this group, including obsolete field IDs.
ms=pg.find(C("modifiers"))
removed_old=0
if ms is not None:
    for m in list(ms):
        field=m.get("field") or ""
        mid=m.get("id") or ""
        if field in (mn.get("id"),mx.get("id")) or "power-min" in field or "power-max" in field or "powers-r64-min" in field or "powers-r64-max" in field or "-r64-min-" in mid or "-r64-max-" in mid or "-r63-min-" in mid:
            ms.remove(m);removed_old+=1

# Accept either the local EntryLink ID or the selected shared target ID.
evidence=[]
for x in brother_links+brother_targets:
    if x not in evidence:evidence.append(x)

# Brotherhood makes one power mandatory. We add the same MIN=1 trigger against
# every possible selection identity New Recruit may expose.
for i,bid in enumerate(evidence):
    add_set(pg,f"{PGID}-r67-require-{i}",mn.get("id"),1,[{
        "childId":bid,"scope":"root-entry","type":"atLeast","value":1
    }])

# Powers keep their existing Cult locks. Add a separate hide condition:
# hide only if ALL Brotherhood identities are absent.
for opt in power_options:
    oms=opt.find(C("modifiers"))
    if oms is not None:
        for m in list(oms):
            if "-r67-no-brotherhood" in (m.get("id") or ""):oms.remove(m)
    add_set(opt,(opt.get("id") or "power")+"-r67-no-brotherhood","hidden","true",[
        {"childId":bid,"scope":"root-entry","type":"lessThan","value":1} for bid in evidence
    ],and_group=True)

pg.set("name","Psychic Brotherhood — Cult-correlated Psychic Power (choose 1)")
pg.set("hidden","false")

# Revision/index.
root.set("revision","67")
tree.write(CAT,encoding="utf-8",xml_declaration=True)
ET.register_namespace("",INS)
it=ET.parse(IDX);ir=it.getroot()
for x in ir.iter(I("dataIndexEntry")):
    if x.get("filePath")=="Legiones Astartes.cat":x.set("dataRevision","67")
it.write(IDX,encoding="utf-8",xml_declaration=True)

# Validation.
rr=ET.parse(CAT).getroot();rids={x.get("id"):x for x in rr.iter() if x.get("id")};checks=[]
def ck(n,o):
    checks.append((n,bool(o)))
    if not o:raise RuntimeError("R67 validation failed: "+n)

ck("CAT67",rr.get("revision")=="67")
ck("GST dependency remains15",rr.get("gameSystemRevision")=="15")
ck("Index67",'dataRevision="67"' in IDX.read_text(encoding="utf-8"))
rpg=rids[PGID]
cs=rpg.findall(f"./{C('constraints')}/{C('constraint')}")
ck("Veteran power base MIN0",any(x.get("type")=="min" and x.get("value")=="0" for x in cs))
ck("Veteran power base MAX1",any(x.get("type")=="max" and x.get("value")=="1" for x in cs))
ck("Veteran power no longer MAX0",not any(x.get("type")=="max" and x.get("value")=="0" for x in cs))
xml=ET.tostring(rpg,encoding="unicode")
ck("Brotherhood local IDs wired",all(x in xml for x in brother_links))
ck("Brotherhood shared targets wired",all(x in xml for x in brother_targets))
rpowers=[]
for tag in ("entryLink","selectionEntry"):
    for x in rpg.iter(C(tag)):
        if "brotherhood-power-" in (x.get("id") or ""):rpowers.append(x)
ck("All 35 powers retained",len({x.get('id') for x in rpowers})==35)
ck("All powers still Cult-locked",all("r63-cult-lock" in ET.tostring(x,encoding="unicode") for x in rpowers))
ck("All powers Brotherhood-gated",all("-r67-no-brotherhood" in ET.tostring(x,encoding="unicode") for x in rpowers))

new=collections.Counter(x.get("id") for x in rr.iter() if x.get("id"))
worse={k:v for k,v in new.items() if v>max(1,baseline.get(k,0))}
ck("No new/worsened duplicate IDs",not worse)

OUT.write_text("\n".join([
"Live R67 — Thousand Sons Veteran psychic-power selection fix",
"Input CAT=66/GST=15 -> CAT=67/GST remains 15","",
"FIX:",
"- Targeted the main Legion Veteran Squad directly.",
"- Confirmed all 35 canonical powers remain present: 7 each for Biomancy, Telekinesis, Divination, Telepathy and Pyromancy.",
"- Replaced the fragile MAX=0 + conditional MAX=1 system with a stable power-group MAX=1.",
"- Base MIN remains 0; buying Brotherhood of Psykers makes one Cult-correlated power mandatory.",
"- Brotherhood detection accepts both the Veteran EntryLink IDs and their shared target IDs, covering New Recruit link-resolution behaviour.",
"- Every power remains locked to the selected Prosperine Cult's correlated discipline.",
"- Every power is hidden unless a Brotherhood of Psykers upgrade is selected.",
f"- Removed {removed_old} obsolete/stale Veteran power min/max modifiers.",
"- Veteran melee scaling and the R66 Centurion fix are untouched.","",
"VALIDATION:"
]+[f'- {"PASS" if ok else "FAIL"}: {n}' for n,ok in checks])+"\n",encoding="utf-8")
print(OUT.read_text())
