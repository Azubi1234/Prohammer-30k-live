from pathlib import Path
import collections, re, xml.etree.ElementTree as ET

CAT=Path("Legiones Astartes.cat"); IDX=Path("index.xml")
OUT=Path("inspection-live-r61-ts-brotherhood-psychic.txt")
NS="http://www.battlescribe.net/schema/catalogueSchema"; INS="http://www.battlescribe.net/schema/dataIndexSchema"
ET.register_namespace("",NS)
C=lambda t:f"{{{NS}}}{t}"; I=lambda t:f"{{{INS}}}{t}"

tree=ET.parse(CAT); root=tree.getroot()
if root.get("revision")!="60": raise RuntimeError(f"R61 expected CAT60, got {root.get('revision')}")
if root.get("gameSystemRevision")!="14": raise RuntimeError(f"R61 expected GST14 dependency, got {root.get('gameSystemRevision')}")
baseline=collections.Counter(x.get("id") for x in root.iter() if x.get("id"))

def cont(p,tag,before=("constraints","categoryLinks","entryLinks","infoLinks","profiles","rules","selectionEntries","selectionEntryGroups","costs","modifiers")):
    q=C(tag); x=p.find(q)
    if x is not None:return x
    x=ET.Element(q); kids=list(p); idx=len(kids)
    for j,k in enumerate(kids):
        if k.tag.split("}")[-1] in before: idx=j; break
    p.insert(idx,x); return x

def constraint(p,id_,typ,val,field="selections",scope="parent"):
    cs=cont(p,"constraints"); q=C("constraint")
    x=next((z for z in cs.findall(q) if z.get("id")==id_),None)
    if x is None:x=ET.SubElement(cs,q)
    x.attrib.update({"id":id_,"type":typ,"value":str(val),"field":field,"scope":scope,
                     "shared":"true","includeChildSelections":"true","includeChildForces":"false"})
    return x

def ensure_single_minmax(g,minv,maxv):
    cs=cont(g,"constraints")
    mins=[x for x in cs.findall(C("constraint")) if x.get("type")=="min"]
    maxs=[x for x in cs.findall(C("constraint")) if x.get("type")=="max"]
    if mins:
        mn=mins[0]; mn.set("value",str(minv))
        for x in mins[1:]:cs.remove(x)
    else: mn=constraint(g,(g.get("id") or "group")+"-r61-min","min",minv)
    if maxs:
        mx=maxs[0]; mx.set("value",str(maxv))
        for x in maxs[1:]:cs.remove(x)
    else: mx=constraint(g,(g.get("id") or "group")+"-r61-max","max",maxv)
    return mn,mx

def clear_mods(e):
    m=e.find(C("modifiers"))
    if m is not None:e.remove(m)

def add_modifier(p,id_,typ,field,value,conds=None,groups=None):
    ms=cont(p,"modifiers"); m=ET.SubElement(ms,C("modifier"),
        {"id":id_,"type":typ,"field":field,"value":str(value)})
    if groups:
        cgs=ET.SubElement(m,C("conditionGroups"))
        for gtype,arr in groups:
            cg=ET.SubElement(cgs,C("conditionGroup"),{"type":gtype})
            cs=ET.SubElement(cg,C("conditions"))
            for c in arr: ET.SubElement(cs,C("condition"),c)
    elif conds:
        cs=ET.SubElement(m,C("conditions"))
        for c in conds: ET.SubElement(cs,C("condition"),c)
    return m

def cond(kind,val,child,scope="root-entry"):
    return {"type":kind,"value":str(val),"field":"selections","scope":scope,"childId":child,
            "shared":"true","includeChildSelections":"true","includeChildForces":"false"}

def hide_if_not_xv(e,suffix):
    add_modifier(e,(e.get("id") or suffix)+suffix+"-not-xv","set","hidden","true",
                 [cond("lessThan",1,"legion-xv","roster")])

def find_direct_group(entry,name):
    return next((g for g in entry.findall(f"./{C('selectionEntryGroups')}/{C('selectionEntryGroup')}")
                 if (g.get("name") or "")==name),None)

def find_desc_groups(entry,prefix):
    return [g for g in entry.iter(C("selectionEntryGroup")) if (g.get("name") or "").startswith(prefix)]

CULT_TO_DISC={
    "Pavoni":"Biomancy",
    "Raptora":"Telekinesis",
    "Corvidae":"Divination",
    "Athanaeans":"Telepathy",
    "Pyrae":"Pyromancy",
}
disc_lower={v.lower():k for k,v in CULT_TO_DISC.items()}

# Build a canonical power-target -> discipline map from any live Brotherhood
# power option whose original ID still carries its discipline. This lets cloned
# Veteran/Terminator entries use the same shared power targets even when their
# clone prefixes obscure the original option ID.
POWER_TARGET_DISC={}
for g in root.iter(C("selectionEntryGroup")):
    if not (g.get("name") or "").startswith("Psychic Brotherhood — Psychic Power"):
        continue
    for tag in ("selectionEntries","entryLinks"):
        cc=g.find(C(tag))
        if cc is None: continue
        for opt in list(cc):
            oid=(opt.get("id") or "").lower()
            m=re.search(r"power-(biomancy|divination|pyromancy|telekinesis|telepathy)-",oid)
            tid=opt.get("targetId")
            if m and tid:
                POWER_TARGET_DISC[tid]=m.group(1)

# Identify live unit roots which actually contain the Brotherhood psychic UI.
unit_roots=[]
for e in root.iter(C("selectionEntry")):
    dg=find_desc_groups(e,"Psychic Brotherhood — Psychic Discipline")
    pg=find_desc_groups(e,"Psychic Brotherhood — Psychic Power")
    if not dg or not pg: continue
    # Keep only the outermost selectionEntry that directly owns these groups.
    direct_d=[g for g in e.findall(f"./{C('selectionEntryGroups')}/{C('selectionEntryGroup')}")
              if (g.get("name") or "").startswith("Psychic Brotherhood — Psychic Discipline")]
    direct_p=[g for g in e.findall(f"./{C('selectionEntryGroups')}/{C('selectionEntryGroup')}")
              if (g.get("name") or "").startswith("Psychic Brotherhood — Psychic Power")]
    if direct_d and direct_p:
        unit_roots.append(e)

if not unit_roots: raise RuntimeError("No Brotherhood psychic-unit roots found")

patched=[]
for e in unit_roots:
    cult=find_direct_group(e,"Prosperine Cult")
    if cult is None:
        raise RuntimeError(f"{e.get('id')} has Brotherhood psychic UI but no direct Prosperine Cult group")
    cult_choices={x.get("name"):x for x in cult.findall(f"./{C('selectionEntries')}/{C('selectionEntry')}")
                  if x.get("name") in CULT_TO_DISC}
    if set(cult_choices)!=set(CULT_TO_DISC):
        raise RuntimeError(f"{e.get('id')} Cult choices incomplete: {sorted(cult_choices)}")

    dg=next(g for g in e.findall(f"./{C('selectionEntryGroups')}/{C('selectionEntryGroup')}")
            if (g.get("name") or "").startswith("Psychic Brotherhood — Psychic Discipline"))
    pg=next(g for g in e.findall(f"./{C('selectionEntryGroups')}/{C('selectionEntryGroup')}")
            if (g.get("name") or "").startswith("Psychic Brotherhood — Psychic Power"))

    # Find actual Brotherhood upgrade selectors on this unit.
    brother_ids=[]
    for x in e.iter():
        if x.tag not in (C("selectionEntry"),C("entryLink")): continue
        if x is e: continue
        n=(x.get("name") or "").lower()
        if "brotherhood of psykers" in n or ("psychic brotherhood" in n and "power" not in n and "discipline" not in n):
            if x.get("id") and x.get("id") not in brother_ids: brother_ids.append(x.get("id"))
    # Legacy live options can use compact names; recover known IDs if they exist in this unit.
    for x in e.iter():
        xid=x.get("id") or ""
        if ("ts-brother" in xid or "ts-brotherhood" in xid) and x.tag in (C("selectionEntry"),C("entryLink")):
            if "disc" not in xid and "power" not in xid and xid not in brother_ids:
                brother_ids.append(xid)
    if not brother_ids:
        raise RuntimeError(f"{e.get('id')} has no Brotherhood upgrade selector")

    for g,kind in [(dg,"disc"),(pg,"power")]:
        g.set("hidden","false")
        mn,_=ensure_single_minmax(g,0,1)
        clear_mods(g)
        hide_if_not_xv(g,"-r61")
        # Hide unless at least one Brotherhood upgrade is actually selected.
        add_modifier(g,g.get("id")+"-r61-hide-no-brother","set","hidden","true",
                     groups=[("and",[cond("lessThan",1,bid) for bid in brother_ids])])
        # Brotherhood ML1 must make exactly one selection in each group.
        for bid in brother_ids:
            add_modifier(g,g.get("id")+"-r61-min-"+re.sub(r"[^a-z0-9]+","-",bid.lower())[-40:],
                         "set",mn.get("id"),1,[cond("atLeast",1,bid)])

    # Discipline options: only the discipline matching the chosen Cult can appear.
    disc_options=[]
    for container_tag in ("selectionEntries","entryLinks"):
        cc=dg.find(C(container_tag))
        if cc is None: continue
        for opt in list(cc):
            name=(opt.get("name") or "").strip()
            if name.lower() not in disc_lower: continue
            cult_name=disc_lower[name.lower()]
            clear_mods(opt); opt.set("hidden","false")
            add_modifier(opt,opt.get("id")+"-r61-cult-lock","set","hidden","true",
                         [cond("lessThan",1,cult_choices[cult_name].get("id"))])
            disc_options.append((name,opt.get("id")))
    if len(disc_options)!=5:
        raise RuntimeError(f"{e.get('id')} expected 5 discipline options, got {disc_options}")
    disc_ids={name.lower():oid for name,oid in disc_options}

    # Psychic powers: identify their discipline from the stable live ID and lock
    # them to the one visible/selected discipline.
    power_counts=collections.Counter()
    for container_tag in ("selectionEntries","entryLinks"):
        cc=pg.find(C(container_tag))
        if cc is None: continue
        for opt in list(cc):
            oid=opt.get("id") or ""
            m=re.search(r"power-(biomancy|divination|pyromancy|telekinesis|telepathy)-",oid.lower())
            disc=m.group(1) if m else POWER_TARGET_DISC.get(opt.get("targetId"))
            if not disc:
                continue
            clear_mods(opt); opt.set("hidden","false")
            add_modifier(opt,oid+"-r61-discipline-lock","set","hidden","true",
                         [cond("lessThan",1,disc_ids[disc])])
            power_counts[disc]+=1
    if set(power_counts)!=set(disc_lower):
        raise RuntimeError(f"{e.get('id')} missing power discipline(s): {dict(power_counts)}")

    patched.append((e.get("id"),e.get("name"),brother_ids,dict(power_counts)))

# Revision.
root.set("revision","61")
tree.write(CAT,encoding="utf-8",xml_declaration=True)
ET.register_namespace("",INS)
it=ET.parse(IDX); ir=it.getroot()
for x in ir.iter(I("dataIndexEntry")):
    if x.get("filePath")=="Legiones Astartes.cat":x.set("dataRevision","61")
it.write(IDX,encoding="utf-8",xml_declaration=True)

# Validation.
rr=ET.parse(CAT).getroot(); rids={x.get("id"):x for x in rr.iter() if x.get("id")}; checks=[]
def ck(n,o):
    checks.append((n,bool(o)))
    if not o: raise RuntimeError("R61 validation failed: "+n)
ck("CAT61",rr.get("revision")=="61")
ck("GST dependency remains 14",rr.get("gameSystemRevision")=="14")
ck("Index61",'dataRevision="61"' in IDX.read_text(encoding="utf-8"))

for eid,name,bids,pc in patched:
    e=rids[eid]
    cult=find_direct_group(e,"Prosperine Cult")
    dg=next(g for g in e.findall(f"./{C('selectionEntryGroups')}/{C('selectionEntryGroup')}")
            if (g.get("name") or "").startswith("Psychic Brotherhood — Psychic Discipline"))
    pg=next(g for g in e.findall(f"./{C('selectionEntryGroups')}/{C('selectionEntryGroup')}")
            if (g.get("name") or "").startswith("Psychic Brotherhood — Psychic Power"))
    ck(name+" discipline group visible-default",dg.get("hidden")!="true")
    ck(name+" power group visible-default",pg.get("hidden")!="true")
    dtxt=ET.tostring(dg,encoding="unicode"); ptxt=ET.tostring(pg,encoding="unicode")
    ck(name+" groups require XV","legion-xv" in dtxt and "legion-xv" in ptxt)
    ck(name+" groups gated by Brotherhood",all(b in dtxt and b in ptxt for b in bids))
    # Five discipline options, one for each Cult.
    dnames=[]
    for tag in ("selectionEntries","entryLinks"):
        cc=dg.find(C(tag))
        if cc is not None:dnames += [(x.get("name") or "") for x in list(cc) if (x.get("name") or "").lower() in disc_lower]
    ck(name+" has five Cult-correlated disciplines",set(dnames)==set(CULT_TO_DISC.values()))
    ck(name+" has all five power pools",set(pc)==set(disc_lower))

new=collections.Counter(x.get("id") for x in rr.iter() if x.get("id"))
worse={k:v for k,v in new.items() if v>max(1,baseline.get(k,0))}
ck("No new/worsened duplicate IDs",not worse)

OUT.write_text("\n".join([
"Live R61 — Thousand Sons Psychic Brotherhood access",
"Input CAT60/GST14 -> CAT61/GST14","",
"BEHAVIOUR:",
f"- Rebuilt the psychic interface on {len(patched)} live Brotherhood-capable unit root(s).",
"- Brotherhood of Psykers remains Mastery Level 1 and therefore selects exactly one psychic power.",
"- The unit still selects exactly one Prosperine Cult.",
"- Only the discipline correlated to that Cult is selectable:",
"  Pavoni -> Biomancy",
"  Raptora -> Telekinesis",
"  Corvidae -> Divination",
"  Athanaeans -> Telepathy",
"  Pyrae -> Pyromancy",
"- After selecting that Cult-locked discipline, exactly one power from that discipline is required.",
"- Discipline/power controls are hidden when the Brotherhood upgrade is not taken and hidden outside a Thousand Sons roster.",
"- Existing canonical ProHammer discipline/power entries are reused; no duplicate psychic-power definitions were created.","",
"PATCHED ROOTS:"
]+[f"- {name} ({eid}) — Brotherhood selectors {bids}; power pools {pc}" for eid,name,bids,pc in patched]+["","VALIDATION:"]+
[f'- {"PASS" if ok else "FAIL"}: {n}' for n,ok in checks])+"\n",encoding="utf-8")
print(OUT.read_text())
