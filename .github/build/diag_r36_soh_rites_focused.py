from pathlib import Path
import re, xml.etree.ElementTree as ET
CAT=Path("Legiones Astartes.cat"); GST=Path("Prohammer 30k.gst"); OUT=Path("inspection-r36-soh-rites-focused.txt")
NS="http://www.battlescribe.net/schema/catalogueSchema"; GNS="http://www.battlescribe.net/schema/gameSystemSchema"
C=lambda t:f"{{{NS}}}{t}"; G=lambda t:f"{{{GNS}}}{t}"
cr=ET.parse(CAT).getroot(); gr=ET.parse(GST).getroot()
pm={c:p for p in cr.iter() for c in p}

def cats(e):
    return [(c.get("name"),c.get("targetId"),c.get("primary")) for c in e.findall(f"./{C('categoryLinks')}/{C('categoryLink')}")]
def ancestors(e,lim=4):
    out=[]; p=pm.get(e)
    while p is not None and len(out)<lim:
        if p.get("name"): out.append(p.get("name"))
        p=pm.get(p)
    return " > ".join(out)

lines=[f"CAT={cr.get('revision')} GST={gr.get('revision')}","","MASTER OF SIGNALS MATCHES:"]
for e in cr.iter():
    n=e.get("name") or ""
    txt=" ".join((t.text or "") for t in e.iter() if t.tag==C("description"))
    if "master of signals" in n.lower() or "master of signals" in txt.lower():
        lines.append(f"{e.tag.split('}')[-1]} | id={e.get('id')} | name={n} | cats={cats(e) if e.tag==C('selectionEntry') else ''} | anc={ancestors(e)}")

lines += ["","BLACK REAVING / LONG MARCH RELATED ROOTS:"]
for e in cr.iter(C("selectionEntry")):
    n=(e.get("name") or "").lower(); i=e.get("id") or ""
    if any(k in n for k in ["black reaving","long march","reaver attack squad"]) or any(k in i for k in ["r25-rite-xvi","r42-role-xvi","r32-soh-long-march"]):
        lines.append(f"id={i} | name={e.get('name')} | type={e.get('type')} | hidden={e.get('hidden')} | cats={cats(e)} | anc={ancestors(e)}")

lines += ["","ALL-CAPS SELECTION ENTRIES:"]
for e in cr.iter(C("selectionEntry")):
    n=(e.get("name") or "").strip()
    letters=re.sub(r"[^A-Za-zÀ-ÿ]","",n)
    if len(letters)>=4 and letters==letters.upper():
        lines.append(f"id={e.get('id')} | name={n} | type={e.get('type')} | hidden={e.get('hidden')} | cats={cats(e)} | anc={ancestors(e)}")

lines += ["","GST FORCE/CATEGORY LINKS:"]
for fe in gr.iter(G("forceEntry")):
    lines.append(f"FORCE {fe.get('id')} {fe.get('name')}")
    for cl in fe.findall(f"./{G('categoryLinks')}/{G('categoryLink')}"):
        if cl.get("targetId") in ("cat-fast","cat-heavy","cat-troops","cat-hq","cat-config","cat-auxiliary"):
            lines.append(ET.tostring(cl,encoding="unicode"))

OUT.write_text("\n".join(lines)+"\n",encoding="utf-8")
print(OUT.read_text())
