from pathlib import Path
import copy, hashlib, re, xml.etree.ElementTree as ET

CAT=Path("Legiones Astartes.cat")
GST=Path("Prohammer 30k.gst")
IDX=Path("index.xml")
OUT=Path("inspection-live-r37-word-bearers.txt")

CNS="http://www.battlescribe.net/schema/catalogueSchema"
GNS="http://www.battlescribe.net/schema/gameSystemSchema"
INS="http://www.battlescribe.net/schema/dataIndexSchema"
ET.register_namespace("",CNS)
C=lambda t:f"{{{CNS}}}{t}"
G=lambda t:f"{{{GNS}}}{t}"
I=lambda t:f"{{{INS}}}{t}"

ct=ET.parse(CAT); cr=ct.getroot()
gt=ET.parse(GST); gr=gt.getroot()
if cr.get("revision")!="36": raise RuntimeError(f"R37 expected CAT 36, got {cr.get('revision')}")
if gr.get("revision")!="2": raise RuntimeError(f"R37 expected GST 2, got {gr.get('revision')}")

# ---------- generic XML helpers ----------
def qns(e): return e.tag.split("}")[0].strip("{")
def cont(p,tag,before=("constraints","categoryLinks","entryLinks","infoLinks","profiles","rules","selectionEntries","selectionEntryGroups","costs","modifiers")):
    ns=qns(p); q=f"{{{ns}}}{tag}"
    x=p.find(q)
    if x is not None:return x
    x=ET.Element(q); kids=list(p); idx=len(kids)
    for j,k in enumerate(kids):
        if k.tag.split("}")[-1] in before:
            idx=j; break
    p.insert(idx,x); return x

def cons(p,id_,typ,val,field="selections",scope="parent",child=False):
    ns=qns(p); cs=cont(p,"constraints")
    q=f"{{{ns}}}constraint"
    x=next((z for z in cs.findall(q) if z.get("id")==id_),None)
    if x is None:x=ET.SubElement(cs,q)
    x.attrib.update({"id":id_,"type":typ,"value":str(val),"field":field,"scope":scope,
                     "shared":"true","includeChildSelections":"true" if child else "false",
                     "includeChildForces":"false"})
    return x

def cost(p,val,idtype="pts"):
    cs=cont(p,"costs",before=("modifiers",))
    ns=qns(p); q=f"{{{ns}}}cost"
    x=next((z for z in cs.findall(q) if z.get("typeId")==idtype),None)
    if x is None:x=ET.SubElement(cs,q,{"name":"Points","typeId":idtype})
    x.set("value",str(val)); return x

def modifier(p,id_,typ,field,value,conditions=None,repeats=None):
    ns=qns(p); ms=cont(p,"modifiers")
    q=f"{{{ns}}}modifier"; x=next((z for z in ms.findall(q) if z.get("id")==id_),None)
    if x is None:x=ET.SubElement(ms,q)
    x.attrib.update({"id":id_,"type":typ,"field":field,"value":str(value)})
    for ch in list(x):x.remove(ch)
    if repeats:
        rs=ET.SubElement(x,f"{{{ns}}}repeats")
        for rp in repeats:
            ET.SubElement(rs,f"{{{ns}}}repeat",{
                "field":rp.get("field","selections"),"scope":rp.get("scope","root-entry"),
                "value":str(rp.get("value",1)),"shared":"true","childId":rp["childId"],
                "includeChildSelections":"true" if rp.get("includeChildSelections",False) else "false",
                "includeChildForces":"false","repeats":str(rp.get("repeats",1)),
                "roundUp":"true" if rp.get("roundUp",False) else "false"})
    if conditions:
        if len(conditions)==1:
            cs=ET.SubElement(x,f"{{{ns}}}conditions"); target=cs
        else:
            cgs=ET.SubElement(x,f"{{{ns}}}conditionGroups")
            cg=ET.SubElement(cgs,f"{{{ns}}}conditionGroup",{"type":"and"})
            target=ET.SubElement(cg,f"{{{ns}}}conditions")
        for c in conditions:
            ET.SubElement(target,f"{{{ns}}}condition",{
                "type":c.get("type","atLeast"),"value":str(c.get("value",1)),
                "field":c.get("field","selections"),"scope":c.get("scope","roster"),
                "childId":c["childId"],"shared":"true",
                "includeChildSelections":"true" if c.get("includeChildSelections",True) else "false",
                "includeChildForces":"false"})
    return x

def catlink(p,id_,name,target,primary=False):
    ns=qns(p); cs=cont(p,"categoryLinks")
    q=f"{{{ns}}}categoryLink"; x=next((z for z in cs.findall(q) if z.get("id")==id_),None)
    if x is None:x=ET.SubElement(cs,q)
    x.attrib.update({"id":id_,"name":name,"targetId":target,"hidden":"false"})
    if primary:x.set("primary","true")
    return x

def add_rule(p,id_,name,text):
    rs=cont(p,"rules"); r=next((z for z in rs.findall(C("rule")) if z.get("id")==id_),None)
    if r is None:r=ET.SubElement(rs,C("rule"))
    r.attrib.update({"id":id_,"name":name,"hidden":"false"})
    d=r.find(C("description"))
    if d is None:d=ET.SubElement(r,C("description"))
    d.text=text; return r

def clear_rules(p):
    rs=p.find(C("rules"))
    if rs is not None:p.remove(rs)

def add_infolink(p,id_,name,target,typ="rule",hidden=False):
    ils=cont(p,"infoLinks"); x=next((z for z in ils.findall(C("infoLink")) if z.get("id")==id_),None)
    if x is None:x=ET.SubElement(ils,C("infoLink"))
    x.attrib.update({"id":id_,"name":name,"targetId":target,"type":typ,"hidden":"true" if hidden else "false"})
    return x

def group(p,id_,name,minv=None,maxv=None,hidden=False):
    gs=cont(p,"selectionEntryGroups",before=("costs","modifiers"))
    g=next((z for z in gs.findall(C("selectionEntryGroup")) if z.get("id")==id_),None)
    if g is None:g=ET.SubElement(gs,C("selectionEntryGroup"))
    g.attrib.update({"id":id_,"name":name,"hidden":"true" if hidden else "false"})
    if minv is not None:cons(g,id_+"-min","min",minv)
    if maxv is not None:cons(g,id_+"-max","max",maxv)
    return g

def sel(p,id_,name,typ="upgrade",pts=0,minv=None,maxv=1,default=None,hidden=False):
    ss=cont(p,"selectionEntries",before=("selectionEntryGroups","costs","modifiers"))
    e=next((z for z in ss.findall(C("selectionEntry")) if z.get("id")==id_),None)
    if e is None:e=ET.SubElement(ss,C("selectionEntry"))
    e.attrib.update({"id":id_,"name":name,"type":typ,"hidden":"true" if hidden else "false"})
    if default is not None:e.set("defaultAmount",str(default))
    if minv is not None:cons(e,id_+"-min","min",minv)
    if maxv is not None:cons(e,id_+"-max","max",maxv)
    cost(e,pts)
    return e

def elink(p,id_,name,target,pts=0,minv=None,maxv=1,hidden=False):
    es=cont(p,"entryLinks",before=("infoLinks","profiles","rules","selectionEntries","selectionEntryGroups","costs","modifiers"))
    e=next((z for z in es.findall(C("entryLink")) if z.get("id")==id_),None)
    if e is None:e=ET.SubElement(es,C("entryLink"))
    e.attrib.update({"id":id_,"name":name,"targetId":target,"type":"selectionEntry","import":"true","hidden":"true" if hidden else "false"})
    if minv is not None:cons(e,id_+"-min","min",minv)
    if maxv is not None:cons(e,id_+"-max","max",maxv)
    cost(e,pts)
    return e

def profile(p,id_,name,ptype,chars):
    ps=cont(p,"profiles",before=("rules","selectionEntries","selectionEntryGroups","costs","modifiers"))
    pr=next((z for z in ps.findall(C("profile")) if z.get("id")==id_),None)
    if pr is None:pr=ET.SubElement(ps,C("profile"))
    pr.attrib.update({"id":id_,"name":name,"typeId":ptype,"hidden":"false"})
    chs=pr.find(C("characteristics"))
    if chs is None:chs=ET.SubElement(pr,C("characteristics"))
    for z in list(chs):chs.remove(z)
    ids={"Range":"weapon-range","S":"weapon-s","AP":"weapon-ap","Type":"weapon-type"}
    for k,v in chars.items():
        z=ET.SubElement(chs,C("characteristic"),{"name":k,"typeId":ids.get(k,k.lower())}); z.text=str(v)
    return pr

def clear_named_groups(p,prefixes):
    gs=p.find(C("selectionEntryGroups"))
    if gs is None:return
    for g in list(gs):
        if any((g.get("id") or "").startswith(x) or (g.get("name") or "").startswith(x) for x in prefixes):
            gs.remove(g)

def deep_prefix(e,prefix):
    x=copy.deepcopy(e)
    oldids=[]
    for z in x.iter():
        if z.get("id"):oldids.append(z.get("id"))
    mapping={o:prefix+o for o in oldids}
    for z in x.iter():
        if z.get("id") in mapping:z.set("id",mapping[z.get("id")])
        for a in ("childId","targetId","field"):
            if z.get(a) in mapping:z.set(a,mapping[z.get(a)])
    return x

def primary_cat(e,target):
    return any(x.get("targetId")==target and x.get("primary")=="true" for x in e.findall(f"./{C('categoryLinks')}/{C('categoryLink')}"))

def set_primary_cat(e,target,name):
    cls=cont(e,"categoryLinks")
    for c in cls.findall(C("categoryLink")):
        if c.get("primary")=="true":c.set("primary","false")
    c=next((z for z in cls.findall(C("categoryLink")) if z.get("targetId")==target),None)
    if c is None:c=ET.SubElement(cls,C("categoryLink"),{"id":e.get("id")+"-cat-"+target,"name":name,"targetId":target,"hidden":"false"})
    c.set("primary","true")

# ---------- index ----------
ids={e.get("id"):e for e in cr.iter() if e.get("id")}
def refresh():
    global ids
    ids={e.get("id"):e for e in cr.iter() if e.get("id")}
refresh()

def find_sel_name(name):
    exact=[e for e in cr.iter(C("selectionEntry")) if (e.get("name") or "").strip().lower()==name.lower()]
    return exact[0] if exact else None

traitor=None
for e in cr.iter(C("selectionEntry")):
    if (e.get("name") or "").strip().lower()=="traitor":
        traitor=e; break
TRAITOR=traitor.get("id") if traitor is not None else None

# ---------- shared rules ----------
sr=cr.find(C("sharedRules"))
if sr is None:
    sr=ET.Element(C("sharedRules"))
    cr.insert(0,sr)
shared={r.get("name"):r for r in sr.findall(C("rule"))}
def shr(name,text,idbase=None):
    r=shared.get(name)
    if r is None:
        rid=idbase or ("r37-wb-rule-"+re.sub(r"[^a-z0-9]+","-",name.lower()).strip("-")[:60])
        r=ET.SubElement(sr,C("rule"),{"id":rid,"name":name,"hidden":"false"})
        shared[name]=r
    d=r.find(C("description"))
    if d is None:d=ET.SubElement(r,C("description"))
    d.text=text; return r

ATSKNF=shared.get("And They Shall Know No Fear")
STANDARD={n:shared.get(n) for n in ["Daemon","Fearless","Bulky","Rending","Fleet","It Will Not Die","Adamantium Will","Zealot","Furious Charge","Counter-Attack","Master-Crafted","Two-Handed","Concussive","Independent Character","Master of the Legion","Primarch","Soul Blaze","Scout"]}

WB_LEG=shr("Legiones Astartes (Word Bearers)",
"""This is the named XVII Legion version of Legiones Astartes. Models with this rule also use the normal Legiones Astartes rules and And They Shall Know No Fear. A model may only possess one named Legiones Astartes rule.""")
FAN=shr("Fanatical Devotion",
"""Non-Daemon units with Legiones Astartes (Word Bearers) may re-roll failed Morale and Pinning tests.""")
DARKS=shr("The Dark Shepherds",
"""A Word Bearers Detachment must include at least one Legion Chaplain Consul or Legion-specific Dark Apostle as an HQ selection. A character specifically stated to count as a Dark Apostle also fulfils this requirement.""")
RITUAL=shr("Ritual of Consecration",
"""Traitor Word Bearers only. When a non-Daemon Word Bearers unit completely destroys an enemy unit during the Assault phase, it may forgo its Consolidation move. If it does, nominate one friendly Daemonic Covenant unit currently in Reserve; that unit may re-roll its next Reserve roll. Only one Covenant unit may receive this benefit each turn.""")
COV=shr("Daemonic Covenant",
"""A Traitor Word Bearers army may include one Daemons of the Ruinstorm Covenant Detachment as its Allied Detachment.
Covenant Force Organisation: HQ 0–1; Troops 1–3; Elites 0–1; Fast Attack 0–1; Heavy Support 0–1. At least one Troops choice is compulsory. The Covenant may cost no more than 25% of the army's total points limit and has no minimum points requirement.
Units use their normal profiles, options, Aetheric Dominions and rules from Daemons of the Ruinstorm. Covenant units cannot fulfil compulsory selections in the primary Detachment or provide the Warlord. Word Bearers and Covenant units are Fellow Warriors. Independent Characters may not join units across these Detachments.""")
SUMM=shr("Daemonic Summoning",
"""All units in a Daemonic Covenant Detachment begin in Reserve and may not deploy normally, Infiltrate or Outflank. When a Covenant unit becomes available, nominate a friendly Summoning Point already on the battlefield: Personal Icons, Icons of Chaos Undivided, Accursed Crozii, or another rule explicitly identified as a Summoning Point. Place the centre model within 6" of the Summoning Point and more than 2" from enemies, then enter using the normal Deep Strike rules. If no legal Summoning Point/position exists, the unit remains in Reserve. Summoning Points may be used while engaged, are not consumed, and may summon multiple units. Deep Strike Mishaps and normal Deep Strike restrictions apply.""")
HARD=shr("Hardened Armour",
"""Failed Armour Saves caused by Blast or Template weapons may be re-rolled. Reduce Advance distance by 1", and reduce Charge or Pursuit distance by 1". In missions using Void Hardened armour, models with Hardened Armour count as Void Hardened. These movement penalties also apply to an Artificer Armour model that is part of a Breacher-style Hardened Armour unit.""")
BITTER=shr("Bitter Duty",
"""Only an Independent Character specifically permitted to join Bitter Duty units may join an Ashen Circle Squad.""")
PRIMARM=shr("Primarch Armour",
"""Primarch Armour confers a 1+ Armour Save and a 4+ Invulnerable Save. A natural roll of 1 always fails.""")
FNP6=shr("Feel No Pain (6+)",
"""After a model fails an eligible saving throw, roll a D6; on a 6 the Wound is ignored, subject to the normal ProHammer Feel No Pain restrictions.""")
PELOY=shr("Preferred Enemy (Loyalists)",
"""The model/unit may re-roll failed hits in close combat against models belonging to the Loyalist faction.""")
NART=shr("Narthecium",
"""A unit containing an Apothecary equipped with a Narthecium may ignore the first failed saving throw it suffers during each player turn. It cannot be used against Instant Death, an attack allowing no saving throw of any kind, if the Apothecary is slain, or while the Apothecary is in base contact with an enemy model. The controlling player chooses the eligible failed save ignored.""")
RED=shr("Reductor",
"""In missions using Victory Points, an Apothecary equipped with a Reductor recovers 1 Victory Point for each slain friendly Legiones Astartes model that belonged to his unit, including attached Independent Characters, provided the Apothecary survives the battle.""")
for n,t in [
 ("Driven to Slaughter","While the Legion Overseer lives, the Covenant Zealot Mob is Fearless and ignores Leadership penalties. If able to charge in the Assault phase it must do so. In a turn it charges, Covenant Zealots (not the Overseer) gain +1 Attack and +1 Initiative. If the Overseer is slain, the unit loses Fearless and this rule; if not locked it immediately becomes Pinned, otherwise it becomes Pinned when that combat ends."),
 ("Expendable","Casualties suffered by a Covenant Zealot Mob, or the destruction of the unit, never cause friendly units to take Morale, Leadership or Pinning tests."),
 ("Daemonic Engine","Each time the Mhara Gal suffers a Glancing or Penetrating Hit, roll a D6 before the Vehicle Damage roll. On a 5+, the hit is ignored."),
 ("Shroud of Dark Fire","When resolving a shooting attack against the Mhara Gal made with a Flame, Melta, Plasma or Volkite weapon, reduce that attack's Strength by 1, to a minimum of 1."),
 ("Accursed","Successful Invulnerable Saves made against the Mhara Gal's close-combat attacks must be re-rolled. Enemy units taking a Fear test caused by the Mhara Gal suffer -2 Leadership. The Mhara Gal never counts as a Scoring Unit."),
 ("Flesh Harvesters","When a Procurator Squad uses Ritual of Consecration, the nominated Daemon unit receives +1 to its next Reserve roll in addition to the normal re-roll. This modifier is not cumulative."),
 ("Daemonkin","After deployment but before the first turn, roll a D6 for the squad. 1: Scout (may make the normal pre-game Scout move and gains Outflank). 2: Furious Charge (+1 Strength and +1 Initiative in assault on the turn it charges). 3: Fleet (may charge even if it Advanced). 4: close-combat attacks gain Rending (To Wound 6 becomes AP2; against vehicles an Armour Penetration roll of 6 adds D3). 5: Feel No Pain (5+). 6: Counter-Attack (when charged while unengaged, pass a Leadership test to gain +1 Attack for that Assault phase)."),
]:
    shr(n,t)
WB_RULES={n:shared[n] for n in ["Driven to Slaughter","Expendable","Daemonic Engine","Shroud of Dark Fire","Accursed","Flesh Harvesters","Daemonkin"]}

def ilrule(e,name,id_):
    r=shared.get(name)
    if r is None: raise RuntimeError("Missing shared rule "+name)
    add_infolink(e,id_,name,r.get("id"),"rule")

def legion_links(e,fanatical=True):
    ilrule(e,"Legiones Astartes (Word Bearers)",e.get("id")+"-wb-leg")
    if ATSKNF is not None:add_infolink(e,e.get("id")+"-wb-atsknf","And They Shall Know No Fear",ATSKNF.get("id"),"rule")
    if fanatical:add_infolink(e,e.get("id")+"-wb-fan","Fanatical Devotion",FAN.get("id"),"rule")

def std(e,name,suffix=None):
    r=shared.get(name)
    if r is None:return
    add_infolink(e,e.get("id")+"-"+(suffix or re.sub(r"[^a-z0-9]+","-",name.lower()).strip("-")),name,r.get("id"),"rule")

# ---------- shared unique profiles ----------
sp=cr.find(C("sharedProfiles"))
if sp is None:
    sp=ET.Element(C("sharedProfiles")); cr.insert(list(cr).index(sr)+1,sp)
def shared_prof(id_,name,chars):
    p=next((z for z in sp.findall(C("profile")) if z.get("id")==id_),None)
    if p is None:p=ET.SubElement(sp,C("profile"))
    p.attrib.update({"id":id_,"name":name,"typeId":"prof-weapon","hidden":"false"})
    chs=p.find(C("characteristics"))
    if chs is None:chs=ET.SubElement(p,C("characteristics"))
    for z in list(chs):chs.remove(z)
    for k,v,tid in [("Range",chars[0],"weapon-range"),("S",chars[1],"weapon-s"),("AP",chars[2],"weapon-ap"),("Type",chars[3],"weapon-type")]:
        z=ET.SubElement(chs,C("characteristic"),{"name":k,"typeId":tid}); z.text=str(v)
    return p
AXE=shared_prof("r37-wb-prof-axe-rake","Axe-rake",("—","+1","—","Melee"))
CUST=shared_prof("r37-wb-prof-custodian-spear","Custodian Spear",("—","+1","Power Weapon","Melee, Two-Handed, Master-crafted"))
CUSTG=shared_prof("r37-wb-prof-custodian-gun","Custodian Spear — Foeblaster Boltgun",('18"',"5","4","Rapid Fire, Twin-linked"))
ILL=shared_prof("r37-wb-prof-illuminarum","Illuminarum",("—","+2","Power Weapon","Melee, Master-crafted, Concussive"))
CROZ=shared_prof("r37-wb-prof-crozius","Accursed Crozius",("—","User","Power Weapon","Melee"))
ANATH=shared_prof("r37-wb-prof-anathame","Anathame Dagger",("—","User","—","Melee, special attack"))

# ---------- visibility ----------
def visibility(e,required):
    e.set("hidden","true")
    modifier(e,e.get("id")+"-r37-show","set","hidden","false",
             [{"childId":x,"scope":"roster"} for x in required])

def traitor_req():
    return ["legion-xvii"]+([TRAITOR] if TRAITOR else [])

# ---------- Legion selector cleanup ----------
leg=ids.get("legion-xvii")
if leg is None: raise RuntimeError("legion-xvii missing")
clear_rules(leg)
legion_links(leg,False)
for nm,rr in [("Fanatical Devotion",FAN),("The Dark Shepherds",DARKS),("Ritual of Consecration",RITUAL),("Daemonic Covenant",COV),("Daemonic Summoning",SUMM)]:
    add_infolink(leg,"r37-leg-xvii-"+re.sub(r"[^a-z0-9]+","-",nm.lower()).strip("-"),nm,rr.get("id"),"rule")

# ---------- hidden army requirement categories in GST ----------
ce=gr.find(G("categoryEntries"))
if ce is None:ce=ET.SubElement(gr,G("categoryEntries"))
def gcat(id_,name):
    x=next((z for z in ce.findall(G("categoryEntry")) if z.get("id")==id_),None)
    if x is None:x=ET.SubElement(ce,G("categoryEntry"))
    x.attrib.update({"id":id_,"name":name,"hidden":"true"}); return x
CAT_DARK_AP="r37-wb-dark-apostle-req"
CAT_DIAB="r37-wb-diabolist-req"
CAT_FAV="r37-wb-favour-limit"
gcat(CAT_DARK_AP,"Word Bearers — Dark Shepherd")
gcat(CAT_DIAB,"Word Bearers — Diabolist")
gcat(CAT_FAV,"Word Bearers — Favour of the Pantheon")

force=next((x for x in gr.iter(G("forceEntry")) if x.get("id")=="force-standard"),None)
if force is None:raise RuntimeError("force-standard missing")
fcls=cont(force,"categoryLinks")
def force_hidden_link(id_,name,target):
    x=next((z for z in fcls.findall(G("categoryLink")) if z.get("id")==id_),None)
    if x is None:x=ET.SubElement(fcls,G("categoryLink"))
    x.attrib.update({"id":id_,"name":name,"targetId":target,"hidden":"true"}); return x
flap=force_hidden_link("r37-wb-dark-ap-force","Word Bearers — Dark Shepherd",CAT_DARK_AP)
cons(flap,"r37-wb-dark-ap-min","min",0,"selections","parent",True)
modifier(flap,"r37-wb-dark-ap-min-set","set","r37-wb-dark-ap-min",1,[{"childId":"legion-xvii","scope":"roster"}])
flfav=force_hidden_link("r37-wb-favour-force","Word Bearers — Favour of the Pantheon",CAT_FAV)
cons(flfav,"r37-wb-favour-max","max",1,"selections","parent",True)

# tag Chaplain and WB Dark Apostles
for id_ in ["hq-consul-chaplain","r46-wb-accursed-crozius","r41-unit-xvii-7-high-chaplain-erebus","r41-unit-xvii-8-kor-phaeron-the-black-cardinal","r41-unit-xvii-9-zardu-layak"]:
    e=ids.get(id_)
    if e is not None:catlink(e,id_+"-r37-darkap","Word Bearers — Dark Shepherd",CAT_DARK_AP)

# Diabolist tags
for id_ in ["r46-wb-diabolist","r41-unit-xvii-7-high-chaplain-erebus","r41-unit-xvii-8-kor-phaeron-the-black-cardinal","r41-unit-xvii-9-zardu-layak"]:
    e=ids.get(id_)
    if e is not None:catlink(e,id_+"-r37-diab","Word Bearers — Diabolist",CAT_DIAB)

# ---------- armoury ----------
acc=ids.get("r46-wb-accursed-crozius"); tw=ids.get("r46-wb-tainted-weapon")
burn=ids.get("r46-wb-burning-lore"); hexb=ids.get("r46-wb-hex-bolts"); icon=ids.get("r46-wb-icon-chaos-undivided")
darkch=ids.get("r46-wb-dark-channelling"); diab=ids.get("r46-wb-diabolist")
for x in [acc,tw,burn,hexb,icon,darkch,diab]:
    if x is None:raise RuntimeError("Missing WB armoury entry")

clear_rules(acc); add_infolink(acc,"r37-acc-prof","Accursed Crozius",CROZ.get("id"),"profile")
add_rule(acc,"r37-acc-rule","Accursed Crozius","The bearer receives a 4+ Invulnerable Save, counts as possessing a Personal Icon/Summoning Point for Daemonic Covenant, and counts as a Dark Apostle for The Dark Shepherds. A model may never possess more than one Accursed Crozius.")
clear_rules(tw); add_rule(tw,"r37-tw-rule","Tainted Weapon","Select instead of a Power Weapon at the same points cost. User Strength, Specialist Weapon. Any unsaved Wound becomes a Massive Wound and inflicts D3 Wounds instead of 1. It is not a Power Weapon and does not ignore Armour Saves.")
clear_rules(hexb); add_rule(hexb,"r37-hex-rule","Hex-Bolts","Bolt Pistols, Bolters, Combi-Bolters, Storm Bolters and the bolter component of Combi-Weapons carried by the unit gain Soul Blaze. Soul Blaze: a unit wounded by such an attack is ablaze; at the end of each turn roll D6, on 4+ it suffers D3 S4 AP5 hits with no Cover Saves, otherwise the blaze ends. Hex-Bolts cannot be combined with Special Issue Ammunition or another ammunition upgrade.")
clear_rules(icon); add_rule(icon,"r37-icon-rule","Icon of Chaos Undivided",'The bearer is a Summoning Point. Friendly non-Daemon Word Bearers units with at least one model within 6" automatically pass Morale and Pinning tests and may not voluntarily fail a break test while within the aura.')
clear_rules(darkch); add_rule(darkch,"r37-darkch-rule","Dark Channelling","Requires a Diabolist in the Detachment. After deployment but before the first turn, roll D6 for each upgraded squad: 1–3 Zealot (Fearless and Hatred); 4–5 models gain +1 Strength; 6 the unit gains Daemon (5+ Invulnerable Save and Fear), ceases to be Scoring, and in VP missions counts as destroyed at battle end even if it survives. Effects apply only to the upgraded squad, not Characters that later join it.")
clear_rules(diab); add_rule(diab,"r37-diab-rule","Diabolist","Gains Daemon and Preferred Enemy (Loyalists). May not select a Bike, Jetbike, Terminator Armour, Power Fist or Thunder Hammer. Enables eligible squads to purchase Dark Channelling. A Diabolist remains a Centurion for Accursed Crozius access; if it purchases one it counts as a Dark Apostle.")
std(diab,"Daemon"); add_infolink(diab,"r37-diab-pel","Preferred Enemy (Loyalists)",PELOY.get("id"),"rule")

# Burning Lore with actual power choices
clear_rules(burn)
add_rule(burn,"r37-burning-rule","Burning Lore","The model becomes a Psyker with Mastery Level 1 and selects exactly one psychic power from Biomancy or Telepathy. It follows the normal ProHammer rules for Psykers.")
# find exemplar ProHammer power selections already present in catalogue
power_ex={}
for e in cr.iter(C("selectionEntry")):
    n=e.get("name") or ""
    if n.startswith("Biomancy — ") or n.startswith("Telepathy — ") or n.startswith("Divination — ") or n.startswith("Telekinesis — "):
        power_ex.setdefault(n,e)

def clean_clone_option(src,newid):
    x=deep_prefix(src,newid+"-")
    x.set("id",newid); x.set("hidden","false")
    # remove conditions/modifiers inherited from another psyker context
    m=x.find(C("modifiers"))
    if m is not None:x.remove(m)
    cs=x.find(C("constraints"))
    if cs is not None:
        for z in list(cs):cs.remove(z)
    cons(x,newid+"-max","max",1)
    return x

def add_power_group(parent,id_,name,prefixes,count):
    g=group(parent,id_,name,count,count)
    ss=cont(g,"selectionEntries")
    # clear previously generated
    for z in list(ss):
        if (z.get("id") or "").startswith(id_+"-p-"):ss.remove(z)
    names=sorted([n for n in power_ex if any(n.startswith(p+" — ") for p in prefixes)])
    for n in names:
        src=power_ex[n]
        slug=re.sub(r"[^a-z0-9]+","-",n.lower()).strip("-")
        ss.append(clean_clone_option(src,id_+"-p-"+slug))
    return g

add_power_group(burn,"r37-burning-powers","Burning Lore — select 1 power",["Biomancy","Telepathy"],1)

# Favour of the Pantheon under Praetor/Centurion, roster max1
for hostid in ["hq-praetor","hq-centurion"]:
    host=ids.get(hostid)
    if host is None:continue
    fg=group(host,"r37-wb-favour-"+hostid,"Favour of the Pantheon — one non-named Word Bearers Independent Character per army",0,1,True)
    modifier(fg,fg.get("id")+"-show","set","hidden","false",[{"childId":"legion-xvii","scope":"roster"}])
    options=[
      ("aura","Daemonic Aura",15,"The model gains a 5+ Invulnerable Save."),
      ("mutation","Daemonic Mutation",15,"The model gains +1 Attack."),
      ("strength","Daemonic Strength",10,"The model gains +1 Strength."),
      ("wings","Daemonic Wings",20,"The model becomes Jump Infantry. This may not be combined with a Jump Pack, Bike, Jetbike or any form of Terminator Armour."),
      ("visage","Daemonic Visage",5,"An enemy unit which loses a close combat involving the bearer suffers an additional -1 Leadership when taking the resulting Morale test.")
    ]
    ss=cont(fg,"selectionEntries")
    for k,n,pts,txt in options:
        id_="r37-wb-favour-"+hostid+"-"+k
        e=next((z for z in ss.findall(C("selectionEntry")) if z.get("id")==id_),None)
        if e is None:e=ET.SubElement(ss,C("selectionEntry"))
        e.attrib.update({"id":id_,"name":n,"type":"upgrade","hidden":"false"})
        cons(e,id_+"-max","max",1); cost(e,pts); add_rule(e,id_+"-rule",n,txt); catlink(e,id_+"-cat","Word Bearers — Favour of the Pantheon",CAT_FAV)

# ---------- core unit patchers ----------
def squad_upgrade(parent,id_,name,per_model,modelid):
    e=sel(parent,id_,name,"upgrade",0,None,1)
    modifier(e,id_+"-cost","increment","pts",per_model,None,[{"childId":modelid,"scope":"root-entry","value":1,"repeats":1}])
    return e

def group_dynamic_max(g,id_,modelid,divisor=1):
    c=cons(g,id_,"max",0)
    modifier(g,id_+"-mod","increment",id_,1,None,[{"childId":modelid,"scope":"root-entry","value":divisor,"repeats":1,"roundUp":False}])
    return c

def strip_old_options(e):
    gs=e.find(C("selectionEntryGroups"))
    if gs is not None:
        for g in list(gs):
            if (g.get("id") or "").endswith("-options") or (g.get("name") or "")=="Options":
                gs.remove(g)

def transport_group(e,id_,allow,modelid=None,jumpid=None,rite_mandatory=False):
    g=group(e,id_,"Dedicated Transport",0,1)
    if rite_mandatory:
        modifier(g,id_+"-min-serrated","set",id_+"-min",1,[{"childId":"r25-rite-xvii-1-last-of-the-serrated-sun","scope":"roster"}])
    # links
    targets={"Rhino":"transport-rhino","Drop Pod":"transport-drop-pod","Dreadclaw Drop Pod":"transport-dreadclaw","Dreadnought Drop Pod":"transport-dreadnought-pod","Spartan Assault Tank":"hs-spartan"}
    for nm in allow:
        if nm=="Land Raider":
            # use direct models; one of the standard variants with sufficient capacity
            lg=group(g,id_+"-lr","Land Raider",0,1)
            for xnm,xid in [("Land Raider Phobos","hs-lr-phobos"),("Land Raider Proteus","hs-lr-proteus"),("Land Raider Achilles","hs-lr-achilles")]:
                l=elink(lg,id_+"-"+re.sub(r"[^a-z0-9]+","-",xnm.lower()),xnm,xid,0,None,1)
                if modelid:
                    modifier(l,l.get("id")+"-hide-size","set","hidden","true",[{"childId":modelid,"scope":"root-entry","type":"atLeast","value":6,"includeChildSelections":False}])
            if rite_mandatory:
                modifier(lg,lg.get("id")+"-hide-serrated","set","hidden","true",[{"childId":"r25-rite-xvii-1-last-of-the-serrated-sun","scope":"roster"}])
        else:
            t=targets[nm]; l=elink(g,id_+"-"+re.sub(r"[^a-z0-9]+","-",nm.lower()),nm,t,0,None,1)
            if modelid and nm in ("Drop Pod","Dreadclaw Drop Pod"):
                modifier(l,l.get("id")+"-hide-size","set","hidden","true",[{"childId":modelid,"scope":"root-entry","type":"atLeast","value":6,"includeChildSelections":False}])
            if rite_mandatory and nm=="Drop Pod":
                l.set("hidden","true"); modifier(l,l.get("id")+"-show-serrated","set","hidden","false",[{"childId":"r25-rite-xvii-1-last-of-the-serrated-sun","scope":"roster"}])
            if rite_mandatory and nm=="Spartan Assault Tank":
                modifier(l,l.get("id")+"-hide-serrated","set","hidden","true",[{"childId":"r25-rite-xvii-1-last-of-the-serrated-sun","scope":"roster"}])
    if jumpid:
        modifier(g,id_+"-hide-jump","set","hidden","true",[{"childId":jumpid,"scope":"root-entry"}])
    return g

# Covenant Zealots
zeal=ids["r41-unit-xvii-0-covenant-zealot-mob"]
clear_rules(zeal); strip_old_options(zeal); cost(zeal,30)
# clean generated model children if any
zs=cont(zeal,"selectionEntries")
for z in list(zs):
    if (z.get("id") or "").startswith("r37-wb-zeal-"):zs.remove(z)
zm=sel(zeal,"r37-wb-zeal-models","Covenant Zealots","model",5,10,40,10)
ov=sel(zeal,"r37-wb-zeal-overseer","Legion Overseer","model",0,1,1,1)
wg=group(ov,"r37-wb-zeal-overseer-weapon","Replace close combat weapon",0,1)
elink(wg,"r37-wb-zeal-pw","Power Weapon","gear-power-weapon",10,None,1)
elink(wg,"r37-wb-zeal-pf","Power Fist","gear-power-fist",15,None,1)
ilrule(zeal,"Driven to Slaughter","r37-wb-zeal-driven"); ilrule(zeal,"Expendable","r37-wb-zeal-exp")
add_rule(zeal,"r37-wb-zeal-wargear","Wargear","Covenant Zealots: Autopistol, close combat weapon, Flak Armour. Legion Overseer: Power Armour, Refractor Field, Bolt Pistol, close combat weapon, Frag Grenades, Krak Grenades.")
visibility(zeal,["legion-xvii"])

# Gal Vorbak patch all genuine XVII copies
def patch_gv(e):
    clear_rules(e); strip_old_options(e)
    legion_links(e,False); std(e,"Daemon"); std(e,"Fearless"); std(e,"Bulky"); std(e,"Rending")
    add_rule(e,e.get("id")+"-rend-restrict","Gal Vorbak Rending","The Rending rule applies only to the Gal Vorbak's close-combat attacks.")
    add_rule(e,e.get("id")+"-wargear","Wargear","Power Armour, Bolter, Bolt Pistol, close-combat weapon, Frag Grenades.")
    # total squad selector already present
    model=next((z for z in e.findall(f"./{C('selectionEntries')}/{C('selectionEntry')}") if (z.get("id") or "").endswith("-additional")),None)
    if model is None:model=sel(e,e.get("id")+"-additional","Gal Vorbak", "model",30,5,10,5)
    model.set("name","Gal Vorbak (total squad size)"); cost(model,30)
    # keep source base total: root 50 + 5*30 = 200
    cost(e,50)
    # under Serrated Sun legal max is 5 because required Drop Pod/Dreadclaw capacity and Bulky
    maxc=next((z for z in model.findall(f"./{C('constraints')}/{C('constraint')}") if z.get("type")=="max"),None)
    if maxc is None:maxc=cons(model,model.get("id")+"-max","max",10)
    maxc.set("value","10")
    modifier(model,e.get("id")+"-serrated-max5","set",maxc.get("id"),5,[{"childId":"r25-rite-xvii-1-last-of-the-serrated-sun","scope":"roster"}])

    rg=group(e,e.get("id")+"-special-ranged","Special weapon replacement — up to 1 per 5 models",0,0)
    rgmax=cons(rg,rg.get("id")+"-dynmax","max",0)
    modifier(rg,rg.get("id")+"-dyn","increment",rgmax.get("id"),1,None,[{"childId":model.get("id"),"scope":"root-entry","value":5,"repeats":1,"roundUp":False}])
    for nm,t,pts in [("Flamer","gear-flamer",5),("Meltagun","gear-meltagun",10),("Plasma Gun","gear-plasma-gun",15)]:
        elink(rg,e.get("id")+"-r-"+re.sub(r"[^a-z0-9]+","-",nm.lower()),nm,t,pts,None,2)
    mg=group(e,e.get("id")+"-special-melee","Close-combat weapon replacement — up to 1 per 5 models",0,0)
    mgmax=cons(mg,mg.get("id")+"-dynmax","max",0)
    modifier(mg,mg.get("id")+"-dyn","increment",mgmax.get("id"),1,None,[{"childId":model.get("id"),"scope":"root-entry","value":5,"repeats":1,"roundUp":False}])
    elink(mg,e.get("id")+"-m-pw","Power Weapon","gear-power-weapon",10,None,2)
    elink(mg,e.get("id")+"-m-pf","Power Fist","gear-power-fist",15,None,2)
    squad_upgrade(e,e.get("id")+"-krak","Krak Grenades — entire squad (+2 pts/model)",2,model.get("id"))
    squad_upgrade(e,e.get("id")+"-melta","Melta Bombs — entire squad (+5 pts/model)",5,model.get("id"))
    dm=group(e,e.get("id")+"-martyr","Dark Martyr",0,2)
    # one melee replacement plus optional armour
    dmg=group(dm,e.get("id")+"-martyr-melee","Replace close-combat weapon",0,1)
    elink(dmg,e.get("id")+"-dm-pw","Power Weapon","gear-power-weapon",10,None,1)
    elink(dmg,e.get("id")+"-dm-pf","Power Fist","gear-power-fist",15,None,1)
    elink(dmg,e.get("id")+"-dm-lc","Lightning Claw","gear-lightning-claw",15,None,1)
    elink(dm,e.get("id")+"-dm-aa","Artificer Armour","gear-artificer-armour",10,None,1)
    transport_group(e,e.get("id")+"-transport",["Land Raider","Dreadclaw Drop Pod","Spartan Assault Tank","Drop Pod"],model.get("id"),None,True)
    visibility(e,traitor_req())

gv_entries=[e for e in cr.iter(C("selectionEntry")) if (e.get("name") or "")=="Gal Vorbak Dark Brethren" and ("xvii" in (e.get("id") or "") or "wb" in (e.get("id") or "")) and "r46-al-reward" not in (e.get("id") or "")]
for e in gv_entries:patch_gv(e)

# Ashen Circle
ashen=ids["r41-unit-xvii-2-ashen-circle"]; clear_rules(ashen); strip_old_options(ashen); cost(ashen,50)
legion_links(ashen,True); ilrule(ashen,"Hardened Armour","r37-wb-ashen-hard"); ilrule(ashen,"Bitter Duty","r37-wb-ashen-bitter")
add_infolink(ashen,"r37-wb-ashen-axe","Axe-rake",AXE.get("id"),"profile")
add_rule(ashen,"r37-wb-ashen-axe-rule","Axe-rake",'A close-combat weapon. Attacks are resolved at +1 Strength. If an enemy Retreats from a close combat involving one or more Axe-rakes, reduce its Retreat distance by 1", to a minimum of 1".')
add_rule(ashen,"r37-wb-ashen-wg","Wargear","Hardened Power Armour, Jump Pack, Hand Flamer, Axe-rake, Frag Grenades.")
amodel=next((z for z in ashen.findall(f"./{C('selectionEntries')}/{C('selectionEntry')}") if (z.get("id") or "").endswith("-additional")),None)
amodel.set("name","Ashen Circle (total squad size)"); cost(amodel,25)
ag=group(ashen,"r37-wb-ashen-melee","Replace Axe-rake — any model",0,0)
agmax=cons(ag,"r37-wb-ashen-melee-dynmax","max",0)
modifier(ag,"r37-wb-ashen-melee-dyn","increment",agmax.get("id"),1,None,[{"childId":amodel.get("id"),"scope":"root-entry","value":1,"repeats":1}])
elink(ag,"r37-wb-ashen-rend","Rending Weapon","gear-rending",5,None,10)
elink(ag,"r37-wb-ashen-pw","Power Weapon","gear-power-weapon",10,None,10)
squad_upgrade(ashen,"r37-wb-ashen-krak","Krak Grenades — entire squad (+2 pts/model)",2,amodel.get("id"))
squad_upgrade(ashen,"r37-wb-ashen-melta","Melta Bombs — entire squad (+5 pts/model)",5,amodel.get("id"))
ic=group(ashen,"r37-wb-ashen-iconoclast","Iconoclast",0,2)
elink(ic,"r37-wb-ashen-pp","Plasma Pistol — replace Hand Flamer","gear-plasma-pistol",15,None,1)
elink(ic,"r37-wb-ashen-aa","Artificer Armour","gear-artificer-armour",10,None,1)
visibility(ashen,["legion-xvii"])

# Mhara Gal
mh=ids["r41-unit-xvii-3-mhara-gal-tainted-dreadnought"]; clear_rules(mh); strip_old_options(mh)
for n in ["Daemon","Fleet","It Will Not Die","Adamantium Will"]:std(mh,n)
for n in ["Daemonic Engine","Shroud of Dark Fire","Accursed"]:ilrule(mh,n,mh.get("id")+"-"+re.sub(r"[^a-z0-9]+","-",n.lower()))
add_rule(mh,"r37-wb-mhara-wg","Wargear","Dreadnought Close Combat Weapon with built-in Twin-linked Bolter; Plasma Cannon; Smoke Launchers; Searchlight.")
primary=group(mh,"r37-wb-mhara-primary","Replace Plasma Cannon",0,1)
for nm,t,pts in [("Multi-Melta","gear-multimelta",0),("Twin-linked Autocannon","dreadnought-p-tlac",5),("Twin-linked Lascannon","dreadnought-p-tllc",20)]:
    elink(primary,"r37-wb-mhara-"+re.sub(r"[^a-z0-9]+","-",nm.lower()),nm,t,pts,None,1)
second=sel(primary,"r37-wb-mhara-second-dccw","Second Dreadnought Close Combat Weapon with built-in Twin-linked Bolter","upgrade",0,None,1)
add_rule(second,"r37-wb-mhara-second-rule","Second Dreadnought Close Combat Weapon","If equipped with two Dreadnought Close Combat Weapons, the Mhara Gal gains +1 Attack.")
built=group(mh,"r37-wb-mhara-builtins","Replace built-in Twin-linked Bolter",0,1)
bmax=next(z for z in built.findall(f"./{C('constraints')}/{C('constraint')}") if z.get("type")=="max")
modifier(built,"r37-wb-mhara-builtins-max2","set",bmax.get("id"),2,[{"childId":"r37-wb-mhara-second-dccw","scope":"root-entry"}])
for nm,t,pts in [("Heavy Flamer","gear-heavy-flamer",10),("Meltagun","gear-meltagun",15),("Plasma Blaster","gear-plasma-blaster",20)]:
    elink(built,"r37-wb-mhara-b-"+re.sub(r"[^a-z0-9]+","-",nm.lower()),nm,t,pts,None,2)
transport_group(mh,"r37-wb-mhara-transport",["Dreadnought Drop Pod"])
visibility(mh,traitor_req())

# Procurators
proc=ids["r41-unit-xvii-4-procurator-squad"]; clear_rules(proc); strip_old_options(proc); cost(proc,30)
legion_links(proc,True); ilrule(proc,"Flesh Harvesters","r37-wb-proc-flesh"); ilrule(proc,"Narthecium","r37-wb-proc-nart"); ilrule(proc,"Reductor","r37-wb-proc-red")
add_rule(proc,"r37-wb-proc-wg","Wargear","Procurators: Power Armour, Bolt Pistol, Chainsword, Frag Grenades. Procurator Prime additionally: Artificer Armour, Narthecium and Reductor.")
pmodel=next((z for z in proc.findall(f"./{C('selectionEntries')}/{C('selectionEntry')}") if (z.get("id") or "").endswith("-additional")),None)
pmodel.set("name","Procurator Squad (total squad size)"); cost(pmodel,20)
for gid,title,opts in [
 ("r37-wb-proc-melee","Chainsword replacement — up to 1 per 5 models",[("Rending Weapon","gear-rending",5),("Power Weapon","gear-power-weapon",10),("Power Fist","gear-power-fist",15)]),
 ("r37-wb-proc-pistol","Bolt Pistol replacement — up to 1 per 5 models",[("Hand Flamer","gear-hand-flamer",5),("Plasma Pistol","gear-plasma-pistol",15)])]:
    g=group(proc,gid,title,0,0); mc=cons(g,gid+"-dynmax","max",0)
    modifier(g,gid+"-dyn","increment",mc.get("id"),1,None,[{"childId":pmodel.get("id"),"scope":"root-entry","value":5,"repeats":1}])
    for nm,t,pts in opts:elink(g,gid+"-"+re.sub(r"[^a-z0-9]+","-",nm.lower()),nm,t,pts,None,2)
squad_upgrade(proc,"r37-wb-proc-krak","Krak Grenades — entire squad (+2 pts/model)",2,pmodel.get("id"))
squad_upgrade(proc,"r37-wb-proc-melta","Melta Bombs — entire squad (+5 pts/model)",5,pmodel.get("id"))
jump=squad_upgrade(proc,"r37-wb-proc-jump","Jump Packs — entire squad (+15 pts/model)",15,pmodel.get("id"))
add_rule(jump,"r37-wb-proc-jump-rule","Jump Packs","If every model purchases Jump Packs, the unit becomes Jump Infantry and may not select a Dedicated Transport.")
prime=group(proc,"r37-wb-proc-prime","Procurator Prime",0,1)
pmg=group(prime,"r37-wb-proc-prime-melee","Replace Chainsword",0,1)
elink(pmg,"r37-wb-proc-prime-pw","Power Weapon","gear-power-weapon",10,None,1)
elink(pmg,"r37-wb-proc-prime-pf","Power Fist","gear-power-fist",15,None,1)
transport_group(proc,"r37-wb-proc-transport",["Rhino","Drop Pod","Dreadclaw Drop Pod"],None,jump.get("id"))
visibility(proc,traitor_req())

# Possessed
pos=ids["r41-unit-xvii-5-possessed-marine-squad"]; clear_rules(pos); strip_old_options(pos); cost(pos,0)
cons(pos,"r37-wb-possessed-roster-max","max",2,"selections","roster",False)
legion_links(pos,False); std(pos,"Daemon"); std(pos,"Fearless"); ilrule(pos,"Daemonkin","r37-wb-poss-daemonkin")
add_rule(pos,"r37-wb-poss-wg","Wargear","Power Armour, Bolt Pistol, close-combat weapon.")
pom=next((z for z in pos.findall(f"./{C('selectionEntries')}/{C('selectionEntry')}") if (z.get("id") or "").endswith("-additional")),None)
pom.set("name","Possessed Marines (total squad size)"); cost(pom,26)
squad_upgrade(pos,"r37-wb-poss-frag","Frag Grenades — entire squad (+1 pt/model)",1,pom.get("id"))
squad_upgrade(pos,"r37-wb-poss-krak","Krak Grenades — entire squad (+2 pts/model)",2,pom.get("id"))
champ=sel(pos,"r37-wb-poss-champ","Upgrade one Possessed Marine to Possessed Champion","upgrade",10,None,1)
cg=group(champ,"r37-wb-poss-champ-melee","Possessed Champion — replace close-combat weapon",0,1)
elink(cg,"r37-wb-poss-champ-rend","Rending Weapon","gear-rending",5,None,1)
elink(cg,"r37-wb-poss-champ-pw","Power Weapon","gear-power-weapon",10,None,1)
elink(cg,"r37-wb-poss-champ-pf","Power Fist","gear-power-fist",15,None,1)
transport_group(pos,"r37-wb-poss-transport",["Rhino","Dreadclaw Drop Pod"])
visibility(pos,traitor_req())

# ---------- named characters ----------
def named_base(e,fan=True,daemon=False,mol=True,ic=True):
    clear_rules(e); legion_links(e,fan)
    if ic:std(e,"Independent Character")
    if mol:std(e,"Master of the Legion")
    if daemon:std(e,"Daemon")

arg=ids["r41-unit-xvii-6-argel-tal"]; named_base(arg,False,True,True,True); std(arg,"Fearless")
add_infolink(arg,"r37-wb-arg-cust","Custodian Spear",CUST.get("id"),"profile"); add_infolink(arg,"r37-wb-arg-custg","Custodian Spear — Foeblaster Boltgun",CUSTG.get("id"),"profile")
add_rule(arg,"r37-wb-arg-spear-rule","Custodian Spear","Two-Handed, Master-crafted Power Weapon with an inbuilt Foeblaster Boltgun. During the first round of each close combat, melee attacks are resolved at +1 Strength and +1 Initiative.")
add_rule(arg,"r37-wb-arg-ret","Lord of the Gal Vorbak","Argel Tal may select one Gal Vorbak Dark Brethren Squad as his personal retinue. It occupies no separate Elites selection; together they count as a single HQ selection.")
visibility(arg,traitor_req())

ere=ids["r41-unit-xvii-7-high-chaplain-erebus"]; named_base(ere,True,False,True,True)
add_infolink(ere,"r37-wb-ere-croz","Master-crafted Accursed Crozius",CROZ.get("id"),"profile"); std(ere,"Master-Crafted")
add_infolink(ere,"r37-wb-ere-anath","Anathame Dagger",ANATH.get("id"),"profile")
add_rule(ere,"r37-wb-ere-high","High Chaplain","Erebus counts as both a Legion Chaplain Consul and a Diabolist for all Word Bearers rules, construction requirements and Rites. He fulfils The Dark Shepherds and enables Dark Channelling.")
add_rule(ere,"r37-wb-ere-croz-rule","Master-crafted Accursed Crozius","Uses the normal Accursed Crozius rules and is additionally Master-crafted: re-roll one failed To Hit roll per turn. It grants a 4+ Invulnerable Save and is a Summoning Point.")
add_rule(ere,"r37-wb-ere-anath-rule","Anathame Dagger","During an Assault phase, exchange one normal Attack for one attack with the dagger. Invulnerable Saves cannot be taken. An unsaved Wound against a non-Vehicle model becomes a Massive Wound (D3). Against Vehicles it has no additional effect.")
add_rule(ere,"r37-wb-ere-psy","Psyker (Mastery Level 1)","Erebus is a Mastery Level 1 Psyker and has Burning Lore at no additional cost.")
add_power_group(ere,"r37-wb-ere-powers","Burning Lore — select 1 power",["Biomancy","Telepathy"],1)
visibility(ere,traitor_req())

kor=ids["r41-unit-xvii-8-kor-phaeron-the-black-cardinal"]; named_base(kor,True,False,True,True); add_infolink(kor,"r37-wb-kor-fnp","Feel No Pain (6+)",FNP6.get("id"),"rule")
add_rule(kor,"r37-wb-kor-term","Terminus Consolaris","Counts as Cataphractii Terminator Armour. Its life-support systems grant Feel No Pain (6+), already reflected in Kor Phaeron's profile/rules.")
add_rule(kor,"r37-wb-kor-black","Black Cardinal","Kor Phaeron counts as both a Dark Apostle and a Diabolist for all Word Bearers rules, requirements and Rites. He fulfils The Dark Shepherds and enables Dark Channelling.")
add_rule(kor,"r37-wb-kor-jealous","Jealous Command","If Kor Phaeron is included, he must be the army's Warlord unless Lorgar is also included.")
add_rule(kor,"r37-wb-kor-psy","Psyker (Mastery Level 1)","Kor Phaeron is a Mastery Level 1 Psyker and has Burning Lore at no additional cost.")
add_power_group(kor,"r37-wb-kor-powers","Burning Lore — select 1 power",["Biomancy","Telepathy"],1)
visibility(kor,traitor_req())

zar=ids["r41-unit-xvii-9-zardu-layak"]; named_base(zar,False,True,True,True); std(zar,"Zealot")
add_rule(zar,"r37-wb-zar-crimson","Crimson Apostle","Zardu Layak counts as both a Dark Apostle and a Diabolist for all Word Bearers rules, army construction requirements and Rites of War.")
add_rule(zar,"r37-wb-zar-channel","Dark Channeler","When rolling on the Dark Channelling table for a unit in an army containing Zardu Layak, add +1 to the result, to a maximum of 6.")
add_rule(zar,"r37-wb-zar-reign","Reign of Fire","If Zardu Layak is the army's Warlord, Ashen Circle Squads may be selected as Troops and may fulfil compulsory Troops selections.")
add_rule(zar,"r37-wb-zar-psy","Psyker (Mastery Level 2)","Zardu Layak selects two powers from Malefic Daemonology and follows the normal ProHammer rules for a Mastery Level 2 Psyker.")
# Malefic powers from ProHammer v2.4
mg=group(zar,"r37-wb-zar-malefic","Malefic Daemonology — select 2 powers",2,2)
mal=[
 ("Summoning",'Conjuration — Range 12". Summon 8 Bloodletters, 9 Pink Horrors, 7 Plaguebearers, 6 Daemonettes, 4 Flesh Hounds, 3 Flamers, 4 Nurglings or 6 Seekers.',None),
 ("Cursed Earth",'Blessing — targets Psyker. All Daemon models within 12" gain +1 to Invulnerable Saves; Deep Striking Daemons do not scatter if the centre model is placed within 12".',None),
 ("Dark Flame","Template, S4 AP5, Assault 1, Soul Blaze, Torrent.",("Template","4","5","Assault 1, Soul Blaze, Torrent")),
 ("Possession",'Conjuration — Range 6". Summon one Bloodthirster, Lord of Change, Great Unclean One or Keeper of Secrets. If successful, the invoking Psyker is removed as a casualty. Only usable by Mastery Level 2+.',None),
 ("Sacrifice",'Conjuration — Range 6". Summon one Herald of Khorne, Tzeentch, Nurgle or Slaanesh with 30 points of wargear. If successful, one friendly model within 6" suffers a Wound with no saves of any kind.',None),
 ("Incursion",'Conjuration — Range 12". Summon 3 Bloodcrushers, 4 Screamers, 3 Plague Drones or 3 Fiends.',None),
 ("Infernal Gaze",'Beam — Range 18", S3 AP4, Assault 1, Armourbane, Fleshbane.',('18"',"3","4","Assault 1, Armourbane, Fleshbane"))
]
for n,txt,wp in mal:
    id_="r37-wb-zar-mal-"+re.sub(r"[^a-z0-9]+","-",n.lower()).strip("-")
    e=sel(mg,id_,n,"upgrade",0,None,1)
    add_rule(e,id_+"-rule",n,txt)
    if wp:profile(e,id_+"-prof",n,"prof-weapon",{"Range":wp[0],"S":wp[1],"AP":wp[2],"Type":wp[3]})
# Anakatis nested
akroot=ids["r41-unit-xvii-10-anakatis-kul-blade-slaves"]; akroot.set("hidden","true")
clear_rules(akroot); std(akroot,"Daemon"); std(akroot,"Fearless"); std(akroot,"Furious Charge"); std(akroot,"It Will Not Die"); std(akroot,"Bulky")
add_rule(akroot,"r37-wb-ak-mind","Mindless Killers","The Anakatis Kul may only be selected as part of Zardu Layak's unit. While Zardu lives they remain part of his unit. If he is slain, surviving Blade-Slaves must charge the nearest eligible enemy in each Assault phase if able and must Pursue retreating enemies whenever legally able.")
add_rule(akroot,"r37-wb-ak-wg","Wargear","Power Armour, pair of Rending Weapons, Plasma Pistol.")
# ensure 2 models shown
akss=cont(akroot,"selectionEntries")
if not any((x.get("id") or "")=="r37-wb-ak-models" for x in akss):
    sel(akroot,"r37-wb-ak-models","Anakatis Kul Blade-Slaves","model",0,2,2,2)
# nested copy
zss=cont(zar,"selectionEntries")
for old in list(zss):
    if old.get("id")=="r37-wb-zardu-anakatis":zss.remove(old)
ak=deep_prefix(akroot,"r37-wb-zardu-anakatis-copy-"); ak.set("id","r37-wb-zardu-anakatis"); ak.set("hidden","false"); cost(ak,100)
# no FOC on nested
cls=ak.find(C("categoryLinks"))
if cls is not None:ak.remove(cls)
cons(ak,"r37-wb-zardu-anakatis-max","max",1)
zss.append(ak)
add_rule(zar,"r37-wb-zar-ak","Anakatis Kul","Zardu Layak may be accompanied by two Anakatis Kul Blade-Slaves for +100 points. Zardu and the Blade-Slaves count as a single HQ selection.")
# optional Warlord record for Reign of Fire
warl=sel(zar,"r37-wb-zardu-warlord","Zardu Layak is the Warlord","upgrade",0,None,1)
visibility(zar,traitor_req())

hol=ids["r41-unit-xvii-11-hol-beloth"]; named_base(hol,True,False,True,True)
add_rule(hol,"r37-wb-hol-ward","Hexaglyphic Ward","The first unsaved Wound suffered by Hol Beloth during the battle is ignored. If it would be a Massive Wound, the Ward is used before rolling D3 Wounds. The Ward then has no further effect.")
add_rule(hol,"r37-wb-hol-exhort","Exhortation of Battle","Once per battle at the beginning of a Word Bearers Assault phase, until the end of that phase Word Bearers models with WS lower than 5 count as WS5; models already WS5+ are unaffected.")
add_rule(hol,"r37-wb-hol-tw","Tainted Weapon","Hol Beloth's Tainted Weapon uses the Word Bearers Armoury rule: unsaved Wounds become Massive Wounds (D3), but it is not a Power Weapon and does not ignore Armour Saves.")
visibility(hol,traitor_req())

# Lorgar
lor=ids["r41-unit-xvii-12-xvii-lorgar-aurelian-the-urizen"]; clear_rules(lor)
std(lor,"Primarch"); legion_links(lor,True); add_infolink(lor,"r37-wb-lorgar-pa","Primarch Armour",PRIMARM.get("id"),"rule")
add_infolink(lor,"r37-wb-lorgar-illum","Illuminarum",ILL.get("id"),"profile")
add_rule(lor,"r37-wb-lorgar-armour","Armour of the Word","Counts as Primarch Armour. Enemy Psykers suffer -1 Leadership when taking a Psychic Test to invoke a power which directly targets Lorgar or a unit he has joined.")
add_rule(lor,"r37-wb-lorgar-illum-rule","Illuminarum","Master-crafted Power Weapon. Attacks are resolved at +2 Strength and have Concussive. Lorgar may also use Illuminarum to make a Smash attack using normal ProHammer rules.")
add_rule(lor,"r37-wb-lorgar-voice","Voice of the Urizen",'Friendly Word Bearers units with at least one model within 12" of Lorgar may re-roll failed Morale and Pinning tests; the second result must be accepted.')
add_rule(lor,"r37-wb-lorgar-fan","Lorgar — Fanatical Devotion","A friendly Word Bearers unit joined by Lorgar has Hatred (Infantry) while he remains part of that unit: in the first round of a melee against Infantry, re-roll failed close-combat To Hit rolls.")
add_rule(lor,"r37-wb-lorgar-oratory","Dark Oratory",'At the beginning of each Word Bearers turn, nominate one friendly Word Bearers unit with at least one model within 12". Until the next Word Bearers turn, it may re-roll close-combat To Hit rolls of 1. Only one unit may benefit at a time.')
trans=sel(lor,"r37-wb-lorgar-transfigured","Lorgar Transfigured","upgrade",75,None,1,hidden=True)
if TRAITOR: modifier(trans,"r37-wb-lorgar-trans-show","set","hidden","false",[{"childId":TRAITOR,"scope":"roster"}])
else: trans.set("hidden","false")
add_rule(trans,"r37-wb-lorgar-trans-rule","Lorgar Transfigured","Gains Psyker (Mastery Level 3), Psychic Ascendancy, and Illuminarum additionally becomes a Force Weapon.")
add_rule(trans,"r37-wb-lorgar-ascend","Psychic Ascendancy","May ignore the first -1 Leadership penalty suffered from Disturbance in the Warp during each player turn. Further penalties apply normally.")
add_rule(trans,"r37-wb-lorgar-force","Illuminarum — Transfigured","Illuminarum retains Master-crafted, +2 Strength, Concussive and Smash and additionally counts as a Force Weapon. After inflicting one or more unsaved Wounds, Lorgar may activate it using normal ProHammer Force Weapon rules.")
add_power_group(trans,"r37-wb-lorgar-trans-powers","Lorgar Transfigured — select 3 powers",["Divination","Telekinesis"],3)
# Retinues
rg=group(lor,"r37-wb-lorgar-retinue","Primarch Retinue — choose up to one (no separate FOC slot)",0,1)
# clone known complete retinues
for label,srcid in [("Legion Honour Guard Squad","hq-praetor-ret-honour"),("Legion Terminator Command Squad","hq-praetor-ret-termcommand")]:
    src=ids.get(srcid)
    if src is not None:
        cp=deep_prefix(src,"r37-wb-lorgar-"+re.sub(r"[^a-z0-9]+","-",label.lower())+"-"); cp.set("id","r37-wb-lorgar-"+re.sub(r"[^a-z0-9]+","-",label.lower())); cp.set("name",label)
        cls=cp.find(C("categoryLinks"))
        if cls is not None:cp.remove(cls)
        cons(cp,cp.get("id")+"-max","max",1)
        cont(rg,"selectionEntries").append(cp)
# Gal Vorbak retinue copy from patched base
gvbase=ids["r41-unit-xvii-1-gal-vorbak-dark-brethren"]
gvc=deep_prefix(gvbase,"r37-wb-lorgar-gv-"); gvc.set("id","r37-wb-lorgar-gv"); gvc.set("name","Gal Vorbak Dark Brethren")
cls=gvc.find(C("categoryLinks"))
if cls is not None:gvc.remove(cls)
cons(gvc,"r37-wb-lorgar-gv-max","max",1)
if TRAITOR:
    gvc.set("hidden","true"); modifier(gvc,"r37-wb-lorgar-gv-show","set","hidden","false",[{"childId":TRAITOR,"scope":"roster"}])
cont(rg,"selectionEntries").append(gvc)
visibility(lor,["legion-xvii"])

# ---------- Rites ----------
DARK="r25-rite-xvii-0-the-dark-brethren"
SERR="r25-rite-xvii-1-last-of-the-serrated-sun"
dark=ids[DARK]; serr=ids[SERR]
dark.set("name","Word Bearers Rite of War — The Dark Brethren")
serr.set("name","Word Bearers Rite of War — Last of the Serrated Sun")
clear_rules(dark); clear_rules(serr)
add_rule(dark,"r37-wb-dark-arch","Arch-Traitors","All Word Bearers Independent Characters in the Detachment may re-roll failed close-combat To Hit rolls against Loyalist models.")
add_rule(dark,"r37-wb-dark-signs","Signs and Portents","After deployment but before the first turn, select one Word Bearers Troops unit and roll D6. On 1–3, all enemy units may re-roll failed close-combat To Hit rolls against that unit. On 4–6, the selected unit may re-roll failed close-combat To Hit rolls against all enemy units.")
add_rule(dark,"r37-wb-dark-beyond","From Beyond","If the army includes its Daemons of the Ruinstorm Covenant, that Covenant may use the normal Ruinstorm Allied Detachment chart instead of the restricted Covenant chart: HQ 1; Troops 1–2; Elites 0–1; Fast Attack 0–1; Heavy Support 0–1. The 25% Covenant cap is removed and normal Allied points restrictions apply. Word Bearers and Ruinstorm Daemons are Sworn Brothers. Before deployment each Ruinstorm Daemon unit is designated Manifested or Summoned: Manifested units use normal Ruinstorm deployment/Manifestation rules; Summoned units begin in Reserve and use Daemonic Summoning. In addition, the Rite specifically permits an Allied Detachment selected from Codex: Chaos Daemons without preventing the Word Bearers' normal Covenant.")
add_rule(dark,"r37-wb-dark-hell","Hell Follows With Them","Whenever an enemy Psyker suffers a Wound from Perils of the Warp, that Wound becomes a Massive Wound and inflicts D3 Wounds instead of 1.")
add_rule(dark,"r37-wb-dark-limit","Limitations","Traitor Word Bearers only. Must include at least one Diabolist. May include no more than one Heavy Support choice. No Fortification or Allied Detachment drawn from another Space Marine Legion. Any Allied Detachment other than Chaos Daemons is treated as Desperate Allies.")
visibility(dark,traitor_req())

add_rule(serr,"r37-wb-serr-company","Company of Monsters","Gal Vorbak Dark Brethren may be selected as Troops and may fulfil compulsory Troops selections. Every Gal Vorbak unit in the Detachment must purchase either a Legion Drop Pod or a Dreadclaw Drop Pod as a Dedicated Transport.")
add_rule(serr,"r37-wb-serr-drop","Drop Elite","Any Word Bearers Infantry unit which may normally purchase a Rhino as a Dedicated Transport may instead purchase a Legion Drop Pod at its normal points cost.")
add_rule(serr,"r37-wb-serr-burning","Burning Sun",'Whenever a Legion Drop Pod or Dreadclaw belonging to this Detachment arrives by Deep Strike, every enemy unit with at least one model within 12" of its final position immediately takes a Pinning test. A unit takes only one test for each arriving Pod.')
add_rule(serr,"r37-wb-serr-limit","Limitations","Traitor Word Bearers only. All Infantry must begin in Reserve and enter using a Deep Striking Drop Pod, Teleportation Transponders or embarked aboard a Flyer Transport. The army may not include Immobile units, a Fortification or an Allied Detachment.")
visibility(serr,traitor_req())

# Dark Brethren mechanical Diabolist + Heavy Support max 1
fld=force_hidden_link("r37-wb-diab-force","Word Bearers — Diabolist",CAT_DIAB)
cons(fld,"r37-wb-diab-min","min",0,"selections","parent",True)
modifier(fld,"r37-wb-diab-min-dark","set","r37-wb-diab-min",1,[{"childId":DARK,"scope":"roster"}])
heavy=next((x for x in fcls.findall(G("categoryLink")) if x.get("targetId")=="cat-heavy"),None)
if heavy is not None:
    cons(heavy,"r37-wb-dark-heavy-max","max",3,"selections","parent",False)
    modifier(heavy,"r37-wb-dark-heavy-set1","set","r37-wb-dark-heavy-max",1,[{"childId":DARK,"scope":"roster"}])

# Last Serrated Sun Troops Gal Vorbak copy
rootse=cont(cr,"selectionEntries")
old=next((x for x in rootse.findall(C("selectionEntry")) if x.get("id")=="r37-wb-serrated-gv-troops"),None)
if old is not None:rootse.remove(old)
gv=deep_prefix(gvbase,"r37-wb-serrated-gv-copy-"); gv.set("id","r37-wb-serrated-gv-troops"); gv.set("name","Gal Vorbak Dark Brethren — Serrated Sun Troops")
set_primary_cat(gv,"cat-troops","Troops"); visibility(gv,traitor_req()+[SERR]); rootse.append(gv)

# Zardu Warlord Ashen Circle Troops copy
old=next((x for x in rootse.findall(C("selectionEntry")) if x.get("id")=="r37-wb-zardu-ashen-troops"),None)
if old is not None:rootse.remove(old)
ac=deep_prefix(ashen,"r37-wb-zardu-ashen-copy-"); ac.set("id","r37-wb-zardu-ashen-troops"); ac.set("name","Ashen Circle — Reign of Fire Troops")
set_primary_cat(ac,"cat-troops","Troops"); visibility(ac,traitor_req()+["r37-wb-zardu-warlord"]); rootse.append(ac)

# Drop Elite: add Drop Pod to any existing Dedicated Transport group that has Rhino and not already Drop Pod
drop_added=0
for g in cr.iter(C("selectionEntryGroup")):
    if "dedicated transport" not in (g.get("name") or "").lower():continue
    links=g.findall(f"./{C('entryLinks')}/{C('entryLink')}")
    if not any(x.get("targetId")=="transport-rhino" for x in links):continue
    if any(x.get("targetId")=="transport-drop-pod" for x in links):continue
    l=elink(g,"r37-wb-serrated-drop-"+hashlib.sha1((g.get("id") or "").encode()).hexdigest()[:10],"Legion Drop Pod — Last of the Serrated Sun","transport-drop-pod",0,None,1,True)
    modifier(l,l.get("id")+"-show","set","hidden","false",[{"childId":"legion-xvii","scope":"roster"},{"childId":SERR,"scope":"roster"}])
    drop_added+=1

# ---------- Daemonic Covenant configuration record ----------
# Put under Army Configuration if present.
armyconf=next((e for e in cr.iter(C("selectionEntry")) if (e.get("name") or "")=="Army Configuration"),None)
if armyconf is not None:
    covsel=sel(armyconf,"r37-wb-covenant-config","Daemonic Covenant — external Ruinstorm Allied Detachment","upgrade",0,None,1,True)
    visibility(covsel,traitor_req())
    add_infolink(covsel,"r37-wb-cov-rule","Daemonic Covenant",COV.get("id"),"rule")
    add_infolink(covsel,"r37-wb-cov-summ","Daemonic Summoning",SUMM.get("id"),"rule")

# ---------- clean giant Source Entry blocks on XVII roots and copies ----------
for e in cr.iter(C("selectionEntry")):
    if "xvii" in (e.get("id") or "") or e.get("id") in [DARK,SERR]:
        rs=e.find(C("rules"))
        if rs is not None:
            for r in list(rs):
                if (r.get("name") or "").lower() in ("source entry","special rules","word bearers — legion rules & armoury"):
                    rs.remove(r)

# ---------- revisions ----------
cr.set("revision","37"); cr.set("gameSystemRevision","3")
gr.set("revision","3")
ct.write(CAT,encoding="utf-8",xml_declaration=True)
ET.register_namespace("",GNS); gt.write(GST,encoding="utf-8",xml_declaration=True)
it=ET.parse(IDX); ir=it.getroot(); ET.register_namespace("",INS)
for x in ir.iter(I("dataIndexEntry")):
    if x.get("filePath")=="Legiones Astartes.cat":x.set("dataRevision","37")
    if x.get("filePath")=="Prohammer 30k.gst":x.set("dataRevision","3")
it.write(IDX,encoding="utf-8",xml_declaration=True)

# ---------- validation ----------
cc=ET.parse(CAT).getroot(); gg=ET.parse(GST).getroot()
checks=[]; notes=[]
def ck(label,ok):
    checks.append((label,bool(ok)))
    if not ok:raise RuntimeError("R37 validation failed: "+label)
ck("CAT revision 37",cc.get("revision")=="37")
ck("GST revision 3",gg.get("revision")=="3")
ck("CAT points to GST 3",cc.get("gameSystemRevision")=="3")
idx=IDX.read_text(encoding="utf-8")
ck("Index CAT 37",'filePath="Legiones Astartes.cat"' in idx and 'dataRevision="37"' in idx)
ck("Index GST 3",'filePath="Prohammer 30k.gst"' in idx and 'dataRevision="3"' in idx)
ck("No ns0 prefixes","ns0:" not in idx and "ns0:" not in CAT.read_text(encoding="utf-8")[:500] and "ns0:" not in GST.read_text(encoding="utf-8")[:500])

cids={e.get("id"):e for e in cc.iter() if e.get("id")}
ck("Possessed 0-2 enforced",any(z.get("id")=="r37-wb-possessed-roster-max" for z in cids["r41-unit-xvii-5-possessed-marine-squad"].iter(C("constraint"))))
ck("Anakatis standalone hidden",cids["r41-unit-xvii-10-anakatis-kul-blade-slaves"].get("hidden")=="true")
ck("Zardu has Anakatis nested",cids.get("r37-wb-zardu-anakatis") is not None)
ck("Lorgar Transfigured exists",cids.get("r37-wb-lorgar-transfigured") is not None)
ck("Lorgar retinue exists",cids.get("r37-wb-lorgar-retinue") is not None)
ck("Serrated Sun Gal Vorbak Troops exists",cids.get("r37-wb-serrated-gv-troops") is not None)
ck("Reign of Fire Ashen Troops exists",cids.get("r37-wb-zardu-ashen-troops") is not None)
ck("Dark Shepherd category exists",any(x.get("id")==CAT_DARK_AP for x in gg.iter(G("categoryEntry"))))
ck("Dark Brethren Diabolist category exists",any(x.get("id")==CAT_DIAB for x in gg.iter(G("categoryEntry"))))
ck("Favour roster limit category exists",any(x.get("id")==CAT_FAV for x in gg.iter(G("categoryEntry"))))
# No giant source dump on main XVII entries.
bad=[]
for e in cc.iter(C("selectionEntry")):
    if (e.get("id") or "").startswith("r41-unit-xvii-") or (e.get("id") or "") in (DARK,SERR):
        for r in e.findall(f"./{C('rules')}/{C('rule')}"):
            if (r.get("name") or "").lower() in ("source entry","word bearers — legion rules & armoury"):bad.append((e.get("id"),r.get("name")))
ck("No XVII Source Entry dumps",not bad)
# Named special units normal capitalization
caps=[]
for e in cc.iter(C("selectionEntry")):
    if (e.get("id") or "").startswith("r41-unit-xvii-"):
        n=e.get("name") or ""; letters=re.sub(r"[^A-Za-z]","",n)
        if len(letters)>3 and letters==letters.upper():caps.append(n)
ck("XVII display names normal capitalization",not caps)

lines=[
"Live R37 — Word Bearers implementation",
"Input CAT=36/GST=2 -> CAT=37/GST=3","",
"SOURCE BASIS:",
"- Forces of the Legions, XVII Word Bearers section (pp.190–204 of the uploaded PDF).",
"- Legiones Astartes Army List for generic Legion units, transports, wargear and Rites framework.",
"- ProHammer Classic v2.4 for psychic disciplines and standard rules.",
"- Daemons of the Ruinstorm Google Doc for the normal Ruinstorm Allied Detachment used by The Dark Brethren's From Beyond override.","",
"IMPLEMENTED:",
"- Rebuilt the Word Bearers Legion selector as rule links rather than a giant Source Entry dump.",
"- Dark Shepherds is mechanically enforced: a Word Bearers force requires a Chaplain/Dark Apostle-equivalent.",
"- Added canonical shared Word Bearers rules and reused the R36 shared-rule structure.",
"- Reworked Accursed Crozius, Tainted Weapon, Burning Lore, Hex-Bolts, Icon of Chaos Undivided, Diabolist and Dark Channelling.",
"- Burning Lore now contains actual selectable Biomancy/Telepathy powers.",
"- Added Favour of the Pantheon to non-named Praetor/Centurion characters with a roster-wide max of one.",
"- Rebuilt/fixed Covenant Zealots, Gal Vorbak, Ashen Circle, Mhara Gal, Procurators and Possessed: correct costs, squad-size scaling, weapon caps, whole-squad costs, 0-2 Possessed cap, champion/leader options and transports.",
"- Gal Vorbak copies/retinues receive the same corrected implementation; Serrated Sun transport requirement is enforced.",
"- Argel Tal, Erebus, Kor Phaeron, Zardu Layak, Hol Beloth and Lorgar now carry their actual rules/wargear instead of sparse source shells.",
"- Anakatis Kul removed as a standalone Elites choice and nested under Zardu Layak for +100 points.",
"- Zardu has a full selectable Malefic Daemonology power pool from ProHammer v2.4.",
"- Lorgar Transfigured implemented at +75 points with three selectable Divination/Telekinesis powers and Primarch retinues.",
"- The Dark Brethren mechanically requires a Diabolist and caps Heavy Support at one.",
"- Last of the Serrated Sun creates compulsory-capable Gal Vorbak Troops and adds Drop Pod access to Rhino-capable Infantry transport groups.",
f"- Added Drop Pod Rite access to {drop_added} additional Rhino-capable Dedicated Transport groups.",
"- Added a Word Bearers Daemonic Covenant configuration record. The actual Ruinstorm units remain sourced from the separate Daemons of the Ruinstorm army list rather than duplicated into the Legion catalogue.","",
"VALIDATION:"
]
lines += [f'- {"PASS" if ok else "FAIL"}: {label}' for label,ok in checks]
if TRAITOR is None:lines += ["","NOTE: No explicit Traitor selector was detected; Traitor-only text remains present but visibility could not be keyed to an allegiance selector."]
OUT.write_text("\n".join(lines)+"\n",encoding="utf-8")
print(OUT.read_text())
