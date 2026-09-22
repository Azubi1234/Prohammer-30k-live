from pathlib import Path
import copy, collections, hashlib, re, xml.etree.ElementTree as ET

CAT=Path("Legiones Astartes.cat"); IDX=Path("index.xml")
OUT=Path("inspection-live-r57-centurion-psychic-ui.txt")
NS="http://www.battlescribe.net/schema/catalogueSchema"; INS="http://www.battlescribe.net/schema/dataIndexSchema"
ET.register_namespace("",NS)
C=lambda t:f"{{{NS}}}{t}"; I=lambda t:f"{{{INS}}}{t}"

tree=ET.parse(CAT); root=tree.getroot()
if root.get("revision")!="56": raise RuntimeError(f"R57 expected CAT56, got {root.get('revision')}")
if root.get("gameSystemRevision")!="14": raise RuntimeError(f"R57 expected GST dependency 14, got {root.get('gameSystemRevision')}")
baseline=collections.Counter(x.get("id") for x in root.iter() if x.get("id"))
ids={x.get("id"):x for x in root.iter() if x.get("id")}

def cont(p,tag,before=("constraints","categoryLinks","entryLinks","infoLinks","profiles","rules","selectionEntries","selectionEntryGroups","costs","modifiers")):
    q=C(tag); x=p.find(q)
    if x is not None: return x
    x=ET.Element(q); kids=list(p); idx=len(kids)
    for j,k in enumerate(kids):
        if k.tag.split("}")[-1] in before: idx=j; break
    p.insert(idx,x); return x

def cons(p,id_,typ,val,field="selections",scope="parent",child=False):
    cs=cont(p,"constraints"); x=next((z for z in cs.findall(C("constraint")) if z.get("id")==id_),None)
    if x is None: x=ET.SubElement(cs,C("constraint"))
    x.attrib.update({"id":id_,"type":typ,"value":str(val),"field":field,"scope":scope,"shared":"true","includeChildSelections":"true" if child else "false","includeChildForces":"false"})
    return x

def modifier(p,id_,typ,field,value,conds):
    ms=cont(p,"modifiers"); x=next((z for z in ms.findall(C("modifier")) if z.get("id")==id_),None)
    if x is None: x=ET.SubElement(ms,C("modifier"))
    x.attrib.update({"id":id_,"type":typ,"field":field,"value":str(value)})
    for ch in list(x): x.remove(ch)
    if len(conds)==1:
        target=ET.SubElement(x,C("conditions"))
    else:
        cgs=ET.SubElement(x,C("conditionGroups")); cg=ET.SubElement(cgs,C("conditionGroup"),{"type":"and"}); target=ET.SubElement(cg,C("conditions"))
    for c in conds:
        ET.SubElement(target,C("condition"),{
            "type":c.get("type","atLeast"),"value":str(c.get("value",1)),
            "field":"selections","scope":c.get("scope","roster"),"childId":c["childId"],
            "shared":"true","includeChildSelections":"true","includeChildForces":"false"
        })
    return x

def add_infolink(p,id_,name,target,typ="rule"):
    ils=cont(p,"infoLinks"); x=ET.SubElement(ils,C("infoLink"),{"id":id_,"name":name,"targetId":target,"type":typ,"hidden":"false"})
    return x

def add_rule(p,id_,name,text):
    rs=cont(p,"rules"); r=ET.SubElement(rs,C("rule"),{"id":id_,"name":name,"hidden":"false"}); d=ET.SubElement(r,C("description")); d.text=text
    return r

cent=ids.get("hq-centurion")
if cent is None: raise RuntimeError("Legion Centurion missing")

# Capture the current canonical Cult targets and power targets before removing the fragile groups.
cent_groups=cent.find(C("selectionEntryGroups"))
if cent_groups is None: raise RuntimeError("Centurion selectionEntryGroups missing")
cult_candidates=[x for x in cent_groups.findall(C("selectionEntryGroup")) if x.get("id")=="r45-cult-hq-centurion"]
power_candidates=[x for x in cent_groups.findall(C("selectionEntryGroup")) if x.get("id")=="r19-ts-centurion-powers"]
if not cult_candidates or not power_candidates: raise RuntimeError("Existing direct TS Centurion psychic groups missing")
old_cult=max(cult_candidates,key=lambda g: len(list(g.iter(C("entryLink")))))
old_power=max(power_candidates,key=lambda g: len(list(g.iter(C("entryLink")))))

cult_targets={}
for l in old_cult.iter(C("entryLink")):
    cult_targets[l.get("name")]=l.get("targetId")

disc_power_targets=collections.defaultdict(list)
for l in old_power.iter(C("entryLink")):
    lid=l.get("id") or ""
    m=re.match(r"r19-ts-centurion-power-(biomancy|divination|pyromancy|telekinesis|telepathy)-",lid)
    if m:
        disc_power_targets[m.group(1)].append((l.get("name"),l.get("targetId")))

expected_cults={"Pavoni","Raptora","Corvidae","Athanaeans","Pyrae"}
if set(cult_targets)!=expected_cults: raise RuntimeError(f"Unexpected Cult targets: {cult_targets}")
for d in ["biomancy","divination","pyromancy","telekinesis","telepathy"]:
    if not disc_power_targets[d]: raise RuntimeError("No powers captured for "+d)

# Remove the old three-layer UI entirely.
sgs=cent_groups
removed=[]
for gid in ["r45-cult-hq-centurion","r19-ts-centurion-disciplines","r19-ts-centurion-powers"]:
    matches=[x for x in list(sgs.findall(C("selectionEntryGroup"))) if x.get("id")==gid]
    for g in matches:
        sgs.remove(g); removed.append(gid)

# New single robust package.
pkg=ET.SubElement(sgs,C("selectionEntryGroup"),{
    "id":"r57-ts-centurion-psychic-package",
    "name":"Thousand Sons — Prosperine Cult & Psychic Powers",
    "hidden":"true"
})
cons(pkg,"r57-ts-centurion-cult-min","min",1)
cons(pkg,"r57-ts-centurion-cult-max","max",1)
# Positive show gate rather than hidden-if-missing. This is intentionally simple.
modifier(pkg,"r57-ts-centurion-show","set","hidden","false",[
    {"childId":"legion-xv","scope":"roster","type":"atLeast","value":1}
])

mapping=[
    ("Pavoni","Biomancy","biomancy"),
    ("Raptora","Telekinesis","telekinesis"),
    ("Corvidae","Divination","divination"),
    ("Athanaeans","Telepathy","telepathy"),
    ("Pyrae","Pyromancy","pyromancy"),
]

for idx,(cult,disc,dkey) in enumerate(mapping):
    ce=ET.SubElement(cont(pkg,"selectionEntries",before=("selectionEntryGroups","costs","modifiers")),C("selectionEntry"),{
        "id":f"r57-ts-centurion-cult-{dkey}",
        "name":f"{cult} — {disc}",
        "type":"upgrade",
        "hidden":"false"
    })
    cons(ce,f"r57-ts-centurion-cult-{dkey}-max","max",1)

    # Reuse the canonical Cult rule links. No new Cult rule definitions.
    target=ids[cult_targets[cult]]
    for j,il in enumerate(target.findall(f"./{C('infoLinks')}/{C('infoLink')}")):
        add_infolink(ce,f"r57-ts-centurion-{dkey}-cult-info-{j}",il.get("name"),il.get("targetId"),il.get("type","rule"))

    add_rule(ce,f"r57-ts-centurion-{dkey}-discipline","Psychic Discipline",f"This Thousand Sons Centurion selects psychic powers from {disc}. The Cult choice and psychic discipline are linked by the current Thousand Sons army rules.")

    pg=ET.SubElement(cont(ce,"selectionEntryGroups",before=("costs","modifiers")),C("selectionEntryGroup"),{
        "id":f"r57-ts-centurion-{dkey}-powers",
        "name":f"{disc} — Psychic Powers",
        "hidden":"false"
    })
    pmin=cons(pg,f"r57-ts-centurion-{dkey}-power-min","min",1)
    pmax=cons(pg,f"r57-ts-centurion-{dkey}-power-max","max",1)
    # Epistolary / ML2 knows two powers.
    modifier(pg,f"r57-ts-centurion-{dkey}-epistolary-min","set",pmin.get("id"),2,[
        {"childId":"hq-consul-librarian-epistolary","scope":"root-entry","type":"atLeast","value":1}
    ])
    modifier(pg,f"r57-ts-centurion-{dkey}-epistolary-max","set",pmax.get("id"),2,[
        {"childId":"hq-consul-librarian-epistolary","scope":"root-entry","type":"atLeast","value":1}
    ])

    for pidx,(pname,ptarget) in enumerate(disc_power_targets[dkey]):
        if ptarget not in ids: raise RuntimeError(f"Missing canonical power target {ptarget} for {pname}")
        l=ET.SubElement(cont(pg,"entryLinks",before=("infoLinks","profiles","rules","selectionEntries","selectionEntryGroups","costs","modifiers")),C("entryLink"),{
            "id":f"r57-ts-centurion-{dkey}-power-{pidx}",
            "name":pname,
            "targetId":ptarget,
            "type":"selectionEntry",
            "import":"true",
            "hidden":"false"
        })
        cons(l,f"r57-ts-centurion-{dkey}-power-{pidx}-max","max",1)

# Keep a concise source-backed reminder on the package without duplicating individual power rules.
add_rule(pkg,"r57-ts-centurion-psyker-rule","Sorcerers of Prospero — Centurion",
         "A Thousand Sons Centurion is a Psyker (Mastery Level 1) unless another upgrade gives it a higher Mastery Level. It selects powers from one Psychic Discipline only. A Librarian Epistolary uses its higher Mastery Level normally.")

# Revision/index bump. GST unchanged.
root.set("revision","57")
tree.write(CAT,encoding="utf-8",xml_declaration=True)
ET.register_namespace("",INS)
it=ET.parse(IDX); ir=it.getroot()
for x in ir.iter(I("dataIndexEntry")):
    if x.get("filePath")=="Legiones Astartes.cat": x.set("dataRevision","57")
it.write(IDX,encoding="utf-8",xml_declaration=True)

# Validation.
rr=ET.parse(CAT).getroot(); rids={x.get("id"):x for x in rr.iter() if x.get("id")}; checks=[]
def ck(n,o):
    checks.append((n,bool(o)))
    if not o: raise RuntimeError("R57 validation failed: "+n)

ck("CAT revision 57",rr.get("revision")=="57")
ck("GST dependency stays 14",rr.get("gameSystemRevision")=="14")
ck("index CAT57",'dataRevision="57"' in IDX.read_text(encoding="utf-8"))
ck("new Centurion psychic package exists","r57-ts-centurion-psychic-package" in rids)
pkg2=rids["r57-ts-centurion-psychic-package"]
ck("package defaults hidden",pkg2.get("hidden")=="true")
ck("package positively shows for XV","legion-xv" in ET.tostring(pkg2,encoding="unicode"))
ck("exactly five Cult choices",len(pkg2.findall(f"./{C('selectionEntries')}/{C('selectionEntry')}"))==5)
for cult,disc,dkey in mapping:
    ce=rids[f"r57-ts-centurion-cult-{dkey}"]
    pg=rids[f"r57-ts-centurion-{dkey}-powers"]
    ck(cult+" has canonical Cult refs",len(ce.findall(f"./{C('infoLinks')}/{C('infoLink')}"))>=2)
    ck(disc+" powers present",len(pg.findall(f"./{C('entryLinks')}/{C('entryLink')}"))==len(disc_power_targets[dkey]))
    ck(disc+" base 1 power",any(x.get("type")=="min" and x.get("value")=="1" for x in pg.findall(f"./{C('constraints')}/{C('constraint')}")) and any(x.get("type")=="max" and x.get("value")=="1" for x in pg.findall(f"./{C('constraints')}/{C('constraint')}")))
    ck(disc+" Epistolary to 2", "hq-consul-librarian-epistolary" in ET.tostring(pg,encoding="unicode"))

# old Centurion groups gone
for gid in ["r45-cult-hq-centurion","r19-ts-centurion-disciplines","r19-ts-centurion-powers"]:
    ck(gid+" removed",gid not in rids)

new=collections.Counter(x.get("id") for x in rr.iter() if x.get("id"))
worse={k:v for k,v in new.items() if v>max(1,baseline.get(k,0))}
ck("no new/worsened duplicate IDs",not worse)

OUT.write_text("\n".join([
    "Live R57 — Thousand Sons Centurion psychic UI rebuild",
    "Input CAT56/GST14 -> CAT57/GST14","",
    "WHY:",
    "- The Cult, discipline and power data existed, but the Centurion UI depended on three linked visibility layers and New Recruit was still rendering none of them.","",
    "FIX:",
    f"- Removed the old fragile groups: {', '.join(removed)}.",
    "- Added one positive-gated Thousand Sons Centurion package that appears when XV Legion is selected.",
    "- Exactly one Prosperine Cult is chosen.",
    "- The chosen Cult directly contains its corresponding psychic discipline's powers; no second linked Discipline selector is required.",
    "- Pavoni -> Biomancy; Raptora -> Telekinesis; Corvidae -> Divination; Athanaeans -> Telepathy; Pyrae -> Pyromancy.",
    "- Normal Centurion: exactly 1 power. Librarian Epistolary: exactly 2 powers.",
    "- Cult Arcana/Cult Mastery and psychic powers still reference the existing canonical shared rules/selections; no duplicate rule definitions were created.","",
    "VALIDATION:"
]+[f'- {"PASS" if ok else "FAIL"}: {n}' for n,ok in checks])+"\n",encoding="utf-8")
print(OUT.read_text())
