from pathlib import Path
import collections, xml.etree.ElementTree as ET

CAT=Path("Legiones Astartes.cat"); IDX=Path("index.xml"); OUT=Path("inspection-live-r47-rg-al-clickthrough-fixes.txt")
NS="http://www.battlescribe.net/schema/catalogueSchema"; INS="http://www.battlescribe.net/schema/dataIndexSchema"
ET.register_namespace("",NS)
C=lambda t:f"{{{NS}}}{t}"; I=lambda t:f"{{{INS}}}{t}"
tree=ET.parse(CAT); root=tree.getroot()
if root.get("revision")!="46": raise RuntimeError(f"R47 expected CAT46, got {root.get('revision')}")
if root.get("gameSystemRevision")!="11": raise RuntimeError(f"R47 expected GST dependency 11, got {root.get('gameSystemRevision')}")
baseline=collections.Counter(x.get("id") for x in root.iter() if x.get("id"))
ids={x.get("id"):x for x in root.iter() if x.get("id")}

def cont(p,tag,before=("constraints","categoryLinks","entryLinks","infoLinks","profiles","rules","selectionEntries","selectionEntryGroups","costs","modifiers")):
    q=C(tag); x=p.find(q)
    if x is not None:return x
    x=ET.Element(q); kids=list(p); idx=len(kids)
    for j,k in enumerate(kids):
        if k.tag.split("}")[-1] in before: idx=j; break
    p.insert(idx,x); return x
def clear_constraints(p):
    x=p.find(C("constraints"))
    if x is not None:p.remove(x)
def cons(p,id_,typ,val,field="selections",scope="parent",child=False,automatic=None):
    cs=cont(p,"constraints"); x=next((z for z in cs.findall(C("constraint")) if z.get("id")==id_),None)
    if x is None:x=ET.SubElement(cs,C("constraint"))
    x.attrib.update({"id":id_,"type":typ,"value":str(val),"field":field,"scope":scope,"shared":"true","includeChildSelections":"true" if child else "false","includeChildForces":"false"})
    if automatic is not None:x.set("automatic","true" if automatic else "false")
    return x
def set_cost(p,val):
    cs=cont(p,"costs",before=("modifiers",)); x=next((z for z in cs.findall(C("cost")) if z.get("typeId")=="pts"),None)
    if x is None:x=ET.SubElement(cs,C("cost"),{"name":"Points","typeId":"pts"})
    x.set("value",str(val)); return x
def modifier(p,id_,typ,field,value,conditions=None,repeats=None):
    ms=cont(p,"modifiers"); x=next((z for z in ms.findall(C("modifier")) if z.get("id")==id_),None)
    if x is None:x=ET.SubElement(ms,C("modifier"))
    x.attrib.update({"id":id_,"type":typ,"field":field,"value":str(value)})
    for ch in list(x):x.remove(ch)
    if repeats:
        rs=ET.SubElement(x,C("repeats"))
        for rp in repeats:
            ET.SubElement(rs,C("repeat"),{
                "field":rp.get("field","selections"),"scope":rp.get("scope","parent"),
                "value":str(rp.get("value",1)),"shared":"true","childId":rp["childId"],
                "includeChildSelections":"true" if rp.get("includeChildSelections",False) else "false",
                "includeChildForces":"false","repeats":str(rp.get("repeats",1)),
                "roundUp":"true" if rp.get("roundUp",False) else "false"})
    if conditions:
        cs=ET.SubElement(x,C("conditions"))
        for cd in conditions:
            ET.SubElement(cs,C("condition"),{
                "type":cd.get("type","atLeast"),"value":str(cd.get("value",1)),
                "field":cd.get("field","selections"),"scope":cd.get("scope","roster"),
                "childId":cd["childId"],"shared":"true","includeChildSelections":"true",
                "includeChildForces":"false"})
    return x
def profile(p,id_,name,vals):
    ps=cont(p,"profiles"); x=ET.SubElement(ps,C("profile"),{"id":id_,"name":name,"typeId":"prof-ranged","typeName":"Ranged Weapon","hidden":"false"})
    ch=ET.SubElement(x,C("characteristics"))
    for nm,tid,val in [("Range","ranged-range",vals[0]),("S","ranged-s",vals[1]),("AP","ranged-ap",vals[2]),("Type","ranged-type",vals[3])]:
        q=ET.SubElement(ch,C("characteristic"),{"name":nm,"typeId":tid});q.text=val
    return x
def rule(p,id_,name,text):
    rs=cont(p,"rules");x=ET.SubElement(rs,C("rule"),{"id":id_,"name":name,"hidden":"false"});d=ET.SubElement(x,C("description"));d.text=text;return x
def group_by_id(root_,id_):
    return next((x for x in root_.iter(C("selectionEntryGroup")) if x.get("id")==id_),None)
def entry_by_id(id_):
    return next((x for x in root.iter(C("selectionEntry")) if x.get("id")==id_),None)
def link_by_id(root_,id_):
    return next((x for x in root_.iter(C("entryLink")) if x.get("id")==id_),None)

# 1) Raven Guard Moritat: one clean double-pistol selection in the existing Pistol Pair group.
mor=entry_by_id("hq-consul-moritat")
if mor is None:raise RuntimeError("Moritat missing")
pair=group_by_id(mor,"r29-mor-pair-group")
if pair is None:raise RuntimeError("Moritat Pistol Pair group missing")
ses=cont(pair,"selectionEntries")
for old in list(ses):
    if old.get("id")=="r47-rg-mor-fulcrum-pair":ses.remove(old)
ful=ET.SubElement(ses,C("selectionEntry"),{
    "id":"r47-rg-mor-fulcrum-pair","name":"Two Fulcrum Hand Cannons","type":"upgrade","hidden":"true","import":"true"})
set_cost(ful,20);cons(ful,"r47-rg-mor-fulcrum-pair-max","max",1)
profile(ful,"r47-rg-mor-fulcrum-pair-profile","Fulcrum Hand Cannon (x2)",('18"',"4","4","Pistol, Rending, Concussive"))
rule(ful,"r47-rg-mor-fulcrum-pair-rule","Two Fulcrum Hand Cannons",
     "Raven Guard Moritat only. Replaces both Bolt Pistols with two Fulcrum Hand Cannons for +20 points total. Each hand cannon is Range 18 inches, Strength 4, AP4, Pistol, Rending, Concussive and is used with the Moritat's normal Dual Pistols and Chain Fire rules.")
modifier(ful,"r47-rg-mor-fulcrum-pair-show","set","hidden","false",[{"childId":"legion-xix","scope":"roster"}])

# 2) Corax Raptor retinue: visible base price + per-model scaling from the sixth model onward.
rap=entry_by_id("r43-corax-ret-3")
if rap is None:raise RuntimeError("Corax Raptor retinue missing")
model_id="r43-corax-ret-3-r41-unit-xix-3-raptor-squad-additional"
for lid,base,ppm in [
    ("r43-corax-ret-3-r43-rap-krak",10,2),
    ("r43-corax-ret-3-r43-rap-melta",25,5),
]:
    l=link_by_id(rap,lid)
    if l is None:raise RuntimeError("Missing Corax Raptor grenade option "+lid)
    set_cost(l,base)
    ms=l.find(C("modifiers"))
    if ms is not None:
        for m in list(ms):
            if m.get("field")=="pts":ms.remove(m)
    modifier(l,lid+"-r47-scale","increment","pts",ppm,repeats=[{
        "childId":model_id,"scope":"parent","value":5,"repeats":1,"includeChildSelections":False
    }])

# 3) Alpharius Lernaean retinue: Sheed as a direct visible upgrade.
lern=entry_by_id("r45-alp-ret-2")
if lern is None:raise RuntimeError("Alpharius Lernaean retinue missing")
gs=lern.find(C("selectionEntryGroups"))
sheed=None
if gs is not None:
    for g in list(gs):
        if g.get("id")=="r45-alp-ret-2-r45-sheed-group":
            sheed=next((x for x in g.findall(f"./{C('selectionEntries')}/{C('selectionEntry')}") if "Sheed Ranko" in (x.get("name") or "")),None)
            gs.remove(g)
            break
if sheed is None:
    # Allow safe rerun during development if already moved.
    sheed=next((x for x in lern.findall(f"./{C('selectionEntries')}/{C('selectionEntry')}") if x.get("id")=="r45-alp-ret-2-r45-sheed-replacement"),None)
if sheed is None:raise RuntimeError("Alpharius retinue Sheed replacement missing")
direct=cont(lern,"selectionEntries",before=("selectionEntryGroups","costs","modifiers"))
if sheed not in list(direct):direct.append(sheed)
sheed.set("hidden","false")
sheed.set("name","Sheed Ranko — replace one Lernaean Terminator (+62 pts)")

# 4) Rebuild Alpharius Lernaean transports as one flat, optional 0-1 group.
gs=cont(lern,"selectionEntryGroups",before=("costs","modifiers"))
old_transport=next((g for g in list(gs) if g.get("id")=="r45-alp-ret-2-r45-lern-transport"),None)
if old_transport is None:raise RuntimeError("Alpharius Lernaean transport group missing")
# Capture current transport links, including those in nested Land Raider subgroup.
transport_links=[]
for l in old_transport.iter(C("entryLink")):
    if l.get("targetId") in {"transport-dreadclaw","hs-spartan","hs-lr-phobos","hs-lr-proteus","hs-lr-achilles"}:
        transport_links.append((l.get("name"),l.get("targetId")))
pos=list(gs).index(old_transport);gs.remove(old_transport)
ng=ET.Element(C("selectionEntryGroup"),{"id":"r47-alp-lern-transport","name":"Dedicated Transport — optional","hidden":"false"})
cons(ng,"r47-alp-lern-transport-min","min",0);cons(ng,"r47-alp-lern-transport-max","max",1)
els=cont(ng,"entryLinks",before=("infoLinks","profiles","rules","selectionEntries","selectionEntryGroups","costs","modifiers"))
seen=set()
for nm,target in transport_links:
    if target in seen:continue
    seen.add(target)
    lid="r47-alp-lern-transport-"+target.replace("_","-")
    l=ET.SubElement(els,C("entryLink"),{"id":lid,"name":nm,"targetId":target,"type":"selectionEntry","import":"true","hidden":"false"})
    cons(l,lid+"-max","max",1)
    # Existing capacities: Dreadclaw and Land Raider variants only for five Lernaeans; Spartan remains available above five.
    if target!="hs-spartan":
        modifier(l,lid+"-cap","set","hidden","true",[{"childId":model_id.replace("r43-corax-ret-3-r41-unit-xix-3-raptor-squad-additional","r45-alp-ret-2-r41-unit-xx-2-lernaean-terminator-squad-additional"),"scope":"parent","type":"atLeast","value":6}])
gs.insert(pos,ng)

# Explicitly remove the normal Lernaean 0-1 tag from Alpharius' retinue, per his source rule.
cls=lern.find(C("categoryLinks"))
removed_limit=0
if cls is not None:
    for x in list(cls):
        if x.get("targetId")=="r45-al-lernaean-limit":
            cls.remove(x);removed_limit+=1

# Revision/index.
root.set("revision","47")
tree.write(CAT,encoding="utf-8",xml_declaration=True)
ET.register_namespace("",INS); it=ET.parse(IDX); ir=it.getroot()
for x in ir.iter(I("dataIndexEntry")):
    if x.get("filePath")=="Legiones Astartes.cat":x.set("dataRevision","47")
it.write(IDX,encoding="utf-8",xml_declaration=True)

# Validation.
rr=ET.parse(CAT).getroot(); rids={x.get("id"):x for x in rr.iter() if x.get("id")}; checks=[]
def ck(n,o):
    checks.append((n,bool(o)))
    if not o:raise RuntimeError("R47 validation failed: "+n)
ck("CAT47",rr.get("revision")=="47");ck("GST dependency still 11",rr.get("gameSystemRevision")=="11")
ck("Index47",'dataRevision="47"' in IDX.read_text(encoding="utf-8"))
f=rids.get("r47-rg-mor-fulcrum-pair");ck("Fulcrum pair exists",f is not None)
ck("Fulcrum pair costs 20",f is not None and any(c.get("typeId")=="pts" and c.get("value")=="20" for c in f.findall(f"./{C('costs')}/{C('cost')}")))
ck("Fulcrum pair Raven Guard gated",f is not None and "legion-xix" in ET.tostring(f,encoding="unicode"))
rap=rids["r43-corax-ret-3"]
for lid,base in [("r43-corax-ret-3-r43-rap-krak","10"),("r43-corax-ret-3-r43-rap-melta","25")]:
    l=next((x for x in rap.iter(C("entryLink")) if x.get("id")==lid),None)
    ck(lid+" visible base price",l is not None and any(c.get("value")==base for c in l.findall(f"./{C('costs')}/{C('cost')}")))
    ck(lid+" scales after five",l is not None and 'value="5"' in ET.tostring(l,encoding="unicode") and 'scope="parent"' in ET.tostring(l,encoding="unicode"))
lern=rids["r45-alp-ret-2"]; xml=ET.tostring(lern,encoding="unicode")
ck("Sheed direct in Alpharius Lernaeans",any(x.get("id")=="r45-alp-ret-2-r45-sheed-replacement" for x in lern.findall(f"./{C('selectionEntries')}/{C('selectionEntry')}")))
ck("No nested Sheed group",not any(g.get("id")=="r45-alp-ret-2-r45-sheed-group" for g in lern.findall(f"./{C('selectionEntryGroups')}/{C('selectionEntryGroup')}")))
tg=next((g for g in lern.findall(f"./{C('selectionEntryGroups')}/{C('selectionEntryGroup')}") if g.get("id")=="r47-alp-lern-transport"),None)
ck("Flat optional Alpharius transport group",tg is not None and any(x.get("type")=="min" and x.get("value")=="0" for x in tg.findall(f"./{C('constraints')}/{C('constraint')}")) and any(x.get("type")=="max" and x.get("value")=="1" for x in tg.findall(f"./{C('constraints')}/{C('constraint')}")))
ck("No nested Land Raider subgroup",tg is not None and not tg.findall(f"./{C('selectionEntryGroups')}/{C('selectionEntryGroup')}"))
ck("No transport defaults",tg is not None and all(x.get("defaultAmount") in (None,"0") for x in tg.iter(C("entryLink"))))
ck("Alpharius retinue ignores normal Lernaean 0-1",not any(x.get("targetId")=="r45-al-lernaean-limit" for x in lern.findall(f"./{C('categoryLinks')}/{C('categoryLink')}")))
new=collections.Counter(x.get("id") for x in rr.iter() if x.get("id")); worse={k:v for k,v in new.items() if v>max(1,baseline.get(k,0))}
ck("No new/worsened duplicate IDs",not worse)

OUT.write_text("\n".join([
"Live R47 — Raven Guard / Alpha Legion click-through fixes",
"Input CAT=46/GST=11 -> CAT=47/GST remains 11","",
"RAVEN GUARD:",
"- Added Two Fulcrum Hand Cannons as a Raven Guard-only Moritat Pistol Pair option for +20 points, replacing both Bolt Pistols.",
"- Corax's Raptor retinue now shows Krak Grenades at +10 points for the five-model minimum and Melta Bombs at +25, then scales +2/+5 for each model above five.","",
"ALPHA LEGION:",
"- Moved Sheed Ranko out of the nested replacement subgroup and made him a direct +62-point upgrade inside Alpharius' Lernaean retinue.",
"- Rebuilt Alpharius' Lernaean Dedicated Transport selector as a flat optional 0-1 choice so no Land Raider subgroup can be auto-selected.",
"- Removed the normal Lernaean 0-1 category from Alpharius' retinue, as his Primarch Retinue rule explicitly exempts it.","",
"VALIDATION:"
]+[f'- {"PASS" if ok else "FAIL"}: {n}' for n,ok in checks])+"\n",encoding="utf-8")
print(OUT.read_text())
