from pathlib import Path
import copy,re,xml.etree.ElementTree as ET

SRC=Path("Legiones Astartes.cat")
if not SRC.exists():
    # The live modular repository no longer carries the retired monolithic
    # catalogue. Rebuild from the current Generic library instead.
    SRC=Path("Legiones-Astartes-Generic.cat")
OUT=Path("modular-catalogues-generated/Legiones-Astartes-Generic.cat")
NS="http://www.battlescribe.net/schema/catalogueSchema"
ET.register_namespace("",NS)
C=lambda t:f"{{{NS}}}{t}"
root=ET.parse(SRC).getroot()
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
            if m and m.group(1).strip().casefold() in name_to_roman:rs.add(name_to_roman[m.group(1).strip().casefold()])
    return next(iter(rs)) if len(rs)==1 else None
def owner(x):
    xid=x.get("id") or ""
    m=re.match(r"r41-unit-([ivxlcdm]+)-",xid,re.I)
    if m and m.group(1).upper() in selectors:return m.group(1).upper()
    if xid.startswith("da22-") or xid.startswith("r40-da-"):return "I"
    return fixed_legion(x)

cat=copy.deepcopy(root)
cat.set("name","Legiones Astartes — Generic Library")
cat.set("library","true")
cat.set("revision","1")
removed=0
containers=("sharedSelectionEntries","sharedSelectionEntryGroups","sharedRules","sharedProfiles","selectionEntries","selectionEntryGroups","rules","profiles")
for cname in containers:
    cont=cat.find(C(cname))
    if cont is None:continue
    for x in list(cont):
        if owner(x):
            cont.remove(x);removed+=1

# Keep the Legion chooser structure in Generic. The live modular build applies
# catalogue-specific auto-Legion identity after generation, hiding the other
# 17 choices and automatically selecting the Legion belonging to the catalogue.
# Removing config-legion here would also remove the chosen Legion from Army
# Configuration, which is not the intended New Recruit UI.

ET.ElementTree(cat).write(OUT,encoding="utf-8",xml_declaration=True)
ET.parse(OUT)
print("Wrote",OUT,"removed Legion-owned/config roots:",removed,"size:",OUT.stat().st_size)
