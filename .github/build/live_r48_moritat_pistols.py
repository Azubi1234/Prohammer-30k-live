from pathlib import Path
import collections, xml.etree.ElementTree as ET

CAT=Path("Legiones Astartes.cat"); IDX=Path("index.xml")
OUT=Path("inspection-live-r48-moritat-pistol-replacement.txt")
NS="http://www.battlescribe.net/schema/catalogueSchema"; INS="http://www.battlescribe.net/schema/dataIndexSchema"
ET.register_namespace("",NS)
C=lambda t:f"{{{NS}}}{t}"; I=lambda t:f"{{{INS}}}{t}"

tree=ET.parse(CAT); root=tree.getroot()
if root.get("revision")!="47": raise RuntimeError(f"R48 expected CAT47, got {root.get('revision')}")
if root.get("gameSystemRevision")!="11": raise RuntimeError(f"R48 expected GST dependency 11, got {root.get('gameSystemRevision')}")
baseline=collections.Counter(x.get("id") for x in root.iter() if x.get("id"))
ids={x.get("id"):x for x in root.iter() if x.get("id")}

mor=ids.get("hq-consul-moritat")
if mor is None: raise RuntimeError("Moritat entry missing")
pair=next((g for g in mor.iter(C("selectionEntryGroup")) if g.get("id")=="r29-mor-pair-group"),None)
if pair is None: raise RuntimeError("Moritat Pistol Pair group missing")

# The group itself is mandatory one-of-one.
pcs=pair.find(C("constraints"))
if pcs is None: raise RuntimeError("Pistol Pair group constraints missing")
mins=[x for x in pcs.findall(C("constraint")) if x.get("type")=="min"]
maxs=[x for x in pcs.findall(C("constraint")) if x.get("type")=="max"]
if not mins or not maxs: raise RuntimeError("Pistol Pair min/max constraints missing")
for x in mins: x.set("value","1")
for x in maxs: x.set("value","1")

# The default Bolt Pistol pair must NOT itself be mandatory.
# Its old child-level min 1 caused New Recruit to show 2/1 when a replacement was chosen.
bolt=ids.get("r29-mor-bolt")
if bolt is None: raise RuntimeError("Two Bolt Pistols option missing")
bcs=bolt.find(C("constraints"))
removed_bolt_min=0
if bcs is not None:
    for x in list(bcs):
        if x.get("type")=="min":
            bcs.remove(x); removed_bolt_min+=1
bolt.set("defaultAmount","1")

# Ensure all whole-pair replacements live INSIDE the same mutually exclusive group.
pair_ses=pair.find(C("selectionEntries"))
if pair_ses is None:
    pair_ses=ET.SubElement(pair,C("selectionEntries"))

ful=ids.get("r47-rg-mor-fulcrum-pair")
if ful is None: raise RuntimeError("Raven Guard Fulcrum pair missing")
# It should already be here; move it if not.
parent_map={c:p for p in root.iter() for c in p}
fp=parent_map.get(ful)
if fp is not pair_ses:
    if fp is not None: fp.remove(ful)
    pair_ses.append(ful)

# Blood Angels' "replace both" option had historically sat beside the group.
# Move it into the same one-of selector so that replacement semantics are correct there too.
inferno=ids.get("r74-ba-moritat-two-inferno")
moved_inferno=False
if inferno is not None:
    parent_map={c:p for p in root.iter() for c in p}
    ip=parent_map.get(inferno)
    if ip is not pair_ses:
        if ip is not None: ip.remove(inferno)
        pair_ses.append(inferno); moved_inferno=True

# Remove any child-level minimum constraints from replacement choices.
# The group enforces exactly one choice; individual choices must remain freely replaceable.
replacement_ids=["r29-mor-hand","r29-mor-plasma","r29-mor-calibanite","r47-rg-mor-fulcrum-pair","r74-ba-moritat-two-inferno"]
removed_other_mins=0
for rid in replacement_ids:
    e=ids.get(rid)
    if e is None: continue
    cs=e.find(C("constraints"))
    if cs is not None:
        for x in list(cs):
            if x.get("type")=="min":
                cs.remove(x); removed_other_mins+=1

# Revision/index.
root.set("revision","48")
tree.write(CAT,encoding="utf-8",xml_declaration=True)
ET.register_namespace("",INS)
it=ET.parse(IDX); ir=it.getroot()
for x in ir.iter(I("dataIndexEntry")):
    if x.get("filePath")=="Legiones Astartes.cat": x.set("dataRevision","48")
it.write(IDX,encoding="utf-8",xml_declaration=True)

# Validation.
rr=ET.parse(CAT).getroot(); rids={x.get("id"):x for x in rr.iter() if x.get("id")}; checks=[]
def ck(name,ok):
    checks.append((name,bool(ok)))
    if not ok: raise RuntimeError("R48 validation failed: "+name)

ck("CAT48",rr.get("revision")=="48")
ck("GST dependency remains 11",rr.get("gameSystemRevision")=="11")
ck("Index48",'dataRevision="48"' in IDX.read_text(encoding="utf-8"))

rm=rids["hq-consul-moritat"]
pg=next(g for g in rm.iter(C("selectionEntryGroup")) if g.get("id")=="r29-mor-pair-group")
pcons=pg.find(C("constraints"))
ck("Pistol Pair min1",any(x.get("type")=="min" and x.get("value")=="1" for x in pcons.findall(C("constraint"))))
ck("Pistol Pair max1",any(x.get("type")=="max" and x.get("value")=="1" for x in pcons.findall(C("constraint"))))

rb=rids["r29-mor-bolt"]; rbcs=rb.find(C("constraints"))
ck("Bolt Pistols are default",rb.get("defaultAmount")=="1")
ck("Bolt Pistols no child min",rbcs is None or not any(x.get("type")=="min" for x in rbcs.findall(C("constraint"))))

direct_ids={x.get("id") for x in pg.findall(f"./{C('selectionEntries')}/{C('selectionEntry')}")}
ck("Fulcrum pair is inside one-of group","r47-rg-mor-fulcrum-pair" in direct_ids)
ck("Hand Flamers are inside one-of group","r29-mor-hand" in direct_ids)
ck("Plasma Pistols are inside one-of group","r29-mor-plasma" in direct_ids)
ck("Calibanite Pistols are inside one-of group","r29-mor-calibanite" in direct_ids)
if inferno is not None: ck("Inferno Pistols are inside one-of group","r74-ba-moritat-two-inferno" in direct_ids)

rf=rids["r47-rg-mor-fulcrum-pair"]
ck("Fulcrum pair still costs 20",any(x.get("typeId")=="pts" and x.get("value")=="20" for x in rf.findall(f"./{C('costs')}/{C('cost')}")))
ck("Fulcrum pair still Raven Guard gated","legion-xix" in ET.tostring(rf,encoding="unicode"))

new=collections.Counter(x.get("id") for x in rr.iter() if x.get("id"))
worse={k:v for k,v in new.items() if v>max(1,baseline.get(k,0))}
ck("No new/worsened duplicate IDs",not worse)

OUT.write_text("\n".join([
"Live R48 — Moritat pistol replacement fix",
"Input CAT=47/GST=11 -> CAT=48/GST remains 11","",
"FIX:",
"- Moritat Pistol Pair remains a mandatory one-of-one selector.",
f"- Removed {removed_bolt_min} child-level minimum constraint from Two Bolt Pistols, so the default pair can actually be replaced.",
"- Two Bolt Pistols remain the default selection when no replacement is chosen.",
"- Two Fulcrum Hand Cannons remain Raven Guard-only at +20 points and now function as a true replacement rather than an additional second pair.",
"- Hand Flamers, Plasma Pistols and Calibanite Plasma Pistols remain mutually exclusive alternatives in the same group.",
f"- Blood Angels Two Inferno Pistols moved into the same replacement group: {'yes' if moved_inferno else 'already there / unavailable'}.",
f"- Removed {removed_other_mins} additional child-level minimum constraint(s) from replacement choices.","",
"VALIDATION:"
]+[f'- {"PASS" if ok else "FAIL"}: {n}' for n,ok in checks])+"\n",encoding="utf-8")
print(OUT.read_text())
