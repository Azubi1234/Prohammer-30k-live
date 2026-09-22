from pathlib import Path
import collections, re, xml.etree.ElementTree as ET
CAT=Path("Legiones Astartes.cat"); GST=Path("Prohammer 30k.gst"); IDX=Path("index.xml")
OUT=Path("inspection-live-r44-raven-guard-final.txt")
CNS="http://www.battlescribe.net/schema/catalogueSchema"; GNS="http://www.battlescribe.net/schema/gameSystemSchema"; INS="http://www.battlescribe.net/schema/dataIndexSchema"
ET.register_namespace("",CNS)
C=lambda t:f"{{{CNS}}}{t}"; G=lambda t:f"{{{GNS}}}{t}"; I=lambda t:f"{{{INS}}}{t}"
ct=ET.parse(CAT);cr=ct.getroot();gt=ET.parse(GST);gr=gt.getroot()
if cr.get("revision")!="43":raise RuntimeError("R44 expected CAT43")
if gr.get("revision")!="8":raise RuntimeError("R44 expected GST8")
base=collections.Counter(x.get("id") for x in cr.iter() if x.get("id"))
ids={x.get("id"):x for x in cr.iter() if x.get("id")}
LEG="legion-xix";LIB="r25-rite-xix-1-liberation-force";DEC="r25-rite-xix-0-decapitation-strike"

def qns(e):return e.tag.split("}")[0].strip("{")
def cont(p,tag):
    ns=qns(p);q=f"{{{ns}}}{tag}";x=p.find(q)
    if x is not None:return x
    x=ET.SubElement(p,q);return x
def modifier(p,id_,typ,field,value,conds):
    ns=qns(p);ms=cont(p,"modifiers");q=f"{{{ns}}}modifier"
    x=next((z for z in ms.findall(q) if z.get("id")==id_),None)
    if x is None:x=ET.SubElement(ms,q)
    x.attrib.update({"id":id_,"type":typ,"field":field,"value":str(value)})
    for ch in list(x):x.remove(ch)
    if len(conds)==1:target=ET.SubElement(x,f"{{{ns}}}conditions")
    else:
        cgs=ET.SubElement(x,f"{{{ns}}}conditionGroups");cg=ET.SubElement(cgs,f"{{{ns}}}conditionGroup",{"type":"and"});target=ET.SubElement(cg,f"{{{ns}}}conditions")
    for c in conds:
        ET.SubElement(target,f"{{{ns}}}condition",{"type":c.get("type","atLeast"),"value":str(c.get("value",1)),"field":"selections","scope":c.get("scope","roster"),"childId":c["childId"],"shared":"true","includeChildSelections":"true","includeChildForces":"false"})
    return x
def hide_when(p,id_,conds):return modifier(p,id_,"set","hidden","true",conds)
def show_when(p,id_,conds):return modifier(p,id_,"set","hidden","false",conds)
def direct_rule_names(e):
    out=set()
    for r in e.findall(f"./{C('rules')}/{C('rule')}"):out.add((r.get("name") or "").strip().casefold())
    for il in e.findall(f"./{C('infoLinks')}/{C('infoLink')}"):
        out.add((il.get("name") or "").strip().casefold())
        t=ids.get(il.get("targetId"))
        if t is not None:out.add((t.get("name") or "").strip().casefold())
    return out
def dedupe_category_targets(e):
    cs=e.find(C("categoryLinks"))
    if cs is None:return 0
    seen=set();n=0
    for c in list(cs):
        key=(c.get("targetId"),c.get("primary"))
        if key in seen:cs.remove(c);n+=1
        else:seen.add(key)
    return n
def profiles(e):return e.findall(f"./{C('profiles')}/{C('profile')}")

# 1. Replacement visibility is Raven Guard only.
fixed_visibility=[]
for eid in ["r43-rg-kaedes-replacement","r43-rg-sharrowkyn-recon","r43-rg-sharrowkyn-seeker"]:
    e=ids[eid];e.set("hidden","true")
    # Remove prior show modifier, then install exact show.
    ms=e.find(C("modifiers"))
    if ms is not None:
        for m in list(ms):
            if m.get("field")=="hidden":ms.remove(m)
    show_when(e,eid+"-r44-show",[{"childId":LEG}]);fixed_visibility.append(eid)

# 2. Fix three stale weapon target IDs.
fix_targets={
 "r43-mor-ranged-combi-meltagun":"gear-combi-melta",
 "r43-del-ranged-combi-meltagun":"gear-combi-melta",
 "r43-mor-heavy-missile-launcher":"gear-missile",
}
for eid,tid in fix_targets.items():
    if eid not in ids or tid not in ids:raise RuntimeError(f"Cannot repair {eid}->{tid}")
    ids[eid].set("targetId",tid)

# 3. Liberation Force: remove R43 recursive over-hiding.
removed_bad=0
for e in cr.iter():
    ms=e.find(C("modifiers"))
    if ms is None:continue
    for m in list(ms):
        if (m.get("id") or "").endswith("-r43-lib-hide"):
            ms.remove(m);removed_bad+=1

# Only actual selectable item that directly has Immobile/S&P is blocked.
# Include the two known Drop Pod chassis because their source rules require Immobile.
forbidden=set()
for e in cr.iter(C("selectionEntry")):
    names=direct_rule_names(e)
    if "immobile" in names or "slow and purposeful" in names:
        forbidden.add(e.get("id"))
for known in ["transport-drop-pod","transport-dreadnought-pod"]:
    if known in ids:forbidden.add(known)

lib_hidden_entries=0;lib_hidden_links=0
for eid in sorted(x for x in forbidden if x):
    e=ids[eid]
    hide_when(e,eid+"-r44-lib-hide",[{"childId":LEG},{"childId":LIB}]);lib_hidden_entries+=1
for l in cr.iter(C("entryLink")):
    if l.get("targetId") in forbidden:
        hide_when(l,(l.get("id") or "lib")+"-r44-lib-hide",[{"childId":LEG},{"childId":LIB}]);lib_hidden_links+=1

# 4. Decapitation Strike: its compulsory Drop Pod/Dreadclaw selector replaces
# the HSS's ordinary transport selector, so two transports cannot be bought.
hss=ids["hs-heavy-support-squad"]
old_transport=next((g for g in hss.findall(f"./{C('selectionEntryGroups')}/{C('selectionEntryGroup')}") if g.get("id")=="hs-hss-transport"),None)
if old_transport is None:raise RuntimeError("HSS transport group missing")
hide_when(old_transport,"hs-hss-transport-r44-decap-hide",[{"childId":LEG},{"childId":DEC}])

# 5. Clean duplicate category tags copied into nested special-unit retinues.
deduped=0
for eid in ["r43-branne-raptor-squad","r43-pra-dark-retinue","r43-corax-ret-2","r43-corax-ret-3"]:
    if eid in ids:deduped+=dedupe_category_targets(ids[eid])

# Revision
cr.set("revision","44");cr.set("gameSystemRevision","9");gr.set("revision","9")
ct.write(CAT,encoding="utf-8",xml_declaration=True);ET.register_namespace("",GNS);gt.write(GST,encoding="utf-8",xml_declaration=True)
ET.register_namespace("",INS);it=ET.parse(IDX);ir=it.getroot()
for x in ir.iter(I("dataIndexEntry")):
    if x.get("filePath")=="Legiones Astartes.cat":x.set("dataRevision","44")
    if x.get("filePath")=="Prohammer 30k.gst":x.set("dataRevision","9")
it.write(IDX,encoding="utf-8",xml_declaration=True)

# Validation
rr=ET.parse(CAT).getroot();gg=ET.parse(GST).getroot();rids={x.get("id"):x for x in rr.iter() if x.get("id")};checks=[]
def ck(n,o):
    checks.append((n,bool(o)))
    if not o:raise RuntimeError("R44 validation: "+n)
ck("CAT44",rr.get("revision")=="44");ck("GST9",gg.get("revision")=="9");ck("CAT points GST9",rr.get("gameSystemRevision")=="9")
idx=IDX.read_text(encoding="utf-8");ck("Index44/9",'dataRevision="44"' in idx and 'dataRevision="9"' in idx)
for eid in fixed_visibility:
    e=rids[eid];txt=ET.tostring(e.find(C("modifiers")),encoding="unicode")
    ck(eid+" RG-only visibility",e.get("hidden")=="true" and LEG in txt)
for eid,tid in fix_targets.items():ck(eid+" target resolves",rids[eid].get("targetId")==tid and tid in rids)
# Parent units that were wrongly hidden must no longer have recursive lib-hide modifiers.
for eid in ["hq-centurion","recon-unit","hs-heavy-support-squad"]:
    txt=ET.tostring(rids[eid].find(C("modifiers")),encoding="unicode") if rids[eid].find(C("modifiers")) is not None else ""
    ck(eid+" not globally hidden by Liberation", "-r43-lib-hide" not in txt and "-r44-lib-hide" not in txt)
# Known pods are blocked.
for eid in ["transport-drop-pod","transport-dreadnought-pod"]:
    if eid in rids:
        txt=ET.tostring(rids[eid].find(C("modifiers")),encoding="unicode")
        ck(eid+" blocked by Liberation",LIB in txt)
# HSS normal transport hidden during Decap, mandatory special group remains.
txt=ET.tostring(next(g for g in rids["hs-heavy-support-squad"].findall(f"./{C('selectionEntryGroups')}/{C('selectionEntryGroup')}") if g.get("id")=="hs-hss-transport"),encoding="unicode")
ck("Decap hides normal HSS transport group",DEC in txt)
req=next(g for g in rids["hs-heavy-support-squad"].findall(f"./{C('selectionEntryGroups')}/{C('selectionEntryGroup')}") if g.get("id")=="r43-dec-hss-trans")
ck("Decap mandatory transport remains",DEC in ET.tostring(req,encoding="unicode"))
# Every main XIX unit/character has an actual model profile.
for i in range(10):
    roots=[x for x in rids.values() if (x.get("id") or "").startswith(f"r41-unit-xix-{i}-") and x.tag==C("selectionEntry")]
    if roots:ck(f"XIX entry {i} has stat profile",len(profiles(roots[0]))>0)
# All R43/R44 entry/info targets resolve inside CAT unless they are categories from GST.
gids={x.get("id") for x in gg.iter() if x.get("id")}
bad=[]
for e in rr.iter():
    if not (e.get("id") or "").startswith(("r43","r44")):continue
    if e.tag not in (C("entryLink"),C("infoLink")):continue
    t=e.get("targetId")
    if t and t not in rids and t not in gids:bad.append((e.get("id"),t))
ck("All R43/R44 link targets resolve",not bad)
new=collections.Counter(x.get("id") for x in rr.iter() if x.get("id"));worse={k:v for k,v in new.items() if v>max(1,base.get(k,0))}
ck("No new/worsened duplicate IDs",not worse)

lines=[
"Live R44 — Raven Guard post-build correction",
"Input CAT=43/GST=8 -> CAT=44/GST=9","",
"CORRECTIONS:",
"- Kaedes Nex and both Sharrowkyn replacement selectors now default hidden and appear only in a Raven Guard roster.",
"- Corrected Mor Deythan/Deliverer Combi-meltagun targets to gear-combi-melta and Mor Deythan Missile Launcher to gear-missile.",
f"- Removed {removed_bad} over-broad R43 Liberation Force hide modifiers that were incorrectly inherited from nested options.",
f"- Liberation Force now blocks only actual selections/options with Immobile or Slow and Purposeful: {lib_hidden_entries} direct entries and {lib_hidden_links} links to them.",
"- Legion Centurions, Recon Squads and Heavy Support Squads are no longer incorrectly hidden merely because a nested option elsewhere contains a forbidden rule.",
"- Decapitation Strike now hides the Heavy Support Squad's ordinary transport group while its mandatory Drop Pod/Dreadclaw group is active, preventing two Dedicated Transports.",
f"- Removed {deduped} duplicate hidden-category tags from copied Raven Guard retinue units.",
"- Confirmed all ten main XIX special unit/character entries retain real model stat profiles.","",
"VALIDATION:"
]+[f'- {"PASS" if ok else "FAIL"}: {n}' for n,ok in checks]
OUT.write_text("\n".join(lines)+"\n",encoding="utf-8");print(OUT.read_text())
