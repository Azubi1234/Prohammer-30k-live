import xml.etree.ElementTree as ET
CNS="http://www.battlescribe.net/schema/catalogueSchema";GNS="http://www.battlescribe.net/schema/gameSystemSchema"
C=lambda t:f"{{{CNS}}}{t}";G=lambda t:f"{{{GNS}}}{t}"
cr=ET.parse("Legiones Astartes.cat").getroot();gr=ET.parse("Prohammer 30k.gst").getroot()
ids={e.get("id") for e in cr.iter() if e.get("id")}|{e.get("id") for e in gr.iter() if e.get("id")}
pm={c:p for p in cr.iter() for c in p}
def chain(e,lim=8):
 out=[];p=e
 while p is not None and len(out)<lim:
  out.append(f"{p.tag.split('}')[-1]}:{p.get('id')}:{p.get('name')}");p=pm.get(p)
 return " > ".join(out)
bad=[]
for e in cr.iter(C("condition")):
 if e.get("field")!="selections":continue
 v=e.get("childId")
 if v and v not in ids:bad.append((v,e.get("scope"),e.get("type"),e.get("value"),chain(e)))
print("BAD_SELECTION_CONDITIONS",len(bad))
for x in bad:print("BADSEL",x)
badrep=[]
for e in cr.iter(C("repeat")):
 if e.get("field")!="selections":continue
 v=e.get("childId")
 if v and v not in ids:badrep.append((v,e.get("scope"),e.get("value"),chain(e)))
print("BAD_SELECTION_REPEATS",len(badrep))
for x in badrep:print("BADREP",x)
