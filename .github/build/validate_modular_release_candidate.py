from pathlib import Path
import xml.etree.ElementTree as ET,json,collections
CNS="http://www.battlescribe.net/schema/catalogueSchema";INS="http://www.battlescribe.net/schema/dataIndexSchema";C=lambda t:f"{{{CNS}}}{t}";I=lambda t:f"{{{INS}}}{t}"
D=Path("modular-catalogues-generated");files=sorted(D.glob("*.cat"));assert len(files)==19
cats={p.name:ET.parse(p).getroot() for p in files};generic=cats["Legiones-Astartes-Generic.cat"]
problems=[]
if generic.get("library")!="true":problems.append("Generic Astartes is not library=true")
gids={x.get("id") for x in generic.iter() if x.get("id")}
# catalogue IDs unique
cids=[r.get("id") for r in cats.values()]
if len(cids)!=len(set(cids)):problems.append("Duplicate catalogue IDs")
# all 18 Legion links exactly once to Generic
for n,r in cats.items():
 if n=="Legiones-Astartes-Generic.cat":continue
 ls=[x for x in r.iter(C("catalogueLink")) if x.get("targetId")==generic.get("id")]
 if len(ls)!=1:problems.append(f"{n}: Generic links={len(ls)}")
# Primarch Chosen generic coverage
for eid in ("veteran-unit","terminator-unit"):
 e=next((x for x in generic.iter(C("selectionEntry")) if x.get("id")==eid),None)
 if e is None:problems.append(f"missing {eid}");continue
 pcs=[x for x in e.iter(C("categoryLink")) if x.get("targetId")=="cat-troops" and "primarch" in (x.get("name") or "").casefold()]
 if len(pcs)!=1:problems.append(f"{eid}: PC troops links={len(pcs)}")
# index checks
idx=ET.parse("index-modular-staging.xml").getroot();entries=list(idx.find(I("dataIndexEntries")))
paths={e.get("filePath") for e in entries}
for p in files:
 fp="modular-catalogues-generated/"+p.name
 if fp not in paths:problems.append("index missing "+fp)
# no duplicate element IDs within each file
for n,r in cats.items():
 ids=[x.get("id") for x in r.iter() if x.get("id")]
 dup=[k for k,v in collections.Counter(ids).items() if v>1]
 if dup:problems.append(f"{n}: duplicate element IDs {dup[:10]}")
report={"catalogues":len(files),"legions":18,"generic_library":generic.get("library"),"index_entries":len(entries),"problems":problems}
Path("modular-release-candidate-audit.json").write_text(json.dumps(report,indent=2));print(json.dumps(report,indent=2))
if problems:raise SystemExit(1)
