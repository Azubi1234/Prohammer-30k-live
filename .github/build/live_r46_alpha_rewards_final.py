from pathlib import Path
import copy, collections, hashlib, re, xml.etree.ElementTree as ET

CAT=Path("Legiones Astartes.cat"); IDX=Path("index.xml")
OUT=Path("inspection-live-r46-alpha-rewards-final.txt")
NS="http://www.battlescribe.net/schema/catalogueSchema"; INS="http://www.battlescribe.net/schema/dataIndexSchema"
ET.register_namespace("",NS)
C=lambda t:f"{{{NS}}}{t}"; I=lambda t:f"{{{INS}}}{t}"
tree=ET.parse(CAT); root=tree.getroot()
if root.get("revision")!="45":raise RuntimeError(f"R46 expected CAT45, got {root.get('revision')}")
base_ids=collections.Counter(x.get("id") for x in root.iter() if x.get("id"))
LEG="legion-xx";COILS="r25-rite-xx-0-the-coils-of-the-hydra";PECH="r41-unit-xx-7-ingo-pech";REWARD_CAT="cat-alpha-reward"

def qns(e):return e.tag.split("}")[0].strip("{")
def cont(p,tag,before=("constraints","categoryLinks","entryLinks","infoLinks","profiles","rules","selectionEntries","selectionEntryGroups","costs","modifiers")):
    q=C(tag);x=p.find(q)
    if x is not None:return x
    x=ET.Element(q);kids=list(p);idx=len(kids)
    for j,k in enumerate(kids):
        if k.tag.split("}")[-1] in before:idx=j;break
    p.insert(idx,x);return x
def cons(p,id_,typ,val,field="selections",scope="parent",child=False):
    cs=cont(p,"constraints");x=next((z for z in cs.findall(C("constraint")) if z.get("id")==id_),None)
    if x is None:x=ET.SubElement(cs,C("constraint"))
    x.attrib.update({"id":id_,"type":typ,"value":str(val),"field":field,"scope":scope,"shared":"true","includeChildSelections":"true" if child else "false","includeChildForces":"false"});return x
def cost(p,val):
    cs=cont(p,"costs",before=("modifiers",));x=next((z for z in cs.findall(C("cost")) if z.get("typeId")=="pts"),None)
    if x is None:x=ET.SubElement(cs,C("cost"),{"name":"Points","typeId":"pts"})
    x.set("value",str(val));return x
def modifier(p,id_,typ,field,value,conds):
    ms=cont(p,"modifiers");x=next((z for z in ms.findall(C("modifier")) if z.get("id")==id_),None)
    if x is None:x=ET.SubElement(ms,C("modifier"))
    x.attrib.update({"id":id_,"type":typ,"field":field,"value":str(value)})
    for ch in list(x):x.remove(ch)
    if len(conds)==1:target=ET.SubElement(x,C("conditions"))
    else:
        cgs=ET.SubElement(x,C("conditionGroups"));cg=ET.SubElement(cgs,C("conditionGroup"),{"type":"and"});target=ET.SubElement(cg,C("conditions"))
    for c in conds:
        ET.SubElement(target,C("condition"),{"type":c.get("type","atLeast"),"value":str(c.get("value",1)),"field":"selections","scope":c.get("scope","roster"),"childId":c["childId"],"shared":"true","includeChildSelections":"true","includeChildForces":"false"})
    return x
def add_rule(p,id_,name,text):
    rs=cont(p,"rules");r=next((z for z in rs.findall(C("rule")) if z.get("id")==id_),None)
    if r is None:r=ET.SubElement(rs,C("rule"))
    r.attrib.update({"id":id_,"name":name,"hidden":"false"});d=r.find(C("description"))
    if d is None:d=ET.SubElement(r,C("description"))
    d.text=text;return r
def add_infolink(p,id_,name,target,typ="rule",hidden=False):
    ils=cont(p,"infoLinks");x=next((z for z in ils.findall(C("infoLink")) if z.get("id")==id_),None)
    if x is None:x=ET.SubElement(ils,C("infoLink"))
    x.attrib.update({"id":id_,"name":name,"targetId":target,"type":typ,"hidden":"true" if hidden else "false"});return x
def group(p,id_,name,minv=None,maxv=None):
    gs=cont(p,"selectionEntryGroups",before=("costs","modifiers"));g=next((z for z in gs.findall(C("selectionEntryGroup")) if z.get("id")==id_),None)
    if g is None:g=ET.SubElement(gs,C("selectionEntryGroup"))
    g.attrib.update({"id":id_,"name":name,"hidden":"false"})
    if minv is not None:cons(g,id_+"-min","min",minv)
    if maxv is not None:cons(g,id_+"-max","max",maxv)
    return g
def sel(p,id_,name,pts=0,maxv=1):
    ss=cont(p,"selectionEntries",before=("selectionEntryGroups","costs","modifiers"));x=ET.SubElement(ss,C("selectionEntry"),{"id":id_,"name":name,"type":"upgrade","hidden":"false"})
    cost(x,pts)
    if maxv is not None:cons(x,id_+"-max","max",maxv)
    return x
def elink(p,id_,name,target,pts=0,maxv=1):
    es=cont(p,"entryLinks",before=("infoLinks","profiles","rules","selectionEntries","selectionEntryGroups","costs","modifiers"));x=ET.SubElement(es,C("entryLink"),{"id":id_,"name":name,"targetId":target,"type":"selectionEntry","import":"true","hidden":"false"})
    if pts:cost(x,pts)
    if maxv is not None:cons(x,id_+"-max","max",maxv)
    return x
def deep_prefix(e,prefix):
    x=copy.deepcopy(e);olds=[z.get("id") for z in x.iter() if z.get("id")];mp={o:prefix+o for o in olds}
    for z in x.iter():
        if z.get("id") in mp:z.set("id",mp[z.get("id")])
        for a in ("childId","targetId","field"):
            if z.get(a) in mp:z.set(a,mp[z.get(a)])
    return x
def normalize(s):
    s=(s or "").replace("’","'").replace("— Rewards of Treachery","").replace("- Rewards of Treachery","").strip()
    s=re.sub(r"^[IVXLCDM]+\s*[—-]\s*","",s,flags=re.I)
    return re.sub(r"[^a-z0-9]+"," ",s.lower()).strip()
def set_reward_categories(e):
    cs=e.find(C("categoryLinks"))
    if cs is not None:e.remove(cs)
    cs=cont(e,"categoryLinks")
    ET.SubElement(cs,C("categoryLink"),{"id":e.get("id")+"-elite","name":"Elites","targetId":"cat-elites","hidden":"false","primary":"true"})
    ET.SubElement(cs,C("categoryLink"),{"id":e.get("id")+"-reward","name":"Rewards of Treachery Limit","targetId":REWARD_CAT,"hidden":"false"})
def exact_visibility(e):
    e.set("hidden","true")
    ms=e.find(C("modifiers"))
    if ms is not None:
        for m in list(ms):
            if m.get("field")=="hidden":ms.remove(m)
    modifier(e,e.get("id")+"-show-coils","set","hidden","false",[{"childId":LEG},{"childId":COILS}])
    modifier(e,e.get("id")+"-show-pech","set","hidden","false",[{"childId":LEG},{"childId":PECH}])
def shared_rule(name):
    sr=root.find(C("sharedRules"))
    return next((x for x in sr.findall(C("rule")) if (x.get("name") or "").casefold()==name.casefold()),None)
def alpha_identity(e):
    # Remove direct old Legion rules/core effects and add Alpha Legion + selected tactic.
    rs=e.find(C("rules")); ils=e.find(C("infoLinks"))
    if rs is not None:
        for r in list(rs):
            nm=(r.get("name") or "")
            if nm.startswith("Legiones Astartes ("):rs.remove(r)
    if ils is not None:
        for i in list(ils):
            nm=(i.get("name") or "")
            if nm.startswith("Legiones Astartes ("):ils.remove(i)
    al=shared_rule("Legiones Astartes (Alpha Legion)")
    if al is None:raise RuntimeError("Alpha Legion shared rule missing")
    add_infolink(e,e.get("id")+"-alpha-legion","Legiones Astartes (Alpha Legion)",al.get("id"),"rule")
    # Dynamic tactic effect; six hidden links, exactly one shown by the army selector.
    for idx,(tid,nm) in enumerate([
        ("r46-al-mutable-0","Counter-Attack"),
        ("r46-al-mutable-1","Furious Charge"),
        ("r46-al-mutable-2","Infiltrate"),
        ("r46-al-mutable-3","Move Through Cover"),
        ("r46-al-mutable-4","Siege Specialists"),
        ("r46-al-mutable-5","Tank Hunters"),
    ]):
        rr=shared_rule(nm)
        if rr is None:raise RuntimeError("Missing shared rule "+nm)
        il=add_infolink(e,e.get("id")+f"-mutable-{idx}",nm,rr.get("id"),"rule",True)
        modifier(il,il.get("id")+"-show","set","hidden","false",[{"childId":tid}])
def original_legion_core_names(donor):
    m=re.match(r"r41-unit-([ivxlcdm]+)-",donor.get("id") or "")
    if not m:return set()
    legid="legion-"+m.group(1)
    leg=next((x for x in root.iter(C("selectionEntry")) if x.get("id")==legid),None)
    if leg is None:return set()
    names=set()
    for x in leg.findall(f"./{C('rules')}/{C('rule')}"):names.add((x.get("name") or "").casefold())
    for x in leg.findall(f"./{C('infoLinks')}/{C('infoLink')}"):names.add((x.get("name") or "").casefold())
    names.add(("Legiones Astartes ("+ (leg.get("name") or "") +")").casefold())
    return names
def strip_original_core(e,donor):
    names=original_legion_core_names(donor)
    rs=e.find(C("rules"))
    if rs is not None:
        for r in list(rs):
            nm=(r.get("name") or "").casefold()
            if nm in names or (r.get("name") or "").startswith("Legiones Astartes ("):rs.remove(r)
    ils=e.find(C("infoLinks"))
    if ils is not None:
        for i in list(ils):
            nm=(i.get("name") or "").casefold()
            if nm in names or (i.get("name") or "").startswith("Legiones Astartes ("):ils.remove(i)

ids={x.get("id"):x for x in root.iter() if x.get("id")}
roots=root.findall(f"./{C('selectionEntries')}/{C('selectionEntry')}")
rewards=[x for x in roots if (x.get("id") or "").startswith("r46-al-reward-")]
donors=[x for x in roots if not (x.get("id") or "").startswith("r46-al-reward-") and not (x.get("id") or "").startswith("r41-unit-xx-")]
by=collections.defaultdict(list)
for d in donors:by[normalize(d.get("name"))].append(d)

def choose_donor(name):
    arr=by.get(normalize(name),[])
    mains=[x for x in arr if (x.get("id") or "").startswith("r41-unit-")]
    if mains:return sorted(mains,key=lambda x:x.get("id"))[0]
    return sorted(arr,key=lambda x:x.get("id") or "")[0] if arr else None

# Clean direct original Legion core names after copy by comparing with donor's Legion selector.
rebuilt=0;unmatched=[];source_dumps=[]
parent=root.find(C("selectionEntries"))
for old in list(rewards):
    rid=old.get("id"); donor=choose_donor(old.get("name"))
    if donor is None:
        if "varagyr wolf guard terminators" in normalize(old.get("name")):
            continue
        unmatched.append((rid,old.get("name")));continue
    cp=deep_prefix(donor,rid+"-copy-");cp.set("id",rid);cp.set("name",(donor.get("name") or "").strip()+" — Rewards of Treachery")
    # Reward copy is an Elites choice and does not inherit donor roster/FoC visibility.
    cns=cp.find(C("constraints"))
    if cns is not None:
        for x in list(cns):
            if x.get("scope")=="roster":cns.remove(x)
    set_reward_categories(cp);exact_visibility(cp);strip_original_core(cp,donor);alpha_identity(cp)
    # Ensure no old text-dump survives from an otherwise finished donor.
    rs=cp.find(C("rules"))
    if rs is not None:
        for r in list(rs):
            if (r.get("name") or "").casefold()=="source entry":
                source_dumps.append((rid,donor.get("id"),donor.get("name")))
    idx=list(parent).index(old);parent.remove(old);parent.insert(idx,cp);rebuilt+=1

# Special rebuild for the one source unit that has no current Space Wolves donor root.
ids={x.get("id"):x for x in root.iter() if x.get("id")}
vr=ids.get("r46-al-reward-14")
if vr is None:raise RuntimeError("Varagyr reward entry missing")
vr.set("name","Varagyr Wolf Guard Terminators — Rewards of Treachery")
# Retain its imported stat profiles, but rebuild everything else cleanly.
for tag in ("rules","infoLinks","selectionEntryGroups","selectionEntries","entryLinks"):
    x=vr.find(C(tag))
    if x is not None:vr.remove(x)
cost(vr,25)
models=ET.SubElement(cont(vr,"selectionEntries",before=("selectionEntryGroups","costs","modifiers")),C("selectionEntry"),{"id":"r46-al-reward-14-models","name":"Varagyr Terminators (total squad size)","type":"model","hidden":"false","defaultAmount":"5"})
cost(models,45);cons(models,"r46-al-reward-14-models-min","min",5);cons(models,"r46-al-reward-14-models-max","max",10)
alpha_identity(vr)
fear=shared_rule("Fearless")
if fear is not None:add_infolink(vr,"r46-al-reward-14-fearless","Fearless",fear.get("id"),"rule")
add_rule(vr,"r46-al-reward-14-glory","Glory Seekers","At the beginning of each Assault phase, if the Varagyr are engaged with one or more enemy Independent Characters, nominate one such Character. Any Varagyr able to direct attacks against that Character must do so. Each Varagyr attacking the nominated Character may re-roll one failed To Hit roll during that Assault phase.")
add_rule(vr,"r46-al-reward-14-jarl","Chosen of the Jarl","The original Space Wolves rule permits a Space Wolves Praetor in Terminator Armour to take the unit as a retinue. As a Rewards of Treachery unit in an Alpha Legion army, this retained rule has no eligible Space Wolves Praetor and therefore does not create an Alpha Legion retinue option.")
add_rule(vr,"r46-al-reward-14-wg","Wargear","Cataphractii Terminator Armour, Combi-bolter, and either a Frost Blade or Frost Axe.")
# any-model ranged replacements
rg=group(vr,"r46-al-reward-14-ranged","Replace Combi-bolter — any model",0,None)
mx=cons(rg,"r46-al-reward-14-ranged-max","max",0);modifier(rg,"r46-al-reward-14-ranged-dyn","increment",mx.get("id"),1,[{"childId":models.get("id"),"scope":"root-entry"}])
def target_by_name(name):
    exact=[x for x in root.iter(C("selectionEntry")) if (x.get("name") or "").casefold()==name.casefold()]
    pref=[x for x in exact if (x.get("id") or "").startswith(("gear-","fa-gear-","r41-universal-gear-","r63-sw-gear-"))]
    return (pref[0] if pref else exact[0]).get("id") if exact else None
for nm,pts in [("Foeblaster Boltgun",5),("Combi-Flamer",10),("Combi-Volkite Charger",10),("Combi-Meltagun",15),("Combi-Plasma Gun",15)]:
    tid=target_by_name(nm)
    if tid:elink(rg,"r46-al-reward-14-r-"+re.sub(r"[^a-z0-9]+","-",nm.lower()).strip("-"),nm,tid,pts,10)
mg=group(vr,"r46-al-reward-14-melee","Replace Frost Blade or Frost Axe — any model",0,None)
mx=cons(mg,"r46-al-reward-14-melee-max","max",0);modifier(mg,"r46-al-reward-14-melee-dyn","increment",mx.get("id"),1,[{"childId":models.get("id"),"scope":"root-entry"}])
for nm,pts in [("Power Fist",5),("Chainfist",10),("Thunder Hammer",10)]:
    tid=target_by_name(nm)
    if tid:elink(mg,"r46-al-reward-14-m-"+re.sub(r"[^a-z0-9]+","-",nm.lower()).strip("-"),nm,tid,pts,10)
hg=group(vr,"r46-al-reward-14-heavy","Heavy weapon — one per five models",0,None)
hmax=cons(hg,"r46-al-reward-14-heavy-max","max",0);modifier(hg,"r46-al-reward-14-heavy-dyn","increment",hmax.get("id"),1,[{"childId":models.get("id"),"scope":"root-entry","value":5}])
for nm,pts in [("Heavy Flamer",10),("Reaper Autocannon",15),("Assault Cannon",20)]:
    tid=target_by_name(nm)
    if tid:elink(hg,"r46-al-reward-14-h-"+re.sub(r"[^a-z0-9]+","-",nm.lower()).strip("-"),nm,tid,pts,2)
tg=group(vr,"r46-al-reward-14-thegn","Varagyr Thegn",0,1)
up=sel(tg,"r46-al-reward-14-thegn-up","Upgrade one Varagyr to Thegn",25,1)
gh=target_by_name("Grenade Harness")
if gh:elink(tg,"r46-al-reward-14-grenade","Grenade Harness",gh,10,1)
add_rule(tg,"r46-al-reward-14-thegn-arm","Thegn Armoury","The Varagyr Thegn may select up to 50 points of permitted weapons and wargear from the Space Marine Armoury and Space Wolves Armoury. This Rewards copy retains that source option; Legion-gated Space Wolves generic items remain unavailable unless explicitly present on the unit.")
tr=group(vr,"r46-al-reward-14-transport","Dedicated Transport",0,1)
for nm,tid in [("Dreadclaw Drop Pod","transport-dreadclaw"),("Spartan Assault Tank","hs-spartan")]:
    if tid in ids:elink(tr,"r46-al-reward-14-"+re.sub(r"[^a-z]+","-",nm.lower()),nm,tid,0,1)
lr=group(tr,"r46-al-reward-14-land-raider","Land Raider",0,1)
for nm,tid in [("Land Raider Phobos","hs-lr-phobos"),("Land Raider Proteus","hs-lr-proteus"),("Land Raider Achilles","hs-lr-achilles")]:
    if tid in ids:elink(lr,"r46-al-reward-14-"+re.sub(r"[^a-z]+","-",nm.lower()),nm,tid,0,1)
set_reward_categories(vr);exact_visibility(vr)

# Add a clean choice for Coils' Subterfuge instead of leaving the player to track it in prose.
ids={x.get("id"):x for x in root.iter() if x.get("id")}
co=ids[COILS]
gs=co.find(C("selectionEntryGroups"))
if gs is not None:
    for g in list(gs):
        if g.get("id")=="r46-coils-subterfuge-choice":gs.remove(g)
sg=group(co,"r46-coils-subterfuge-choice","Subterfuge — choose one before first-turn dice",1,1)
a=sel(sg,"r46-coils-subterfuge-plus1","+1 to the roll to determine who takes the first turn",0,1)
b=sel(sg,"r46-coils-subterfuge-seize","Re-roll a failed Seize the Initiative attempt",0,1)

# Revision
root.set("revision","46")
tree.write(CAT,encoding="utf-8",xml_declaration=True)
ET.register_namespace("",INS);it=ET.parse(IDX);ir=it.getroot()
for x in ir.iter(I("dataIndexEntry")):
    if x.get("filePath")=="Legiones Astartes.cat":x.set("dataRevision","46")
it.write(IDX,encoding="utf-8",xml_declaration=True)

# Validation
rr=ET.parse(CAT).getroot();rids={x.get("id"):x for x in rr.iter() if x.get("id")};checks=[]
def ck(n,o):
    checks.append((n,bool(o)))
    if not o:raise RuntimeError("R46 validation failed: "+n)
ck("CAT46",rr.get("revision")=="46")
ck("GST dependency remains 10",rr.get("gameSystemRevision")=="10")
ck("Index46",'dataRevision="46"' in IDX.read_text(encoding="utf-8"))
reward_after=[x for x in rr.findall(f"./{C('selectionEntries')}/{C('selectionEntry')}") if (x.get("id") or "").startswith("r46-al-reward-")]
ck("62 Rewards remain",len(reward_after)==62)
ck("61 donor Rewards rebuilt",rebuilt==61)
ck("No unmatched Rewards",not unmatched)
ck("No donor Source Entry dumps",not source_dumps)
# All Rewards title/readable, gated, Elites, Alpha Legion, no direct old named Legion.
for rw in reward_after:
    letters=re.sub(r"[^A-Za-z]","",rw.get("name") or "")
    ck(rw.get("id")+" readable name",not (len(letters)>3 and letters==letters.upper()))
    txt=ET.tostring(rw,encoding="unicode")
    ck(rw.get("id")+" Coils/Pech gated",rw.get("hidden")=="true" and COILS in txt and PECH in txt)
    ck(rw.get("id")+" Elites primary",any(c.get("targetId")=="cat-elites" and c.get("primary")=="true" for c in rw.findall(f"./{C('categoryLinks')}/{C('categoryLink')}")))
    ck(rw.get("id")+" reward limit",any(c.get("targetId")==REWARD_CAT for c in rw.findall(f"./{C('categoryLinks')}/{C('categoryLink')}")))
    direct_names=[(x.get("name") or "") for x in rw.findall(f"./{C('rules')}/{C('rule')}")]+[(x.get("name") or "") for x in rw.findall(f"./{C('infoLinks')}/{C('infoLink')}")]
    ck(rw.get("id")+" Alpha Legion rule",any(n=="Legiones Astartes (Alpha Legion)" for n in direct_names))
    ck(rw.get("id")+" no foreign named Legion",not any(n.startswith("Legiones Astartes (") and n!="Legiones Astartes (Alpha Legion)" for n in direct_names))
    ck(rw.get("id")+" no Source Entry",not any(n=="Source Entry" for n in direct_names))
# Mutable tactic still exact
leg=rids[LEG];m=next(g for g in leg.findall(f"./{C('selectionEntryGroups')}/{C('selectionEntryGroup')}") if g.get("id")=="r46-al-mutable-tactics")
ck("Mutable Tactics still six",len(m.findall(f"./{C('selectionEntries')}/{C('selectionEntry')}"))==6)
ck("Coils Subterfuge selector exists","r46-coils-subterfuge-choice" in rids or any(g.get("id")=="r46-coils-subterfuge-choice" for g in rr.iter(C("selectionEntryGroup"))))
# Links resolve
allids=set(rids);bad=[]
for e in rr.iter():
    if not (e.get("id") or "").startswith("r46"):continue
    if e.tag not in (C("entryLink"),C("infoLink")):continue
    t=e.get("targetId")
    if t and t not in allids and not t.startswith(("cat-","r40-","r41-","r42-","r43-","r45-")):bad.append((e.get("id"),t))
ck("R46 direct links resolve",not bad)
new=collections.Counter(x.get("id") for x in rr.iter() if x.get("id"));worse={k:v for k,v in new.items() if v>max(1,base_ids.get(k,0))}
ck("No new/worsened duplicate IDs",not worse)

OUT.write_text("\n".join([
"Live R46 — Alpha Legion Rewards of Treachery finalisation",
"Input CAT=45 -> CAT=46; GST remains revision 10","",
"REWARDS OF TREACHERY:",
f"- Rebuilt {rebuilt} Rewards entries directly from the current finished donor-unit roots, preserving their current profiles, options and unit-specific rules.",
"- Replaced each donor's original named Legiones Astartes/core Legion package with Legiones Astartes (Alpha Legion).",
"- Every Rewards unit dynamically references the one selected Mutable Tactic using the same canonical shared rule; no separate tactic copies were created.",
"- Every Rewards entry is Elites, shares the single Rewards of Treachery 0-1 limit, and is hidden unless Coils of the Hydra or Ingo Pech's Master of Deceit enables it.",
"- Normalised Rewards unit names out of legacy ALL-CAPS presentation.",
"- Rebuilt the only donor absent from the current root catalogue, Varagyr Wolf Guard Terminators, from its source entry with real profiles/options/rules instead of a Source Entry dump.","",
"COILS OF THE HYDRA:",
"- Added an explicit mandatory Subterfuge 1-of-2 selector: +1 to the first-turn roll OR re-roll a failed Seize the Initiative attempt.",
"- Existing R45 three-compulsory-Troops, non-Vigilator Consul cap and Mutable Tactics interaction remain intact.","",
"VALIDATION:"
]+[f'- {"PASS" if ok else "FAIL"}: {n}' for n,ok in checks])+"\n",encoding="utf-8")
print(OUT.read_text())
