from pathlib import Path
import collections, re, xml.etree.ElementTree as ET

CAT=Path("Legiones Astartes.cat"); IDX=Path("index.xml")
OUT=Path("inspection-live-r63-ts-direct-cult-powers.txt")
NS="http://www.battlescribe.net/schema/catalogueSchema"; INS="http://www.battlescribe.net/schema/dataIndexSchema"
ET.register_namespace("",NS)
C=lambda t:f"{{{NS}}}{t}"; I=lambda t:f"{{{INS}}}{t}"

tree=ET.parse(CAT); root=tree.getroot()
if root.get("revision")!="62": raise RuntimeError(f"R63 expected CAT62, got {root.get('revision')}")
if root.get("gameSystemRevision")!="15": raise RuntimeError(f"R63 expected GST15 dependency, got {root.get('gameSystemRevision')}")
baseline=collections.Counter(x.get("id") for x in root.iter() if x.get("id"))

def cont(p,tag,before=("constraints","categoryLinks","entryLinks","infoLinks","profiles","rules","selectionEntries","selectionEntryGroups","costs","modifiers")):
    q=C(tag); x=p.find(q)
    if x is not None:return x
    x=ET.Element(q); kids=list(p); idx=len(kids)
    for j,k in enumerate(kids):
        if k.tag.split("}")[-1] in before:idx=j;break
    p.insert(idx,x); return x

def constraint(p,id_,typ,val,field="selections",scope="parent"):
    cs=cont(p,"constraints"); x=next((z for z in cs.findall(C("constraint")) if z.get("id")==id_),None)
    if x is None:x=ET.SubElement(cs,C("constraint"))
    x.attrib.update({"id":id_,"type":typ,"value":str(val),"field":field,"scope":scope,
                     "shared":"true","includeChildSelections":"true","includeChildForces":"false"})
    return x

def ensure_minmax(g,minv,maxv):
    cs=cont(g,"constraints")
    mins=[x for x in cs.findall(C("constraint")) if x.get("type")=="min"]
    maxs=[x for x in cs.findall(C("constraint")) if x.get("type")=="max"]
    if mins:
        mn=mins[0]; mn.set("value",str(minv))
        for x in mins[1:]:cs.remove(x)
    else: mn=constraint(g,(g.get("id") or "g")+"-r63-min","min",minv)
    if maxs:
        mx=maxs[0]; mx.set("value",str(maxv))
        for x in maxs[1:]:cs.remove(x)
    else: mx=constraint(g,(g.get("id") or "g")+"-r63-max","max",maxv)
    return mn,mx

def clear_mods(e):
    m=e.find(C("modifiers"))
    if m is not None:e.remove(m)

def cond(kind,val,child,scope="root-entry"):
    return {"type":kind,"value":str(val),"field":"selections","scope":scope,"childId":child,
            "shared":"true","includeChildSelections":"true","includeChildForces":"false"}

def modifier(p,id_,typ,field,value,conds=None,groups=None):
    ms=cont(p,"modifiers"); m=ET.SubElement(ms,C("modifier"),
        {"id":id_,"type":typ,"field":field,"value":str(value)})
    if groups:
        cgs=ET.SubElement(m,C("conditionGroups"))
        for gt,arr in groups:
            cg=ET.SubElement(cgs,C("conditionGroup"),{"type":gt})
            cs=ET.SubElement(cg,C("conditions"))
            for c in arr:ET.SubElement(cs,C("condition"),c)
    elif conds:
        cs=ET.SubElement(m,C("conditions"))
        for c in conds:ET.SubElement(cs,C("condition"),c)
    return m

CULT_TO_DISC={
    "Pavoni":"biomancy",
    "Raptora":"telekinesis",
    "Corvidae":"divination",
    "Athanaeans":"telepathy",
    "Pyrae":"pyromancy",
}

# Stable shared power target -> discipline lookup. This survives cloned unit IDs.
POWER_TARGET_DISC={}
for g in root.iter(C("selectionEntryGroup")):
    if not (g.get("name") or "").startswith("Psychic Brotherhood — Psychic Power"):
        continue
    for tag in ("selectionEntries","entryLinks"):
        cc=g.find(C(tag))
        if cc is None:continue
        for opt in list(cc):
            oid=(opt.get("id") or "").lower()
            m=re.search(r"power-(biomancy|divination|pyromancy|telekinesis|telepathy)-",oid)
            if m and opt.get("targetId"):
                POWER_TARGET_DISC[opt.get("targetId")]=m.group(1)

def direct_group(e,prefix):
    return next((g for g in e.findall(f"./{C('selectionEntryGroups')}/{C('selectionEntryGroup')}")
                 if (g.get("name") or "").startswith(prefix)),None)

roots=[]
for e in root.iter(C("selectionEntry")):
    cult=direct_group(e,"Prosperine Cult")
    power=direct_group(e,"Psychic Brotherhood — Psychic Power")
    if cult is not None and power is not None:
        roots.append(e)

if not roots:raise RuntimeError("No live Brotherhood roots found")

patched=[]
for e in roots:
    cult=direct_group(e,"Prosperine Cult")
    power=direct_group(e,"Psychic Brotherhood — Psychic Power")
    disc=direct_group(e,"Psychic Brotherhood — Psychic Discipline")

    cult_choices={x.get("name"):x for x in cult.findall(f"./{C('selectionEntries')}/{C('selectionEntry')}")
                  if x.get("name") in CULT_TO_DISC}
    if set(cult_choices)!=set(CULT_TO_DISC):
        raise RuntimeError(f"{e.get('id')} missing Cult choices: {sorted(cult_choices)}")

    # Recover the Brotherhood upgrade selector(s) on this exact unit.
    brother_ids=[]
    for x in e.iter():
        if x.tag not in (C("selectionEntry"),C("entryLink")) or x is e:continue
        n=(x.get("name") or "").lower(); xid=x.get("id") or ""
        if "brotherhood of psykers" in n or (("ts-brother" in xid or "ts-brotherhood" in xid) and "disc" not in xid and "power" not in xid):
            if xid and xid not in brother_ids:brother_ids.append(xid)
    if not brother_ids:raise RuntimeError(f"{e.get('id')} has no Brotherhood selector")

    # The Cult already determines the discipline. Hide the redundant discipline group
    # permanently and make it non-compulsory so it can never produce an error.
    if disc is not None:
        disc.set("hidden","true")
        ensure_minmax(disc,0,1)
        clear_mods(disc)
        for tag in ("selectionEntries","entryLinks"):
            cc=disc.find(C(tag))
            if cc is not None:
                for x in list(cc):
                    x.set("hidden","true");clear_mods(x)

    # One power is required only after Brotherhood is actually purchased.
    power.set("name","Psychic Brotherhood — Cult Power (choose 1)")
    power.set("hidden","false")
    mn,_=ensure_minmax(power,0,1)
    clear_mods(power)

    # Hide entire power group while Brotherhood is absent.
    modifier(power,power.get("id")+"-r63-hide-no-brother","set","hidden","true",
             groups=[("and",[cond("lessThan",1,bid) for bid in brother_ids])])
    # Any valid Brotherhood-price selector turns the group's minimum on.
    for bid in brother_ids:
        modifier(power,power.get("id")+"-r63-min-"+re.sub(r"[^a-z0-9]+","-",bid.lower())[-40:],
                 "set",mn.get("id"),1,[cond("atLeast",1,bid)])

    counts=collections.Counter()
    unknown=[]
    # Direct Cult -> power gating.
    for tag in ("selectionEntries","entryLinks"):
        cc=power.find(C(tag))
        if cc is None:continue
        for opt in list(cc):
            oid=opt.get("id") or ""
            m=re.search(r"power-(biomancy|divination|pyromancy|telekinesis|telepathy)-",oid.lower())
            d=m.group(1) if m else POWER_TARGET_DISC.get(opt.get("targetId"))
            if not d:
                unknown.append((oid,opt.get("name"),opt.get("targetId")));continue
            cult_name=next(k for k,v in CULT_TO_DISC.items() if v==d)
            opt.set("hidden","false")
            clear_mods(opt)
            modifier(opt,oid+"-r63-cult-lock","set","hidden","true",
                     [cond("lessThan",1,cult_choices[cult_name].get("id"))])
            counts[d]+=1

    if unknown:raise RuntimeError(f"{e.get('id')} unmapped Brotherhood powers: {unknown}")
    if set(counts)!=set(CULT_TO_DISC.values()):
        raise RuntimeError(f"{e.get('id')} incomplete pools: {dict(counts)}")

    patched.append((e.get("id"),e.get("name"),brother_ids,dict(counts)))

# Revision only; GST untouched.
root.set("revision","63")
tree.write(CAT,encoding="utf-8",xml_declaration=True)
ET.register_namespace("",INS)
it=ET.parse(IDX);ir=it.getroot()
for x in ir.iter(I("dataIndexEntry")):
    if x.get("filePath")=="Legiones Astartes.cat":x.set("dataRevision","63")
it.write(IDX,encoding="utf-8",xml_declaration=True)

# Validation.
rr=ET.parse(CAT).getroot();rids={x.get("id"):x for x in rr.iter() if x.get("id")};checks=[]
def ck(n,o):
    checks.append((n,bool(o)))
    if not o:raise RuntimeError("R63 validation failed: "+n)

ck("CAT63",rr.get("revision")=="63")
ck("GST dependency remains 15",rr.get("gameSystemRevision")=="15")
ck("Index63",'dataRevision="63"' in IDX.read_text(encoding="utf-8"))

for eid,name,bids,counts in patched:
    e=rids[eid]
    cult=direct_group(e,"Prosperine Cult")
    power=direct_group(e,"Psychic Brotherhood — Cult Power")
    disc=direct_group(e,"Psychic Brotherhood — Psychic Discipline")
    ck(name+" power group exists",power is not None)
    ck(name+" power group max1",any(x.get("type")=="max" and x.get("value")=="1" for x in power.findall(f"./{C('constraints')}/{C('constraint')}")))
    ptxt=ET.tostring(power,encoding="unicode")
    ck(name+" power group Brotherhood gated",all(b in ptxt for b in bids))
    if disc is not None:
        ck(name+" redundant discipline hidden",disc.get("hidden")=="true")
    for cult_name,d in CULT_TO_DISC.items():
        cid=next(x.get("id") for x in cult.findall(f"./{C('selectionEntries')}/{C('selectionEntry')}") if x.get("name")==cult_name)
        matching=[]
        for tag in ("selectionEntries","entryLinks"):
            cc=power.find(C(tag))
            if cc is None:continue
            for opt in list(cc):
                oid=opt.get("id") or ""
                m=re.search(r"power-(biomancy|divination|pyromancy|telekinesis|telepathy)-",oid.lower())
                od=m.group(1) if m else POWER_TARGET_DISC.get(opt.get("targetId"))
                if od==d:matching.append(opt)
        ck(name+f" {cult_name} has powers",len(matching)>0)
        ck(name+f" {cult_name} directly gates its powers",all(cid in ET.tostring(x,encoding="unicode") for x in matching))

new=collections.Counter(x.get("id") for x in rr.iter() if x.get("id"))
worse={k:v for k,v in new.items() if v>max(1,baseline.get(k,0))}
ck("No new/worsened duplicate IDs",not worse)

OUT.write_text("\n".join([
"Live R63 — Thousand Sons direct Cult power access",
"Input CAT62/GST15 -> CAT63/GST15","",
"BEHAVIOUR:",
f"- Patched {len(patched)} live Brotherhood-capable unit roots.",
"- Brotherhood of Psykers remains Mastery Level 1.",
"- Prosperine Cult remains a mandatory one-of-five selection.",
"- Removed the redundant player-facing Discipline choice from Brotherhood units.",
"- Selecting a Cult now directly exposes only the powers from its correlated discipline:",
"  Athanaeans -> Telepathy",
"  Corvidae -> Divination",
"  Pavoni -> Biomancy",
"  Pyrae -> Pyromancy",
"  Raptora -> Telekinesis",
"- After Brotherhood is purchased, exactly one Cult-correlated psychic power is required.",
"- The power group stays hidden when Brotherhood of Psykers is not purchased.",
"- Canonical shared ProHammer psychic power entries are reused; no duplicate powers were created.",
"- Shattered Legions R62 architecture is untouched.","",
"PATCHED ROOTS:"
]+[f"- {name} ({eid}) — selectors {bids}; pools {counts}" for eid,name,bids,counts in patched]+[
"","VALIDATION:"
]+[f'- {"PASS" if ok else "FAIL"}: {n}' for n,ok in checks])+"\n",encoding="utf-8")
print(OUT.read_text())
