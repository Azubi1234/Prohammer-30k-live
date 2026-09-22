from pathlib import Path
import xml.etree.ElementTree as ET, re
CAT=Path("Legiones Astartes.cat"); OUT=Path("inspection-r37-wb-targets.txt")
NS="http://www.battlescribe.net/schema/catalogueSchema"; C=lambda t:f"{{{NS}}}{t}"
r=ET.parse(CAT).getroot(); pm={c:p for p in r.iter() for c in p}
def anc(e,lim=4):
    out=[]; p=pm.get(e)
    while p is not None and len(out)<lim:
        if p.get("name"): out.append(p.get("name"))
        p=pm.get(p)
    return " > ".join(out)
def cons(e):
    return [(x.get("id"),x.get("type"),x.get("value"),x.get("scope"),x.get("field")) for x in e.findall(f"./{C('constraints')}/{C('constraint')}")]
def costs(e):
    return [(x.get("typeId"),x.get("value")) for x in e.findall(f"./{C('costs')}/{C('cost')}")]
lines=[]
wanted=("praetor","centurion","chaplain","veteran squad","terminator squad","tactical squad","breacher","assault squad","honour guard")
for e in r.iter(C("selectionEntry")):
    n=(e.get("name") or "").lower()
    if any(w in n for w in wanted) and (anc(e).endswith("Legiones Astartes") or "Legion Consul Upgrade" in anc(e) or e.get("id") in ("hq-praetor","hq-centurion")):
        lines.append(f"ENTRY id={e.get('id')} name={e.get('name')} type={e.get('type')} costs={costs(e)} cons={cons(e)} anc={anc(e)}")
for e in r.iter(C("selectionEntry")):
    i=e.get("id") or ""; n=(e.get("name") or "")
    if i in ("transport-rhino","transport-drop-pod","transport-dreadclaw","transport-dreadnought-drop-pod","terminator-unit","veteran-unit","tactical-unit","breacher-unit","assault-unit"):
        lines.append(f"CORE id={i} name={n} type={e.get('type')} costs={costs(e)} cons={cons(e)} anc={anc(e)}")
lines.append("\nWB ENTRYLINKS:")
for l in r.iter(C("entryLink")):
    if (l.get("targetId") or "").startswith("r46-wb"):
        lines.append(f"LINK id={l.get('id')} name={l.get('name')} target={l.get('targetId')} hidden={l.get('hidden')} anc={anc(l,6)}")
lines.append("\nSHARED RULE IDS:")
for sr in r.findall(f"./{C('sharedRules')}/{C('rule')}"):
    if (sr.get("name") or "") in ("Daemon","Fearless","Bulky","Rending","Fleet","It Will Not Die","Adamantium Will","Zealot","Scout","Furious Charge","Counter-Attack","Feel No Pain (5+)","Feel No Pain (6+)","Hardened Armour","Preferred Enemy (Loyalists)","Soul Blaze","Independent Character","Master of the Legion","Primarch","Concussive","Two-Handed","Master-Crafted"):
        lines.append(f"RULE id={sr.get('id')} name={sr.get('name')}")
OUT.write_text("\n".join(lines)+"\n",encoding="utf-8")
print(OUT.read_text())
