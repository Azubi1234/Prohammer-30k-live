import xml.etree.ElementTree as ET, re
NS="http://www.battlescribe.net/schema/catalogueSchema"; C=lambda t:f"{{{NS}}}{t}"
r=ET.parse("Legiones Astartes.cat").getroot()
print("REV",r.get("revision"),"GST",r.get("gameSystemRevision"))
for e in r.iter(C("selectionEntry")):
    direct=[g for g in e.findall(f"./{C('selectionEntryGroups')}/{C('selectionEntryGroup')}")]
    cult=[g for g in direct if (g.get("name") or "")=="Prosperine Cult"]
    disc=[g for g in direct if (g.get("name") or "").startswith("Psychic Brotherhood — Psychic Discipline")]
    power=[g for g in direct if (g.get("name") or "").startswith("Psychic Brotherhood — Psychic Power")]
    if not cult or not power: continue
    print("\\nROOT",e.get("id"),e.get("name"))
    for g in cult+disc+power:
        print(" GROUP",g.get("id"),g.get("name"),"hidden",g.get("hidden"))
        cs=g.find(C("constraints"))
        if cs is not None:
            print("  CONS",[(x.get("id"),x.get("type"),x.get("value")) for x in cs.findall(C("constraint"))])
        m=g.find(C("modifiers"))
        if m is not None: print("  MODS",ET.tostring(m,encoding="unicode")[:7000])
        for tag in ("selectionEntries","entryLinks"):
            cc=g.find(C(tag))
            if cc is None: continue
            for x in list(cc):
                print("  OPT",tag,x.get("id"),x.get("name"),"target",x.get("targetId"),"hidden",x.get("hidden"))
                mm=x.find(C("modifiers"))
                if mm is not None: print("    MODS",ET.tostring(mm,encoding="unicode")[:2500])
    bros=[]
    for x in e.iter():
        if x.tag not in (C("selectionEntry"),C("entryLink")) or x is e: continue
        n=(x.get("name") or "").lower(); xid=x.get("id") or ""
        if "brotherhood of psykers" in n or ("ts-brother" in xid and "disc" not in xid and "power" not in xid):
            bros.append((x.get("id"),x.get("name"),x.get("hidden")))
    print(" BROTHERS",bros)
