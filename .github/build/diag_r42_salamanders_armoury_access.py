from pathlib import Path
import xml.etree.ElementTree as ET
CAT=Path("Legiones Astartes.cat"); OUT=Path("inspection-r42-salamanders-armoury-access.txt")
NS="http://www.battlescribe.net/schema/catalogueSchema"; C=lambda t:f"{{{NS}}}{t}"
r=ET.parse(CAT).getroot(); pm={c:p for p in r.iter() for c in p}
def chain(e,lim=9):
    out=[];p=e
    while p is not None and len(out)<lim:
        out.append((p.tag.split('}')[-1],p.get("id"),p.get("name")))
        p=pm.get(p)
    return out
for tid in ["r46-sal-inferno-pistol","r46-sal-mastercrafted","r46-sal-artificer-armour","r46-sal-ceramite"]:
    print("\\n====",tid,"====")
    for l in r.iter(C("entryLink")):
        if l.get("targetId")!=tid:continue
        ch=chain(l)
        txt=" > ".join((n or "") for _,_,n in ch)
        print(l.get("id"),"|",txt)
