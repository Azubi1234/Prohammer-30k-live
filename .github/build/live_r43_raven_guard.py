from pathlib import Path
import copy, hashlib, re, collections, xml.etree.ElementTree as ET

CAT=Path("Legiones Astartes.cat"); GST=Path("Prohammer 30k.gst"); IDX=Path("index.xml")
OUT=Path("inspection-live-r43-raven-guard.txt")
CNS="http://www.battlescribe.net/schema/catalogueSchema"; GNS="http://www.battlescribe.net/schema/gameSystemSchema"; INS="http://www.battlescribe.net/schema/dataIndexSchema"
ET.register_namespace("",CNS)
C=lambda t:f"{{{CNS}}}{t}"; G=lambda t:f"{{{GNS}}}{t}"; I=lambda t:f"{{{INS}}}{t}"
ct=ET.parse(CAT); cr=ct.getroot(); gt=ET.parse(GST); gr=gt.getroot()
if cr.get("revision")!="42": raise RuntimeError(f"R43 expected CAT42, got {cr.get('revision')}")
if gr.get("revision")!="7": raise RuntimeError(f"R43 expected GST7, got {gr.get('revision')}")
baseline_ids=collections.Counter(x.get("id") for x in cr.iter() if x.get("id"))

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
def cost(p,val):
    cs=cont(p,"costs",before=("modifiers",));x=next((z for z in cs.findall(C("cost")) if z.get("typeId")=="pts"),None)
    if x is None:x=ET.SubElement(cs,C("cost"),{"name":"Points","typeId":"pts"})
    x.set("value",str(val));return x
def modifier(p,id_,typ,field,value,conditions=None,repeats=None):
    ns=qns(p);ms=cont(p,"modifiers");q=f"{{{ns}}}modifier";x=next((z for z in ms.findall(q) if z.get("id")==id_),None)
    if x is None:x=ET.SubElement(ms,q)
    x.attrib.update({"id":id_,"type":typ,"field":field,"value":str(value)})
    for ch in list(x):x.remove(ch)
    if repeats:
        rs=ET.SubElement(x,f"{{{ns}}}repeats")
        for rp in repeats:
            ET.SubElement(rs,f"{{{ns}}}repeat",{"field":rp.get("field","selections"),"scope":rp.get("scope","root-entry"),"value":str(rp.get("value",1)),"shared":"true","childId":rp["childId"],"includeChildSelections":"true" if rp.get("includeChildSelections",False) else "false","includeChildForces":"false","repeats":str(rp.get("repeats",1)),"roundUp":"true" if rp.get("roundUp",False) else "false"})
    if conditions:
        if len(conditions)==1:target=ET.SubElement(x,f"{{{ns}}}conditions")
        else:
            cgs=ET.SubElement(x,f"{{{ns}}}conditionGroups");cg=ET.SubElement(cgs,f"{{{ns}}}conditionGroup",{"type":"and"});target=ET.SubElement(cg,f"{{{ns}}}conditions")
        for c in conditions:
            ET.SubElement(target,f"{{{ns}}}condition",{"type":c.get("type","atLeast"),"value":str(c.get("value",1)),"field":c.get("field","selections"),"scope":c.get("scope","roster"),"childId":c["childId"],"shared":"true","includeChildSelections":"true" if c.get("includeChildSelections",True) else "false","includeChildForces":"false"})
    return x
def catlink(p,id_,name,target,primary=False):
    ns=qns(p);cs=cont(p,"categoryLinks");q=f"{{{ns}}}categoryLink";x=next((z for z in cs.findall(q) if z.get("id")==id_),None)
    if x is None:x=ET.SubElement(cs,q)
    x.attrib.update({"id":id_,"name":name,"targetId":target,"hidden":"false"})
    if primary:x.set("primary","true")
    return x
def add_rule(p,id_,name,text):
    rs=cont(p,"rules");r=next((z for z in rs.findall(C("rule")) if z.get("id")==id_),None)
    if r is None:r=ET.SubElement(rs,C("rule"))
    r.attrib.update({"id":id_,"name":name,"hidden":"false"});d=r.find(C("description"))
    if d is None:d=ET.SubElement(r,C("description"))
    d.text=text;return r
def clear_rules(p):
    rs=p.find(C("rules"))
    if rs is not None:p.remove(rs)
def add_infolink(p,id_,name,target,typ="rule",hidden=False):
    ils=cont(p,"infoLinks");x=next((z for z in ils.findall(C("infoLink")) if z.get("id")==id_),None)
    if x is None:x=ET.SubElement(ils,C("infoLink"))
    x.attrib.update({"id":id_,"name":name,"targetId":target,"type":typ,"hidden":"true" if hidden else "false"});return x
def group(p,id_,name,minv=None,maxv=None,hidden=False):
    gs=cont(p,"selectionEntryGroups",before=("costs","modifiers"));g=next((z for z in gs.findall(C("selectionEntryGroup")) if z.get("id")==id_),None)
    if g is None:g=ET.SubElement(gs,C("selectionEntryGroup"))
    g.attrib.update({"id":id_,"name":name,"hidden":"true" if hidden else "false"})
    if minv is not None:cons(g,id_+"-min","min",minv)
    if maxv is not None:cons(g,id_+"-max","max",maxv)
    return g
def sel(p,id_,name,typ="upgrade",pts=0,minv=None,maxv=1,default=None,hidden=False):
    ss=cont(p,"selectionEntries",before=("selectionEntryGroups","costs","modifiers"));e=next((z for z in ss.findall(C("selectionEntry")) if z.get("id")==id_),None)
    if e is None:e=ET.SubElement(ss,C("selectionEntry"))
    e.attrib.update({"id":id_,"name":name,"type":typ,"hidden":"true" if hidden else "false"})
    if default is not None:e.set("defaultAmount",str(default))
    if minv is not None:cons(e,id_+"-min","min",minv)
    if maxv is not None:cons(e,id_+"-max","max",maxv)
    cost(e,pts);return e
def elink(p,id_,name,target,pts=0,minv=None,maxv=1,hidden=False):
    es=cont(p,"entryLinks",before=("infoLinks","profiles","rules","selectionEntries","selectionEntryGroups","costs","modifiers"));e=next((z for z in es.findall(C("entryLink")) if z.get("id")==id_),None)
    if e is None:e=ET.SubElement(es,C("entryLink"))
    e.attrib.update({"id":id_,"name":name,"targetId":target,"type":"selectionEntry","import":"true","hidden":"true" if hidden else "false"})
    if minv is not None:cons(e,id_+"-min","min",minv)
    if maxv is not None:cons(e,id_+"-max","max",maxv)
    if pts!=0:cost(e,pts)
    return e
def visibility(e,req):
    e.set("hidden","true")
    ms=e.find(C("modifiers"))
    if ms is not None:
        for m in list(ms):
            if m.get("field")=="hidden":ms.remove(m)
    modifier(e,e.get("id")+"-r43-show","set","hidden","false",[{"childId":x,"scope":"roster"} for x in req])
def deep_prefix(e,prefix):
    x=copy.deepcopy(e);olds=[z.get("id") for z in x.iter() if z.get("id")];mp={o:prefix+o for o in olds}
    for z in x.iter():
        if z.get("id") in mp:z.set("id",mp[z.get("id")])
        for a in ("childId","targetId","field"):
            if z.get(a) in mp:z.set(a,mp[z.get(a)])
    return x
def set_primary(e,target,name):
    cs=cont(e,"categoryLinks")
    for c in cs.findall(C("categoryLink")):
        if c.get("primary")=="true":c.set("primary","false")
    x=next((z for z in cs.findall(C("categoryLink")) if z.get("targetId")==target),None)
    if x is None:x=ET.SubElement(cs,C("categoryLink"),{"id":e.get("id")+"-cat-"+target,"name":name,"targetId":target,"hidden":"false"})
    x.set("primary","true")
def strip_primary_categories(e):
    cs=e.find(C("categoryLinks"))
    if cs is not None:
        for c in list(cs):
            if c.get("primary")=="true":cs.remove(c)
def strip_old_options(e):
    gs=e.find(C("selectionEntryGroups"))
    if gs is None:return
    for g in list(gs):
        if (g.get("name") or "")=="Options":gs.remove(g)
def model_selector(e):
    return next((z for z in e.findall(f"./{C('selectionEntries')}/{C('selectionEntry')}") if (z.get("id") or "").endswith("-additional") or (z.get("name") or "")=="Squad Models"),None)
def dynmax(g,id_,modelid,factor=1,divisor=1):
    c=cons(g,id_,"max",0)
    modifier(g,id_+"-mod","increment",id_,factor,None,[{"childId":modelid,"scope":"root-entry","value":divisor,"repeats":1,"roundUp":False}]);return c
def squad_link(e,id_,name,target,ppm,modelid,maxv=1):
    l=elink(e,id_,name,target,0,None,maxv)
    modifier(l,id_+"-cost","increment","pts",ppm,None,[{"childId":modelid,"scope":"root-entry","value":1,"repeats":1}]);return l
def primary_cat(e,target):
    return any(c.get("targetId")==target and c.get("primary")=="true" for c in e.findall(f"./{C('categoryLinks')}/{C('categoryLink')}"))
def idmap():return {e.get("id"):e for e in cr.iter() if e.get("id")}
ids=idmap();LEG="legion-xix";LOY="allegiance-loyalist"
DEC="r25-rite-xix-0-decapitation-strike";LIB="r25-rite-xix-1-liberation-force"

# Shared rules
sr=cr.find(C("sharedRules"))
if sr is None:sr=ET.Element(C("sharedRules"));cr.insert(0,sr)
def find_sr(name):return next((x for x in sr.findall(C("rule")) if x.get("name")==name),None)
def shr(id_,name,text):
    r=next((x for x in sr.findall(C("rule")) if x.get("id")==id_),None)
    if r is None:r=ET.SubElement(sr,C("rule"),{"id":id_,"name":name,"hidden":"false"})
    else:r.set("name",name)
    d=r.find(C("description"))
    if d is None:d=ET.SubElement(r,C("description"))
    d.text=text;return r
rg_rules={
"Legiones Astartes (Raven Guard)":"This model belongs to the XIX Legion. It follows the normal Legiones Astartes rules and is affected by rules referring to Legiones Astartes (Raven Guard). A model may possess only one named Legiones Astartes rule.",
"Surgical Strike":"Whenever a Raven Guard unit deploys using Deep Strike, the Raven Guard player may re-roll the Scatter die and all dice rolled for scatter distance. The entire result must be re-rolled and the second result accepted.",
"Rapid Reaction":"At the beginning of each Raven Guard turn, if at least one friendly Legion Reconnaissance Squad or Mor Deythan Squad has a surviving model on the battlefield and is not Falling Back, add +1 to all Raven Guard Reserve rolls that turn. This bonus is not cumulative.",
"Shadow Masters":"Raven Guard Legion Reconnaissance Squads lose Support Squad and may fulfil compulsory Troops selections normally. Raven Guard Legion Reconnaissance Squads and Independent Characters purchase Sniper Rifles for 2 points instead of 5 points or another normally applicable price.",
"Limited Vehicles":"A Raven Guard Detachment may never include more Heavy Support selections than Fast Attack selections. Dedicated Transports are ignored.",
"Raven's Talons":"A pair of Raven's Talons counts as a pair of Rending Weapons. The bearer receives the normal +1 Attack bonus for fighting with two close-combat weapons.",
"Infravisor":"The bearer gains Night Vision and +1 Ballistic Skill, to a maximum of BS6. When taking an Initiative test caused by Blind, the bearer and any unit joined by the bearer count as Initiative 1.",
"Shroud Bombs":"Shroud Bombs count as Defensive Grenades. An enemy unit attempting to charge the equipped unit must first pass a Leadership test. If it fails, it may not attempt that charge and may not declare another charge that turn. Vehicles, Daemons and units containing a model with Night Vision are unaffected.",
"Cameleoline":"The bearer gains the Stealth special rule.",
"Teleportation Transponders":"The equipped model or unit gains Deep Strike and may deploy using Deep Strike even if the mission would not normally permit it. An Independent Character intending to Deep Strike with another unit must purchase Transponders separately.",
"Fatal Strike":"Once per battle, at the beginning of a Raven Guard Shooting phase, nominate one enemy unit within 18 inches and line of sight of the Mor Deythan Squad. Until the end of that Shooting phase, models in the squad re-roll To Hit rolls of 1 and To Wound rolls of 1 against it; against Vehicles, re-roll Armour Penetration rolls of 1 instead.",
"Swooping Killers":"During an Assault phase in which the Dark Furies charge, models in the squad may re-roll To Hit rolls of 1 until the end of that Assault phase.",
"Terran Veterans":"Deliverers do not benefit from Infiltrate if it is granted by another Raven Guard rule or Rite of War. They may always deploy using Teleportation Transponders if purchased normally.",
"Unstable Creation":"Raptors may never fulfil compulsory Troops selections and may not be joined by an Independent Character other than Corvus Corax or Branne Nev.",
"The Raven's Due":"At the beginning of the battle, nominate one enemy Independent Character or unit-upgrade Character. Kaedes Nex may re-roll failed To Hit rolls against that model in close combat and when shooting his Fulcrum Hand Cannons at a unit containing it. Unsaved Wounds caused by Nex's shooting may be allocated to the nominated model first if it is within range and line of sight.",
"Executioner's Instinct":"If Kaedes Nex causes one or more unsaved Wounds upon his nominated target, that model's unit must immediately take a Pinning test.",
"Master of Descent":"If Alvarex Maun begins the battle in Reserve embarked aboard a Drop Pod, Dreadclaw or Flyer Transport, Maun and that Transport arrive automatically during the first Raven Guard turn. No Reserve roll is required.",
"Commander of the Talons":"An army containing Agapito Nev may include up to two Dark Fury Assault Squads rather than the normal 0–1. Agapito's squad may re-roll failed Morale tests caused by shooting casualties.",
"First Into the Fray":"During an Assault phase in which Agapito and his squad charge, that squad may re-roll all failed To Hit rolls during the first round of that close combat.",
"Commander of the Survivors":"If the army includes Branne Nev, one Raptor Squad may be selected without occupying an Elites choice. It still counts as Elites for all other purposes and may not fulfil a compulsory selection. Branne may join a Raptor Squad despite Unstable Creation.",
"Hold Fast":"Branne Nev and any Raven Guard unit he has joined may re-roll failed Morale and Pinning tests.",
"Ghost in the Dark":"While Sharrowkyn's unit is in cover, improve its Cover Save by 1, to a maximum of 3+.",
"Perfect Ambusher":"When Sharrowkyn shoots at an enemy unit within 12 inches, he may re-roll failed To Hit rolls.",
"The Shadowed Lord":"Corvus Corax has Stealth and Hit & Run. If the Avenging Shadow variant is selected, Stealth is replaced by Shrouded; Hit & Run is retained.",
"Sire of the Raven Guard":"Friendly Raven Guard Infantry units with at least one model within 12 inches of Corvus Corax improve any Cover Save they receive by 1, to a maximum of 3+.",
"Secret Deployment":"Instead of deploying normally, secretly record one terrain feature outside the enemy deployment zone and hold Corax off the battlefield. From the second Raven Guard turn onwards, at the beginning of a Movement phase, reveal it and place Corax wholly within or in contact with it and more than 6 inches from enemy models. Corax may Move, Shoot and charge normally that turn. No Reserve roll is required. If he cannot be placed legally, he may try again later. A Primarch Retinue deploys normally and does not accompany him.",
}
R={}
for n,t in rg_rules.items():R[n]=shr("r43-rg-"+re.sub(r"[^a-z0-9]+","-",n.lower()).strip("-")[:70],n,t)
def generic(name):
    x=find_sr(name)
    if x is None:
        fallback={
        "Infiltrate":"May deploy using the normal Infiltrate rules.",
        "Move Through Cover":"Roll 3D6 for Difficult Terrain tests and use the highest result.",
        "Stubborn":"Ignore negative Leadership modifiers on Morale and Pinning tests.",
        "Fleet":"May charge even if it Advanced in the same turn.",
        "Furious Charge":"Models gain +1 Strength and +1 Initiative in assault on the turn they charged.",
        "Rending":"Uses the normal ProHammer Rending rule.",
        "Independent Character":"Uses the normal ProHammer Independent Character rules.",
        "Master of the Legion":"Permits use of a Rite of War and follows the normal Master of the Legion restrictions.",
        "Primarch":"Uses the normal Primarch rules.",
        "Stealth":"Improves Cover Saves as described by the ProHammer Stealth rule.",
        "Shrouded":"Uses the normal ProHammer Shrouded rule.",
        "Hit & Run":"Uses the normal ProHammer Hit & Run rule.",
        "Hatred":"Uses the normal ProHammer Hatred rule.",
        }
        x=shr("r43-generic-"+re.sub(r"[^a-z0-9]+","-",name.lower()).strip("-"),name,fallback.get(name,"Use the normal ProHammer rule."))
    return x
def ilr(e,name,suffix=None):
    rr=R.get(name) or generic(name);add_infolink(e,e.get("id")+"-"+(suffix or re.sub(r"[^a-z0-9]+","-",name.lower()).strip("-")),name,rr.get("id"),"rule")
def legion(e):
    ilr(e,"Legiones Astartes (Raven Guard)","rg-leg")
    for n in ["Surgical Strike","Rapid Reaction","Shadow Masters","Limited Vehicles"]:ilr(e,n,"rg-"+re.sub(r"[^a-z0-9]+","-",n.lower()).strip("-"))

# Shared profiles
sp=cr.find(C("sharedProfiles"))
if sp is None:sp=ET.Element(C("sharedProfiles"));cr.insert(1,sp)
def shprof(id_,name,chars):
    p=next((x for x in sp.findall(C("profile")) if x.get("id")==id_),None)
    if p is None:p=ET.SubElement(sp,C("profile"))
    p.attrib.update({"id":id_,"name":name,"typeId":"prof-weapon","hidden":"false"});chs=p.find(C("characteristics"))
    if chs is None:chs=ET.SubElement(p,C("characteristics"))
    for z in list(chs):chs.remove(z)
    for k,v,tid in [("Range",chars[0],"weapon-range"),("S",chars[1],"weapon-s"),("AP",chars[2],"weapon-ap"),("Type",chars[3],"weapon-type")]:
        z=ET.SubElement(chs,C("characteristic"),{"name":k,"typeId":tid});z.text=str(v)
    return p
P_FUL=shprof("r43-rg-prof-fulcrum","Fulcrum Hand Cannon",('18"',"4","4","Pistol, Rending, Concussive"))
P_WRATH=shprof("r43-rg-prof-wrath","Wrath & Justice",('12"',"6","4","Assault 2, Rending, Master-crafted"))
P_TAL=shprof("r43-rg-prof-corvidine","Corvidine Talons",("—","+1","Power Weapon","Melee, paired, Shred, Rending"))
P_TOL=shprof("r43-rg-prof-tolaedus","Tolaedus",("—","User","Power Weapon","Melee, Master-crafted"))
P_SUD=shprof("r43-rg-prof-sudden","Sudden Blade",("—","User","Rending Weapon","Melee, Master-crafted, Rending"))

# Legion selector
leg=ids[LEG];clear_rules(leg);legion(leg)
for n in ["Raven's Talons","Infravisor","Shroud Bombs","Cameleoline","Teleportation Transponders"]:ilr(leg,n,"arm-"+re.sub(r"[^a-z0-9]+","-",n.lower()).strip("-"))
add_infolink(leg,"r43-rg-fulcrum-prof","Fulcrum Hand Cannon",P_FUL.get("id"),"profile")

# Canonical Raven Guard armoury wrappers
for eid,rule_name,prof in [
("r46-rg-talons-model","Raven's Talons",None),("r46-rg-talons-character","Raven's Talons",None),
("r46-rg-hand-cannon","Raven's Talons",None),
("r46-rg-infravisor","Infravisor",None),("r46-rg-shroud-character","Shroud Bombs",None),("r46-rg-shroud-unit","Shroud Bombs",None),
("r46-rg-cameleoline","Cameleoline",None),("r46-rg-trans-character","Teleportation Transponders",None),("r46-rg-trans-unit","Teleportation Transponders",None)]:
    if eid not in ids:continue
    clear_rules(ids[eid])
    if eid=="r46-rg-hand-cannon":
        add_rule(ids[eid],eid+"-effect","Fulcrum Hand Cannon",'Replace one Bolt Pistol. Range 18", Strength 4, AP4, Pistol, Rending, Concussive.')
        add_infolink(ids[eid],eid+"-profile","Fulcrum Hand Cannon",P_FUL.get("id"),"profile")
    else:ilr(ids[eid],rule_name,"canonical")

# GST hidden categories / force enforcement
ce=gr.find(G("categoryEntries"))
if ce is None:ce=ET.SubElement(gr,G("categoryEntries"))
def gcat(id_,name):
    x=next((z for z in ce.findall(G("categoryEntry")) if z.get("id")==id_),None)
    if x is None:x=ET.SubElement(ce,G("categoryEntry"))
    x.attrib.update({"id":id_,"name":name,"hidden":"true"});return x
force=next(x for x in gr.iter(G("forceEntry")) if x.get("id")=="force-standard");fcls=cont(force,"categoryLinks")
def fl(id_,name,target):
    x=next((z for z in fcls.findall(G("categoryLink")) if z.get("id")==id_),None)
    if x is None:x=ET.SubElement(fcls,G("categoryLink"))
    x.attrib.update({"id":id_,"name":name,"targetId":target,"hidden":"true"});return x
CAT_HS="r43-rg-heavy-count";CAT_DEC_HS="r43-rg-decap-heavy";CAT_DEC_CON="r43-rg-decap-consul";CAT_DF="r43-rg-dark-fury-limit";CAT_DEL="r43-rg-deliverer-limit";CAT_RAP="r43-rg-raptor-limit";CAT_COMP="r43-rg-compulsory-troops";CAT_SHAR="r43-rg-sharrowkyn-limit"
for cid,n in [(CAT_HS,"Raven Guard — Heavy Support count"),(CAT_DEC_HS,"Decapitation Strike — Heavy Support"),(CAT_DEC_CON,"Decapitation Strike — Consul"),(CAT_DF,"Raven Guard — Dark Fury limit"),(CAT_DEL,"Raven Guard — Deliverer limit"),(CAT_RAP,"Raven Guard — Raptor limit"),(CAT_COMP,"Raven Guard — compulsory-capable Troops"),(CAT_SHAR,"Raven Guard — Sharrowkyn limit")]:gcat(cid,n)
# Heavy <= Fast
x=fl("r43-rg-heavy-force","Raven Guard — Heavy Support count",CAT_HS);mx=cons(x,"r43-rg-heavy-max","max",99,"selections","parent",True)
modifier(x,"r43-rg-heavy-zero","set",mx.get("id"),0,[{"childId":LEG,"scope":"roster"}])
modifier(x,"r43-rg-heavy-per-fast","increment",mx.get("id"),1,[{"childId":LEG,"scope":"roster"}],[{"childId":"cat-fast","scope":"force","value":1,"repeats":1}])
# Decap Heavy max1
x=fl("r43-rg-decap-heavy-force","Decapitation Strike — Heavy Support",CAT_DEC_HS);mx2=cons(x,"r43-rg-decap-heavy-max","max",99,"selections","parent",True);modifier(x,"r43-rg-decap-heavy-one","set",mx2.get("id"),1,[{"childId":DEC,"scope":"roster"}])
# Decap Consul max1
x=fl("r43-rg-decap-consul-force","Decapitation Strike — Consul",CAT_DEC_CON);mc=cons(x,"r43-rg-decap-consul-max","max",99,"selections","parent",True);modifier(x,"r43-rg-decap-consul-one","set",mc.get("id"),1,[{"childId":DEC,"scope":"roster"}])
# fixed 0-1 categories
for fid,cid,name in [("r43-rg-del-force",CAT_DEL,"Deliverer"),("r43-rg-rap-force",CAT_RAP,"Raptor"),("r43-rg-shar-force",CAT_SHAR,"Sharrowkyn")]:
    x=fl(fid,name+" limit",cid);cons(x,fid+"-max","max",1,"selections","parent",True)
# Dark Fury 0-1 normally, 0-2 with Agapito selected
x=fl("r43-rg-df-force","Dark Fury limit",CAT_DF);dfmx=cons(x,"r43-rg-df-max","max",1,"selections","parent",True)
modifier(x,"r43-rg-df-agapito","set",dfmx.get("id"),2,[{"childId":"r43-rg-agapito-replacement","scope":"roster"}])
# Compulsory-capable Troops >=2 in RG
x=fl("r43-rg-comp-force","Raven Guard — compulsory-capable Troops",CAT_COMP);cm=cons(x,"r43-rg-comp-min","min",0,"selections","parent",True);modifier(x,"r43-rg-comp-two","set",cm.get("id"),2,[{"childId":LEG,"scope":"roster"}])

# Tag top-level FOC entries
for e in cr.findall(f"./{C('selectionEntries')}/{C('selectionEntry')}"):
    if primary_cat(e,"cat-heavy"):
        catlink(e,e.get("id")+"-r43-rg-heavy","Raven Guard — Heavy Support count",CAT_HS)
        catlink(e,e.get("id")+"-r43-rg-decap-heavy","Decapitation Strike — Heavy Support",CAT_DEC_HS)
# Consul choices
cent=ids["hq-centurion"];cg=next((g for g in cent.iter(C("selectionEntryGroup")) if g.get("id")=="hq-centurion-consuls"),None)
if cg is None:raise RuntimeError("Centurion Consul group missing")
for c in cg.findall(C("selectionEntry")):catlink(c,c.get("id")+"-r43-rg-consul","Decapitation Strike — Consul",CAT_DEC_CON)

# RG compulsory-capable Troops: exclude Support/non-compulsory, except Recon because Shadow Masters removes Support.
def textish(e):
    return " ".join([(r.get("name") or "")+" "+(r.findtext(C("description")) or "") for r in e.iter(C("rule"))]+[(i.get("name") or "") for i in e.iter(C("infoLink"))]).lower()
comp_tag=0
for e in cr.findall(f"./{C('selectionEntries')}/{C('selectionEntry')}"):
    if not primary_cat(e,"cat-troops"):continue
    txt=textish(e)
    if e.get("id")!="recon-unit" and ("support squad" in txt or "non-compulsory" in txt or "may not fulfil compulsory" in txt or "may not fulfill compulsory" in txt):continue
    catlink(e,e.get("id")+"-r43-rg-comp","Raven Guard — compulsory-capable Troops",CAT_COMP);comp_tag+=1

# Shadow Masters: Recon Sniper Rifle = 2 pts, including Sergeant forms.
recon=ids["recon-unit"];sniper_discount=0
for l in recon.iter(C("entryLink")):
    if l.get("targetId")=="gear-sniper-rifle" or "sniper rifle" in (l.get("name") or "").lower():
        c=next((z for z in l.findall(f"./{C('costs')}/{C('cost')}") if z.get("typeId")=="pts"),None)
        if c is not None:
            modifier(l,l.get("id")+"-r43-rg-sniper","set","pts",2,[{"childId":LEG,"scope":"roster"}]);sniper_discount+=1
# IC Sniper Rifle for 2 points
for hid in ["hq-praetor","hq-centurion"]:
    h=ids[hid];wg=next((g for g in h.findall(f"./{C('selectionEntryGroups')}/{C('selectionEntryGroup')}") if "weapon replacement" in (g.get("name") or "").lower()),None)
    if wg is not None and not any(l.get("id")==f"r43-{hid}-rg-sniper" for l in wg.findall(C("entryLink"))):
        l=elink(wg,f"r43-{hid}-rg-sniper","Sniper Rifle — Raven Guard","gear-sniper-rifle",2,None,1,True);modifier(l,l.get("id")+"-show","set","hidden","false",[{"childId":LEG}])

# Correct RG armoury links on ICs.
term_ids={"hq-praetor-term","hq-praetor-tart","hq-praetor-cat","hq-centurion-term","hq-centurion-tart","hq-centurion-cat"}
for hid in ["hq-praetor","hq-centurion"]:
    h=ids[hid]
    for l in h.iter(C("entryLink")):
        if l.get("targetId") in {"r46-rg-hand-cannon","r46-rg-infravisor","r46-rg-shroud-character","r46-rg-cameleoline","r46-rg-talons-character","r46-rg-trans-character"}:
            modifier(l,l.get("id")+"-r43-hide-not-rg","set","hidden","true",[{"childId":LEG,"type":"lessThan","value":1}])
            if l.get("targetId")=="r46-rg-cameleoline":
                for tid in term_ids:
                    modifier(l,l.get("id")+"-r43-cam-"+tid,"set","hidden","true",[{"childId":tid,"scope":"root-entry"}])
            if l.get("targetId")=="r46-rg-trans-character":
                # default hidden; show only with a Terminator armour selection
                l.set("hidden","true")
                for tid in term_ids:
                    if tid.startswith(hid):
                        modifier(l,l.get("id")+"-r43-show-"+tid,"set","hidden","false",[{"childId":LEG},{"childId":tid,"scope":"root-entry"}])
            if l.get("targetId")=="r46-rg-talons-character":
                # pair of claws prerequisite
                l.set("hidden","true")
                for pid in ["gear-pair-claws","gear-hq-pair-claws"]:
                    modifier(l,l.get("id")+"-r43-claws-"+pid,"set","hidden","false",[{"childId":LEG},{"childId":pid,"scope":"root-entry"}])

# Controlled Sergeant Armoury propagation for Fulcrum/Infravisor.
serg_added=0
for g in cr.iter(C("selectionEntryGroup")):
    n=(g.get("name") or "").lower()
    if "armoury" not in n:continue
    if not any(k in n for k in ["sergeant","huscarl","hunt-master","warden","chieftain","strike leader","alpha"]):continue
    # leaf armoury groups only
    if g.find(C("selectionEntryGroups")) is not None:continue
    es=cont(g,"entryLinks")
    for tid,nm in [("r46-rg-hand-cannon","Fulcrum Hand Cannon"),("r46-rg-infravisor","Infravisor")]:
        if any(l.get("targetId")==tid for l in es.findall(C("entryLink"))):continue
        lid="r43-rg-serg-"+hashlib.sha1(((g.get("id") or "")+tid).encode()).hexdigest()[:12]
        l=elink(g,lid,nm,tid,0,None,1,True);modifier(l,lid+"-show","set","hidden","false",[{"childId":LEG}]);serg_added+=1

# Veteran Raven's Talons quantity scales with actual squad size.
vet=ids["veteran-unit"]
for l in vet.iter(C("entryLink")):
    if l.get("targetId")=="r46-rg-talons-model":
        cs=l.find(C("constraints"))
        if cs is not None:
            for z in list(cs):
                if z.get("type")=="max":cs.remove(z)
        m=next((x for x in vet.iter(C("selectionEntry")) if x.get("id")=="veteran-included"),None)
        if m is not None:
            maxc=cons(l,l.get("id")+"-r43-dynmax","max",0)
            modifier(l,l.get("id")+"-r43-dynmax-mod","increment",maxc.get("id"),1,None,[{"childId":m.get("id"),"scope":"root-entry","value":1,"repeats":1}])

# Unit patch helpers
def clone_sergeant_armoury(e,id_,name,terminator=False):
    srcroot=ids["terminator-unit"] if terminator and "terminator-unit" in ids else ids["veteran-unit"]
    cand=[]
    for g in srcroot.iter(C("selectionEntryGroup")):
        nm=(g.get("name") or "").lower()
        if "armoury" in nm and ("sergeant" in nm or "additional armoury" in nm):
            cand.append(g)
    if not cand:return None
    src=cand[0];cp=deep_prefix(src,id_+"-clone-");cp.set("id",id_);cp.set("name",name)
    gs=cont(e,"selectionEntryGroups",before=("costs","modifiers"));gs.append(cp);return cp
def transport_group(e,id_,items,modelid=None):
    g=group(e,id_,"Dedicated Transport",0,1)
    targets={"Rhino":"transport-rhino","Drop Pod":"transport-drop-pod","Dreadclaw Drop Pod":"transport-dreadclaw","Spartan Assault Tank":"hs-spartan"}
    for nm in items:
        if nm=="Land Raider":
            lg=group(g,id_+"-lr","Land Raider",0,1)
            for nn,tid in [("Land Raider Phobos","hs-lr-phobos"),("Land Raider Proteus","hs-lr-proteus"),("Land Raider Achilles","hs-lr-achilles")]:
                l=elink(lg,id_+"-"+re.sub(r"[^a-z0-9]+","-",nn.lower()),nn,tid,0,None,1)
                if modelid:modifier(l,l.get("id")+"-cap","set","hidden","true",[{"childId":modelid,"scope":"root-entry","type":"atLeast","value":6,"includeChildSelections":False}])
        else:
            l=elink(g,id_+"-"+re.sub(r"[^a-z0-9]+","-",nm.lower()),nm,targets[nm],0,None,1)
            if modelid and nm=="Dreadclaw Drop Pod":modifier(l,l.get("id")+"-cap","set","hidden","true",[{"childId":modelid,"scope":"root-entry","type":"atLeast","value":6,"includeChildSelections":False}])
    return g
def replace_group(e,id_,name,modelid,choices,per=1):
    g=group(e,id_,name,0,None);dynmax(g,id_+"-dynmax",modelid,1,per)
    for nm,tid,pts in choices:elink(g,id_+"-"+re.sub(r"[^a-z0-9]+","-",nm.lower()),nm,tid,pts,None,10)
    return g

mor=ids["r41-unit-xix-0-mor-deythan-squad"];clear_rules(mor);strip_old_options(mor);legion(mor);ilr(mor,"Infiltrate");ilr(mor,"Move Through Cover");ilr(mor,"Fatal Strike")
add_rule(mor,"r43-mor-wg","Wargear","Power Armour, Sniper Rifle, Bolt Pistol, close-combat weapon and Frag Grenades.")
mm=model_selector(mor);mm.set("name","Mor Deythan (total squad size)");cost(mm,24)
replace_group(mor,"r43-mor-ranged","Replace Sniper Rifle — any model",mm.get("id"),[("Combi-flamer","gear-combi-flamer",10),("Combi-meltagun","gear-combi-meltagun",15),("Combi-plasma gun","gear-combi-plasma",15),("Combi-volkite charger","gear-combi-volkite",10)],1)
replace_group(mor,"r43-mor-heavy","Replace Sniper Rifle — 1 per 5 models",mm.get("id"),[("Heavy Bolter","gear-heavy-bolter",15),("Missile Launcher","gear-missile-launcher",20)],5)
squad_link(mor,"r43-mor-krak","Krak Grenades — entire squad","gear-krak",2,mm.get("id"))
elink(mor,"r43-mor-shroud","Shroud Bombs","r46-rg-shroud-unit",0,None,1)
clone_sergeant_armoury(mor,"r43-mor-sgt-arm","Mor Deythan Sergeant Armoury — up to 50 points",False)

dark=ids["r41-unit-xix-1-dark-fury-assault-squad"];clear_rules(dark);strip_old_options(dark);legion(dark);ilr(dark,"Swooping Killers");ilr(dark,"Raven's Talons")
add_rule(dark,"r43-dark-wg","Wargear","Power Armour, Jump Pack, Bolt Pistol, Raven's Talons and Frag Grenades.")
dm=model_selector(dark);dm.set("name","Dark Furies (total squad size)");cost(dm,34)
squad_link(dark,"r43-dark-krak","Krak Grenades — entire squad","gear-krak",2,dm.get("id"));squad_link(dark,"r43-dark-melta","Melta Bombs — entire squad","gear-melta-bombs",5,dm.get("id"))
clone_sergeant_armoury(dark,"r43-dark-leader-arm","Dark Fury Strike Leader Armoury — up to 50 points",False)
catlink(dark,"r43-dark-limit-cat","Raven Guard — Dark Fury limit",CAT_DF)

deliver=ids["r41-unit-xix-2-deliverer-terminator-squad"];clear_rules(deliver);strip_old_options(deliver);legion(deliver);ilr(deliver,"Stubborn");ilr(deliver,"Terran Veterans")
add_rule(deliver,"r43-del-wg","Wargear","Cataphractii Terminator Armour, Combi-bolter and Power Weapon.")
de=model_selector(deliver);de.set("name","Deliverers (total squad size)");cost(de,43)
replace_group(deliver,"r43-del-melee","Replace Power Weapon — any model",de.get("id"),[("Power Fist","gear-power-fist",10),("Chainfist","gear-chainfist",15),("Pair of Raven's Talons","r46-rg-talons-character",10)],1)
replace_group(deliver,"r43-del-ranged","Replace Combi-bolter — any model",de.get("id"),[("Combi-flamer","gear-combi-flamer",10),("Combi-meltagun","gear-combi-meltagun",15),("Combi-plasma gun","gear-combi-plasma",15),("Combi-volkite charger","gear-combi-volkite",10)],1)
replace_group(deliver,"r43-del-heavy","Replace Combi-bolter — 1 per 5 models",de.get("id"),[("Heavy Flamer","gear-heavy-flamer",10),("Reaper Autocannon","gear-reaper-autocannon",15),("Multi-Melta","gear-multimelta",20)],5)
clone_sergeant_armoury(deliver,"r43-del-chief-arm","Deliverer Chieftain Armoury — up to 50 points",True)
transport_group(deliver,"r43-del-transport",["Land Raider","Dreadclaw Drop Pod","Spartan Assault Tank"],de.get("id"))
catlink(deliver,"r43-del-limit-cat","Raven Guard — Deliverer limit",CAT_DEL)

rap=ids["r41-unit-xix-3-raptor-squad"];clear_rules(rap);strip_old_options(rap);legion(rap)
for n in ["Fleet","Furious Charge","Move Through Cover","Rending","Unstable Creation"]:ilr(rap,n)
add_rule(rap,"r43-rap-wg","Wargear","Power Armour, Bolt Pistol, close-combat weapon and Frag Grenades.")
rm=model_selector(rap);rm.set("name","Raptors (total squad size)");cost(rm,32)
squad_link(rap,"r43-rap-krak","Krak Grenades — entire squad","gear-krak",2,rm.get("id"));squad_link(rap,"r43-rap-melta","Melta Bombs — entire squad","gear-melta-bombs",5,rm.get("id"))
replace_group(rap,"r43-rap-pistol","Replace Bolt Pistol — 1 per 5 models",rm.get("id"),[("Hand Flamer","gear-hand-flamer",5),("Plasma Pistol","gear-plasma-pistol",15)],5)
clone_sergeant_armoury(rap,"r43-rap-alpha-arm","Raptor Alpha Armoury — up to 50 points",False)
catlink(rap,"r43-rap-limit-cat","Raven Guard — Raptor limit",CAT_RAP)

# Root visibility
for e in [mor,dark,deliver]:visibility(e,[LEG])
visibility(rap,[LEG,LOY])

# Special characters: clean source dumps, preserve profiles/groups
def charbase(e,mol=False):
    clear_rules(e);legion(e)
    if mol:ilr(e,"Master of the Legion")
    ilr(e,"Independent Character")

nex=ids["r41-unit-xix-4-kaedes-nex"];clear_rules(nex);legion(nex);ilr(nex,"The Raven's Due");ilr(nex,"Executioner's Instinct")
add_rule(nex,"r43-nex-danger","Dangerous Weaponry","The Raven Guard source lists Dangerous Weaponry for Kaedes Nex but does not define a Raven Guard effect for it. No additional rule effect is invented here.")
add_rule(nex,"r43-nex-wg","Wargear","Power Armour, Refractor Field, two Fulcrum Hand Cannons, Rending Weapon, Jump Pack, Frag Grenades and Krak Grenades.")
add_infolink(nex,"r43-nex-fulcrum","Fulcrum Hand Cannon",P_FUL.get("id"),"profile")
add_rule(nex,"r43-nex-join","No Independent Character may join Kaedes Nex's squad.","No Independent Character may join Kaedes Nex's squad.")

maun=ids["r41-unit-xix-5-alvarex-maun"];charbase(maun,True);ilr(maun,"Master of Descent")
add_rule(maun,"r43-maun-wg","Wargear","Artificer Armour, Refractor Field, Bolt Pistol, Tolaedus, Nightfall Pattern Strato-Vox and Frag Grenades.")
add_infolink(maun,"r43-maun-tol","Tolaedus",P_TOL.get("id"),"profile")
add_rule(maun,"r43-maun-vox","Nightfall Pattern Strato-Vox","Counts as a Nuncio Vox. Once during each Raven Guard turn, one friendly Raven Guard unit deploying by Deep Strike with its first model within 12 inches of Maun may re-roll the dice rolled for scatter distance; the second result is accepted.")
add_rule(maun,"r43-maun-command","Command Squad","Alvarex Maun may be accompanied by a Legion Command Squad. Maun and the Command Squad count as a single HQ selection.")

aga=ids["r41-unit-xix-6-agapito-nev"];clear_rules(aga);legion(aga);ilr(aga,"Commander of the Talons");ilr(aga,"First Into the Fray")
add_rule(aga,"r43-aga-wg","Wargear","Power Armour, Refractor Field, Jump Pack, Bolter, Power Weapon, close-combat weapon and Frag Grenades.")

branne=ids["r41-unit-xix-7-branne-nev"];charbase(branne,True);ilr(branne,"Commander of the Survivors");ilr(branne,"Hold Fast")
add_rule(branne,"r43-branne-wg","Wargear","Artificer Armour, Refractor Field, Bolter, Bolt Pistol, Power Weapon, Frag Grenades and Krak Grenades.")

shar=ids["r41-unit-xix-8-nykona-sharrowkyn"];clear_rules(shar);legion(shar)
for n in ["Infiltrate","Move Through Cover","Ghost in the Dark","Perfect Ambusher"]:ilr(shar,n)
add_rule(shar,"r43-shar-wg","Wargear","Artificer Armour, Refractor Field, Bolt Pistol, Sniper Rifle, Sudden Blade and Frag Grenades.")
add_infolink(shar,"r43-shar-sudden","Sudden Blade",P_SUD.get("id"),"profile")

cor=ids["r41-unit-xix-9-xix-corvus-corax-the-raven-lord"];clear_rules(cor);legion(cor);ilr(cor,"Primarch")
for n in ["The Shadowed Lord","Sire of the Raven Guard","Secret Deployment"]:ilr(cor,n)
add_rule(cor,"r43-cor-wg","Wargear","Sable Armour, Korvidine Pinions, Corvidine Talons, Wrath & Justice and Frag Grenades.")
add_rule(cor,"r43-cor-sable","Sable Armour","Counts as Primarch Armour.")
add_rule(cor,"r43-cor-pinions","Korvidine Pinions","Corax is Jump Infantry and follows the normal ProHammer Jump Infantry rules. This ability may never be lost, disabled or destroyed by damage to wargear.")
add_infolink(cor,"r43-cor-talons-prof","Corvidine Talons",P_TAL.get("id"),"profile");add_infolink(cor,"r43-cor-wrath-prof","Wrath & Justice",P_WRATH.get("id"),"profile")

# hide replacement characters as standalone FOC entries
for e in [nex,aga,shar]:
    e.set("hidden","true")
    ms=e.find(C("modifiers"))
    if ms is not None:
        for m in list(ms):
            if m.get("field")=="hidden":ms.remove(m)
# proper standalone
visibility(maun,[LEG]);visibility(branne,[LEG]);visibility(cor,[LEG,LOY])

# Character replacement helper
def strip_foc_and_visibility(e):
    strip_primary_categories(e)
    cs=e.find(C("constraints"))
    if cs is not None:
        for x in list(cs):
            if x.get("scope")=="roster":cs.remove(x)
    ms=e.find(C("modifiers"))
    if ms is not None:
        for x in list(ms):
            if x.get("field")=="hidden":ms.remove(x)
    e.set("hidden","false")
def add_replacement(parent,groupid,copyid,src,display,pts,limitcat=None):
    g=group(parent,groupid,"Raven Guard Character Replacement",0,1)
    ss=cont(g,"selectionEntries",before=("selectionEntryGroups","costs","modifiers"))
    old=next((x for x in ss.findall(C("selectionEntry")) if x.get("id")==copyid),None)
    if old is not None:ss.remove(old)
    cp=deep_prefix(src,copyid+"-clone-");cp.set("id",copyid);cp.set("name",display);cp.set("type","model");strip_foc_and_visibility(cp);cost(cp,pts);cons(cp,copyid+"-unique","max",1,"selections","roster")
    if limitcat:catlink(cp,copyid+"-limitcat",display+" limit",limitcat)
    ss.append(cp);return cp

# Estimate normal leader replacement cost from source/current composition.
# Destroyer base = root 70 + five 16-point included models = 150; replace one 16-point model.
kaedes_nested=add_replacement(ids["destroyer-unit"],"r43-rg-nex-group","r43-rg-kaedes-replacement",nex,"Kaedes Nex — replaces Destroyer Sergeant",119,None)
modifier(kaedes_nested,"r43-rg-kaedes-show","set","hidden","false",[{"childId":LEG}])
# Agapito replaces one 34-point Strike Leader: +106 net.
ag_nested=add_replacement(dark,"r43-rg-ag-group","r43-rg-agapito-replacement",aga,"Agapito Nev — replaces Strike Leader",106,None)
# Sharrowkyn replaces 14-point Recon Sergeant or 20-point Seeker Sergeant.
sh_recon=add_replacement(recon,"r43-rg-shar-recon-group","r43-rg-sharrowkyn-recon",shar,"Nykona Sharrowkyn — replaces Recon Sergeant",111,CAT_SHAR)
modifier(sh_recon,"r43-rg-shar-recon-show","set","hidden","false",[{"childId":LEG}])
seek=ids["fa-seeker"]
sh_seek=add_replacement(seek,"r43-rg-shar-seeker-group","r43-rg-sharrowkyn-seeker",shar,"Nykona Sharrowkyn — replaces Seeker Sergeant",105,CAT_SHAR)
modifier(sh_seek,"r43-rg-shar-seeker-show","set","hidden","false",[{"childId":LEG}])

# Branne no-slot Raptor nested selection
bg=group(branne,"r43-branne-raptor","Commander of the Survivors — Raptor Squad (no Elites slot)",0,1)
bss=cont(bg,"selectionEntries",before=("selectionEntryGroups","costs","modifiers"))
cp=deep_prefix(rap,"r43-branne-raptor-copy-");cp.set("id","r43-branne-raptor-squad");cp.set("name","Raptor Squad — Commander of the Survivors");strip_foc_and_visibility(cp);catlink(cp,"r43-branne-rap-limit","Raven Guard — Raptor limit",CAT_RAP);bss.append(cp)

# Dark Fury retinue under Praetor with Jump Pack
pra=ids["hq-praetor"];pg=group(pra,"r43-rg-dark-retinue","Raven Guard — Dark Fury Retinue",0,1,True)
modifier(pg,"r43-rg-dark-retinue-show","set","hidden","false",[{"childId":LEG},{"childId":"hq-praetor-jump","scope":"root-entry"}])
pss=cont(pg,"selectionEntries",before=("selectionEntryGroups","costs","modifiers"))
dcp=deep_prefix(dark,"r43-pra-dark-copy-");dcp.set("id","r43-pra-dark-retinue");dcp.set("name","Dark Fury Assault Squad — Retinue");strip_foc_and_visibility(dcp);catlink(dcp,"r43-pra-dark-limit","Raven Guard — Dark Fury limit",CAT_DF);pss.append(dcp)

# Corax Primarch retinue
cg=group(cor,"r43-corax-retinue","Primarch Retinue — choose up to one (no separate FOC slot)",0,1)
css=cont(cg,"selectionEntries",before=("selectionEntryGroups","costs","modifiers"))
# generic Honour Guard / Terminator Command from any existing nested selection by name
def find_sel_name(name):
    return next((x for x in cr.iter(C("selectionEntry")) if x.get("name")==name),None)
for idx,name in enumerate(["Legion Honour Guard Squad","Legion Terminator Command Squad"]):
    src=find_sel_name(name)
    if src is not None:
        cp=deep_prefix(src,f"r43-corax-ret-{idx}-");cp.set("id",f"r43-corax-ret-{idx}");strip_foc_and_visibility(cp);css.append(cp)
for idx,src,name,cat in [(2,dark,"Dark Fury Assault Squad",CAT_DF),(3,rap,"Raptor Squad",CAT_RAP)]:
    cp=deep_prefix(src,f"r43-corax-ret-{idx}-");cp.set("id",f"r43-corax-ret-{idx}");cp.set("name",name);strip_foc_and_visibility(cp);catlink(cp,f"r43-corax-ret-{idx}-limit",name+" limit",cat);css.append(cp)
# Avenging Shadow variant
av=sel(cor,"r43-corax-avenging","The Avenging Shadow — post-Istvaan variant","upgrade",0,None,1)
add_rule(av,"r43-corax-avenging-arm","Patchwork Panoply","Corax has a 2+ Armour Save and 4+ Invulnerable Save instead of his normal Primarch Armour protection. His armour still counts as Primarch Armour for all other purposes.")
add_rule(av,"r43-corax-avenging-ghost","Ghost of Istvaan","Replace the Stealth granted by The Shadowed Lord with Shrouded. Corax retains Hit & Run.")
add_rule(av,"r43-corax-avenging-hate","Hater of Traitors","Corax has Hatred (Traitor Legiones Astartes).")
ilr(av,"Shrouded");ilr(av,"Hatred")

# Deliverer/Raptor limits
catlink(deliver,"r43-del-limit","Raven Guard — Deliverer limit",CAT_DEL);catlink(rap,"r43-rap-limit","Raven Guard — Raptor limit",CAT_RAP)

# Rites
dec=ids[DEC];clear_rules(dec)
add_rule(dec,"r43-dec-bell","For Whom the Bell Tolls","All Raven Guard units gain Preferred Enemy (Independent Characters). An enemy unit containing one or more Independent Characters counts as a Preferred Enemy until all Independent Characters in it have been slain or left the unit.")
add_rule(dec,"r43-dec-pred","Predatory Strike","If the mission requires a roll for deployment order, deployment zone choice or which player takes the first turn, the Raven Guard player may re-roll that roll. The entire result is re-rolled and the second result accepted. This may be used once per battle.")
add_rule(dec,"r43-dec-fury","Fury From Above","Raven Guard Legion Heavy Support Squads must select either a Legion Drop Pod or Anvillus Dreadclaw Drop Pod as a Dedicated Transport at normal cost. Normal Transport Capacity and deployment restrictions apply.")
add_rule(dec,"r43-dec-limit","Limitations","The Detachment may include no more than one Heavy Support choice and no more than one Centurion upgraded to a Consul. It may not include a Fortification or an Allied Detachment drawn from another Space Marine Legion.")
visibility(dec,[LEG])
# Required HSS transport
hss=ids["hs-heavy-support-squad"];hg=group(hss,"r43-dec-hss-trans","Decapitation Strike — required Dedicated Transport",0,1,True)
mn=cons(hg,"r43-dec-hss-trans-min","min",0);modifier(hg,"r43-dec-hss-trans-show","set","hidden","false",[{"childId":LEG},{"childId":DEC}]);modifier(hg,"r43-dec-hss-trans-min1","set",mn.get("id"),1,[{"childId":LEG},{"childId":DEC}])
elink(hg,"r43-dec-hss-pod","Legion Drop Pod","transport-drop-pod",0,None,1);elink(hg,"r43-dec-hss-dc","Anvillus Dreadclaw Drop Pod","transport-dreadclaw",0,None,1)

lib=ids[LIB];clear_rules(lib)
add_rule(lib,"r43-lib-freedom","Freedom Fighters","Once per battle, at the beginning of any Game Turn, the Raven Guard player may declare Freedom Fighters. Until the end of that Game Turn, every model in the Raven Guard Detachment and any allied Imperialis Militia Detachment gains Zealot.")
add_rule(lib,"r43-lib-slayer","Slayers of Tyrants","If the mission awards Victory Points for slaying the enemy Warlord, replace the normal award with D3 times its normal value.")
add_rule(lib,"r43-lib-example","Lead by Example","Models in an allied Imperialis Militia Detachment gain Fearless while at least one model is within 6 inches of a friendly model with Legiones Astartes (Raven Guard).")
add_rule(lib,"r43-lib-liberators","Liberators","An Allied Detachment drawn from the Imperialis Militia may be included without preventing use of this Rite. All other Allied Detachment rules continue to apply.")
add_rule(lib,"r43-lib-limit","Limitations","Loyalist Raven Guard only. The Detachment may not include units with Immobile or Slow and Purposeful, and may not include a Fortification.")
visibility(lib,[LEG,LOY])

# Liberation: hide selections whose own rules explicitly say Immobile or Slow and Purposeful.
blocked=0
for e in cr.iter(C("selectionEntry")):
    if e in (lib,):continue
    txt=textish(e)
    if re.search(r"\bimmobile\b",txt) or "slow and purposeful" in txt:
        modifier(e,e.get("id")+"-r43-lib-hide","set","hidden","true",[{"childId":LEG},{"childId":LIB}]);blocked+=1

# Raptor/Deliverer source 0-1 and Dark Fury inferred normal 0-1
# Note: Agapito explicitly says "rather than the normal 0-1", which resolves the Dark Fury unit-page omission.

# Revision
cr.set("revision","43");cr.set("gameSystemRevision","8");gr.set("revision","8")
ct.write(CAT,encoding="utf-8",xml_declaration=True);ET.register_namespace("",GNS);gt.write(GST,encoding="utf-8",xml_declaration=True)
ET.register_namespace("",INS);it=ET.parse(IDX);ir=it.getroot()
for x in ir.iter(I("dataIndexEntry")):
    if x.get("filePath")=="Legiones Astartes.cat":x.set("dataRevision","43")
    if x.get("filePath")=="Prohammer 30k.gst":x.set("dataRevision","8")
it.write(IDX,encoding="utf-8",xml_declaration=True)

# Validation
rr=ET.parse(CAT).getroot();gg=ET.parse(GST).getroot();checks=[]
def ck(n,o):
    checks.append((n,bool(o)))
    if not o:raise RuntimeError("R43 validation failed: "+n)
ck("CAT43",rr.get("revision")=="43");ck("GST8",gg.get("revision")=="8");ck("CAT points GST8",rr.get("gameSystemRevision")=="8")
idx=IDX.read_text(encoding="utf-8");ck("Index43/8",'dataRevision="43"' in idx and 'dataRevision="8"' in idx)
rids={x.get("id"):x for x in rr.iter() if x.get("id")};gids={x.get("id"):x for x in gg.iter() if x.get("id")}
# no Source Entry on XIX roots
for i in range(10):
    k=next((x for x in rids if x.startswith(f"r41-unit-xix-{i}-")),None)
    if k:ck(k+" no Source Entry",not any((z.get("name") or "")=="Source Entry" for z in rids[k].findall(f"./{C('rules')}/{C('rule')}")))
# replacement chars hidden as top-level
for eid in ["r41-unit-xix-4-kaedes-nex","r41-unit-xix-6-agapito-nev","r41-unit-xix-8-nykona-sharrowkyn"]:ck(eid+" not standalone",rids[eid].get("hidden")=="true")
ck("Kaedes nested in Destroyers","r43-rg-kaedes-replacement" in rids)
ck("Agapito nested in Dark Furies","r43-rg-agapito-replacement" in rids)
ck("Sharrowkyn Recon/Seeker replacements","r43-rg-sharrowkyn-recon" in rids and "r43-rg-sharrowkyn-seeker" in rids)
ck("Corax no numeral name",not re.match(r"^[IVX]+\s*[—-]",rids["r41-unit-xix-9-xix-corvus-corax-the-raven-lord"].get("name") or ""))
ck("Raptor loyalist gated",LOY in ET.tostring(rids["r41-unit-xix-3-raptor-squad"],encoding="unicode"))
ck("Liberation loyalist gated",LOY in ET.tostring(rids[LIB],encoding="unicode"))
ck("Decap HSS transport group exists","r43-dec-hss-trans" in gids or "r43-dec-hss-trans" in rids or any(x.get("id")=="r43-dec-hss-trans" for x in rr.iter()))
ck("Heavy<=Fast category exists",CAT_HS in gids)
ck("Dark Fury/Deliverer/Raptor limits exist",all(x in gids for x in [CAT_DF,CAT_DEL,CAT_RAP]))
ck("Recon sniper discounted",sniper_discount>0)
ck("Sergeant armoury RG gear propagated",serg_added>0)
newids=collections.Counter(x.get("id") for x in rr.iter() if x.get("id"));worse={k:v for k,v in newids.items() if v>max(1,baseline_ids.get(k,0))}
ck("No new/worsened duplicate IDs",not worse)

lines=[
"Live R43 — Raven Guard implementation",
"Input CAT=42/GST=7 -> CAT=43/GST=8","",
"LEGION:",
"- Rebuilt Surgical Strike, Rapid Reaction, Shadow Masters and Limited Vehicles as clean shared rules.",
"- Limited Vehicles is mechanically enforced: Raven Guard Heavy Support selections may never exceed Fast Attack selections.",
f"- Raven Guard compulsory-capable Troops counter tags {comp_tag} legal Troops; Recon Squads count despite their normal Support Squad rule.",
f"- Applied the Shadow Masters 2-point Sniper Rifle discount to {sniper_discount} Recon Sniper selectors and added 2-point IC Sniper access.","",
"ARMOURY:",
"- Raven's Talons, Fulcrum Hand Cannon, Infravisor, Shroud Bombs, Cameleoline and Teleportation Transponders now use canonical shared rule/profile references.",
f"- Added {serg_added} controlled Sergeant-armoury links for Fulcrum Hand Cannon/Infravisor instead of exposing them to ordinary models.",
"- Raven's Talons on Veteran models scale with real squad size; Character Talons require a pair of Lightning Claws; IC Transponders require Terminator armour.","",
"UNITS:",
"- Rebuilt Mor Deythan, Dark Furies, Deliverers and Raptors with real rules, dynamic squad-wide costs, model-scaled replacement limits and leader Armoury access.",
"- Deliverers are roster-wide 0-1; Raptors are Loyalist-only and roster-wide 0-1.",
"- Dark Furies use the 0-1 limit explicitly referenced by Agapito Nev; Agapito raises it to 0-2.",
"- Deliverer transport capacity hides Land Raiders/Dreadclaws above five Terminator models.","",
"CHARACTERS:",
"- Kaedes Nex is no longer a standalone HQ: he is a Destroyer Sergeant replacement.",
"- Agapito Nev is no longer a standalone HQ: he is a Dark Fury Strike Leader replacement.",
"- Nykona Sharrowkyn is no longer a standalone HQ: he replaces a Recon or Seeker Sergeant, with one shared roster-wide limit.",
"- Alvarex Maun and Branne Nev remain genuine HQ choices with their rules restored.",
"- Branne can take one no-slot Raptor Squad, still sharing the normal Raptor 0-1.",
"- Corvus Corax is Loyalist-only, has functional Primarch retinue choices and the selectable Avenging Shadow variant.",
"- The source lists Dangerous Weaponry for Kaedes Nex without defining a Raven Guard effect; R43 preserves the name and explicitly does not invent a rule.","",
"RITES:",
"- Decapitation Strike: max one Heavy Support, max one Consul Centurion, Heavy Support Squads require Drop Pod/Dreadclaw, plus source battlefield effects.",
f"- Liberation Force: Loyalist-only and hides {blocked} entries whose own rules explicitly include Immobile or Slow and Purposeful. Militia/Fortification restrictions remain text where those external structures are unavailable.","",
"VALIDATION:"
]+[f'- {"PASS" if ok else "FAIL"}: {n}' for n,ok in checks]
OUT.write_text("\n".join(lines)+"\n",encoding="utf-8");print(OUT.read_text())
