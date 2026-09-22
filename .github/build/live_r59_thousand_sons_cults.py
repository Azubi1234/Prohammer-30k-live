from pathlib import Path
import copy, collections, hashlib, re, xml.etree.ElementTree as ET

CAT=Path("Legiones Astartes.cat"); IDX=Path("index.xml")
OUT=Path("inspection-live-r59-thousand-sons-cults.txt")
NS="http://www.battlescribe.net/schema/catalogueSchema"; INS="http://www.battlescribe.net/schema/dataIndexSchema"
ET.register_namespace("",NS)
C=lambda t:f"{{{NS}}}{t}"; I=lambda t:f"{{{INS}}}{t}"

tree=ET.parse(CAT); root=tree.getroot()
if root.get("revision")!="58":
    raise RuntimeError(f"R59 expected CAT58, got {root.get('revision')}")
if root.get("gameSystemRevision")!="14":
    raise RuntimeError(f"R59 expected GST14 dependency, got {root.get('gameSystemRevision')}")
baseline=collections.Counter(x.get("id") for x in root.iter() if x.get("id"))
ids={x.get("id"):x for x in root.iter() if x.get("id")}

LEGION="legion-xv"

def cont(p,tag,before=("constraints","categoryLinks","entryLinks","infoLinks","profiles","rules","selectionEntries","selectionEntryGroups","costs","modifiers")):
    q=C(tag); x=p.find(q)
    if x is not None: return x
    x=ET.Element(q); kids=list(p); idx=len(kids)
    for j,k in enumerate(kids):
        if k.tag.split("}")[-1] in before:
            idx=j; break
    p.insert(idx,x); return x

def cons(p,id_,typ,val,field="selections",scope="parent",child=False):
    cs=cont(p,"constraints"); x=next((z for z in cs.findall(C("constraint")) if z.get("id")==id_),None)
    if x is None: x=ET.SubElement(cs,C("constraint"))
    x.attrib.update({
        "id":id_,"type":typ,"value":str(val),"field":field,"scope":scope,
        "shared":"true","includeChildSelections":"true" if child else "false","includeChildForces":"false"
    })
    return x

def modifier(p,id_,typ,field,value,conds=None):
    ms=cont(p,"modifiers"); x=next((z for z in ms.findall(C("modifier")) if z.get("id")==id_),None)
    if x is None: x=ET.SubElement(ms,C("modifier"))
    x.attrib.update({"id":id_,"type":typ,"field":field,"value":str(value)})
    for ch in list(x): x.remove(ch)
    if conds:
        if len(conds)==1:
            target=ET.SubElement(x,C("conditions"))
        else:
            cgs=ET.SubElement(x,C("conditionGroups"))
            cg=ET.SubElement(cgs,C("conditionGroup"),{"type":"and"})
            target=ET.SubElement(cg,C("conditions"))
        for c in conds:
            ET.SubElement(target,C("condition"),{
                "type":c.get("type","atLeast"),"value":str(c.get("value",1)),
                "field":c.get("field","selections"),"scope":c.get("scope","roster"),
                "childId":c["childId"],"shared":"true",
                "includeChildSelections":"true" if c.get("includeChildSelections",True) else "false",
                "includeChildForces":"false"
            })
    return x

def remove_hidden_modifiers(e):
    ms=e.find(C("modifiers"))
    if ms is None: return 0
    n=0
    for m in list(ms):
        if m.get("field")=="hidden":
            ms.remove(m); n+=1
    return n

def add_hide_if_not_xv(e,prefix):
    modifier(e,prefix+"-hide-not-xv","set","hidden","true",[
        {"childId":LEGION,"scope":"roster","type":"lessThan","value":1}
    ])

def ensure_max(e,id_,value):
    cs=cont(e,"constraints")
    maxs=[x for x in cs.findall(C("constraint")) if x.get("type")=="max"]
    if maxs:
        maxs[0].set("value",str(value))
        for x in maxs[1:]: cs.remove(x)
        return maxs[0]
    return cons(e,id_,"max",value)

def unique_info_copy(src_info,dst,prefix):
    for i,il in enumerate(src_info):
        cp=copy.deepcopy(il)
        cp.set("id",f"{prefix}-info-{i}")
        dst.append(cp)

# ----------------------------------------------------------------------
# 1) Prosperine Cults: replace fragile shared selection-entry links with
#    local 1-of-5 selections, but keep canonical shared RULE references.
# ----------------------------------------------------------------------
CULT_TARGETS={
    "Pavoni":"r41-universal-gear-b478f13351e219",
    "Raptora":"r41-universal-gear-672318630ac401",
    "Corvidae":"r41-universal-gear-89023418208357",
    "Athanaeans":"r41-universal-gear-1cf60d95bdb439",
    "Pyrae":"r41-universal-gear-79bc55e0fd1aa0",
}
for name,tid in CULT_TARGETS.items():
    if tid not in ids: raise RuntimeError(f"Missing canonical Cult target {name}: {tid}")

cult_groups=[g for g in root.iter(C("selectionEntryGroup")) if (g.get("name") or "")=="Prosperine Cult"]
if not cult_groups: raise RuntimeError("No Prosperine Cult groups found")

converted_groups=0; converted_choices=0; hidden_mods_removed=0
for g in cult_groups:
    g.set("hidden","false")
    hidden_mods_removed += remove_hidden_modifiers(g)
    add_hide_if_not_xv(g,(g.get("id") or "cult")+"-r59")

    # enforce exact 1-of-5 whenever the group is visible
    cs=cont(g,"constraints")
    mins=[x for x in cs.findall(C("constraint")) if x.get("type")=="min"]
    maxs=[x for x in cs.findall(C("constraint")) if x.get("type")=="max"]
    if mins:
        mins[0].set("value","1")
        for x in mins[1:]: cs.remove(x)
    else:
        cons(g,(g.get("id") or "cult")+"-r59-min","min",1)
    if maxs:
        maxs[0].set("value","1")
        for x in maxs[1:]: cs.remove(x)
    else:
        cons(g,(g.get("id") or "cult")+"-r59-max","max",1)

    # capture any existing option IDs, then replace the linked-selection UI
    existing_links={}
    elc=g.find(C("entryLinks"))
    if elc is not None:
        for l in list(elc):
            if (l.get("name") or "") in CULT_TARGETS:
                existing_links[l.get("name")]=l.get("id")
        g.remove(elc)

    sec=g.find(C("selectionEntries"))
    if sec is not None:
        # remove only existing Cult choices; preserve unrelated local entries if any
        for e in list(sec):
            if (e.get("name") or "") in CULT_TARGETS:
                sec.remove(e)
    else:
        sec=cont(g,"selectionEntries",before=("selectionEntryGroups","costs","modifiers"))

    for idx,name in enumerate(["Pavoni","Raptora","Corvidae","Athanaeans","Pyrae"]):
        eid=existing_links.get(name) or f"{g.get('id')}-r59-{idx}"
        e=ET.SubElement(sec,C("selectionEntry"),{
            "id":eid,"name":name,"type":"upgrade","hidden":"false"
        })
        cons(e,eid+"-max","max",1)
        target=ids[CULT_TARGETS[name]]
        src_infos=target.findall(f"./{C('infoLinks')}/{C('infoLink')}")
        if not src_infos:
            raise RuntimeError(f"Canonical Cult target {name} has no infoLinks")
        dst=cont(e,"infoLinks",before=("profiles","rules","selectionEntries","selectionEntryGroups","costs","modifiers"))
        unique_info_copy(src_infos,dst,eid+"-r59")
        converted_choices+=1
    converted_groups+=1

# Refresh IDs after local conversions
ids={x.get("id"):x for x in root.iter() if x.get("id")}

# ----------------------------------------------------------------------
# 2) Centurion: the package existed but New Recruit didn't render it.
#    Use the same visible-by-default / hide-if-not-XV convention as Cults.
# ----------------------------------------------------------------------
CENT_PKG="r57-ts-centurion-psychic-package"
centpkg=ids.get(CENT_PKG)
if centpkg is None: raise RuntimeError("R57 Thousand Sons Centurion psychic package missing")
centpkg.set("hidden","false")
cent_hidden_removed=remove_hidden_modifiers(centpkg)
add_hide_if_not_xv(centpkg,"r59-ts-centurion-package")

# Each local Cult choice must remain present with a non-empty power list.
cent_cult_ids=[
    "r57-ts-centurion-cult-biomancy",
    "r57-ts-centurion-cult-telekinesis",
    "r57-ts-centurion-cult-divination",
    "r57-ts-centurion-cult-telepathy",
    "r57-ts-centurion-cult-pyromancy",
]
for eid in cent_cult_ids:
    if eid not in ids: raise RuntimeError("Missing Centurion Cult choice "+eid)
    ids[eid].set("hidden","false")

# ----------------------------------------------------------------------
# 3) Veteran close-combat replacements:
#    remove repeat-based max math and replace with explicit 5..10 values.
#    Apply to every current Veteran copy carrying the same live option group.
# ----------------------------------------------------------------------
veteran_roots=[]
for e in root.iter(C("selectionEntry")):
    if (e.get("name") or "")!="Legion Veteran Squad": continue
    melee=next((g for g in e.iter(C("selectionEntryGroup")) if (g.get("name") or "")=="Close Combat Weapon Replacements"),None)
    models=next((m for m in e.findall(f"./{C('selectionEntries')}/{C('selectionEntry')}") if (m.get("name") or "")=="Legion Veterans"),None)
    if melee is not None and models is not None:
        veteran_roots.append((e,models,melee))

if not veteran_roots: raise RuntimeError("No Veteran roots with melee group/model selector found")

melee_roots_fixed=0; melee_options_fixed=0; repeat_mods_removed=0
for vr,models,melee in veteran_roots:
    # Aggregate group maximum = ordinary Veterans + Sergeant = total squad size.
    mcs=cont(melee,"constraints")
    maxs=[x for x in mcs.findall(C("constraint")) if x.get("type")=="max"]
    if maxs:
        mx=maxs[0]; mx.set("value","5")
        for x in maxs[1:]: mcs.remove(x)
    else:
        mx=cons(melee,(melee.get("id") or "melee")+"-r59-max","max",5)
    maxid=mx.get("id")

    # Remove old modifiers that write this max field, including repeat math.
    ms=melee.find(C("modifiers"))
    if ms is not None:
        for m in list(ms):
            if m.get("field")==maxid:
                ms.remove(m); repeat_mods_removed+=1

    # ordinary Veteran count 4 => total 5. Counts 5..9 => total 6..10.
    for ordinary in range(5,10):
        modifier(melee,
                 f"{melee.get('id')}-r59-total-{ordinary+1}",
                 "set",maxid,ordinary+1,[
                     {"childId":models.get("id"),"scope":"root-entry","type":"atLeast",
                      "value":ordinary,"includeChildSelections":False}
                 ])

    # Any single melee replacement option may be selected for the full 10-model squad.
    for container_tag in ("entryLinks","selectionEntries"):
        cc=melee.find(C(container_tag))
        if cc is None: continue
        for opt in list(cc):
            ensure_max(opt,(opt.get("id") or "melee-opt")+"-r59-max",10)
            melee_options_fixed+=1
    melee_roots_fixed+=1

# ----------------------------------------------------------------------
# 4) Sanity checks for source-specific Cult eligibility.
#    These are audit-only: do not invent Cult access where source says none.
# ----------------------------------------------------------------------
def find_root_contains(fragment, xv_only=False):
    rows=[e for e in root.findall(f"./{C('selectionEntries')}/{C('selectionEntry')}") if fragment in (e.get("name") or "").lower()]
    if xv_only:
        rows=[e for e in rows if (e.get("id") or "").startswith("r41-unit-xv-")]
    return rows

def has_cult_group(e):
    # Direct unit selector only; nested retinues are separate units and may have their own Cult.
    return any((g.get("name") or "")=="Prosperine Cult" for g in e.findall(f"./{C('selectionEntryGroups')}/{C('selectionEntryGroup')}"))

required_cult_units={
    "sekhemt":["sekhmet","sekhemet"], # tolerate catalogue spelling
    "khenetai":["khenetai"],
    "ammitara":["ammitara"],
    "numerologist":["numerologist"],
}
cult_presence={}
for label,frags in required_cult_units.items():
    matches=[]
    for f in frags: matches += find_root_contains(f, True)
    # unique by id
    uniq={e.get("id"):e for e in matches}.values()
    cult_presence[label]=[(e.get("id"),has_cult_group(e)) for e in uniq]

no_cult_units={}
for label,frag in [("castellax","castellax-achea"),("osiron","osiron")]:
    matches=find_root_contains(frag, True)
    no_cult_units[label]=[(e.get("id"),has_cult_group(e)) for e in matches]

# ----------------------------------------------------------------------
# Revision/index.
# ----------------------------------------------------------------------
root.set("revision","59")
tree.write(CAT,encoding="utf-8",xml_declaration=True)
ET.register_namespace("",INS)
it=ET.parse(IDX); ir=it.getroot()
for x in ir.iter(I("dataIndexEntry")):
    if x.get("filePath")=="Legiones Astartes.cat":
        x.set("dataRevision","59")
it.write(IDX,encoding="utf-8",xml_declaration=True)

# ----------------------------------------------------------------------
# Validation after write.
# ----------------------------------------------------------------------
rr=ET.parse(CAT).getroot(); rids={x.get("id"):x for x in rr.iter() if x.get("id")}; checks=[]
def ck(name,ok):
    checks.append((name,bool(ok)))
    if not ok: raise RuntimeError("R59 validation failed: "+name)

ck("CAT revision 59",rr.get("revision")=="59")
ck("GST dependency remains 14",rr.get("gameSystemRevision")=="14")
ck("Index CAT59",'dataRevision="59"' in IDX.read_text(encoding="utf-8"))

# All Cult groups local and robust.
cult_after=[g for g in rr.iter(C("selectionEntryGroup")) if (g.get("name") or "")=="Prosperine Cult"]
ck("Cult group count preserved",len(cult_after)==len(cult_groups))
for g in cult_after:
    local=g.findall(f"./{C('selectionEntries')}/{C('selectionEntry')}")
    links=g.findall(f"./{C('entryLinks')}/{C('entryLink')}")
    ck(g.get("id")+" has five local Cults",len([x for x in local if (x.get("name") or "") in CULT_TARGETS])==5)
    ck(g.get("id")+" has no linked Cult selections",not any((x.get("name") or "") in CULT_TARGETS for x in links))
    ck(g.get("id")+" visible-default",g.get("hidden")!="true")
    txt=ET.tostring(g,encoding="unicode")
    ck(g.get("id")+" hides outside XV",LEGION in txt and 'type="lessThan"' in txt)
    for x in local:
        if (x.get("name") or "") not in CULT_TARGETS: continue
        ck(x.get("id")+" has Cult rule refs",len(x.findall(f"./{C('infoLinks')}/{C('infoLink')}"))>=1)

# Centurion UI
cp=rids[CENT_PKG]
ck("Centurion TS package visible-default",cp.get("hidden")!="true")
cptxt=ET.tostring(cp,encoding="unicode")
ck("Centurion TS package hides outside XV",LEGION in cptxt and 'type="lessThan"' in cptxt)
ck("Centurion has five Cult choices",len(cp.findall(f"./{C('selectionEntries')}/{C('selectionEntry')}"))==5)
for d in ["biomancy","telekinesis","divination","telepathy","pyromancy"]:
    pg=rids[f"r57-ts-centurion-{d}-powers"]
    ck("Centurion "+d+" power list nonempty",len(pg.findall(f"./{C('entryLinks')}/{C('entryLink')}"))>0)

# Praetor and Brotherhood structures still exist.
for rid in ["r45-cult-hq-praetor","r19-ts-praetor-disciplines","r19-ts-praetor-powers",
            "r45-cult-veteran-unit","r19-ts-veteran-unit-brotherhood-disciplines","r19-ts-veteran-unit-brotherhood-powers",
            "r45-cult-terminator-unit","r19-ts-terminator-unit-brotherhood-disciplines","r19-ts-terminator-unit-brotherhood-powers"]:
    ck(rid+" exists",rid in rids)

# Veteran scaling in every detected live Veteran copy.
for oldvr,oldmodels,oldmelee in veteran_roots:
    vr=rids[oldvr.get("id")]
    models=next((m for m in vr.findall(f"./{C('selectionEntries')}/{C('selectionEntry')}") if (m.get("name") or "")=="Legion Veterans"),None)
    melee=next((g for g in vr.iter(C("selectionEntryGroup")) if (g.get("name") or "")=="Close Combat Weapon Replacements"),None)
    ck(vr.get("id")+" Veteran model selector exists",models is not None)
    ck(vr.get("id")+" melee group exists",melee is not None)
    maxc=next(x for x in melee.findall(f"./{C('constraints')}/{C('constraint')}") if x.get("type")=="max")
    ck(vr.get("id")+" melee base max5",maxc.get("value")=="5")
    mt=ET.tostring(melee,encoding="unicode")
    ck(vr.get("id")+" melee scales to 10",f'field="{maxc.get("id")}" value="10"' in mt and models.get("id") in mt)
    max_writers=[m for m in melee.findall(f"./{C('modifiers')}/{C('modifier')}") if m.get("field")==maxc.get("id")]
    ck(vr.get("id")+" no repeat max math",all(m.find(C("repeats")) is None for m in max_writers))
    for cc_tag in ("entryLinks","selectionEntries"):
        cc=melee.find(C(cc_tag))
        if cc is None: continue
        for opt in list(cc):
            maxvals=[float(x.get("value")) for x in opt.findall(f"./{C('constraints')}/{C('constraint')}") if x.get("type")=="max"]
            ck(opt.get("id")+" individual max10",maxvals and max(maxvals)>=10)

# Source-specific Cult access/exclusions.
for label,rows in cult_presence.items():
    ck(label+" unit found",bool(rows))
    ck(label+" has Cult",all(v for _,v in rows))
for label,rows in no_cult_units.items():
    ck(label+" unit found",bool(rows))
    ck(label+" has no Cult",all(not v for _,v in rows))

# Named fixed-cult characters should not gain a generic Cult selector.
for fragment in ["ahzek ahriman","phosis t'kar","magistus amon","hathor maat","sanakht"]:
    matches=find_root_contains(fragment, True)
    ck(fragment+" found",bool(matches))
    ck(fragment+" no generic Cult selector",all(not has_cult_group(e) for e in matches))

# IDs.
new=collections.Counter(x.get("id") for x in rr.iter() if x.get("id"))
worse={k:v for k,v in new.items() if v>max(1,baseline.get(k,0))}
if worse: print("R59_DUPLICATES",worse)
ck("No new/worsened duplicate IDs",not worse)

OUT.write_text("\n".join([
    "Live R59 — Thousand Sons Cult / psychic UI rebuild",
    "Input CAT58/GST14 -> CAT59/GST14","",
    "WHY:",
    "- The Prosperine Cult system existed in XML, but most Cult options were entryLinks to shared selection entries. New Recruit rendered the parent group while failing to expose the linked Cult choices.",
    "- The R57 Centurion package used hidden=true plus a positive show modifier, which was still not reliably rendering in New Recruit.",
    "- Veteran melee replacement scaling relied on repeat-based modifier math; New Recruit was still capping the visible choice at five in a 10-model squad.","",
    "CULT REBUILD:",
    f"- Rebuilt {converted_groups} existing Prosperine Cult groups into local 1-of-5 choices ({converted_choices} local Cult selections).",
    "- The local choices keep their existing option IDs wherever possible, so all Cult->discipline restrictions continue to work.",
    "- Cult choices reference the existing canonical Cult rules; no duplicate Cult rule definitions were created.",
    "- Every Cult group is now visible by default and hidden only when XV Legion is absent.",
    "- No new Cult access was invented: Castellax-Achea and Osiron remain without Cults; fixed-Cult named characters remain fixed.","",
    "CENTURION:",
    f"- Removed {cent_hidden_removed} fragile hidden/show modifier(s) from the R57 Centurion package.",
    "- Thousand Sons Centurion Cult & Psychic Powers is now visible-default and hidden only outside XV.",
    "- Exactly one Cult remains mandatory; its corresponding psychic power list remains directly nested under the Cult choice.",
    "- Normal Centurion remains ML1 / one power; Librarian Epistolary remains two powers.","",
    "VETERANS:",
    f"- Rebuilt close-combat replacement scaling on {melee_roots_fixed} Veteran entries/copies.",
    "- 5-model Veteran squad: max 5 melee replacements.",
    "- 10-model Veteran squad: max 10 melee replacements.",
    f"- Updated {melee_options_fixed} individual melee options to allow up to 10, with the aggregate squad-size cap enforced by the parent group.",
    f"- Removed {repeat_mods_removed} repeat-based melee max modifier(s).",
    "- Pride of the Legion Veteran copy receives the same scaling as the base Veteran Squad.","",
    "VALIDATION:"
]+[f'- {"PASS" if ok else "FAIL"}: {n}' for n,ok in checks])+"\n",encoding="utf-8")
print(OUT.read_text())
