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
        x=parent[x];out.append(x)
    return out

term=next((g for g in root.iter(C("selectionEntryGroup")) if g.get("id")=="r45-cult-terminator-unit"),None)
vet=next((g for g in root.iter(C("selectionEntryGroup")) if g.get("id")=="r45-cult-veteran-unit"),None)
if term is None or vet is None: raise SystemExit("missing canonical Cult groups")
unit=next((a for a in ancestors(term) if a.tag==C("selectionEntry") and a.get("type") in ("unit","model")),None)
if unit is None: raise SystemExit("canonical Terminator unit missing")
bids=[e.get("id") for e in unit.iter(C("entryLink")) if e.get("targetId") in ("r45-ts-brotherhood","r45-ts-brotherhood-fellowship")]
bids=[x for x in bids if x]

vm={c.get("name"):c for c in vet.findall(f"./{C('selectionEntries')}/{C('selectionEntry')}")}
tm={c.get("name"):c for c in term.findall(f"./{C('selectionEntries')}/{C('selectionEntry')}")}
fail=[]
for cname in ("Pavoni","Raptora","Corvidae","Athanaeans","Pyrae"):
    vg=[g for g in vm[cname].findall(f"./{C('selectionEntryGroups')}/{C('selectionEntryGroup')}") if (g.get("name") or "")=="Psychic Brotherhood Power — choose 1"]
    tg=[g for g in tm[cname].findall(f"./{C('selectionEntryGroups')}/{C('selectionEntryGroup')}") if (g.get("name") or "")=="Psychic Brotherhood Power — choose 1"]
    if len(vg)!=1 or len(tg)!=1:
        fail.append(f"{cname}: veteran/terminator group count mismatch");continue
    v=vg[0];t=tg[0]
    vp=v.findall(f"./{C('entryLinks')}/{C('entryLink')}")
    tp=t.findall(f"./{C('entryLinks')}/{C('entryLink')}")
    if [x.get("targetId") for x in vp] != [x.get("targetId") for x in tp]:
        fail.append(f"{cname}: spell targets differ from Veteran")
    if t.get("hidden")!="true":
        fail.append(f"{cname}: Terminator parent group not hidden before Brotherhood")
    if any(x.get("hidden")=="true" for x in tp):
        fail.append(f"{cname}: Terminator child spell link hidden")
    txt=ET.tostring(t,encoding="unicode")
    for bid in bids:
        if bid not in txt: fail.append(f"{cname}: local Brotherhood gate {bid} absent")
    if 'field="hidden" value="false"' not in txt:
        fail.append(f"{cname}: parent reveal missing")
    mins=[c for c in t.findall(f"./{C('constraints')}/{C('constraint')}") if c.get("type")=="min"]
    maxs=[c for c in t.findall(f"./{C('constraints')}/{C('constraint')}") if c.get("type")=="max"]
    if len(mins)!=1 or mins[0].get("value")!="0": fail.append(f"{cname}: baseline MIN not 0")
    if len(maxs)!=1 or maxs[0].get("value")!="1": fail.append(f"{cname}: MAX not 1")
    if mins and f'field="{mins[0].get("id")}" value="1"' not in txt:
        fail.append(f"{cname}: Brotherhood MIN1 trigger missing")

print("TS Terminator renderability test — exact Veteran pattern")
if fail:
    for x in fail: print("FAIL:",x)
    raise SystemExit(1)
print("PASS: Terminator groups mirror working Veteran UI pattern; child spells are not hidden")
