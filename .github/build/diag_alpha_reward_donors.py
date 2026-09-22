import xml.etree.ElementTree as ET,re
NS="http://www.battlescribe.net/schema/catalogueSchema"; C=lambda t:f"{{{NS}}}{t}"
r=ET.parse("Legiones Astartes.cat").getroot()
roots=r.findall(f"./{C('selectionEntries')}/{C('selectionEntry')}")
def norm(s):
 s=(s or "").replace("’","'").replace("— Rewards of Treachery","").replace("- Rewards of Treachery","")
 s=re.sub(r"^[IVXLCDM]+\s*[—-]\s*","",s,flags=re.I)
 return re.sub(r"[^a-z0-9]+"," ",s.lower()).strip()
rewards=[e for e in roots if (e.get("id") or "").startswith("r46-al-reward-")]
donors=[e for e in roots if not (e.get("id") or "").startswith("r46-al-reward-") and not (e.get("id") or "").startswith("r41-unit-xx-")]
by={}
for e in donors:by.setdefault(norm(e.get("name")),[]).append(e)
ok=0
for rw in rewards:
 key=norm(rw.get("name"));c=by.get(key,[])
 print(rw.get("id"),"|",rw.get("name"),"| MATCH",[(x.get("id"),x.get("name")) for x in c])
 if len(c)==1:ok+=1
print("UNIQUE",ok,"of",len(rewards))
