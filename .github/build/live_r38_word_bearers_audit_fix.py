from pathlib import Path
import re, xml.etree.ElementTree as ET

CAT=Path("Legiones Astartes.cat"); GST=Path("Prohammer 30k.gst"); IDX=Path("index.xml")
OUT=Path("inspection-live-r38-word-bearers-audit-fix.txt")
CNS="http://www.battlescribe.net/schema/catalogueSchema"; GNS="http://www.battlescribe.net/schema/gameSystemSchema"; INS="http://www.battlescribe.net/schema/dataIndexSchema"
ET.register_namespace("",CNS); C=lambda t:f"{{{CNS}}}{t}"; G=lambda t:f"{{{GNS}}}{t}"; I=lambda t:f"{{{INS}}}{t}"
ct=ET.parse(CAT); cr=ct.getroot(); gt=ET.parse(GST); gr=gt.getroot()
if cr.get("revision")!="37": raise RuntimeError(f"R38 expected CAT37, got {cr.get('revision')}")
if gr.get("revision")!="3": raise RuntimeError(f"R38 expected GST3, got {gr.get('revision')}")

def qns(e):return e.tag.split("}")[0].strip("{")
def cont(p,tag,before=("constraints","categoryLinks","entryLinks","infoLinks","profiles","rules","selectionEntries","selectionEntryGroups","costs","modifiers")):
    ns=qns(p); q=f"{{{ns}}}{tag}"; x=p.find(q)
    if x is not None:return x
    x=ET.Element(q); kids=list(p); idx=len(kids)
    for j,k in enumerate(kids):
        if k.tag.split("}")[-1] in before:idx=j;break
    p.insert(idx,x);return x
def cons(p,id_,typ,val,field="selections",scope="parent",child=False):
    ns=qns(p); cs=cont(p,"constraints"); q=f"{{{ns}}}constraint"
    x=next((z for z in cs.findall(q) if z.get("id")==id_),None)
    if x is None:x=ET.SubElement(cs,q)
    x.attrib.update({"id":id_,"type":typ,"value":str(val),"field":field,"scope":scope,"shared":"true","includeChildSelections":"true" if child else "false","includeChildForces":"false"})
    return x
def cost(p,val):
    cs=cont(p,"costs",before=("modifiers",)); x=next((z for z in cs.findall(C("cost")) if z.get("typeId")=="pts"),None)
    if x is None:x=ET.SubElement(cs,C("cost"),{"name":"Points","typeId":"pts"})
    x.set("value",str(val));return x
def modifier(p,id_,typ,field,value,conditions):
    ns=qns(p); ms=cont(p,"modifiers"); x=next((z for z in ms.findall(f"{{{ns}}}modifier") if z.get("id")==id_),None)
    if x is None:x=ET.SubElement(ms,f"{{{ns}}}modifier")
    x.attrib.update({"id":id_,"type":typ,"field":field,"value":str(value)})
    for ch in list(x):x.remove(ch)
    if len(conditions)==1:target=ET.SubElement(x,f"{{{ns}}}conditions")
    else:
        cgs=ET.SubElement(x,f"{{{ns}}}conditionGroups"); cg=ET.SubElement(cgs,f"{{{ns}}}conditionGroup",{"type":"and"}); target=ET.SubElement(cg,f"{{{ns}}}conditions")
    for c in conditions:
        ET.SubElement(target,f"{{{ns}}}condition",{"type":c.get("type","atLeast"),"value":str(c.get("value",1)),"field":"selections","scope":c.get("scope","roster"),"childId":c["childId"],"shared":"true","includeChildSelections":"true","includeChildForces":"false"})
    return x
def add_infolink(p,id_,name,target,typ="rule"):
    ils=cont(p,"infoLinks"); x=next((z for z in ils.findall(C("infoLink")) if z.get("id")==id_),None)
    if x is None:x=ET.SubElement(ils,C("infoLink"))
    x.attrib.update({"id":id_,"name":name,"targetId":target,"type":typ,"hidden":"false"});return x
def elink(p,id_,name,target,pts,maxv=1,hidden=True):
    es=cont(p,"entryLinks"); x=next((z for z in es.findall(C("entryLink")) if z.get("id")==id_),None)
    if x is None:x=ET.SubElement(es,C("entryLink"))
    x.attrib.update({"id":id_,"name":name,"targetId":target,"type":"selectionEntry","import":"true","hidden":"true" if hidden else "false"})
    cons(x,id_+"-max","max",maxv); cost(x,pts); return x

ids={e.get("id"):e for e in cr.iter() if e.get("id")}

# 1. Remove accidental hard max=0 constraints from groups whose real max is dynamic.
dynamic_titles={
 "Special weapon replacement — up to 1 per 5 models",
 "Close-combat weapon replacement — up to 1 per 5 models",
 "Replace Axe-rake — any model",
 "Chainsword replacement — up to 1 per 5 models",
 "Bolt Pistol replacement — up to 1 per 5 models",
}
removed_zero_caps=0
for g in cr.iter(C("selectionEntryGroup")):
    if (g.get("name") or "") not in dynamic_titles:continue
    cs=g.find(C("constraints"))
    if cs is None:continue
    for c in list(cs):
        if c.get("type")=="max" and c.get("value")=="0" and "dynmax" not in (c.get("id") or ""):
            cs.remove(c); removed_zero_caps+=1

# 2. Canonical shared WB armoury rules.
sr=cr.find(C("sharedRules")); shared={r.get("name"):r for r in sr.findall(C("rule"))}
def shr(name,text):
    r=shared.get(name)
    if r is None:
        rid="r38-wb-shared-"+re.sub(r"[^a-z0-9]+","-",name.lower()).strip("-")[:70]
        r=ET.SubElement(sr,C("rule"),{"id":rid,"name":name,"hidden":"false"}); shared[name]=r
    d=r.find(C("description"))
    if d is None:d=ET.SubElement(r,C("description"))
    d.text=text;return r

arm_rules={
"Accursed Crozius":"""User Strength Power Weapon. The bearer receives a 4+ Invulnerable Save, counts as a Personal Icon/Summoning Point for Daemonic Covenant, and counts as a Dark Apostle for The Dark Shepherds. A model may never possess more than one Accursed Crozius.""",
"Tainted Weapon":"""Selected instead of a Power Weapon at the same points cost. User Strength, Specialist Weapon. Any unsaved Wound inflicted becomes a Massive Wound and inflicts D3 Wounds instead of 1. It is not a Power Weapon and does not ignore Armour Saves.""",
"Burning Lore":"""A Word Bearers Praetor, Centurion, Chaplain or Diabolist that is not already a Psyker may purchase Burning Lore. The model becomes a Psyker with Mastery Level 1 and selects exactly one power from Biomancy or Telepathy.""",
"Hex-Bolts":"""Bolt Pistols, Bolters, Combi-Bolters, Storm Bolters and the bolter component of Combi-Weapons carried by the upgraded unit gain Soul Blaze. Soul Blaze: at the end of each turn, a unit wounded by such an attack suffers D3 Strength 4 AP5 hits with no Cover Saves on a 4+; otherwise the blaze ends. Hex-Bolts cannot be combined with Special Issue Ammunition or another ammunition upgrade.""",
"Icon of Chaos Undivided":"""The bearer is a Summoning Point. Friendly non-Daemon Word Bearers units with at least one model within 6" automatically pass Morale and Pinning tests and may not voluntarily fail a break test while within the aura.""",
"Dark Channelling":"""Requires a Diabolist in the Detachment. After deployment but before the first turn, roll D6 for each upgraded squad. 1–3: Zealot — the unit automatically passes Morale/Pinning, may not voluntarily fail a break test, and in the first round of a melee may re-roll failed To Hit rolls against enemies it was not engaged with in the prior turn. 4–5: models gain +1 Strength. 6: the unit gains Daemon — a 5+ Invulnerable Save and Fear — ceases to be Scoring, and in VP missions counts as destroyed at battle end even if it survives. Effects apply only to the upgraded squad.""",
"Diabolist":"""Gains Daemon and Preferred Enemy (Loyalists). May not select a Bike, Jetbike, Terminator Armour, Power Fist or Thunder Hammer. Enables eligible squads to purchase Dark Channelling. A Diabolist remains a Centurion for Accursed Crozius access and counts as a Dark Apostle if it purchases one.""",
}
for n,t in arm_rules.items():shr(n,t)

# Replace direct local armoury definitions with a single shared reference.
for eid,nm in [
 ("r46-wb-accursed-crozius","Accursed Crozius"),
 ("r46-wb-tainted-weapon","Tainted Weapon"),
 ("r46-wb-burning-lore","Burning Lore"),
 ("r46-wb-hex-bolts","Hex-Bolts"),
 ("r46-wb-icon-chaos-undivided","Icon of Chaos Undivided"),
 ("r46-wb-dark-channelling","Dark Channelling"),
 ("r46-wb-diabolist","Diabolist"),
]:
    e=ids[eid]; rs=e.find(C("rules"))
    if rs is not None:
        for r in list(rs):
            if (r.get("name") or "")==nm:rs.remove(r)
    add_infolink(e,"r38-"+eid+"-canonical",nm,shared[nm].get("id"),"rule")

# Hol Beloth uses canonical Tainted Weapon instead of redefining it.
hol=ids["r41-unit-xvii-11-hol-beloth"]
rs=hol.find(C("rules"))
if rs is not None:
    for r in list(rs):
        if (r.get("name") or "")=="Tainted Weapon":rs.remove(r)
add_infolink(hol,"r38-wb-hol-tainted","Tainted Weapon",shared["Tainted Weapon"].get("id"),"rule")

# Erebus/Kor explicitly reference canonical Burning Lore.
for eid in ["r41-unit-xvii-7-high-chaplain-erebus","r41-unit-xvii-8-kor-phaeron-the-black-cardinal"]:
    add_infolink(ids[eid],"r38-"+eid+"-burning","Burning Lore",shared["Burning Lore"].get("id"),"rule")
# Erebus references canonical Crozius plus its Master-crafted modification.
add_infolink(ids["r41-unit-xvii-7-high-chaplain-erebus"],"r38-wb-ere-crozius-rule","Accursed Crozius",shared["Accursed Crozius"].get("id"),"rule")

# 3. Dark Channelling links are hidden until a Diabolist-equivalent is actually selected.
dark_links=0
for l in cr.iter(C("entryLink")):
    if l.get("targetId")!="r46-wb-dark-channelling":continue
    l.set("hidden","true")
    modifier(l,(l.get("id") or "dark")+"-r38-show","set","hidden","false",[
        {"childId":"legion-xvii","scope":"roster"},
        {"childId":"r37-wb-diabolist-req","scope":"roster"},
    ])
    dark_links+=1

# 4. Tainted Weapon is genuinely available to WB Characters that can buy a Power Weapon.
# Generic Sergeant armoury groups: copy same cost as the local Power Weapon link.
tainted_links=0
for g in cr.iter(C("selectionEntryGroup")):
    direct=g.findall(f"./{C('entryLinks')}/{C('entryLink')}")
    pw=next((x for x in direct if x.get("targetId")=="gear-power-weapon"),None)
    if pw is None:continue
    if any(x.get("targetId")=="r46-wb-tainted-weapon" for x in direct):continue
    pc=pw.find(f"./{C('costs')}/{C('cost')}"); pts=float(pc.get("value")) if pc is not None else 0
    l=elink(g,"r38-wb-tainted-"+re.sub(r"[^a-z0-9]+","-",g.get("id","group").lower())[-55:],"Tainted Weapon — Word Bearers", "r46-wb-tainted-weapon",pts,1,True)
    modifier(l,l.get("id")+"-show","set","hidden","false",[{"childId":"legion-xvii","scope":"roster"}])
    tainted_links+=1

# Unit-specific Characters with +10 Power Weapon choices.
for gid in [
 "r37-wb-zeal-overseer-weapon",
 "r37-wb-ashen-iconoclast",
 "r37-wb-proc-prime-melee",
 "r37-wb-poss-champ-melee",
]:
    g=ids.get(gid)
    if g is None:
        # ids map does not include groups; find manually
        g=next((x for x in cr.iter(C("selectionEntryGroup")) if x.get("id")==gid),None)
    if g is None:continue
    if any(x.get("targetId")=="r46-wb-tainted-weapon" for x in g.findall(f"./{C('entryLinks')}/{C('entryLink')}")):continue
    elink(g,gid+"-tainted","Tainted Weapon","r46-wb-tainted-weapon",10,1,False)
    tainted_links+=1
# Gal Vorbak Dark Martyr groups can be copied/prefixed; detect by name.
for g in cr.iter(C("selectionEntryGroup")):
    if (g.get("name") or "")!="Replace close-combat weapon":continue
    # only within a Gal Vorbak root
    pmap={c:p for p in cr.iter() for c in p}; p=g; names=[]
    while p in pmap:
        p=pmap[p]
        if p.get("name"):names.append(p.get("name"))
        if "Gal Vorbak" in " ".join(names):break
    if "Gal Vorbak" not in " ".join(names):continue
    if any(x.get("targetId")=="r46-wb-tainted-weapon" for x in g.findall(f"./{C('entryLinks')}/{C('entryLink')}")):continue
    elink(g,(g.get("id") or "")+"-tainted","Tainted Weapon","r46-wb-tainted-weapon",10,1,False)
    tainted_links+=1

# 5. Daemonkin result 5 includes its actual ProHammer effect rather than a bare name.
daemonkin=shared.get("Daemonkin")
if daemonkin is not None:
    d=daemonkin.find(C("description"))
    d.text="""After deployment but before the first turn, roll a D6 for the squad. 1: Scout — make the normal pre-game Scout move and gain Outflank. 2: Furious Charge — +1 Strength and +1 Initiative in assault on the turn the unit charges. 3: Fleet — may charge even if it Advanced. 4: close-combat attacks gain Rending — a To Wound roll of 6 is AP2; against vehicles an Armour Penetration roll of 6 adds D3. 5: Feel No Pain (5+) — after an eligible failed saving throw, ignore the Wound on a 5+. 6: Counter-Attack — when charged while unengaged, pass a Leadership test to gain +1 Attack for that Assault phase."""

# 6. Ensure no all-caps XVII unit names regressed.
for e in cr.iter(C("selectionEntry")):
    if not (e.get("id") or "").startswith("r41-unit-xvii-"):continue
    n=e.get("name") or ""; letters=re.sub(r"[^A-Za-z]","",n)
    if len(letters)>3 and letters==letters.upper():
        e.set("name",n.lower().title().replace(" Of "," of ").replace(" The "," the "))

# Revision
cr.set("revision","38"); cr.set("gameSystemRevision","4"); gr.set("revision","4")
ct.write(CAT,encoding="utf-8",xml_declaration=True); ET.register_namespace("",GNS); gt.write(GST,encoding="utf-8",xml_declaration=True)
it=ET.parse(IDX); ir=it.getroot(); ET.register_namespace("",INS)
for x in ir.iter(I("dataIndexEntry")):
    if x.get("filePath")=="Legiones Astartes.cat":x.set("dataRevision","38")
    if x.get("filePath")=="Prohammer 30k.gst":x.set("dataRevision","4")
it.write(IDX,encoding="utf-8",xml_declaration=True)

# Validation
cc=ET.parse(CAT).getroot(); gg=ET.parse(GST).getroot(); checks=[]
def ck(n,o):
    checks.append((n,bool(o)))
    if not o:raise RuntimeError("R38 validation failed: "+n)
ck("CAT revision 38",cc.get("revision")=="38")
ck("GST revision 4",gg.get("revision")=="4")
ck("CAT points GST4",cc.get("gameSystemRevision")=="4")
idx=IDX.read_text(encoding="utf-8"); ck("Index 38/4",'dataRevision="38"' in idx and 'dataRevision="4"' in idx)
# dynamic groups no accidental static zero max
badzero=[]
for g in cc.iter(C("selectionEntryGroup")):
    if (g.get("name") or "") in dynamic_titles:
        for c in g.findall(f"./{C('constraints')}/{C('constraint')}"):
            if c.get("type")=="max" and c.get("value")=="0" and "dynmax" not in (c.get("id") or ""):badzero.append((g.get("id"),c.get("id")))
ck("Dynamic weapon groups no hard max0",not badzero)
# shared armoury only one canonical shared definition each
csr=cc.find(C("sharedRules"))
for n in arm_rules:
    ck("Shared canonical "+n,len([r for r in csr.findall(C("rule")) if r.get("name")==n])==1)
# Dark Channelling links mechanically gated
dls=[l for l in cc.iter(C("entryLink")) if l.get("targetId")=="r46-wb-dark-channelling"]
ck("Dark Channelling links exist",len(dls)>0)
ck("Dark Channelling links default hidden",all(l.get("hidden")=="true" for l in dls))
# no local duplicate named armoury rule definitions outside sharedRules
pmap={c:p for p in cc.iter() for c in p}; dup=[]
for r in cc.iter(C("rule")):
    if (r.get("name") or "") not in arm_rules:continue
    if pmap.get(r) is not csr:dup.append((r.get("name"),pmap.get(r).tag if pmap.get(r) is not None else ""))
ck("No local duplicate WB armoury rule definitions",not dup)

lines=[
"Live R38 — Word Bearers audit fixes",
"Input CAT=37/GST=3 -> CAT=38/GST=4","",
"FIXES:",
f"- Removed {removed_zero_caps} accidental hard max-0 constraints from dynamic squad weapon groups; scaling caps can now function.",
"- Canonicalised Accursed Crozius, Tainted Weapon, Burning Lore, Hex-Bolts, Icon of Chaos Undivided, Dark Channelling and Diabolist as shared rule definitions.",
f"- Mechanically gated {dark_links} Dark Channelling links behind the presence of a Diabolist-equivalent.",
f"- Added {tainted_links} Tainted Weapon access links to eligible generic/unit-specific Word Bearers Characters at the matching Power Weapon cost.",
"- Expanded Daemonkin's Feel No Pain result with the actual effect rather than a reference-only name.",
"- Preserved normal XVII display capitalization.","",
"VALIDATION:"
]+[f'- {"PASS" if ok else "FAIL"}: {n}' for n,ok in checks]
OUT.write_text("\n".join(lines)+"\n",encoding="utf-8")
print(OUT.read_text())
