import xml.etree.ElementTree as ET, collections, re
NS="http://www.battlescribe.net/schema/catalogueSchema"; C=lambda t:f"{{{NS}}}{t}"
r=ET.parse("Legiones Astartes.cat").getroot()
def cons(e):return [(x.get("type"),x.get("value"),x.get("scope"),x.get("field")) for x in e.findall(f"./{C('constraints')}/{C('constraint')}")]
def cats(e):return [(x.get("targetId"),x.get("primary")) for x in e.findall(f"./{C('categoryLinks')}/{C('categoryLink')}")]
def costs(e):return [(x.get("typeId"),x.get("value")) for x in e.findall(f"./{C('costs')}/{C('cost')}")]
def rules(e):return [(x.get("name"),(x.findtext(C("description")) or "")[:500].replace("\\n"," | ")) for x in e.findall(f"./{C('rules')}/{C('rule')}")]
def infos(e):return [(x.get("name"),x.get("targetId")) for x in e.findall(f"./{C('infoLinks')}/{C('infoLink')}")]
def groups(e):
    out=[]
    for g in e.findall(f"./{C('selectionEntryGroups')}/{C('selectionEntryGroup')}"):
        out.append((g.get("id"),g.get("name"),g.get("hidden"),cons(g),
            [(x.tag.split("}")[-1],x.get("id"),x.get("name"),x.get("targetId"),costs(x),cons(x),x.get("hidden")) for x in list(g) if x.tag in (C("selectionEntry"),C("entryLink"))]))
    return out
print("REV",r.get("revision"))
for e in r.findall(f"./{C('selectionEntries')}/{C('selectionEntry')}"):
    eid=e.get("id") or "";n=(e.get("name") or "")
    if eid.startswith("r41-unit-xx-"):
        print("\\nXX",eid,n,"hidden",e.get("hidden"),"cost",costs(e),"cats",cats(e),"cons",cons(e))
        print("RULES",rules(e));print("INFOS",infos(e));print("GROUPS",groups(e))
for e in r.iter(C("selectionEntry")):
    n=(e.get("name") or "").lower();eid=e.get("id") or ""
    if "coils of the hydra" in n or "headhunter leviath" in n:
        print("\\nRITE",eid,e.get("name"),"hidden",e.get("hidden"),"cons",cons(e),"rules",rules(e),"groups",groups(e))
print("\\nTACTIC-RELATED")
for e in r.iter():
    n=(e.get("name") or "").lower();eid=e.get("id") or ""
    if "mutable tactic" in n or "siege specialists" in n or "coordinated sabotage" in n or "legion saboteur" in n:
        print(e.tag.split("}")[-1],eid,e.get("name"),"target",e.get("targetId"),"hidden",e.get("hidden"),"cost",costs(e) if e.tag in (C("selectionEntry"),C("entryLink")) else [],"cons",cons(e) if e.tag in (C("selectionEntry"),C("entryLink"),C("selectionEntryGroup")) else [])
print("\\nREWARDS",sum(1 for e in r.findall(f"./{C('selectionEntries')}/{C('selectionEntry')}") if (e.get("id") or "").startswith("r46-al-reward-")))
for e in r.findall(f"./{C('selectionEntries')}/{C('selectionEntry')}"):
    if (e.get("id") or "").startswith("r46-al-reward-"):
        print(e.get("id"),"|",e.get("name"),"|",cats(e),"|",costs(e),"| sourceRules", [x[0] for x in rules(e)][:8])
