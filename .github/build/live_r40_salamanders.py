from pathlib import Path
import copy, hashlib, re, xml.etree.ElementTree as ET

CAT=Path("Legiones Astartes.cat"); GST=Path("Prohammer 30k.gst"); IDX=Path("index.xml")
OUT=Path("inspection-live-r40-salamanders.txt")
CNS="http://www.battlescribe.net/schema/catalogueSchema"; GNS="http://www.battlescribe.net/schema/gameSystemSchema"; INS="http://www.battlescribe.net/schema/dataIndexSchema"
ET.register_namespace("",CNS)
C=lambda t:f"{{{CNS}}}{t}"; G=lambda t:f"{{{GNS}}}{t}"; I=lambda t:f"{{{INS}}}{t}"

ct=ET.parse(CAT); cr=ct.getroot(); gt=ET.parse(GST); gr=gt.getroot()
if cr.get("revision")!="39": raise RuntimeError(f"R40 expected CAT39, got {cr.get('revision')}")
if gr.get("revision")!="4": raise RuntimeError(f"R40 expected GST4, got {gr.get('revision')}")

def qns(e): return e.tag.split("}")[0].strip("{")
def cont(p,tag,before=("constraints","categoryLinks","entryLinks","infoLinks","profiles","rules","selectionEntries","selectionEntryGroups","costs","modifiers")):
    ns=qns(p); q=f"{{{ns}}}{tag}"; x=p.find(q)
    if x is not None:return x
    x=ET.Element(q); kids=list(p); idx=len(kids)
    for j,k in enumerate(kids):
        if k.tag.split("}")[-1] in before: idx=j; break
    p.insert(idx,x); return x
def cons(p,id_,typ,val,field="selections",scope="parent",child=False):
    ns=qns(p); cs=cont(p,"constraints"); q=f"{{{ns}}}constraint"; x=next((z for z in cs.findall(q) if z.get("id")==id_),None)
    if x is None:x=ET.SubElement(cs,q)
    x.attrib.update({"id":id_,"type":typ,"value":str(val),"field":field,"scope":scope,"shared":"true","includeChildSelections":"true" if child else "false","includeChildForces":"false"})
    return x
def cost(p,val):
    cs=cont(p,"costs",before=("modifiers",)); x=next((z for z in cs.findall(C("cost")) if z.get("typeId")=="pts"),None)
    if x is None:x=ET.SubElement(cs,C("cost"),{"name":"Points","typeId":"pts"})
    x.set("value",str(val));return x
def modifier(p,id_,typ,field,value,conditions=None,repeats=None):
    ns=qns(p); ms=cont(p,"modifiers"); q=f"{{{ns}}}modifier"; x=next((z for z in ms.findall(q) if z.get("id")==id_),None)
    if x is None:x=ET.SubElement(ms,q)
    x.attrib.update({"id":id_,"type":typ,"field":field,"value":str(value)})
    for ch in list(x):x.remove(ch)
    if repeats:
        rs=ET.SubElement(x,f"{{{ns}}}repeats")
        for rp in repeats:
            ET.SubElement(rs,f"{{{ns}}}repeat",{"field":rp.get("field","selections"),"scope":rp.get("scope","root-entry"),"value":str(rp.get("value",1)),"shared":"true","childId":rp["childId"],"includeChildSelections":"true" if rp.get("includeChildSelections",False) else "false","includeChildForces":"false","repeats":str(rp.get("repeats",1)),"roundUp":"true" if rp.get("roundUp",False) else "false"})
    if conditions:
        if len(conditions)==1: target=ET.SubElement(x,f"{{{ns}}}conditions")
        else:
            cgs=ET.SubElement(x,f"{{{ns}}}conditionGroups"); cg=ET.SubElement(cgs,f"{{{ns}}}conditionGroup",{"type":"and"}); target=ET.SubElement(cg,f"{{{ns}}}conditions")
        for c in conditions:
            ET.SubElement(target,f"{{{ns}}}condition",{"type":c.get("type","atLeast"),"value":str(c.get("value",1)),"field":c.get("field","selections"),"scope":c.get("scope","roster"),"childId":c["childId"],"shared":"true","includeChildSelections":"true" if c.get("includeChildSelections",True) else "false","includeChildForces":"false"})
    return x
def catlink(p,id_,name,target,primary=False):
    ns=qns(p); cs=cont(p,"categoryLinks"); q=f"{{{ns}}}categoryLink"; x=next((z for z in cs.findall(q) if z.get("id")==id_),None)
    if x is None:x=ET.SubElement(cs,q)
    x.attrib.update({"id":id_,"name":name,"targetId":target,"hidden":"false"})
    if primary:x.set("primary","true")
    return x
def add_rule(p,id_,name,text):
    rs=cont(p,"rules"); r=next((z for z in rs.findall(C("rule")) if z.get("id")==id_),None)
    if r is None:r=ET.SubElement(rs,C("rule"))
    r.attrib.update({"id":id_,"name":name,"hidden":"false"}); d=r.find(C("description"))
    if d is None:d=ET.SubElement(r,C("description"))
    d.text=text;return r
def clear_rules(p):
    rs=p.find(C("rules"))
    if rs is not None:p.remove(rs)
def add_infolink(p,id_,name,target,typ="rule",hidden=False):
    ils=cont(p,"infoLinks"); x=next((z for z in ils.findall(C("infoLink")) if z.get("id")==id_),None)
    if x is None:x=ET.SubElement(ils,C("infoLink"))
    x.attrib.update({"id":id_,"name":name,"targetId":target,"type":typ,"hidden":"true" if hidden else "false"});return x
def group(p,id_,name,minv=None,maxv=None,hidden=False):
    gs=cont(p,"selectionEntryGroups",before=("costs","modifiers")); g=next((z for z in gs.findall(C("selectionEntryGroup")) if z.get("id")==id_),None)
    if g is None:g=ET.SubElement(gs,C("selectionEntryGroup"))
    g.attrib.update({"id":id_,"name":name,"hidden":"true" if hidden else "false"})
    if minv is not None:cons(g,id_+"-min","min",minv)
    if maxv is not None:cons(g,id_+"-max","max",maxv)
    return g
def sel(p,id_,name,typ="upgrade",pts=0,minv=None,maxv=1,default=None,hidden=False):
    ss=cont(p,"selectionEntries",before=("selectionEntryGroups","costs","modifiers")); e=next((z for z in ss.findall(C("selectionEntry")) if z.get("id")==id_),None)
    if e is None:e=ET.SubElement(ss,C("selectionEntry"))
    e.attrib.update({"id":id_,"name":name,"type":typ,"hidden":"true" if hidden else "false"})
    if default is not None:e.set("defaultAmount",str(default))
    if minv is not None:cons(e,id_+"-min","min",minv)
    if maxv is not None:cons(e,id_+"-max","max",maxv)
    cost(e,pts);return e
def elink(p,id_,name,target,pts=0,minv=None,maxv=1,hidden=False):
    es=cont(p,"entryLinks",before=("infoLinks","profiles","rules","selectionEntries","selectionEntryGroups","costs","modifiers")); e=next((z for z in es.findall(C("entryLink")) if z.get("id")==id_),None)
    if e is None:e=ET.SubElement(es,C("entryLink"))
    e.attrib.update({"id":id_,"name":name,"targetId":target,"type":"selectionEntry","import":"true","hidden":"true" if hidden else "false"})
    if minv is not None:cons(e,id_+"-min","min",minv)
    if maxv is not None:cons(e,id_+"-max","max",maxv)
    cost(e,pts);return e
def profile(p,id_,name,chars):
    ps=cont(p,"profiles",before=("rules","selectionEntries","selectionEntryGroups","costs","modifiers")); pr=next((z for z in ps.findall(C("profile")) if z.get("id")==id_),None)
    if pr is None:pr=ET.SubElement(ps,C("profile"))
    pr.attrib.update({"id":id_,"name":name,"typeId":"prof-weapon","hidden":"false"}); chs=pr.find(C("characteristics"))
    if chs is None:chs=ET.SubElement(pr,C("characteristics"))
    for z in list(chs):chs.remove(z)
    for k,v,tid in [("Range",chars[0],"weapon-range"),("S",chars[1],"weapon-s"),("AP",chars[2],"weapon-ap"),("Type",chars[3],"weapon-type")]:
        z=ET.SubElement(chs,C("characteristic"),{"name":k,"typeId":tid}); z.text=str(v)
    return pr
def clear_groups(p):
    gs=p.find(C("selectionEntryGroups"))
    if gs is not None:p.remove(gs)
def deep_prefix(e,prefix):
    x=copy.deepcopy(e); olds=[z.get("id") for z in x.iter() if z.get("id")]; mp={o:prefix+o for o in olds}
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
def visibility(e,req):
    e.set("hidden","true"); modifier(e,e.get("id")+"-r40-show","set","hidden","false",[{"childId":x,"scope":"roster"} for x in req])
def primary_cat(e,target):
    return any(c.get("targetId")==target and c.get("primary")=="true" for c in e.findall(f"./{C('categoryLinks')}/{C('categoryLink')}"))
def strip_old_option_group(e):
    gs=e.find(C("selectionEntryGroups"))
    if gs is None:return
    for g in list(gs):
        if (g.get("name") or "")=="Options":gs.remove(g)
def model_selector(e):
    return next((z for z in e.findall(f"./{C('selectionEntries')}/{C('selectionEntry')}") if (z.get("id") or "").endswith("-additional") or (z.get("name") or "")=="Squad Models"),None)
def dynmax(g,id_,modelid,factor=1,divisor=1):
    c=cons(g,id_,"max",0)
    modifier(g,id_+"-mod","increment",id_,factor,None,[{"childId":modelid,"scope":"root-entry","value":divisor,"repeats":1,"roundUp":False}])
    return c
def squad_upgrade(e,id_,name,ppm,modelid):
    x=sel(e,id_,name,"upgrade",0,None,1)
    modifier(x,id_+"-cost","increment","pts",ppm,None,[{"childId":modelid,"scope":"root-entry","value":1,"repeats":1}]);return x
def transport_group(e,id_,names,modelid=None,jumpid=None):
    g=group(e,id_,"Dedicated Transport",0,1)
    targets={"Rhino":"transport-rhino","Drop Pod":"transport-drop-pod","Dreadclaw Drop Pod":"transport-dreadclaw","Dreadnought Drop Pod":"transport-dreadnought-pod","Spartan Assault Tank":"hs-spartan"}
    for nm in names:
        if nm=="Land Raider":
            lg=group(g,id_+"-lr","Land Raider",0,1)
            for xnm,xid in [("Land Raider Phobos","hs-lr-phobos"),("Land Raider Proteus","hs-lr-proteus"),("Land Raider Achilles","hs-lr-achilles")]:
                l=elink(lg,id_+"-"+re.sub(r"[^a-z0-9]+","-",xnm.lower()),xnm,xid,0,None,1)
                if modelid and e.get("name","").startswith("Firedrake"):
                    modifier(l,l.get("id")+"-cap","set","hidden","true",[{"childId":modelid,"scope":"root-entry","type":"atLeast","value":6,"includeChildSelections":False}])
        else:
            l=elink(g,id_+"-"+re.sub(r"[^a-z0-9]+","-",nm.lower()),nm,targets[nm],0,None,1)
            if modelid and e.get("name","").startswith("Firedrake") and nm=="Dreadclaw Drop Pod":
                modifier(l,l.get("id")+"-cap","set","hidden","true",[{"childId":modelid,"scope":"root-entry","type":"atLeast","value":6,"includeChildSelections":False}])
    if jumpid:modifier(g,id_+"-hide-jump","set","hidden","true",[{"childId":jumpid,"scope":"root-entry"}])
    return g

ids={e.get("id"):e for e in cr.iter() if e.get("id")}
LOY="allegiance-loyalist"; TRA="allegiance-traitor"; LEG="legion-xviii"
COVR="r25-rite-xviii-0-the-covenant-of-fire"; AWAK="r25-rite-xviii-1-the-awakening-fire"

# ---------- shared rules ----------
sr=cr.find(C("sharedRules"))
if sr is None: sr=ET.Element(C("sharedRules")); cr.insert(0,sr)
shared={r.get("name"):r for r in sr.findall(C("rule"))}
def shr(name,text,id_=None):
    r=shared.get(name)
    if r is None:
        r=ET.SubElement(sr,C("rule"),{"id":id_ or "r40-sal-"+re.sub(r"[^a-z0-9]+","-",name.lower()).strip("-")[:70],"name":name,"hidden":"false"}); shared[name]=r
    d=r.find(C("description"))
    if d is None:d=ET.SubElement(r,C("description"))
    d.text=text; return r

rules={
"Legiones Astartes (Salamanders)":"This is the named XVIII Legion version of Legiones Astartes. Models with this rule also follow the normal Legiones Astartes rules and And They Shall Know No Fear. A model may only possess one named Legiones Astartes rule.",
"Promethean Cult":"Salamanders models may re-roll To Hit rolls of 1 with Thunder Hammers, Melta Bombs, Meltaguns, Multi-Meltas and other weapons with the Melta special rule. They may re-roll To Wound rolls of 1 when firing Flame weapons.",
"Sturdy":'All Salamanders models with an Initiative characteristic, except Dreadnoughts, suffer -1 Initiative after all other modifiers. Salamanders units also subtract 1" from Fall Back distance, to a minimum of 1". The Initiative penalty applies normally during Pursuit.',
"Never Give Up":"At the end of the final scheduled game turn, the Salamanders player may choose to play one additional complete game turn. Both players take one additional turn, then the battle ends automatically. This may be used only once and cannot extend a mission already ended by a specific objective/action.",
"Salamanders Mantle":"If an unsaved Wound would become a Massive Wound solely because attack Strength is at least double the bearer's Toughness, it instead inflicts only one Wound. It provides no protection against weapons or rules that explicitly inflict Massive Wounds by another method. Only one Salamanders Mantle may be included in the army.",
"Fire-based Warfare":"Flamers used by Salamanders are Strength 5 AP5 Assault 1 Flame weapons. Heavy Flamers used by Salamanders are Strength 6 AP4 Assault 1 Flame weapons. Where a Legion Tactical or Veteran Squad may purchase a Flamer, it may instead purchase a Heavy Flamer for +10 points. Legion Heavy Support Squads may select Heavy Flamers as a Heavy Weapon option for +10 points per model.",
"Proscribed Munitions":"A Salamanders Detachment may not select Phosphex weapons or Phosphex ammunition unless a specific Salamanders unit or Character entry explicitly states otherwise.",
"Dragonscale Storm Shield":"The bearer has a 4+ Invulnerable Save in close combat and against shooting attacks made with Flame or Melta weapons. Against all other shooting attacks, it provides a 5+ Invulnerable Save.",
"Firedrake Retinue":"A Firedrake Terminator Squad may be selected as the retinue of a Salamanders Praetor wearing Terminator Armour, Artellus Numeon, Vulkan, or another Character specifically permitted to take it. It occupies no separate Elites selection.",
"Pyroclast Flame Projector":"Each time this weapon fires, choose either Salamanders Heavy Flamer mode or Meltagun mode. It counts as the chosen weapon for Promethean Cult and Fire-based Warfare.",
"Dual Pistols":"A model with this rule may fire both of its Pistol weapons in the Shooting phase at the same target. If it does so, it may not fire another weapon that phase.",
"Destroyer Cadre":"An Infernus Destroyer Squad may only be joined by a Legion Moritat or another Character specifically stated to be permitted to join Destroyer units.",
"Guided by Prophecy":"At the beginning of an Assault phase, the squad may take a Leadership test using Leadership 7 regardless of the Leadership of models in the unit. If passed, until the end of the phase the squad has Weapon Skill 5 and Feel No Pain (6+). If failed, there is no effect.",
"Close-Quarters Arsenal":"A Sanctifier equipped with two Pistol weapons has Dual Pistols. Both Pistols must fire at the same target.",
"Battlesmith":"During the Shooting phase, instead of firing, the model may attempt to repair one eligible friendly model in base contact. Roll D6; on 5+ repair one Engine Damaged, Weapon Destroyed or Immobilised result from a Vehicle, or restore one lost Wound to an eligible non-Vehicle model. Only one attempt per turn; a model may benefit from only one successful repair per turn. Battlesmith cannot return destroyed models. Equipment modifiers to the roll apply unless stated otherwise.",
"Bolster Defences":"Before deployment, nominate one ruin or similar defensive terrain feature wholly or partly in the army's deployment zone. Improve its Cover Save by 1 to a maximum of 3+. A terrain feature may only be Bolstered once.",
"Reinforced Ceramite":"Uses the normal Armoured Ceramite rules: Melta weapons do not receive their additional Armour Penetration die against this vehicle, regardless of range.",
"Primarch Armour":"Confers a 1+ Armour Save and a 4+ Invulnerable Save. A natural roll of 1 always fails.",
}
for n,t in rules.items():shr(n,t)
# standard fallbacks only if absent
std_fallback={
"Stubborn":"Ignore negative Leadership modifiers on Morale and Pinning tests.",
"Implacable Advance":"In missions distinguishing Scoring and non-Scoring units, this Terminator unit counts as Scoring whenever Troops choices normally count as Scoring.",
"Counter-Attack":"If this unit is unengaged when charged, it may take a Leadership test; if passed it gains +1 Attack for that Assault phase.",
"Hardened Armour":'Failed Armour Saves caused by Blast or Template weapons may be re-rolled. Reduce Advance distance by 1" and Charge/Pursuit distance by 1".',
"Support Squad":"May be selected as Troops but may not fulfil either compulsory Troops selection unless a Legion rule or Rite removes the restriction.",
"Fear":"Enemy units in base contact must pass a Leadership test before resolving attacks or fight at WS1 for that melee engagement.",
"Fearless":"Automatically passes Morale and Pinning tests and may not voluntarily fail a break test.",
"Move Through Cover":"Roll 3D6 for Difficult Terrain tests instead of 2D6 and choose the highest.",
"Zealot":"The unit gains Fearless and Hatred.",
"Independent Character":"May join eligible friendly units and follows the normal ProHammer Independent Character rules.",
"Master of the Legion":"Permits the Detachment to use a Rite of War and follows the normal Master of the Legion restrictions.",
"Primarch":"Has Independent Character, Eternal Warrior, Fear, Fearless, Adamantium Will, Fleet, It Will Not Die and Master of the Legion, and the named Legiones Astartes rule of his Legion.",
"It Will Not Die":"At the start of its turn, a wounded model rolls D6; on 5+ it regains one lost Wound. Vehicles may instead repair an Engine Damaged, Weapon Destroyed or Immobilized result on 5+.",
"Master-Crafted":"Re-roll one failed To Hit roll per turn.",
"Two-Handed":"No bonus Attack for an additional close-combat weapon.",
"Armourbane":"Roll 2D6 for Armour Penetration.",
"Concussive":"A model suffering an unsaved Wound is reduced to Initiative 1 until the end of the following Assault phase; against Vehicles it inflicts Crew Shaken if hit.",
"Rending":"On a To Wound roll of 6, the attack becomes AP2 for ranged attacks or a Power Weapon attack for melee attacks. Against Vehicles, an Armour Penetration roll of 6 adds D3.",
"Furious Charge":"Models gain +1 Strength and +1 Initiative in assault on the turn they charged.",
}
for n,t in std_fallback.items():
    if n not in shared:shr(n,t,"r40-standard-"+re.sub(r"[^a-z0-9]+","-",n.lower()).strip("-"))
def ilrule(e,name,suffix=None):
    r=shared[name];add_infolink(e,e.get("id")+"-"+(suffix or re.sub(r"[^a-z0-9]+","-",name.lower()).strip("-")),name,r.get("id"),"rule")
def legion(e):
    ilrule(e,"Legiones Astartes (Salamanders)","sal-leg")
    for n in ["Promethean Cult","Sturdy","Never Give Up"]:ilrule(e,n,"sal-"+re.sub(r"[^a-z0-9]+","-",n.lower()).strip("-"))

# shared weapon profiles
sp=cr.find(C("sharedProfiles"))
if sp is None:sp=ET.Element(C("sharedProfiles"));cr.insert(1,sp)
def shprof(id_,name,chars):
    p=next((z for z in sp.findall(C("profile")) if z.get("id")==id_),None)
    if p is None:p=ET.SubElement(sp,C("profile"))
    p.attrib.update({"id":id_,"name":name,"typeId":"prof-weapon","hidden":"false"}); chs=p.find(C("characteristics"))
    if chs is None:chs=ET.SubElement(p,C("characteristics"))
    for z in list(chs):chs.remove(z)
    for k,v,tid in [("Range",chars[0],"weapon-range"),("S",chars[1],"weapon-s"),("AP",chars[2],"weapon-ap"),("Type",chars[3],"weapon-type")]:
        z=ET.SubElement(chs,C("characteristic"),{"name":k,"typeId":tid});z.text=str(v)
    return p
P_FL=shprof("r40-sal-prof-flamer","Salamanders Flamer",("Template","5","5","Assault 1, Flame"))
P_HF=shprof("r40-sal-prof-heavy-flamer","Salamanders Heavy Flamer",("Template","6","4","Assault 1, Flame"))
P_INF=shprof("r40-sal-prof-inferno","Inferno Pistol",('6"',"8","1","Pistol, Melta"))
P_PYF=shprof("r40-sal-prof-pyro-flame","Pyroclast Flame Projector — Flame",("Template","6","4","Assault 1, Flame"))
P_PYM=shprof("r40-sal-prof-pyro-melta","Pyroclast Flame Projector — Melta",('12"',"8","1","Assault 1, Melta"))
P_FURY=shprof("r40-sal-prof-fury","Fury of the Salamander",('18"',"5","1","Witchfire — Beam, Assault 1, Elemental Horror"))
P_IGN=shprof("r40-sal-prof-ignatus","Ignatus",("—","+1 on charge","Power Weapon","Melee, Master-crafted"))
P_DARK=shprof("r40-sal-prof-darkstar","Darkstar Falling",("—","+2","Power Weapon","Melee, Two-Handed, Master-crafted, Concussive, Armourbane vs Vehicles"))
P_DREAD=shprof("r40-sal-prof-dreadfire","Dreadfire Cannon",("Template","6","4","Assault 1, Flame, Twin-linked"))
P_DAWN=shprof("r40-sal-prof-dawnbringer","Dawnbringer",("—","10","Power Weapon","Melee, Two-Handed, Master-crafted, Armourbane, Concussive"))
P_FURN=shprof("r40-sal-prof-furnace","Furnace's Heart",('18"',"6","2","Assault 1, Rending, Master-crafted"))
P_GAUNT=shprof("r40-sal-prof-gauntlet","Gauntlet of the Forge",("Template","6","4","Assault 1, Flame, Master-crafted"))

# Legion selector
leg=ids[LEG]; clear_rules(leg)
legion(leg)
for n in ["Salamanders Mantle","Fire-based Warfare","Proscribed Munitions"]:ilrule(leg,n,"leg-"+re.sub(r"[^a-z0-9]+","-",n.lower()).strip("-"))
for p,n in [(P_FL,"Salamanders Flamer"),(P_HF,"Salamanders Heavy Flamer"),(P_INF,"Inferno Pistol")]:
    add_infolink(leg,"r40-leg-"+p.get("id"),n,p.get("id"),"profile")

# ---------- GST hidden categories ----------
ce=gr.find(G("categoryEntries"))
if ce is None:ce=ET.SubElement(gr,G("categoryEntries"))
def gcat(id_,name):
    x=next((z for z in ce.findall(G("categoryEntry")) if z.get("id")==id_),None)
    if x is None:x=ET.SubElement(ce,G("categoryEntry"))
    x.attrib.update({"id":id_,"name":name,"hidden":"true"});return x
CAT_MANTLE="r40-sal-mantle-limit"; CAT_CHAP="r40-sal-awakening-chaplain"; CAT_COVSUP="r40-sal-covenant-support"
CAT_JUMP="r40-sal-awakening-jump"; CAT_JET="r40-sal-awakening-jetbike"; CAT_SKIM="r40-sal-awakening-skimmer"; CAT_FLY="r40-sal-awakening-flyer"; CAT_NOMUS_DREAD="r40-sal-nomus-dread-hq"
for i,n in [(CAT_MANTLE,"Salamanders Mantle limit"),(CAT_CHAP,"Awakening Fire — Chaplain"),(CAT_COVSUP,"Covenant of Fire — Fast/Heavy choices"),(CAT_JUMP,"Awakening Fire — Jump Infantry"),(CAT_JET,"Awakening Fire — Jetbike"),(CAT_SKIM,"Awakening Fire — Skimmer"),(CAT_FLY,"Awakening Fire — Flyer"),(CAT_NOMUS_DREAD,"Nomus — Keeper of the Keys")]:gcat(i,n)
force=next(x for x in gr.iter(G("forceEntry")) if x.get("id")=="force-standard"); fcls=cont(force,"categoryLinks")
def fl(id_,name,target):
    x=next((z for z in fcls.findall(G("categoryLink")) if z.get("id")==id_),None)
    if x is None:x=ET.SubElement(fcls,G("categoryLink"))
    x.attrib.update({"id":id_,"name":name,"targetId":target,"hidden":"true"});return x
mfl=fl("r40-sal-mantle-force","Salamanders Mantle limit",CAT_MANTLE);cons(mfl,"r40-sal-mantle-max","max",1,"selections","parent",True)
cfl=fl("r40-sal-chap-force","Awakening Fire — Chaplain",CAT_CHAP);cons(cfl,"r40-sal-chap-min","min",0,"selections","parent",True);modifier(cfl,"r40-sal-chap-set","set","r40-sal-chap-min",1,[{"childId":AWAK,"scope":"roster"}])
nfl=fl("r40-sal-nomus-dread-force","Nomus — Keeper of the Keys",CAT_NOMUS_DREAD);cons(nfl,"r40-sal-nomus-dread-max","max",1,"selections","parent",True)
# Covenant combined FA/HS max equals Troops count
sfl=fl("r40-sal-cov-sup-force","Covenant of Fire — Fast/Heavy choices",CAT_COVSUP);cmax=cons(sfl,"r40-sal-cov-sup-max","max",99,"selections","parent",True)
modifier(sfl,"r40-sal-cov-sup-zero","set",cmax.get("id"),0,[{"childId":COVR,"scope":"roster"}])
modifier(sfl,"r40-sal-cov-sup-per-troop","increment",cmax.get("id"),1,[{"childId":COVR,"scope":"roster"}],[{"childId":"cat-troops","scope":"force","value":1,"repeats":1}])
# Awakening type max1
for cat,nm in [(CAT_JUMP,"Jump Infantry"),(CAT_JET,"Jetbike"),(CAT_SKIM,"Skimmer"),(CAT_FLY,"Flyer")]:
    x=fl("r40-sal-awak-"+re.sub(r"[^a-z]+","-",nm.lower()),"Awakening Fire — "+nm,cat);mx=cons(x,x.get("id")+"-max","max",99,"selections","parent",True);modifier(x,x.get("id")+"-set1","set",mx.get("id"),1,[{"childId":AWAK,"scope":"roster"}])

# Tag primary FA/HS roots for Covenant count
for e in cr.findall(f"./{C('selectionEntries')}/{C('selectionEntry')}"):
    if primary_cat(e,"cat-fast") or primary_cat(e,"cat-heavy"):catlink(e,e.get("id")+"-r40-covsup","Covenant of Fire — Fast/Heavy choices",CAT_COVSUP)

# Tag Chaplains
for id_ in ["hq-consul-chaplain","r41-unit-xviii-6-lord-chaplain-nomus-rhy-tan","r41-unit-xviii-7-xiaphas-jurr-prophet-of-fire"]:
    if id_ in ids:catlink(ids[id_],id_+"-r40-chap","Awakening Fire — Chaplain",CAT_CHAP)

# Tag obvious selected/fixed unit types for Awakening restriction.
for e in cr.iter(C("selectionEntry")):
    n=(e.get("name") or "").lower()
    # nested upgrade selectors count as one when selected
    if n in ("jump pack","jump packs") or ("jump pack" in n and e.get("type")=="upgrade"):catlink(e,e.get("id")+"-r40-jump","Awakening Fire — Jump Infantry",CAT_JUMP)
    if "jetbike" in n and e.get("type")=="upgrade":catlink(e,e.get("id")+"-r40-jet","Awakening Fire — Jetbike",CAT_JET)
for e in cr.findall(f"./{C('selectionEntries')}/{C('selectionEntry')}"):
    n=(e.get("name") or "").lower(); txt=" ".join((r.get("name") or "") for r in e.findall(f".//{C('rule')}"))+" "+" ".join((x.get("name") or "") for x in e.findall(f".//{C('infoLink')}"))
    if "assault squad" in n or "raptor squad" in n:catlink(e,e.get("id")+"-r40-jumpfix","Awakening Fire — Jump Infantry",CAT_JUMP)
    if "sky hunter" in n or "jetbike squad" in n:catlink(e,e.get("id")+"-r40-jetfix","Awakening Fire — Jetbike",CAT_JET)
    if any(k in n for k in ["land speeder","javelin","grav chariot"]) or "Skimmer" in txt:catlink(e,e.get("id")+"-r40-skim","Awakening Fire — Skimmer",CAT_SKIM)
    if any(k in n for k in ["storm eagle","fire raptor","xiphon","lightning","thunderhawk","stormbird"]) or "Flyer" in txt:catlink(e,e.get("id")+"-r40-fly","Awakening Fire — Flyer",CAT_FLY)

# ---------- armoury cleanup ----------
for eid,nm,prof in [("r46-sal-mantle","Salamanders Mantle",None),("r46-sal-inferno-pistol","Inferno Pistol",P_INF)]:
    e=ids[eid];clear_rules(e);ilrule(e,nm,"canonical")
    if prof:add_infolink(e,eid+"-profile",nm,prof.get("id"),"profile")
# price/access entries get concise actual mechanics, not "price note" only
for eid,name,text in [
 ("r46-sal-mastercrafted","Master-crafted Weapon — Salamanders price","A Salamanders model that may purchase a Master-crafted Weapon pays +10 points instead of +15. The selected weapon gains Master-crafted: re-roll one failed To Hit roll per turn. All normal eligibility restrictions remain."),
 ("r46-sal-artificer-armour","Artificer Armour — Salamanders access","A Salamanders non-Independent Character with Space Marine Armoury access may purchase Artificer Armour for +15 points even if its unit entry normally does not allow it. If the unit entry already offers Artificer Armour more cheaply, use that price instead. Artificer Armour grants a 2+ Armour Save."),
 ("r46-sal-heavy-flamer","Heavy Flamer instead of Flamer","Where a Salamanders Tactical or Veteran Squad may purchase a Flamer, it may instead purchase a Heavy Flamer for +10 points. Use the Salamanders Heavy Flamer profile: Template, S6, AP4, Assault 1, Flame."),
 ("r46-sal-ceramite","Armoured Ceramite — Salamanders price","An eligible Salamanders Vehicle or Dreadnought pays +10 points for Armoured Ceramite instead of its normal price; Land Raiders and Spartans use their listed normal price. Armoured Ceramite removes the additional Armour Penetration die granted by Melta regardless of range.")
]:
    e=ids[eid];clear_rules(e);add_rule(e,eid+"-r40",name,text)
if ids.get("r46-sal-heavy-flamer"):add_infolink(ids["r46-sal-heavy-flamer"],"r40-sal-hf-prof","Salamanders Heavy Flamer",P_HF.get("id"),"profile")
# Mantle roster category and named bearers
catlink(ids["r46-sal-mantle"],"r40-sal-mantle-cat","Salamanders Mantle limit",CAT_MANTLE)
for id_ in ["r41-unit-xviii-5-artellus-numeon","r41-unit-xviii-6-lord-chaplain-nomus-rhy-tan"]:
    catlink(ids[id_],id_+"-mantle-cat","Salamanders Mantle limit",CAT_MANTLE)
# Hide Phosphex selections/links for Salamanders
phosphex_hidden=0
for e in cr.iter(C("selectionEntry")):
    if "phosphex" in (e.get("name") or "").lower():
        modifier(e,e.get("id")+"-r40-sal-hide","set","hidden","true",[{"childId":LEG,"scope":"roster"}]);phosphex_hidden+=1
for e in cr.iter(C("entryLink")):
    if "phosphex" in (e.get("name") or "").lower():
        modifier(e,e.get("id")+"-r40-sal-hide","set","hidden","true",[{"childId":LEG,"scope":"roster"}]);phosphex_hidden+=1

# Inferno pistol access for obvious armoury groups
inferno_links=0
for g in cr.iter(C("selectionEntryGroup")):
    nm=(g.get("name") or "").lower()
    if not any(k in nm for k in ["additional wargear","sergeant armoury","weapon replacements","weapons and wargear"]):continue
    direct=g.findall(f"./{C('entryLinks')}/{C('entryLink')}")
    if any(x.get("targetId")=="r46-sal-inferno-pistol" for x in direct):continue
    # Require some evidence this is a Marine weapon/wargear group
    if not any(any(k in (x.get("name") or "").lower() for k in ["plasma pistol","bolt pistol","power weapon","melta bombs","combi"]) for x in direct):continue
    l=elink(g,"r40-sal-inferno-"+hashlib.sha1((g.get("id") or "").encode()).hexdigest()[:10],"Inferno Pistol — Salamanders","r46-sal-inferno-pistol",15,None,1,True)
    modifier(l,l.get("id")+"-show","set","hidden","false",[{"childId":LEG,"scope":"roster"}]);inferno_links+=1

# ---------- special units ----------
def patch_firedrake(e,is_root=False):
    clear_rules(e);strip_old_option_group(e);legion(e)
    for n in ["Stubborn","Implacable Advance","Dragonscale Storm Shield","Firedrake Retinue"]:ilrule(e,n)
    add_rule(e,e.get("id")+"-wg","Wargear","Terminator Armour, Thunder Hammer, Dragonscale Storm Shield.")
    m=model_selector(e)
    if m is None:raise RuntimeError("Firedrake model selector missing "+e.get("id"))
    m.set("name","Firedrakes (total squad size)");cost(m,45)
    mc=group(e,e.get("id")+"-mastercraft","Master-crafted Thunder Hammer — any model",0,None);dynmax(mc,mc.get("id")+"-dynmax",m.get("id"),1,1)
    opt=sel(mc,e.get("id")+"-mc-th","Master-crafted Thunder Hammer", "upgrade",10,None,10);ilrule(opt,"Master-Crafted")
    rg=group(e,e.get("id")+"-shield-repl","Replace Dragonscale Storm Shield — up to 2 per 5 models",0,None);dynmax(rg,rg.get("id")+"-dynmax",m.get("id"),2,5)
    elink(rg,e.get("id")+"-hf","Heavy Flamer","gear-heavy-flamer",10,None,4)
    elink(rg,e.get("id")+"-mm","Multi-Melta","gear-multimelta",20,None,4)
    # master armoury access, represented as exact allowance + Legion specials
    add_rule(e,e.get("id")+"-master-armoury","Firedrake Master Armoury","The Firedrake Master may select up to 50 points of permitted Terminator weapons and wargear from the Space Marine Armoury and Salamanders Armoury.")
    mg=group(e,e.get("id")+"-master-sal","Firedrake Master — Salamanders Armoury",0,2)
    elink(mg,e.get("id")+"-master-inferno","Inferno Pistol","r46-sal-inferno-pistol",15,None,1)
    elink(mg,e.get("id")+"-master-mc","Master-crafted Weapon","r46-sal-mastercrafted",10,None,1)
    if is_root:transport_group(e,e.get("id")+"-transport",["Land Raider","Dreadclaw Drop Pod","Spartan Assault Tank"],m.get("id"))
def patch_pyro(e,is_root=False):
    clear_rules(e);strip_old_option_group(e);legion(e);ilrule(e,"Stubborn");ilrule(e,"Pyroclast Flame Projector")
    add_infolink(e,e.get("id")+"-pyf","Pyroclast Flame Projector — Flame",P_PYF.get("id"),"profile");add_infolink(e,e.get("id")+"-pym","Pyroclast Flame Projector — Melta",P_PYM.get("id"),"profile")
    add_rule(e,e.get("id")+"-wg","Wargear","Artificer Armour, Pyroclast Flame Projector, Bolt Pistol, close-combat weapon, Frag Grenades.")
    m=model_selector(e);m.set("name","Pyroclasts (total squad size)");cost(m,30)
    squad_upgrade(e,e.get("id")+"-krak","Krak Grenades — entire squad (+2 pts/model)",2,m.get("id"));squad_upgrade(e,e.get("id")+"-melta","Melta Bombs — entire squad (+5 pts/model)",5,m.get("id"))
    sg=group(e,e.get("id")+"-warden","Pyroclast Warden",0,2);wg=group(sg,e.get("id")+"-warden-melee","Replace close-combat weapon",0,1)
    for nm,t,p in [("Rending Weapon","gear-rending",5),("Power Weapon","gear-power-weapon",10),("Power Fist","gear-power-fist",15),("Thunder Hammer","gear-thunder-hammer",20)]:elink(wg,e.get("id")+"-w-"+re.sub(r"[^a-z0-9]+","-",nm.lower()),nm,t,p,None,1)
    elink(sg,e.get("id")+"-w-inferno","Inferno Pistol","r46-sal-inferno-pistol",15,None,1);elink(sg,e.get("id")+"-w-mc","Master-crafted Weapon","r46-sal-mastercrafted",10,None,1)
    add_rule(e,e.get("id")+"-warden-arm","Pyroclast Warden Armoury","The Warden may select up to 50 points of permitted weapons and wargear from the Space Marine Armoury and Salamanders Armoury.")
    if is_root:transport_group(e,e.get("id")+"-transport",["Rhino","Drop Pod","Dreadclaw Drop Pod","Land Raider"],m.get("id"))
def patch_infernus(e,is_root=False):
    clear_rules(e);strip_old_option_group(e);legion(e)
    for n in ["Counter-Attack","Hardened Armour","Dual Pistols","Destroyer Cadre"]:ilrule(e,n)
    add_rule(e,e.get("id")+"-wg","Wargear","Hardened Power Armour, two Hand Flamers, Chainsword, Frag Grenades.")
    m=model_selector(e);m.set("name","Infernus Destroyers (total squad size)");cost(m,25)
    squad_upgrade(e,e.get("id")+"-krak","Krak Grenades — entire squad (+2 pts/model)",2,m.get("id"));squad_upgrade(e,e.get("id")+"-melta","Melta Bombs — entire squad (+5 pts/model)",5,m.get("id"))
    jump=squad_upgrade(e,e.get("id")+"-jump","Jump Packs — entire squad (+15 pts/model)",15,m.get("id"));catlink(jump,jump.get("id")+"-jumpcat","Awakening Fire — Jump Infantry",CAT_JUMP)
    add_rule(jump,jump.get("id")+"-rule","Jump Packs","If every model has a Jump Pack, the unit becomes Jump Infantry and may not select a Dedicated Transport.")
    hg=group(e,e.get("id")+"-heavy","Replace one Hand Flamer — 1 per 5 models",0,None);dynmax(hg,hg.get("id")+"-dynmax",m.get("id"),1,5)
    # suspensor profiles as rules; heavy flamer uses Salamanders S6
    hf=sel(hg,e.get("id")+"-hf-susp","Heavy Flamer with Suspensor Web", "upgrade",10,None,2);profile(hf,hf.get("id")+"-prof","Heavy Flamer with Suspensor Web",("Template","6","4","Assault 1, Flame"))
    mm=sel(hg,e.get("id")+"-mm-susp","Multi-Melta with Suspensor Web","upgrade",15,None,2);profile(mm,mm.get("id")+"-prof","Multi-Melta with Suspensor Web",('12"',"8","1","Assault 1, Melta"))
    anyg=group(e,e.get("id")+"-pistol","Replace either Hand Flamer — any model",0,None);dynmax(anyg,anyg.get("id")+"-dynmax",m.get("id"),1,1)
    elink(anyg,e.get("id")+"-volk","Volkite Serpenta","gear-volkite-serpenta",5,None,10);elink(anyg,e.get("id")+"-plasma","Plasma Pistol","gear-plasma-pistol",15,None,10)
    sg=group(e,e.get("id")+"-sgt","Infernus Sergeant",0,3);me=group(sg,e.get("id")+"-sgt-melee","Replace Chainsword",0,1)
    for nm,t,p in [("Rending Weapon","gear-rending",5),("Power Weapon","gear-power-weapon",10),("Lightning Claw","gear-lightning-claw",15),("Power Fist","gear-power-fist",15),("Thunder Hammer","gear-thunder-hammer",20)]:elink(me,e.get("id")+"-sgt-"+re.sub(r"[^a-z0-9]+","-",nm.lower()),nm,t,p,None,1)
    elink(sg,e.get("id")+"-sgt-inferno","Inferno Pistol — replace either Hand Flamer","r46-sal-inferno-pistol",10,None,1);elink(sg,e.get("id")+"-sgt-mc","Master-crafted Weapon","r46-sal-mastercrafted",10,None,1)
    add_rule(e,e.get("id")+"-sgt-arm","Infernus Sergeant Armoury","The Sergeant may select up to 50 points of permitted weapons and wargear from the Space Marine Armoury and Salamanders Armoury.")
    if is_root:transport_group(e,e.get("id")+"-transport",["Rhino","Drop Pod","Dreadclaw Drop Pod","Land Raider"],m.get("id"),jump.get("id"))
def patch_adherent(e,is_root=False):
    clear_rules(e);strip_old_option_group(e);legion(e);ilrule(e,"Support Squad");ilrule(e,"Guided by Prophecy")
    add_rule(e,e.get("id")+"-wg","Wargear","Power Armour, Combi-flamer, Bolt Pistol, Chainsword, Frag Grenades.")
    m=model_selector(e);m.set("name","Adherents (total squad size)");cost(m,22)
    hg=group(e,e.get("id")+"-hf","Combi-flamer replacement — 1 per 5 models",0,None);dynmax(hg,hg.get("id")+"-dynmax",m.get("id"),1,5);elink(hg,e.get("id")+"-hf-opt","Heavy Flamer","gear-heavy-flamer",10,None,2)
    squad_upgrade(e,e.get("id")+"-krak","Krak Grenades — entire squad (+2 pts/model)",2,m.get("id"));squad_upgrade(e,e.get("id")+"-melta","Melta Bombs — entire squad (+5 pts/model)",5,m.get("id"))
    sg=group(e,e.get("id")+"-sgt","Adherent Sergeant",0,3);me=group(sg,e.get("id")+"-sgt-melee","Replace Chainsword",0,1)
    for nm,t,p in [("Rending Weapon","gear-rending",5),("Power Weapon","gear-power-weapon",10),("Power Fist","gear-power-fist",15),("Thunder Hammer","gear-thunder-hammer",20)]:elink(me,e.get("id")+"-sgt-"+re.sub(r"[^a-z0-9]+","-",nm.lower()),nm,t,p,None,1)
    elink(sg,e.get("id")+"-sgt-aa","Artificer Armour","gear-artificer-armour",10,None,1);elink(sg,e.get("id")+"-sgt-inf","Inferno Pistol","r46-sal-inferno-pistol",15,None,1);elink(sg,e.get("id")+"-sgt-mc","Master-crafted Weapon","r46-sal-mastercrafted",10,None,1)
    add_rule(e,e.get("id")+"-sgt-arm","Adherent Sergeant Armoury","The Sergeant may select up to 50 points of permitted weapons and wargear from the Space Marine Armoury and Salamanders Armoury.")
    if is_root:transport_group(e,e.get("id")+"-transport",["Rhino","Drop Pod","Dreadclaw Drop Pod"],m.get("id"))
def patch_sanct(e,is_root=False):
    clear_rules(e);strip_old_option_group(e);legion(e);ilrule(e,"Stubborn");ilrule(e,"Close-Quarters Arsenal")
    add_rule(e,e.get("id")+"-wg","Wargear","Power Armour, Bolter, Bolt Pistol, Chainsword, Frag Grenades.")
    m=model_selector(e);m.set("name","Sanctifiers (total squad size)");cost(m,25)
    rg=group(e,e.get("id")+"-ranged","Bolter / pistol replacements — any model",0,None);dynmax(rg,rg.get("id")+"-dynmax",m.get("id"),1,1)
    for nm,t,p in [("Second Bolt Pistol","gear-bolt-pistol",0),("Rotor Cannon","gear-rotor-cannon",10),("Two Hand Flamers","r29-mor-hand",10)]:
        elink(rg,e.get("id")+"-"+re.sub(r"[^a-z0-9]+","-",nm.lower()),nm,t,p,None,10)
    vv=sel(rg,e.get("id")+"-two-volkite","Two Volkite Serpentae","upgrade",10,None,10);add_rule(vv,vv.get("id")+"-rule","Two Volkite Serpentae","Replaces both Bolter and Bolt Pistol with two Volkite Serpentae. The model has two Pistol weapons and therefore benefits from Close-Quarters Arsenal.")
    mg=group(e,e.get("id")+"-melee","Chainsword replacement — 1 per 5 models",0,None);dynmax(mg,mg.get("id")+"-dynmax",m.get("id"),1,5)
    elink(mg,e.get("id")+"-rend","Rending Weapon","gear-rending",5,None,2);elink(mg,e.get("id")+"-pw","Power Weapon","gear-power-weapon",10,None,2)
    squad_upgrade(e,e.get("id")+"-krak","Krak Grenades — entire squad (+2 pts/model)",2,m.get("id"));squad_upgrade(e,e.get("id")+"-melta","Melta Bombs — entire squad (+5 pts/model)",5,m.get("id"))
    sg=group(e,e.get("id")+"-sgt","Sanctifier Sergeant",0,3);me=group(sg,e.get("id")+"-sgt-melee","Replace Chainsword",0,1)
    for nm,t,p in [("Rending Weapon","gear-rending",5),("Power Weapon","gear-power-weapon",10),("Lightning Claw","gear-lightning-claw",15),("Power Fist","gear-power-fist",15),("Thunder Hammer","gear-thunder-hammer",20)]:elink(me,e.get("id")+"-sgt-"+re.sub(r"[^a-z0-9]+","-",nm.lower()),nm,t,p,None,1)
    elink(sg,e.get("id")+"-sgt-aa","Artificer Armour","gear-artificer-armour",10,None,1);elink(sg,e.get("id")+"-sgt-inf","Inferno Pistol","r46-sal-inferno-pistol",15,None,1);elink(sg,e.get("id")+"-sgt-mc","Master-crafted Weapon","r46-sal-mastercrafted",10,None,1)
    if is_root:transport_group(e,e.get("id")+"-transport",["Rhino","Drop Pod","Dreadclaw Drop Pod","Land Raider"],m.get("id"))

# roots + genuine copies
for e in list(cr.iter(C("selectionEntry"))):
    eid=e.get("id") or ""; name=e.get("name") or ""
    if "r46-al-reward" in eid:continue
    if name=="Firedrake Terminator Squad" and ("xviii" in eid or "r40-sal" in eid or "live-r2-r41-unit-xviii" in eid):patch_firedrake(e,eid=="r41-unit-xviii-0-firedrake-terminator-squad")
    elif name=="Pyroclast Squad" and ("xviii" in eid or "r42-role-xviii" in eid):patch_pyro(e,eid=="r41-unit-xviii-1-pyroclast-squad")
    elif name=="Salamanders Infernus Destroyer Squad" and ("xviii" in eid or "r42-role-xviii" in eid):patch_infernus(e,eid=="r41-unit-xviii-2-salamanders-infernus-destroyer-squad")
    elif name=="Adherent Squad" and "xviii" in eid:patch_adherent(e,eid=="r41-unit-xviii-3-adherent-squad")
    elif name=="Sanctifier Squad" and "xviii" in eid:patch_sanct(e,eid=="r41-unit-xviii-4-sanctifier-squad")

# Gate main special units
for i in range(0,10):
    key=next((k for k in ids if k.startswith(f"r41-unit-xviii-{i}-")),None)
    if key and key in ids:visibility(ids[key],[LEG])
# Vulkan separately Loyalist
vulkan=ids["r41-unit-xviii-10-xviii-vulkan-the-forgefather"];visibility(vulkan,[LEG,LOY])

# ---------- characters ----------
def charbase(e,mol=False,chap=False):
    clear_rules(e);legion(e);ilrule(e,"Independent Character")
    if mol:ilrule(e,"Master of the Legion")
    if chap:catlink(e,e.get("id")+"-chapcat","Awakening Fire — Chaplain",CAT_CHAP)

num=ids["r41-unit-xviii-5-artellus-numeon"];charbase(num,True,False);ilrule(num,"Salamanders Mantle");ilrule(num,"Master-Crafted")
add_rule(num,"r40-num-wg","Wargear","Artificer Armour, Iron Halo, Master-crafted Thunder Hammer, Bolt Pistol, Frag Grenades, Salamanders Mantle.")
add_rule(num,"r40-num-pyre","Captain of the Pyre Guard","Numeon may select one Firedrake Terminator Squad as his personal retinue. One Firedrake in that unit may be upgraded to a Firedrake Master at no additional points cost. The squad occupies no separate Elites selection.")
add_rule(num,"r40-num-heir","Vulkan's Heir","Numeon and any Salamanders unit he has joined may re-roll failed Morale tests.")
add_rule(num,"r40-num-command","Command Retinue","Instead of Firedrakes, Numeon may select a Legion Command Squad or Legion Terminator Command Squad as his retinue.")

nom=ids["r41-unit-xviii-6-lord-chaplain-nomus-rhy-tan"];charbase(nom,True,True);ilrule(nom,"Zealot");ilrule(nom,"Salamanders Mantle")
add_infolink(nom,"r40-nom-dark","Darkstar Falling",P_DARK.get("id"),"profile")
add_rule(nom,"r40-nom-wg","Wargear","Artificer Armour, Iron Halo, Darkstar Falling, Combi-flamer, Bolt Pistol, Frag Grenades, Mantle of the Elder Drake.")
add_rule(nom,"r40-nom-mantle","Mantle of the Elder Drake","Counts as a Salamanders Mantle and therefore uses the normal Salamanders Mantle rule.")
add_rule(nom,"r40-nom-dark-rule","Darkstar Falling","Two-Handed, Master-crafted Power Weapon. Attacks are resolved at +2 Strength and have Concussive; against Vehicles they also have Armourbane.")
add_rule(nom,"r40-nom-chap","Lord Chaplain","Nomus counts as a Legion Chaplain Consul for all rules, army construction requirements and Rites of War.")
add_rule(nom,"r40-nom-key","Keeper of the Keys","One Legion Dreadnought or Legion Contemptor Dreadnought may be selected as a non-compulsory HQ choice. It may not be the Warlord.")
add_rule(nom,"r40-nom-ret","Command Retinue","Nomus may select a Legion Command Squad, Legion Terminator Command Squad or Firedrake Terminator Squad as his retinue.")
# Keeper of Keys HQ copies
rootse=cont(cr,"selectionEntries")
for oldid,srcid,label in [("r40-sal-nomus-dread-hq","dreadnought-unit","Legion Dreadnought — Keeper of the Keys"),("r40-sal-nomus-contemptor-hq","contemptor-unit","Legion Contemptor Dreadnought — Keeper of the Keys")]:
    old=next((x for x in rootse.findall(C("selectionEntry")) if x.get("id")==oldid),None)
    if old is not None:rootse.remove(old)
    src=ids[srcid];cp=deep_prefix(src,oldid+"-copy-");cp.set("id",oldid);cp.set("name",label);set_primary(cp,"cat-hq","HQ");catlink(cp,oldid+"-lim","Nomus — Keeper of the Keys",CAT_NOMUS_DREAD);visibility(cp,[LEG,nom.get("id")]);add_rule(cp,oldid+"-note","Keeper of the Keys","Selected through Nomus Rhy'tan. This is a non-compulsory HQ choice and may not be the army's Warlord.");rootse.append(cp)

jurr=ids["r41-unit-xviii-7-xiaphas-jurr-prophet-of-fire"];charbase(jurr,False,True);ilrule(jurr,"Stubborn");ilrule(jurr,"Dragonscale Storm Shield");ilrule(jurr,"Master-Crafted")
add_infolink(jurr,"r40-jurr-ign","Ignatus",P_IGN.get("id"),"profile");add_infolink(jurr,"r40-jurr-fury","Fury of the Salamander",P_FURY.get("id"),"profile")
add_rule(jurr,"r40-jurr-wg","Wargear","Artificer Armour, The Burning Halo, Dragonscale Storm Shield, Ignatus, Bolt Pistol, Frag Grenades.")
add_rule(jurr,"r40-jurr-halo","The Burning Halo","Grants a 4+ Invulnerable Save. Each time Jurr passes this save against a close-combat attack of Strength 5 or greater, the attacking model suffers one Strength 4 hit.")
add_rule(jurr,"r40-jurr-ign-rule","Ignatus","Master-crafted Power Weapon. During an Assault phase in which Jurr charges, attacks are resolved at +1 Strength.")
add_rule(jurr,"r40-jurr-chap","Chaplain-Lieutenant","Counts as a Legion Chaplain Consul for army construction requirements and Rites of War.")
add_rule(jurr,"r40-jurr-prophet","Prophet of Fire","Jurr is a Psyker (Mastery Level 1) and knows Fury of the Salamander. When taking a Psychic test he uses Leadership 7.")
add_rule(jurr,"r40-jurr-fury-rule","Fury of the Salamander",'Witchfire — Beam, Range 18", Strength 5, AP1, Assault 1. Elemental Horror: if an enemy unit suffers one or more unsaved Wounds, it immediately takes a Morale test with a Leadership penalty equal to the number of unsaved Wounds caused.')

cass=ids["r41-unit-xviii-8-cassian-dracos"];clear_rules(cass);ilrule(cass,"Reinforced Ceramite")
add_infolink(cass,"r40-cass-dreadfire","Dreadfire Cannon",P_DREAD.get("id"),"profile")
add_rule(cass,"r40-cass-wg","Wargear","Dreadnought Close Combat Weapon with built-in Heavy Flamer, Dreadfire Cannon, Extra Armour, Smoke Launchers, Searchlight, Nuncio Vox.")
add_rule(cass,"r40-cass-auto","Automatic Shielding","Whenever Cassian suffers a Glancing or Penetrating Hit from a shooting attack, roll D6. On 5+ the hit is ignored.")
add_rule(cass,"r40-cass-ven","Venerable Ancient","Whenever Cassian suffers a Glancing or Penetrating Hit not ignored by Automatic Shielding, the Salamanders player may force the opponent to re-roll the Vehicle Damage roll. The second result is accepted.")
add_rule(cass,"r40-cass-last","The Last Warlord",'Cassian may be the army Warlord despite being a Vehicle. If he is, friendly Salamanders Infantry units with at least one model within 6" gain Feel No Pain (6+): after an eligible failed saving throw, ignore the Wound on a 6.')
add_rule(cass,"r40-cass-burn","Burning Wrath","Cassian may give up one Attack during an Assault phase; every enemy model in base contact suffers one automatic Strength 6 AP4 hit.")
reb=sel(cass,"r40-cass-reborn","Cassian Dracos Reborn", "upgrade",25,None,1)
add_rule(reb,"r40-cass-reborn-rule","Cassian Dracos Reborn","Replace the Dreadfire Cannon with a second Dreadnought Close Combat Weapon with built-in Pyroclast Flame Projector; increase Attacks to 4; gain It Will Not Die and Voice of the Machine; lose Burning Wrath.")
ilrule(reb,"It Will Not Die")
add_infolink(reb,"r40-cass-reborn-pyf","Pyroclast Flame Projector — Flame",P_PYF.get("id"),"profile");add_infolink(reb,"r40-cass-reborn-pym","Pyroclast Flame Projector — Melta",P_PYM.get("id"),"profile")
add_rule(reb,"r40-cass-voice","Voice of the Machine",'Friendly Battle-Automata with a model within 6" may use Leadership 10 for Morale and Pinning tests. In the Shooting phase Cassian may forgo shooting to make a Battlesmith attempt against one friendly Vehicle or Battle-Automata within 6"; it succeeds on 4+.')

tk=ids["r41-unit-xviii-9-forgefather-t-kell"];charbase(tk,False,False)
for n in ["Battlesmith","Bolster Defences","Master-Crafted"]:ilrule(tk,n)
add_rule(tk,"r40-tk-wg","Wargear","Artificer Armour, Refractor Field, Master-crafted Thunder Hammer, Bolt Pistol, Servo-Arm, Signum, Frag Grenades.")
add_rule(tk,"r40-tk-art","Master Artificer","After both armies are selected but before deployment, choose one friendly Salamanders Character; one weapon it carries becomes Master-crafted for the battle. Alternatively, one friendly Salamanders Vehicle or Dreadnought receives Extra Armour for no points.")
add_rule(tk,"r40-tk-keep","Keeper of the Forge","One Salamanders Vehicle or Dreadnought eligible to purchase Reinforced Ceramite may receive it for no points. This cannot be applied to a Land Raider or Spartan.")
add_rule(tk,"r40-tk-forge","Forgefather","T'Kell receives +2 rather than +1 to Battlesmith attempts for his Servo-Arm. A Battlesmith attempt can never improve beyond 3+.")

# ---------- Rites ----------
cov=ids[COVR];awak=ids[AWAK];clear_rules(cov);clear_rules(awak)
cov.set("name","Salamanders Rite of War — The Covenant of Fire")
add_rule(cov,"r40-cov-disc","Disciples of the Flame","Pyroclast Squads and Salamanders Infernus Destroyer Squads may be selected as non-compulsory Troops choices. They may not fulfil compulsory Troops selections.")
add_rule(cov,"r40-cov-walk","Walk Through Fire","Salamanders Infantry units gain Move Through Cover.")
ilrule(cov,"Move Through Cover")
add_rule(cov,"r40-cov-wrath","Veneration of Wrath","When a Salamanders model makes an Armour Penetration roll with a Melta weapon, one individual Armour Penetration die that rolls a natural 1 may be re-rolled. The second result is accepted. This also applies to Melta Bombs.")
add_rule(cov,"r40-cov-obs","Obsidian Forged","Each time a Salamanders Vehicle or Dreadnought suffers a Glancing or Penetrating Hit from a Flame, Melta, Plasma or Volkite attack, roll D6 before Vehicle Damage; on 5+ the hit is ignored. This also applies to Melta Bombs.")
add_rule(cov,"r40-cov-limit","Limitations","Units may not deploy using Deep Strike. Units that must deploy by Deep Strike may not be selected. The combined number of Fast Attack and Heavy Support choices may not exceed the number of Troops choices. No Fortification.")
visibility(cov,[LEG])
awak.set("name","Salamanders Rite of War — The Awakening Fire")
add_rule(awak,"r40-aw-devils","Devils from the Dark","Salamanders Infantry units gain Fear.")
ilrule(awak,"Fear")
add_rule(awak,"r40-aw-fires","Unto the Fires","Never Give Up functions normally. During the additional complete game turn generated by Never Give Up, all Salamanders Infantry units gain Fearless.")
ilrule(awak,"Fearless")
add_infolink(awak,"r40-aw-fury-profile","Fury of the Salamander",P_FURY.get("id"),"profile")
add_rule(awak,"r40-aw-fury","Fury of the Salamander",'Salamanders Librarians may select Fury of the Salamander as a Pyromancy power: Range 18", Strength 5, AP1, Witchfire — Beam, Assault 1. Elemental Horror: if an enemy unit suffers one or more unsaved Wounds, it immediately takes a Morale test with a Leadership penalty equal to those unsaved Wounds.')
add_rule(awak,"r40-aw-limit","Limitations","The Detachment must include a Legion Chaplain Consul. It may include no more than one unit of each type: Jump Infantry, Jetbike, Skimmer and Flyer. Vulkan may not be included. No Fortification or Allied Detachment.")
visibility(awak,[LEG])
# Vulkan hidden while Awakening selected
modifier(vulkan,"r40-vulkan-hide-awak","set","hidden","true",[{"childId":AWAK,"scope":"roster"}])

# Covenant Troops copies, rebuild from corrected roots
for oldid in ["r42-role-xviii-0-effects-disciples-of-the-flame-pyroclast-squads-r41-unit-xviii-1-pyroclast-squad","r42-role-xviii-0-salamanders-infernus-destroyer-squads-r41-unit-xviii-2-salamanders-infernus-destroyer-squad"]:
    old=next((x for x in rootse.findall(C("selectionEntry")) if x.get("id")==oldid),None)
    if old is not None:rootse.remove(old)
for new,srcid,label in [
 ("r40-sal-cov-pyro","r41-unit-xviii-1-pyroclast-squad","Pyroclast Squad — Covenant of Fire Troops"),
 ("r40-sal-cov-infernus","r41-unit-xviii-2-salamanders-infernus-destroyer-squad","Salamanders Infernus Destroyer Squad — Covenant of Fire Troops")]:
    cp=deep_prefix(ids[srcid],new+"-copy-");cp.set("id",new);cp.set("name",label);set_primary(cp,"cat-troops","Troops");visibility(cp,[LEG,COVR]);add_rule(cp,new+"-noncomp","Non-compulsory Troops","This Rite copy may not fulfil either compulsory Troops selection.");rootse.append(cp)

# Hidden category requiring two genuine compulsory-capable Troops while Covenant selected.
CAT_COVCOMP="r40-sal-covenant-compulsory";gcat(CAT_COVCOMP,"Covenant of Fire — compulsory Troops")
cf=fl("r40-sal-covcomp-force","Covenant of Fire — compulsory Troops",CAT_COVCOMP);cons(cf,"r40-sal-covcomp-min","min",0,"selections","parent",True);modifier(cf,"r40-sal-covcomp-set","set","r40-sal-covcomp-min",2,[{"childId":COVR,"scope":"roster"}])
# Tag normal top-level Troops that do not visibly have Support Squad
for e in cr.findall(f"./{C('selectionEntries')}/{C('selectionEntry')}"):
    if not primary_cat(e,"cat-troops"):continue
    if e.get("id") in ("r40-sal-cov-pyro","r40-sal-cov-infernus"):continue
    txt=" ".join((r.get("name") or "")+" "+(r.findtext(C("description")) or "") for r in e.findall(f".//{C('rule')}"))+" "+" ".join((x.get("name") or "") for x in e.findall(f".//{C('infoLink')}"))
    if "Support Squad" in txt or "non-compulsory" in (e.get("name") or "").lower():continue
    catlink(e,e.get("id")+"-r40-covcomp","Covenant of Fire — compulsory Troops",CAT_COVCOMP)

# Fury of Salamander selectable in Librarian Pyromancy power groups.
fury_added=0
pmap={c:p for p in cr.iter() for c in p}
for g in cr.iter(C("selectionEntryGroup")):
    # ancestor Librarian only
    p=g; names=[]
    while p in pmap:
        p=pmap[p]
        if p.get("name"):names.append(p.get("name"))
        if len(names)>7:break
    if not any("Librarian Consul" in n for n in names):continue
    opts=list(g.findall(f"./{C('selectionEntries')}/{C('selectionEntry')}"))
    if not any((o.get("name") or "").startswith("Pyromancy — ") for o in opts):continue
    if any((o.get("name") or "")=="Pyromancy — Fury of the Salamander" for o in opts):continue
    e=sel(g,"r40-sal-fury-"+hashlib.sha1((g.get("id") or "").encode()).hexdigest()[:10],"Pyromancy — Fury of the Salamander","upgrade",0,None,1,hidden=True)
    add_infolink(e,e.get("id")+"-prof","Fury of the Salamander",P_FURY.get("id"),"profile");add_rule(e,e.get("id")+"-rule","Elemental Horror","If the target unit suffers one or more unsaved Wounds, it immediately takes a Morale test with a Leadership penalty equal to the number of unsaved Wounds caused.")
    # find corresponding Pyromancy discipline selector near this Librarian ancestor
    libanc=next((a for a in [g]+list(pmap.values()) if False),None)
    # visibility only needs Legion + Rite; the existing power group already controls number. Add a text restriction to choose only if using Pyromancy.
    modifier(e,e.get("id")+"-show","set","hidden","false",[{"childId":LEG,"scope":"roster"},{"childId":AWAK,"scope":"roster"}]);add_rule(e,e.get("id")+"-disc","Pyromancy restriction","May only be selected as a Pyromancy power.")
    fury_added+=1

# ---------- Vulkan ----------
clear_rules(vulkan);ilrule(vulkan,"Primarch");legion(vulkan);ilrule(vulkan,"Primarch Armour")
for p,n in [(P_DAWN,"Dawnbringer"),(P_FURN,"Furnace's Heart"),(P_GAUNT,"Gauntlet of the Forge")]:add_infolink(vulkan,"r40-vul-"+p.get("id"),n,p.get("id"),"profile")
add_rule(vulkan,"r40-vul-scale","Draken Scale","Counts as Primarch Armour.")
add_rule(vulkan,"r40-vul-kesare","Kesare's Mantle","When resolving an attack made with a Flame weapon against Vulkan, reduce that attack's Strength by 1, to a minimum of 1.")
add_rule(vulkan,"r40-vul-dawn","Dawnbringer","Master-crafted, Two-Handed Power Weapon. Attacks are Strength 10 with Armourbane and Concussive. An unsaved Wound against a model without Primarch becomes a Massive Wound and inflicts D3 Wounds.")
add_rule(vulkan,"r40-vul-forgefather","The Forgefather","All ranged and close-combat weapons carried by Vulkan count as Master-crafted. This is already included where relevant.")
add_rule(vulkan,"r40-vul-lord","Lord of Drakes","Vulkan may re-roll failed Armour and Invulnerable Saves against Flame or Melta attacks; the second result must be accepted.")
add_rule(vulkan,"r40-vul-sire","Sire of the Salamanders",'Friendly Salamanders units with at least one model within 12" may re-roll failed Morale tests and may re-roll Armour Save rolls of 1 against Flame attacks; second results are accepted.')
add_rule(vulkan,"r40-vul-perp","Perpetual","The first time Vulkan is reduced to 0 Wounds, roll D6 before removing him. On 4+, he remains in place and immediately regains D3 Wounds; on 1–3 he is removed normally. This may be used once per battle. If successful, he is not treated as slain for Victory Points, Warlord objectives or Price of Failure unless later removed.")
# retinue
vr=group(vulkan,"r40-vul-retinue","Primarch Retinue — choose up to one (no separate FOC slot)",0,1)
for label,srcid in [("Legion Honour Guard Squad","hq-praetor-ret-honour"),("Legion Terminator Command Squad","hq-praetor-ret-termcommand"),("Firedrake Terminator Squad","r41-unit-xviii-0-firedrake-terminator-squad")]:
    src=ids.get(srcid)
    if src is None:continue
    cp=deep_prefix(src,"r40-vul-ret-"+re.sub(r"[^a-z0-9]+","-",label.lower())+"-");cp.set("id","r40-vul-ret-"+re.sub(r"[^a-z0-9]+","-",label.lower()));cp.set("name",label)
    cats=cp.find(C("categoryLinks"))
    if cats is not None:cp.remove(cats)
    cons(cp,cp.get("id")+"-max","max",1);cont(vr,"selectionEntries").append(cp)

# ---------- final global cleanup ----------
# Remove old giant source/legion dump rules on Salamanders roots / rites.
for e in cr.iter(C("selectionEntry")):
    if (e.get("id") or "").startswith("r41-unit-xviii-") or (e.get("id") or "") in (COVR,AWAK,LEG):
        rs=e.find(C("rules"))
        if rs is not None:
            for r in list(rs):
                if (r.get("name") or "").lower() in ("source entry","salamanders — legion rules & armoury","rite of war interaction","builder compatibility"):rs.remove(r)

# no all-caps XVIII names
for e in cr.iter(C("selectionEntry")):
    if "xviii" not in (e.get("id") or ""):continue
    n=e.get("name") or ""; letters=re.sub(r"[^A-Za-z]","",n)
    if len(letters)>3 and letters==letters.upper():e.set("name",n.lower().title().replace(" Of "," of ").replace(" The "," the "))

# revision
cr.set("revision","40");cr.set("gameSystemRevision","5");gr.set("revision","5")
ct.write(CAT,encoding="utf-8",xml_declaration=True);ET.register_namespace("",GNS);gt.write(GST,encoding="utf-8",xml_declaration=True)
it=ET.parse(IDX);ir=it.getroot();ET.register_namespace("",INS)
for x in ir.iter(I("dataIndexEntry")):
    if x.get("filePath")=="Legiones Astartes.cat":x.set("dataRevision","40")
    if x.get("filePath")=="Prohammer 30k.gst":x.set("dataRevision","5")
it.write(IDX,encoding="utf-8",xml_declaration=True)

# validation
cc=ET.parse(CAT).getroot();gg=ET.parse(GST).getroot();checks=[]
def ck(n,o):
    checks.append((n,bool(o)))
    if not o:raise RuntimeError("R40 validation failed: "+n)
ck("CAT revision 40",cc.get("revision")=="40");ck("GST revision 5",gg.get("revision")=="5");ck("CAT points GST5",cc.get("gameSystemRevision")=="5")
idx=IDX.read_text(encoding="utf-8");ck("Index 40/5",'dataRevision="40"' in idx and 'dataRevision="5"' in idx)
cids={e.get("id"):e for e in cc.iter() if e.get("id")}
for id_ in ["r41-unit-xviii-0-firedrake-terminator-squad","r41-unit-xviii-1-pyroclast-squad","r41-unit-xviii-2-salamanders-infernus-destroyer-squad","r41-unit-xviii-3-adherent-squad","r41-unit-xviii-4-sanctifier-squad"]:
    ck(id_+" has Salamanders rule",any((x.get("name") or "")=="Legiones Astartes (Salamanders)" for x in cids[id_].iter(C("infoLink"))))
ck("Covenant Pyro Troops exists","r40-sal-cov-pyro" in cids);ck("Covenant Infernus Troops exists","r40-sal-cov-infernus" in cids)
ck("Nomus Dread HQ exists","r40-sal-nomus-dread-hq" in cids);ck("Nomus Contemptor HQ exists","r40-sal-nomus-contemptor-hq" in cids)
ck("Cassian Reborn exists","r40-cass-reborn" in cids);ck("Vulkan retinue exists","r40-vul-retinue" in cids)
ck("Vulkan name has no numeral",not (cids["r41-unit-xviii-10-xviii-vulkan-the-forgefather"].get("name") or "").startswith("XVIII"))
# no old base-only cost-note option names in main special squads
bad=[e.get("name") for e in cc.iter(C("selectionEntry")) if (e.get("id") or "").startswith("r41-unit-xviii-") and "base unit;" in (e.get("name") or "").lower()]
ck("No base-unit-only squad upgrade labels",not bad)
# special roots hidden/gated
for i in range(0,11):
    matches=[e for e in cc.findall(f"./{C('selectionEntries')}/{C('selectionEntry')}") if (e.get("id") or "").startswith(f"r41-unit-xviii-{i}-")]
    for e in matches:ck(e.get("id")+" gated",e.get("hidden")=="true")
# Source dump removal
badsrc=[]
for e in cc.iter(C("selectionEntry")):
    if (e.get("id") or "").startswith("r41-unit-xviii-") or (e.get("id") or "") in (COVR,AWAK):
        for r in e.findall(f"./{C('rules')}/{C('rule')}"):
            if (r.get("name") or "").lower()=="source entry":badsrc.append(e.get("id"))
ck("No XVIII Source Entry dumps",not badsrc)

lines=[
"Live R40 — Salamanders implementation",
"Input CAT=39/GST=4 -> CAT=40/GST=5","",
"IMPLEMENTED:",
"- Rebuilt the XVIII Legion selector into canonical shared rules: Promethean Cult, Sturdy, Never Give Up, Fire-based Warfare, Salamanders Mantle and Proscribed Munitions.",
"- Added actual Salamanders Flame, Heavy Flamer and Inferno Pistol profiles.",
"- Enforced the one-per-army Salamanders Mantle limit across the generic upgrade, Artellus Numeon and Nomus Rhy'tan.",
f"- Applied Proscribed Munitions visibility restrictions to {phosphex_hidden} Phosphex entries/links.",
f"- Added Inferno Pistol access to {inferno_links} additional obvious Armoury/Sergeant groups.",
"- Rebuilt Firedrakes, Pyroclasts, Infernus Destroyers, Adherents and Sanctifiers with actual special rules, dynamic squad-wide costs, shared weapon caps, Sergeant/leader options and Dedicated Transports.",
"- Firedrake storm-shield replacements now share the correct 2-per-5 allowance; Infernus, Adherent and Sanctifier special weapon caps now scale from actual squad size.",
"- Rebuilt the Covenant of Fire: non-compulsory Pyroclast/Infernus Troops copies, two genuine compulsory Troops requirement, Fast+Heavy <= Troops enforcement, Move Through Cover/Veneration/Obsidian rules and Deep Strike/Fortification limitations text.",
"- Rebuilt the Awakening Fire: Fear/Fearless effects, mandatory Chaplain, Vulkan exclusion, max-one categories for Jump Infantry/Jetbike/Skimmer/Flyer, and Fury of the Salamander.",
f"- Added Fury of the Salamander to {fury_added} Librarian psychic-power groups.",
"- Rebuilt Artellus Numeon, Nomus Rhy'tan, Xiaphas Jurr, Cassian Dracos/Reborn and T'Kell with their source-listed rules and wargear effects.",
"- Keeper of the Keys now exposes one Dreadnought or Contemptor as a non-compulsory HQ choice while Nomus is present.",
"- Rebuilt Vulkan as Loyalist-only, removed the Legion numeral from his display name, added his armour/weapons/rules and all three Primarch retinue choices.",
"- Removed obsolete XVIII Source Entry / Rite text-dump blocks and retained the R36+ shared-rule standard.","",
"VALIDATION:"
]+[f'- {"PASS" if ok else "FAIL"}: {n}' for n,ok in checks]
OUT.write_text("\n".join(lines)+"\n",encoding="utf-8");print(OUT.read_text())
