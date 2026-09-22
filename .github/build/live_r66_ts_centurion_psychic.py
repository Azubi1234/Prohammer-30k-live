from pathlib import Path
import copy, collections, hashlib, xml.etree.ElementTree as ET

CAT=Path("Legiones Astartes.cat"); IDX=Path("index.xml")
OUT=Path("inspection-live-r66-ts-centurion-psychic-ui.txt")
NS="http://www.battlescribe.net/schema/catalogueSchema"; INS="http://www.battlescribe.net/schema/dataIndexSchema"
ET.register_namespace("",NS)
C=lambda t:f"{{{NS}}}{t}"; I=lambda t:f"{{{INS}}}{t}"

tree=ET.parse(CAT); root=tree.getroot()
if root.get("revision")!="65": raise RuntimeError(f"R66 expected CAT65, got {root.get('revision')}")
if root.get("gameSystemRevision")!="15": raise RuntimeError(f"R66 expected GST15 dependency, got {root.get('gameSystemRevision')}")
baseline=collections.Counter(x.get("id") for x in root.iter() if x.get("id"))
ids={x.get("id"):x for x in root.iter() if x.get("id")}

CENT="hq-centurion"
OLDPKG="r57-ts-centurion-psychic-package"
ASSIGN="r62-shat-assign-2a678f656c73"
LEGION="legion-xv"
PSYKER_RULE="r64-ts-psyker-ml1"

for req in [CENT,OLDPKG,ASSIGN,PSYKER_RULE]:
    if req not in ids: raise RuntimeError("Missing required element "+req)

def qns(e): return e.tag.split("}")[0].strip("{")
def cont(p,tag,before=("constraints","categoryLinks","entryLinks","infoLinks","profiles","rules","selectionEntries","selectionEntryGroups","costs","modifiers")):
    q=C(tag); x=p.find(q)
    if x is not None:return x
    x=ET.Element(q); kids=list(p); idx=len(kids)
    for j,k in enumerate(kids):
        if k.tag.split("}")[-1] in before: idx=j; break
    p.insert(idx,x); return x
def cons(p,id_,typ,val,field="selections",scope="parent"):
    cs=cont(p,"constraints"); x=next((z for z in cs.findall(C("constraint")) if z.get("id")==id_),None)
    if x is None:x=ET.SubElement(cs,C("constraint"))
    x.attrib.update({"id":id_,"type":typ,"value":str(val),"field":field,"scope":scope,"shared":"true","includeChildSelections":"false","includeChildForces":"false"})
    return x
def modifier(p,id_,typ,field,value,conds):
    ms=cont(p,"modifiers"); x=next((z for z in ms.findall(C("modifier")) if z.get("id")==id_),None)
    if x is None:x=ET.SubElement(ms,C("modifier"))
    x.attrib.update({"id":id_,"type":typ,"field":field,"value":str(value)})
    for ch in list(x):x.remove(ch)
    target=ET.SubElement(x,C("conditions"))
    for c in conds:
        ET.SubElement(target,C("condition"),{
            "type":c.get("type","atLeast"),"value":str(c.get("value",1)),
            "field":"selections","scope":c.get("scope","roster"),"childId":c["childId"],
            "shared":"true","includeChildSelections":"true","includeChildForces":"false"
        })
    return x
def infolink(p,id_,name,target,hidden=False):
    ils=cont(p,"infoLinks"); x=next((z for z in ils.findall(C("infoLink")) if z.get("id")==id_),None)
    if x is None:x=ET.SubElement(ils,C("infoLink"))
    x.attrib.update({"id":id_,"name":name,"targetId":target,"type":"rule","hidden":"true" if hidden else "false"})
    return x
def deep_prefix(e,prefix):
    x=copy.deepcopy(e)
    olds=[z.get("id") for z in x.iter() if z.get("id")]
    mp={o:prefix+o for o in olds}
    for z in x.iter():
        oid=z.get("id")
        if oid in mp:z.set("id",mp[oid])
        for a in ("childId","field","targetId"):
            if z.get(a) in mp:z.set(a,mp[z.get(a)])
    return x
def unique_ids(e):
    seen=set()
    for z in e.iter():
        oid=z.get("id")
        if not oid:continue
        if oid in seen:raise RuntimeError(f"Duplicate ID inside clone: {oid}")
        seen.add(oid)

cent=ids[CENT]
old=ids[OLDPKG]
assign=ids[ASSIGN]

# Find the old package's direct container and remove it.
old_parent=next((p for p in root.iter() if old in list(p)),None)
if old_parent is None: raise RuntimeError("Old Centurion psychic package parent missing")
old_parent.remove(old)

# Build two clean packages from the proven R64 content.
normal=deep_prefix(old,"r66-ts-cent-normal-")
normal.set("id","r66-ts-centurion-normal-psychic-package")
normal.set("name","Thousand Sons — Prosperine Cult & Psychic Powers")
normal.set("hidden","true")
# Strip all inherited top-level visibility logic. The normal package uses one simple condition.
ms=normal.find(C("modifiers"))
if ms is not None:
    normal.remove(ms)
modifier(normal,"r66-ts-cent-normal-show","set","hidden","false",[{"childId":LEGION,"scope":"roster"}])
unique_ids(normal)

shat=deep_prefix(old,"r66-ts-cent-shat-")
shat.set("id","r66-ts-centurion-shattered-psychic-package")
shat.set("name","Prosperine Cult & Psychic Powers")
shat.set("hidden","false")
# The package is physically nested under the selected Thousand Sons assignment,
# so it needs NO sibling/root visibility conditions at all.
ms=shat.find(C("modifiers"))
if ms is not None:
    shat.remove(ms)
unique_ids(shat)

# Append normal package directly to Centurion.
cent_groups=cont(cent,"selectionEntryGroups",before=("costs","modifiers"))
cent_groups.append(normal)

# Append Shattered package directly inside the Thousand Sons assignment choice.
assign_groups=cont(assign,"selectionEntryGroups",before=("costs","modifiers"))
assign_groups.append(shat)

# Replace the old complicated Centurion Psyker info-link visibility.
old_link=next((x for x in cent.findall(f"./{C('infoLinks')}/{C('infoLink')}") if x.get("id")=="r64-ts-centurion-psyker-link"),None)
if old_link is not None:
    old_link.set("hidden","true")
    mods=old_link.find(C("modifiers"))
    if mods is not None:old_link.remove(mods)
    modifier(old_link,"r66-ts-cent-psyker-normal-show","set","hidden","false",[{"childId":LEGION,"scope":"roster"}])
else:
    old_link=infolink(cent,"r66-ts-centurion-psyker-normal","Psyker (Mastery Level 1)",PSYKER_RULE,True)
    modifier(old_link,"r66-ts-cent-psyker-normal-show","set","hidden","false",[{"childId":LEGION,"scope":"roster"}])

# Shattered TS assignment itself carries the Psyker rule, avoiding sibling visibility entirely.
# Remove any previous R66 duplicate if re-run against a local working copy.
ails=cont(assign,"infoLinks")
for x in list(ails):
    if x.get("id")=="r66-ts-centurion-shattered-psyker":ails.remove(x)
infolink(assign,"r66-ts-centurion-shattered-psyker","Psyker (Mastery Level 1)",PSYKER_RULE,False)

# Clean old package IDs should be completely gone.
# Revision.
root.set("revision","66")
tree.write(CAT,encoding="utf-8",xml_declaration=True)

ET.register_namespace("",INS)
it=ET.parse(IDX); ir=it.getroot()
for x in ir.iter(I("dataIndexEntry")):
    if x.get("filePath")=="Legiones Astartes.cat":x.set("dataRevision","66")
it.write(IDX,encoding="utf-8",xml_declaration=True)

# Validation.
rr=ET.parse(CAT).getroot(); rids={x.get("id"):x for x in rr.iter() if x.get("id")}; checks=[]
def ck(name,ok):
    checks.append((name,bool(ok)))
    if not ok:raise RuntimeError("R66 validation failed: "+name)

ck("CAT66",rr.get("revision")=="66")
ck("GST dependency remains15",rr.get("gameSystemRevision")=="15")
ck("Index66",'dataRevision="66"' in IDX.read_text(encoding="utf-8"))
ck("Old package root removed",OLDPKG not in rids)
ck("Normal package exists","r66-ts-centurion-normal-psychic-package" in rids)
ck("Shattered package exists","r66-ts-centurion-shattered-psychic-package" in rids)

n=rids["r66-ts-centurion-normal-psychic-package"]
s=rids["r66-ts-centurion-shattered-psychic-package"]

# The normal package has exactly one simple legion selector visibility dependency.
nxml=ET.tostring(n,encoding="unicode")
ck("Normal package keyed only to XV Legion",LEGION in nxml and "r62-shattered-theme" not in nxml and ASSIGN not in nxml)

# Shattered package is nested under the exact TS assignment choice and has no visibility modifiers.
pm={c:p for p in rr.iter() for c in p}
ck("Shattered package nested inside TS assignment",pm.get(s) is not None and pm.get(pm.get(s)) is not None and any(a.get("id")==ASSIGN for a in [pm.get(s),pm.get(pm.get(s))] if a is not None))
ck("Shattered package is not hidden",s.get("hidden")=="false")
ck("Shattered package has no visibility modifier",s.find(C("modifiers")) is None)

# Both packages contain all five Cult choices and each Cult contains an actual power group.
def cults(pkg):
    return [x for x in pkg.findall(f"./{C('selectionEntries')}/{C('selectionEntry')}") if any(k in (x.get("name") or "") for k in ["Pavoni","Raptora","Corvidae","Athanaeans","Pyrae"])]
for label,pkg in [("normal",n),("shattered",s)]:
    cs=cults(pkg)
    ck(label+" five Cults",len(cs)==5)
    for cult in cs:
        pgs=[g for g in cult.findall(f"./{C('selectionEntryGroups')}/{C('selectionEntryGroup')}") if "Psychic Powers" in (g.get("name") or "")]
        ck(label+" "+(cult.get("name") or "")+" has power group",len(pgs)==1)
        ck(label+" "+(cult.get("name") or "")+" power choices",len(pgs[0].findall(f"./{C('entryLinks')}/{C('entryLink')}"))>=7)

# Normal root and Shattered assignment each carry the ML1 rule in their appropriate place.
rc=rids[CENT]; ra=rids[ASSIGN]
ck("Normal Centurion ML1 link present",any(x.get("targetId")==PSYKER_RULE for x in rc.findall(f"./{C('infoLinks')}/{C('infoLink')}")))
ck("Shattered TS assignment ML1 link present",any(x.get("targetId")==PSYKER_RULE for x in ra.findall(f"./{C('infoLinks')}/{C('infoLink')}")))

new=collections.Counter(x.get("id") for x in rr.iter() if x.get("id"))
worse={k:v for k,v in new.items() if v>max(1,baseline.get(k,0))}
ck("No new/worsened duplicate IDs",not worse)

OUT.write_text("\n".join([
"Live R66 — Thousand Sons Centurion psychic UI repair",
"Input CAT=65/GST=15 -> CAT=66/GST remains 15","",
"FIX:",
"- Removed the old Centurion psychic package whose visibility depended on both roster Legion and a sibling Shattered-Legion assignment.",
"- Normal Thousand Sons Centurions now use a direct Cult + Psychic Powers package with one simple XV-Legion visibility condition.",
"- Shattered Legions Centurions assigned to Thousand Sons now receive the entire Cult + Psychic Powers package INSIDE the selected Thousand Sons assignment itself.",
"- Shattered Thousand Sons assignment also directly carries Psyker (Mastery Level 1), so it no longer depends on a sibling visibility calculation.",
"- Five Cult packages retained: Pavoni/Biomancy, Raptora/Telekinesis, Corvidae/Divination, Athanaeans/Telepathy, Pyrae/Pyromancy.",
"- Each Cult retains its actual correlated power list; normal Centurion selects one power, Librarian Epistolary scaling remains inside the copied package.",
"- No Veteran/melee logic changed in R66.","",
"VALIDATION:"
]+[f'- {"PASS" if ok else "FAIL"}: {name}' for name,ok in checks])+"\n",encoding="utf-8")
print(OUT.read_text())
