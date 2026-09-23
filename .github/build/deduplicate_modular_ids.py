from pathlib import Path
import xml.etree.ElementTree as ET,collections,json
NS="http://www.battlescribe.net/schema/catalogueSchema";ET.register_namespace("",NS)
D=Path("modular-catalogues-generated");report={}
for p in sorted(D.glob("*.cat")):
 t=ET.parse(p);r=t.getroot();els=[x for x in r.iter() if x.get("id")];by=collections.defaultdict(list)
 for x in els:by[x.get("id")].append(x)
 changed={}
 for old,xs in by.items():
  if len(xs)<2:continue
  # Keep first occurrence stable; rename later duplicate objects. References are intentionally not globally retargeted:
  # duplicate IDs are ambiguous by definition and most listed duplicates are nested cloned constraints/modifiers.
  for i,x in enumerate(xs[1:],2):
   new=f"{old}-moddup{i}"
   while any(y.get("id")==new for y in els):new+="-x"
   x.set("id",new);changed.setdefault(old,[]).append(new)
 if changed:
  t.write(p,encoding="utf-8",xml_declaration=True);ET.parse(p);report[p.name]=changed
Path("modular-deduplicate-audit.json").write_text(json.dumps(report,indent=2));print(json.dumps(report,indent=2))

# RC rerun after correcting Generic library index distribution.
