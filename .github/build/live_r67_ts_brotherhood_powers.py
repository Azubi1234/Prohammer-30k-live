from pathlib import Path
import collections, re, xml.etree.ElementTree as ET

CAT=Path("Legiones Astartes.cat"); IDX=Path("index.xml")
OUT=Path("inspection-live-r67-ts-brotherhood-power-selection.txt")
NS="http://www.battlescribe.net/schema/catalogueSchema"; INS="http://www.battlescribe.net/schema/dataIndexSchema"
ET.register_namespace("",NS)
C=lambda t:f"{{{NS}}}{t}"; I=lambda t:f"{{{INS}}}{t}"

tree=ET.parse(CAT); root=tree.getroot()
if root.get("revision")!="66": raise RuntimeError(f"R67 expected CAT66, got {root.get('revision')}")
if root.get("gameSystemRevision")!="15": raise RuntimeError(f"R67 expected GST15, got {root.get('gameSystemRevision')}")
baseline=collections.Counter(x.get("id") for x in root.iter() if x.get("id"))

def cont(p,tag,before=("constraints","categoryLinks","entryLinks","infoLinks","profiles","rules","selectionEntries","selectionEntryGroups","costs","modifiers")):
    q=C(tag); x=p.find(q)
    if x is not None:return x
    x=ET.Element(q); kids=list(p); idx=len(kids)
    for j,k in enumerate(kids):
        if k.tag.split("}")[-1] in before: idx=j; break
    p.insert(idx,x); return x

def ensure_one_constraint(p,typ,val,id_):
    cs=cont(p,"constraints")
    hits=[x for x in cs.findall(C("constraint")) if x.get("type")==typ]
    if hits:
        x=hits[0]
        for z in hits[1:]:cs.remove(z)
    else:
        x=ET.SubElement(cs,C("constraint"))
    x.attrib.update({
        "id":id_,"type":typ,"value":str(val),"field":"selections","scope":"parent",
        "shared":"true","includeChildSelections":"false","includeChildForces":"false"
    })
    return x

def clear_modifiers_for_field(p,field):
    ms=p.find(C("modifiers"))
    if ms is None:return 0
    n=0
    for m in list(ms):
        if m.get("field")==field:
            ms.remove(m);n+=1
    return n

def add_set_modifier(p,id_,field,value,conditions,and_group=False):
    ms=cont(p,"modifiers")
    m=ET.SubElement(ms,C("modifier"),{"id":id_,"type":"set","field":field,"value":str(value)})
    if and_group and len(conditions)>1:
        cgs=ET.SubElement(m,C("conditionGroups"))
        cg=ET.SubElement(cgs,C("conditionGroup"),{"type":"and"})
        cs=ET.SubElement(cg,C("conditions"))
    else:
        cs=ET.SubElement(m,C("conditions"))
    for c in conditions:
        ET.SubElement(cs,C("condition"),{
            "type":c.get("type","atLeast"),"value":str(c.get("value",1)),
            "field":"selections","scope":c.get("scope","root-entry"),"childId":c["childId"],
            "shared":"true","includeChildSelections":"true","includeChildForces":"false"
        })
    return m

def root_owner(g):
    # direct owner selectionEntry
    pm={c:p for p in root.iter() for c in p}
    p=pm.get(g)
    while p is not None and p.tag!=C("selectionEntry"):p=pm.get(p)
    return p

# Every current Brotherhood-capable root has one direct Cult Power group.
roots=[]
for e in root.iter(C("selectionEntry")):
    pgs=[g for g in e.findall(f"./{C('selectionEntryGroups')}/{C('selectionEntryGroup')}")
         if (g.get("name") or "").startswith("Psychic Brotherhood — Cult Power")]
    if pgs:
        roots.append((e,pgs[0]))

if not roots:raise RuntimeError("No Brotherhood Cult Power roots found")

patched=[]
for e,pg in roots:
    # Find the actual Brotherhood purchase links on this exact root.
    brother_links=[]
    brother_targets=[]
    for x in e.iter(C("entryLink")):
        n=(x.get("name") or "").lower()
        if "brotherhood of psykers" in n and "power" not in n:
            if x.get("id") and x.get("id") not in brother_links:brother_links.append(x.get("id"))
            if x.get("targetId") and x.get("targetId") not in brother_targets:brother_targets.append(x.get("targetId"))
    if not brother_links:
        raise RuntimeError(f"{e.get('id')} has Cult Power group but no Brotherhood purchase link")

    # The old failure was MAX=0 plus a conditional MAX=1 modifier.
    # Make selection capacity reliable: max 1 always; min 0 until Brotherhood is bought.
    mn=ensure_one_constraint(pg,"min",0,(pg.get("id") or "power")+"-r67-min")
    mx=ensure_one_constraint(pg,"max",1,(pg.get("id") or "power")+"-r67-max")
    clear_modifiers_for_field(pg,mn.get("id"))
    clear_modifiers_for_field(pg,mx.get("id"))

    # Remove old legacy modifiers that target obsolete min/max constraint IDs.
    ms=pg.find(C("modifiers"))
    if ms is not None:
        for m in list(ms):
            field=m.get("field") or ""
            if field not in ("hidden",mn.get("id"),mx.get("id")) and ("power-min" in field or "powers-r64-min" in field or "powers-r64-max" in field):
                ms.remove(m)

    # Accept BOTH the local entry-link ID and the shared target ID as evidence.
    # Different NR/BattleScribe resolution paths count one or the other.
    evidence=[]
    for bid in brother_links+brother_targets:
        if bid not in evidence:evidence.append(bid)

    # Brotherhood makes one power mandatory. Multiple set-min modifiers are harmless;
    # whichever selected ID New Recruit recognizes sets min to 1.
    for idx,bid in enumerate(evidence):
        add_set_modifier(pg,f"{pg.get('id')}-r67-min-{idx}",mn.get("id"),1,[
            {"childId":bid,"scope":"root-entry","type":"atLeast","value":1}
        ])

    # Power options: keep the existing Cult lock, but add one clean "no Brotherhood"
    # hide condition using all recognized Brotherhood IDs.
    power_options=[]
    power_options += pg.findall(f"./{C('entryLinks')}/{C('entryLink')}")
    power_options += pg.findall(f"./{C('selectionEntries')}/{C('selectionEntry')}")
    if not power_options:
        # Some Rite clones carry only an empty psychic-shell group and inherit their
        # real choices elsewhere. Do not manufacture duplicate powers there.
        continue
    if len(power_options)<35:raise RuntimeError(f"{e.get('id')} has incomplete power pool: {len(power_options)}")
    for pidx,opt in enumerate(power_options):
        # Remove any earlier R67 modifier if working-copy rerun.
        oms=opt.find(C("modifiers"))
        if oms is not None:
            for m in list(oms):
                if "-r67-hide-no-brotherhood" in (m.get("id") or ""):oms.remove(m)
        add_set_modifier(opt,f"{opt.get('id')}-r67-hide-no-brotherhood","hidden","true",
            [{"childId":bid,"scope":"root-entry","type":"lessThan","value":1} for bid in evidence],
            and_group=True)

    pg.set("name","Psychic Brotherhood — Cult-correlated Psychic Power (choose 1)")
    pg.set("hidden","false")
    patched.append((e.get("id"),e.get("name"),pg.get("id"),brother_links,brother_targets,len(power_options)))

# Revision/index.
root.set("revision","67")
tree.write(CAT,encoding="utf-8",xml_declaration=True)
ET.register_namespace("",INS)
it=ET.parse(IDX);ir=it.getroot()
for x in ir.iter(I("dataIndexEntry")):
    if x.get("filePath")=="Legiones Astartes.cat":x.set("dataRevision","67")
it.write(IDX,encoding="utf-8",xml_declaration=True)

# Validation.
rr=ET.parse(CAT).getroot(); rids={x.get("id"):x for x in rr.iter() if x.get("id")}; checks=[]
def ck(n,o):
    checks.append((n,bool(o)))
    if not o:raise RuntimeError("R67 validation failed: "+n)

ck("CAT67",rr.get("revision")=="67")
ck("GST dependency remains 15",rr.get("gameSystemRevision")=="15")
ck("Index67",'dataRevision="67"' in IDX.read_text(encoding="utf-8"))
ck("At least one real Brotherhood power root patched",len(patched)>=1)

for eid,name,pgid,links,targets,count in patched:
    pg=rids[pgid]
    cs=pg.findall(f"./{C('constraints')}/{C('constraint')}")
    ck(name+" max one power",any(x.get("type")=="max" and x.get("value")=="1" for x in cs))
    ck(name+" base min zero",any(x.get("type")=="min" and x.get("value")=="0" for x in cs))
    xml=ET.tostring(pg,encoding="unicode")
    ck(name+" Brotherhood min evidence",all(x in xml for x in links+targets))
    opts=[]
    opts += pg.findall(f"./{C('entryLinks')}/{C('entryLink')}")
    opts += pg.findall(f"./{C('selectionEntries')}/{C('selectionEntry')}")
    ck(name+" powers retained",len(opts)==count and count>=35)
    ck(name+" every power gated by Brotherhood",all("-r67-hide-no-brotherhood" in ET.tostring(x,encoding="unicode") for x in opts))
    ck(name+" Cult locks retained",all("r63-cult-lock" in ET.tostring(x,encoding="unicode") for x in opts))

# Main Veteran specifically.
v=rids["veteran-unit"]
vpg=next(g for g in v.findall(f"./{C('selectionEntryGroups')}/{C('selectionEntryGroup')}")
         if (g.get("name") or "").startswith("Psychic Brotherhood — Cult-correlated"))
ck("Main Veteran power group present",vpg is not None)
vmx=next(x for x in vpg.findall(f"./{C('constraints')}/{C('constraint')}") if x.get("type")=="max")
ck("Main Veteran no longer max0",vmx.get("value")=="1")
vopts=vpg.findall(f"./{C('entryLinks')}/{C('entryLink')}")+vpg.findall(f"./{C('selectionEntries')}/{C('selectionEntry')}")
ck("Main Veteran has 35 powers",len(vopts)==35)

new=collections.Counter(x.get("id") for x in rr.iter() if x.get("id"))
worse={k:v for k,v in new.items() if v>max(1,baseline.get(k,0))}
ck("No new/worsened duplicate IDs",not worse)

OUT.write_text("\n".join([
"Live R67 — Thousand Sons Brotherhood power selection repair",
"Input CAT=66/GST=15 -> CAT=67/GST remains 15","",
"FIX:",
f"- Patched {len(patched)} live Veteran/Terminator roots that directly own the 35-power Brotherhood pool.",
"- Removed the fragile power-group MAX=0 architecture.",
"- Every Cult-correlated power group now has a reliable base MAX=1, so New Recruit can actually select a power.",
"- Base MIN remains 0; selecting Brotherhood sets MIN=1.",
"- Brotherhood detection now accepts both the local entry-link ID and its shared Brotherhood target ID, avoiding New Recruit link-resolution differences.",
"- Every psychic power is hidden while no Brotherhood upgrade is selected.",
"- Existing Prosperine Cult correlation remains intact: Pavoni/Biomancy, Raptora/Telekinesis, Corvidae/Divination, Athanaeans/Telepathy, Pyrae/Pyromancy.",
"- Main Legion Veteran Squad retains all 35 canonical powers (7 per correlated discipline) and may select exactly one after Brotherhood is purchased.",
"- No Veteran melee scaling, Centurion, Praetor or Shattered-Legions assignment logic changed.","",
"PATCHED ROOTS:"
]+[f"- {name} ({eid}) — {count} powers; Brotherhood links {links}; targets {targets}" for eid,name,pgid,links,targets,count in patched]+[
"","VALIDATION:"
]+[f'- {"PASS" if ok else "FAIL"}: {n}' for n,ok in checks])+"\n",encoding="utf-8")
print(OUT.read_text())
