from pathlib import Path
import xml.etree.ElementTree as ET
CAT=Path("Legiones Astartes.cat"); OUT=Path("inspection-r37-word-bearers-armoury-psychic.txt")
NS="http://www.battlescribe.net/schema/catalogueSchema"; C=lambda t:f"{{{NS}}}{t}"
r=ET.parse(CAT).getroot()
pm={c:p for p in r.iter() for c in p}
def anc(e,lim=5):
    out=[]; p=pm.get(e)
    while p is not None and len(out)<lim:
        if p.get("name"):out.append(p.get("name"))
        p=pm.get(p)
    return " > ".join(out)
def costs(e): return [(x.get("typeId"),x.get("value")) for x in e.findall(f"./{C('costs')}/{C('cost')}")]
def cons(e): return [(x.get("id"),x.get("type"),x.get("value"),x.get("scope"),x.get("field")) for x in e.findall(f"./{C('constraints')}/{C('constraint')}")]
lines=[f"CAT={r.get('revision')}","","==== r46-wb* ENTRIES ===="]
for e in r.iter(C("selectionEntry")):
    i=e.get("id") or ""; n=e.get("name") or ""
    if i.startswith("r46-wb") or "word bearers" in n.lower() or "dark channelling" in n.lower() or "burning lore" in n.lower() or "hex-bolts" in n.lower() or "accursed crozius" in n.lower():
        lines.append(f"{e.tag.split('}')[-1]} id={i} name={n} type={e.get('type')} hidden={e.get('hidden')} costs={costs(e)} cons={cons(e)} anc={anc(e)}")
        for rr in e.findall(f"./{C('rules')}/{C('rule')}"):
            lines.append(f"  RULE {rr.get('name')}: {(rr.findtext(C('description')) or '')[:500].replace(chr(10),' | ')}")
        for il in e.findall(f"./{C('infoLinks')}/{C('infoLink')}"):
            lines.append(f"  INFOLINK {il.get('name')} -> {il.get('targetId')} type={il.get('type')}")
        for g in e.findall(f"./{C('selectionEntryGroups')}/{C('selectionEntryGroup')}"):
            lines.append(f"  GROUP {g.get('id')} {g.get('name')} cons={cons(g)}")
lines += ["","==== PSYCHIC NAMED GROUPS / ENTRIES ===="]
for e in r.iter():
    n=(e.get("name") or "").lower()
    i=e.get("id") or ""
    if any(k in n for k in ["biomancy","telepathy","malefic daemonology","daemonology","psychic discipline","psychic powers"]) and e.tag in (C("selectionEntry"),C("selectionEntryGroup")):
        lines.append(f"{e.tag.split('}')[-1]} id={i} name={e.get('name')} type={e.get('type')} hidden={e.get('hidden')} anc={anc(e)} cons={cons(e)}")
OUT.write_text("\n".join(lines)+"\n",encoding="utf-8")
print(OUT.read_text())
