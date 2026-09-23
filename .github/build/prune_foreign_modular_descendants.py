from pathlib import Path
import re,xml.etree.ElementTree as ET,json
NS="http://www.battlescribe.net/schema/catalogueSchema";ET.register_namespace("",NS);C=lambda t:f"{{{NS}}}{t}"
D=Path("modular-catalogues-generated");gp=D/"Legiones-Astartes-Generic.cat"
gr=ET.parse(gp).getroot()
files=[p for p in D.glob("*.cat") if p!=gp]
roots={};id_owner={}
for p in files:
 r=ET.parse(p).getroot();roots[p]=r
 for x in r.iter():
  if x.get("id"):id_owner.setdefault(x.get("id"),set()).add(p.name)
generic_ids={x.get("id") for x in gr.iter() if x.get("id")}
gst=ET.parse("Prohammer 30k.gst").getroot();gst_ids={x.get("id") for x in gst.iter() if x.get("id")}
tokens={"model","unit","upgrade","parent","root-entry","roster","force","self"}
stats={}
for p,r in roots.items():
 own=p.name;removed=0
 changed=True
 while changed:
  changed=False
  parent={c:q for q in r.iter() for c in q}
  for x in list(r.iter()):
   if x is r:continue
   refs=[x.get(a) for a in ("targetId","childId") if x.get(a)]
   foreign=[tid for tid in refs if tid not in tokens and tid not in generic_ids and tid not in gst_ids and tid not in {z.get("id") for z in r.iter() if z.get("id")} and tid in id_owner]
   if not foreign:continue
   # Cross-Legion Shattered assignment descendants and copied foreign armoury/options
   # are monolith baggage. Remove the smallest referencing element, preserving the owning root.
   par=parent.get(x)
   if par is not None:
    par.remove(x);removed+=1;changed=True
  if changed:continue
 ET.ElementTree(r).write(p,encoding="utf-8",xml_declaration=True);ET.parse(p);stats[own]=removed
print(json.dumps(stats,indent=2));print("removed",sum(stats.values()),"foreign descendant references")
