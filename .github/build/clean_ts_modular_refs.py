from pathlib import Path
import xml.etree.ElementTree as ET
NS="http://www.battlescribe.net/schema/catalogueSchema";ET.register_namespace("",NS);C=lambda t:f"{{{NS}}}{t}"
p=Path("modular-catalogues-generated/Thousand-Sons.cat");t=ET.parse(p);r=t.getroot()
old_prefixes=("r45-cult-r41-unit-xv-0-sekhmet-terminator-cabal-","r45-cult-r41-unit-xv-2-ammitara-occult-intercession-cabal-")
removed=0
for parent in r.iter():
    for x in list(parent):
        if x.tag==C("condition") and (x.get("childId") or "").startswith(old_prefixes):
            parent.remove(x);removed+=1

# Diagnose Ahriman's current force-weapon structure. Remove the stale repeat only if
# its target is absent; the underlying group/options remain intact and are audited separately.
ids={x.get("id"):x for x in r.iter() if x.get("id")}
stale="live-r2-r41-unit-xv-6-ahzek-ahriman-retinue-0-hq-centurion-ret-command-champ-pw"
for parent in r.iter():
    for x in list(parent):
        if x.tag==C("repeat") and x.get("childId")==stale and stale not in ids:
            parent.remove(x);removed+=1
t.write(p,encoding="utf-8",xml_declaration=True);ET.parse(p)
print("Removed obsolete TS conditions/repeats:",removed)
