from pathlib import Path
import glob,json,re,xml.etree.ElementTree as ET,collections

SRC=Path("Legiones Astartes.cat")
GST=Path("Prohammer 30k.gst")
GEN=Path("modular-catalogues-generated")
OUT=Path("modular-reference-audit.json")
CNS="http://www.battlescribe.net/schema/catalogueSchema"
GNS="http://www.battlescribe.net/schema/gameSystemSchema"
C=lambda t:f"{{{CNS}}}{t}"

src=ET.parse(SRC).getroot(); gst=ET.parse(GST).getroot()
src_ids={x.get("id") for x in src.iter() if x.get("id")}
gst_ids={x.get("id") for x in gst.iter() if x.get("id")}

files=sorted(p for p in GEN.glob("*.cat") if p.name!="Legiones-Astartes-Generic.cat")
if len(files)!=18:raise RuntimeError(f"Expected 18 Legion catalogues, got {len(files)}")

cats={}
id_owners=collections.defaultdict(set)
for f in files:
    r=ET.parse(f).getroot(); cats[f.name]=r
    for x in r.iter():
        if x.get("id"):id_owners[x.get("id")].add(f.name)

# IDs that appear in multiple Legion catalogues are expected only for copied
# game-system metadata. Selection/rule/profile ownership should be unique.
interesting_tags={"selectionEntry","selectionEntryGroup","rule","profile"}
duplicate_owned=[]
for iid,owners in id_owners.items():
    if len(owners)<2:continue
    sample=None
    for r in cats.values():
        sample=next((x for x in r.iter() if x.get("id")==iid),None)
        if sample is not None:break
    tag=sample.tag.split("}")[-1] if sample is not None else ""
    if tag in interesting_tags:duplicate_owned.append({"id":iid,"owners":sorted(owners),"tag":tag,"name":sample.get("name")})

reports={}
attrs=("targetId","childId")
SCHEMA_TOKENS={"model","unit","upgrade","parent","root-entry","roster","force","self"}
for fname,r in cats.items():
    local={x.get("id") for x in r.iter() if x.get("id")}
    valid_local=valid_generic=valid_gst=0
    unresolved=[];cross_legion=[]
    for x in r.iter():
        for a in attrs:
            tid=x.get(a)
            if not tid or tid in SCHEMA_TOKENS:continue
            if tid in local:
                valid_local+=1;continue
            other=sorted(id_owners.get(tid,set())-{fname})
            if other:
                cross_legion.append({"from_id":x.get("id"),"from_name":x.get("name"),"attribute":a,"target":tid,"other_legions":other})
                continue
            if tid in src_ids:
                valid_generic+=1;continue
            if tid in gst_ids:
                valid_gst+=1;continue
            # Some fields/condition IDs are intentionally local constraint IDs
            # and can be external to the generated owned subset. Record all for review.
            anc=x
            # Find the nearest meaningful selection object for diagnostics.
            pm={ch:pa for pa in r.iter() for ch in pa}
            while anc is not None and anc.tag.split("}")[-1] not in ("selectionEntry","selectionEntryGroup","entryLink"):
                anc=pm.get(anc)
            unresolved.append({"from_id":x.get("id"),"from_name":x.get("name"),"tag":x.tag.split("}")[-1],
                               "attribute":a,"target":tid,
                               "owner_id":anc.get("id") if anc is not None else None,
                               "owner_name":anc.get("name") if anc is not None else None})
    reports[fname]={"local":valid_local,"generic_parent":valid_generic,"game_system":valid_gst,
                    "cross_legion_count":len(cross_legion),"unresolved_count":len(unresolved),
                    "cross_legion":cross_legion[:500],"unresolved":unresolved[:500]}

summary={"files":len(files),"duplicate_owned_count":len(duplicate_owned),
         "cross_legion_total":sum(x["cross_legion_count"] for x in reports.values()),
         "unresolved_total":sum(x["unresolved_count"] for x in reports.values())}
OUT.write_text(json.dumps({"summary":summary,"duplicate_owned":duplicate_owned,"catalogues":reports},indent=2,ensure_ascii=False)+"\n",encoding="utf-8")
print(json.dumps(summary,indent=2))
for f,x in reports.items():print(f, "cross",x["cross_legion_count"],"unresolved",x["unresolved_count"],"generic",x["generic_parent"])
