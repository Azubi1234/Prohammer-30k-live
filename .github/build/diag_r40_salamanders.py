from pathlib import Path
import xml.etree.ElementTree as ET
CAT=Path("Legiones Astartes.cat"); OUT=Path("inspection-r40-salamanders-audit.txt")
NS="http://www.battlescribe.net/schema/catalogueSchema"; C=lambda t:f"{{{NS}}}{t}"
r=ET.parse(CAT).getroot(); pm={c:p for p in r.iter() for c in p}
def anc(e,lim=5):
    out=[]; p=pm.get(e)
    while p is not None and len(out)<lim:
        if p.get("name"): out.append(p.get("name"))
        p=pm.get(p)
    return " > ".join(out)
def cats(e): return [(c.get("name"),c.get("targetId"),c.get("primary")) for c in e.findall(f"./{C('categoryLinks')}/{C('categoryLink')}")]
def rules(e):
    out=[]
    for rr in e.findall(f"./{C('rules')}/{C('rule')}"):
        out.append((rr.get("name"),(rr.findtext(C("description")) or "")[:400].replace("\n"," | ")))
    for il in e.findall(f"./{C('infoLinks')}/{C('infoLink')}"):
        if il.get("type")=="rule": out.append(("LINK:"+str(il.get("name")),il.get("targetId")))
    return out
lines=[f"CAT={r.get('revision')}",""]
for e in r.iter(C("selectionEntry")):
    i=e.get("id") or ""; n=(e.get("name") or "").lower()
    if ("r41-unit-xviii-" in i or "r25-rite-xviii" in i or "r42-role-xviii" in i
        or any(k in n for k in ["salamanders","vulkan","artellus numeon","nomus rhy","xiaphas jurr","cassian dracos","pyroclast","firedrake","infernus destroyer"])):
        lines.append(f"ENTRY id={i} name={e.get('name')} type={e.get('type')} hidden={e.get('hidden')} cats={cats(e)} anc={anc(e)}")
        for rn,rd in rules(e): lines.append(f"  RULE {rn}: {rd}")
        for g in e.findall(f"./{C('selectionEntryGroups')}/{C('selectionEntryGroup')}"):
            lines.append(f"  GROUP {g.get('id')} {g.get('name')}")
        lines.append("")
OUT.write_text("\n".join(lines),encoding="utf-8")
print(OUT.read_text())
