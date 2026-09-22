import xml.etree.ElementTree as ET, re, collections
NS="http://www.battlescribe.net/schema/catalogueSchema"; C=lambda t:f"{{{NS}}}{t}"
r=ET.parse("Legiones Astartes.cat").getroot(); ids={x.get("id"):x for x in r.iter() if x.get("id")}; pm={c:p for p in r.iter() for c in p}
def costs(e): return [(x.get("typeId"),x.get("value")) for x in e.findall(f"./{C('costs')}/{C('cost')}")]
def cons(e): return [(x.get("id"),x.get("type"),x.get("value"),x.get("scope"),x.get("field")) for x in e.findall(f"./{C('constraints')}/{C('constraint')}")]
def mods(e):
    m=e.find(C("modifiers")); return ET.tostring(m,encoding="unicode") if m is not None else ""
def cats(e): return [(x.get("name"),x.get("targetId"),x.get("primary")) for x in e.findall(f"./{C('categoryLinks')}/{C('categoryLink')}")]
def dump(e,depth=0,maxdepth=6):
    ind="  "*depth
    print(f"{ind}{e.tag.split('}')[-1]} id={e.get('id')} name={e.get('name')} type={e.get('type')} hidden={e.get('hidden')} default={e.get('defaultAmount')} cost={costs(e)} cons={cons(e)} cats={cats(e)}")
    if mods(e): print(ind+" MODS "+mods(e)[:5000])
    for rr in e.findall(f"./{C('rules')}/{C('rule')}"): print(ind+" RULE",rr.get("id"),rr.get("name"),":",(rr.findtext(C("description")) or "")[:400].replace("\\n"," | "))
    for il in e.findall(f"./{C('infoLinks')}/{C('infoLink')}"): print(ind+" INFO",il.get("id"),il.get("name"),"->",il.get("targetId"),"hidden",il.get("hidden"))
    if depth>=maxdepth:return
    for tag in ("selectionEntries","selectionEntryGroups","entryLinks"):
        p=e.find(C(tag))
        if p is not None:
            for x in list(p):dump(x,depth+1,maxdepth)

print("REV",r.get("revision"),"GST",r.get("gameSystemRevision"))
for eid in ["legion-xv","hq-centurion","hq-praetor","veteran-unit","terminator-unit"]:
    print("\\n====",eid,"====")
    dump(ids[eid],0,7)

print("\\n==== TS NAMED/SPECIAL ROOTS ====")
for e in r.findall(f"./{C('selectionEntries')}/{C('selectionEntry')}"):
    eid=e.get("id") or ""; n=(e.get("name") or "").lower()
    if "r41-unit-xv-" in eid or any(k in n for k in ["ahriman","phosis","amon","sanakht","magnus","sekhemet","sek hmet","khenetai"]):
        print("\\nROOT",eid,e.get("name")); dump(e,0,5)

print("\\n==== DIRECT PSYCHIC/CULT GROUP ROOTS ====")
for e in r.iter(C("selectionEntry")):
    gs=e.findall(f"./{C('selectionEntryGroups')}/{C('selectionEntryGroup')}")
    names=[g.get("name") or "" for g in gs]
    if any("Prosperine Cult" in n or "Psychic" in n for n in names):
        print("ROOT",e.get("id"),e.get("name"),"groups",names)

print("\\n==== VETERAN MELEE-ish ====")
v=ids["veteran-unit"]
for g in v.iter(C("selectionEntryGroup")):
    n=(g.get("name") or "").lower()
    if any(k in n for k in ["melee","combat","weapon replacement","veteran weapons","power weapon"]):
        print("GROUP",g.get("id"),g.get("name"),"cons",cons(g),"mods",mods(g)[:7000])
        for x in list(g):
            if x.tag in (C("selectionEntry"),C("entryLink")):
                print(" OPT",x.get("id"),x.get("name"),x.get("targetId"),"cost",costs(x),"cons",cons(x),"mods",mods(x)[:4000])

print("\\n==== VETERAN MODEL SELECTORS ====")
for x in v.iter(C("selectionEntry")):
    if x.get("type")=="model":
        print(x.get("id"),x.get("name"),"default",x.get("defaultAmount"),"cons",cons(x),"cost",costs(x))
