import xml.etree.ElementTree as ET,re
NS="http://www.battlescribe.net/schema/catalogueSchema"; C=lambda t:f"{{{NS}}}{t}"
r=ET.parse("Legiones Astartes.cat").getroot()
def cats(e):return [(x.get("targetId"),x.get("primary"),x.get("name")) for x in e.findall(f"./{C('categoryLinks')}/{C('categoryLink')}")]
def direct_text(e):
 return " ".join([(x.get("name") or "")+" "+(x.findtext(C("description")) or "") for x in e.findall(f"./{C('rules')}/{C('rule')}")]+[(x.get("name") or "") for x in e.findall(f"./{C('infoLinks')}/{C('infoLink')}")])
print("ROOTS WITH legion-i CONDITIONS OR DA-ish IDs/NAMES")
for e in r.findall(f"./{C('selectionEntries')}/{C('selectionEntry')}"):
 xml=ET.tostring(e,encoding="unicode")
 n=(e.get("name") or "")
 eid=e.get("id") or ""
 if 'childId="legion-i"' in xml or eid.startswith(("da","r40-da","r41-unit-i","r6-da","r7-da","r8-da")) or any(k in n.lower() for k in ["deathwing","dreadwing","cenobium","corswain","sedras","redloss","holguin","lion el"]):
  print("ROOT",eid,"|",n,"| type",e.get("type"),"| hidden",e.get("hidden"),"| cats",cats(e),"| direct",direct_text(e)[:800])
print("\\nALL DA-ish SHARED ENTRIES")
for e in r.iter(C("selectionEntry")):
 eid=e.get("id") or ""; n=(e.get("name") or "")
 if eid.startswith(("da","r40-da")):
  print(e.tag.split("}")[-1],eid,"|",n,"| cats",cats(e))
