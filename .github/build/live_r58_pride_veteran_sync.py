from pathlib import Path
import copy, collections, hashlib, xml.etree.ElementTree as ET

CAT=Path("Legiones Astartes.cat"); IDX=Path("index.xml")
OUT=Path("inspection-live-r58-pride-veteran-sync.txt")
NS="http://www.battlescribe.net/schema/catalogueSchema"; INS="http://www.battlescribe.net/schema/dataIndexSchema"
ET.register_namespace("",NS)
C=lambda t:f"{{{NS}}}{t}"; I=lambda t:f"{{{INS}}}{t}"

tree=ET.parse(CAT); root=tree.getroot()
if root.get("revision")!="57": raise RuntimeError(f"R58 expected CAT57, got {root.get('revision')}")
if root.get("gameSystemRevision")!="14": raise RuntimeError(f"R58 expected GST14 dependency, got {root.get('gameSystemRevision')}")
baseline_ids=collections.Counter(e.get("id") for e in root.iter() if e.get("id"))

ids={e.get("id"):e for e in root.iter() if e.get("id")}
BASE="veteran-unit"; PRIDE="r35-pride-veteran-veteran-unit"
base=ids.get(BASE); old=ids.get(PRIDE)
if base is None or old is None: raise RuntimeError("Base/Pride Veteran entry missing")

# Preserve ONLY the things which are supposed to differ because this is a FOC-shift copy:
# - root ID (external references depend on it)
# - Troops/helper category links
# - hidden state + Pride visibility modifier
old_categories=copy.deepcopy(old.find(C("categoryLinks")))
old_modifiers=copy.deepcopy(old.find(C("modifiers")))
old_hidden=old.get("hidden","true")

# Deep-copy the CURRENT live Veteran Squad. Remap every internal ID so the copy is
# self-contained while references to shared/global targets remain shared.
cp=copy.deepcopy(base)
internal_ids={e.get("id") for e in cp.iter() if e.get("id")}
idmap={}
for oid in internal_ids:
    if oid==BASE:
        idmap[oid]=PRIDE
    else:
        idmap[oid]="r58-pride-sync-"+hashlib.sha1(oid.encode()).hexdigest()[:16]

for e in cp.iter():
    oid=e.get("id")
    if oid in idmap: e.set("id",idmap[oid])
    for attr in ("childId","field","targetId"):
        v=e.get(attr)
        if v in idmap: e.set(attr,idmap[v])

cp.set("id",PRIDE)
cp.set("name","Legion Veteran Squad")
cp.set("hidden",old_hidden)

# Replace the base Elites category with the old Pride Troops/helper categories.
cur=cp.find(C("categoryLinks"))
if cur is not None: cp.remove(cur)
if old_categories is not None:
    # Its link IDs were already unique in the live catalogue and belong to the Pride root.
    cp.insert(0,old_categories)

# Replace root-level modifiers with the old Pride visibility gate.
cur=cp.find(C("modifiers"))
if cur is not None: cp.remove(cur)
if old_modifiers is not None:
    cp.append(old_modifiers)

# Put it back at the exact same top-level position.
container=root.find(C("selectionEntries"))
if container is None: raise RuntimeError("Root selectionEntries missing")
pos=list(container).index(old)
container.remove(old)
container.insert(pos,cp)

# Revision/index.
root.set("revision","58")
tree.write(CAT,encoding="utf-8",xml_declaration=True)
ET.register_namespace("",INS)
it=ET.parse(IDX); ir=it.getroot()
for x in ir.iter(I("dataIndexEntry")):
    if x.get("filePath")=="Legiones Astartes.cat": x.set("dataRevision","58")
it.write(IDX,encoding="utf-8",xml_declaration=True)

# Validation.
rr=ET.parse(CAT).getroot(); rids={e.get("id"):e for e in rr.iter() if e.get("id")}; checks=[]
def ck(name,ok):
    checks.append((name,bool(ok)))
    if not ok: raise RuntimeError("R58 validation failed: "+name)

ck("CAT revision 58",rr.get("revision")=="58")
ck("GST dependency remains 14",rr.get("gameSystemRevision")=="14")
ck("Index CAT58",'dataRevision="58"' in IDX.read_text(encoding="utf-8"))

pv=rids[PRIDE]; bv=rids[BASE]
ck("Pride Veteran hidden by default",pv.get("hidden")=="true")
pvcats=pv.findall(f"./{C('categoryLinks')}/{C('categoryLink')}")
ck("Pride Veteran is Troops primary",any(x.get("targetId")=="cat-troops" and x.get("primary")=="true" for x in pvcats))
ck("Pride Veteran is not Elites primary",not any(x.get("targetId")=="cat-elites" and x.get("primary")=="true" for x in pvcats))
pmods=ET.tostring(pv.find(C("modifiers")),encoding="unicode") if pv.find(C("modifiers")) is not None else ""
ck("Pride Veteran gated by Pride of the Legion","rite-pride" in pmods)

# The entire selectable structure should now match the current base Veteran by names,
# modulo internal IDs and the root FOC category.
def direct_names(e,tag):
    p=e.find(C(tag))
    return [] if p is None else [(x.tag.split("}")[-1],x.get("name")) for x in list(p)]
ck("Direct model/upgrades mirror base",direct_names(pv,"selectionEntries")==direct_names(bv,"selectionEntries"))
ck("Direct option groups mirror base",direct_names(pv,"selectionEntryGroups")==direct_names(bv,"selectionEntryGroups"))
ck("Direct entry links mirror base",direct_names(pv,"entryLinks")==direct_names(bv,"entryLinks"))

# Find groups by name on each tree.
def group_by_name(e,name):
    return next((g for g in e.iter(C("selectionEntryGroup")) if g.get("name")==name),None)

bm=group_by_name(bv,"Close Combat Weapon Replacements")
pm=group_by_name(pv,"Close Combat Weapon Replacements")
ck("Pride melee group exists",pm is not None)
bcons=next(x for x in bm.findall(f"./{C('constraints')}/{C('constraint')}") if x.get("type")=="max")
pcons=next(x for x in pm.findall(f"./{C('constraints')}/{C('constraint')}") if x.get("type")=="max")
ck("Pride melee base max matches current Veteran",pcons.get("value")==bcons.get("value")=="1")
pmtxt=ET.tostring(pm,encoding="unicode")
# Current live Veteran model count: 4-9 ordinary Veterans + Sergeant = 5-10 total.
pincluded=next(e for e in pv.findall(f"./{C('selectionEntries')}/{C('selectionEntry')}") if e.get("name")=="Legion Veterans")
ck("Pride ordinary Veterans still 4-9",
   any(x.get("type")=="min" and x.get("value")=="4" for x in pincluded.findall(f"./{C('constraints')}/{C('constraint')}")) and
   any(x.get("type")=="max" and x.get("value")=="9" for x in pincluded.findall(f"./{C('constraints')}/{C('constraint')}")))
ck("Pride melee scales from current model selector",pincluded.get("id") in pmtxt and 'value="1"' in pmtxt)

# Important TS package: FOC shift must NOT delete legal unit options.
allnames=[e.get("name") or "" for e in pv.iter()]
ck("Pride keeps Brotherhood of Psykers",any("Brotherhood of Psykers (Mastery Level 1)"==n for n in allnames))
ck("Pride keeps Fellowships Brotherhood price",any("Brotherhood of Psykers (Fellowships price)"==n for n in allnames))
ck("Pride keeps Prosperine Cult",any(n=="Prosperine Cult" for n in allnames))
ck("Pride keeps Psychic Brotherhood powers",any(n=="Psychic Brotherhood — Psychic Powers" for n in allnames))
ck("Pride keeps Psychic Brotherhood disciplines",any(n=="Psychic Brotherhood — Psychic Discipline(s)" for n in allnames))

# Other key option families which stale FOC clones had previously lost/desynced.
for nm in ["Veteran Tactic (choose one)","Bolter Replacements","Individual Wargear",
           "Specialist Weapons (1 per 5 models)","Squad Equipment",
           "Legion Veteran Sergeant — Additional Armoury (max 50 pts)"]:
    ck("Pride keeps "+nm,group_by_name(pv,nm) is not None)

# No new/worsened duplicate IDs.
new_ids=collections.Counter(e.get("id") for e in rr.iter() if e.get("id"))
worse={k:v for k,v in new_ids.items() if v>max(1,baseline_ids.get(k,0))}
if worse: print("R58_DUPLICATES",worse)
ck("No new/worsened duplicate IDs",not worse)

OUT.write_text("\n".join([
"Live R58 — Pride Veteran full-sync fix",
"Input CAT57/GST14 -> CAT58/GST14","",
"ARCHITECTURE RULE:",
"- A Rite/Theme FOC shift changes only category/visibility unless the written rule explicitly changes the unit.",
"- The Pride of the Legion Veteran Troops entry is now rebuilt directly from the current live Legion Veteran Squad rather than maintained as an independent stale clone.","",
"FIX:",
"- Pride Veteran remains a conditional Troops choice under Pride of the Legion.",
"- Every current Veteran option is preserved: unit size, Veteran Tactics, melee/ranged replacements, specialist weapons, individual wargear, squad equipment, Sergeant Armoury, transports and Legion-specific upgrades.",
"- Close Combat Weapon Replacements now use the same live dynamic scaling as the base Veteran Squad: 5 models -> up to 5 replacements; 10 models -> up to 10.",
"- Thousand Sons Brotherhood of Psykers, Prosperine Cult, discipline and power access are retained because the source does not remove them when Veterans change FOC slot.",
"- Fellowships of Prospero still changes the Brotherhood price from +25 to +15 normally.","",
"VALIDATION:"
]+[f'- {"PASS" if ok else "FAIL"}: {n}' for n,ok in checks])+"\n",encoding="utf-8")
print(OUT.read_text())
