from pathlib import Path
import xml.etree.ElementTree as ET,json,re
NS="http://www.battlescribe.net/schema/catalogueSchema";C=lambda t:f"{{{NS}}}{t}"
paths=[Path("modular-catalogues-generated/Legiones-Astartes-Generic.cat")]+sorted(Path("modular-catalogues-generated").glob("*.cat"))
seen=set();out=[]
for p in paths:
 if p in seen:continue
 seen.add(p);r=ET.parse(p).getroot()
 for x in r.iter():
  n=x.get("name") or "";i=x.get("id") or ""
  if "primarch" in n.casefold() and ("chosen" in n.casefold() or "rite" in n.casefold()):
   out.append({"file":p.name,"tag":x.tag.split("}")[-1],"id":i,"name":n})
Path("primarch-chosen-discovery.json").write_text(json.dumps(out,indent=2));print(json.dumps(out,indent=2))
