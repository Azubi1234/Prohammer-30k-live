from pathlib import Path
import xml.etree.ElementTree as ET

CAT=Path("Legiones-Astartes-Generic.cat")
NS="http://www.battlescribe.net/schema/catalogueSchema"
C=lambda t:f"{{{NS}}}{t}"

root=ET.parse(CAT).getroot()
parent={c:p for p in root.iter() for c in p}

def ancestors(x):
    out=[]
    while x in parent:
        x=parent[x]; out.append(x)
    return out

def nearest_unit(cult_group):
    for a in ancestors(cult_group):
        if a.tag==C("selectionEntry") and a.get("type") in ("unit","model"):
            return a
    return None

def local_brotherhood_ids(unit):
    ids=[]
    for e in unit.iter(C("entryLink")):
        if e.get("targetId") in ("r45-ts-brotherhood","r45-ts-brotherhood-fellowship"):
            ids.append(e.get("id"))
    return [x for x in ids if x]

def condition_ids(x):
    return {c.get("childId") for c in x.iter(C("condition")) if c.get("childId")}

def has_reveal_for(link, local_ids):
    if link.get("hidden")!="true":
        return False
    for m in link.findall(f"./{C('modifiers')}/{C('modifier')}"):
        if m.get("field")=="hidden" and m.get("value")=="false":
            if condition_ids(m) & set(local_ids):
                return True
    return False

def has_min_trigger(group, local_ids):
    mins=[c for c in group.findall(f"./{C('constraints')}/{C('constraint')}") if c.get("type")=="min"]
    if len(mins)!=1:
        return False
    mid=mins[0].get("id")
    for m in group.findall(f"./{C('modifiers')}/{C('modifier')}"):
        if m.get("field")==mid and m.get("value")=="1":
            if condition_ids(m) & set(local_ids):
                return True
    return False

fail=[]
checked=[]

# Canonical package is mandatory.
canonical=next((g for g in root.iter(C("selectionEntryGroup")) if g.get("id")=="r45-cult-terminator-unit"),None)
if canonical is None:
    fail.append("canonical r45-cult-terminator-unit missing")
    groups=[]
else:
    groups=[canonical]

# Also test copied Terminator Cult packages that actually carry Brotherhood links.
for g in root.iter(C("selectionEntryGroup")):
    if g is canonical or (g.get("name") or "")!="Prosperine Cult":
        continue
    if "terminator" not in (g.get("id") or "").lower():
        continue
    u=nearest_unit(g)
    if u is not None and local_brotherhood_ids(u):
        groups.append(g)

for cg in groups:
    unit=nearest_unit(cg)
    if unit is None:
        fail.append(f"{cg.get('id')}: no containing Terminator unit")
        continue
    bids=local_brotherhood_ids(unit)
    if not bids:
        fail.append(f"{cg.get('id')}: no local Brotherhood entryLink IDs")
        continue

    cults=cg.findall(f"./{C('selectionEntries')}/{C('selectionEntry')}")
    if len(cults)!=5:
        fail.append(f"{cg.get('id')}: expected 5 Cults, got {len(cults)}")
        continue

    for cult in cults:
        cname=cult.get("name")
        pgs=[g for g in cult.findall(f"./{C('selectionEntryGroups')}/{C('selectionEntryGroup')}") if (g.get("name") or "")=="Psychic Brotherhood Power — choose 1"]
        if len(pgs)!=1:
            fail.append(f"{cg.get('id')} {cname}: expected exactly 1 power group, got {len(pgs)}")
            continue
        pg=pgs[0]
        powers=pg.findall(f"./{C('entryLinks')}/{C('entryLink')}")
        if len(powers)!=7:
            fail.append(f"{cg.get('id')} {cname}: expected 7 powers, got {len(powers)}")
        if not has_min_trigger(pg,bids):
            fail.append(f"{cg.get('id')} {cname}: group MIN1 is not triggered by local Brotherhood IDs {bids}")
        for p in powers:
            if not has_reveal_for(p,bids):
                fail.append(f"{cg.get('id')} {cname} / {p.get('name')}: no reveal modifier using local Brotherhood IDs {bids}")

        mastery=[x for x in cult.findall(f"./{C('infoLinks')}/{C('infoLink')}") if "Cult Mastery" in (x.get("name") or "")]
        if len(mastery)!=1:
            fail.append(f"{cg.get('id')} {cname}: expected one Cult Mastery link")
        elif not has_reveal_for(mastery[0],bids):
            fail.append(f"{cg.get('id')} {cname}: Cult Mastery has no reveal using local Brotherhood IDs {bids}")

    checked.append((cg.get("id"),unit.get("id"),bids))

print("TS Terminator psychic rendering regression test")
for cg,unit,bids in checked:
    print("CHECKED",cg,"unit",unit,"brotherhood",",".join(bids))
if fail:
    print("FAILURES:",len(fail))
    for x in fail: print("FAIL:",x)
    raise SystemExit(1)
print("PASS: all Terminator Cult power groups, spells and Cult Mastery use local Brotherhood link IDs")
