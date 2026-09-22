import xml.etree.ElementTree as ET,re,collections
NS="http://www.battlescribe.net/schema/catalogueSchema"; C=lambda t:f"{{{NS}}}{t}"
r=ET.parse("Legiones Astartes.cat").getroot(); roots=r.findall(f"./{C('selectionEntries')}/{C('selectionEntry')}")
def norm(s):
 s=(s or "").replace("’","'").replace("— Rewards of Treachery","").replace("- Rewards of Treachery","")
 s=re.sub(r"^[IVXLCDM]+\s*[—-]\s*","",s,flags=re.I);return re.sub(r"[^a-z0-9]+"," ",s.lower()).strip()
def rules(e):return [(x.get("name"),(x.findtext(C("description")) or "")[:180]) for x in e.findall(f"./{C('rules')}/{C('rule')}")]
def infos(e):return [(x.get("name"),x.get("targetId")) for x in e.findall(f"./{C('infoLinks')}/{C('infoLink')}")]
def groups(e):return [(x.get("id"),x.get("name"),len(x.findall(f"./{C('selectionEntries')}/{C('selectionEntry')}")),len(x.findall(f"./{C('entryLinks')}/{C('entryLink')}"))) for x in e.findall(f"./{C('selectionEntryGroups')}/{C('selectionEntryGroup')}")]
def profile_count(e):return sum(1 for _ in e.iter(C("profile")))
def option_count(e):return sum(1 for _ in e.iter(C("selectionEntry")))+sum(1 for _ in e.iter(C("entryLink")))
def source_dump(e):return any((x.get("name") or "")=="Source Entry" for x in e.iter(C("rule")))
def named_la(e):
 return [x.get("name") for x in list(e.findall(f"./{C('rules')}/{C('rule')}"))+list(e.findall(f"./{C('infoLinks')}/{C('infoLink')}")) if re.match(r"^Legiones Astartes \(.+\)$",x.get("name") or "",re.I)]
def donor_for(rw):
 k=norm(rw.get("name"))
 cand=[e for e in roots if (e.get("id") or "").startswith("r41-unit-") and not (e.get("id") or "").startswith("r41-unit-xx-") and norm(e.get("name"))==k]
 if cand:return cand[0]
 if "varagyr" in k:
  cand=[e for e in roots if "varagyr" in norm(e.get("name")) and not (e.get("id") or "").startswith("r46-al-reward-") and "retinue" not in norm(e.get("name"))]
  if cand:return sorted(cand,key=lambda e:(0 if (e.get("id") or "").startswith("r63-sw-varagyr") else 1,len(e.get("id") or "")))[0]
 return None
rewards=[e for e in roots if (e.get("id") or "").startswith("r46-al-reward-")]
print("CAT",r.get("revision"),"REWARDS",len(rewards))
summary=collections.Counter()
for rw in rewards:
 d=donor_for(rw)
 if d is None:
  print("MISSING_DONOR",rw.get("id"),rw.get("name"));continue
 dla=named_la(d);rla=named_la(rw)
 ds=source_dump(d);rs=source_dump(rw)
 dr=rules(d);di=infos(d);rr=rules(rw);ri=infos(rw)
 # direct unit-specific rule names, excluding generic legion/core mechanics and source-entry
 excl={"source entry","legiones astartes","standard wargear","dedicated transport"}
 dunits=[n for n,_ in dr if (n or "").casefold() not in excl and not (n or "").startswith("Legiones Astartes")]
 runits=[n for n,_ in rr if (n or "").casefold() not in excl and not (n or "").startswith("Legiones Astartes")]
 print("\n",rw.get("id"),rw.get("name"))
 print(" DONOR",d.get("id"),d.get("name"),"sourceDump",ds,"directLA",dla,"profiles",profile_count(d),"options",option_count(d),"directRules",len(dr),"directInfos",len(di))
 print(" REWARD sourceDump",rs,"directLA",rla,"profiles",profile_count(rw),"options",option_count(rw),"directRules",len(rr),"directInfos",len(ri))
 print(" DONOR_RULES",dr[:25])
 print(" REWARD_RULES",rr[:25])
 print(" DONOR_INFOS",di[:25])
 print(" REWARD_INFOS",ri[:25])
 if ds:summary["donor_source_dump"]+=1
 if dla:summary["donor_direct_la"]+=1
 if rla:summary["reward_direct_la"]+=1
 if profile_count(rw)<profile_count(d):summary["lost_profiles"]+=1
 if option_count(rw)<option_count(d):summary["lost_options"]+=1
 if len(runits)<len(dunits):summary["fewer_direct_unit_rules"]+=1
print("\nSUMMARY",dict(summary))
