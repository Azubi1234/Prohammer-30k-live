from pathlib import Path
import collections, xml.etree.ElementTree as ET

CAT=Path("Legiones Astartes.cat"); IDX=Path("index.xml")
OUT=Path("inspection-live-r49-schema-entrylink-repair.txt")
NS="http://www.battlescribe.net/schema/catalogueSchema"; INS="http://www.battlescribe.net/schema/dataIndexSchema"
ET.register_namespace("",NS)
C=lambda t:f"{{{NS}}}{t}"; I=lambda t:f"{{{INS}}}{t}"

tree=ET.parse(CAT); root=tree.getroot()
if root.get("revision")!="48": raise RuntimeError(f"R49 expected CAT48, got {root.get('revision')}")
if root.get("gameSystemRevision")!="11": raise RuntimeError(f"R49 expected GST dependency 11, got {root.get('gameSystemRevision')}")
baseline=collections.Counter(x.get("id") for x in root.iter() if x.get("id"))

def ensure_entrylinks(parent):
    box=parent.find(C("entryLinks"))
    if box is not None:return box
    box=ET.Element(C("entryLinks"))
    kids=list(parent)
    # BattleScribe catalogue order: constraints, categoryLinks, entryLinks,
    # infoLinks, profiles, rules, selectionEntries, selectionEntryGroups, costs, modifiers.
    before={"infoLinks","profiles","rules","selectionEntries","selectionEntryGroups","costs","modifiers"}
    idx=len(kids)
    for i,k in enumerate(kids):
        if k.tag.split("}")[-1] in before:
            idx=i;break
    parent.insert(idx,box)
    return box

# ---------------------------------------------------------------------------
# Repair R41 structural regression:
# entryLink elements were created *inside* selectionEntries containers.
# Move them to the proper entryLinks sibling under the same owning parent.
# ---------------------------------------------------------------------------
parent_map={c:p for p in root.iter() for c in p}
misplaced=[]
for sebox in list(root.iter(C("selectionEntries"))):
    owner=parent_map.get(sebox)
    if owner is None:continue
    links=[x for x in list(sebox) if x.tag==C("entryLink")]
    if not links:continue
    target=ensure_entrylinks(owner)
    existing={x.get("id") for x in target.findall(C("entryLink"))}
    for link in links:
        lid=link.get("id")
        if lid in existing:
            raise RuntimeError(f"Duplicate entryLink id while repairing {lid}")
        sebox.remove(link);target.append(link);existing.add(lid)
        misplaced.append((lid,link.get("name"),owner.get("id"),owner.get("name")))
    if len(list(sebox))==0:
        owner.remove(sebox)

# ---------------------------------------------------------------------------
# Explicit TS validation helpers.
# ---------------------------------------------------------------------------
ids={x.get("id"):x for x in root.iter() if x.get("id")}
def children(boxid,tag):
    e=ids.get(boxid)
    if e is None:return []
    box=e.find(C(tag))
    return list(box) if box is not None else []
def direct_links(boxid):
    return children(boxid,"entryLinks")
def direct_selections(boxid):
    return children(boxid,"selectionEntries")

ts_core_groups=[
"r45-cult-hq-praetor","r19-ts-praetor-disciplines","r19-ts-praetor-powers",
"r45-cult-hq-centurion","r19-ts-centurion-disciplines","r19-ts-centurion-powers",
"r45-cult-tactical-unit","r19-ts-tactical-brotherhood-disciplines","r19-ts-tactical-brotherhood-powers",
"r45-cult-veteran-unit","r19-ts-veteran-unit-brotherhood-disciplines","r19-ts-veteran-unit-brotherhood-powers",
"r45-cult-terminator-unit","r19-ts-terminator-unit-brotherhood-disciplines","r19-ts-terminator-unit-brotherhood-powers",
"r45-cult-r41-unit-xv-0-sekhmet-terminator-cabal","r19-ts-sekhmet-disciplines","r19-ts-sekhmet-powers",
"r45-cult-r41-unit-xv-2-ammitara-occult-intercession-cabal","r19-ts-ammitara-disciplines","r19-ts-ammitara-powers",
]

# Revision.
root.set("revision","49")
tree.write(CAT,encoding="utf-8",xml_declaration=True)
ET.register_namespace("",INS)
it=ET.parse(IDX); ir=it.getroot()
for x in ir.iter(I("dataIndexEntry")):
    if x.get("filePath")=="Legiones Astartes.cat":x.set("dataRevision","49")
it.write(IDX,encoding="utf-8",xml_declaration=True)

# ---------------------------------------------------------------------------
# Validation after serialisation.
# ---------------------------------------------------------------------------
rr=ET.parse(CAT).getroot(); rids={x.get("id"):x for x in rr.iter() if x.get("id")}; checks=[]
def ck(name,ok):
    checks.append((name,bool(ok)))
    if not ok:raise RuntimeError("R49 validation failed: "+name)

ck("CAT49",rr.get("revision")=="49")
ck("GST dependency remains 11",rr.get("gameSystemRevision")=="11")
ck("Index49",'dataRevision="49"' in IDX.read_text(encoding="utf-8"))

# No invalid container remains anywhere.
bad=[]
for box in rr.iter(C("selectionEntries")):
    for x in list(box):
        if x.tag!=C("selectionEntry"):
            bad.append((x.tag.split("}")[-1],x.get("id"),x.get("name")))
ck("Every selectionEntries container contains only selectionEntry",not bad)

# Conversely, entryLinks containers contain only entryLink.
bad2=[]
for box in rr.iter(C("entryLinks")):
    for x in list(box):
        if x.tag!=C("entryLink"):
            bad2.append((x.tag.split("}")[-1],x.get("id"),x.get("name")))
ck("Every entryLinks container contains only entryLink",not bad2)

# TS core groups must now have real visible link children.
expected_counts={
"r45-cult-hq-praetor":5,
"r19-ts-praetor-disciplines":5,
"r19-ts-praetor-powers":35,
"r45-cult-hq-centurion":5,
"r19-ts-centurion-disciplines":5,
"r19-ts-centurion-powers":35,
"r45-cult-tactical-unit":5,
"r19-ts-tactical-brotherhood-disciplines":5,
"r19-ts-tactical-brotherhood-powers":35,
"r45-cult-veteran-unit":5,
"r19-ts-veteran-unit-brotherhood-disciplines":5,
"r19-ts-veteran-unit-brotherhood-powers":35,
"r45-cult-terminator-unit":5,
"r19-ts-terminator-unit-brotherhood-disciplines":5,
"r19-ts-terminator-unit-brotherhood-powers":35,
"r45-cult-r41-unit-xv-0-sekhmet-terminator-cabal":5,
"r19-ts-sekhmet-disciplines":5,
"r19-ts-sekhmet-powers":35,
"r45-cult-r41-unit-xv-2-ammitara-occult-intercession-cabal":5,
"r19-ts-ammitara-disciplines":5,
"r19-ts-ammitara-powers":35,
}
for gid,n in expected_counts.items():
    g=rids.get(gid);ck(gid+" exists",g is not None)
    links=g.findall(f"./{C('entryLinks')}/{C('entryLink')}")
    ck(gid+f" has {n} proper entryLinks",len(links)==n)

# Verify cult -> discipline gating survived.
cult_map={
"Pavoni":"Biomancy","Raptora":"Telekinesis","Corvidae":"Divination","Athanaeans":"Telepathy","Pyrae":"Pyromancy"
}
for cult_gid,disc_gid in [
("r45-cult-hq-praetor","r19-ts-praetor-disciplines"),
("r45-cult-hq-centurion","r19-ts-centurion-disciplines"),
("r45-cult-veteran-unit","r19-ts-veteran-unit-brotherhood-disciplines"),
("r45-cult-terminator-unit","r19-ts-terminator-unit-brotherhood-disciplines"),
("r45-cult-r41-unit-xv-0-sekhmet-terminator-cabal","r19-ts-sekhmet-disciplines"),
]:
    cults={x.get("name"):x.get("id") for x in rids[cult_gid].findall(f"./{C('entryLinks')}/{C('entryLink')}")}
    discs={x.get("name"):x for x in rids[disc_gid].findall(f"./{C('entryLinks')}/{C('entryLink')}")}
    for cult,disc in cult_map.items():
        ck(f"{disc_gid} {disc} exists",disc in discs)
        txt=ET.tostring(discs[disc],encoding="unicode")
        ck(f"{disc_gid} {disc} gated by {cult}",cults[cult] in txt)

# Power links must target valid shared selections and be gated by discipline IDs.
for gid in ["r19-ts-praetor-powers","r19-ts-centurion-powers","r19-ts-sekhmet-powers"]:
    for l in rids[gid].findall(f"./{C('entryLinks')}/{C('entryLink')}"):
        ck(l.get("id")+" target resolves",l.get("targetId") in rids)
        txt=ET.tostring(l,encoding="unicode")
        ck(l.get("id")+" has discipline gate","-disc-" in txt or "disc-" in txt)

# Legion visibility still tied to XV.
for gid in ["r45-cult-hq-praetor","r45-cult-hq-centurion","r45-cult-tactical-unit","r45-cult-veteran-unit","r45-cult-terminator-unit"]:
    txt=ET.tostring(rids[gid],encoding="unicode")
    ck(gid+" XV-gated","legion-xv" in txt)

new=collections.Counter(x.get("id") for x in rr.iter() if x.get("id"))
worse={k:v for k,v in new.items() if v>max(1,baseline.get(k,0))}
ck("No new/worsened duplicate IDs",not worse)

ts_moved=[x for x in misplaced if any(s in ((x[2] or "")+" "+(x[3] or "")).lower() for s in ["ts-","cult","psychic","thousand","sek","ammitara"])]
OUT.write_text("\n".join([
"Live R49 — schema entryLink repair / Thousand Sons restore",
"Input CAT=48/GST=11 -> CAT=49/GST remains 11","",
"ROOT CAUSE:",
"- R41 universalisation converted compatible local selectionEntry nodes into entryLink nodes in place.",
"- Those links were left inside selectionEntries containers instead of being moved to entryLinks containers.",
"- XML parsing still succeeded, but New Recruit ignores entryLink elements in a selectionEntries container.",
"- Thousand Sons were hit especially hard because Cult, Discipline and Psychic Power selectors are mostly links.","",
"FIX:",
f"- Moved {len(misplaced)} misplaced entryLink elements across the catalogue into schema-correct entryLinks containers.",
f"- Of those, {len(ts_moved)} were in immediately identifiable Thousand Sons / psychic / Cult contexts.",
"- Existing IDs, target IDs, costs, constraints, Cult gates, discipline gates and power gates were preserved.",
"- Empty selectionEntries containers created by the move were removed.",
"- This is a structural repair only; it does not rebalance or rewrite any army rules.","",
"THOUSAND SONS:",
"- Praetor and Centurion Cult selectors restored.",
"- Tactical/Veteran/Terminator/Sekhmet/Ammitara Cult selectors restored.",
"- Cult-correlated Psychic Discipline selectors restored.",
"- Psychic Power selectors restored and remain gated by the selected discipline.",
"- Existing mapping remains Pavoni→Biomancy, Raptora→Telekinesis, Corvidae→Divination, Athanaeans→Telepathy, Pyrae→Pyromancy.","",
"VALIDATION:"
]+[f'- {"PASS" if ok else "FAIL"}: {name}' for name,ok in checks])+"\n",encoding="utf-8")
print(OUT.read_text())
