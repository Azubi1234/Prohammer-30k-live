from pathlib import Path
import xml.etree.ElementTree as ET, collections, subprocess, re

CAT=Path("Legiones Astartes.cat"); IDX=Path("index.xml")
OUT=Path("inspection-live-r52-loader-structure-repair.txt")
NS="http://www.battlescribe.net/schema/catalogueSchema"; INS="http://www.battlescribe.net/schema/dataIndexSchema"
ET.register_namespace("",NS)
C=lambda t:f"{{{NS}}}{t}"; I=lambda t:f"{{{INS}}}{t}"

tree=ET.parse(CAT); root=tree.getroot()
if root.get("revision")!="51": raise RuntimeError(f"R52 expected CAT51, got {root.get('revision')}")
if root.get("gameSystemRevision")!="11": raise RuntimeError("R52 expected GST dependency 11")
baseline_ids=collections.Counter(e.get("id") for e in root.iter() if e.get("id"))
ids={e.get("id"):e for e in root.iter() if e.get("id")}

# BattleScribe 2.03 direct-child order for SelectionEntry:
# modifiers, modifierGroups, constraints, profiles, rules, infoGroups, infoLinks,
# categoryLinks, selectionEntries, selectionEntryGroups, entryLinks, costs.
ORDER={
 "modifiers":0,"modifierGroups":1,"constraints":2,"profiles":3,"rules":4,
 "infoGroups":5,"infoLinks":6,"categoryLinks":7,"selectionEntries":8,
 "selectionEntryGroups":9,"entryLinks":10,"costs":11
}
def reorder_selection_entry(e):
    kids=list(e)
    unknown=[k.tag.split("}")[-1] for k in kids if k.tag.split("}")[-1] not in ORDER]
    if unknown: raise RuntimeError(f"Unknown SelectionEntry children on {e.get('id')}: {unknown}")
    ordered=sorted(enumerate(kids), key=lambda pair:(ORDER[pair[1].tag.split("}")[-1]], pair[0]))
    for k in kids:e.remove(k)
    for _,k in ordered:e.append(k)

targets=["r32-soh-maloghurst-replacement","r32-soh-torgaddon-upgrade"]
before={}
after={}
for tid in targets:
    e=ids.get(tid)
    if e is None: raise RuntimeError("Missing loader repair target "+tid)
    before[tid]=[x.tag.split("}")[-1] for x in e]
    reorder_selection_entry(e)
    after[tid]=[x.tag.split("}")[-1] for x in e]

# Revision/index
root.set("revision","52")
tree.write(CAT,encoding="utf-8",xml_declaration=True)
ET.register_namespace("",INS)
it=ET.parse(IDX); ir=it.getroot()
for x in ir.iter(I("dataIndexEntry")):
    if x.get("filePath")=="Legiones Astartes.cat":x.set("dataRevision","52")
it.write(IDX,encoding="utf-8",xml_declaration=True)

# Core static validation.
rr=ET.parse(CAT).getroot(); rids={e.get("id"):e for e in rr.iter() if e.get("id")}; checks=[]
def ck(n,o):
    checks.append((n,bool(o)))
    if not o: raise RuntimeError("R52 validation failed: "+n)
ck("CAT52",rr.get("revision")=="52")
ck("GST dependency remains 11",rr.get("gameSystemRevision")=="11")
ck("Index52",'dataRevision="52"' in IDX.read_text(encoding="utf-8"))
for tid in targets:
    seq=[x.tag.split("}")[-1] for x in rids[tid]]
    vals=[ORDER[x] for x in seq]
    ck(tid+" direct children schema ordered",vals==sorted(vals))

# Link target integrity (CAT/GST ids)
g=ET.parse("Prohammer 30k.gst").getroot()
allids=set(rids)|{e.get("id") for e in g.iter() if e.get("id")}
bad_entry=[];bad_info=[];bad_cat=[]
for e in rr.iter(C("entryLink")):
    if e.get("targetId") and e.get("targetId") not in allids:bad_entry.append((e.get("id"),e.get("targetId")))
for e in rr.iter(C("infoLink")):
    if e.get("targetId") and e.get("targetId") not in allids:bad_info.append((e.get("id"),e.get("targetId")))
for e in rr.iter(C("categoryLink")):
    if e.get("targetId") and e.get("targetId") not in allids:bad_cat.append((e.get("id"),e.get("targetId")))
ck("No unresolved entryLink targets",not bad_entry)
ck("No unresolved infoLink targets",not bad_info)
ck("No unresolved categoryLink targets",not bad_cat)

new_ids=collections.Counter(e.get("id") for e in rr.iter() if e.get("id"))
worse={k:v for k,v in new_ids.items() if v>max(1,baseline_ids.get(k,0))}
ck("No new/worsened duplicate IDs",not worse)

OUT.write_text("\n".join([
"Live R52 — New Recruit loader structure repair",
"Input CAT=51/GST=11 -> CAT=52/GST remains 11","",
"REPAIR:",
f"- Maloghurst direct children: {before[targets[0]]} -> {after[targets[0]]}",
f"- Tarik Torgaddon direct children: {before[targets[1]]} -> {after[targets[1]]}",
"- These were the only two official-schema error types/counts newly introduced after known-working R47.",
"- Reordered them to the official BattleScribe 2.03 SelectionEntry sequence without changing their rules, profiles, costs, or options.",
"- R49/R50/R51 content, including Shattered Legions work and the Moritat pistol selector, is otherwise untouched.","",
"VALIDATION:"
]+[f'- {"PASS" if ok else "FAIL"}: {n}' for n,ok in checks])+"\n",encoding="utf-8")
print(OUT.read_text())
