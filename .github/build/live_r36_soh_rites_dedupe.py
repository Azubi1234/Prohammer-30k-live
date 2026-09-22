from pathlib import Path
import ast, re, hashlib, xml.etree.ElementTree as ET

CAT=Path("Legiones Astartes.cat")
GST=Path("Prohammer 30k.gst")
IDX=Path("index.xml")
OUT=Path("inspection-live-r36-soh-rites-rule-dedupe-names.txt")
R34=Path(".github/build/live_r34_rules_soh_names.py")

CNS="http://www.battlescribe.net/schema/catalogueSchema"
GNS="http://www.battlescribe.net/schema/gameSystemSchema"
INS="http://www.battlescribe.net/schema/dataIndexSchema"
C=lambda t:f"{{{CNS}}}{t}"
G=lambda t:f"{{{GNS}}}{t}"
I=lambda t:f"{{{INS}}}{t}"

ct=ET.parse(CAT); cr=ct.getroot()
gt=ET.parse(GST); gr=gt.getroot()
if cr.get("revision")!="35": raise RuntimeError(f"R36 expected CAT 35, got {cr.get('revision')}")
if gr.get("revision")!="1": raise RuntimeError(f"R36 expected GST 1, got {gr.get('revision')}")

# ----------------------------------------------------------------------
# Helpers
# ----------------------------------------------------------------------
def container(parent, tag, ns=CNS, before=()):
    q=f"{{{ns}}}{tag}"
    x=parent.find(q)
    if x is not None: return x
    x=ET.Element(q)
    kids=list(parent)
    idx=len(kids)
    if before:
        for j,k in enumerate(kids):
            if k.tag.split("}")[-1] in before:
                idx=j; break
    parent.insert(idx,x)
    return x

def constraint(parent,id_,typ,val,field="selections",scope="parent",inc=True):
    cs=container(parent,"constraints", parent.tag.split("}")[0].strip("{") if "}" in parent.tag else CNS,
                 before=("categoryLinks","entryLinks","infoLinks","profiles","rules","selectionEntries","selectionEntryGroups","costs"))
    ns=parent.tag.split("}")[0].strip("{")
    q=f"{{{ns}}}constraint"
    old=next((x for x in cs.findall(q) if x.get("id")==id_),None)
    if old is None:
        old=ET.SubElement(cs,q)
    old.attrib.update({"id":id_,"type":typ,"value":str(val),"field":field,"scope":scope,"shared":"true","includeChildSelections":"true" if inc else "false","includeChildForces":"false"})
    return old

def modifier(parent,id_,typ,field,value,conds=None,repeats=None,ns=CNS):
    ms=container(parent,"modifiers",ns,before=("constraints","categoryLinks","entryLinks","infoLinks","profiles","rules","selectionEntries","selectionEntryGroups","costs"))
    m=next((x for x in ms.findall(f"{{{ns}}}modifier") if x.get("id")==id_),None)
    if m is None: m=ET.SubElement(ms,f"{{{ns}}}modifier")
    m.attrib.update({"id":id_,"type":typ,"field":field,"value":str(value)})
    for ch in list(m): m.remove(ch)
    if repeats:
        rs=ET.SubElement(m,f"{{{ns}}}repeats")
        for rp in repeats:
            ET.SubElement(rs,f"{{{ns}}}repeat",{
                "field":rp.get("field","selections"),"scope":rp.get("scope","force"),"value":str(rp.get("value",1)),
                "shared":"true","childId":rp["childId"],"includeChildSelections":"true" if rp.get("includeChildSelections",False) else "false",
                "includeChildForces":"false","repeats":str(rp.get("repeats",1)),"roundUp":"true" if rp.get("roundUp",False) else "false"
            })
    if conds:
        if len(conds)==1:
            cs=ET.SubElement(m,f"{{{ns}}}conditions")
            c=conds[0]
            ET.SubElement(cs,f"{{{ns}}}condition",{
                "type":c.get("type","atLeast"),"value":str(c.get("value",1)),"field":c.get("field","selections"),
                "scope":c.get("scope","roster"),"childId":c["childId"],"shared":"true",
                "includeChildSelections":"true","includeChildForces":"false"
            })
        else:
            cgs=ET.SubElement(m,f"{{{ns}}}conditionGroups")
            cg=ET.SubElement(cgs,f"{{{ns}}}conditionGroup",{"type":"and"})
            cs=ET.SubElement(cg,f"{{{ns}}}conditions")
            for c in conds:
                ET.SubElement(cs,f"{{{ns}}}condition",{
                    "type":c.get("type","atLeast"),"value":str(c.get("value",1)),"field":c.get("field","selections"),
                    "scope":c.get("scope","roster"),"childId":c["childId"],"shared":"true",
                    "includeChildSelections":"true","includeChildForces":"false"
                })
    return m

def catlink(entry,id_,name,target,primary=False,ns=CNS):
    cls=container(entry,"categoryLinks",ns,before=("entryLinks","infoLinks","profiles","rules","selectionEntries","selectionEntryGroups","costs"))
    q=f"{{{ns}}}categoryLink"
    x=next((z for z in cls.findall(q) if z.get("id")==id_),None)
    if x is None: x=ET.SubElement(cls,q)
    x.attrib.update({"id":id_,"name":name,"targetId":target,"hidden":"false"})
    if primary: x.set("primary","true")
    return x

def ensure_rule(entry,id_,name,text):
    rs=container(entry,"rules",CNS,before=("selectionEntries","selectionEntryGroups","costs"))
    r=next((x for x in rs.findall(C("rule")) if x.get("id")==id_),None)
    if r is None: r=ET.SubElement(rs,C("rule"))
    r.attrib.update({"id":id_,"name":name,"hidden":"false"})
    d=r.find(C("description"))
    if d is None: d=ET.SubElement(r,C("description"))
    d.text=text
    return r

def remove_direct_rules(entry):
    rs=entry.find(C("rules"))
    if rs is not None:
        entry.remove(rs)

def add_info_link(parent,id_,name,target,hidden=False):
    # infoLinks precede profiles/rules/selectionEntries/selectionEntryGroups/costs.
    il=container(parent,"infoLinks",CNS,before=("profiles","rules","selectionEntries","selectionEntryGroups","costs"))
    old=next((x for x in il.findall(C("infoLink")) if x.get("targetId")==target and x.get("type")=="rule"),None)
    if old is not None: return old
    x=ET.SubElement(il,C("infoLink"),{"id":id_,"name":name,"hidden":"true" if hidden else "false","targetId":target,"type":"rule"})
    return x

def slug(s):
    x=re.sub(r"[^a-z0-9]+","-",s.lower()).strip("-")
    return x[:72] or "rule"

def norm(s):
    return re.sub(r"\s+"," ",(s or "").strip())

# ----------------------------------------------------------------------
# Canonical shared rule definitions
# ----------------------------------------------------------------------
mod=ast.parse(R34.read_text(encoding="utf-8"))
vals={}
for node in mod.body:
    if isinstance(node,ast.Assign) and len(node.targets)==1 and isinstance(node.targets[0],ast.Name):
        nm=node.targets[0].id
        if nm in {"USR","DEEP_STRIKE","INDEPENDENT_CHARACTER","MASTER_OF_LEGION","PRIMARCH"}:
            vals[nm]=ast.literal_eval(node.value)
USR=vals["USR"]
canonical={**USR}
canonical["Scout"]=USR["Scouts"]
canonical["Deep Strike"]=vals["DEEP_STRIKE"]
canonical["Independent Character"]=vals["INDEPENDENT_CHARACTER"]
canonical["Master of the Legion"]=vals["MASTER_OF_LEGION"]
canonical["Primarch"]=vals["PRIMARCH"]
canonical.update({
 "Armoured Ceramite":"A vehicle equipped with Armoured Ceramite does not suffer the additional Armour Penetration die normally granted by the Melta special rule. Melta weapons therefore roll only one D6 for Armour Penetration against this vehicle, regardless of range.",
 "Armoured Cockpit":"Whenever a vehicle with an Armoured Cockpit suffers a Crew Shaken or Crew Stunned result, roll a D6. On a 4+, that result is ignored.",
 "Auxiliary Drive":"At the start of the controlling player's Movement phase, if a vehicle equipped with an Auxiliary Drive is Immobilised, roll a D6. On a 4+, remove one Immobilised result. The vehicle may move normally during that Movement phase.",
 "Flare Shield":"Against shooting attacks which strike the vehicle's Front Armour, reduce the Strength of Blast and Template weapons by 2 and all other ranged attacks by 1. A Flare Shield has no effect in close combat.",
 "Implacable Advance":"In any mission which distinguishes between Scoring and non-Scoring units, a Legion Terminator Squad counts as a Scoring Unit whenever Troops choices normally count as Scoring Units."
})

# Locate/create sharedRules in schema-friendly root position.
sr=cr.find(C("sharedRules"))
if sr is None:
    sr=ET.Element(C("sharedRules"))
    kids=list(cr); idx=len(kids)
    for j,k in enumerate(kids):
        if k.tag.split("}")[-1] in ("sharedProfiles","sharedInfoGroups"):
            idx=j; break
    cr.insert(idx,sr)

shared_by_name={}
for r in sr.findall(C("rule")):
    shared_by_name.setdefault(r.get("name",""),r)

def shared_rule(name,text,prefix="r36-shared"):
    r=shared_by_name.get(name)
    if r is None:
        rid=f"{prefix}-{slug(name)}-{hashlib.sha1(name.encode()).hexdigest()[:7]}"
        r=ET.SubElement(sr,C("rule"),{"id":rid,"name":name,"hidden":"false"})
        d=ET.SubElement(r,C("description")); d.text=text
        shared_by_name[name]=r
    else:
        d=r.find(C("description"))
        if d is None: d=ET.SubElement(r,C("description"))
        d.text=text
        r.set("hidden","false")
    return r

for n,t in canonical.items(): shared_rule(n,t)

# ----------------------------------------------------------------------
# Convert local standard rules to shared references.
# Also de-duplicate any remaining exact duplicate simple rules safely.
# ----------------------------------------------------------------------
pm={c:p for p in cr.iter() for c in p}

def replace_rule_with_link(rule,target_rule):
    rules=pm.get(rule)
    if rules is None or rules.tag!=C("rules"): return False
    owner=pm.get(rules)
    if owner is None or owner.tag not in (C("selectionEntry"),C("selectionEntryGroup")): return False
    rid=rule.get("id") or (owner.get("id","owner")+"-"+slug(rule.get("name","rule")))
    add_info_link(owner,"r36-link-"+hashlib.sha1(rid.encode()).hexdigest()[:12],target_rule.get("name",""),target_rule.get("id"),rule.get("hidden")=="true")
    rules.remove(rule)
    if len(list(rules))==0: owner.remove(rules)
    return True

canonical_converted=0
for r in list(cr.iter(C("rule"))):
    # Skip rules already in sharedRules.
    p=pm.get(r)
    if p is sr: continue
    n=(r.get("name") or "").strip()
    if n in canonical:
        if replace_rule_with_link(r,shared_rule(n,canonical[n])):
            canonical_converted+=1

# Rebuild parent map after structural edits.
pm={c:p for p in cr.iter() for c in p}
groups={}
for r in cr.iter(C("rule")):
    p=pm.get(r)
    if p is sr: continue
    # Only simple static rules are candidates.
    if any(ch.tag!=C("description") for ch in list(r)): continue
    name=(r.get("name") or "").strip()
    desc=norm(r.findtext(C("description")))
    if not name or not desc: continue
    groups.setdefault(name,[]).append((r,desc))
exact_shared_names=0; exact_converted=0
for name,items in list(groups.items()):
    if len(items)<2: continue
    descs={d for _,d in items}
    if len(descs)!=1: continue
    text=next(iter(descs))
    target=shared_rule(name,text,"r36-exact")
    exact_shared_names+=1
    # parent map may become stale per removal, but rules->owner chain still works for current nodes
    for r,_ in list(items):
        pm={c:p for p in cr.iter() for c in p}
        if replace_rule_with_link(r,target): exact_converted+=1

# ----------------------------------------------------------------------
# Sons of Horus Rites of War — functional implementation
# ----------------------------------------------------------------------
ids={e.get("id"):e for e in cr.iter() if e.get("id")}
LONG="r25-rite-xvi-0-the-long-march"
BLACK="r25-rite-xvi-1-the-black-reaving"
long=ids.get(LONG); black=ids.get(BLACK)
if long is None or black is None: raise RuntimeError("Sons of Horus Rite entries missing")
long.set("name","Sons of Horus Rite of War — The Long March")
black.set("name","Sons of Horus Rite of War — The Black Reaving")

remove_direct_rules(long)
ensure_rule(long,"r36-long-relentless","Relentless March",
"""At the beginning of each Sons of Horus player turn, determine the position of the majority of the surviving models in each Sons of Horus Infantry unit. Until the beginning of the next Sons of Horus player turn:
• Within the Sons of Horus deployment zone — the unit gains Relentless.
• Outside either player's deployment zone — the unit gains Fleet.
• Within the enemy deployment zone — the unit gains Crusader.
If a unit is equally divided between two areas, the controlling player chooses which applicable rule it gains.""")
ensure_rule(long,"r36-long-portion","The Warmaster's Portion",
"""During the first Sons of Horus player turn, all units in the Detachment may re-roll To Hit rolls of 1.
Legion Terminator Squads may also be selected as non-compulsory Troops choices. They may not fulfil compulsory Troops selections.""")
ensure_rule(long,"r36-long-limit","The Long March — Limitations",
"""This Rite may only be selected by a Traitor Sons of Horus Detachment.
Models with Slow and Purposeful may only be included if they begin the battle embarked aboard a Transport or enter play using Deep Strike.
The Detachment may not include a Fortification or an Allied Detachment.""")
for rn in ("Relentless","Fleet","Crusader"):
    add_info_link(long,f"r36-long-{slug(rn)}",rn,shared_by_name[rn].get("id"))

remove_direct_rules(black)
ensure_rule(black,"r36-black-onslaught","Reaver Onslaught",
"""Reaver Attack Squads may be selected as Troops choices and may fulfil compulsory Troops selections. At least one of the Detachment's compulsory Troops choices must be a Reaver Attack Squad.""")
ensure_rule(black,"r36-black-encirclement","Cthonian Encirclement",
"""After both armies have been selected, nominate up to two Sons of Horus Infantry units. These units gain Outflank. Any Dedicated Transport purchased for one of these units also gains Outflank and enters play together with its passengers. An Independent Character which begins the battle attached to one of these nominated units may Outflank with it.
When one of the two nominated units enters play, the Sons of Horus player may choose the side table edge from which that unit enters instead of rolling to determine the edge. The other nominated unit follows the normal ProHammer Outflank rules.""")
ensure_rule(black,"r36-black-lodge","Lodge Ceremony",
"""Once per battle, at the beginning of a Sons of Horus player turn, the Warlord may declare a Lodge Ceremony. Until the end of that player turn, all non-Vehicle Sons of Horus units gain Fleet.""")
ensure_rule(black,"r36-black-cut","Cut Them Apart",
"""During the first round of a close combat, a Sons of Horus unit which charged an enemy unit that was already engaged with another friendly Sons of Horus unit may re-roll To Hit rolls of 1. This benefit applies only during the player turn in which the unit charged.""")
ensure_rule(black,"r36-black-limit","The Black Reaving — Limitations",
"""The Detachment must include a Legion Centurion upgraded to a Master of Signals Consul.
At least one compulsory Troops choice must be a Reaver Attack Squad.
The Detachment must include at least as many Fast Attack choices as Heavy Support choices.
The Detachment may not include a Fortification or an Allied Detachment.""")
for rn in ("Outflank","Fleet"):
    add_info_link(black,f"r36-black-{slug(rn)}",rn,shared_by_name[rn].get("id"))

# Ensure Rite role copies display only under the correct Rite.
longcopy=ids.get("r32-soh-long-march-terminator-troops")
if longcopy is None: raise RuntimeError("Long March Terminator Troops copy missing")
longcopy.set("hidden","true")
modifier(longcopy,"r36-longcopy-show","set","hidden","false",[
    {"childId":"legion-xvi"},{"childId":LONG}
])

reavercopy=ids.get("r42-role-xvi-1-effects-reaver-onslaught-reaver-attack-squads-r41-unit-xvi-1-reaver-attack-squad")
if reavercopy is None: raise RuntimeError("Black Reaving Reaver Troops copy missing")
reavercopy.set("hidden","true")
modifier(reavercopy,"r36-black-reaver-show","set","hidden","false",[
    {"childId":"legion-xvi"},{"childId":BLACK}
])

# ----------------------------------------------------------------------
# Hidden categories and Force constraints for Rite requirements.
# ----------------------------------------------------------------------
ce=container(gr,"categoryEntries",GNS,before=("forceEntries",))
def gst_category(id_,name):
    e=next((x for x in ce.findall(G("categoryEntry")) if x.get("id")==id_),None)
    if e is None: e=ET.SubElement(ce,G("categoryEntry"))
    e.attrib.update({"id":id_,"name":name,"hidden":"true"})
    return e

CAT_MOS="r36-soh-black-master-signals"
CAT_REAVER="r36-soh-black-reaver-comp"
CAT_LONG_COMP="r36-soh-long-compulsory-troops"
gst_category(CAT_MOS,"Black Reaving — Master of Signals requirement")
gst_category(CAT_REAVER,"Black Reaving — compulsory Reaver requirement")
gst_category(CAT_LONG_COMP,"Long March — compulsory Troops excluding Terminators")

# Tag Master of Signals nested upgrade.
mos=ids.get("hq-consul-signals")
if mos is None: raise RuntimeError("Master of Signals entry missing")
catlink(mos,"r36-black-mos-cat","Black Reaving — Master of Signals requirement",CAT_MOS)

# Tag Black Reaving Reaver Troops copy.
catlink(reavercopy,"r36-black-reaver-cat","Black Reaving — compulsory Reaver requirement",CAT_REAVER)

# Tag Troops that can fulfil normal compulsory Troops for Long March.
def primary_cat(e,target):
    return any(c.get("targetId")==target and c.get("primary")=="true" for c in e.findall(f"./{C('categoryLinks')}/{C('categoryLink')}"))
def disallowed_compulsory(e):
    if e is longcopy: return True
    texts=[]
    for r in e.findall(f"./{C('rules')}/{C('rule')}"):
        texts.append((r.get("name") or "")+" "+(r.findtext(C("description")) or ""))
    txt=" ".join(texts).lower()
    # Also inspect shared-link names after de-dup.
    for il in e.findall(f"./{C('infoLinks')}/{C('infoLink')}"):
        txt+=" "+(il.get("name") or "").lower()
    return ("support squad" in txt or "may not fulfil" in txt and "compulsory" in txt or "non-compulsory troops" in (e.get("name") or "").lower())

long_comp_tagged=0
for e in cr.findall(f"./{C('selectionEntries')}/{C('selectionEntry')}")+cr.findall(f"./{C('sharedSelectionEntries')}/{C('selectionEntry')}"):
    if e.get("type")=="unit" and primary_cat(e,"cat-troops") and not disallowed_compulsory(e):
        catlink(e,"r36-long-comp-"+hashlib.sha1((e.get("id") or "").encode()).hexdigest()[:10],"Long March — compulsory Troops",CAT_LONG_COMP)
        long_comp_tagged+=1

# Force links/constraints.
force=next((x for x in gr.iter(G("forceEntry")) if x.get("id")=="force-standard"),None)
if force is None: raise RuntimeError("Standard force missing")
fcls=container(force,"categoryLinks",GNS)

def hidden_force_link(id_,name,target):
    cl=next((x for x in fcls.findall(G("categoryLink")) if x.get("id")==id_),None)
    if cl is None: cl=ET.SubElement(fcls,G("categoryLink"))
    cl.attrib.update({"id":id_,"name":name,"hidden":"true","targetId":target})
    return cl

fl_mos=hidden_force_link("r36-soh-black-mos-force","Black Reaving — Master of Signals",CAT_MOS)
c=constraint(fl_mos,"r36-soh-black-mos-min","min",0,ns if False else "selections","parent",True)
modifier(fl_mos,"r36-soh-black-mos-min-set","set","r36-soh-black-mos-min",1,[{"childId":BLACK}],ns=GNS)

fl_re=hidden_force_link("r36-soh-black-reaver-force","Black Reaving — compulsory Reaver",CAT_REAVER)
constraint(fl_re,"r36-soh-black-reaver-min","min",0,"selections","parent",True)
modifier(fl_re,"r36-soh-black-reaver-min-set","set","r36-soh-black-reaver-min",1,[{"childId":BLACK}],ns=GNS)

fl_lc=hidden_force_link("r36-soh-long-comp-force","Long March — compulsory Troops",CAT_LONG_COMP)
constraint(fl_lc,"r36-soh-long-comp-min","min",0,"selections","parent",True)
modifier(fl_lc,"r36-soh-long-comp-min-set","set","r36-soh-long-comp-min",2,[{"childId":LONG}],ns=GNS)

# Black Reaving: Fast Attack selections must be >= Heavy Support selections.
fast=next((x for x in fcls.findall(G("categoryLink")) if x.get("id")=="fl-fast"),None)
if fast is None: raise RuntimeError("Fast Attack force link missing")
constraint(fast,"r36-soh-black-fast-min","min",0,"selections","parent",False)
modifier(fast,"r36-soh-black-fast-per-heavy","increment","r36-soh-black-fast-min",1,
         [{"childId":BLACK}],
         repeats=[{"field":"selections","scope":"force","value":1,"childId":"cat-heavy","includeChildSelections":False,"repeats":1,"roundUp":False}],
         ns=GNS)

# ----------------------------------------------------------------------
# Catalogue-wide display-name cleanup for unit entries.
# ----------------------------------------------------------------------
def smart_title(s):
    # Normal display capitalization; preserve em dashes and parenthetical suffixes.
    words=s.lower().split(" ")
    out=[]
    small={"of","the","and","or"}
    for idx,w in enumerate(words):
        if not w:
            out.append(w); continue
        # Handle hyphen compounds but not apostrophe possessives.
        parts=w.split("-")
        pp=[]
        for p in parts:
            if not p: pp.append(p); continue
            if idx>0 and p in small:
                pp.append(p)
            else:
                pp.append(p[0].upper()+p[1:])
        out.append("-".join(pp))
    t=" ".join(out)
    # common possessive / project spellings
    t=t.replace("Angel's","Angel's").replace("Falcon’s","Falcon’s")
    t=t.replace("Mhara Gal","Mhara Gal").replace("Gal Vorbak","Gal Vorbak")
    return t

name_changes=[]
for e in cr.iter(C("selectionEntry")):
    if e.get("type")!="unit": continue
    n=(e.get("name") or "").strip()
    letters=re.sub(r"[^A-Za-zÀ-ÿ]","",n)
    if len(letters)>=4 and letters==letters.upper():
        nn=smart_title(n)
        if nn!=n:
            e.set("name",nn); name_changes.append((n,nn))

# ----------------------------------------------------------------------
# Rebuild parent map and run a second shared-rule conversion on newly
# created local rules where appropriate (none of the Rite custom names).
# ----------------------------------------------------------------------
pm={c:p for p in cr.iter() for c in p}
# Any local canonical rule accidentally reintroduced gets converted.
second=0
for r in list(cr.iter(C("rule"))):
    p=pm.get(r)
    if p is sr: continue
    n=(r.get("name") or "").strip()
    if n in canonical:
        if replace_rule_with_link(r,shared_by_name[n]): second+=1

# ----------------------------------------------------------------------
# Revisioning and serialization
# ----------------------------------------------------------------------
cr.set("revision","36")
cr.set("gameSystemRevision","2")
ET.register_namespace("",CNS)
ct.write(CAT,encoding="utf-8",xml_declaration=True)

gr.set("revision","2")
ET.register_namespace("",GNS)
gt.write(GST,encoding="utf-8",xml_declaration=True)

it=ET.parse(IDX); ir=it.getroot()
ET.register_namespace("",INS)
for x in ir.iter(I("dataIndexEntry")):
    if x.get("filePath")=="Legiones Astartes.cat": x.set("dataRevision","36")
    if x.get("filePath")=="Prohammer 30k.gst": x.set("dataRevision","2")
it.write(IDX,encoding="utf-8",xml_declaration=True)

# ----------------------------------------------------------------------
# Validation
# ----------------------------------------------------------------------
cc=ET.parse(CAT).getroot(); gg=ET.parse(GST).getroot(); checks=[]
def ck(label,ok):
    checks.append((label,bool(ok)))
    if not ok: raise RuntimeError("R36 validation failed: "+label)
ck("CAT revision 36",cc.get("revision")=="36")
ck("CAT points at GST revision 2",cc.get("gameSystemRevision")=="2")
ck("GST revision 2",gg.get("revision")=="2")
idx=IDX.read_text(encoding="utf-8")
ck("Index CAT 36",'filePath="Legiones Astartes.cat"' in idx and 'dataRevision="36"' in idx)
ck("Index GST 2",'filePath="Prohammer 30k.gst"' in idx and 'dataRevision="2"' in idx)
ck("No ns0 prefixes","ns0:" not in idx and "ns0:" not in CAT.read_text(encoding="utf-8")[:500] and "ns0:" not in GST.read_text(encoding="utf-8")[:500])

# No local canonical rules remain.
csr=cc.find(C("sharedRules"))
local_canonical=[]
pm2={c:p for p in cc.iter() for c in p}
for r in cc.iter(C("rule")):
    if pm2.get(r) is csr: continue
    if (r.get("name") or "") in canonical: local_canonical.append(r.get("name"))
ck("Canonical standard rules exist only as shared rules",not local_canonical)

# No all-caps unit display names remain.
caps=[]
for e in cc.iter(C("selectionEntry")):
    if e.get("type")!="unit": continue
    n=e.get("name") or ""; letters=re.sub(r"[^A-Za-zÀ-ÿ]","",n)
    if len(letters)>=4 and letters==letters.upper(): caps.append(n)
ck("No all-caps unit display names",not caps)

# Rite mechanics present.
gids={x.get("id"):x for x in gg.iter() if x.get("id")}
ck("Black Reaving Master of Signals force requirement", "r36-soh-black-mos-force" in gids)
ck("Black Reaving compulsory Reaver force requirement", "r36-soh-black-reaver-force" in gids)
ck("Long March compulsory Troops force requirement", "r36-soh-long-comp-force" in gids)
ck("Black Reaving Fast>=Heavy modifier", "r36-soh-black-fast-per-heavy" in gids)

lines=[
"Live R36 — Sons of Horus Rites, shared-rule de-duplication, unit-name cleanup",
"Input CAT=35/GST=1 -> CAT=36/GST=2","",
"SONS OF HORUS RITES:",
"- The Long March split into functional/readable rule components; Traitor gating retained.",
"- Long March Terminator Troops copy retained as non-compulsory and a hidden requirement now forces two other compulsory-capable Troops.",
"- The Black Reaving Reaver Troops copy is gated to the Rite and counts toward a hidden compulsory-Reaver requirement.",
"- Black Reaving now mechanically requires a Legion Master of Signals Consul.",
"- Black Reaving now mechanically requires Fast Attack selections >= Heavy Support selections.",
"- Battlefield-only effects (Relentless March zones, Cthonian Encirclement deployment, Lodge Ceremony, Cut Them Apart) remain rule text because they depend on in-game state.",
"",
"RULE DE-DUPLICATION:",
f"- Converted {canonical_converted+second} local standard-rule blocks into references to canonical shared rules.",
f"- Created/reused {exact_shared_names} additional shared rules for exact duplicate static definitions and converted {exact_converted} local copies.",
"- Standard ProHammer rules, Deep Strike, Independent Character, Master of the Legion, Primarch, Armoured Ceramite, Armoured Cockpit, Auxiliary Drive, Flare Shield and Implacable Advance now use shared rule definitions.",
"- Conditions/costs remain on their selectors; the named rule itself is referenced once rather than redefined repeatedly.",
"",
"DISPLAY NAMES:",
f"- Normalised {len(name_changes)} all-caps unit entries/copies to normal display capitalization.",
f"- Tagged {long_comp_tagged} Troops entries as eligible Long March compulsory Troops.",
"",
"VALIDATION:"
]
lines += [f'- {"PASS" if ok else "FAIL"}: {label}' for label,ok in checks]
lines += ["","UNIT NAME CHANGES:"]+[f"- {a} -> {b}" for a,b in name_changes]
OUT.write_text("\n".join(lines)+"\n",encoding="utf-8")
print(OUT.read_text())
