from pathlib import Path
import json,re,xml.etree.ElementTree as ET,collections

CAT=Path("Legiones Astartes.cat")
OUT=Path("migration-audit")
NS="http://www.battlescribe.net/schema/catalogueSchema"
C=lambda t:f"{{{NS}}}{t}"

LEGIONS={
"I":"Dark Angels","III":"Emperor's Children","IV":"Iron Warriors","V":"White Scars",
"VI":"Space Wolves","VII":"Imperial Fists","VIII":"Night Lords","IX":"Blood Angels",
"X":"Iron Hands","XII":"World Eaters","XIII":"Ultramarines","XIV":"Death Guard",
"XV":"Thousand Sons","XVI":"Sons of Horus","XVII":"Word Bearers","XVIII":"Salamanders",
"XIX":"Raven Guard","XX":"Alpha Legion"}

root=ET.parse(CAT).getroot()
parent={c:p for p in root.iter() for c in p}
ids={x.get("id"):x for x in root.iter() if x.get("id")}

# Discover the authoritative 18 selectors rather than trusting display spelling.
cfg=ids.get("config-legion")
selectors={}
if cfg is not None:
    for e in cfg.iter(C("selectionEntry")):
        m=re.match(r"^([IVXLCDM]+)\s+Legion\s+[—-]\s+(.+)$",e.get("name") or "",re.I)
        if m: selectors[m.group(1).upper()]=(e.get("id"),m.group(2).strip())
if len(selectors)!=18:
    raise RuntimeError(f"Expected 18 Legion selectors, found {len(selectors)}: {selectors}")

selector_to_roman={v[0]:k for k,v in selectors.items()}
name_to_roman={v[1].casefold():k for k,v in selectors.items()}

def top_owner_node(x):
    cur=x
    while parent.get(cur) is not None and parent[cur] is not root:
        cur=parent[cur]
    return cur

def fixed_legion(x):
    names=[]
    for q in (C("rule"),C("infoLink")):
        for y in x.iter(q):
            n=y.get("name") or ""
            m=re.match(r"Legiones Astartes \((.+)\)",n)
            if m:names.append(m.group(1).strip())
    rs={name_to_roman[n.casefold()] for n in names if n.casefold() in name_to_roman}
    return next(iter(rs)) if len(rs)==1 else None

# Evidence is deliberately conservative. A node is Legion-owned only when it
# has direct fixed-Legion identity, lives beneath the canonical Legion selector,
# or uses a stable r41 unit ID carrying a Roman Legion number.
evidence=collections.defaultdict(set)
for roman,(sid,lname) in selectors.items():
    s=ids[sid]
    for x in s.iter():
        if x.get("id"): evidence[x.get("id")].add(roman)

for x in root.iter():
    xid=x.get("id")
    if not xid:continue
    fl=fixed_legion(x)
    if fl:evidence[xid].add(fl)
    m=re.match(r"r41-unit-([ivxlcdm]+)-",xid,re.I)
    if m and m.group(1).upper() in selectors:evidence[xid].add(m.group(1).upper())
    # Older Dark Angels package predates the r41 naming convention.
    if xid.startswith("da22-") or xid.startswith("r40-da-"):
        evidence[xid].add("I")

# Roll descendant evidence up to root-level catalogue objects. We do NOT
# automatically claim shared targets; cross references are reported separately.
buckets=collections.defaultdict(list)
ambiguous=[]
root_children=[]
for container_name in ("sharedSelectionEntries","sharedSelectionEntryGroups","sharedRules","sharedProfiles","selectionEntries","selectionEntryGroups","rules","profiles"):
    cont=root.find(C(container_name))
    if cont is None:continue
    for x in list(cont):
        xid=x.get("id")
        if not xid:continue
        # Ownership belongs to the root object itself. Nested conditions/options
        # referencing Legion selectors are dependencies, not ownership evidence.
        ev=set(evidence.get(xid,set()))
        rec={"id":xid,"name":x.get("name"),"tag":x.tag.split("}")[-1],"container":container_name}
        if len(ev)==1:
            roman=next(iter(ev));buckets[roman].append(rec)
        elif len(ev)>1:
            rec["legions"]=sorted(ev);ambiguous.append(rec)
        else:
            buckets["GENERIC"].append(rec)
        root_children.append((x,rec,ev))

# Cross-reference inventory: this is the important safety report before moving.
ownership={}
for roman,recs in buckets.items():
    for r in recs:ownership[r["id"]]=roman
for r in ambiguous:ownership[r["id"]]="AMBIGUOUS"

refs=[]
attrs=("targetId","childId","field")
for x,rec,ev in root_children:
    src=ownership.get(rec["id"],"GENERIC")
    for y in x.iter():
        for a in attrs:
            tid=y.get(a)
            if not tid or tid not in ids:continue
            target_top=top_owner_node(ids[tid])
            dst=ownership.get(target_top.get("id"),"GENERIC")
            if src!=dst:
                refs.append({"source":rec["id"],"source_owner":src,"target":tid,
                             "target_top":target_top.get("id"),"target_owner":dst,"attribute":a})

OUT.mkdir(exist_ok=True)
summary={"catalogue_revision":root.get("revision"),"selectors":selectors,
         "counts":{k:len(v) for k,v in buckets.items()},
         "ambiguous":len(ambiguous),"cross_owner_references":len(refs)}
(OUT/"summary.json").write_text(json.dumps(summary,indent=2,ensure_ascii=False)+"\n",encoding="utf-8")
(OUT/"ambiguous.json").write_text(json.dumps(ambiguous,indent=2,ensure_ascii=False)+"\n",encoding="utf-8")
(OUT/"cross-owner-references.json").write_text(json.dumps(refs,indent=2,ensure_ascii=False)+"\n",encoding="utf-8")
for roman,name in LEGIONS.items():
    (OUT/(roman.lower()+"-"+re.sub(r"[^a-z0-9]+","-",name.casefold()).strip("-")+".json")).write_text(
        json.dumps(buckets.get(roman,[]),indent=2,ensure_ascii=False)+"\n",encoding="utf-8")
(OUT/"generic-astartes.json").write_text(json.dumps(buckets["GENERIC"],indent=2,ensure_ascii=False)+"\n",encoding="utf-8")

print(json.dumps(summary,indent=2,ensure_ascii=False))
print("Audit only: no catalogue objects moved or deleted.")
