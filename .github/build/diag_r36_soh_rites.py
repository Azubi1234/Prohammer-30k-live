from pathlib import Path
import xml.etree.ElementTree as ET
CAT=Path("Legiones Astartes.cat"); GST=Path("Prohammer 30k.gst"); OUT=Path("inspection-r36-soh-rites.txt")
CNS="http://www.battlescribe.net/schema/catalogueSchema"; GNS="http://www.battlescribe.net/schema/gameSystemSchema"
C=lambda t:f"{{{CNS}}}{t}"; G=lambda t:f"{{{GNS}}}{t}"
cr=ET.parse(CAT).getroot(); gr=ET.parse(GST).getroot()
ids={x.get("id"):x for x in cr.iter() if x.get("id")}
def dump(e,indent=0,depth=5):
    if e is None:return ["MISSING"]
    pad="  "*indent
    a=[pad+e.tag.split("}")[-1]+" "+str({k:v for k,v in e.attrib.items()})]
    if e.text and e.text.strip(): a.append(pad+"  TEXT="+e.text.strip().replace("\n"," | "))
    if depth>0:
        for ch in list(e):
            a += dump(ch,indent+1,depth-1)
    return a
lines=[f"CAT={cr.get('revision')} GST={gr.get('revision')}",""]
for rid in ["r25-rite-xvi-0-the-long-march","r25-rite-xvi-1-the-black-reaving"]:
    lines += ["==== "+rid+" ===="]+dump(ids.get(rid),0,7)+[""]
# Related selection entries / copies.
for e in cr.iter(C("selectionEntry")):
    n=(e.get("name") or "").lower(); i=e.get("id") or ""
    if any(k in n for k in ["long march","black reaving","reaver onslaught","cthonian encirclement"]) or "r32-soh-long-march" in i or "r42-role-xvi-1" in i:
        lines += ["==== RELATED "+i+" / "+(e.get("name") or "")+" ===="]+dump(e,0,5)+[""]
# GST relevant force links.
for cl in gr.iter(G("categoryLink")):
    if cl.get("targetId") in ("cat-fast","cat-heavy","cat-troops"):
        lines += ["==== GST "+cl.get("name","")+" ===="]+dump(cl,0,6)+[""]
OUT.write_text("\n".join(lines)+"\n",encoding="utf-8")
print(OUT.read_text())
