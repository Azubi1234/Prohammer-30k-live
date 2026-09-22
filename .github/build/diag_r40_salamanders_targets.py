from pathlib import Path
import xml.etree.ElementTree as ET
CAT=Path("Legiones Astartes.cat"); GST=Path("Prohammer 30k.gst"); OUT=Path("inspection-r40-salamanders-targets.txt")
NS="http://www.battlescribe.net/schema/catalogueSchema"; GNS="http://www.battlescribe.net/schema/gameSystemSchema"
C=lambda t:f"{{{NS}}}{t}"; G=lambda t:f"{{{GNS}}}{t}"
r=ET.parse(CAT).getroot(); g=ET.parse(GST).getroot(); pm={c:p for p in r.iter() for c in p}
def anc(e,lim=6):
    out=[]; p=pm.get(e)
    while p is not None and len(out)<lim:
        if p.get("name"):out.append(p.get("name"))
        p=pm.get(p)
    return " > ".join(out)
lines=["LOYALTY:"]
for e in r.iter(C("selectionEntry")):
    n=(e.get("name") or "").lower()
    if n in ("loyalist","traitor") or "allegiance" in n:
        lines.append(f"{e.get('id')} | {e.get('name')} | {anc(e)}")
lines+=["","SAL LINKS:"]
for l in r.iter(C("entryLink")):
    if (l.get("targetId") or "").startswith("r46-sal"):
        lines.append(f"{l.get('id')} | {l.get('name')} -> {l.get('targetId')} | {anc(l)}")
lines+=["","CATEGORIES:"]
for c in g.iter(G("categoryEntry")):
    n=(c.get("name") or "").lower()
    if any(k in n for k in ["jump","jetbike","skimmer","flyer","fortification","vehicle","dreadnought","infantry"]):
        lines.append(f"{c.get('id')} | {c.get('name')} hidden={c.get('hidden')}")
lines+=["","CORE TARGETS:"]
for e in r.iter(C("selectionEntry")):
    n=(e.get("name") or "").lower()
    if any(k in n for k in ["legion librarian consul","legion chaplain consul","dreadnought","contemptor dreadnought"]) and len(anc(e).split(" > "))<5:
        lines.append(f"{e.get('id')} | {e.get('name')} | type={e.get('type')} | {anc(e)}")
OUT.write_text("\n".join(lines)+"\n",encoding="utf-8"); print(OUT.read_text())
