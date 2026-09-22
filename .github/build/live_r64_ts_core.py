from pathlib import Path
import copy, collections, re, xml.etree.ElementTree as ET

CAT=Path("Legiones Astartes.cat"); IDX=Path("index.xml")
OUT=Path("inspection-live-r64-ts-core-psychic-veterans.txt")
NS="http://www.battlescribe.net/schema/catalogueSchema"; INS="http://www.battlescribe.net/schema/dataIndexSchema"
ET.register_namespace("",NS)
C=lambda t:f"{{{NS}}}{t}"; I=lambda t:f"{{{INS}}}{t}"

tree=ET.parse(CAT); root=tree.getroot()
if root.get("revision")!="63": raise RuntimeError(f"R64 expected CAT63, got {root.get('revision')}")
if root.get("gameSystemRevision")!="15": raise RuntimeError(f"R64 expected GST15, got {root.get('gameSystemRevision')}")
baseline=collections.Counter(x.get("id") for x in root.iter() if x.get("id"))
ids={x.get("id"):x for x in root.iter() if x.get("id")}

LEG="legion-xv"; SHAT="r62-shattered-theme"

def cont(p,tag,before=("constraints","categoryLinks","entryLinks","infoLinks","profiles","rules","selectionEntries","selectionEntryGroups","costs","modifiers")):
    q=C(tag); x=p.find(q)
    if x is not None:return x
    x=ET.Element(q); kids=list(p); idx=len(kids)
    for j,k in enumerate(kids):
        if k.tag.split("}")[-1] in before:idx=j;break
    p.insert(idx,x); return x

def ensure_constraint(p,id_,typ,val,field="selections",scope="parent",child=False):
    cs=cont(p,"constraints"); hits=[z for z in cs.findall(C("constraint")) if z.get("type")==typ]
    x=next((z for z in hits if z.get("id")==id_),None)
    if x is None and hits:
        x=hits[0]; x.set("id",id_)
        for z in hits[1:]:cs.remove(z)
    if x is None:x=ET.SubElement(cs,C("constraint"))
    x.attrib.update({"id":id_,"type":typ,"value":str(val),"field":field,"scope":scope,
                     "shared":"true","includeChildSelections":"true" if child else "false","includeChildForces":"false"})
    return x

def clear_field_mods(e,field):
    ms=e.find(C("modifiers"))
    if ms is None:return 0
    n=0
    for m in list(ms):
        if m.get("field")==field:
            ms.remove(m); n+=1
    return n

def clear_all_mods(e):
    ms=e.find(C("modifiers"))
    if ms is not None:e.remove(ms)

def add_conditions_modifier(p,id_,typ,field,value,conds):
    ms=cont(p,"modifiers"); m=ET.SubElement(ms,C("modifier"),{"id":id_,"type":typ,"field":field,"value":str(value)})
    if len(conds)==1:
        target=ET.SubElement(m,C("conditions"))
    else:
        cgs=ET.SubElement(m,C("conditionGroups")); cg=ET.SubElement(cgs,C("conditionGroup"),{"type":"and"}); target=ET.SubElement(cg,C("conditions"))
    for c in conds:
        ET.SubElement(target,C("condition"),{
            "type":c.get("type","atLeast"),"value":str(c.get("value",1)),"field":"selections",
            "scope":c.get("scope","roster"),"childId":c["childId"],"shared":"true",
            "includeChildSelections":"true" if c.get("includeChildSelections",True) else "false",
            "includeChildForces":"false"
        })
    return m

def add_repeat_modifier(p,id_,field,child,value=1):
    ms=cont(p,"modifiers"); m=ET.SubElement(ms,C("modifier"),{"id":id_,"type":"increment","field":field,"value":str(value)})
    rs=ET.SubElement(m,C("repeats"))
    ET.SubElement(rs,C("repeat"),{
        "value":"1","repeats":"1","field":"selections","scope":"root-entry","childId":child,
        "shared":"true","roundUp":"false","includeChildSelections":"false","includeChildForces":"false"
    })
    return m

def add_rule(p,id_,name,text):
    rs=cont(p,"rules"); r=ET.SubElement(rs,C("rule"),{"id":id_,"name":name,"hidden":"false"})
    d=ET.SubElement(r,C("description"));d.text=text;return r

def shared_rule(id_,name,text):
    sr=root.find(C("sharedRules"))
    if sr is None:
        sr=ET.Element(C("sharedRules")); root.insert(0,sr)
    r=next((x for x in sr.findall(C("rule")) if x.get("id")==id_),None)
    if r is None:r=ET.SubElement(sr,C("rule"),{"id":id_,"name":name,"hidden":"false"})
    r.set("name",name); d=r.find(C("description"))
    if d is None:d=ET.SubElement(r,C("description"))
    d.text=text;return r

def add_conditional_info(root_entry,id_,name,target,assign_id,extra_hide_child=None):
    ils=cont(root_entry,"infoLinks"); old=next((x for x in ils.findall(C("infoLink")) if x.get("id")==id_),None)
    if old is not None:ils.remove(old)
    x=ET.SubElement(ils,C("infoLink"),{"id":id_,"name":name,"targetId":target,"type":"rule","hidden":"false"})
    # Hide if neither a normal XV army nor Shattered theme.
    add_conditions_modifier(x,id_+"-hide-not-ts","set","hidden","true",[
        {"childId":LEG,"scope":"roster","type":"lessThan","value":1},
        {"childId":SHAT,"scope":"roster","type":"lessThan","value":1},
    ])
    # In Shattered mode, only an XV-assigned character is a Thousand Sons Psyker.
    add_conditions_modifier(x,id_+"-hide-wrong-shattered","set","hidden","true",[
        {"childId":assign_id,"scope":"root-entry","type":"lessThan","value":1},
        {"childId":SHAT,"scope":"roster","type":"atLeast","value":1},
    ])
    if extra_hide_child:
        add_conditions_modifier(x,id_+"-hide-higher-ml","set","hidden","true",[
            {"childId":extra_hide_child,"scope":"root-entry","type":"atLeast","value":1}
        ])
    return x

def extract_assign_id(group):
    for c in group.iter(C("condition")):
        cid=c.get("childId") or ""
        if cid.startswith("r62-shat-assign-"):return cid
    return None

def clean_ts_visibility(group,assign_id,prefix):
    group.set("hidden","false")
    clear_field_mods(group,"hidden")
    add_conditions_modifier(group,prefix+"-hide-not-ts","set","hidden","true",[
        {"childId":LEG,"scope":"roster","type":"lessThan","value":1},
        {"childId":SHAT,"scope":"roster","type":"lessThan","value":1},
    ])
    add_conditions_modifier(group,prefix+"-hide-wrong-shattered","set","hidden","true",[
        {"childId":assign_id,"scope":"root-entry","type":"lessThan","value":1},
        {"childId":SHAT,"scope":"roster","type":"atLeast","value":1},
    ])

# ------------------------------------------------------------------
# 1) Explicit Thousand Sons Psyker levels on generic HQs.
# ------------------------------------------------------------------
ml1=shared_rule("r64-ts-psyker-ml1","Psyker (Mastery Level 1)",
    "A Thousand Sons Centurion and its Consul variants are Psykers (Mastery Level 1) unless another rule grants a higher Mastery Level. "
    "The model selects powers only from the Psychic Discipline associated with its chosen Prosperine Cult. "
    "A Librarian Consul follows its normal Librarian Mastery Level rules.")
ml2=shared_rule("r64-ts-psyker-ml2","Psyker (Mastery Level 2)",
    "A Thousand Sons Praetor is a Psyker (Mastery Level 2). It selects its psychic powers only from the Psychic Discipline associated with its chosen Prosperine Cult. "
    "If upgraded to Mastery Level 3 by an applicable Rite of War, it instead knows and may select three powers from that same Cult-correlated Discipline.")

cent=ids["hq-centurion"]; pra=ids["hq-praetor"]
cent_pkg=ids["r57-ts-centurion-psychic-package"]
cent_assign=extract_assign_id(cent_pkg) or "r62-shat-assign-2a678f656c73"
clean_ts_visibility(cent_pkg,cent_assign,"r64-ts-centurion-package")
# Ensure the package itself says what the model is.
rs=cent_pkg.find(C("rules"))
if rs is not None:
    for r in list(rs):
        if "Sorcerers of Prospero" in (r.get("name") or "") or "Psyker" in (r.get("name") or ""):rs.remove(r)
add_rule(cent_pkg,"r64-ts-centurion-package-ml","Psyker (Mastery Level 1)",
         "This Thousand Sons Centurion is a Psyker (Mastery Level 1), unless a Consul upgrade grants a higher Mastery Level.")
add_conditional_info(cent,"r64-ts-centurion-psyker-link","Psyker (Mastery Level 1)",ml1.get("id"),cent_assign,"hq-consul-librarian-epistolary")

# Harden every Centurion nested power group.
cent_choices=cent_pkg.findall(f"./{C('selectionEntries')}/{C('selectionEntry')}")
if len(cent_choices)!=5:raise RuntimeError(f"Centurion expected 5 Cult choices, got {len(cent_choices)}")
for ce in cent_choices:
    pgs=ce.findall(f"./{C('selectionEntryGroups')}/{C('selectionEntryGroup')}")
    if len(pgs)!=1:raise RuntimeError(f"Centurion {ce.get('name')} expected one power group")
    pg=pgs[0]
    mn=ensure_constraint(pg,pg.get("id")+"-r64-min","min",1)
    mx=ensure_constraint(pg,pg.get("id")+"-r64-max","max",1)
    # Preserve only non-min/max modifiers; then explicitly set Epistolary to two.
    clear_field_mods(pg,mn.get("id"));clear_field_mods(pg,mx.get("id"))
    add_conditions_modifier(pg,pg.get("id")+"-r64-epi-min","set",mn.get("id"),2,[{"childId":"hq-consul-librarian-epistolary","scope":"root-entry"}])
    add_conditions_modifier(pg,pg.get("id")+"-r64-epi-max","set",mx.get("id"),2,[{"childId":"hq-consul-librarian-epistolary","scope":"root-entry"}])

# ------------------------------------------------------------------
# 2) Rebuild Praetor psychic UI as direct Cult -> correlated powers.
#    The existing R59 local Cult IDs broke the old R29 discipline gates.
# ------------------------------------------------------------------
old_cult=ids["r45-cult-hq-praetor"]; old_power=ids["r19-ts-praetor-powers"]
pra_assign=extract_assign_id(old_cult) or "r62-shat-assign-d301e2010305"

# Capture canonical Cult info and canonical powers.
cult_info={}
for ce in old_cult.findall(f"./{C('selectionEntries')}/{C('selectionEntry')}"):
    cult_info[ce.get("name")]=[copy.deepcopy(x) for x in ce.findall(f"./{C('infoLinks')}/{C('infoLink')}")]

power_by_disc=collections.defaultdict(list)
for x in old_power.findall(f"./{C('selectionEntries')}/{C('selectionEntry')}"):
    xid=(x.get("id") or "").lower()
    m=re.search(r"power-(biomancy|divination|pyromancy|telekinesis|telepathy)-",xid)
    if m and x.get("targetId"):
        power_by_disc[m.group(1)].append((x.get("name"),x.get("targetId")))
for d in ["biomancy","divination","pyromancy","telekinesis","telepathy"]:
    if len(power_by_disc[d])<5:raise RuntimeError("Praetor canonical power pool incomplete: "+d)

sgs=cont(pra,"selectionEntryGroups",before=("costs","modifiers"))
for gid in ["r45-cult-hq-praetor","r19-ts-praetor-disciplines","r19-ts-praetor-powers"]:
    for g in list(sgs.findall(C("selectionEntryGroup"))):
        if g.get("id")==gid:sgs.remove(g)

pkg=ET.SubElement(sgs,C("selectionEntryGroup"),{"id":"r64-ts-praetor-psychic-package","name":"Thousand Sons — Prosperine Cult & Psychic Powers","hidden":"false"})
ensure_constraint(pkg,"r64-ts-praetor-cult-min","min",1);ensure_constraint(pkg,"r64-ts-praetor-cult-max","max",1)
clean_ts_visibility(pkg,pra_assign,"r64-ts-praetor-package")
add_rule(pkg,"r64-ts-praetor-package-ml","Psyker (Mastery Level 2)",
         "This Thousand Sons Praetor is a Psyker (Mastery Level 2). Select exactly two powers from the Discipline associated with the chosen Prosperine Cult; three if the Mastery Level 3 upgrade is selected.")

mapping=[
    ("Pavoni","Biomancy","biomancy"),
    ("Raptora","Telekinesis","telekinesis"),
    ("Corvidae","Divination","divination"),
    ("Athanaeans","Telepathy","telepathy"),
    ("Pyrae","Pyromancy","pyromancy"),
]
ses=cont(pkg,"selectionEntries",before=("selectionEntryGroups","costs","modifiers"))
for idx,(cult,disc,key) in enumerate(mapping):
    ce=ET.SubElement(ses,C("selectionEntry"),{"id":f"r64-ts-praetor-cult-{key}","name":f"{cult} — {disc}","type":"upgrade","hidden":"false"})
    ensure_constraint(ce,f"r64-ts-praetor-cult-{key}-max","max",1)
    ils=cont(ce,"infoLinks",before=("profiles","rules","selectionEntries","selectionEntryGroups","costs","modifiers"))
    for j,il in enumerate(cult_info.get(cult,[])):
        cp=copy.deepcopy(il); cp.set("id",f"r64-ts-praetor-{key}-cult-info-{j}"); ils.append(cp)
    pg=ET.SubElement(cont(ce,"selectionEntryGroups",before=("costs","modifiers")),C("selectionEntryGroup"),
                     {"id":f"r64-ts-praetor-{key}-powers","name":f"{disc} — Psychic Powers","hidden":"false"})
    mn=ensure_constraint(pg,f"r64-ts-praetor-{key}-min","min",2)
    mx=ensure_constraint(pg,f"r64-ts-praetor-{key}-max","max",2)
    add_conditions_modifier(pg,f"r64-ts-praetor-{key}-ml3-min","set",mn.get("id"),3,[{"childId":"r18-ts-guard-praetor-ml3","scope":"root-entry"}])
    add_conditions_modifier(pg,f"r64-ts-praetor-{key}-ml3-max","set",mx.get("id"),3,[{"childId":"r18-ts-guard-praetor-ml3","scope":"root-entry"}])
    els=cont(pg,"entryLinks",before=("infoLinks","profiles","rules","selectionEntries","selectionEntryGroups","costs","modifiers"))
    for pidx,(pname,target) in enumerate(power_by_disc[key]):
        l=ET.SubElement(els,C("entryLink"),{"id":f"r64-ts-praetor-{key}-power-{pidx}","name":pname,"targetId":target,"type":"selectionEntry","import":"true","hidden":"false"})
        ensure_constraint(l,f"r64-ts-praetor-{key}-power-{pidx}-max","max",1)

add_conditional_info(pra,"r64-ts-praetor-psyker-link","Psyker (Mastery Level 2)",ml2.get("id"),pra_assign,"r18-ts-guard-praetor-ml3")

# ------------------------------------------------------------------
# 3) Veteran melee scaling: true total models, across every live copy.
# ------------------------------------------------------------------
veteran_patches=[]
for e in root.iter(C("selectionEntry")):
    # Find a Legion Veterans model counter under this exact unit.
    vm=next((x for x in e.findall(f"./{C('selectionEntries')}/{C('selectionEntry')}")
             if x.get("type")=="model" and (x.get("name") or "")=="Legion Veterans"),None)
    if vm is None:continue
    mg=next((g for g in e.findall(f"./{C('selectionEntryGroups')}/{C('selectionEntryGroup')}")
             if (g.get("name") or "")=="Close Combat Weapon Replacements"),None)
    if mg is None:continue
    maxs=[x for x in mg.findall(f"./{C('constraints')}/{C('constraint')}") if x.get("type")=="max"]
    if not maxs:continue
    mx=maxs[0]; mx.set("value","1")
    # Remove all legacy arithmetic on this cap, then use 1 Sergeant + N Veterans.
    clear_field_mods(mg,mx.get("id"))
    add_repeat_modifier(mg,(mg.get("id") or "vet-melee")+"-r64-total-models",mx.get("id"),vm.get("id"),1)
    # Individual weapon choices should never be the limiting cap.
    for l in mg.findall(f"./{C('entryLinks')}/{C('entryLink')}"):
        for c in l.findall(f"./{C('constraints')}/{C('constraint')}"):
            if c.get("type")=="max" and float(c.get("value","0"))<10:c.set("value","10")
    veteran_patches.append((e.get("id"),e.get("name"),mg.get("id"),vm.get("id")))

if not any(x[0]=="veteran-unit" for x in veteran_patches):raise RuntimeError("Main Veteran melee group not patched")

# ------------------------------------------------------------------
# 4) Brotherhood Cult-power UI: keep visible and capacity-gate it.
#    This avoids New Recruit failing to redisplay a modifier-hidden group.
# ------------------------------------------------------------------
brotherhood_patches=[]
for e in root.iter(C("selectionEntry")):
    groups=e.findall(f"./{C('selectionEntryGroups')}/{C('selectionEntryGroup')}")
    cult=next((g for g in groups if (g.get("name") or "")=="Prosperine Cult"),None)
    power=next((g for g in groups if (g.get("name") or "").startswith("Psychic Brotherhood — Cult Power")),None)
    if cult is None or power is None:continue

    bids=[]
    for x in e.iter():
        if x.tag not in (C("selectionEntry"),C("entryLink")) or x is e:continue
        n=(x.get("name") or "").lower(); xid=x.get("id") or ""
        if "brotherhood of psykers" in n and "power" not in n and xid not in bids:bids.append(xid)
    if not bids:continue

    power.set("name","Psychic Brotherhood — Cult Power (requires Brotherhood; choose 1)")
    power.set("hidden","false")
    clear_field_mods(power,"hidden")
    mn=ensure_constraint(power,(power.get("id") or "power")+"-r64-min","min",0)
    mx=ensure_constraint(power,(power.get("id") or "power")+"-r64-max","max",0)
    clear_field_mods(power,mn.get("id"));clear_field_mods(power,mx.get("id"))
    for i,bid in enumerate(bids):
        add_conditions_modifier(power,(power.get("id") or "power")+f"-r64-min-{i}","set",mn.get("id"),1,[{"childId":bid,"scope":"root-entry"}])
        add_conditions_modifier(power,(power.get("id") or "power")+f"-r64-max-{i}","set",mx.get("id"),1,[{"childId":bid,"scope":"root-entry"}])

    # Put Cult Power immediately after the Cult selector in XML/UI ordering.
    sgs=e.find(C("selectionEntryGroups"))
    if sgs is not None:
        children=list(sgs); ci=children.index(cult); pi=children.index(power)
        if pi!=ci+1:
            sgs.remove(power); sgs.insert(ci+1,power)
    brotherhood_patches.append((e.get("id"),e.get("name"),bids,power.get("id")))

# ------------------------------------------------------------------
# Revision/index.
# ------------------------------------------------------------------
root.set("revision","64")
tree.write(CAT,encoding="utf-8",xml_declaration=True)
ET.register_namespace("",INS)
it=ET.parse(IDX);ir=it.getroot()
for x in ir.iter(I("dataIndexEntry")):
    if x.get("filePath")=="Legiones Astartes.cat":x.set("dataRevision","64")
it.write(IDX,encoding="utf-8",xml_declaration=True)

# ------------------------------------------------------------------
# Validation.
# ------------------------------------------------------------------
rr=ET.parse(CAT).getroot(); rids={x.get("id"):x for x in rr.iter() if x.get("id")}; checks=[]
def ck(n,o):
    checks.append((n,bool(o)))
    if not o:raise RuntimeError("R64 validation failed: "+n)

ck("CAT64",rr.get("revision")=="64")
ck("GST dependency remains 15",rr.get("gameSystemRevision")=="15")
ck("Index64",'dataRevision="64"' in IDX.read_text(encoding="utf-8"))
ck("Centurion ML1 shared rule exists","r64-ts-psyker-ml1" in rids)
ck("Praetor ML2 shared rule exists","r64-ts-psyker-ml2" in rids)
ck("Centurion conditional ML1 link exists","r64-ts-centurion-psyker-link" in rids)
ck("Praetor conditional ML2 link exists","r64-ts-praetor-psyker-link" in rids)

cp=rids["r57-ts-centurion-psychic-package"]
ck("Centurion package five Cults",len(cp.findall(f"./{C('selectionEntries')}/{C('selectionEntry')}"))==5)
for ce in cp.findall(f"./{C('selectionEntries')}/{C('selectionEntry')}"):
    pgs=ce.findall(f"./{C('selectionEntryGroups')}/{C('selectionEntryGroup')}")
    ck("Centurion "+ce.get("name")+" has powers",len(pgs)==1 and len(pgs[0].findall(f"./{C('entryLinks')}/{C('entryLink')}"))>=5)

pp=rids["r64-ts-praetor-psychic-package"]
ck("Praetor package five Cults",len(pp.findall(f"./{C('selectionEntries')}/{C('selectionEntry')}"))==5)
for ce in pp.findall(f"./{C('selectionEntries')}/{C('selectionEntry')}"):
    pg=ce.find(f"./{C('selectionEntryGroups')}/{C('selectionEntryGroup')}")
    ck("Praetor "+ce.get("name")+" has 7 powers",pg is not None and len(pg.findall(f"./{C('entryLinks')}/{C('entryLink')}"))==7)
    vals=[(x.get("type"),x.get("value")) for x in pg.findall(f"./{C('constraints')}/{C('constraint')}")]
    ck("Praetor "+ce.get("name")+" base ML2 knows two",("min","2") in vals and ("max","2") in vals)
    ck("Praetor "+ce.get("name")+" ML3 supported","r18-ts-guard-praetor-ml3" in ET.tostring(pg,encoding="unicode"))

for old in ["r45-cult-hq-praetor","r19-ts-praetor-disciplines","r19-ts-praetor-powers"]:
    ck(old+" removed",old not in rids)

main_v=next(x for x in veteran_patches if x[0]=="veteran-unit")
mg=rids[main_v[2]]
mx=next(x for x in mg.findall(f"./{C('constraints')}/{C('constraint')}") if x.get("type")=="max")
ck("Veteran melee base cap is Sergeant",mx.get("value")=="1")
mtxt=ET.tostring(mg,encoding="unicode")
ck("Veteran melee scales from selected Veterans",main_v[3] in mtxt and "<" in mtxt)
ck("Veteran melee patched across copies",len(veteran_patches)>=2)

ck("Brotherhood power roots retained",len(brotherhood_patches)>=5)
for eid,name,bids,pid in brotherhood_patches:
    pg=rids[pid]; vals=[(x.get("type"),x.get("value")) for x in pg.findall(f"./{C('constraints')}/{C('constraint')}")]
    ck(name+" power group visible",pg.get("hidden")=="false")
    ck(name+" power group locked without Brotherhood",("max","0") in vals)
    txt=ET.tostring(pg,encoding="unicode")
    ck(name+" Brotherhood unlock wired",all(b in txt for b in bids))

new=collections.Counter(x.get("id") for x in rr.iter() if x.get("id"))
worse={k:v for k,v in new.items() if v>max(1,baseline.get(k,0))}
ck("No new/worsened duplicate IDs",not worse)

OUT.write_text("\n".join([
"Live R64 — Thousand Sons core psychic + Veteran scaling repair",
"Input CAT63/GST15 -> CAT64/GST15","",
"GENERIC THOUSAND SONS CHARACTERS:",
"- Legion Centurion/Consuls now display an explicit conditional Psyker (Mastery Level 1) rule.",
"- The existing Centurion Cult -> correlated-power package was hardened and kept: one Cult, one power; Librarian Epistolary two powers.",
"- Legion Praetor now displays an explicit conditional Psyker (Mastery Level 2) rule.",
"- Replaced the broken old Praetor Cult -> Discipline -> Power chain (which referenced obsolete pre-R59 Cult IDs) with one direct package.",
"- Praetor chooses one Cult and exactly two powers from its correlated Discipline.",
"- Guard of the Crimson King Mastery Level 3 upgrade raises the same Cult-correlated power allowance to three.",
"- Both character packages work for a normal XV Legion roster and for a Shattered Legions character assigned to the XV Legion.","",
"VETERANS:",
f"- Replaced legacy fixed/set melee caps on {len(veteran_patches)} live Veteran roots with a real model-count formula: 1 Sergeant + selected Legion Veterans.",
"- Main Veteran squad therefore allows 5 melee replacements at 5 models and 10 at 10 models; individual weapon links no longer impose the lower cap.","",
"PSYCHIC BROTHERHOODS:",
f"- Hardened {len(brotherhood_patches)} Brotherhood-capable Veteran/Terminator roots.",
"- Cult Power groups are no longer visibility-dependent on New Recruit recalculating a hidden group.",
"- The group stays visible beside the Cult selector but has max 0 until Brotherhood of Psykers is selected; Brotherhood then sets min/max to exactly 1.",
"- Existing R63 Cult gating remains: Pavoni->Biomancy, Raptora->Telekinesis, Corvidae->Divination, Athanaeans->Telepathy, Pyrae->Pyromancy.","",
"VALIDATION:"
]+[f'- {"PASS" if ok else "FAIL"}: {n}' for n,ok in checks])+"\n",encoding="utf-8")
print(OUT.read_text())
