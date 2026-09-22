from pathlib import Path
import copy, collections, hashlib, re, xml.etree.ElementTree as ET

CAT=Path("Legiones Astartes.cat"); GST=Path("Prohammer 30k.gst"); IDX=Path("index.xml"); OUT=Path("inspection-live-r46-alpha-rewards.txt")
CNS="http://www.battlescribe.net/schema/catalogueSchema"; GNS="http://www.battlescribe.net/schema/gameSystemSchema"; INS="http://www.battlescribe.net/schema/dataIndexSchema"
ET.register_namespace("",CNS)
C=lambda t:f"{{{CNS}}}{t}"; G=lambda t:f"{{{GNS}}}{t}"; I=lambda t:f"{{{INS}}}{t}"
ct=ET.parse(CAT);cr=ct.getroot();gt=ET.parse(GST);gr=gt.getroot()
if cr.get("revision")!="45":raise RuntimeError(f"R46 expected CAT45, got {cr.get('revision')}")
if gr.get("revision")!="10":raise RuntimeError(f"R46 expected GST10, got {gr.get('revision')}")
baseline=collections.Counter(x.get("id") for x in cr.iter() if x.get("id"))
LEG="legion-xx";COILS="r25-rite-xx-0-the-coils-of-the-hydra";PECH="r41-unit-xx-7-ingo-pech";CAT_REWARD="cat-alpha-reward"
TACTICS=[("r46-al-mutable-0","Counter-Attack"),("r46-al-mutable-1","Furious Charge"),("r46-al-mutable-2","Infiltrate"),("r46-al-mutable-3","Move Through Cover"),("r46-al-mutable-4","Siege Specialists"),("r46-al-mutable-5","Tank Hunters")]

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
def clear_constraints(p,typ=None,scope=None):
    cs=p.find(C("constraints"))
    if cs is None:return
    for x in list(cs):
        if (typ is None or x.get("type")==typ) and (scope is None or x.get("scope")==scope):cs.remove(x)
def modifier(p,id_,typ,field,value,conditions=None):
    ns=qns(p);ms=cont(p,"modifiers");q=f"{{{ns}}}modifier";x=next((z for z in ms.findall(q) if z.get("id")==id_),None)
    if x is None:x=ET.SubElement(ms,q)
    x.attrib.update({"id":id_,"type":typ,"field":field,"value":str(value)})
    for ch in list(x):x.remove(ch)
    if conditions:
        if len(conditions)==1:target=ET.SubElement(x,f"{{{ns}}}conditions")
        else:
            cgs=ET.SubElement(x,f"{{{ns}}}conditionGroups");cg=ET.SubElement(cgs,f"{{{ns}}}conditionGroup",{"type":"and"});target=ET.SubElement(cg,f"{{{ns}}}conditions")
        for c in conditions:
            ET.SubElement(target,f"{{{ns}}}condition",{"type":c.get("type","atLeast"),"value":str(c.get("value",1)),"field":c.get("field","selections"),"scope":c.get("scope","roster"),"childId":c["childId"],"shared":"true","includeChildSelections":"true" if c.get("includeChildSelections",True) else "false","includeChildForces":"false"})
    return x
def add_infolink(p,id_,name,target,typ="rule",hidden=False):
    ils=cont(p,"infoLinks");x=next((z for z in ils.findall(C("infoLink")) if z.get("id")==id_),None)
    if x is None:x=ET.SubElement(ils,C("infoLink"))
    x.attrib.update({"id":id_,"name":name,"targetId":target,"type":typ,"hidden":"true" if hidden else "false"});return x
def elink(p,id_,name,target,pts=0,maxv=1,hidden=False):
    es=cont(p,"entryLinks",before=("infoLinks","profiles","rules","selectionEntries","selectionEntryGroups","costs","modifiers"));e=next((z for z in es.findall(C("entryLink")) if z.get("id")==id_),None)
    if e is None:e=ET.SubElement(es,C("entryLink"))
    e.attrib.update({"id":id_,"name":name,"targetId":target,"type":"selectionEntry","import":"true","hidden":"true" if hidden else "false"})
    if pts:
        cs=cont(e,"costs",before=("modifiers",));ET.SubElement(cs,C("cost"),{"name":"Points","typeId":"pts","value":str(pts)})
    if maxv is not None:cons(e,id_+"-max","max",maxv)
    return e
def catlink(p,id_,name,target,primary=False):
    cs=cont(p,"categoryLinks");x=next((z for z in cs.findall(C("categoryLink")) if z.get("id")==id_),None)
    if x is None:x=ET.SubElement(cs,C("categoryLink"))
    x.attrib.update({"id":id_,"name":name,"targetId":target,"hidden":"false"})
    if primary:x.set("primary","true")
    return x
def deep_prefix(e,prefix):
    x=copy.deepcopy(e);olds=[z.get("id") for z in x.iter() if z.get("id")];mp={o:prefix+o for o in olds}
    for z in x.iter():
        if z.get("id") in mp:z.set("id",mp[z.get("id")])
        for a in ("childId","targetId","field"):
            if z.get(a) in mp:z.set(a,mp[z.get(a)])
    return x
def norm(s):
    s=(s or "").replace("’","'").replace("— Rewards of Treachery","").replace("- Rewards of Treachery","")
    s=re.sub(r"^[IVXLCDM]+\s*[—-]\s*","",s,flags=re.I)
    return re.sub(r"[^a-z0-9]+"," ",s.lower()).strip()
def simple_name(s):
    s=re.sub(r"\s*[—-]\s*Rewards of Treachery\s*$","",s or "",flags=re.I)
    # Make old all-caps reward titles readable using donor's current title instead later.
    return s
def direct_names(e):
    return {(x.get("name") or "").casefold() for x in e.findall(f"./{C('rules')}/{C('rule')}")} | {(x.get("name") or "").casefold() for x in e.findall(f"./{C('infoLinks')}/{C('infoLink')}")}
def source_dump_text(e):
    for r in e.findall(f"./{C('rules')}/{C('rule')}"):
        if (r.get("name") or "")=="Source Entry":return r.findtext(C("description")) or ""
    return ""
def strip_hidden_mods(e):
    ms=e.find(C("modifiers"))
    if ms is not None:
        for m in list(ms):
            if m.get("field")=="hidden":ms.remove(m)
def allegiance_reqs(e):
    out=[]
    ms=e.find(C("modifiers"))
    if ms is not None:
        for c in ms.iter(C("condition")):
            if c.get("childId") in ("allegiance-loyalist","allegiance-traitor"):out.append(c.get("childId"))
    # Preserve only one if source actually has one.
    return sorted(set(out))
def has_named_la(e):
    for x in list(e.findall(f"./{C('rules')}/{C('rule')}"))+list(e.findall(f"./{C('infoLinks')}/{C('infoLink')}")):
        if re.match(r"^Legiones Astartes \(.+\)$",x.get("name") or "",re.I):return True
    return False
def set_reward_categories(e):
    cs=e.find(C("categoryLinks"))
    if cs is not None:e.remove(cs)
    catlink(e,e.get("id")+"-elite","Elites","cat-elites",True)
    catlink(e,e.get("id")+"-reward-limit","Rewards of Treachery Limit",CAT_REWARD,False)
def strip_roster_limits(e):
    clear_constraints(e,scope="roster")
def reward_visibility(e,loyalty):
    e.set("hidden","true");strip_hidden_mods(e)
    base=[{"childId":LEG},{"childId":COILS}]
    if loyalty:base.append({"childId":loyalty})
    modifier(e,e.get("id")+"-show-coils","set","hidden","false",base)
    base=[{"childId":LEG},{"childId":PECH}]
    if loyalty:base.append({"childId":loyalty})
    modifier(e,e.get("id")+"-show-pech","set","hidden","false",base)

ids={x.get("id"):x for x in cr.iter() if x.get("id")}

# Repair three legacy universal-gear target IDs still used by a few donor entries.
# These are catalogue-wide stale links, so fix the source entries before Rewards cloning.
LEGACY_TARGET_MAP={
    "gear-artificer-armour":"gear-hq-artificer",
    "gear-thunder-hammer":"gear-thunder",
    "gear-rotor-cannon":"gear-rotor",
}
legacy_target_repairs=0
for link in cr.iter(C("entryLink")):
    old=link.get("targetId")
    if old in LEGACY_TARGET_MAP:
        new=LEGACY_TARGET_MAP[old]
        if new not in ids:raise RuntimeError(f"Replacement target {new} missing for {old}")
        link.set("targetId",new);legacy_target_repairs+=1
ids={x.get("id"):x for x in cr.iter() if x.get("id")}

shared_rules=cr.find(C("sharedRules"))
def shared_rule(name):
    x=next((z for z in shared_rules.findall(C("rule")) if (z.get("name") or "").casefold()==name.casefold()),None)
    if x is None:raise RuntimeError("Missing shared rule "+name)
    return x
AL_LA=shared_rule("Legiones Astartes (Alpha Legion)"); HUB=shared_rule("Martial Hubris")
TACTIC_RULES={n:shared_rule(n) for _,n in TACTICS}

# Clean two legacy duplicate retinue groups identified by R45 child audit.
legacy_ret_removed=0
for eid in ["r41-unit-xx-4-armillus-dynat","r41-unit-xx-7-ingo-pech"]:
    e=ids[eid];gs=e.find(C("selectionEntryGroups"))
    if gs is not None:
        for g in list(gs):
            if (g.get("id") or "").startswith("live-r2-") and "retinue" in (g.get("name") or "").lower():
                gs.remove(g);legacy_ret_removed+=1

# Main top-level donor pool. Prefer r41-unit roots; later Legion-specific rebuilt roots are fallback for Varagyr.
root_container=cr.find(C("selectionEntries"));roots=root_container.findall(C("selectionEntry"))
main_donors=[e for e in roots if (e.get("id") or "").startswith("r41-unit-") and not (e.get("id") or "").startswith("r41-unit-xx-")]
all_nonreward=[e for e in roots if not (e.get("id") or "").startswith("r46-al-reward-") and not (e.get("id") or "").startswith("r41-unit-xx-")]

def find_donor(rw):
    key=norm(rw.get("name"))
    exact=[e for e in main_donors if norm(e.get("name"))==key]
    if len(exact)==1:return exact[0]
    if len(exact)>1:
        exact=sorted(exact,key=lambda e:(not (e.get("id") or "").startswith("r41-unit-"),len(e.get("id") or "")))
        return exact[0]
    # Varagyr renamed in later rebuild.
    if "varagyr" in key:
        cand=[e for e in all_nonreward if "varagyr" in norm(e.get("name")) and "retinue" not in norm(e.get("name"))]
        if cand:return sorted(cand,key=lambda e:(0 if (e.get("id") or "").startswith("r63-sw-varagyr") else 1,len(e.get("id") or "")))[0]
    return None

# Donor Legion selector/core rule metadata.
def legion_token(eid):
    m=re.match(r"r41-unit-([ivxlcdm]+)-",eid or "",re.I)
    if m:return m.group(1).lower()
    if (eid or "").startswith("r63-sw-"):return "vi"
    return None
def core_meta(tok):
    sel=ids.get("legion-"+tok)
    names=set();targets=set()
    if sel is not None:
        for x in sel.findall(f"./{C('rules')}/{C('rule')}"):names.add((x.get("name") or "").casefold())
        for x in sel.findall(f"./{C('infoLinks')}/{C('infoLink')}"):
            names.add((x.get("name") or "").casefold());targets.add(x.get("targetId"))
    return names,targets

# Remove direct donor core effects from a cloned node while retaining unit-listed fixed rules/equipment.
def transform_node(node,donor_core_names,donor_core_targets,old_source_text,add_alpha=False):
    had=False
    rs=node.find(C("rules"))
    if rs is not None:
        for r in list(rs):
            nm=r.get("name") or "";ncf=nm.casefold()
            if nm=="Source Entry":rs.remove(r);continue
            if re.match(r"^Legiones Astartes \(.+\)$",nm,re.I):
                rs.remove(r);had=True;continue
            if ncf in donor_core_names and nm.lower() not in old_source_text.lower():
                rs.remove(r)
    ils=node.find(C("infoLinks"))
    if ils is not None:
        for il in list(ils):
            nm=il.get("name") or "";ncf=nm.casefold()
            if re.match(r"^Legiones Astartes \(.+\)$",nm,re.I):
                ils.remove(il);had=True;continue
            if (ncf in donor_core_names or il.get("targetId") in donor_core_targets) and nm.lower() not in old_source_text.lower():
                ils.remove(il)
    if had or add_alpha:
        add_infolink(node,node.get("id")+"-al-la","Legiones Astartes (Alpha Legion)",AL_LA.get("id"),"rule")
    return had

def uniquify_cloned_modifier_ids(e):
    """Fix duplicate modifier IDs inherited from donor roots.
    Modifier IDs are not link targets; suffixing repeated occurrences is safe.
    Any duplicate non-modifier ID is treated as a real structural error."""
    seen={}; fixed=0
    for x in e.iter():
        oid=x.get("id")
        if not oid: continue
        n=seen.get(oid,0); seen[oid]=n+1
        if n==0: continue
        if x.tag!=C("modifier"):
            raise RuntimeError(f"Duplicate non-modifier ID inherited in {e.get('id')}: {oid} on {x.tag}")
        x.set("id",f"{oid}-dup{n+1}"); fixed+=1
    return fixed

def add_alpha_root_rules(e):
    # Martial Hubris is an Alpha Legion army rule affecting this unit.
    if "martial hubris" not in direct_names(e):add_infolink(e,e.get("id")+"-al-hubris","Martial Hubris",HUB.get("id"),"rule")
    existing=direct_names(e)
    for tid,n in TACTICS:
        if n.casefold() in existing:continue
        il=add_infolink(e,e.get("id")+"-mutable-"+tid,n,TACTIC_RULES[n].get("id"),"rule",True)
        modifier(il,il.get("id")+"-show","set","hidden","false",[{"childId":tid,"scope":"roster"}])

# Reward rebuild.
old_rewards=[e for e in list(root_container.findall(C("selectionEntry"))) if (e.get("id") or "").startswith("r46-al-reward-")]
if len(old_rewards)!=62:raise RuntimeError(f"Expected 62 rewards, found {len(old_rewards)}")
rebuilt=[];no_donor=[];la_units=0;term_units=0;loyalty_kept=0
for old in old_rewards:
    rid=old.get("id");src_text=source_dump_text(old);don=find_donor(old)
    if don is None:
        no_donor.append((rid,old.get("name")));continue
    tok=legion_token(don.get("id"));core_names,core_targets=core_meta(tok) if tok else (set(),set())
    loyalty=allegiance_reqs(don);loy=loyalty[0] if len(loyalty)==1 else None
    if loy:loyalty_kept+=1
    donor_la=has_named_la(don)
    cp=deep_prefix(don,rid+"-donor-");cp.set("id",rid);cp.set("name",(don.get("name") or simple_name(old.get("name")))+" — Rewards of Treachery")
    strip_roster_limits(cp);set_reward_categories(cp);reward_visibility(cp,loy)
    # Transform every nested selection entry: donor named LA becomes Alpha LA;
    # donor inherited core rules are removed unless the old reward source explicitly listed them.
    for node in [cp]+list(cp.iter(C("selectionEntry"))):
        transform_node(node,core_names,core_targets,src_text,add_alpha=(node is cp and donor_la))
    if donor_la:
        la_units+=1;add_alpha_root_rules(cp)
        xmltxt=ET.tostring(cp,encoding="unicode").lower()
        if "terminator armour" in xmltxt or "cataphractii" in xmltxt or "tartaros" in xmltxt:
            # Entire-unit Terminator check: special unit roots using Terminator armour.
            n=(don.get("name") or "").lower()
            likely_all=any(k in n for k in ["terminator","firedrake","deathshroud","grave warden","gorgon","morlock","red butcher","crimson paladin","sekhmet","justaerin","deliverer","contekar","dominator cohort","varagyr"])
            if likely_all:
                if not any(x.get("targetId")=="r46-al-trans-unit" for x in cp.iter(C("entryLink"))):
                    l=elink(cp,rid+"-al-trans","Teleportation Transponders","r46-al-trans-unit",0,1,False)
                term_units+=1
    # Donor roots may contain old duplicated modifier IDs; make each clone structurally unique.
    uniquify_cloned_modifier_ids(cp)
    # replace old in the same root position
    pos=list(root_container).index(old);root_container.remove(old);root_container.insert(pos,cp);rebuilt.append((rid,don.get("id"),don.get("name"),donor_la,loy))

if no_donor:raise RuntimeError("Missing Rewards donors: "+repr(no_donor))

# One more cleanup on reward copies: root category and top-level duplicate Source Entry guarantee.
ids={x.get("id"):x for x in cr.iter() if x.get("id")}
for rid,_,_,_,_ in rebuilt:
    rw=ids[rid]
    for r in rw.iter(C("rule")):
        if (r.get("name") or "")=="Source Entry":raise RuntimeError(f"{rid} donor still contains Source Entry: {r.get('id')}")

# Revision
cr.set("revision","46");cr.set("gameSystemRevision","11");gr.set("revision","11")
ct.write(CAT,encoding="utf-8",xml_declaration=True);ET.register_namespace("",GNS);gt.write(GST,encoding="utf-8",xml_declaration=True)
ET.register_namespace("",INS);it=ET.parse(IDX);ir=it.getroot()
for x in ir.iter(I("dataIndexEntry")):
    if x.get("filePath")=="Legiones Astartes.cat":x.set("dataRevision","46")
    if x.get("filePath")=="Prohammer 30k.gst":x.set("dataRevision","11")
it.write(IDX,encoding="utf-8",xml_declaration=True)

# Validation
rr=ET.parse(CAT).getroot();gg=ET.parse(GST).getroot();rids={x.get("id"):x for x in rr.iter() if x.get("id")};gids={x.get("id") for x in gg.iter() if x.get("id")};checks=[]
def ck(n,o):
    checks.append((n,bool(o)))
    if not o:raise RuntimeError("R46 validation failed: "+n)
ck("CAT46",rr.get("revision")=="46");ck("GST11",gg.get("revision")=="11");ck("CAT->GST11",rr.get("gameSystemRevision")=="11")
idx=IDX.read_text(encoding="utf-8");ck("Index46/11",'dataRevision="46"' in idx and 'dataRevision="11"' in idx)
rewards=[e for e in rr.findall(f"./{C('selectionEntries')}/{C('selectionEntry')}") if (e.get("id") or "").startswith("r46-al-reward-")]
ck("62 Rewards rebuilt",len(rewards)==62 and len(rebuilt)==62)
ck("No Source Entry anywhere in Rewards",not any((x.get("name") or "")=="Source Entry" for e in rewards for x in e.iter(C("rule"))))
# Each reward root is Elites + shared reward limit.
ck("All Rewards are Elites",all(any(c.get("targetId")=="cat-elites" and c.get("primary")=="true" for c in e.findall(f"./{C('categoryLinks')}/{C('categoryLink')}")) for e in rewards))
ck("All Rewards share one-per-army category",all(any(c.get("targetId")==CAT_REWARD for c in e.findall(f"./{C('categoryLinks')}/{C('categoryLink')}")) for e in rewards))
# Visibility gated by Coils/Pech and Alpha.
ck("All Rewards gated to Coils or Pech",all(LEG in ET.tostring(e.find(C("modifiers")),encoding="unicode") and COILS in ET.tostring(e.find(C("modifiers")),encoding="unicode") and PECH in ET.tostring(e.find(C("modifiers")),encoding="unicode") for e in rewards))
# Named donor LA must be absent at root; Alpha LA present when donor had LA.
bad_donor_la=[];bad_alpha=[]
meta={rid:(dla,loy) for rid,_,_,dla,loy in rebuilt}
for e in rewards:
    nms=[(x.get("name") or "") for x in list(e.findall(f"./{C('rules')}/{C('rule')}"))+list(e.findall(f"./{C('infoLinks')}/{C('infoLink')}"))]
    if any(re.match(r"^Legiones Astartes \((?!Alpha Legion).+\)$",n,re.I) for n in nms):bad_donor_la.append(e.get("id"))
    if meta[e.get("id")][0] and "Legiones Astartes (Alpha Legion)" not in nms:bad_alpha.append(e.get("id"))
ck("No donor Legiones Astartes remains on Reward roots",not bad_donor_la)
ck("Alpha LA installed on eligible Rewards",not bad_alpha)
# Current-unit real model profile present.
ck("All Rewards retain model profiles",all(any(p.get("typeId")=="prof-model" for p in e.iter(C("profile"))) for e in rewards))
# Native old retinue duplicates removed.
for eid in ["r41-unit-xx-4-armillus-dynat","r41-unit-xx-7-ingo-pech"]:
    ck(eid+" legacy retinue removed",not any((g.get("id") or "").startswith("live-r2-") and "retinue" in (g.get("name") or "").lower() for g in rids[eid].findall(f"./{C('selectionEntryGroups')}/{C('selectionEntryGroup')}")))
# All R46 reward links resolve.
bad=[]
for e in rewards:
    for x in list(e.iter(C("entryLink")))+list(e.iter(C("infoLink"))):
        t=x.get("targetId")
        if t and t not in rids and t not in gids:bad.append((e.get("id"),x.get("id"),t))
print("UNRESOLVED_REWARD_TARGETS", repr(bad[:300]))
ck("All Reward entry/info targets resolve",not bad)
new=collections.Counter(x.get("id") for x in rr.iter() if x.get("id"));worse={k:v for k,v in new.items() if v>max(1,baseline.get(k,0))}
print("WORSE_IDS", repr(worse))
ck("No new/worsened duplicate IDs",not worse)

lines=[
"Live R46 — Alpha Legion Rewards of Treachery rebuild",
"Input CAT=45/GST=10 -> CAT=46/GST=11","",
"REWARDS OF TREACHERY:",
f"- Rebuilt all {len(rebuilt)} Rewards entries from the current live donor units instead of the stale imported copies.",
"- Every Reward is an Elites choice and shares the army-wide one-Rewards-unit limit.",
"- Rewards appear only when The Coils of the Hydra is selected or Ingo Pech is present.",
f"- {la_units} donor units with a named Legiones Astartes rule were converted to Legiones Astartes (Alpha Legion), receive Martial Hubris and dynamically display the selected Mutable Tactic.",
"- Donor core Legion rules are stripped unless the unit's own old source entry explicitly listed that rule/equipment; unit-specific rules/options are retained.",
f"- Preserved explicit donor allegiance gates on {loyalty_kept} Rewards where the current donor unit has a Loyalist/Traitor availability condition.",
f"- Added Alpha Legion Teleportation Transponders to {term_units} eligible all-Terminator Rewards units.",
"- Current donor stat profiles/options replace the old Source Entry-era clones; no Reward contains a Source Entry dump.",
f"- Repaired {legacy_target_repairs} legacy catalogue links using retired Artificer Armour / Thunder Hammer / Rotor Cannon target IDs before cloning.","",
"NATIVE CLEANUP:",
f"- Removed {legacy_ret_removed} obsolete imported retinue group(s) left beside the new Dynat/Pech retinue selectors.","",
"VALIDATION:"
]+[f'- {"PASS" if ok else "FAIL"}: {n}' for n,ok in checks]
OUT.write_text("\n".join(lines)+"\n",encoding="utf-8");print(OUT.read_text())
