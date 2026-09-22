from pathlib import Path
import copy, collections, hashlib, re, xml.etree.ElementTree as ET

CAT=Path("Legiones Astartes.cat"); GST=Path("Prohammer 30k.gst"); IDX=Path("index.xml"); OUT=Path("inspection-live-r45-alpha-legion.txt")
CNS="http://www.battlescribe.net/schema/catalogueSchema"; GNS="http://www.battlescribe.net/schema/gameSystemSchema"; INS="http://www.battlescribe.net/schema/dataIndexSchema"
ET.register_namespace("",CNS)
C=lambda t:f"{{{CNS}}}{t}"; G=lambda t:f"{{{GNS}}}{t}"; I=lambda t:f"{{{INS}}}{t}"
ct=ET.parse(CAT);cr=ct.getroot();gt=ET.parse(GST);gr=gt.getroot()
if cr.get("revision")!="44":raise RuntimeError(f"R45 expected CAT44, got {cr.get('revision')}")
if gr.get("revision")!="9":raise RuntimeError(f"R45 expected GST9, got {gr.get('revision')}")
baseline=collections.Counter(x.get("id") for x in cr.iter() if x.get("id"))
LEG="legion-xx"; TRAITOR="allegiance-traitor"; COILS="r25-rite-xx-0-the-coils-of-the-hydra"; HEAD="r25-rite-xx-1-headhunter-leviathal"

def qns(e):return e.tag.split("}")[0].strip("{")
def cont(p,tag,before=("constraints","categoryLinks","entryLinks","infoLinks","profiles","rules","selectionEntries","selectionEntryGroups","costs","modifiers")):
    ns=qns(p);q=f"{{{ns}}}{tag}";x=p.find(q)
    if x is not None:return x
    x=ET.Element(q);kids=list(p);idx=len(kids)
    for j,k in enumerate(kids):
        if k.tag.split("}")[-1] in before:idx=j;break
    p.insert(idx,x);return x
def getcost(e):
    return next((x for x in e.findall(f"./{C('costs')}/{C('cost')}") if x.get("typeId")=="pts"),None)
def cost(p,val):
    cs=cont(p,"costs",before=("modifiers",));x=getcost(p)
    if x is None:x=ET.SubElement(cs,C("cost"),{"name":"Points","typeId":"pts"})
    x.set("value",str(val));return x
def constraints(p):return p.find(f"./{C('constraints')}")
def cons(p,id_,typ,val,field="selections",scope="parent",child=False):
    ns=qns(p);cs=cont(p,"constraints");q=f"{{{ns}}}constraint";x=next((z for z in cs.findall(q) if z.get("id")==id_),None)
    if x is None:x=ET.SubElement(cs,q)
    x.attrib.update({"id":id_,"type":typ,"value":str(val),"field":field,"scope":scope,"shared":"true","includeChildSelections":"true" if child else "false","includeChildForces":"false"});return x
def clear_constraints(p,typ=None,scope=None):
    cs=p.find(C("constraints"))
    if cs is None:return
    for x in list(cs):
        if (typ is None or x.get("type")==typ) and (scope is None or x.get("scope")==scope):cs.remove(x)
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
def visibility(e,req):
    e.set("hidden","true");ms=e.find(C("modifiers"))
    if ms is not None:
        for m in list(ms):
            if m.get("field")=="hidden":ms.remove(m)
    modifier(e,e.get("id")+"-r45-show","set","hidden","false",[{"childId":x,"scope":"roster"} for x in req])
def catlink(p,id_,name,target,primary=False):
    ns=qns(p);cs=cont(p,"categoryLinks");q=f"{{{ns}}}categoryLink";x=next((z for z in cs.findall(q) if z.get("id")==id_),None)
    if x is None:x=ET.SubElement(cs,q)
    x.attrib.update({"id":id_,"name":name,"targetId":target,"hidden":"false"})
    if primary:x.set("primary","true")
    return x
def set_primary(e,target,name):
    cs=cont(e,"categoryLinks")
    for x in cs.findall(C("categoryLink")):x.set("primary","false")
    x=next((z for z in cs.findall(C("categoryLink")) if z.get("targetId")==target),None)
    if x is None:x=ET.SubElement(cs,C("categoryLink"),{"id":e.get("id")+"-"+target,"name":name,"targetId":target,"hidden":"false"})
    x.set("primary","true")
def strip_primary(e):
    cs=e.find(C("categoryLinks"))
    if cs is not None:
        for x in list(cs):
            if x.get("primary")=="true":cs.remove(x)
def add_rule(p,id_,name,text):
    rs=cont(p,"rules");r=next((z for z in rs.findall(C("rule")) if z.get("id")==id_),None)
    if r is None:r=ET.SubElement(rs,C("rule"))
    r.attrib.update({"id":id_,"name":name,"hidden":"false"});d=r.find(C("description"))
    if d is None:d=ET.SubElement(r,C("description"))
    d.text=text;return r
def clear_rules(p):
    rs=p.find(C("rules"))
    if rs is not None:p.remove(rs)
def clear_infos(p):
    x=p.find(C("infoLinks"))
    if x is not None:p.remove(x)
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
def sel(p,id_,name,typ="upgrade",pts=0,minv=None,maxv=1,hidden=False):
    ss=cont(p,"selectionEntries",before=("selectionEntryGroups","costs","modifiers"));e=next((z for z in ss.findall(C("selectionEntry")) if z.get("id")==id_),None)
    if e is None:e=ET.SubElement(ss,C("selectionEntry"))
    e.attrib.update({"id":id_,"name":name,"type":typ,"hidden":"true" if hidden else "false"})
    cost(e,pts)
    if minv is not None:cons(e,id_+"-min","min",minv)
    if maxv is not None:cons(e,id_+"-max","max",maxv)
    return e
def elink(p,id_,name,target,pts=0,minv=None,maxv=1,hidden=False):
    es=cont(p,"entryLinks",before=("infoLinks","profiles","rules","selectionEntries","selectionEntryGroups","costs","modifiers"));e=next((z for z in es.findall(C("entryLink")) if z.get("id")==id_),None)
    if e is None:e=ET.SubElement(es,C("entryLink"))
    e.attrib.update({"id":id_,"name":name,"targetId":target,"type":"selectionEntry","import":"true","hidden":"true" if hidden else "false"})
    if pts:cost(e,pts)
    if minv is not None:cons(e,id_+"-min","min",minv)
    if maxv is not None:cons(e,id_+"-max","max",maxv)
    return e
def remove_group_by_name(e,name):
    gs=e.find(C("selectionEntryGroups"))
    if gs is None:return
    for g in list(gs):
        if (g.get("name") or "")==name:gs.remove(g)
def remove_group_by_id(e,id_):
    gs=e.find(C("selectionEntryGroups"))
    if gs is None:return
    for g in list(gs):
        if g.get("id")==id_:gs.remove(g)
def clear_group(g):
    for tag in ["entryLinks","selectionEntries","selectionEntryGroups","rules","infoLinks"]:
        x=g.find(C(tag))
        if x is not None:g.remove(x)
    clear_constraints(g)
def deep_prefix(e,prefix):
    x=copy.deepcopy(e);olds=[z.get("id") for z in x.iter() if z.get("id")];mp={o:prefix+o for o in olds}
    for z in x.iter():
        if z.get("id") in mp:z.set("id",mp[z.get("id")])
        for a in ("childId","targetId","field"):
            if z.get(a) in mp:z.set(a,mp[z.get(a)])
    return x
def strip_visibility(e):
    e.set("hidden","false");ms=e.find(C("modifiers"))
    if ms is not None:
        for m in list(ms):
            if m.get("field")=="hidden":ms.remove(m)
def model_selector(e):
    return next((z for z in e.findall(f"./{C('selectionEntries')}/{C('selectionEntry')}") if (z.get("id") or "").endswith("-additional") or "Squad Models"==(z.get("name") or "")),None)
def squad_link(e,id_,name,target,ppm,modelid):
    l=elink(e,id_,name,target,0,None,1);modifier(l,id_+"-cost","increment","pts",ppm,None,[{"childId":modelid,"scope":"root-entry","value":1,"repeats":1}]);return l
def dynmax(g,id_,modelid,divisor=1):
    c=cons(g,id_,"max",0);modifier(g,id_+"-mod","increment",id_,1,None,[{"childId":modelid,"scope":"root-entry","value":divisor,"repeats":1}]);return c
def dynexact(g,prefix,modelid):
    mn=cons(g,prefix+"-min","min",0);mx=cons(g,prefix+"-max","max",0)
    modifier(g,prefix+"-minmod","increment",mn.get("id"),1,None,[{"childId":modelid,"scope":"root-entry","value":1,"repeats":1}])
    modifier(g,prefix+"-maxmod","increment",mx.get("id"),1,None,[{"childId":modelid,"scope":"root-entry","value":1,"repeats":1}])
def find_target(*names):
    for n in names:
        exact=[x for x in cr.iter(C("selectionEntry")) if (x.get("name") or "").casefold()==n.casefold()]
        pref=[x for x in exact if (x.get("id") or "").startswith(("gear-","fa-gear-","hsgear-","r41-universal-gear-"))]
        if pref:return pref[0].get("id")
        if exact:return exact[0].get("id")
    raise RuntimeError("Missing target "+"/".join(names))
def profile(e,id_,name,chars):
    ps=cont(e,"profiles");p=next((x for x in ps.findall(C("profile")) if x.get("id")==id_),None)
    if p is None:p=ET.SubElement(ps,C("profile"))
    p.attrib.update({"id":id_,"name":name,"typeId":"prof-weapon","hidden":"false"});chs=p.find(C("characteristics"))
    if chs is None:chs=ET.SubElement(p,C("characteristics"))
    for z in list(chs):chs.remove(z)
    for nm,val,tid in [("Range",chars[0],"weapon-range"),("S",chars[1],"weapon-s"),("AP",chars[2],"weapon-ap"),("Type",chars[3],"weapon-type")]:
        z=ET.SubElement(chs,C("characteristic"),{"name":nm,"typeId":tid});z.text=str(val)
    return p
def shared_profile(id_,name,chars):
    sp=cr.find(C("sharedProfiles"))
    if sp is None:sp=ET.Element(C("sharedProfiles"));cr.insert(1,sp)
    p=next((x for x in sp.findall(C("profile")) if x.get("id")==id_),None)
    if p is None:p=ET.SubElement(sp,C("profile"))
    p.attrib.update({"id":id_,"name":name,"typeId":"prof-weapon","hidden":"false"});chs=p.find(C("characteristics"))
    if chs is None:chs=ET.SubElement(p,C("characteristics"))
    for z in list(chs):chs.remove(z)
    for nm,val,tid in [("Range",chars[0],"weapon-range"),("S",chars[1],"weapon-s"),("AP",chars[2],"weapon-ap"),("Type",chars[3],"weapon-type")]:
        z=ET.SubElement(chs,C("characteristic"),{"name":nm,"typeId":tid});z.text=str(val)
    return p
def idmap():return {x.get("id"):x for x in cr.iter() if x.get("id")}
ids=idmap()

# shared rules
sr=cr.find(C("sharedRules"))
if sr is None:sr=ET.Element(C("sharedRules"));cr.insert(0,sr)
def find_sr(name):
    return next((x for x in sr.findall(C("rule")) if (x.get("name") or "").casefold()==name.casefold()),None)
def shr(id_,name,text):
    r=next((x for x in sr.findall(C("rule")) if x.get("id")==id_),None)
    if r is None:r=ET.SubElement(sr,C("rule"),{"id":id_,"name":name,"hidden":"false"})
    r.set("name",name);d=r.find(C("description"))
    if d is None:d=ET.SubElement(r,C("description"))
    d.text=text;return r
rules={
"Legiones Astartes (Alpha Legion)":"This model belongs to the XX Legion. It follows the normal Legiones Astartes rules and is affected by rules referring to Legiones Astartes (Alpha Legion). A model may possess only one named Legiones Astartes rule.",
"Mutable Tactics":"An Alpha Legion army must select exactly one Mutable Tactic: Counter-Attack, Furious Charge, Infiltrate, Move Through Cover, Siege Specialists or Tank Hunters. The selected Veteran Skill applies for the battle to all qualifying non-Vehicle units in the Detachment with Legiones Astartes (Alpha Legion). It does not count towards a unit's normal Veteran Skill allowance and all normal restrictions of the selected skill continue to apply.",
"Siege Specialists":"Add +1 to Armour Penetration rolls made against Fortifications, Buildings, Bunkers and other immobile structures with an Armour Value.",
"Martial Hubris":"In a mission using Victory Points, compare completely destroyed units at the end of the battle. If more Alpha Legion units have been completely destroyed than enemy units, the opponent receives an additional D3 × 50 Victory Points. If both players lost the same number of units, this rule has no effect.",
"Infiltration Network":"Legion Operatives may be selected as Troops. Up to two additional Legion Operative units may be selected without occupying a Troops selection; they are still paid for normally and count as units for Martial Hubris.",
"Banestrike":"A natural To Wound roll of 6 made with Banestrike Ammunition is resolved at AP3.",
"Power Dagger":"Counts as a Power Weapon with Rending and Specialist Weapon. Attacks are resolved at -1 Strength.",
"Venom Spheres":"The bearer gains Hammer of Wrath.",
"Pre-emptive Strike":"After both armies have deployed but before the first turn begins, nominate one enemy unit. A non-Vehicle unit suffers D6 Strength 4 hits; Armour Saves are allowed, and if at least one casualty is caused it immediately takes a Pinning test at -1 Leadership. Against a Vehicle, roll D6: 1–3 no effect, 4–5 one Glancing Hit, 6 one Penetrating Hit. No range or line of sight is required.",
"Teleportation Transponders":"The equipped model or unit gains Deep Strike and may deploy by Deep Strike even if the mission would not normally permit it. An Independent Character intending to Deep Strike with another unit must purchase Transponders separately.",
"Operative Cell":"Before deployment, choose exactly one Operative Cell skill set: Scouts (Infiltrate and Move Through Cover), Assassins (Infiltrate and Furious Charge), or Saboteurs (Infiltrate and Siege Specialists).",
"Human Agents":"Legion Operatives do not possess Legiones Astartes and do not benefit from Mutable Tactics or other rules which specifically affect Alpha Legion Space Marines.",
"All as Planned":"After both armies have deployed but before the first turn begins, this Headhunter Kill Team may make one Pre-emptive Strike.",
"Hydra's Wail":"Enemy units with at least one model within 12 inches of an Effrit Disruption Cadre suffer -1 Leadership on Pinning tests. Enemy Nuncio Voxes and Teleport Homers may not be used while their bearer is within 12 inches of an Effrit model.",
"The Harrowing":"Armillus Dynat and any unit he has joined gain Counter-Attack. Models in that unit add +1 to Armour Penetration rolls made against Vehicles in close combat.",
"Weapon Mastery":"Armillus Dynat may divide his close-combat attacks between his Power Weapon and Thunder Hammer in any combination, including bonus Attacks.",
"Lone Killer":"Exodus may never join another unit and no Independent Character may join him. He may not fulfil a compulsory HQ selection and may never be the army's Warlord.",
"Deadshot":"Before battle, nominate one enemy Independent Character or unit-upgrade Character. When Exodus fires at a unit containing that model, successful Wounds caused by Exodus may be allocated to the nominated model first if it is in range and line of sight. All Attacks are made at AP2.",
"Execute the Mandate":"If the enemy Warlord is slain by an attack made by Exodus, the Alpha Legion player receives an additional 50 Victory Points.",
"Delegatus":"Autilon Skorr counts as a Legion Delegatus Consul for all rules and restrictions.",
"Desperate for Glory":"Once per battle, at the beginning of an Alpha Legion turn, Autilon Skorr may invoke this rule. Until the beginning of the next Alpha Legion turn, Skorr and any unit he has joined gain Fearless and Feel No Pain (5+).",
"Master of Deceit":"An army containing Ingo Pech may use The Rewards of Treachery rule from The Coils of the Hydra even if it is not using that Rite. If the army is already using The Coils, Pech does not permit a second Rewards unit.",
"False Disposition":"After both armies have deployed but before determining the first player, nominate Mathias Herzog and one other friendly non-Vehicle Alpha Legion unit. Both may immediately redeploy wholly within the Alpha Legion deployment zone. Units in Reserve or using Infiltrate are not eligible.",
"Headhunter Commander":"One Headhunter Kill Team may be selected without occupying an Elites choice in an army containing Mathias Herzog. It remains an Elites unit for all other purposes.",
"Hydra's Resilience":"While Sheed Ranko remains alive, his Lernaean Terminator Squad has Stubborn.",
"Master of Lies":"After both armies have deployed but before the first turn begins, nominate one friendly Alpha Legion unit. It may redeploy anywhere it could legally have deployed at the beginning of battle, obeying normal deployment restrictions. It may not be placed into Reserve unless already eligible to begin in Reserve.",
"The Hydra":"Before either army deploys, secretly record one enemy unit as the Priority Target. Reveal it the first time an Alpha Legion unit attacks it. Once revealed, friendly units with Legiones Astartes (Alpha Legion) re-roll To Hit rolls of 1 against that target in shooting and close combat.",
"Sire of the Alpha Legion":"Friendly units with Legiones Astartes (Alpha Legion) with at least one model within 12 inches of Alpharius may use his Leadership for Morale and Pinning tests.",
"I Am Alpharius":"Alpharius is not deployed normally and does not begin in Reserve. At the beginning of any Alpha Legion turn, replace one friendly Infantry model on the battlefield with Legiones Astartes (Alpha Legion) with Alpharius, as close as possible to its previous position. The replaced model is a casualty. Alpharius enters at full Wounds, joins the unit if applicable, remains in the same close combat if applicable, and may Move, Shoot and charge normally that turn. No Reserve roll is required. If unrevealed when the battle ends, he counts as slain for relevant Victory Point purposes."
}
R={n:shr("r45-al-"+re.sub(r"[^a-z0-9]+","-",n.lower()).strip("-")[:70],n,t) for n,t in rules.items()}
def generic(name):
    x=find_sr(name)
    if x is None:
        fallback={"Counter-Attack":"When charged, a unit that passes the normal Counter-Attack test receives the normal charge bonus as described by ProHammer.","Furious Charge":"Models gain +1 Strength and +1 Initiative in assault on the turn they charged.","Infiltrate":"May deploy using the normal Infiltrate rules.","Move Through Cover":"Roll 3D6 for Difficult Terrain tests and use the highest result.","Tank Hunters":"Re-roll failed Armour Penetration rolls against Vehicles.","Stubborn":"Ignore negative Leadership modifiers on Morale and Pinning tests.","Independent Character":"Uses the normal ProHammer Independent Character rules.","Master of the Legion":"Permits use of a Rite of War and follows the normal Master of the Legion restrictions.","Primarch":"Uses the normal Primarch rules.","Deep Strike":"Uses the normal ProHammer Deep Strike rules.","Hammer of Wrath":"Uses the normal ProHammer Hammer of Wrath rule.","Rending":"Uses the normal ProHammer Rending rule.","Specialist Weapon":"A model only receives the +1 Attack bonus for two weapons if both weapons have Specialist Weapon."}
        x=shr("r45-al-generic-"+re.sub(r"[^a-z0-9]+","-",name.lower()).strip("-"),name,fallback.get(name,"Use the normal ProHammer rule."))
    return x
def ilr(e,name,suffix=None,hidden=False):
    rr=R.get(name) or generic(name);return add_infolink(e,e.get("id")+"-"+(suffix or re.sub(r"[^a-z0-9]+","-",name.lower()).strip("-")),name,rr.get("id"),"rule",hidden)
def legion(e,mutable=True):
    ilr(e,"Legiones Astartes (Alpha Legion)","al-leg")
    ilr(e,"Martial Hubris","al-hubris")
    if mutable:mutable_links(e)

# profiles
P_BANE=shared_profile("r45-al-prof-banestrike","Banestrike Bolter",('18"',"4","4","Rapid Fire, Banestrike"))
P_DAG=shared_profile("r45-al-prof-power-dagger","Power Dagger",("—","User -1","Power Weapon","Melee, Rending, Specialist Weapon"))
P_RIME=shared_profile("r45-al-prof-rime-shard","Rime-shard",("—","User +2","Power Weapon","Melee, Two-Handed, Master-crafted"))
P_PALE=shared_profile("r45-al-prof-pale-spear","Pale Spear",("—","User","Power Weapon","Melee, Two-Handed, Armourbane, Massive Wound (D3) vs non-Primarchs"))
P_SPITE=shared_profile("r45-al-prof-hydras-spite","Hydra's Spite",('18"',"7","2","Assault 2, Gets Hot"))

# Mutable selector rebuilt on Legion selection
leg=ids[LEG]
for tag in ["rules","infoLinks"]:
    x=leg.find(C(tag))
    if x is not None:leg.remove(x)
ilr(leg,"Legiones Astartes (Alpha Legion)","named");ilr(leg,"Mutable Tactics","mutable-rule");ilr(leg,"Martial Hubris","hubris");ilr(leg,"Infiltration Network","network")
mg=next((g for g in leg.findall(f"./{C('selectionEntryGroups')}/{C('selectionEntryGroup')}") if g.get("id")=="r46-al-mutable-tactics"),None)
if mg is None:mg=group(leg,"r46-al-mutable-tactics","Mutable Tactics",1,1)
clear_group(mg);mg.set("name","Mutable Tactics — choose exactly one");cons(mg,"r46-al-mutable-min","min",1);cons(mg,"r46-al-mutable-max","max",1)
TACTICS=[("r46-al-mutable-0","Counter-Attack"),("r46-al-mutable-1","Furious Charge"),("r46-al-mutable-2","Infiltrate"),("r46-al-mutable-3","Move Through Cover"),("r46-al-mutable-4","Siege Specialists"),("r46-al-mutable-5","Tank Hunters")]
tactic_ids={}
for tid,n in TACTICS:
    x=sel(mg,tid,n,"upgrade",0,None,1);tactic_ids[n]=tid;ilr(x,n,"effect")
def mutable_links(e):
    for tid,n in TACTICS:
        il=ilr(e,"Siege Specialists" if n=="Siege Specialists" else n,"mutable-"+tid,True)
        modifier(il,il.get("id")+"-show","set","hidden","false",[{"childId":tid,"scope":"roster"}])

# Canonical armoury entries
ids=idmap()
for eid,n in [("r46-al-banestrike-character","Banestrike Ammunition"),("r46-al-banestrike-model","Banestrike Ammunition — eligible model"),("r46-al-power-dagger","Power Dagger"),("r46-al-venom-spheres","Venom Spheres"),("r46-al-trans-character","Teleportation Transponders"),("r46-al-trans-unit","Teleportation Transponders")]:
    if eid not in ids:continue
    e=ids[eid];clear_rules(e);clear_infos(e);clear_constraints(e,"max")
    if "banestrike" in eid:
        add_rule(e,eid+"-rule","Banestrike Ammunition",'Use the Banestrike profile. With a Foeblaster Boltgun, Combi-Bolter or Bolter component of a Combi-Weapon, retain the normal number of shots and firing type, but reduce range to 18 inches, use AP4 and apply Banestrike. It may not be combined with another ammunition type.')
        add_infolink(e,eid+"-bane-rule","Banestrike",R["Banestrike"].get("id"),"rule");add_infolink(e,eid+"-profile","Banestrike Bolter",P_BANE.get("id"),"profile")
    elif eid=="r46-al-power-dagger":
        ilr(e,"Power Dagger","rule");add_infolink(e,eid+"-profile","Power Dagger",P_DAG.get("id"),"profile")
    elif eid=="r46-al-venom-spheres":
        ilr(e,"Venom Spheres","rule");ilr(e,"Hammer of Wrath","how")
    else:ilr(e,"Teleportation Transponders","rule");ilr(e,"Deep Strike","deep")

# Add missing Alpha armoury links to generic HQ and Sergeant armouries.
def parent_map():return {c:p for p in cr.iter() for c in p}
pm=parent_map()
def ancestors(e,lim=12):
    out=[];p=e
    while p is not None and len(out)<lim:out.append(p);p=pm.get(p)
    return out
serg_links=0
for g in cr.iter(C("selectionEntryGroup")):
    nm=(g.get("name") or "").lower()
    chain=" ".join((x.get("name") or "").lower() for x in ancestors(g))
    if "armoury" not in nm:continue
    is_ic=any((x.get("id") or "") in ("hq-praetor","hq-centurion") for x in ancestors(g))
    is_serg=any(k in chain for k in ["sergeant","prime","principal","alpha","chieftain","strike leader","huscarl","hunt-master"])
    if not (is_ic or is_serg):continue
    for tid,nm2 in [("r46-al-power-dagger","Power Dagger"),("r46-al-venom-spheres","Venom Spheres")]:
        if any(x.get("targetId")==tid for x in g.findall(f"./{C('entryLinks')}/{C('entryLink')}")):continue
        lid="r45-al-arm-"+hashlib.sha1(((g.get("id") or "")+tid).encode()).hexdigest()[:12]
        l=elink(g,lid,nm2,tid,0,None,1,True);modifier(l,lid+"-show","set","hidden","false",[{"childId":LEG}]);serg_links+=1

# Generic IC transponders only with terminator armour.
for hid in ["hq-praetor","hq-centurion"]:
    h=ids[hid]
    groups=[g for g in h.iter(C("selectionEntryGroup")) if "wargear" in (g.get("name") or "").lower() or "armoury" in (g.get("name") or "").lower()]
    if groups:
        g=groups[-1]
        if not any(l.get("targetId")=="r46-al-trans-character" for l in h.iter(C("entryLink"))):
            l=elink(g,"r45-"+hid+"-al-trans","Teleportation Transponders","r46-al-trans-character",0,None,1,True)
            # show only when AL + a terminator armour selection is present
            for tid in [hid+"-term",hid+"-tart",hid+"-cat"]:
                modifier(l,l.get("id")+"-"+tid,"set","hidden","false",[{"childId":LEG},{"childId":tid,"scope":"root-entry"}])

# Whole-squad Banestrike for Veteran and Seeker, replacing old per-model AL links.
def remove_target_links(root,target):
    removed=0
    for p in root.iter():
        es=p.find(C("entryLinks"))
        if es is not None:
            for l in list(es):
                if l.get("targetId")==target:es.remove(l);removed+=1
    return removed
def add_banestrike_squad(root,modelid,sgtid,prefix):
    remove_target_links(root,"r46-al-banestrike-model")
    g=group(root,prefix+"-group","Alpha Legion — Banestrike Ammunition",0,1,True)
    modifier(g,prefix+"-show","set","hidden","false",[{"childId":LEG}])
    x=sel(g,prefix,"Banestrike Ammunition — all eligible models","upgrade",5,None,1)
    modifier(x,prefix+"-models","increment","pts",5,None,[{"childId":modelid,"scope":"root-entry","value":1,"repeats":1,"includeChildSelections":False}])
    # non-eligible ranged replacements reduce price by 5 for each model using them
    eligible_targets={"gear-bolter","gear-foeblaster","gear-combi-bolter","gear-combi-flamer","gear-combi-melta","gear-combi-plasma","gear-combi-volkite","gear-combi-grenade"}
    for l in root.iter(C("entryLink")):
        n=(l.get("name") or "").lower()
        if "replace" not in n and "replacement" not in n:continue
        if l.get("targetId") in eligible_targets or "combi-" in n or "foeblaster" in n:continue
        if any(k in n for k in ["bolter replacement","bolt pistol","chainsword","power weapon","armour","wargear"]):continue
        modifier(x,prefix+"-sub-"+hashlib.sha1((l.get("id") or n).encode()).hexdigest()[:10],"increment","pts",-5,None,[{"childId":l.get("id"),"scope":"root-entry","value":1,"repeats":1}])
    add_infolink(x,prefix+"-profile","Banestrike Bolter",P_BANE.get("id"),"profile");add_infolink(x,prefix+"-rule","Banestrike",R["Banestrike"].get("id"),"rule")
    return x
add_banestrike_squad(ids["veteran-unit"],"veteran-included","veteran-sergeant","r45-al-vet-bane")
add_banestrike_squad(ids["fa-seeker"],"fa-seeker-included","fa-seeker-sgt","r45-al-seeker-bane")

# Terminator Squad transponders.
term=ids.get("terminator-unit")
if term is not None:
    g=next((x for x in term.iter(C("selectionEntryGroup")) if "squad equipment" in (x.get("name") or "").lower()),None) or group(term,"r45-al-term-gear","Alpha Legion Wargear")
    if not any(x.get("targetId")=="r46-al-trans-unit" for x in term.iter(C("entryLink"))):
        l=elink(g,"r45-al-term-trans","Teleportation Transponders","r46-al-trans-unit",0,None,1,True);modifier(l,l.get("id")+"-show","set","hidden","false",[{"childId":LEG}])

# Helpers for Alpha native units.
def clear_native(e):
    clear_rules(e);clear_infos(e);remove_group_by_name(e,"Options")
def model(e,name,pts,minv,maxv):
    m=model_selector(e)
    if m is None:m=sel(e,e.get("id")+"-additional",name,"model",pts,minv,maxv)
    m.set("name",name);cost(m,pts);clear_constraints(m);cons(m,m.get("id")+"-min","min",minv);cons(m,m.get("id")+"-max","max",maxv);return m
def armoury_clone(parent,id_,name,limit=50,strip_targets=()):
    # Prefer Seeker Sergeant additional armoury.
    src=None
    seek=ids["fa-seeker"]
    for g in seek.iter(C("selectionEntryGroup")):
        nm=(g.get("name") or "").lower()
        if "armoury" in nm and "sergeant" in nm:
            src=g;break
    if src is None:return None
    cp=deep_prefix(src,id_+"-clone-");cp.set("id",id_);cp.set("name",name);clear_constraints(cp);cons(cp,id_+"-pts","max",limit,"pts","parent",True)
    for p in cp.iter():
        es=p.find(C("entryLinks"))
        if es is not None:
            for l in list(es):
                if l.get("targetId") in strip_targets:es.remove(l)
    cont(parent,"selectionEntryGroups",before=("costs","modifiers")).append(cp);return cp
def transport_group(e,id_,modelid):
    g=group(e,id_,"Dedicated Transport",0,1)
    # Land Raider patterns
    lr=group(g,id_+"-lr","Land Raider",0,1)
    for nm,tid in [("Land Raider Phobos","hs-lr-phobos"),("Land Raider Proteus","hs-lr-proteus"),("Land Raider Achilles","hs-lr-achilles")]:
        if tid not in ids:continue
        l=elink(lr,id_+"-"+tid,nm,tid,0,None,1)
        modifier(l,l.get("id")+"-cap","set","hidden","true",[{"childId":modelid,"scope":"root-entry","type":"atLeast","value":6,"includeChildSelections":False}])
    if "transport-dreadclaw" in ids:
        l=elink(g,id_+"-dc","Dreadclaw Drop Pod","transport-dreadclaw",0,None,1);modifier(l,l.get("id")+"-cap","set","hidden","true",[{"childId":modelid,"scope":"root-entry","type":"atLeast","value":6,"includeChildSelections":False}])
    if "hs-spartan" in ids:elink(g,id_+"-spartan","Spartan Assault Tank","hs-spartan",0,None,1)
    return g

# Hidden categories and force links
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
CAT_HEAD="r45-al-headhunter-limit";CAT_LERN="r45-al-lernaean-limit";CAT_REWARD="cat-alpha-reward";CAT_COILS_CONS="r45-al-coils-consul";CAT_COILS_TROOPS="r45-al-coils-compulsory";CAT_HEAD_COMP="r45-al-headhunter-compulsory"
for cid,n in [(CAT_HEAD,"Alpha Legion — Headhunter limit"),(CAT_LERN,"Alpha Legion — Lernaean limit"),(CAT_COILS_CONS,"Coils — non-Vigilator Consuls"),(CAT_COILS_TROOPS,"Coils — compulsory-capable Troops"),(CAT_HEAD_COMP,"Headhunter Leviathal — compulsory Headhunters")]:gcat(cid,n)
# existing Rewards category may already exist; ensure.
gcat(CAT_REWARD,"Rewards of Treachery Limit")
x=fl("r45-al-head-limit-force","Alpha Legion — Headhunter limit",CAT_HEAD);mx=cons(x,"r45-al-head-limit-max","max",1,"selections","parent",True);modifier(x,"r45-al-head-limit-rite","set",mx.get("id"),99,[{"childId":HEAD,"scope":"roster"}])
x=fl("r45-al-lern-limit-force","Alpha Legion — Lernaean limit",CAT_LERN);cons(x,"r45-al-lern-limit-max","max",1,"selections","parent",True)
x=fl("r45-al-reward-force","Rewards of Treachery Limit",CAT_REWARD);cons(x,"r45-al-reward-max","max",1,"selections","parent",True)
x=fl("r45-al-coils-cons-force","Coils — non-Vigilator Consuls",CAT_COILS_CONS);cm=cons(x,"r45-al-coils-cons-max","max",99,"selections","parent",True);modifier(x,"r45-al-coils-cons-one","set",cm.get("id"),1,[{"childId":COILS,"scope":"roster"}])
x=fl("r45-al-coils-troops-force","Coils — compulsory-capable Troops",CAT_COILS_TROOPS);tm=cons(x,"r45-al-coils-troops-min","min",0,"selections","parent",True);modifier(x,"r45-al-coils-troops-three","set",tm.get("id"),3,[{"childId":COILS,"scope":"roster"}])
x=fl("r45-al-head-comp-force","Headhunter Leviathal — compulsory Headhunters",CAT_HEAD_COMP);hm=cons(x,"r45-al-head-comp-min","min",0,"selections","parent",True);modifier(x,"r45-al-head-comp-two","set",hm.get("id"),2,[{"childId":HEAD,"scope":"roster"}])

# Coils compulsory Troop candidates (excluding Support/noncompulsory).
def direct_text(e):
    return " ".join((x.get("name") or "")+" "+(x.findtext(C("description")) or "") for x in e.findall(f"./{C('rules')}/{C('rule')}")).lower()+" "+" ".join((x.get("name") or "").lower() for x in e.findall(f"./{C('infoLinks')}/{C('infoLink')}"))
for e in cr.findall(f"./{C('selectionEntries')}/{C('selectionEntry')}"):
    if not any(c.get("targetId")=="cat-troops" and c.get("primary")=="true" for c in e.findall(f"./{C('categoryLinks')}/{C('categoryLink')}")):continue
    txt=direct_text(e)
    if "support squad" in txt or "may not fulfil" in txt or "may not fulfill" in txt or "non-compulsory" in txt:continue
    catlink(e,e.get("id")+"-r45-coils-comp","Coils — compulsory-capable Troops",CAT_COILS_TROOPS)

# Consul tags except Vigilator.
cent=ids["hq-centurion"]
cg=next(g for g in cent.iter(C("selectionEntryGroup")) if g.get("id")=="hq-centurion-consuls")
for c in cg.findall(C("selectionEntry")):
    if "vigilator" not in (c.get("name") or "").lower():catlink(c,c.get("id")+"-r45-coils-cons","Coils — non-Vigilator Consuls",CAT_COILS_CONS)

# ---- Legion Operatives ----
op=ids["r41-unit-xx-0-legion-operatives"];clear_native(op)
om=model(op,"Operatives (total squad size)",6,10,20)
add_rule(op,"r45-op-wg","Wargear","Close-combat weapon and either a Laspistol or Autopistol.")
ilr(op,"Operative Cell");ilr(op,"Human Agents")
cells=group(op,"r45-op-cell","Operative Cell — choose one",1,1)
for i,(nm,rs) in enumerate([("Scouts",["Infiltrate","Move Through Cover"]),("Assassins",["Infiltrate","Furious Charge"]),("Saboteurs",["Infiltrate","Siege Specialists"])]):
    x=sel(cells,f"r45-op-cell-{i}",nm,"upgrade",0,None,1)
    for rn in rs:ilr(x,rn,"rule-"+re.sub(r"[^a-z]+","-",rn.lower()))
for nm,tid,ppm in [("Frag Grenades — entire squad","gear-frag",1),("Krak Grenades — entire squad","gear-krak",1),("Melta Bombs — entire squad","gear-melta-bombs",2)]:
    if tid in ids:squad_link(op,"r45-op-"+re.sub(r"[^a-z]+","-",nm.lower())[:30],nm,tid,ppm,om.get("id"))
lead=sel(op,"r45-op-leader","Upgrade one Operative to Operative Leader","upgrade",5,None,1)
add_rule(lead,"r45-op-leader-prof-note","Operative Leader","Use the Operative Leader profile shown for this unit.")
armoury_clone(lead,"r45-op-leader-arm","Operative Leader — Armoury weapons (max 10 pts)",10,("gear-hq-artificer","gear-artificer","r46-al-venom-spheres"))
visibility(op,[LEG])

# slotless 0-2 Operatives rebuilt from clean base
aux=ids.get("r46-al-operative-aux")
if aux is not None:
    parent=next(p for p in cr.iter() for c in list(p) if c is aux)
    idx=list(parent).index(aux);parent.remove(aux)
    aux=deep_prefix(op,"r45-opaux-copy-");aux.set("id","r46-al-operative-aux");aux.set("name","Legion Operatives (slotless 0–2)");strip_primary(aux);clear_constraints(aux,"max","roster");cons(aux,"r46-al-operative-aux-roster","max",2,"selections","roster")
    strip_visibility(aux);visibility(aux,[LEG]);parent.insert(idx,aux)
else:
    aux=deep_prefix(op,"r45-opaux-copy-");aux.set("id","r46-al-operative-aux");aux.set("name","Legion Operatives (slotless 0–2)");strip_primary(aux);cons(aux,"r46-al-operative-aux-roster","max",2,"selections","roster");strip_visibility(aux);visibility(aux,[LEG]);cont(cr,"selectionEntries").append(aux)

ids=idmap()

# ---- Headhunter Kill Team ----
hh=ids["r41-unit-xx-1-headhunter-kill-team"];clear_native(hh)
hm=model(hh,"Headhunters (total squad size)",32,5,10)
add_rule(hh,"r45-hh-wg","Wargear","Power Armour, Bolter, Banestrike Ammunition, Kraken Bolts, close-combat weapon, Frag Grenades and Melta Bombs.")
legion(hh);ilr(hh,"Infiltrate");ilr(hh,"Move Through Cover");ilr(hh,"All as Planned");ilr(hh,"Pre-emptive Strike")
add_infolink(hh,"r45-hh-bane-prof","Banestrike Bolter",P_BANE.get("id"),"profile");add_infolink(hh,"r45-hh-bane-rule","Banestrike",R["Banestrike"].get("id"),"rule")
spg=group(hh,"r45-hh-special","Special Weapons — up to two models",0,2)
for nm,tid,pts in [("Heavy Flamer",find_target("Heavy Flamer"),10),("Meltagun",find_target("Meltagun"),10),("Plasma Gun",find_target("Plasma Gun"),15),("Multi-Melta",find_target("Multi-Melta"),25),("Heavy Bolter with Suspensor and Hellfire Rounds",find_target("Heavy Bolter with Suspensor and Hellfire Rounds"),15)]:
    elink(spg,"r45-hh-"+re.sub(r"[^a-z0-9]+","-",nm.lower()).strip("-"),nm+" — replaces Bolter",tid,pts,None,2)
pd=elink(hh,"r45-hh-dagger","Power Dagger — any model","r46-al-power-dagger",0,None,10);mx=cons(pd,"r45-hh-dagger-dyn","max",0);modifier(pd,"r45-hh-dagger-dynmod","increment",mx.get("id"),1,None,[{"childId":hm.get("id"),"scope":"root-entry","value":1,"repeats":1}])
prime=group(hh,"r45-hh-prime","Headhunter Prime",0,1);elink(prime,"r45-hh-prime-art","Artificer Armour",find_target("Artificer Armour"),10,None,1);elink(prime,"r45-hh-prime-venom","Venom Spheres","r46-al-venom-spheres",0,None,1)
armoury_clone(hh,"r45-hh-prime-arm","Headhunter Prime — Armoury (max 50 pts)",50,("gear-hq-artificer","gear-artificer","r46-al-venom-spheres"))
catlink(hh,"r45-hh-limit","Alpha Legion — Headhunter limit",CAT_HEAD)
visibility(hh,[LEG])

# ---- Lernaean Terminators ----
le=ids["r41-unit-xx-2-lernaean-terminator-squad"];clear_native(le)
lm=model(le,"Lernaean Terminators (total squad size)",48,5,10)
add_rule(le,"r45-lern-wg","Wargear","Cataphractii Terminator Armour. Each model must select one ranged weapon and one melee weapon from the groups below.")
legion(le)
rg=group(le,"r45-lern-ranged","Ranged Weapon — one per model");dynexact(rg,"r45-lern-ranged",lm.get("id"))
for nm,tid,pts in [("Storm Bolter",find_target("Storm Bolter"),0),("Foeblaster Boltgun",find_target("Foeblaster Boltgun"),0),("Combi-Flamer",find_target("Combi-Flamer"),10),("Combi-Meltagun",find_target("Combi-Meltagun"),15),("Combi-Plasma Gun",find_target("Combi-Plasma Gun"),15),("Combi-Volkite Charger",find_target("Combi-Volkite Charger"),10)]:
    elink(rg,"r45-lern-r-"+re.sub(r"[^a-z0-9]+","-",nm.lower()).strip("-"),nm,tid,pts,None,10)
spec=group(rg,"r45-lern-r-special","Special ranged weapons — maximum two",0,2)
for nm,tid,pts in [("Plasma Gun",find_target("Plasma Gun"),15),("Plasma Cannon",find_target("Plasma Cannon"),20),("Conversion Beamer",find_target("Conversion Beamer"),35)]:
    elink(spec,"r45-lern-sp-"+re.sub(r"[^a-z0-9]+","-",nm.lower()).strip("-"),nm,tid,pts,None,2)
mg2=group(le,"r45-lern-melee","Melee Weapon — one per model");dynexact(mg2,"r45-lern-melee",lm.get("id"))
for nm,tid,pts in [("Power Weapon",find_target("Power Weapon"),0),("Power Fist",find_target("Power Fist"),0),("Chainfist",find_target("Chainfist"),5)]:
    elink(mg2,"r45-lern-m-"+re.sub(r"[^a-z0-9]+","-",nm.lower()).strip("-"),nm,tid,pts,None,10)
elink(le,"r45-lern-transponders","Teleportation Transponders","r46-al-trans-unit",0,None,1)
transport_group(le,"r45-lern-transport",lm.get("id"))
catlink(le,"r45-lern-limit","Alpha Legion — Lernaean limit",CAT_LERN)
visibility(le,[LEG])

# Sheed nested replacement as upgrade (does not add model count)
sheed=ids["r41-unit-xx-9-sheed-ranko"];clear_native(sheed);legion(sheed);ilr(sheed,"Hydra's Resilience")
add_rule(sheed,"r45-sheed-wg","Wargear","Cataphractii Terminator Armour, Combi-plasma gun, two Power Weapons, Auspex and Nuncio Vox.")
sheed.set("hidden","true")
sg=group(le,"r45-sheed-group","Sheed Ranko replacement",0,1)
sc=deep_prefix(sheed,"r45-sheed-copy-");sc.set("id","r45-sheed-replacement");sc.set("name","Sheed Ranko — replaces one Lernaean Terminator");sc.set("type","upgrade");strip_primary(sc);strip_visibility(sc);cost(sc,62);clear_constraints(sc,"max","roster");cons(sc,"r45-sheed-replacement-unique","max",1,"selections","roster");cont(sg,"selectionEntries").append(sc)

# ---- Effrit ----
ef=ids["r41-unit-xx-3-effrit-disruption-cadre"];clear_native(ef)
em=model(ef,"Effrit Disruptors (total squad size)",25,5,10)
add_rule(ef,"r45-eff-wg","Wargear","Power Armour, Bolter with Banestrike Ammunition, Bolt Pistol, close-combat weapon and Frag Grenades.")
legion(ef);ilr(ef,"Infiltrate");ilr(ef,"Move Through Cover");ilr(ef,"Hydra's Wail")
add_infolink(ef,"r45-eff-bane-prof","Banestrike Bolter",P_BANE.get("id"),"profile");add_infolink(ef,"r45-eff-bane-rule","Banestrike",R["Banestrike"].get("id"),"rule")
for tid,nm in [("r46-al-power-dagger","Power Dagger — any model"),("gear-melta-bombs","Melta Bombs — any model")]:
    l=elink(ef,"r45-eff-"+re.sub(r"[^a-z]+","-",nm.lower())[:28],nm,tid,0 if tid.startswith("r46") else 5,None,10)
    if tid.startswith("r46"):cost(l,5)
    mx=cons(l,l.get("id")+"-dyn","max",0);modifier(l,l.get("id")+"-dynmod","increment",mx.get("id"),1,None,[{"childId":em.get("id"),"scope":"root-entry","value":1,"repeats":1}])
eg=group(ef,"r45-eff-special","Special Weapon — one per five models");dynmax(eg,"r45-eff-special-maxdyn",em.get("id"),5)
for nm,tid,pts in [("M.40 Targeter and Stalker Bolter",find_target("M.40 Targeter and Stalker Bolter"),10),("Meltagun",find_target("Meltagun"),10),("Plasma Gun",find_target("Plasma Gun"),15)]:
    elink(eg,"r45-eff-"+re.sub(r"[^a-z0-9]+","-",nm.lower()).strip("-"),nm+" — replaces Bolter",tid,pts,None,2)
pg=group(ef,"r45-eff-principal","Effrit Principal",0,1);elink(pg,"r45-eff-pr-art","Artificer Armour",find_target("Artificer Armour"),10,None,1);elink(pg,"r45-eff-pr-venom","Venom Spheres","r46-al-venom-spheres",0,None,1)
armoury_clone(ef,"r45-eff-pr-arm","Effrit Principal — Armoury (max 50 pts)",50,("gear-hq-artificer","gear-artificer","r46-al-venom-spheres"))
visibility(ef,[LEG])

ids=idmap()

# Character helper
def char_clean(e,mol=False,ic=True):
    clear_native(e);legion(e)
    if ic:ilr(e,"Independent Character")
    if mol:ilr(e,"Master of the Legion")
def retinue_group(ch,id_,choices,limit_lernaean=True):
    remove_group_by_id(ch,id_)
    g=group(ch,id_,"Retinue — choose up to one (no separate FOC slot)",0,1)
    ss=cont(g,"selectionEntries",before=("selectionEntryGroups","costs","modifiers"))
    def find_named(name):
        if name=="Lernaean Terminator Squad":return le
        if name=="Legion Seeker Squad":return ids["fa-seeker"]
        for x in cr.iter(C("selectionEntry")):
            if (x.get("name") or "")==name:return x
        return None
    for i,nm in enumerate(choices):
        src=find_named(nm)
        if src is None:continue
        cp=deep_prefix(src,f"{id_}-{i}-");cp.set("id",f"{id_}-{i}");strip_primary(cp);strip_visibility(cp);clear_constraints(cp,"max","roster")
        if nm=="Lernaean Terminator Squad" and limit_lernaean:catlink(cp,cp.get("id")+"-lernlimit","Alpha Legion — Lernaean limit",CAT_LERN)
        ss.append(cp)
    return g

dyn=ids["r41-unit-xx-4-armillus-dynat"];char_clean(dyn,True,True);ilr(dyn,"The Harrowing");ilr(dyn,"Weapon Mastery")
add_rule(dyn,"r45-dyn-wg","Wargear","Artificer Armour, Iron Halo, Power Weapon, Thunder Hammer, Bolt Pistol, Nuncio Vox, Frag Grenades and Krak Grenades.")
retinue_group(dyn,"r45-dyn-ret",["Legion Command Squad","Legion Terminator Command Squad","Lernaean Terminator Squad"],True);visibility(dyn,[LEG])

exo=ids["r41-unit-xx-5-exodus"];char_clean(exo,False,False)
for n in ["Infiltrate","Move Through Cover","Scout","Lone Killer","Deadshot","Execute the Mandate"]:ilr(exo,n)
add_rule(exo,"r45-exo-wg","Wargear","Power Armour, M.40 Targeter and Stalker Bolter, Bolt Pistol, Combat Blade, Cameleoline, Frag Grenades and Krak Grenades.")
og=group(exo,"r45-exo-options","Options",0,None);elink(og,"r45-exo-melta","Melta Bombs","gear-melta-bombs",5,None,1);elink(og,"r45-exo-dagger","Power Dagger","r46-al-power-dagger",0,None,1);elink(og,"r45-exo-venom","Venom Spheres","r46-al-venom-spheres",0,None,1)
visibility(exo,[LEG])

sk=ids["r41-unit-xx-6-autilon-skorr"];char_clean(sk,True,True);ilr(sk,"Delegatus");ilr(sk,"Desperate for Glory")
add_rule(sk,"r45-sk-wg","Wargear","Artificer Armour, Refractor Field, Bolt Pistol, Rime-shard, Frag Grenades and Krak Grenades.");add_infolink(sk,"r45-sk-rime","Rime-shard",P_RIME.get("id"),"profile")
catlink(sk,"r45-sk-cons","Coils — non-Vigilator Consuls",CAT_COILS_CONS);visibility(sk,[LEG,TRAITOR])

pech=ids["r41-unit-xx-7-ingo-pech"];char_clean(pech,True,True);ilr(pech,"Master of Deceit")
add_rule(pech,"r45-pech-wg","Wargear","Artificer Armour, Iron Halo, Power Weapon, Bolter, Nuncio Vox, Frag Grenades and Krak Grenades.")
retinue_group(pech,"r45-pech-ret",["Legion Command Squad","Legion Terminator Command Squad","Lernaean Terminator Squad","Legion Seeker Squad"],True);visibility(pech,[LEG])

herz=ids["r41-unit-xx-8-mathias-herzog"];char_clean(herz,True,True);ilr(herz,"False Disposition");ilr(herz,"Headhunter Commander")
add_rule(herz,"r45-herz-wg","Wargear","Artificer Armour, Iron Halo, Bolter with Banestrike Ammunition, Bolt Pistol, Power Weapon, Frag Grenades and Krak Grenades.");add_infolink(herz,"r45-herz-bane","Banestrike",R["Banestrike"].get("id"),"rule");add_infolink(herz,"r45-herz-bane-prof","Banestrike Bolter",P_BANE.get("id"),"profile")
hg=group(herz,"r45-herz-hh","Headhunter Commander — no-slot Kill Team",0,1);hss=cont(hg,"selectionEntries",before=("selectionEntryGroups","costs","modifiers"));hcp=deep_prefix(hh,"r45-herz-hh-copy-");hcp.set("id","r45-herz-hh-squad");hcp.set("name","Headhunter Kill Team — Headhunter Commander");strip_primary(hcp);strip_visibility(hcp);clear_constraints(hcp,"max","roster");catlink(hcp,"r45-herz-hh-limit","Alpha Legion — Headhunter limit",CAT_HEAD);hss.append(hcp);visibility(herz,[LEG])

# Alpharius
alp=ids["r41-unit-xx-10-xx-alpharius-the-hydra"];clear_native(alp);legion(alp);ilr(alp,"Primarch")
for n in ["Master of Lies","The Hydra","Sire of the Alpha Legion","I Am Alpharius"]:ilr(alp,n)
add_rule(alp,"r45-alp-wg","Wargear","Pythian Scales, Pale Spear, Hydra's Spite and Frag Grenades.")
add_rule(alp,"r45-alp-scales","Pythian Scales","Counts as Primarch Armour.")
add_infolink(alp,"r45-alp-pale","Pale Spear",P_PALE.get("id"),"profile");add_infolink(alp,"r45-alp-spite","Hydra's Spite",P_SPITE.get("id"),"profile")
retinue_group(alp,"r45-alp-ret",["Legion Honour Guard Squad","Legion Terminator Command Squad","Lernaean Terminator Squad"],False);visibility(alp,[LEG])
alp.set("name","Alpharius, the Hydra")

# ---- Saboteur on Seeker ----
seek=ids["fa-seeker"];remove_group_by_id(seek,"r45-al-saboteur-group")
sg=group(seek,"r45-al-saboteur-group","Alpha Legion — Legion Saboteur",0,1,True);modifier(sg,"r45-al-sab-group-show","set","hidden","false",[{"childId":LEG}])
sab=sel(sg,"r45-al-saboteur","Upgrade Seeker Sergeant to Legion Saboteur","upgrade",25,None,1);cons(sab,"r45-al-saboteur-unique","max",1,"selections","roster");ilr(sab,"Pre-emptive Strike");add_rule(sab,"r45-al-sab-coord","Coordinated Sabotage","After Mutable Tactics has been selected, the Saboteur's squad selects one additional Veteran Skill from the Mutable Tactics list at no additional cost. It may not duplicate the army's Mutable Tactic.")
sg2=group(sab,"r45-al-sab-extra","Coordinated Sabotage — choose one additional skill",1,1)
for tid,n in TACTICS:
    x=sel(sg2,"r45-al-sab-"+tid,n,"upgrade",0,None,1)
    ilr(x,n,"effect")
    modifier(x,x.get("id")+"-hide-dup","set","hidden","true",[{"childId":tid,"scope":"roster"}])

# ---- Rites ----
co=ids[COILS];clear_rules(co);clear_infos(co)
add_rule(co,"r45-coils-sub","Subterfuge","Before determining which player takes the first turn, choose either +1 to the Alpha Legion roll to determine who takes the first turn, or re-roll a failed Seize the Initiative attempt. Choose before relevant dice are rolled.")
add_rule(co,"r45-coils-sig","Signal Corruption","Enemy Reserve rolls suffer -1. This applies to normal Reserve rolls but not units entering automatically on a specified turn.")
add_rule(co,"r45-coils-reward","The Rewards of Treachery","The Detachment may include one Legion-specific unit normally available only to another Space Marine Legion. It may not be a Primarch, named Character, Independent Character or Unique unit. It is selected as Elites, retains its profile, equipment, options and unit-specific rules, replaces its original named Legiones Astartes rule with Legiones Astartes (Alpha Legion), and benefits from Alpha Legion rules including Mutable Tactics but not the core Legion rules of its original Legion.")
add_rule(co,"r45-coils-limit","Limitations","The Detachment has three compulsory Troops choices. Every Infantry unit must possess Infiltrate or Deep Strike, or have access to and purchase a Dedicated Transport; if relying on Mutable Tactics, Infiltrate must be selected. No more than one non-Vigilator Consul. No Fortification or Allied Detachment from another Space Marine Legion.")
visibility(co,[LEG])

he=ids[HEAD];clear_rules(he);clear_infos(he)
add_rule(he,"r45-head-sudden","Sudden Strike","The Alpha Legion player may re-roll the dice used to determine which player takes the first turn. The entire result is re-rolled and the second result accepted.")
add_rule(he,"r45-head-flags","False Flags","During the first Game Turn, an enemy unit declaring a shooting attack against an Alpha Legion unit must first pass a Leadership test unless that enemy unit has already been fired upon by an Alpha Legion unit during the current player turn. On failure it may not make that shooting attack. This does not affect Overwatch, Return Fire or Stand & Shoot.")
add_rule(he,"r45-head-serpent","Leave No Head Upon the Serpent","The Alpha Legion must destroy the enemy Warlord before battle ends. If the enemy Warlord survives, the opponent gains an additional D3 × 50 Victory Points. No effect in missions without Victory Points.")
add_rule(he,"r45-head-limit","Limitations","Every Alpha Legion Vehicle must begin the battle in Reserve unless the mission specifically prohibits it. The Detachment may not include an Allied Detachment.")
visibility(he,[LEG])

# Headhunter Troops copy for Rite, compulsory min2 via hidden category.
troop_id="r45-al-headhunter-troops"
old=ids.get(troop_id)
if old is not None:
    par=next(p for p in cr.iter() for c in list(p) if c is old);par.remove(old)
ht=deep_prefix(hh,"r45-headtroop-copy-");ht.set("id",troop_id);ht.set("name","Headhunter Kill Team — Headhunter Leviathal Troops");set_primary(ht,"cat-troops","Troops");strip_visibility(ht);visibility(ht,[LEG,HEAD]);clear_constraints(ht,"max","roster")
# remove normal HKT 0-1 hidden category from the Troops copy and use rite's lifted limit.
cs=ht.find(C("categoryLinks"))
if cs is not None:
    for x in list(cs):
        if x.get("targetId")==CAT_HEAD:cs.remove(x)
catlink(ht,"r45-headtroop-comp","Headhunter Leviathal — compulsory Headhunters",CAT_HEAD_COMP)
cont(cr,"selectionEntries").append(ht)

# Rewards visibility: current pool appears only with Coils or Pech (OR). Preserve for R46 rebuild.
PECH="r41-unit-xx-7-ingo-pech"
reward_count=0
for rw in cr.findall(f"./{C('selectionEntries')}/{C('selectionEntry')}"):
    if not (rw.get("id") or "").startswith("r46-al-reward-"):continue
    rw.set("hidden","true");ms=rw.find(C("modifiers"))
    if ms is not None:
        for m in list(ms):
            if m.get("field")=="hidden":ms.remove(m)
    # two independent show modifiers implement OR
    modifier(rw,rw.get("id")+"-r45-show-coils","set","hidden","false",[{"childId":LEG},{"childId":COILS}])
    modifier(rw,rw.get("id")+"-r45-show-pech","set","hidden","false",[{"childId":LEG},{"childId":PECH}])
    reward_count+=1

# Revision
cr.set("revision","45");cr.set("gameSystemRevision","10");gr.set("revision","10")
ct.write(CAT,encoding="utf-8",xml_declaration=True);ET.register_namespace("",GNS);gt.write(GST,encoding="utf-8",xml_declaration=True)
ET.register_namespace("",INS);it=ET.parse(IDX);ir=it.getroot()
for x in ir.iter(I("dataIndexEntry")):
    if x.get("filePath")=="Legiones Astartes.cat":x.set("dataRevision","45")
    if x.get("filePath")=="Prohammer 30k.gst":x.set("dataRevision","10")
it.write(IDX,encoding="utf-8",xml_declaration=True)

# validation
rr=ET.parse(CAT).getroot();gg=ET.parse(GST).getroot();rids={x.get("id"):x for x in rr.iter() if x.get("id")};gids={x.get("id") for x in gg.iter() if x.get("id")};checks=[]
def ck(n,o):
    checks.append((n,bool(o)))
    if not o:raise RuntimeError("R45 validation failed: "+n)
ck("CAT45",rr.get("revision")=="45");ck("GST10",gg.get("revision")=="10");ck("CAT->GST10",rr.get("gameSystemRevision")=="10")
idx=IDX.read_text(encoding="utf-8");ck("Index45/10",'dataRevision="45"' in idx and 'dataRevision="10"' in idx)
lg=rids[LEG];mgroup=next(g for g in lg.findall(f"./{C('selectionEntryGroups')}/{C('selectionEntryGroup')}") if g.get("id")=="r46-al-mutable-tactics")
choices=[x for x in mgroup.findall(f"./{C('selectionEntries')}/{C('selectionEntry')}")]
ck("Mutable Tactics exactly six choices",len(choices)==6 and {x.get("name") for x in choices}=={n for _,n in TACTICS})
ck("Mutable Tactics mandatory one",any(x.get("type")=="min" and x.get("value")=="1" for x in mgroup.findall(f"./{C('constraints')}/{C('constraint')}")) and any(x.get("type")=="max" and x.get("value")=="1" for x in mgroup.findall(f"./{C('constraints')}/{C('constraint')}")))
for i in range(11):
    roots=[x for x in rr.findall(f"./{C('selectionEntries')}/{C('selectionEntry')}") if (x.get("id") or "").startswith(f"r41-unit-xx-{i}-")]
    if roots:
        e=roots[0]
        ck(f"XX entry {i} no Source Entry",not any((x.get("name") or "")=="Source Entry" for x in e.findall(f"./{C('rules')}/{C('rule')}")))
ck("Sheed not standalone",rids["r41-unit-xx-9-sheed-ranko"].get("hidden")=="true")
ck("Sheed replacement exists","r45-sheed-replacement" in rids)
ck("Saboteur exists and roster 0-1","r45-al-saboteur" in rids and any(x.get("scope")=="roster" and x.get("type")=="max" and x.get("value")=="1" for x in rids["r45-al-saboteur"].findall(f"./{C('constraints')}/{C('constraint')}")))
ck("Saboteur has six extra tactics",len(next(g for g in rids["r45-al-saboteur"].findall(f"./{C('selectionEntryGroups')}/{C('selectionEntryGroup')}") if g.get("id")=="r45-al-sab-extra").findall(f"./{C('selectionEntries')}/{C('selectionEntry')}"))==6)
ck("Headhunter Troops copy exists",troop_id in rids)
ck("Coils categories exist",all(x in gids for x in [CAT_COILS_CONS,CAT_COILS_TROOPS]))
ck("Rewards pool gated",reward_count==62)
ck("Alpharius readable name",rids["r41-unit-xx-10-xx-alpharius-the-hydra"].get("name")=="Alpharius, the Hydra")
# direct R45 entry/info targets resolve against CAT/GST
bad=[]
for e in rr.iter():
    if not (e.get("id") or "").startswith("r45"):continue
    if e.tag not in (C("entryLink"),C("infoLink")):continue
    t=e.get("targetId")
    if t and t not in rids and t not in gids:bad.append((e.get("id"),t))
ck("All R45 links resolve",not bad)
new=collections.Counter(x.get("id") for x in rr.iter() if x.get("id"));worse={k:v for k,v in new.items() if v>max(1,baseline.get(k,0))}
ck("No new/worsened duplicate IDs",not worse)
OUT.write_text("\n".join([
"Live R45 — Alpha Legion native implementation",
"Input CAT=44/GST=9 -> CAT=45/GST=10","",
"MUTABLE TACTICS:",
"- Rebuilt as a mandatory one-of-six selector on the XX Legion selection.",
"- Counter-Attack, Furious Charge, Infiltrate, Move Through Cover, Siege Specialists and Tank Hunters each reference their actual rule effect.",
"- Native Alpha Legion units dynamically display the selected Mutable Tactic.",
"- Legion Saboteur has a separate mandatory extra-tactic selector and automatically hides the army-wide tactic so it cannot be duplicated.","",
"NATIVE UNITS:",
"- Rebuilt Legion Operatives, Headhunter Kill Team, Lernaean Terminator Squad and Effrit Disruption Cadre with real rules/options instead of Source Entry blocks.",
"- Operative Cell is a real 1-of-3 selector; the separate slotless 0-2 Operative entry is rebuilt from the clean unit.",
"- Headhunters have proper 0-1 tracking (lifted by Headhunter Leviathal), combined max-two special weapons and model-scaled Power Daggers.",
"- Lernaeans have model-scaled weapon choices, 0-1 tracking, Terminator transports and Sheed Ranko as a +62 replacement rather than an HQ.",
"- Effrit special weapons scale one per five models.","",
"CHARACTERS:",
"- Rebuilt Dynat, Exodus, Skorr, Pech, Herzog, Sheed Ranko and Alpharius.",
"- Skorr is Traitor-only and counts toward the Coils Consul limit.",
"- Dynat/Pech received selectable no-slot retinues; Herzog received a no-slot Headhunter Kill Team.",
"- Alpharius has clean rules, weapon profiles and selectable Primarch retinues; his Lernaean retinue ignores the normal Lernaean 0-1 as written.","",
"RITES:",
"- Coils now mechanically requires three compulsory-capable Troops and limits non-Vigilator Consuls to one. Rewards are gated to Coils or Ingo Pech.",
"- Headhunter Leviathal has a dedicated Troops Headhunter entry and mechanically requires two compulsory Headhunter selections.",
"- Battlefield/deployment-only effects remain rule text.","",
"REWARDS:",
f"- Existing {reward_count}-unit Rewards of Treachery pool is now correctly visibility-gated. Its donor-clone content is audited/rebuilt in the next pass rather than silently trusted.","",
"VALIDATION:"
]+[f'- {"PASS" if ok else "FAIL"}: {n}' for n,ok in checks])+"\n",encoding="utf-8")
print(OUT.read_text())
