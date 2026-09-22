from pathlib import Path
import collections, xml.etree.ElementTree as ET

CAT=Path("Legiones Astartes.cat"); IDX=Path("index.xml")
OUT=Path("inspection-live-r51-load-repair.txt")
NS="http://www.battlescribe.net/schema/catalogueSchema"; INS="http://www.battlescribe.net/schema/dataIndexSchema"
ET.register_namespace("",NS)
C=lambda t:f"{{{NS}}}{t}"; I=lambda t:f"{{{INS}}}{t}"

tree=ET.parse(CAT); root=tree.getroot()
if root.get("revision")!="50":
    raise RuntimeError(f"R51 expected CAT50, got {root.get('revision')}")
if root.get("gameSystemRevision")!="11":
    raise RuntimeError(f"R51 expected GST dependency 11, got {root.get('gameSystemRevision')}")
baseline=collections.Counter(x.get("id") for x in root.iter() if x.get("id"))
ids={x.get("id"):x for x in root.iter() if x.get("id")}

# ---------------------------------------------------------------------------
# 1) Repair six live entryLinks exposed by the R49 container repair.
#    The old r44-if-transponder-unit was retired; current IF unit version is
#    r64-if-gear-trans-unit.
# ---------------------------------------------------------------------------
OLD_IF="r44-if-transponder-unit"
NEW_IF="r64-if-gear-trans-unit"
if NEW_IF not in ids:
    raise RuntimeError("Current Imperial Fists unit transponder entry missing")

repaired_if=[]
for e in root.iter(C("entryLink")):
    if e.get("targetId")==OLD_IF:
        repaired_if.append((e.get("id"),e.get("name")))
        e.set("targetId",NEW_IF)
if len(repaired_if)!=6:
    raise RuntimeError(f"Expected six stale IF transponder links, found {len(repaired_if)}")

# ---------------------------------------------------------------------------
# 2) Repair stale defaultSelectionEntryId values in cloned Tactical loadouts.
# ---------------------------------------------------------------------------
default_repairs={
    "r40-da-storm-tactical-tac-loadout":"r40-da-storm-tactical-load-standard",
    "r57-iw-hammer-tactical-tac-loadout":"r57-iw-hammer-tactical-load-standard",
}
for gid,child in default_repairs.items():
    g=ids.get(gid)
    if g is None: raise RuntimeError(f"Missing cloned loadout group {gid}")
    direct={x.get("id") for x in g.findall(f"./{C('selectionEntries')}/{C('selectionEntry')}")}
    if child not in direct:
        raise RuntimeError(f"{child} is not a direct selectionEntry of {gid}")
    g.set("defaultSelectionEntryId",child)

# ---------------------------------------------------------------------------
# 3) Repair Ahriman's Cabal repeat target.
# ---------------------------------------------------------------------------
OLD_AHR="live-r2-r41-unit-xv-6-ahzek-ahriman-retinue-0-hq-centurion-ret-command-champ-pw"
NEW_AHR="live-r2-r41-unit-xv-6-ahzek-ahriman-retinue-0-hq-centurion-ret-command-w-15"
if NEW_AHR not in ids:
    raise RuntimeError("Current Ahriman Command Squad Power Weapon link missing")
ahr_repeats=[]
for e in root.iter(C("repeat")):
    if e.get("field")=="selections" and e.get("childId")==OLD_AHR:
        e.set("childId",NEW_AHR); ahr_repeats.append(e)
if len(ahr_repeats)!=1:
    raise RuntimeError(f"Expected one stale Ahriman repeat, found {len(ahr_repeats)}")

# ---------------------------------------------------------------------------
# 4) Low-risk stale selection conditions with direct known replacements.
# ---------------------------------------------------------------------------
condition_map={
    "gear-hq-pair-claws":"gear-pair-claws",
    "r37-praetor-jetbike-rule":"r37-praetor-jetbike",
    "r37-centurion-jetbike-rule":"r37-centurion-jetbike",
}
for new in condition_map.values():
    if new not in ids: raise RuntimeError(f"Known replacement target missing: {new}")

condition_repairs=collections.Counter()
for e in root.iter(C("condition")):
    if e.get("field")!="selections": continue
    old=e.get("childId")
    if old in condition_map:
        e.set("childId",condition_map[old])
        condition_repairs[old]+=1

# ---------------------------------------------------------------------------
# Revision/index.
# ---------------------------------------------------------------------------
root.set("revision","51")
tree.write(CAT,encoding="utf-8",xml_declaration=True)

ET.register_namespace("",INS)
it=ET.parse(IDX); ir=it.getroot()
for x in ir.iter(I("dataIndexEntry")):
    if x.get("filePath")=="Legiones Astartes.cat":
        x.set("dataRevision","51")
it.write(IDX,encoding="utf-8",xml_declaration=True)

# ---------------------------------------------------------------------------
# Validation against current GST.
# ---------------------------------------------------------------------------
rr=ET.parse(CAT).getroot()
gg=ET.parse("Prohammer 30k.gst").getroot()
rids={x.get("id") for x in rr.iter() if x.get("id")}
gids={x.get("id") for x in gg.iter() if x.get("id")}
allids=rids|gids
checks=[]
def ck(name,ok):
    checks.append((name,bool(ok)))
    if not ok: raise RuntimeError("R51 validation failed: "+name)

ck("CAT51",rr.get("revision")=="51")
ck("GST dependency remains 11",rr.get("gameSystemRevision")=="11")
ck("Index51",'dataRevision="51"' in IDX.read_text(encoding="utf-8"))

# No unresolved entryLink/infoLink/categoryLink targets.
for tag,label in [(C("entryLink"),"entryLink"),(C("infoLink"),"infoLink"),(C("categoryLink"),"categoryLink")]:
    bad=[(e.get("id"),e.get("targetId")) for e in rr.iter(tag)
         if e.get("targetId") and e.get("targetId") not in allids]
    ck(f"No unresolved {label} targets",not bad)

# All group defaults resolve to a direct child selection/link.
baddefs=[]
for g in rr.iter(C("selectionEntryGroup")):
    d=g.get("defaultSelectionEntryId")
    if not d: continue
    direct={x.get("id") for x in g.findall(f"./{C('selectionEntries')}/{C('selectionEntry')}")}
    direct|={x.get("id") for x in g.findall(f"./{C('entryLinks')}/{C('entryLink')}")}
    if d not in direct: baddefs.append((g.get("id"),d))
ck("All defaultSelectionEntryId values resolve",not baddefs)

# Selection repeats must resolve.
badreps=[(e.get("childId"),e.get("scope")) for e in rr.iter(C("repeat"))
         if e.get("field")=="selections" and e.get("childId") and e.get("childId") not in allids]
ck("All selection-repeat targets resolve",not badreps)

# Structural R49 repair remains sound.
for boxname,childtag in [
    ("selectionEntries",C("selectionEntry")),
    ("entryLinks",C("entryLink")),
    ("selectionEntryGroups",C("selectionEntryGroup")),
    ("infoLinks",C("infoLink")),
]:
    bad=[]
    for box in rr.iter(C(boxname)):
        for x in list(box):
            if x.tag!=childtag: bad.append((boxname,x.tag,x.get("id")))
    ck(f"{boxname} contains only correct child type",not bad)

# Preserve the R50 Moritat structure.
allmap={x.get("id"):x for x in rr.iter() if x.get("id")}
mor=allmap.get("r29-mor-pair-group")
bolt=allmap.get("r29-mor-bolt")
ful=allmap.get("r47-rg-mor-fulcrum-pair")
ck("Moritat Pistol Pair exists",mor is not None)
ck("Moritat default remains Two Bolt Pistols",mor.get("defaultSelectionEntryId")=="r29-mor-bolt")
ck("Bolt Pistols remain replaceable","defaultAmount" not in bolt.attrib)
ck("Fulcrum pair remains present",ful is not None)
ck("Fulcrum pair remains +20",any(c.get("typeId")=="pts" and c.get("value")=="20"
                                      for c in ful.findall(f"./{C('costs')}/{C('cost')}")))

# Do not introduce/worsen duplicate IDs.
new=collections.Counter(x.get("id") for x in rr.iter() if x.get("id"))
worse={k:v for k,v in new.items() if v>max(1,baseline.get(k,0))}
ck("No new/worsened duplicate IDs",not worse)

OUT.write_text("\n".join([
    "Live R51 — catalogue load repair",
    "Input CAT=50/GST=11 -> CAT=51/GST remains 11","",
    "REPAIRS:",
    f"- Repointed {len(repaired_if)} stale live Imperial Fists Teleportation Transponder links from {OLD_IF} to {NEW_IF}.",
    "- Corrected Dark Angels Storm of War Tactical Squad default loadout to its cloned Bolters + Bolt Pistols child ID.",
    "- Corrected Iron Warriors Hammer compulsory Tactical Squad default loadout to its cloned Bolters + Bolt Pistols child ID.",
    "- Corrected Ahriman's Cabal Power Weapon repeat to the current Command Squad Power Weapon link.",
    f"- Repaired {sum(condition_repairs.values())} low-risk stale selection conditions: {dict(condition_repairs)}.",
    "- Preserved the R50 Moritat one-of pistol-pair/default/Fulcrum structure.","",
    "VALIDATION:"
]+[f'- {"PASS" if ok else "FAIL"}: {name}' for name,ok in checks])+"\n",encoding="utf-8")
print(OUT.read_text())
