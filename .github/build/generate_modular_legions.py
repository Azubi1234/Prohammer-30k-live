from pathlib import Path
import copy,re,uuid,xml.etree.ElementTree as ET

SRC=Path("Legiones Astartes.cat")
OUT=Path("modular-catalogues-generated")
NS="http://www.battlescribe.net/schema/catalogueSchema"
ET.register_namespace("",NS)
C=lambda t:f"{{{NS}}}{t}"

LEGIONS={
"I":"Dark Angels","III":"Emperor's Children","IV":"Iron Warriors","V":"White Scars",
"VI":"Space Wolves","VII":"Imperial Fists","VIII":"Night Lords","IX":"Blood Angels",
"X":"Iron Hands","XII":"World Eaters","XIII":"Ultramarines","XIV":"Death Guard",
"XV":"Thousand Sons","XVI":"Sons of Horus","XVII":"Word Bearers","XVIII":"Salamanders",
"XIX":"Raven Guard","XX":"Alpha Legion"}

tree=ET.parse(SRC);root=tree.getroot()
parent={c:p for p in root.iter() for c in p}
ids={x.get("id"):x for x in root.iter() if x.get("id")}
cfg=ids["config-legion"]
selectors={}
for e in cfg.iter(C("selectionEntry")):
    m=re.match(r"^([IVXLCDM]+)\s+Legion\s+[—-]\s+(.+)$",e.get("name") or "",re.I)
    if m:selectors[m.group(1).upper()]=(e.get("id"),m.group(2).strip())
name_to_roman={v[1].casefold():k for k,v in selectors.items()}

def fixed_legion(x):
    rs=set()
    for q in (C("rule"),C("infoLink")):
        for y in x.iter(q):
            m=re.match(r"Legiones Astartes \((.+)\)",y.get("name") or "")
            if m and m.group(1).strip().casefold() in name_to_roman:
                rs.add(name_to_roman[m.group(1).strip().casefold()])
    return next(iter(rs)) if len(rs)==1 else None

def owner(x):
    xid=x.get("id") or ""
    m=re.match(r"r41-unit-([ivxlcdm]+)-",xid,re.I)
    if m and m.group(1).upper() in selectors:return m.group(1).upper()
    if xid.startswith("da22-") or xid.startswith("r40-da-"):return "I"
    fl=fixed_legion(x)
    return fl

containers=("sharedSelectionEntries","sharedSelectionEntryGroups","sharedRules","sharedProfiles",
            "selectionEntries","selectionEntryGroups","rules","profiles")
owned={r:[] for r in LEGIONS}
for cname in containers:
    cont=root.find(C(cname))
    if cont is None:continue
    for x in list(cont):
        o=owner(x)
        if o in owned:owned[o].append((cname,x))

def new_id(roman):
    return "mod-"+roman.lower()+"-"+uuid.uuid5(uuid.NAMESPACE_URL,"prohammer30k:"+roman).hex[:20]

OUT.mkdir(exist_ok=True)
for roman,lname in LEGIONS.items():
    cat=ET.Element(C("catalogue"),{
        "id":new_id(roman),
        "name":lname,
        "revision":"1",
        "battleScribeVersion":root.get("battleScribeVersion","2.03"),
        "gameSystemId":root.get("gameSystemId",""),
        "gameSystemRevision":root.get("gameSystemRevision","1"),
        "library":"false"
    })
    # Preserve publication metadata where possible.
    for tag in ("publications","costTypes","profileTypes","categoryEntries","forceEntries"):
        src=root.find(C(tag))
        if src is not None:cat.append(copy.deepcopy(src))
    # Link back to generic Legiones Astartes library. This is a generated
    # staging catalogue; the final parent/library conversion occurs only after validation.
    links=ET.SubElement(cat,C("catalogueLinks"))
    ET.SubElement(links,C("catalogueLink"),{
        "id":"link-generic-"+roman.lower(),
        "name":"Legiones Astartes — Generic",
        "targetId":root.get("id",""),
        "type":"catalogue",
        "importRootEntries":"true"
    })
    by_container={}
    for cname,x in owned[roman]:by_container.setdefault(cname,[]).append(x)
    for cname in containers:
        xs=by_container.get(cname,[])
        if not xs:continue
        dest=ET.SubElement(cat,C(cname))
        for x in xs:dest.append(copy.deepcopy(x))
    path=OUT/(re.sub(r"[^A-Za-z0-9]+","-",lname).strip("-")+".cat")
    ET.ElementTree(cat).write(path,encoding="utf-8",xml_declaration=True)
    # Parse round-trip immediately.
    ET.parse(path)
    print(f"{roman:>4} {lname:<20} {len(owned[roman]):>4} root objects -> {path}")

print("Generated staging catalogues only; source Legiones Astartes.cat remains untouched.")
