from pathlib import Path
import xml.etree.ElementTree as ET,json,collections
NS="http://www.battlescribe.net/schema/catalogueSchema";GS="http://www.battlescribe.net/schema/gameSystemSchema"
C=lambda t:f"{{{NS}}}{t}"
D=Path("modular-catalogues-generated")
gp=D/"Legiones-Astartes-Generic.cat";gr=ET.parse(gp).getroot()
gst=ET.parse("Prohammer 30k.gst").getroot()
generic_ids={x.get("id") for x in gr.iter() if x.get("id")}
gst_ids={x.get("id") for x in gst.iter() if x.get("id")}
tokens={"model","unit","upgrade","parent","root-entry","roster","force","self"}
report={};bad_total=0
for p in sorted(D.glob("*.cat")):
    if p==gp:continue
    r=ET.parse(p).getroot();local={x.get("id") for x in r.iter() if x.get("id")}
    bad=[];counts=collections.Counter()
    for x in r.iter():
      for a in ("targetId","childId"):
        tid=x.get(a)
        if not tid or tid in tokens:continue
        if tid in local:counts["local"]+=1
        elif tid in generic_ids:counts["generic"]+=1
        elif tid in gst_ids:counts["gst"]+=1
        else:
          counts["unresolved"]+=1
          if len(bad)<100:bad.append({"tag":x.tag.split("}")[-1],"attribute":a,"target":tid,"id":x.get("id"),"name":x.get("name")})
    links=r.find(C("catalogueLinks"))
    glinks=[] if links is None else [x for x in links.findall(C("catalogueLink")) if x.get("targetId")==gr.get("id")]
    if len(glinks)!=1:bad.append({"catalogue_link_problem":len(glinks)})
    report[p.name]={"counts":dict(counts),"bad":bad}
    bad_total+=counts["unresolved"]+(0 if len(glinks)==1 else 1)
out={"generic_id":gr.get("id"),"legions":len(report),"bad_total":bad_total,"report":report}
Path("modular-loadability-audit.json").write_text(json.dumps(out,indent=2),encoding="utf-8")
print(json.dumps({"legions":len(report),"bad_total":bad_total,"per_legion":{k:v["counts"].get("unresolved",0) for k,v in report.items()}},indent=2))
if bad_total:raise SystemExit(1)
