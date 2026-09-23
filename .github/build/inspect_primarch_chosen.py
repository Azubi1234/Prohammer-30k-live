from pathlib import Path
import xml.etree.ElementTree as ET,json
NS="http://www.battlescribe.net/schema/catalogueSchema";C=lambda t:f"{{{NS}}}{t}"
D=Path("modular-catalogues-generated");out=[]
for p in sorted(D.glob("*.cat")):
 r=ET.parse(p).getroot()
 for x in r.iter(C("categoryLink")):
  if "primarch" in (x.get("name") or "").casefold():
   par={c:q for q in r.iter() for c in q}.get(x)
   out.append({"file":p.name,"category":ET.tostring(x,encoding="unicode"),"parent":ET.tostring(par,encoding="unicode")[:12000] if par is not None else None})
 for x in r.iter(C("selectionEntry")):
  if x.get("id") in ("veteran-unit","terminator-unit","da22-rite-primarchs-chosen"):
   out.append({"file":p.name,"entry":x.get("id"),"xml":ET.tostring(x,encoding="unicode")[:20000]})
Path("primarch-chosen-structure.json").write_text(json.dumps(out,indent=2));print("records",len(out))
