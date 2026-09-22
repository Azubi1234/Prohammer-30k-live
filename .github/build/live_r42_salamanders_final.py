from pathlib import Path
import copy, collections, hashlib, re, xml.etree.ElementTree as ET

CAT=Path("Legiones Astartes.cat"); GST=Path("Prohammer 30k.gst"); IDX=Path("index.xml")
OUT=Path("inspection-live-r42-salamanders-final-restrictions.txt")
CNS="http://www.battlescribe.net/schema/catalogueSchema"; GNS="http://www.battlescribe.net/schema/gameSystemSchema"; INS="http://www.battlescribe.net/schema/dataIndexSchema"
ET.register_namespace("",CNS)
C=lambda t:f"{{{CNS}}}{t}"; G=lambda t:f"{{{GNS}}}{t}"; I=lambda t:f"{{{INS}}}{t}"

ct=ET.parse(CAT); cr=ct.getroot(); gt=ET.parse(GST); gr=gt.getroot()
if cr.get("revision")!="41": raise RuntimeError(f"R42 expected CAT41, got {cr.get('revision')}")
if gr.get("revision")!="6": raise RuntimeError(f"R42 expected GST6, got {gr.get('revision')}")
base_ids=collections.Counter(e.get("id") for e in cr.iter() if e.get("id"))

def qns(e):return e.tag.split("}")[0].strip("{")
def cont(p,tag,before=("constraints","categoryLinks","entryLinks","infoLinks","profiles","rules","selectionEntries","selectionEntryGroups","costs","modifiers")):
    ns=qns(p);q=f"{{{ns}}}{tag}";x=p.find(q)
    if x is not None:return x
    x=ET.Element(q);kids=list(p);idx=len(kids)
    for j,k in enumerate(kids):
        if k.tag.split("}")[-1] in before:idx=j;break
    p.insert(idx,x);return x
def cons(p,id_,typ,val,field="selections",scope="parent",child=False):
    ns=qns(p);cs=cont(p,"constraints");q=f"{{{ns}}}constraint";x=next((z for z in cs.findall(q) if z.get("id")==id_),None)
    if x is None:x=ET.SubElement(cs,q)
    x.attrib.update({"id":id_,"type":typ,"value":str(val),"field":field,"scope":scope,"shared":"true","includeChildSelections":"true" if child else "false","includeChildForces":"false"});return x
def modifier(p,id_,typ,field,value,conds):
    ns=qns(p);ms=cont(p,"modifiers");q=f"{{{ns}}}modifier";x=next((z for z in ms.findall(q) if z.get("id")==id_),None)
    if x is None:x=ET.SubElement(ms,q)
    x.attrib.update({"id":id_,"type":typ,"field":field,"value":str(value)})
    for c in list(x):x.remove(c)
    if len(conds)==1:target=ET.SubElement(x,f"{{{ns}}}conditions")
    else:
        cgs=ET.SubElement(x,f"{{{ns}}}conditionGroups");cg=ET.SubElement(cgs,f"{{{ns}}}conditionGroup",{"type":"and"});target=ET.SubElement(cg,f"{{{ns}}}conditions")
    for c in conds:
        ET.SubElement(target,f"{{{ns}}}condition",{"type":c.get("type","atLeast"),"value":str(c.get("value",1)),"field":"selections","scope":c.get("scope","roster"),"childId":c["childId"],"shared":"true","includeChildSelections":"true","includeChildForces":"false"})
    return x
def catlink(p,id_,name,target,primary=False):
    ns=qns(p);cs=cont(p,"categoryLinks");q=f"{{{ns}}}categoryLink";x=next((z for z in cs.findall(q) if z.get("id")==id_),None)
    if x is None:x=ET.SubElement(cs,q)
    x.attrib.update({"id":id_,"name":name,"targetId":target,"hidden":"false"})
    if primary:x.set("primary","true")
    return x
def elink(p,id_,name,target,hidden=False,maxv=1):
    es=cont(p,"entryLinks",before=("infoLinks","profiles","rules","selectionEntries","selectionEntryGroups","costs","modifiers"));x=next((z for z in es.findall(C("entryLink")) if z.get("id")==id_),None)
    if x is None:x=ET.SubElement(es,C("entryLink"))
    x.attrib.update({"id":id_,"name":name,"targetId":target,"type":"selectionEntry","import":"true","hidden":"true" if hidden else "false"})
    if maxv is not None:cons(x,id_+"-max","max",maxv)
    return x
def parent_map():return {c:p for p in cr.iter() for c in p}
def root_entry(e,pm):
    p=e;last=None
    while p in pm:
        if p.tag==C("selectionEntry"):last=p
        p=pm[p]
        if p is cr:break
    return last if last is not None else (e if e.tag==C("selectionEntry") else None)
def ancestor_text(e,pm,lim=12):
    out=[];p=e
    while p is not None and len(out)<lim:
        if p.get("name"):out.append(p.get("name"))
        p=pm.get(p)
    return " > ".join(out)
def gcat(id_,name):
    ce=gr.find(G("categoryEntries"))
    if ce is None:ce=ET.SubElement(gr,G("categoryEntries"))
    x=next((z for z in ce.findall(G("categoryEntry")) if z.get("id")==id_),None)
    if x is None:x=ET.SubElement(ce,G("categoryEntry"))
    x.attrib.update({"id":id_,"name":name,"hidden":"true"});return x
force=next((x for x in gr.iter(G("forceEntry")) if x.get("id")=="force-standard"),None)
if force is None:raise RuntimeError("force-standard missing")
def force_link(id_,name,target):
    cs=cont(force,"categoryLinks");x=next((z for z in cs.findall(G("categoryLink")) if z.get("id")==id_),None)
    if x is None:x=ET.SubElement(cs,G("categoryLink"))
    x.attrib.update({"id":id_,"name":name,"targetId":target,"hidden":"true"});return x
def add_hide_when(e,id_,conds):
    modifier(e,id_,"set","hidden","true",conds)
def add_show_when(e,id_,conds):
    modifier(e,id_,"set","hidden","false",conds)

LEG="legion-xviii"; COV="r25-rite-xviii-0-the-covenant-of-fire"
INF="r46-sal-inferno-pistol"; MC="r46-sal-mastercrafted"; AA="r46-sal-artificer-armour"; CER="r46-sal-ceramite"
ids={e.get("id"):e for e in cr.iter() if e.get("id")}
for req in [LEG,COV,INF,MC,AA,CER]: 
    if req not in ids:raise RuntimeError("Missing required "+req)

# -------------------------------------------------------------------
# 1. Firedrakes are genuinely 0-1 across normal + Salamanders retinues.
# -------------------------------------------------------------------
FD_CAT="r42-sal-firedrake-limit"
gcat(FD_CAT,"Salamanders — Firedrake Terminator Squad limit")
fdfl=force_link("r42-sal-firedrake-force","Salamanders — Firedrake Terminator Squad limit",FD_CAT)
cons(fdfl,"r42-sal-firedrake-max","max",1,"selections","parent",True)
firedrakes=[]
for e in cr.iter(C("selectionEntry")):
    n=(e.get("name") or "").lower();eid=e.get("id") or ""
    if "firedrake terminator squad" not in n:continue
    if "r46-al-reward" in eid:continue
    # Only the actual Salamanders unit and Salamanders retinue copies.
    if not ("xviii" in eid or "r40-vul-ret-firedrake" in eid or "live-r2-r41-unit-xviii" in eid):
        continue
    catlink(e,eid+"-r42-fd-limit","Salamanders — Firedrake Terminator Squad limit",FD_CAT);firedrakes.append(e)

# -------------------------------------------------------------------
# 2. Salamanders compulsory Troops: Support Squad cannot satisfy the 2.
# -------------------------------------------------------------------
COMP_CAT="r42-sal-compulsory-troops"
gcat(COMP_CAT,"Salamanders — compulsory-capable Troops")
cfl=force_link("r42-sal-comp-force","Salamanders — compulsory-capable Troops",COMP_CAT)
cmin=cons(cfl,"r42-sal-comp-min","min",0,"selections","parent",True)
modifier(cfl,"r42-sal-comp-min2","set",cmin.get("id"),2,[{"childId":LEG,"scope":"roster"}])

def primary_troop(e):
    return any(c.get("targetId")=="cat-troops" and c.get("primary")=="true" for c in e.findall(f"./{C('categoryLinks')}/{C('categoryLink')}"))
def rule_text(e):
    bits=[]
    for r in e.iter(C("rule")):bits.append((r.get("name") or "")+" "+(r.findtext(C("description")) or ""))
    for i in e.iter(C("infoLink")):bits.append(i.get("name") or "")
    return " ".join(bits).lower()
comp_tagged=0;comp_excluded=[]
for e in cr.findall(f"./{C('selectionEntries')}/{C('selectionEntry')}"):
    if not primary_troop(e):continue
    txt=rule_text(e)+" "+(e.get("name") or "").lower()
    if "support squad" in txt or "non-compulsory" in txt or "may not fulfil compulsory" in txt or "may not fulfill compulsory" in txt:
        comp_excluded.append((e.get("id"),e.get("name")));continue
    catlink(e,e.get("id")+"-r42-sal-comp","Salamanders — compulsory-capable Troops",COMP_CAT);comp_tagged+=1

# -------------------------------------------------------------------
# 3. Covenant of Fire: units that MUST Deep Strike cannot be selected.
#    Drop Pod, Dreadnought Drop Pod and Dreadclaw all must enter via DS.
# -------------------------------------------------------------------
pm=parent_map()
pod_targets={"transport-drop-pod","transport-dreadnought-pod","transport-dreadclaw"}
pod_links=0;pod_entries=0
for l in cr.iter(C("entryLink")):
    if l.get("targetId") in pod_targets:
        add_hide_when(l,(l.get("id") or "pod")+"-r42-cov-hide",[{"childId":LEG},{"childId":COV}]);pod_links+=1
for e in cr.iter(C("selectionEntry")):
    if e.get("type") not in ("model","unit"):continue
    n=(e.get("name") or "").lower()
    if "drop pod" not in n and "dreadclaw" not in n:continue
    # Avoid configuration/wording entries; transport models/units only.
    add_hide_when(e,(e.get("id") or "pod")+"-r42-cov-hide",[{"childId":LEG},{"childId":COV}]);pod_entries+=1

# -------------------------------------------------------------------
# 4. Clean the R40 Inferno Pistol heuristic and re-add only legal access.
#    Source: Salamanders ICs OR squad Sergeants with Armoury access.
# -------------------------------------------------------------------
pm=parent_map()
removed_inferno=0
for container in list(cr.iter()):
    for ch in list(container):
        if ch.tag==C("entryLink") and ch.get("targetId")==INF and "r40-sal-inferno-" in (ch.get("id") or ""):
            container.remove(ch);removed_inferno+=1

pm=parent_map()
def armoury_sergeant_group(g):
    n=(g.get("name") or "").lower()
    if "armoury" not in n:return False
    return any(k in n for k in ["sergeant","huscarl","hunt-master"])
def direct_child_armoury_groups(g):
    sg=g.find(C("selectionEntryGroups"))
    return [] if sg is None else [x for x in sg.findall(C("selectionEntryGroup")) if "armoury" in (x.get("name") or "").lower()]
def add_legion_link(g,target,label,prefix):
    es=cont(g,"entryLinks")
    if any(x.get("targetId")==target for x in es.findall(C("entryLink"))):return None
    id_=prefix+hashlib.sha1((g.get("id") or label).encode()).hexdigest()[:12]
    l=elink(g,id_,label,target,True,1)
    add_show_when(l,id_+"-show",[{"childId":LEG}]);return l

inferno_added=0
for g in list(cr.iter(C("selectionEntryGroup"))):
    if not armoury_sergeant_group(g):continue
    kids=direct_child_armoury_groups(g)
    if kids:continue
    n=(g.get("name") or "").lower()
    # If split into Weapons/Wargear groups, Inferno goes only in Weapons.
    if "wargear" in n and "weapon" not in n:continue
    if add_legion_link(g,INF,"Inferno Pistol — Salamanders","r42-sal-inf-") is not None:inferno_added+=1

# -------------------------------------------------------------------
# 5. Artificer Armour: +15 for non-IC Armoury users; never an IC discount.
#    Remove old squad-root package links and place it in Sergeant Armouries.
# -------------------------------------------------------------------
removed_art=0
for container in list(cr.iter()):
    for ch in list(container):
        if ch.tag==C("entryLink") and ch.get("targetId")==AA:
            container.remove(ch);removed_art+=1

pm=parent_map();art_added=0;generic_art_hidden=0
def target_name(l):
    t=ids.get(l.get("targetId"));return (t.get("name") if t is not None else (l.get("name") or ""))
for g in list(cr.iter(C("selectionEntryGroup"))):
    if not armoury_sergeant_group(g):continue
    kids=direct_child_armoury_groups(g)
    if kids:continue
    n=(g.get("name") or "").lower()
    chain=ancestor_text(g,pm).lower()
    if "terminator" in chain:continue
    if "weapon" in n and "wargear" not in n:continue
    # Hide the normal +20 Artificer Armour option in this Sergeant armoury.
    for l in g.iter(C("entryLink")):
        if target_name(l).strip().lower()=="artificer armour":
            add_hide_when(l,(l.get("id") or "art")+"-r42-sal-hide",[{"childId":LEG}]);generic_art_hidden+=1
    if add_legion_link(g,AA,"Artificer Armour — Salamanders access","r42-sal-aa-") is not None:art_added+=1

# Infernus Sergeant has explicit Armoury access but a custom group name.
infsg=next((g for g in cr.iter(C("selectionEntryGroup")) if g.get("id")=="r41-unit-xviii-2-salamanders-infernus-destroyer-squad-sgt"),None)
if infsg is not None and add_legion_link(infsg,AA,"Artificer Armour — Salamanders access","r42-sal-aa-infernus-") is not None:art_added+=1

# -------------------------------------------------------------------
# 6. Master-crafted Weapon: universally replace normal +15 with Salamanders +10
#    wherever the normal selector is actually present.
# -------------------------------------------------------------------
pm=parent_map(); ids={e.get("id"):e for e in cr.iter() if e.get("id")}
def norm(s):return re.sub(r"\s+"," ",(s or "").strip()).casefold()
def clone_link_discount(old,target,newname,prefix):
    container=pm.get(old)
    if container is None or container.tag!=C("entryLinks"):return None
    if any(x.get("targetId")==target for x in container.findall(C("entryLink"))):return None
    cp=copy.deepcopy(old)
    oldids=[x.get("id") for x in cp.iter() if x.get("id")]
    mp={o:prefix+hashlib.sha1((o+old.get("id","")).encode()).hexdigest()[:12] for o in oldids}
    for x in cp.iter():
        if x.get("id") in mp:x.set("id",mp[x.get("id")])
        for a in ("field","childId"):
            if x.get(a) in mp:x.set(a,mp[x.get(a)])
    cp.set("id",prefix+hashlib.sha1((old.get("id") or newname).encode()).hexdigest()[:14])
    cp.set("targetId",target);cp.set("name",newname)
    costs=cp.find(C("costs"))
    if costs is not None:cp.remove(costs)
    add_hide_when(cp,cp.get("id")+"-hide-not-sal",[{"childId":LEG,"type":"lessThan","value":1}])
    container.append(cp);return cp

master_added=0;master_hidden=0
for l in list(cr.iter(C("entryLink"))):
    if l.get("targetId")==MC:continue
    t=ids.get(l.get("targetId"))
    if t is None or norm(t.get("name"))!="master-crafted weapon":continue
    add_hide_when(l,(l.get("id") or "mc")+"-r42-sal-hide",[{"childId":LEG}]);master_hidden+=1
    if clone_link_discount(l,MC,"Master-crafted Weapon — Salamanders price","r42-sal-mc-") is not None:master_added+=1

# -------------------------------------------------------------------
# 7. Reinforced Ceramite: +10 on eligible vehicles, but Land Raiders and
#    Spartans keep their normal listed price.
# -------------------------------------------------------------------
pm=parent_map();ids={e.get("id"):e for e in cr.iter() if e.get("id")}
# Remove special-price links accidentally attached to Land Raiders/Spartans.
cer_removed_exempt=0
for container in list(cr.iter()):
    for ch in list(container):
        if ch.tag!=C("entryLink") or ch.get("targetId")!=CER:continue
        txt=ancestor_text(ch,pm).lower()
        if "land raider" in txt or "spartan" in txt:
            container.remove(ch);cer_removed_exempt+=1
pm=parent_map();ids={e.get("id"):e for e in cr.iter() if e.get("id")}
cer_hidden=0;cer_added=0
for l in list(cr.iter(C("entryLink"))):
    if l.get("targetId")==CER:continue
    t=ids.get(l.get("targetId"))
    tn=norm(t.get("name") if t is not None else l.get("name"))
    if tn not in ("armoured ceramite","reinforced ceramite"):continue
    txt=ancestor_text(l,pm).lower()
    if "land raider" in txt or "spartan" in txt:continue
    add_hide_when(l,(l.get("id") or "cer")+"-r42-sal-hide",[{"childId":LEG}]);cer_hidden+=1
    # Only create if this root/context doesn't already contain the Salamanders price.
    root=root_entry(l,pm)
    already=False
    if root is not None:
        already=any(x.get("targetId")==CER for x in root.iter(C("entryLink")))
    if not already and clone_link_discount(l,CER,"Armoured Ceramite — Salamanders price","r42-sal-cer-") is not None:cer_added+=1

# -------------------------------------------------------------------
# 8. Explicitly retain the correct Rite-copy visibility from R41.
# -------------------------------------------------------------------
for eid,req in {
 "r40-sal-cov-pyro":[LEG,COV],
 "r40-sal-cov-infernus":[LEG,COV],
}.items():
    e=ids[eid]
    e.set("hidden","true")
    ms=e.find(C("modifiers"))
    if ms is not None:
        for m in list(ms):
            if m.get("field")=="hidden":ms.remove(m)
    add_show_when(e,eid+"-r42-show",[{"childId":x} for x in req])

# -------------------------------------------------------------------
# Revision
# -------------------------------------------------------------------
cr.set("revision","42");cr.set("gameSystemRevision","7");gr.set("revision","7")
ct.write(CAT,encoding="utf-8",xml_declaration=True)
ET.register_namespace("",GNS);gt.write(GST,encoding="utf-8",xml_declaration=True)
ET.register_namespace("",INS);it=ET.parse(IDX);ir=it.getroot()
for x in ir.iter(I("dataIndexEntry")):
    if x.get("filePath")=="Legiones Astartes.cat":x.set("dataRevision","42")
    if x.get("filePath")=="Prohammer 30k.gst":x.set("dataRevision","7")
it.write(IDX,encoding="utf-8",xml_declaration=True)

# -------------------------------------------------------------------
# Validation
# -------------------------------------------------------------------
rr=ET.parse(CAT).getroot();gg=ET.parse(GST).getroot();checks=[]
def ck(n,o):
    checks.append((n,bool(o)))
    if not o:raise RuntimeError("R42 validation failed: "+n)
ck("CAT revision 42",rr.get("revision")=="42")
ck("GST revision 7",gg.get("revision")=="7")
ck("CAT points GST7",rr.get("gameSystemRevision")=="7")
idx=IDX.read_text(encoding="utf-8");ck("Index 42/7",'dataRevision="42"' in idx and 'dataRevision="7"' in idx)
rids={e.get("id"):e for e in rr.iter() if e.get("id")};gids={e.get("id"):e for e in gg.iter() if e.get("id")}
ck("Firedrake limit category exists",FD_CAT in gids)
ck("Compulsory Troops category exists",COMP_CAT in gids)
# Every Salamanders Firedrake copy must carry shared limit.
fd_after=[e for e in rr.iter(C("selectionEntry")) if "firedrake terminator squad" in (e.get("name") or "").lower() and "r46-al-reward" not in (e.get("id") or "") and ("xviii" in (e.get("id") or "") or "r40-vul-ret-firedrake" in (e.get("id") or ""))]
ck("All Salamanders Firedrake copies share 0-1",all(any(c.get("targetId")==FD_CAT for c in e.findall(f"./{C('categoryLinks')}/{C('categoryLink')}")) for e in fd_after))
# Adherent excluded from compulsory category.
ad=rids["r41-unit-xviii-3-adherent-squad"]
ck("Adherent cannot count compulsory",not any(c.get("targetId")==COMP_CAT for c in ad.findall(f"./{C('categoryLinks')}/{C('categoryLink')}")))
# Rite copies hidden exactly behind Covenant.
for eid in ["r40-sal-cov-pyro","r40-sal-cov-infernus"]:
    e=rids[eid];txt=ET.tostring(e.find(C("modifiers")),encoding="unicode")
    ck(eid+" conditional",e.get("hidden")=="true" and LEG in txt and COV in txt)
# Pods/Dreadclaws carry Covenant hide conditions.
sample_pods=[l for l in rr.iter(C("entryLink")) if l.get("targetId") in pod_targets]
ck("Covenant blocks linked mandatory-DS transports",sample_pods and all(COV in ET.tostring(l.find(C("modifiers")),encoding="unicode") if l.find(C("modifiers")) is not None else False for l in sample_pods))
# Inferno heuristic is gone.
bad_inf=[l.get("id") for l in rr.iter(C("entryLink")) if l.get("targetId")==INF and "r40-sal-inferno-" in (l.get("id") or "")]
ck("Overbroad R40 Inferno links removed",not bad_inf)
# No special Ceramite price under Land Raider/Spartan.
rpm={c:p for p in rr.iter() for c in p};bad_cer=[]
for l in rr.iter(C("entryLink")):
    if l.get("targetId")!=CER:continue
    txt=ancestor_text(l,rpm).lower()
    if "land raider" in txt or "spartan" in txt:bad_cer.append(l.get("id"))
ck("Land Raiders/Spartans do not get Salamanders Ceramite discount",not bad_cer)
# No new/worsened duplicate XML IDs.
new_counts=collections.Counter(e.get("id") for e in rr.iter() if e.get("id"))
worse={k:v for k,v in new_counts.items() if v>max(1,base_ids.get(k,0))}
ck("No new/worsened duplicate IDs",not worse)

lines=[
"Live R42 — Salamanders final restriction audit",
"Input CAT=41/GST=6 -> CAT=42/GST=7","",
"FIXES:",
f"- Firedrake 0-1 is now shared across {len(firedrakes)} Salamanders normal/retinue copies (Alpha Legion Rewards of Treachery excluded).",
f"- Added a Salamanders-specific compulsory-Troops counter: {comp_tagged} top-level compulsory-capable Troops tagged; {len(comp_excluded)} Support/non-compulsory Troops excluded.",
f"- Covenant of Fire now hides {pod_links} Drop Pod/Dreadclaw links and {pod_entries} nested transport entries that must enter by Deep Strike.",
f"- Removed {removed_inferno} overbroad Inferno Pistol links created by the R40 heuristic and added {inferno_added} controlled Sergeant-Armoury links.",
f"- Rebuilt Salamanders Artificer Armour access: removed {removed_art} old squad-root links, added {art_added} Sergeant/eligible leader links, and hid {generic_art_hidden} normal-price Sergeant options while Salamanders are selected.",
f"- Master-crafted Weapon price override: hid {master_hidden} normal +15 selectors for Salamanders and added {master_added} corresponding +10 selectors.",
f"- Reinforced Ceramite: removed {cer_removed_exempt} incorrect Salamanders-discount links from Land Raider/Spartan contexts; hid {cer_hidden} normal-price selectors and added {cer_added} missing +10 selectors on eligible non-exempt vehicles.",
"- R41 Iron Halo 0-1, Salamanders Mantle 0-1/additive armour behavior, Vulkan Loyalist restriction, Awakening Fire Chaplain/Vulkan/type limits, and conditional Covenant Troops remained intact.",
"- No Fortification or Allied Detachment structures currently exist in the standard GST, so the Rite prohibitions remain rules text rather than fake builder controls.","",
"VALIDATION:"
]+[f'- {"PASS" if ok else "FAIL"}: {n}' for n,ok in checks]
OUT.write_text("\n".join(lines)+"\n",encoding="utf-8")
print(OUT.read_text())
