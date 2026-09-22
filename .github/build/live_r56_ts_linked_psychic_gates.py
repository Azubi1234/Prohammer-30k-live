from pathlib import Path
import collections, hashlib, xml.etree.ElementTree as ET

CAT=Path("Legiones Astartes.cat"); GST=Path("Prohammer 30k.gst"); IDX=Path("index.xml")
OUT=Path("inspection-live-r56-ts-linked-psychic-gates.txt")
CNS="http://www.battlescribe.net/schema/catalogueSchema"; GNS="http://www.battlescribe.net/schema/gameSystemSchema"; INS="http://www.battlescribe.net/schema/dataIndexSchema"
ET.register_namespace("",CNS)
C=lambda t:f"{{{CNS}}}{t}"; G=lambda t:f"{{{GNS}}}{t}"; I=lambda t:f"{{{INS}}}{t}"

ct=ET.parse(CAT); cr=ct.getroot(); gt=ET.parse(GST); gr=gt.getroot()
if cr.get("revision")!="55": raise RuntimeError(f"R56 expected CAT55, got {cr.get('revision')}")
if gr.get("revision")!="13": raise RuntimeError(f"R56 expected GST13, got {gr.get('revision')}")
baseline=collections.Counter(x.get("id") for x in cr.iter() if x.get("id"))
ids={x.get("id"):x for x in cr.iter() if x.get("id")}

# Build entryLink -> canonical shared selection target map for the TS psychic system.
psychic_names={
    "Pavoni","Raptora","Corvidae","Athanaeans","Pyrae",
    "Biomancy","Divination","Pyromancy","Telekinesis","Telepathy",
    "Brotherhood of Psykers (Mastery Level 1)",
    "Brotherhood of Psykers (Fellowships price)",
    "Brotherhood of Psykers (20-model Tactical Squad)",
}
link_to_target={}
for l in cr.iter(C("entryLink")):
    tid=l.get("targetId")
    t=ids.get(tid)
    if t is None: continue
    if (t.get("name") or "") in psychic_names:
        link_to_target[l.get("id")]=tid

def direct_modifiers(e):
    ms=e.find(C("modifiers"))
    return ms,list(ms) if ms is not None else []

def cond_dict(c,child,type_override=None):
    return {
        "type":type_override or c.get("type","atLeast"),
        "value":c.get("value","1"),
        "field":c.get("field","selections"),
        "scope":c.get("scope","root-entry"),
        "childId":child,
        "shared":c.get("shared","true"),
        "includeChildSelections":c.get("includeChildSelections","true"),
        "includeChildForces":c.get("includeChildForces","false"),
    }

def add_simple_modifier(ms,id_,typ,field,value,condition):
    if any(x.get("id")==id_ for x in ms.findall(C("modifier"))): return False
    m=ET.SubElement(ms,C("modifier"),{"id":id_,"type":typ,"field":field,"value":str(value)})
    cs=ET.SubElement(m,C("conditions"))
    ET.SubElement(cs,C("condition"),condition)
    return True

patched_hidden=0; patched_other=0; refs_seen=0
examples=[]
for e in cr.iter():
    ms,mods=direct_modifiers(e)
    if ms is None: continue
    for m in list(mods):
        mid=m.get("id") or ""
        # Avoid recursively processing compatibility modifiers.
        if "-r56-linkcompat-" in mid: continue
        rel=[]
        for c in m.iter(C("condition")):
            cid=c.get("childId")
            if cid in link_to_target:
                rel.append((c,cid,link_to_target[cid]))
        if not rel: continue
        refs_seen += len(rel)
        for idx,(c,local_id,target_id) in enumerate(rel):
            suffix=hashlib.sha1((mid+"|"+local_id+"|"+target_id+"|"+str(idx)).encode()).hexdigest()[:10]
            new_id=(e.get("id") or "anon")+"-r56-linkcompat-"+suffix
            typ=m.get("type","set"); field=m.get("field"); value=m.get("value","")
            ctype=c.get("type","atLeast")
            # Hidden-if-missing is the key broken UI case. If canonical target is selected,
            # explicitly unhide the option/group even if the client does not count the link ID.
            if field=="hidden" and value=="true" and ctype=="lessThan" and c.get("value")=="1":
                nc=cond_dict(c,target_id,"atLeast"); nc["value"]="1"
                if add_simple_modifier(ms,new_id,"set","hidden","false",nc):
                    patched_hidden+=1
                    if len(examples)<20: examples.append((e.get("id"),e.get("name"),local_id,target_id,"show"))
            else:
                # For min/max/other state changes, mirror the modifier using the canonical target.
                nc=cond_dict(c,target_id)
                if add_simple_modifier(ms,new_id,typ,field,value,nc):
                    patched_other+=1
                    if len(examples)<20: examples.append((e.get("id"),e.get("name"),local_id,target_id,field))

# Explicit sanity checks for the most visible selectors.
must_groups=[
 "r45-cult-hq-praetor","r19-ts-praetor-disciplines","r19-ts-praetor-powers",
 "r45-cult-hq-centurion","r19-ts-centurion-disciplines","r19-ts-centurion-powers",
 "r45-cult-veteran-unit","r19-ts-veteran-unit-brotherhood-disciplines","r19-ts-veteran-unit-brotherhood-powers",
 "r45-cult-terminator-unit","r19-ts-terminator-unit-brotherhood-disciplines","r19-ts-terminator-unit-brotherhood-powers",
]
for gid in must_groups:
    if gid not in ids: raise RuntimeError("Missing expected TS psychic group "+gid)

# Revision bump and another GST bump to force a completely fresh pair.
cr.set("revision","56"); cr.set("gameSystemRevision","14"); gr.set("revision","14")
ET.register_namespace("",CNS); ct.write(CAT,encoding="utf-8",xml_declaration=True)
ET.register_namespace("",GNS); gt.write(GST,encoding="utf-8",xml_declaration=True)
it=ET.parse(IDX); ir=it.getroot()
for x in ir.iter(I("dataIndexEntry")):
    if x.get("filePath")=="Legiones Astartes.cat": x.set("dataRevision","56")
    elif x.get("filePath")=="Prohammer 30k.gst": x.set("dataRevision","14")
ET.register_namespace("",INS); it.write(IDX,encoding="utf-8",xml_declaration=True)

# Validate XML/revisions/links and confirm compatibility modifiers landed.
rr=ET.parse(CAT).getroot(); gg=ET.parse(GST).getroot(); checks=[]
def ck(n,o):
    checks.append((n,bool(o)))
    if not o: raise RuntimeError("R56 validation failed: "+n)
ck("CAT revision 56",rr.get("revision")=="56")
ck("CAT points GST14",rr.get("gameSystemRevision")=="14")
ck("GST revision 14",gg.get("revision")=="14")
idx=IDX.read_text(encoding="utf-8")
ck("index CAT56/GST14",'dataRevision="56"' in idx and 'dataRevision="14"' in idx)
ck("TS linked psychic references found",refs_seen>0)
ck("TS hidden compatibility gates added",patched_hidden>0)
ck("TS non-hidden compatibility gates added",patched_other>0)
text=CAT.read_text(encoding="utf-8")
ck("canonical catalogue namespace",'ns0:' not in text and '<catalogue xmlns="http://www.battlescribe.net/schema/catalogueSchema"' in text[:500])

# No new/worsened duplicate IDs.
new=collections.Counter(x.get("id") for x in rr.iter() if x.get("id"))
worse={k:v for k,v in new.items() if v>max(1,baseline.get(k,0))}
ck("no new/worsened duplicate IDs",not worse)

# All entry/info link targets resolve against CAT or GST.
rids={x.get("id") for x in rr.iter() if x.get("id")}; gids={x.get("id") for x in gg.iter() if x.get("id")}
bad=[]
for x in rr.iter():
    if x.tag not in (C("entryLink"),C("infoLink"),C("categoryLink")): continue
    tid=x.get("targetId")
    if tid and tid not in rids and tid not in gids: bad.append((x.get("id"),tid))
ck("all catalogue link targets resolve",not bad)

OUT.write_text("\n".join([
 "Live R56 — Thousand Sons linked psychic gate compatibility",
 "Input CAT55/GST13 -> CAT56/GST14","",
 "WHY:",
 "- The TS psychic system was present in the XML, but many Cult/discipline/Brotherhood visibility conditions still referenced local entryLink IDs after those choices were universalised into shared selections.",
 "- New Recruit can resolve linked selections by their shared target identity, which can leave the old local-ID visibility gates hiding every discipline/power.","",
 "FIX:",
 f"- Found {refs_seen} TS psychic/Cult/Brotherhood condition references to linked selections.",
 f"- Added {patched_hidden} canonical-target visibility overrides so Cult-linked disciplines/powers actually appear.",
 f"- Added {patched_other} canonical-target mirrors for mandatory min/max/state modifiers.",
 "- No psychic rule, Cult, discipline or power was duplicated; all selectors still reference the existing canonical shared entries.",
 "- Praetor, Centurion/Consul, Veteran Brotherhood and Terminator Brotherhood selectors were explicitly verified present.",
 "- Bumped CAT and GST together again to force a fresh New Recruit pair.","",
 "EXAMPLES:",
]+[f"- {a} / {b}: {c} -> {d} ({e})" for a,b,c,d,e in examples]+[
 "","VALIDATION:"
]+[f'- {"PASS" if ok else "FAIL"}: {n}' for n,ok in checks])+"\n",encoding="utf-8")
print(OUT.read_text())
