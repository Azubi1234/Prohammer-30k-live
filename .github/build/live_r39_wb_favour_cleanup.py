from pathlib import Path
import xml.etree.ElementTree as ET

CAT=Path("Legiones Astartes.cat")
IDX=Path("index.xml")
OUT=Path("inspection-live-r39-wb-favour-cleanup.txt")

CNS="http://www.battlescribe.net/schema/catalogueSchema"
INS="http://www.battlescribe.net/schema/dataIndexSchema"
ET.register_namespace("",CNS)
C=lambda t:f"{{{CNS}}}{t}"
I=lambda t:f"{{{INS}}}{t}"

tree=ET.parse(CAT)
root=tree.getroot()
if root.get("revision")!="38":
    raise RuntimeError(f"R39 expected CAT revision 38, got {root.get('revision')}")

legacy_ids={
    "r47-wb-favour-aura",
    "r47-wb-favour-mutation",
    "r47-wb-favour-strength",
    "r47-wb-favour-wings",
    "r47-wb-favour-visage",
}

# Remove every link to the obsolete shared Wargear versions.
removed_links=[]
for parent in root.iter():
    for child in list(parent):
        if child.tag==C("entryLink") and child.get("targetId") in legacy_ids:
            removed_links.append((child.get("id"),child.get("name"),child.get("targetId")))
            parent.remove(child)

# Remove the obsolete sharedSelectionEntries themselves.
sse=root.find(C("sharedSelectionEntries"))
removed_entries=[]
if sse is not None:
    for e in list(sse):
        if e.get("id") in legacy_ids:
            removed_entries.append((e.get("id"),e.get("name")))
            sse.remove(e)

# Validate the intended dedicated Favour groups remain.
groups={g.get("id"):g for g in root.iter(C("selectionEntryGroup")) if g.get("id")}
required_groups={
    "r37-wb-favour-hq-praetor",
    "r37-wb-favour-hq-centurion",
}
missing=required_groups-set(groups)
if missing:
    raise RuntimeError("Dedicated Favour group missing: "+", ".join(sorted(missing)))

# Validate each dedicated group still has the five options.
expected={"Daemonic Aura","Daemonic Mutation","Daemonic Strength","Daemonic Wings","Daemonic Visage"}
dedicated={}
for gid in required_groups:
    names={e.get("name") for e in groups[gid].findall(f"./{C('selectionEntries')}/{C('selectionEntry')}")}
    dedicated[gid]=names
    if names != expected:
        raise RuntimeError(f"{gid} options differ: {sorted(names)}")

# Bump catalogue only; GST remains revision 4.
root.set("revision","39")
tree.write(CAT,encoding="utf-8",xml_declaration=True)

ET.register_namespace("",INS)
it=ET.parse(IDX); ir=it.getroot()
for x in ir.iter(I("dataIndexEntry")):
    if x.get("filePath")=="Legiones Astartes.cat":
        x.set("dataRevision","39")
it.write(IDX,encoding="utf-8",xml_declaration=True)

# Final parse/check.
rr=ET.parse(CAT).getroot()
all_ids={e.get("id") for e in rr.iter() if e.get("id")}
remaining_links=[
    (e.get("id"),e.get("targetId"))
    for e in rr.iter(C("entryLink"))
    if e.get("targetId") in legacy_ids
]
checks=[
    ("Catalogue revision 39",rr.get("revision")=="39"),
    ("Obsolete shared Favour entries removed",not (legacy_ids & all_ids)),
    ("No links target obsolete Favour entries",not remaining_links),
    ("Praetor dedicated Favour group retained","r37-wb-favour-hq-praetor" in all_ids),
    ("Centurion dedicated Favour group retained","r37-wb-favour-hq-centurion" in all_ids),
    ("Index advertises CAT 39",'dataRevision="39"' in IDX.read_text(encoding="utf-8")),
]
failed=[n for n,ok in checks if not ok]
if failed:
    raise RuntimeError("R39 validation failed: "+"; ".join(failed))

lines=[
    "Live R39 — Word Bearers Favour of the Pantheon display cleanup",
    "Input CAT=38 -> CAT=39; GST remains revision 4",
    "",
    "CHANGES:",
    f"- Removed {len(removed_entries)} obsolete shared Favour of the Pantheon Wargear entries.",
    f"- Removed {len(removed_links)} links to those obsolete Wargear entries.",
    "- Retained the dedicated Favour of the Pantheon selector under Word Bearers Praetors and Centurions.",
    "- No rules, points or eligibility of the dedicated Favour selector were changed.",
    "",
    "REMOVED SHARED ENTRIES:",
]
lines += [f"- {i}: {n}" for i,n in removed_entries]
lines += ["","VALIDATION:"]
lines += [f'- {"PASS" if ok else "FAIL"}: {n}' for n,ok in checks]
OUT.write_text("\n".join(lines)+"\n",encoding="utf-8")
print(OUT.read_text())
