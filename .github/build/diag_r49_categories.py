import xml.etree.ElementTree as ET, collections
NS="http://www.battlescribe.net/schema/catalogueSchema"; C=lambda t:f"{{{NS}}}{t}"
r=ET.parse("Legiones Astartes.cat").getroot()
co=collections.Counter(); ex={}
for e in r.findall(f"./{C('selectionEntries')}/{C('selectionEntry')}"):
 for c in e.findall(f"./{C('categoryLinks')}/{C('categoryLink')}"):
  if c.get("primary")=="true":
   co[(c.get("targetId"),c.get("name"))]+=1;ex.setdefault((c.get("targetId"),c.get("name")),(e.get("id"),e.get("name")))
print("PRIMARY ROOT CATEGORIES")
for k,v in co.most_common():print(k,v,"example",ex[k])
print("LEGION NAMES")
cfg=next(x for x in r.iter(C("selectionEntryGroup")) if x.get("id")=="config-legion")
for e in cfg.findall(f"./{C('selectionEntries')}/{C('selectionEntry')}"):print(e.get("id"),e.get("name"))
