import xml.etree.ElementTree as ET,re
NS="http://www.battlescribe.net/schema/catalogueSchema"; C=lambda t:f"{{{NS}}}{t}"
r=ET.parse("Legiones Astartes.cat").getroot(); ids={x.get("id"):x for x in r.iter() if x.get("id")}
def cons(e): return [(x.get("id"),x.get("type"),x.get("value"),x.get("scope"),x.get("field")) for x in e.findall(f"./{C('constraints')}/{C('constraint')}")]
def mods(e):
    m=e.find(C("modifiers")); return ET.tostring(m,encoding="unicode") if m is not None else ""
def cost(e): return [(x.get("typeId"),x.get("value")) for x in e.findall(f"./{C('costs')}/{C('cost')}")]
def print_group(g):
    print("GROUP",g.get("id"),"|",g.get("name"),"| hidden",g.get("hidden"),"| cons",cons(g))
    print(" MODS",mods(g))
    for tag in ("selectionEntries","entryLinks"):
        cc=g.find(C(tag))
        if cc is None: continue
        for x in list(cc):
            print("  OPT",x.get("id"),"|",x.get("name"),"| target",x.get("targetId"),"| hidden",x.get("hidden"),"| cost",cost(x),"| cons",cons(x))
            print("   MODS",mods(x))
print("REV",r.get("revision"))
for eid in ["hq-centurion","hq-praetor"]:
    e=ids[eid]
    print("\\n====",eid,e.get("name"),"====")
    for g in e.findall(f"./{C('selectionEntryGroups')}/{C('selectionEntryGroup')}"):
        n=(g.get("name") or "").lower(); gid=g.get("id") or ""
        if any(k in n for k in ["cult","psychic","discipline","power"]) or "ts-" in gid:
            print_group(g)
    print("DIRECT INFOS",[(x.get("id"),x.get("name"),x.get("targetId"),x.get("hidden"),mods(x)) for x in e.findall(f"./{C('infoLinks')}/{C('infoLink')}") if "psy" in (x.get("name") or "").lower() or "thousand" in (x.get("name") or "").lower()])
    print("DIRECT RULES",[(x.get("id"),x.get("name"),(x.findtext(C("description")) or "")[:400]) for x in e.findall(f"./{C('rules')}/{C('rule')}") if "psy" in (x.get("name") or "").lower() or "thousand" in (x.get("name") or "").lower()])

v=ids["veteran-unit"]
print("\\n==== VETERAN MODEL COUNTS ====")
for x in v.iter(C("selectionEntry")):
    if x.get("type")=="model": print(x.get("id"),x.get("name"),"default",x.get("defaultAmount"),"cons",cons(x),"cost",cost(x))
print("\\n==== VETERAN GROUPS WITH MAX5 OR MELEE ====")
for g in v.iter(C("selectionEntryGroup")):
    s=str(cons(g))+" "+mods(g)+" "+(g.get("name") or "")
    if "5" in s or any(k in (g.get("name") or "").lower() for k in ["melee","combat","weapon"]):
        # only groups plausibly weapon options
        if any(k in (g.get("name") or "").lower() for k in ["melee","combat","weapon","armoury","specialist"]):
            print_group(g)

print("\\n==== BROTHERHOOD/CULT/POWER ON VETERAN ====")
for g in v.findall(f"./{C('selectionEntryGroups')}/{C('selectionEntryGroup')}"):
    if any(k in (g.get("name") or "") for k in ["Prosperine","Psychic Brotherhood"]): print_group(g)
