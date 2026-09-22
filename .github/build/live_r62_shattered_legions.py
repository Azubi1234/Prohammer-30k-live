from pathlib import Path
import copy, collections, hashlib, re, xml.etree.ElementTree as ET

CAT=Path("Legiones Astartes.cat"); GST=Path("Prohammer 30k.gst"); IDX=Path("index.xml")
OUT=Path("inspection-live-r62-shattered-legions.txt")
CNS="http://www.battlescribe.net/schema/catalogueSchema"
GNS="http://www.battlescribe.net/schema/gameSystemSchema"
INS="http://www.battlescribe.net/schema/dataIndexSchema"
ET.register_namespace("",CNS)
C=lambda t:f"{{{CNS}}}{t}"; G=lambda t:f"{{{GNS}}}{t}"; I=lambda t:f"{{{INS}}}{t}"

ct=ET.parse(CAT); cr=ct.getroot(); gt=ET.parse(GST); gr=gt.getroot()
if cr.get("revision")!="61": raise RuntimeError(f"R62 expected CAT61, got {cr.get('revision')}")
if gr.get("revision")!="14": raise RuntimeError(f"R62 expected GST14, got {gr.get('revision')}")
baseline_ids=collections.Counter(x.get("id") for x in cr.iter() if x.get("id"))

def qns(e): return e.tag.split("}")[0].strip("{")
def T(e,tag): return f"{{{qns(e)}}}{tag}"
def cont(p,tag,before=("constraints","categoryLinks","entryLinks","infoLinks","profiles","rules","selectionEntries","selectionEntryGroups","costs","modifiers")):
    q=T(p,tag); x=p.find(q)
    if x is not None:return x
    x=ET.Element(q); kids=list(p); idx=len(kids)
    for j,k in enumerate(kids):
        if k.tag.split("}")[-1] in before: idx=j; break
    p.insert(idx,x); return x
def cons(p,id_,typ,val,field="selections",scope="parent",child=False):
    cs=cont(p,"constraints"); q=T(p,"constraint")
    x=next((z for z in cs.findall(q) if z.get("id")==id_),None)
    if x is None:x=ET.SubElement(cs,q)
    x.attrib.update({"id":id_,"type":typ,"value":str(val),"field":field,"scope":scope,
                     "shared":"true","includeChildSelections":"true" if child else "false","includeChildForces":"false"})
    return x
def modifier(p,id_,typ,field,value,conds=None,groups=None):
    ms=cont(p,"modifiers"); q=T(p,"modifier")
    x=ET.SubElement(ms,q,{"id":id_,"type":typ,"field":field,"value":str(value)})
    if groups:
        cgs=ET.SubElement(x,T(x,"conditionGroups"))
        for gtype,arr in groups:
            cg=ET.SubElement(cgs,T(x,"conditionGroup"),{"type":gtype})
            cs=ET.SubElement(cg,T(x,"conditions"))
            for c in arr:ET.SubElement(cs,T(x,"condition"),c)
    elif conds:
        cs=ET.SubElement(x,T(x,"conditions"))
        for c in conds:ET.SubElement(cs,T(x,"condition"),c)
    return x
def cond(kind,val,child,scope="roster",include=True):
    return {"type":kind,"value":str(val),"field":"selections","scope":scope,"childId":child,
            "shared":"true","includeChildSelections":"true" if include else "false","includeChildForces":"false"}
def add_rule(p,id_,name,text):
    rs=cont(p,"rules"); q=T(p,"rule")
    r=ET.SubElement(rs,q,{"id":id_,"name":name,"hidden":"false"})
    d=ET.SubElement(r,T(r,"description"));d.text=text;return r
def info_link(p,id_,name,target,typ="rule",hidden=False):
    ils=cont(p,"infoLinks"); q=T(p,"infoLink")
    x=ET.SubElement(ils,q,{"id":id_,"name":name,"targetId":target,"type":typ,"hidden":"true" if hidden else "false"});return x
def group(p,id_,name,minv=None,maxv=None,hidden=False):
    gs=cont(p,"selectionEntryGroups",before=("costs","modifiers"));q=T(p,"selectionEntryGroup")
    g=ET.SubElement(gs,q,{"id":id_,"name":name,"hidden":"true" if hidden else "false"})
    if minv is not None:cons(g,id_+"-min","min",minv)
    if maxv is not None:cons(g,id_+"-max","max",maxv)
    return g
def sel(p,id_,name,hidden=False,default=None):
    ss=cont(p,"selectionEntries",before=("selectionEntryGroups","costs","modifiers"));q=T(p,"selectionEntry")
    e=ET.SubElement(ss,q,{"id":id_,"name":name,"type":"upgrade","hidden":"true" if hidden else "false"})
    if default is not None:e.set("defaultAmount",str(default))
    cons(e,id_+"-max","max",1)
    return e
def catlink(p,id_,name,target,primary=False):
    cs=cont(p,"categoryLinks");q=T(p,"categoryLink")
    x=ET.SubElement(cs,q,{"id":id_,"name":name,"targetId":target,"hidden":"false"})
    if primary:x.set("primary","true")
    return x
def primary_cat(e):
    for c in e.findall(f"./{C('categoryLinks')}/{C('categoryLink')}"):
        if c.get("primary")=="true":return c.get("targetId")
    return None
def direct_rule_names(e):
    return [(x.get("name") or "") for x in e.findall(f"./{C('rules')}/{C('rule')}")]+[(x.get("name") or "") for x in e.findall(f"./{C('infoLinks')}/{C('infoLink')}")]
def fixed_legion_name(e):
    for n in direct_rule_names(e):
        m=re.match(r"Legiones Astartes \((.+)\)",n)
        if m:return m.group(1)
    return None
def h(s):return hashlib.sha1(s.encode()).hexdigest()[:12]
def norm(s):return re.sub(r"[^a-z0-9]+"," ",(s or "").casefold()).strip()

# ----------------------------------------------------------------------
# Legion/config discovery.
# ----------------------------------------------------------------------
ids={x.get("id"):x for x in cr.iter() if x.get("id")}
cfg=ids.get("config-legion")
if cfg is None or cfg.tag!=C("selectionEntryGroup"):raise RuntimeError("config-legion group missing")
cfg_ss=cfg.find(C("selectionEntries"))
if cfg_ss is None:raise RuntimeError("config-legion has no selectionEntries")

legions=[]
for e in cfg_ss.findall(C("selectionEntry")):
    eid=e.get("id") or ""
    if not eid.startswith("legion-"):continue
    m=re.match(r"^([IVXLCDM]+)\s+Legion\s+[—-]\s+(.+)$",e.get("name") or "",re.I)
    if not m:continue
    roman=m.group(1).lower(); lname=m.group(2).strip()
    legions.append((roman,eid,lname,e))
if len(legions)!=18:raise RuntimeError(f"Expected 18 playable Legions, found {[(x[1],x[2]) for x in legions]}")
legion_ids={eid for _,eid,_,_ in legions}
legion_by_roman={roman:(eid,lname,e) for roman,eid,lname,e in legions}
legion_name_to_id={lname.casefold():eid for _,eid,lname,_ in legions}

THEME="r62-shattered-theme"
if THEME in ids:raise RuntimeError("R62 Shattered theme already exists")

# ----------------------------------------------------------------------
# Shattered Theme -> 2-3 constituent Legions -> one Warlord's Legion.
# ----------------------------------------------------------------------
theme=ET.SubElement(cfg_ss,C("selectionEntry"),{
    "id":THEME,"name":"Shattered Legions Theme","type":"upgrade","hidden":"false"
})
cons(theme,THEME+"-max","max",1)
add_rule(theme,THEME+"-rule","Shattered Legions",
"""A Shattered Legions force uses the Legiones Astartes Army List but is composed of warriors from two or three different Legions. Select two or three Constituent Legions below and nominate one of them as the Warlord's Legion. Every generic unit must then be assigned to exactly one selected Legion. A unit retains the normal special rules and eligible Legion-specific wargear of its assigned Legion. Models from different Legions may not be mixed in the same unit. Dedicated Transports inherit the Legion of the unit that purchased them. Legion-specific units are 0–1 per entry and require a Praetor, Centurion or named HQ Character from the same Legion. Primarchs and Blackshields are prohibited. If the Warlord is slain, only units from the Warlord's Legion remain Scoring.""")
add_rule(theme,THEME+"-alliance","Shattered Allegiance",
"""The force uses the single Loyalist/Traitor Allegiance selected for the roster. Characters and units retain their normal allegiance restrictions. An Independent Character may join a unit from another selected Legion, but neither model nor unit gains the other's Legion-specific rules, wargear or abilities.""")
add_rule(theme,THEME+"-rites","Rites of War",
"""Shattered Legions does not itself grant permission to use a Legion-specific Rite of War. The normal generic Rites remain available. Legion-specific Rites remain unavailable unless a later project rule explicitly permits them.""")

cg=group(theme,"r62-shattered-constituents","Constituent Legions — choose 2–3",2,3)
wg=group(theme,"r62-shattered-warlord","Warlord's Legion — choose 1",1,1)

const_ids={}; warlord_ids={}
for roman,eid,lname,leg in legions:
    cid=f"r62-shat-const-{roman}"; wid=f"r62-shat-warlord-{roman}"
    c=sel(cg,cid,lname); const_ids[eid]=cid
    add_rule(c,cid+"-rule","Constituent Legion",f"{lname} is one of the Legions represented in this Shattered Legions force.")
    w=sel(wg,wid,lname,hidden=False); warlord_ids[eid]=wid
    # Warlord option only legal for an actually selected constituent Legion.
    modifier(w,wid+"-hide-not-const","set","hidden","true",[cond("lessThan",1,cid)])
    add_rule(w,wid+"-rule","Warlord's Legion",f"The army's Warlord must belong to {lname}. If the Warlord is slain, only {lname} units remain Scoring for the rest of the battle.")

# Alpha Legion's army-level Mutable Tactic is still one shared choice if XX is represented.
alpha=next((e for r,eid,n,e in legions if eid=="legion-xx"),None)
if alpha is not None:
    src=next((g for g in alpha.findall(f"./{C('selectionEntryGroups')}/{C('selectionEntryGroup')}") if "Mutable Tactic" in (g.get("name") or "")),None)
    if src is not None:
        cp=copy.deepcopy(src)
        # remap all local IDs so this is a separate Shattered-level selector.
        oldids=[x.get("id") for x in cp.iter() if x.get("id")]
        mp={o:"r62-shat-alpha-"+h(o) for o in oldids}
        for x in cp.iter():
            if x.get("id") in mp:x.set("id",mp[x.get("id")])
            for a in ("field","childId"):
                if x.get(a) in mp:x.set(a,mp[x.get(a)])
        cp.set("id","r62-shat-alpha-mutable");cp.set("name","Alpha Legion — Mutable Tactic (choose 1)")
        cp.set("hidden","false")
        # Strip old visibility mods and hide only when Alpha Legion is not a constituent.
        ms=cp.find(C("modifiers"))
        if ms is not None:cp.remove(ms)
        modifier(cp,"r62-shat-alpha-mutable-hide","set","hidden","true",[cond("lessThan",1,const_ids["legion-xx"])])
        theme_groups=cont(theme,"selectionEntryGroups",before=("costs","modifiers"))
        theme_groups.append(cp)

# ----------------------------------------------------------------------
# Generic units: add exact one Assigned Legion in Shattered mode.
# ----------------------------------------------------------------------
top_container=cr.find(C("selectionEntries"))
if top_container is None:raise RuntimeError("catalogue root selectionEntries missing")
top_roots=list(top_container.findall(C("selectionEntry")))

# Exclude fixed-Legion roots and configuration/Reward entries. Every other
# selectable model/unit in the Legiones catalogue is assignable.
generic_roots=[]
fixed_top=[]
for e in top_roots:
    if e.get("type") not in ("unit","model"):continue
    fl=fixed_legion_name(e)
    if fl:
        fixed_top.append(e);continue
    eid=e.get("id") or ""; n=(e.get("name") or "")
    if eid.startswith("r46-al-reward-") or "Rewards of Treachery" in n:continue
    generic_roots.append(e)

assignment_ids={}
assignment_groups=0
for e in generic_roots:
    rid=e.get("id") or ""
    gid="r62-shat-assign-group-"+h(rid)
    g=group(e,gid,"Shattered Legions — Assigned Legion",0,1,hidden=False)
    modifier(g,gid+"-hide","set","hidden","true",[cond("lessThan",1,THEME)])
    mn=next(x for x in g.findall(f"./{C('constraints')}/{C('constraint')}") if x.get("type")=="min")
    modifier(g,gid+"-min-on","set",mn.get("id"),1,[cond("atLeast",1,THEME)])
    for roman,legid,lname,leg in legions:
        aid="r62-shat-assign-"+h(rid+"|"+legid)
        a=sel(g,aid,lname,hidden=False); assignment_ids[(rid,legid)]=aid
        modifier(a,aid+"-hide-not-const","set","hidden","true",[cond("lessThan",1,const_ids[legid])])
        add_rule(a,aid+"-identity",f"Legiones Astartes ({lname})",
                 f"This unit is assigned to {lname} for the Shattered Legions Theme. It uses the normal {lname} Legion rules and may purchase Legion-specific wargear/options which would normally be legal for this unit or its models. Rules belonging to another constituent Legion do not apply.")
        # Reuse canonical shared rule links already present on the Legion selector.
        seen=set()
        for il in leg.findall(f"./{C('infoLinks')}/{C('infoLink')}"):
            if il.get("type")!="rule" or not il.get("targetId"):continue
            key=il.get("targetId")
            if key in seen:continue
            seen.add(key)
            info_link(a,aid+"-info-"+h(key),il.get("name") or lname,key,"rule")
    assignment_groups+=1

# ----------------------------------------------------------------------
# Modifier localisation:
# Existing Legion-specific options assume one roster-wide Legion selection.
# In Shattered mode, clone those effects using the unit's local Assigned Legion.
# Negative "hide if Legion absent" modifiers are disabled in Shattered mode and
# replaced by "hide if this unit is not assigned that Legion".
# ----------------------------------------------------------------------
def condition_parent_map(m):
    return {c:p for p in m.iter() for c in p}
def condition_containers_with_legion(m):
    pm=condition_parent_map(m); out=[]
    for c in m.iter(T(m,"condition")):
        if c.get("childId") in legion_ids:
            p=pm.get(c)
            if p is not None and p.tag==T(m,"conditions"):out.append((c,p))
    return out
def append_cond(container,c):
    # Avoid duplicate identical theme gates.
    for x in container.findall(T(container,"condition")):
        if x.get("childId")==c["childId"] and x.get("type")==c["type"] and x.get("value")==c["value"]:return
    ET.SubElement(container,T(container,"condition"),c)
def clone_modifier_for_assignment(m,root_id):
    hits=condition_containers_with_legion(m)
    if not hits:return None
    cp=copy.deepcopy(m); cp.set("id",(m.get("id") or "mod")+"-r62-shat-"+h(root_id+(m.get("id") or "")+str(generic_mod_clones)))
    for c in cp.iter(T(cp,"condition")):
        leg=c.get("childId")
        if leg in legion_ids:
            aid=assignment_ids.get((root_id,leg))
            if aid is None:return None
            c.set("childId",aid);c.set("scope","root-entry")
    # Require Shattered mode in every logical condition block touched by a Legion condition.
    pm=condition_parent_map(cp)
    touched=[]
    for c in cp.iter(T(cp,"condition")):
        if c.get("childId") in [assignment_ids.get((root_id,l)) for l in legion_ids]:
            p=pm.get(c)
            if p is not None and p not in touched:touched.append(p)
    for p in touched:append_cond(p,cond("atLeast",1,THEME))
    return cp

generic_mod_clones=0; generic_negative_gates=0; unsupported_negative=0
for e in generic_roots:
    rid=e.get("id") or ""
    # Snapshot because we append cloned modifiers during traversal.
    mods=[m for m in e.iter(C("modifier")) if not (m.get("id") or "").startswith("r62-")]
    for m in mods:
        hits=condition_containers_with_legion(m)
        if not hits:continue
        negative=any(c.get("type")=="lessThan" and c.get("value")=="1" for c,_ in hits)
        cp=clone_modifier_for_assignment(m,rid)
        if cp is not None:
            parent=next((p for p in e.iter() if m in list(p)),None)
            if parent is not None:
                parent.append(cp);generic_mod_clones+=1
        if negative:
            # Stop the old roster-wide "missing Legion" modifier from firing while
            # Shattered is selected. Conditions containers are AND blocks in the
            # catalogue patterns used for these gates.
            containers=[]
            for c,p in hits:
                if c.get("type")=="lessThan" and c.get("value")=="1" and p not in containers:containers.append(p)
            if not containers:
                unsupported_negative+=1;continue
            for p in containers:
                append_cond(p,cond("lessThan",1,THEME))
                generic_negative_gates+=1

# ----------------------------------------------------------------------
# Fixed Legion-specific roots/copies: constituent selection substitutes for the
# normal single-Legion selector. Primarchs are prohibited.
# ----------------------------------------------------------------------
# Detect canonical r41 Legion entries, plus fixed-Legion role copies will be
# patched by their own direct Legion identity.
def legion_id_from_fixed_name(name):
    return legion_name_to_id.get((name or "").casefold())
def is_primarch(e):
    return any((n or "").casefold()=="primarch" for n in direct_rule_names(e)) or "primarch" in " ".join(direct_rule_names(e)).casefold()

fixed_entries=[]
for e in cr.iter(C("selectionEntry")):
    if e.get("type") not in ("unit","model"):continue
    fl=fixed_legion_name(e)
    lid=legion_id_from_fixed_name(fl)
    if lid:fixed_entries.append((e,lid))

fixed_mod_clones=0; fixed_negative_gates=0
for e,lid in fixed_entries:
    # Skip the ordinary Legion config entries themselves (they are upgrades anyway).
    const=const_ids[lid]
    mods=[m for m in e.iter(C("modifier")) if not (m.get("id") or "").startswith("r62-")]
    for m in mods:
        hits=condition_containers_with_legion(m)
        own=[(c,p) for c,p in hits if c.get("childId")==lid]
        if not own:continue
        cp=copy.deepcopy(m);cp.set("id",(m.get("id") or "mod")+"-r62-fixed-"+h((e.get("id") or "")+(m.get("id") or "")+str(fixed_mod_clones)))
        for c in cp.iter(T(cp,"condition")):
            if c.get("childId")==lid:
                c.set("childId",const);c.set("scope","roster")
        pm=condition_parent_map(cp);touched=[]
        for c in cp.iter(T(cp,"condition")):
            if c.get("childId")==const:
                p=pm.get(c)
                if p is not None and p not in touched:touched.append(p)
        for p in touched:append_cond(p,cond("atLeast",1,THEME))
        parent=next((p for p in e.iter() if m in list(p)),None)
        if parent is not None:parent.append(cp);fixed_mod_clones+=1
        if any(c.get("type")=="lessThan" and c.get("value")=="1" for c,_ in own):
            for c,p in own:
                if c.get("type")=="lessThan" and c.get("value")=="1":
                    append_cond(p,cond("lessThan",1,THEME));fixed_negative_gates+=1
    # Explicit constituent guard catches roots with no old Legion visibility modifier.
    modifier(e,"r62-fixed-hide-const-"+h(e.get("id") or ""), "set","hidden","true",
             groups=[("and",[cond("atLeast",1,THEME),cond("lessThan",1,const)])])
    if is_primarch(e):
        modifier(e,"r62-shat-no-primarch-"+h(e.get("id") or ""),"set","hidden","true",[cond("atLeast",1,THEME)])

# ----------------------------------------------------------------------
# Same-Legion HQ requirement for Legion-specific non-HQ units.
# Qualifying generic commanders: Praetor or Centurion assigned to that Legion.
# Qualifying fixed commanders: a non-Primarch Legion-specific HQ entry.
# ----------------------------------------------------------------------
hq_candidates={lid:[] for lid in legion_ids}
for rid in ("hq-praetor","hq-centurion"):
    if rid in ids:
        for lid in legion_ids:
            aid=assignment_ids.get((rid,lid))
            if aid:hq_candidates[lid].append(aid)
for e,lid in fixed_entries:
    if primary_cat(e)=="cat-hq" and not is_primarch(e):
        if e.get("id") not in hq_candidates[lid]:hq_candidates[lid].append(e.get("id"))

hq_requirements=0
for e,lid in fixed_entries:
    if is_primarch(e) or primary_cat(e)=="cat-hq":continue
    # Rewards copies are Alpha Legion constructs, not constituent-Legion special units.
    if (e.get("id") or "").startswith("r46-al-reward-"):continue
    candidates=hq_candidates[lid]
    if not candidates:continue
    arr=[cond("atLeast",1,THEME)]+[cond("lessThan",1,x) for x in candidates]
    modifier(e,"r62-shat-hqreq-"+h(e.get("id") or ""),"set","hidden","true",groups=[("and",arr)])
    hq_requirements+=1

# ----------------------------------------------------------------------
# Shared 0-1 categories for each canonical Legion-specific entry.
# This also catches retinue/FOC copies with the same base unit name.
# ----------------------------------------------------------------------
force=next((x for x in gr.iter(G("forceEntry")) if x.get("id")=="force-standard"),None)
if force is None:raise RuntimeError("force-standard missing")
gce=gr.find(G("categoryEntries"))
if gce is None:gce=ET.SubElement(gr,G("categoryEntries"))
fcl=cont(force,"categoryLinks")

canonical_special=[]
for e in top_roots:
    if e.get("type") not in ("unit","model"):continue
    fl=fixed_legion_name(e); lid=legion_id_from_fixed_name(fl)
    if not lid:continue
    if (e.get("id") or "").startswith("r46-al-reward-"):continue
    # Rite/role copies are not new Legion-specific entries; prefer r41 canonical
    # roots or fixed roots whose name does not advertise a shifted role.
    eid=e.get("id") or ""; n=e.get("name") or ""
    if eid.startswith("r41-unit-"):
        canonical_special.append((e,lid))
    elif not any(k in n for k in [" — Troops"," — Retinue"," — Rewards of Treachery"," — Covenant"," — Horror"," — Terror Assault"," — Long March"," — First Company"]):
        # Covers older Dark Angels-style canonical roots if present.
        canonical_special.append((e,lid))

# dedupe by exact legion + exact display name
canon_map={}
for e,lid in canonical_special:canon_map.setdefault((lid,e.get("name") or ""),e)
canonical_special=[(e,lid) for (lid,n),e in canon_map.items()]

limit_categories=0;limit_links=0
for e,lid in canonical_special:
    name=e.get("name") or ""; key=lid+"|"+name
    cid="r62-shat-limit-"+h(key)
    ce=ET.SubElement(gce,G("categoryEntry"),{"id":cid,"name":"Shattered 0–1 — "+name,"hidden":"true"})
    fl=ET.SubElement(fcl,G("categoryLink"),{"id":"r62-force-"+h(key),"name":"Shattered 0–1 — "+name,"targetId":cid,"hidden":"true"})
    mx=cons(fl,"r62-force-max-"+h(key),"max",99,"selections","parent",True)
    modifier(fl,"r62-force-limit-"+h(key),"set",mx.get("id"),1,[cond("atLeast",1,THEME)])
    limit_categories+=1
    base=norm(name)
    for x in cr.iter(C("selectionEntry")):
        xn=norm(x.get("name") or "")
        if not (xn==base or xn.startswith(base+" retinue") or xn.startswith(base+" covenant") or xn.startswith(base+" troops") or xn.startswith(base+" first company") or xn.startswith(base+" long march")):
            continue
        # Do not count Rewards of Treachery as the original Legion's entry.
        if (x.get("id") or "").startswith("r46-al-reward-"):continue
        catlink(x,"r62-limit-link-"+h((x.get("id") or "")+cid),"Shattered 0–1 — "+name,cid)
        limit_links+=1

# ----------------------------------------------------------------------
# Revision/index.
# ----------------------------------------------------------------------
cr.set("revision","62");cr.set("gameSystemRevision","15");gr.set("revision","15")
ct.write(CAT,encoding="utf-8",xml_declaration=True)
ET.register_namespace("",GNS);gt.write(GST,encoding="utf-8",xml_declaration=True)
ET.register_namespace("",INS);it=ET.parse(IDX);ir=it.getroot()
for x in ir.iter(I("dataIndexEntry")):
    if x.get("filePath")=="Legiones Astartes.cat":x.set("dataRevision","62")
    if x.get("filePath")=="Prohammer 30k.gst":x.set("dataRevision","15")
it.write(IDX,encoding="utf-8",xml_declaration=True)

# ----------------------------------------------------------------------
# Validation.
# ----------------------------------------------------------------------
rr=ET.parse(CAT).getroot();gg=ET.parse(GST).getroot()
rids={x.get("id"):x for x in rr.iter() if x.get("id")};gids={x.get("id"):x for x in gg.iter() if x.get("id")}
checks=[]
def ck(n,o):
    checks.append((n,bool(o)))
    if not o:raise RuntimeError("R62 validation failed: "+n)
ck("CAT62",rr.get("revision")=="62")
ck("GST15",gg.get("revision")=="15")
ck("CAT points GST15",rr.get("gameSystemRevision")=="15")
idx=IDX.read_text(encoding="utf-8");ck("Index62/15",'dataRevision="62"' in idx and 'dataRevision="15"' in idx)
ck("Shattered theme exists",THEME in rids)
th=rids[THEME]
const=next(g for g in th.findall(f"./{C('selectionEntryGroups')}/{C('selectionEntryGroup')}") if g.get("id")=="r62-shattered-constituents")
war=next(g for g in th.findall(f"./{C('selectionEntryGroups')}/{C('selectionEntryGroup')}") if g.get("id")=="r62-shattered-warlord")
ck("18 constituent choices",len(const.findall(f"./{C('selectionEntries')}/{C('selectionEntry')}"))==18)
ck("18 Warlord Legion choices",len(war.findall(f"./{C('selectionEntries')}/{C('selectionEntry')}"))==18)
ck("Constituent min2/max3",any(x.get("type")=="min" and x.get("value")=="2" for x in const.findall(f"./{C('constraints')}/{C('constraint')}")) and any(x.get("type")=="max" and x.get("value")=="3" for x in const.findall(f"./{C('constraints')}/{C('constraint')}")))
ck("Warlord Legion min1/max1",any(x.get("type")=="min" and x.get("value")=="1" for x in war.findall(f"./{C('constraints')}/{C('constraint')}")) and any(x.get("type")=="max" and x.get("value")=="1" for x in war.findall(f"./{C('constraints')}/{C('constraint')}")))
ck("Generic assignment groups added",assignment_groups>20)
for rid in ["hq-praetor","hq-centurion","tactical-unit","veteran-unit","terminator-unit"]:
    if rid in rids:
        gs=[g for g in rids[rid].findall(f"./{C('selectionEntryGroups')}/{C('selectionEntryGroup')}") if (g.get("name") or "")=="Shattered Legions — Assigned Legion"]
        ck(rid+" assignment selector",len(gs)==1 and len(gs[0].findall(f"./{C('selectionEntries')}/{C('selectionEntry')}"))==18)
# Primarchs all explicitly blocked in Shattered.
prim=[e for e in rr.iter(C("selectionEntry")) if e.get("type") in ("unit","model") and is_primarch(e)]
ck("Primarchs detected",len(prim)>0)
ck("All Primarchs blocked",all(THEME in ET.tostring(e,encoding="unicode") for e in prim))
ck("Special 0-1 categories created",limit_categories>20 and limit_links>=limit_categories)
ck("Same-Legion HQ requirements added",hq_requirements>20)

new=collections.Counter(x.get("id") for x in rr.iter() if x.get("id"))
worse={k:v for k,v in new.items() if v>max(1,baseline_ids.get(k,0))}
if worse:print("R62_DUPLICATES",list(worse.items())[:100])
ck("No new/worsened duplicate IDs",not worse)

OUT.write_text("\n".join([
"Live R62 — Shattered Legions Theme",
"Input CAT61/GST14 -> CAT62/GST15","",
"CONFIGURATION:",
"- Added Shattered Legions Theme as an alternative to selecting one normal Legion.",
"- Exactly 2–3 of the 18 playable Legions must be selected as Constituent Legions.",
"- Exactly one selected constituent Legion must be nominated as the Warlord's Legion.",
"- The existing single Loyalist/Traitor Allegiance selection remains authoritative.",
"- Legion-specific Rites are not unlocked merely by selecting a constituent Legion; generic Rites remain available.",
"- If Alpha Legion is selected, the Theme exposes one shared Alpha Legion Mutable Tactic selector rather than one per unit.","",
"UNIT ASSIGNMENT:",
f"- Added {assignment_groups} Shattered 'Assigned Legion' selectors to generic top-level units/models.",
"- In Shattered mode each such unit must select exactly one Legion, and only selected constituent Legions are shown.",
"- The assignment choice reuses canonical shared Legion rule references where available.",
"- Existing Legion-specific options/wargear visibility was localised to the unit's Assigned Legion instead of becoming roster-wide.",
f"- Created {generic_mod_clones} local-assignment modifier clones and protected {generic_negative_gates} old negative Legion gates from firing in Shattered mode.","",
"LEGION-SPECIFIC UNITS:",
f"- Patched {len(fixed_entries)} fixed-Legion unit/copy entries so a selected constituent Legion can unlock its own entries without selecting the normal one-Legion config.",
f"- Added {hq_requirements} same-Legion HQ requirements to non-HQ Legion-specific entries.",
f"- Created {limit_categories} shared conditional 0–1 categories with {limit_links} linked unit/copy instances.",
"- Primarchs are explicitly hidden in Shattered Legions.",
"- Rewards of Treachery copies are not treated as the original Legion's special-unit entry.","",
"DEDICATED TRANSPORTS:",
"- No separate Legion selection is added to nested Dedicated Transports; their Legion is inherited from the purchasing unit, and local Legion option gates can read the parent root assignment.","",
"KNOWN BUILDER BOUNDARY:",
"- The Warlord's Legion choice is mechanically restricted to a selected constituent Legion. The battlefield consequence of the Warlord being slain remains rules text because New Recruit cannot know in-game casualty state.",
"- A later Blackshields implementation will explicitly hide Blackshield choices while Shattered Legions is selected.","",
"VALIDATION:"
]+[f'- {"PASS" if ok else "FAIL"}: {n}' for n,ok in checks])+"\n",encoding="utf-8")
print(OUT.read_text())
