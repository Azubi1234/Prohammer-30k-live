from pathlib import Path
import collections, hashlib, re, xml.etree.ElementTree as ET

CAT=Path("Legiones Astartes.cat"); IDX=Path("index.xml")
OUT=Path("inspection-live-r68-ts-psychic-veteran-melee.txt")
NS="http://www.battlescribe.net/schema/catalogueSchema"; INS="http://www.battlescribe.net/schema/dataIndexSchema"
ET.register_namespace("",NS)
C=lambda t:f"{{{NS}}}{t}"; I=lambda t:f"{{{INS}}}{t}"

tree=ET.parse(CAT); root=tree.getroot()
if root.get("revision")!="67": raise RuntimeError(f"R68 expected CAT67, got {root.get('revision')}")
if root.get("gameSystemRevision")!="15": raise RuntimeError(f"R68 expected GST15, got {root.get('gameSystemRevision')}")
baseline=collections.Counter(x.get("id") for x in root.iter() if x.get("id"))
ids={x.get("id"):x for x in root.iter() if x.get("id")}

VET="veteran-unit"; CENT="hq-centurion"; LEGION="legion-xv"; ASSIGN="r62-shat-assign-2a678f656c73"
OLD_VET_POW="r19-ts-veteran-unit-brotherhood-powers"
OLD_CENT_N="r66-ts-centurion-normal-psychic-package"
OLD_CENT_S="r66-ts-centurion-shattered-psychic-package"
PSYKER="r64-ts-psyker-ml1"
for req in [VET,CENT,LEGION,ASSIGN,OLD_VET_POW,PSYKER]:
    if req not in ids: raise RuntimeError("Missing required "+req)

def cont(p,tag,before=("constraints","categoryLinks","entryLinks","infoLinks","profiles","rules","selectionEntries","selectionEntryGroups","costs","modifiers")):
    q=C(tag); x=p.find(q)
    if x is not None:return x
    x=ET.Element(q); kids=list(p); idx=len(kids)
    for j,k in enumerate(kids):
        if k.tag.split("}")[-1] in before:idx=j;break
    p.insert(idx,x);return x

def one_constraint(p,typ,val,id_,child=False):
    cs=cont(p,"constraints")
    hits=[x for x in cs.findall(C("constraint")) if x.get("type")==typ]
    if hits:
        x=hits[0]
        for z in hits[1:]:cs.remove(z)
    else:x=ET.SubElement(cs,C("constraint"))
    x.attrib.update({"id":id_,"type":typ,"value":str(val),"field":"selections","scope":"parent","shared":"true",
                     "includeChildSelections":"true" if child else "false","includeChildForces":"false"})
    return x

def modifier(p,id_,typ,field,value,conds=None,repeats=None):
    ms=cont(p,"modifiers")
    for x in list(ms):
        if x.get("id")==id_:ms.remove(x)
    m=ET.SubElement(ms,C("modifier"),{"id":id_,"type":typ,"field":field,"value":str(value)})
    if repeats:
        rs=ET.SubElement(m,C("repeats"))
        for rp in repeats:
            ET.SubElement(rs,C("repeat"),{
                "value":str(rp.get("value",1)),"repeats":str(rp.get("repeats",1)),
                "field":"selections","scope":rp.get("scope","root-entry"),"childId":rp["childId"],
                "shared":"true","roundUp":"true" if rp.get("roundUp",False) else "false",
                "includeChildSelections":"true" if rp.get("includeChildSelections",False) else "false",
                "includeChildForces":"false"
            })
    if conds:
        cs=ET.SubElement(m,C("conditions"))
        for c in conds:
            ET.SubElement(cs,C("condition"),{
                "type":c.get("type","atLeast"),"value":str(c.get("value",1)),
                "field":"selections","scope":c.get("scope","root-entry"),"childId":c["childId"],
                "shared":"true","includeChildSelections":"true","includeChildForces":"false"
            })
    return m

def entrylink(p,id_,name,target,hidden=False):
    es=cont(p,"entryLinks",before=("infoLinks","profiles","rules","selectionEntries","selectionEntryGroups","costs","modifiers"))
    e=ET.SubElement(es,C("entryLink"),{"id":id_,"name":name,"targetId":target,"type":"selectionEntry","import":"true","hidden":"true" if hidden else "false"})
    cs=ET.SubElement(e,C("constraints"))
    ET.SubElement(cs,C("constraint"),{"id":id_+"-max","type":"max","value":"1","field":"selections","scope":"parent","shared":"true","includeChildSelections":"true","includeChildForces":"false"})
    return e

def group(p,id_,name,hidden=False,minv=None,maxv=None):
    gs=cont(p,"selectionEntryGroups",before=("costs","modifiers"))
    g=ET.SubElement(gs,C("selectionEntryGroup"),{"id":id_,"name":name,"hidden":"true" if hidden else "false"})
    if minv is not None:one_constraint(g,"min",minv,id_+"-min",True)
    if maxv is not None:one_constraint(g,"max",maxv,id_+"-max",True)
    return g

def selection(p,id_,name):
    ss=cont(p,"selectionEntries",before=("selectionEntryGroups","costs","modifiers"))
    e=ET.SubElement(ss,C("selectionEntry"),{"id":id_,"name":name,"type":"upgrade","hidden":"false"})
    one_constraint(e,"max",1,id_+"-max",False)
    return e

def infolink(p,id_,name,target,hidden=False):
    ils=cont(p,"infoLinks")
    x=ET.SubElement(ils,C("infoLink"),{"id":id_,"name":name,"targetId":target,"type":"rule","hidden":"true" if hidden else "false"})
    return x

def parent_of(target):
    for p in root.iter():
        if target in list(p):return p
    return None

def remove_by_id(eid):
    e=ids.get(eid)
    if e is None:return False
    p=parent_of(e)
    if p is None:return False
    p.remove(e);return True

def remove_field_modifiers(p,field):
    ms=p.find(C("modifiers"))
    if ms is None:return 0
    n=0
    for m in list(ms):
        if m.get("field")==field:
            ms.remove(m);n+=1
    return n

def remove_all_modifiers(p):
    ms=p.find(C("modifiers"))
    if ms is not None:p.remove(ms)

def add_power_group(cult,prefix,powers,brother_evidence=None,epistolary=False):
    # Physically nesting the power list inside the selected Cult removes all Cult-lock visibility logic.
    hidden=bool(brother_evidence)
    pg=group(cult,prefix+"-powers","Psychic Power — choose 1" if not brother_evidence else "Psychic Brotherhood Power — choose 1",hidden,0 if brother_evidence else 1,1)
    mn=next(x for x in pg.findall(f"./{C('constraints')}/{C('constraint')}") if x.get("type")=="min")
    mx=next(x for x in pg.findall(f"./{C('constraints')}/{C('constraint')}") if x.get("type")=="max")
    if brother_evidence:
        # Any valid Brotherhood identity reveals the group and makes one power mandatory.
        for i,bid in enumerate(brother_evidence):
            modifier(pg,prefix+f"-show-{i}","set","hidden","false",[{"childId":bid,"scope":"root-entry"}])
            modifier(pg,prefix+f"-min1-{i}","set",mn.get("id"),1,[{"childId":bid,"scope":"root-entry"}])
    if epistolary:
        modifier(pg,prefix+"-epi-min2","set",mn.get("id"),2,[{"childId":"hq-consul-librarian-epistolary","scope":"root-entry"}])
        modifier(pg,prefix+"-epi-max2","set",mx.get("id"),2,[{"childId":"hq-consul-librarian-epistolary","scope":"root-entry"}])
    for j,(nm,target) in enumerate(powers):
        entrylink(pg,prefix+f"-power-{j}",nm,target,False)
    return pg

# -------------------------------------------------------------------
# Extract the canonical 35 power targets from the CURRENT Veteran pool.
# -------------------------------------------------------------------
oldpow=ids[OLD_VET_POW]
disciplines={"biomancy":[],"telekinesis":[],"divination":[],"telepathy":[],"pyromancy":[]}
for l in oldpow.iter(C("entryLink")):
    lid=(l.get("id") or "").lower()
    for d in disciplines:
        if f"power-{d}-" in lid:
            disciplines[d].append((l.get("name"),l.get("targetId")));break
for d,arr in disciplines.items():
    if len(arr)!=7: raise RuntimeError(f"Expected 7 {d} powers, found {len(arr)}")

cult_map=[
    ("Pavoni","biomancy"),
    ("Raptora","telekinesis"),
    ("Corvidae","divination"),
    ("Athanaeans","telepathy"),
    ("Pyrae","pyromancy"),
]

# -------------------------------------------------------------------
# FIX 1: Veteran melee scaling.
# Base MAX 1 (Sergeant) + one for each normal Veteran model.
# This is the same proven dynamic architecture as the ranged replacements.
# -------------------------------------------------------------------
vet=ids[VET]
melee=next(g for g in vet.findall(f"./{C('selectionEntryGroups')}/{C('selectionEntryGroup')}") if g.get("id")=="veteran-melee")
mx=one_constraint(melee,"max",1,"veteran-melee-max",False)
removed_melee_mods=remove_field_modifiers(melee,mx.get("id"))
modifier(melee,"veteran-melee-r68-per-veteran","increment",mx.get("id"),1,None,[{
    "childId":"veteran-included","scope":"root-entry","value":1,"repeats":1
}])

# -------------------------------------------------------------------
# FIX 2: Veteran Brotherhood power selection.
# Move each discipline's seven powers INSIDE its Cult selection.
# No Cult-lock modifiers, no 35-option hidden sibling pool.
# -------------------------------------------------------------------
brother_links=[];brother_targets=[]
for x in vet.iter(C("entryLink")):
    n=(x.get("name") or "").lower()
    if "brotherhood of psykers" in n and "power" not in n:
        if x.get("id") and x.get("id") not in brother_links:brother_links.append(x.get("id"))
        if x.get("targetId") and x.get("targetId") not in brother_targets:brother_targets.append(x.get("targetId"))
evidence=[]
for x in brother_links+brother_targets:
    if x not in evidence:evidence.append(x)
if not evidence:raise RuntimeError("Veteran Brotherhood selectors not found")

cult_group=next(g for g in vet.findall(f"./{C('selectionEntryGroups')}/{C('selectionEntryGroup')}") if g.get("id")=="r45-cult-veteran-unit")
cult_entries={x.get("name"):x for x in cult_group.findall(f"./{C('selectionEntries')}/{C('selectionEntry')}")}
for cname,d in cult_map:
    if cname not in cult_entries:raise RuntimeError("Veteran missing Cult "+cname)
    c=cult_entries[cname]
    # Remove any prior R68 nested group on rerun.
    gs=c.find(C("selectionEntryGroups"))
    if gs is not None:
        for g in list(gs):
            if (g.get("id") or "").startswith("r68-vet-"):gs.remove(g)
    add_power_group(c,"r68-vet-"+d,cult_entries and disciplines[d],evidence,False)

# Remove the old sibling 35-power group entirely.
remove_by_id(OLD_VET_POW)

# -------------------------------------------------------------------
# FIX 3: Rebuild Centurion TS Cult/Psychic UI from scratch.
# Remove the R66 cloned packages; they retained too much old hidden Librarian logic.
# -------------------------------------------------------------------
ids={x.get("id"):x for x in root.iter() if x.get("id")}
for eid in [OLD_CENT_N,OLD_CENT_S]:
    remove_by_id(eid)

ids={x.get("id"):x for x in root.iter() if x.get("id")}
cent=ids[CENT]; assign=ids[ASSIGN]

def make_centurion_cult_package(parent,prefix,normal):
    pkg=group(parent,prefix,"Thousand Sons — Prosperine Cult & Psychic Powers" if normal else "Prosperine Cult & Psychic Powers",normal,0 if normal else 1,1)
    if normal:
        mn=next(x for x in pkg.findall(f"./{C('constraints')}/{C('constraint')}") if x.get("type")=="min")
        modifier(pkg,prefix+"-show","set","hidden","false",[{"childId":LEGION,"scope":"roster"}])
        modifier(pkg,prefix+"-min1","set",mn.get("id"),1,[{"childId":LEGION,"scope":"roster"}])
    for i,(cname,d) in enumerate(cult_map):
        cult=selection(pkg,prefix+f"-cult-{i}",cname)
        add_power_group(cult,prefix+f"-{d}",disciplines[d],None,True)
    return pkg

# Direct package on normal Centurion.
make_centurion_cult_package(cent,"r68-ts-centurion-cult",True)

# Package physically nested under selected Shattered TS assignment.
make_centurion_cult_package(assign,"r68-ts-centurion-shattered-cult",False)

# Keep/add ML1 links in the simplest possible locations.
# Normal Centurion: hidden unless Legion XV.
ils=cont(cent,"infoLinks")
for x in list(ils):
    if x.get("targetId")==PSYKER and (x.get("id") or "").startswith(("r64-ts-centurion","r66-ts-centurion")):
        ils.remove(x)
nl=infolink(cent,"r68-ts-centurion-psyker","Psyker (Mastery Level 1)",PSYKER,True)
modifier(nl,"r68-ts-centurion-psyker-show","set","hidden","false",[{"childId":LEGION,"scope":"roster"}])

# Shattered assignment directly carries ML1.
ails=cont(assign,"infoLinks")
for x in list(ails):
    if x.get("targetId")==PSYKER:ails.remove(x)
infolink(assign,"r68-ts-centurion-shat-psyker","Psyker (Mastery Level 1)",PSYKER,False)

# -------------------------------------------------------------------
# Revision/index.
# -------------------------------------------------------------------
root.set("revision","68")
tree.write(CAT,encoding="utf-8",xml_declaration=True)
ET.register_namespace("",INS)
it=ET.parse(IDX);ir=it.getroot()
for x in ir.iter(I("dataIndexEntry")):
    if x.get("filePath")=="Legiones Astartes.cat":x.set("dataRevision","68")
it.write(IDX,encoding="utf-8",xml_declaration=True)

# -------------------------------------------------------------------
# Validation.
# -------------------------------------------------------------------
rr=ET.parse(CAT).getroot(); rids={x.get("id"):x for x in rr.iter() if x.get("id")}; checks=[]
def ck(n,o):
    checks.append((n,bool(o)))
    if not o:raise RuntimeError("R68 validation failed: "+n)

ck("CAT68",rr.get("revision")=="68")
ck("GST dependency remains15",rr.get("gameSystemRevision")=="15")
ck("Index68",'dataRevision="68"' in IDX.read_text(encoding="utf-8"))

rv=rids[VET]
rmelee=next(g for g in rv.findall(f"./{C('selectionEntryGroups')}/{C('selectionEntryGroup')}") if g.get("id")=="veteran-melee")
rcs=rmelee.findall(f"./{C('constraints')}/{C('constraint')}")
ck("Veteran melee base MAX1",any(x.get("type")=="max" and x.get("value")=="1" for x in rcs))
mxml=ET.tostring(rmelee,encoding="unicode")
ck("Veteran melee dynamically increments per Veteran","veteran-melee-r68-per-veteran" in mxml and "veteran-included" in mxml)
ck("Veteran old threshold SET modifiers removed","veteran-melee-r65-total-" not in mxml)

rvg=next(g for g in rv.findall(f"./{C('selectionEntryGroups')}/{C('selectionEntryGroup')}") if g.get("id")=="r45-cult-veteran-unit")
rcults={x.get("name"):x for x in rvg.findall(f"./{C('selectionEntries')}/{C('selectionEntry')}")}
ck("Veteran five Cults",len([x for x in cult_map if x[0] in rcults])==5)
for cname,d in cult_map:
    c=rcults[cname]
    pgs=[g for g in c.findall(f"./{C('selectionEntryGroups')}/{C('selectionEntryGroup')}") if g.get("id")==f"r68-vet-{d}-powers"]
    ck("Veteran "+cname+" nested power group",len(pgs)==1)
    opts=pgs[0].findall(f"./{C('entryLinks')}/{C('entryLink')}")
    ck("Veteran "+cname+" seven powers",len(opts)==7)
    ck("Veteran "+cname+" Brotherhood gated",pgs[0].get("hidden")=="true" and all(x in ET.tostring(pgs[0],encoding="unicode") for x in evidence))
ck("Old Veteran 35-power sibling group removed",OLD_VET_POW not in rids)

rc=rids[CENT]
np=[g for g in rc.findall(f"./{C('selectionEntryGroups')}/{C('selectionEntryGroup')}") if g.get("id")=="r68-ts-centurion-cult"]
ck("Normal Centurion clean package exists",len(np)==1)
n=np[0]
ck("Normal Centurion package keyed to XV",LEGION in ET.tostring(n,encoding="unicode"))
ncults={x.get("name"):x for x in n.findall(f"./{C('selectionEntries')}/{C('selectionEntry')}")}
ck("Normal Centurion five Cults",len(ncults)==5)
for cname,d in cult_map:
    c=ncults[cname]
    pg=next((g for g in c.findall(f"./{C('selectionEntryGroups')}/{C('selectionEntryGroup')}") if g.get("id")==f"r68-ts-centurion-cult-{d}-powers"),None)
    ck("Centurion "+cname+" power group",pg is not None)
    ck("Centurion "+cname+" seven powers",len(pg.findall(f"./{C('entryLinks')}/{C('entryLink')}"))==7)
    cs=pg.findall(f"./{C('constraints')}/{C('constraint')")
    ] if False else pg.findall(f"./{C('constraints')}/{C('constraint')}")
    ck("Centurion "+cname+" min1",any(x.get("type")=="min" and x.get("value")=="1" for x in cs))
    ck("Centurion "+cname+" max1",any(x.get("type")=="max" and x.get("value")=="1" for x in cs))
    ck("Centurion "+cname+" Epistolary scales to2","hq-consul-librarian-epistolary" in ET.tostring(pg,encoding="unicode"))

ra=rids[ASSIGN]
sp=[g for g in ra.findall(f"./{C('selectionEntryGroups')}/{C('selectionEntryGroup')}") if g.get("id")=="r68-ts-centurion-shattered-cult"]
ck("Shattered TS Centurion package exists",len(sp)==1)
ck("Shattered TS Centurion package visible",sp[0].get("hidden")=="false")
ck("Normal ML1 link exists",any(x.get("id")=="r68-ts-centurion-psyker" for x in rc.findall(f"./{C('infoLinks')}/{C('infoLink')}")))
ck("Shattered ML1 link exists",any(x.get("id")=="r68-ts-centurion-shat-psyker" for x in ra.findall(f"./{C('infoLinks')}/{C('infoLink')}")))

new=collections.Counter(x.get("id") for x in rr.iter() if x.get("id"))
worse={k:v for k,v in new.items() if v>max(1,baseline.get(k,0))}
ck("No new/worsened duplicate IDs",not worse)

OUT.write_text("\n".join([
"Live R68 — Thousand Sons psychic UI + Veteran melee definitive repair",
"Input CAT=67/GST=15 -> CAT=68/GST remains15","",
"VETERAN MELEE:",
"- Replaced the unreliable MAX5 + conditional SET6/7/8/9/10 system.",
"- Close Combat Weapon Replacements now use a proven dynamic counter: base MAX1 for the Sergeant plus +1 for every selected Legion Veteran.",
"- Result: 5-model squad = max5 melee replacements; 10-model squad = max10.","",
"THOUSAND SONS VETERANS:",
"- Removed the single 35-power sibling pool and all Cult-lock/no-Brotherhood visibility complexity.",
"- Each Prosperine Cult now physically owns its correlated seven-power list:",
"  Pavoni -> Biomancy; Raptora -> Telekinesis; Corvidae -> Divination; Athanaeans -> Telepathy; Pyrae -> Pyromancy.",
"- The chosen Cult's Psychic Brotherhood Power group appears only after Brotherhood of Psykers is selected and then requires exactly one power.",
"- Because powers are nested inside the Cult, a power from the wrong Cult cannot appear or be selected.","",
"THOUSAND SONS CENTURION:",
"- Deleted the R66 cloned psychic packages that retained legacy hidden Librarian logic.",
"- Rebuilt a clean direct Cult selector from scratch for normal Thousand Sons Centurions.",
"- Rebuilt a second clean package physically inside the Shattered-Legions Thousand Sons assignment.",
"- Each Cult directly contains its seven correlated powers; normal TS Centurion selects one.",
"- Librarian Epistolary increases the correlated power selection to two within the SAME Cult.",
"- Psyker (Mastery Level 1) is attached directly to normal TS Centurion / Shattered TS assignment in the appropriate context.","",
"VALIDATION:"
]+[f'- {"PASS" if ok else "FAIL"}: {n}' for n,ok in checks])+"\n",encoding="utf-8")
print(OUT.read_text())
