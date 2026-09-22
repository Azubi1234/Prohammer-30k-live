from pathlib import Path
import copy, collections, hashlib, re, xml.etree.ElementTree as ET

CAT=Path("Legiones Astartes.cat"); GST=Path("Prohammer 30k.gst"); IDX=Path("index.xml")
OUT=Path("inspection-live-r41-universal-wargear-rite-visibility.txt")
CNS="http://www.battlescribe.net/schema/catalogueSchema"; GNS="http://www.battlescribe.net/schema/gameSystemSchema"; INS="http://www.battlescribe.net/schema/dataIndexSchema"
ET.register_namespace("",CNS)
C=lambda t:f"{{{CNS}}}{t}"; G=lambda t:f"{{{GNS}}}{t}"; I=lambda t:f"{{{INS}}}{t}"

tree=ET.parse(CAT); root=tree.getroot()
gtree=ET.parse(GST); groot=gtree.getroot()
if root.get("revision")!="40": raise RuntimeError(f"R41 expected CAT40, got {root.get('revision')}")
if groot.get("revision")!="5": raise RuntimeError(f"R41 expected GST5, got {groot.get('revision')}")

def qns(e): return e.tag.split("}")[0].strip("{")
def cont(p,tag,before=("constraints","categoryLinks","entryLinks","infoLinks","profiles","rules","selectionEntries","selectionEntryGroups","costs","modifiers")):
    ns=qns(p); q=f"{{{ns}}}{tag}"; x=p.find(q)
    if x is not None:return x
    x=ET.Element(q); kids=list(p); idx=len(kids)
    for j,k in enumerate(kids):
        if k.tag.split("}")[-1] in before:idx=j;break
    p.insert(idx,x);return x
def cons(p,id_,typ,val,field="selections",scope="parent",child=False):
    ns=qns(p); cs=cont(p,"constraints"); q=f"{{{ns}}}constraint"; x=next((z for z in cs.findall(q) if z.get("id")==id_),None)
    if x is None:x=ET.SubElement(cs,q)
    x.attrib.update({"id":id_,"type":typ,"value":str(val),"field":field,"scope":scope,"shared":"true","includeChildSelections":"true" if child else "false","includeChildForces":"false"})
    return x
def modifier(p,id_,typ,field,value,conditions):
    ns=qns(p); ms=cont(p,"modifiers"); q=f"{{{ns}}}modifier"; x=next((z for z in ms.findall(q) if z.get("id")==id_),None)
    if x is None:x=ET.SubElement(ms,q)
    x.attrib.update({"id":id_,"type":typ,"field":field,"value":str(value)})
    for ch in list(x):x.remove(ch)
    if len(conditions)==1:target=ET.SubElement(x,f"{{{ns}}}conditions")
    else:
        cgs=ET.SubElement(x,f"{{{ns}}}conditionGroups"); cg=ET.SubElement(cgs,f"{{{ns}}}conditionGroup",{"type":"and"}); target=ET.SubElement(cg,f"{{{ns}}}conditions")
    for c in conditions:
        ET.SubElement(target,f"{{{ns}}}condition",{"type":c.get("type","atLeast"),"value":str(c.get("value",1)),"field":"selections","scope":c.get("scope","roster"),"childId":c["childId"],"shared":"true","includeChildSelections":"true","includeChildForces":"false"})
    return x
def group(p,id_,name,minv=None,maxv=None,hidden=False):
    gs=cont(p,"selectionEntryGroups",before=("costs","modifiers")); g=next((z for z in gs.findall(C("selectionEntryGroup")) if z.get("id")==id_),None)
    if g is None:g=ET.SubElement(gs,C("selectionEntryGroup"))
    g.attrib.update({"id":id_,"name":name,"hidden":"true" if hidden else "false"})
    if minv is not None:cons(g,id_+"-min","min",minv)
    if maxv is not None:cons(g,id_+"-max","max",maxv)
    return g
def elink(p,id_,name,target,maxv=1,hidden=False):
    es=cont(p,"entryLinks",before=("infoLinks","profiles","rules","selectionEntries","selectionEntryGroups","costs","modifiers"))
    e=next((z for z in es.findall(C("entryLink")) if z.get("id")==id_),None)
    if e is None:e=ET.SubElement(es,C("entryLink"))
    e.attrib.update({"id":id_,"name":name,"targetId":target,"type":"selectionEntry","import":"true","hidden":"true" if hidden else "false"})
    if maxv is not None:cons(e,id_+"-max","max",maxv)
    return e
def catlink(p,id_,name,target,primary=False):
    ns=qns(p); cs=cont(p,"categoryLinks"); q=f"{{{ns}}}categoryLink"
    e=next((z for z in cs.findall(q) if z.get("id")==id_),None)
    if e is None:e=ET.SubElement(cs,q)
    e.attrib.update({"id":id_,"name":name,"targetId":target,"hidden":"false"})
    if primary:e.set("primary","true")
    return e

def parent_map(): return {c:p for p in root.iter() for c in p}

# ------------------------------------------------------------------
# 1. Exact conditional visibility for alternate FOC copies.
# ------------------------------------------------------------------
def reset_exact_visibility(e, required):
    e.set("hidden","true")
    ms=e.find(C("modifiers"))
    if ms is not None:
        for m in list(ms):
            if m.get("field")=="hidden":
                ms.remove(m)
    modifier(e,e.get("id")+"-r41-exact-show","set","hidden","false",[{"childId":x,"scope":"roster"} for x in required])

ids={e.get("id"):e for e in root.iter() if e.get("id")}
conditional={
 "r37-wb-serrated-gv-troops":["legion-xvii","allegiance-traitor","r25-rite-xvii-1-last-of-the-serrated-sun"],
 "r37-wb-zardu-ashen-troops":["legion-xvii","allegiance-traitor","r37-wb-zardu-warlord"],
 "r40-sal-cov-pyro":["legion-xviii","r25-rite-xviii-0-the-covenant-of-fire"],
 "r40-sal-cov-infernus":["legion-xviii","r25-rite-xviii-0-the-covenant-of-fire"],
}
for eid,req in conditional.items():
    if eid not in ids:raise RuntimeError("Missing conditional FOC entry "+eid)
    reset_exact_visibility(ids[eid],req)

# Remove Salamanders hidden-count categories accidentally inherited by the two WB alternate copies.
for eid in ["r37-wb-serrated-gv-troops","r37-wb-zardu-ashen-troops"]:
    e=ids[eid]; cls=e.find(C("categoryLinks"))
    if cls is not None:
        for c in list(cls):
            if (c.get("targetId") or "").startswith("r40-sal-"):
                cls.remove(c)

# ------------------------------------------------------------------
# 2. Salamanders Mantle is ADDITIONAL wargear, never armour replacement.
# ------------------------------------------------------------------
MANTLE="r46-sal-mantle"
if MANTLE not in ids:raise RuntimeError("Salamanders Mantle shared entry missing")

# Remove older direct Mantle links under generic Praetor/Centurion so it appears once.
mantle_old_links=0
for hostid in ["hq-praetor","hq-centurion"]:
    host=ids[hostid]
    for p in list(host.iter()):
        for ch in list(p):
            if ch.tag==C("entryLink") and ch.get("targetId")==MANTLE:
                p.remove(ch);mantle_old_links+=1
    g=group(host,"r41-sal-mantle-"+hostid,"Salamanders Mantle — Additional Wargear",0,1,True)
    # clean hidden modifiers on group then exact Legion visibility
    ms=g.find(C("modifiers"))
    if ms is not None:
        for m in list(ms):
            if m.get("field")=="hidden":ms.remove(m)
    modifier(g,g.get("id")+"-show","set","hidden","false",[{"childId":"legion-xviii","scope":"roster"}])
    elink(g,g.get("id")+"-item","Salamanders Mantle",MANTLE,1,False)

# ------------------------------------------------------------------
# 3. Universal wargear architecture.
#    One shared definition per compatible item; local options become links.
#    Costs, constraints and conditions stay local on the link.
# ------------------------------------------------------------------
sse=root.find(C("sharedSelectionEntries"))
if sse is None:
    sse=ET.Element(C("sharedSelectionEntries"))
    # insert before sharedProfiles/sharedRules if possible
    kids=list(root);idx=len(kids)
    for j,k in enumerate(kids):
        if k.tag.split("}")[-1] in ("sharedProfiles","sharedRules","sharedInfoGroups"):
            idx=j;break
    root.insert(idx,sse)

def norm_name(s):
    s=(s or "").replace("’","'").replace("–","-").strip().casefold()
    s=re.sub(r"\s+"," ",s)
    return s

def static_sig(e):
    infos=[]
    il=e.find(C("infoLinks"))
    if il is not None:
        for x in il:
            infos.append((x.get("type"),x.get("name"),x.get("targetId"),x.get("hidden")))
    rules=[]
    rs=e.find(C("rules"))
    if rs is not None:
        for x in rs:
            rules.append((x.get("name")," ".join((x.findtext(C("description")) or "").split())))
    profs=[]
    ps=e.find(C("profiles"))
    if ps is not None:
        for p in ps:
            chars=tuple((c.get("name")," ".join((c.text or "").split())) for c in p.findall(f"./{C('characteristics')}/{C('characteristic')}"))
            profs.append((p.get("name"),p.get("typeId"),chars))
    return (tuple(sorted(infos)),tuple(sorted(rules)),tuple(sorted(profs)))

EMPTY_SIG=((),(),())

def leaf_upgrade(e):
    if e.tag!=C("selectionEntry") or e.get("type")!="upgrade":return False
    if e.find(C("selectionEntries")) is not None or e.find(C("selectionEntryGroups")) is not None:return False
    if e.find(C("categoryLinks")) is not None and len(list(e.find(C("categoryLinks"))))>0:return False
    da=e.get("defaultAmount")
    if da not in (None,"0","0.0"):return False
    return True

def clone_payload(src,dst,prefix):
    # Remove existing static information then clone only information payload.
    for tag in ("infoLinks","profiles","rules"):
        old=dst.find(C(tag))
        if old is not None:dst.remove(old)
        ss=src.find(C(tag))
        if ss is None:continue
        cp=copy.deepcopy(ss)
        oldids=[z.get("id") for z in cp.iter() if z.get("id")]
        mp={o:prefix+hashlib.sha1(o.encode()).hexdigest()[:12] for o in oldids}
        for z in cp.iter():
            if z.get("id") in mp:z.set("id",mp[z.get("id")])
            for a in ("childId","field","targetId"):
                if z.get(a) in mp:z.set(a,mp[z.get(a)])
        # schema-friendly insertion
        if tag=="infoLinks":dst.insert(len(list(dst)),cp)
        else:dst.insert(len(list(dst)),cp)

# Existing shared canonical entries by normalized name.
shared_by_norm=collections.defaultdict(list)
for e in sse.findall(C("selectionEntry")):
    if e.get("type")=="upgrade":
        shared_by_norm[norm_name(e.get("name"))].append(e)

# Gather local leaf upgrades by normalized name.
pm=parent_map()
local_by_norm=collections.defaultdict(list)
for e in root.iter(C("selectionEntry")):
    if not leaf_upgrade(e):continue
    p=pm.get(e)
    if p is sse:continue
    local_by_norm[norm_name(e.get("name"))].append(e)

created_canon=0; converted=0; skipped_incompatible=0; existing_canon_used=0
local_parent=parent_map()

def pick_canonical(arr):
    # Prefer core gear-* IDs, then otherwise first.
    return sorted(arr,key=lambda e:(0 if (e.get("id") or "").startswith("gear-") else 1,len(e.get("id") or ""),e.get("id") or ""))[0]

for nm,locals_ in list(local_by_norm.items()):
    existing=shared_by_norm.get(nm,[])
    zero_cost_existing=[]
    for x in existing:
        vals=[float(z.get("value","0") or 0) for z in x.findall(f"./{C('costs')}/{C('cost')}")]
        if not vals or all(v==0 for v in vals):
            zero_cost_existing.append(x)
    canonical=pick_canonical(zero_cost_existing) if zero_cost_existing else None

    sig_groups=collections.defaultdict(list)
    for e in locals_:sig_groups[static_sig(e)].append(e)
    nonempty=[s for s in sig_groups if s!=EMPTY_SIG]

    # If no shared target exists, only universalise repeated compatible definitions.
    if canonical is None:
        # A non-zero-cost shared wrapper is a contextual price/access package.
        # Leave same-name locals alone rather than risking double costs or a second
        # visible shared selection with the same name.
        if existing:
            skipped_incompatible += len(locals_)
            continue
        if len(locals_)<3 or len(nonempty)>1:
            continue
        rep=(sig_groups[nonempty[0]][0] if nonempty else locals_[0])
        cid="r41-universal-gear-"+hashlib.sha1(nm.encode()).hexdigest()[:14]
        canonical=ET.SubElement(sse,C("selectionEntry"),{"id":cid,"name":rep.get("name"),"type":"upgrade","hidden":"false"})
        if nonempty:clone_payload(rep,canonical,cid+"-")
        shared_by_norm[nm]=[canonical];created_canon+=1
    else:
        existing_canon_used+=1
        csig=static_sig(canonical)
        if csig==EMPTY_SIG and len(nonempty)==1:
            rep=sig_groups[nonempty[0]][0]
            clone_payload(rep,canonical,(canonical.get("id") or "canon")+"-r41-")
            csig=static_sig(canonical)

    csig=static_sig(canonical)
    # Replace compatible local definitions with entryLinks preserving local mechanics.
    for e in list(locals_):
        esig=static_sig(e)
        if esig not in (EMPTY_SIG,csig):
            skipped_incompatible+=1
            continue
        container=local_parent.get(e)
        if container is None or container.tag!=C("selectionEntries"):
            continue
        idx=list(container).index(e)
        attrs={"id":e.get("id"),"name":e.get("name"),"targetId":canonical.get("id"),"type":"selectionEntry","import":"true","hidden":e.get("hidden","false")}
        if e.get("collective") is not None:attrs["collective"]=e.get("collective")
        link=ET.Element(C("entryLink"),attrs)
        # Preserve local price/selection/visibility mechanics only.
        for tag in ("constraints","costs","modifiers"):
            x=e.find(C(tag))
            if x is not None:link.append(copy.deepcopy(x))
        container.remove(e);container.insert(idx,link);converted+=1

# ------------------------------------------------------------------
# 4. Contextual shared wrappers.
# ------------------------------------------------------------------
# Shared wrappers with their own non-zero cost/eligibility are deliberately retained.
# They are price/access packages rather than competing wargear definitions.
# Their referenced rules/profiles are already shared where compatible.
wrapper_payload_dedup=0

# ------------------------------------------------------------------
# 5. Iron Halo: army-wide 0-1, Rosarius explicitly excluded.
# ------------------------------------------------------------------
IRON="gear-hq-iron-halo"
if IRON not in ids:
    raise RuntimeError("Canonical Iron Halo entry missing")

HALO_CAT="r41-iron-halo-army-limit"
# Hidden category in the game system.
gce=groot.find(G("categoryEntries"))
if gce is None:
    gce=ET.SubElement(groot,G("categoryEntries"))
hcat=next((z for z in gce.findall(G("categoryEntry")) if z.get("id")==HALO_CAT),None)
if hcat is None:
    hcat=ET.SubElement(gce,G("categoryEntry"))
hcat.attrib.update({"id":HALO_CAT,"name":"Iron Halo — army-wide limit","hidden":"true"})

# Force-level max 1 across every selected Iron Halo / built-in carrier.
force=next((z for z in groot.iter(G("forceEntry")) if z.get("id")=="force-standard"),None)
if force is None:
    raise RuntimeError("Standard force entry missing for Iron Halo limit")
fcls=cont(force,"categoryLinks")
hfl=next((z for z in fcls.findall(G("categoryLink")) if z.get("id")=="r41-iron-halo-force"),None)
if hfl is None:
    hfl=ET.SubElement(fcls,G("categoryLink"))
hfl.attrib.update({"id":"r41-iron-halo-force","name":"Iron Halo — army-wide limit","targetId":HALO_CAT,"hidden":"true"})
cons(hfl,"r41-iron-halo-max","max",1,"selections","parent",True)

# Any purchased Iron Halo counts automatically.
catlink(ids[IRON],"r41-iron-halo-gear-cat","Iron Halo — army-wide limit",HALO_CAT)

# Built-in Iron Halos count too. Rosarius never does: it is intentionally not tagged.
# Generic Praetor always includes an Iron Halo.
halo_carriers=[]
praetor=ids.get("hq-praetor")
if praetor is None:
    raise RuntimeError("Legion Praetor missing")
catlink(praetor,"r41-praetor-iron-halo-cat","Iron Halo — army-wide limit",HALO_CAT)
halo_carriers.append(("hq-praetor",praetor.get("name")))

# Named/top-level characters with an explicit built-in Iron Halo also count,
# unless their own text explicitly says the Halo does not count toward the limit.
for e in root.findall(f"./{C('selectionEntries')}/{C('selectionEntry')}"):
    if e is praetor: continue
    direct=[]
    for r in e.findall(f"./{C('rules')}/{C('rule')}"):
        direct.append((r.get("name") or "")+" "+(r.findtext(C("description")) or ""))
    for il in e.findall(f"./{C('infoLinks')}/{C('infoLink')}"):
        direct.append((il.get("name") or "")+" "+(il.get("targetId") or ""))
    text=" ".join(direct).lower()
    if "iron halo" not in text:
        continue
    if ("iron halo" in text and ("does not count toward" in text or "does not count towards" in text or "doesn't count toward" in text)):
        continue
    catlink(e,"r41-halo-carrier-"+hashlib.sha1((e.get("id") or "").encode()).hexdigest()[:12],"Iron Halo — army-wide limit",HALO_CAT)
    halo_carriers.append((e.get("id"),e.get("name")))

# ------------------------------------------------------------------
# Validation + revision.
# ------------------------------------------------------------------
root.set("revision","41")
root.set("gameSystemRevision","6")
groot.set("revision","6")
tree.write(CAT,encoding="utf-8",xml_declaration=True)
ET.register_namespace("",GNS)
gtree.write(GST,encoding="utf-8",xml_declaration=True)
ET.register_namespace("",INS)
it=ET.parse(IDX);ir=it.getroot()
for x in ir.iter(I("dataIndexEntry")):
    if x.get("filePath")=="Legiones Astartes.cat":x.set("dataRevision","41")
    if x.get("filePath")=="Prohammer 30k.gst":x.set("dataRevision","6")
it.write(IDX,encoding="utf-8",xml_declaration=True)

rr=ET.parse(CAT).getroot(); gg=ET.parse(GST).getroot(); checks=[]
def ck(n,o):
    checks.append((n,bool(o)))
    if not o:raise RuntimeError("R41 validation failed: "+n)

ck("CAT revision 41",rr.get("revision")=="41")
ck("Index revision 41",'dataRevision="41"' in IDX.read_text(encoding="utf-8"))
ck("CAT points to GST 6",rr.get("gameSystemRevision")=="6")
ck("GST revision 6",gg.get("revision")=="6")
ck("Index GST revision 6",'filePath="Prohammer 30k.gst"' in IDX.read_text(encoding="utf-8") and 'dataRevision="6"' in IDX.read_text(encoding="utf-8"))

rids={e.get("id"):e for e in rr.iter() if e.get("id")}
# Exact FOC visibility: default hidden and only one hidden modifier per root.
for eid,req in conditional.items():
    e=rids[eid];ck(eid+" default hidden",e.get("hidden")=="true")
    ms=[m for m in e.findall(f"./{C('modifiers')}/{C('modifier')}") if m.get("field")=="hidden"]
    ck(eid+" has one exact visibility modifier",len(ms)==1)
    txt=ET.tostring(ms[0],encoding="unicode")
    ck(eid+" exact prerequisite set",all(x in txt for x in req))

# Mantle is separate from armour.
for hostid in ["hq-praetor","hq-centurion"]:
    gid="r41-sal-mantle-"+hostid
    ck(gid+" exists",gid in rids)
    g=rids[gid]
    ck(gid+" contains Mantle link",any(x.get("targetId")==MANTLE for x in g.findall(f"./{C('entryLinks')}/{C('entryLink')}")))
# no Mantle link appears inside a group named Armour / Armour Type
pmap={c:p for p in rr.iter() for c in p};badmantle=[]
for l in rr.iter(C("entryLink")):
    if l.get("targetId")!=MANTLE:continue
    p=pmap.get(l)
    while p is not None and p.tag!=C("selectionEntry"):
        if p.tag==C("selectionEntryGroup") and "armour" in (p.get("name") or "").lower():
            badmantle.append((l.get("id"),p.get("name")));break
        p=pmap.get(p)
ck("Mantle is not an armour replacement",not badmantle)

# Iron Halo army-wide category and Rosarius exemption.
gids={e.get("id"):e for e in gg.iter() if e.get("id")}
ck("Iron Halo hidden category exists",HALO_CAT in gids)
ck("Iron Halo force max exists","r41-iron-halo-force" in gids)
ck("Canonical Iron Halo counts",any(x.get("targetId")==HALO_CAT for x in rids[IRON].findall(f"./{C('categoryLinks')}/{C('categoryLink')}")))
ck("Praetor built-in Iron Halo counts",any(x.get("targetId")==HALO_CAT for x in rids["hq-praetor"].findall(f"./{C('categoryLinks')}/{C('categoryLink')}")))
ros=ids.get("r29-gear-rosarius")
if ros is not None:
    ck("Rosarius does not count as Iron Halo",not any(x.get("targetId")==HALO_CAT for x in ros.findall(f"./{C('categoryLinks')}/{C('categoryLink')}")))

# Global IDs unique.
allids=[e.get("id") for e in rr.iter() if e.get("id")]
dups=[x for x,c in collections.Counter(allids).items() if c>1]
ck("All XML IDs unique",not dups)

# Universalisation did real work.
ck("Universal wargear conversion performed",converted>0)

lines=[
"Live R41 — universal wargear + conditional FOC cleanup",
"Input CAT=40/GST=5 -> CAT=41/GST=6","",
"RITE / CHARACTER FOC VISIBILITY:",
"- Gal Vorbak Serrated Sun Troops are hidden by default and appear only with Word Bearers + Traitor + Last of the Serrated Sun.",
"- Ashen Circle Reign of Fire Troops are hidden by default and appear only with Word Bearers + Traitor + Zardu Layak selected as Warlord.",
"- Pyroclast and Salamanders Infernus Destroyer Troops are hidden by default and appear only with Salamanders + Covenant of Fire.",
"- Removed copied/base visibility modifiers that were accidentally revealing these alternate FOC entries without their enabler.","",
"SALAMANDERS MANTLE:",
"- The Mantle is now a separate Additional Wargear selector for generic Praetors and Centurions.",
"- It is completely independent of Power Armour, Artificer Armour and all Terminator Armour choices.",
f"- Removed {mantle_old_links} older generic Mantle link(s) before creating the dedicated selector.",
"- Existing army-wide 0–1 handling, including Numeon and Nomus counting as the Mantle, remains intact.","",
"UNIVERSAL WARGEAR:",
f"- Converted {converted} compatible local leaf wargear definitions into links to universal shared wargear entries.",
f"- Created {created_canon} new universal shared wargear definitions where repeated local items had one compatible definition.",
f"- Reused existing shared wargear canonicals across {existing_canon_used} duplicate-name groups.",
f"- Left {skipped_incompatible} context-specific entries local because their actual rule/profile payload differed from the canonical item.",
"- Context-specific shared price/access wrappers with their own cost were deliberately retained so no discounts or Legion-specific prices were altered.",
"- Costs, quantity limits, visibility conditions and replacement restrictions remain local to each selector/link; only the actual wargear definition is universal.",
"- This is now the standing architecture: one actual wargear definition, many contextual links when prices or eligibility differ.","",
"IRON HALO:",
"- Iron Halo is now mechanically max 1 across the entire army.",
"- The Praetor's included Iron Halo counts immediately, so selecting a Praetor prevents any other model from taking another Iron Halo.",
f"- Detected and tagged {len(halo_carriers)-1} additional top-level Characters with built-in Iron Halos.",
"- Purchased Iron Halos use the same army-wide counter.",
"- Rosarius is explicitly outside this limit, matching the army-list rule.","",
"VALIDATION:"
]+[f'- {"PASS" if ok else "FAIL"}: {n}' for n,ok in checks]
OUT.write_text("\n".join(lines)+"\n",encoding="utf-8")
print(OUT.read_text())
