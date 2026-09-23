from pathlib import Path
import xml.etree.ElementTree as ET,collections,json
NS="http://www.battlescribe.net/schema/catalogueSchema";C=lambda t:f"{{{NS}}}{t}"
D=Path("modular-catalogues-generated");fs=list(D.glob("*.cat"))
assert len(fs)==19,len(fs)
roots={p.name:ET.parse(p).getroot() for p in fs}
generic=roots["Legiones-Astartes-Generic.cat"];gid=generic.get("id")
problems=[]
for n,r in roots.items():
    if n=="Legiones-Astartes-Generic.cat":continue
    links=r.find(C("catalogueLinks"))
    hits=[] if links is None else [x for x in links.findall(C("catalogueLink")) if x.get("targetId")==gid]
    if len(hits)!=1:problems.append(f"{n}: generic links={len(hits)}")
# Verify Legion-owned root IDs don't leak into generic library.
generic_ids={x.get("id") for x in generic.iter() if x.get("id")}
legion_root_ids=set()
containers=("sharedSelectionEntries","sharedSelectionEntryGroups","sharedRules","sharedProfiles","selectionEntries","selectionEntryGroups","rules","profiles")
for n,r in roots.items():
    if n=="Legiones-Astartes-Generic.cat":continue
    for cname in containers:
        c=r.find(C(cname))
        if c is not None:
            legion_root_ids|={x.get("id") for x in list(c) if x.get("id")}
leaks=sorted(generic_ids & legion_root_ids)
print(json.dumps({"catalogues":len(fs),"generic_id":gid,"link_problems":problems,"legion_root_leaks":len(leaks)},indent=2))
if problems or leaks:raise SystemExit(1)
