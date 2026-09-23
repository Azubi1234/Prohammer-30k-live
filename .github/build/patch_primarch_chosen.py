from pathlib import Path
import xml.etree.ElementTree as ET,re,json
NS="http://www.battlescribe.net/schema/catalogueSchema";ET.register_namespace("",NS);C=lambda t:f"{{{NS}}}{t}"
D=Path("modular-catalogues-generated");gp=D/"Legiones-Astartes-Generic.cat"
def add_pc(root,e):
 cls=e.find(C("categoryLinks"))
 if cls is None: cls=ET.SubElement(e,C("categoryLinks"))
 if any(x.get("id")==e.get("id")+"-primarchs-chosen-troops" for x in cls.findall(C("categoryLink"))):return False
 cl=ET.SubElement(cls,C("categoryLink"),{"targetId":"cat-troops","id":e.get("id")+"-primarchs-chosen-troops","primary":"true","name":"Troops — Primarch's Chosen","hidden":"true"})
 ms=ET.SubElement(cl,C("modifiers"));m=ET.SubElement(ms,C("modifier"),{"id":e.get("id")+"-pc-show-troops","type":"set","field":"hidden","value":"false"})
 cs=ET.SubElement(m,C("conditions"));ET.SubElement(cs,C("condition"),{"type":"atLeast","value":"1","field":"selections","scope":"force","childId":"da22-rite-primarchs-chosen","shared":"true","includeChildSelections":"true","includeChildForces":"false"})
 return True
t=ET.parse(gp);r=t.getroot();ids={x.get("id"):x for x in r.iter(C("selectionEntry"))};changed=[]
for eid in ("veteran-unit","terminator-unit"):
 if add_pc(r,ids[eid]):changed.append(eid)
t.write(gp,encoding="utf-8",xml_declaration=True)
# audit likely specialist Terminator units lacking the PC link
audit={}
for p in sorted(D.glob("*.cat")):
 if p==gp:continue
 rr=ET.parse(p).getroot();miss=[];have=[]
 for e in rr.iter(C("selectionEntry")):
  n=e.get("name") or ""
  if e.get("type")!="unit" or "terminator" not in n.casefold():continue
  cats=e.find(C("categoryLinks")); links=[] if cats is None else list(cats.findall(C("categoryLink")))
  elite=any(x.get("targetId")=="cat-elites" for x in links)
  pc=any("primarch" in (x.get("name") or "").casefold() for x in links)
  if elite:(have if pc else miss).append({"id":e.get("id"),"name":n})
 audit[p.name]={"with_pc":have,"missing_pc":miss}
Path("primarch-chosen-terminator-audit.json").write_text(json.dumps(audit,indent=2))
print("patched generic",changed)
print("missing specialist candidates",json.dumps({k:v["missing_pc"] for k,v in audit.items() if v["missing_pc"]},indent=2))
