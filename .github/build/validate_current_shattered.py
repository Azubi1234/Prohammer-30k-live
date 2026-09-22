from pathlib import Path
import xml.etree.ElementTree as ET, collections, re
CAT=Path("Legiones Astartes.cat"); GST=Path("Prohammer 30k.gst")
OUT=Path("inspection-current-shattered-legions-r64.txt")
NS="http://www.battlescribe.net/schema/catalogueSchema"; GNS="http://www.battlescribe.net/schema/gameSystemSchema"
C=lambda t:f"{{{NS}}}{t}"; G=lambda t:f"{{{GNS}}}{t}"
r=ET.parse(CAT).getroot(); g=ET.parse(GST).getroot(); ids={x.get("id"):x for x in r.iter() if x.get("id")}
checks=[]; lines=[f"CAT={r.get('revision')} GST={g.get('revision')}"]
def ck(n,o):
    checks.append((n,bool(o))); lines.append(f'{"PASS" if o else "FAIL"}: {n}')
THEME="r62-shattered-theme"
ck("Theme exists",THEME in ids)
if THEME in ids:
    th=ids[THEME]
    cg=next((x for x in th.findall(f"./{C('selectionEntryGroups')}/{C('selectionEntryGroup')}") if x.get("id")=="r62-shattered-constituents"),None)
    wg=next((x for x in th.findall(f"./{C('selectionEntryGroups')}/{C('selectionEntryGroup')}") if x.get("id")=="r62-shattered-warlord"),None)
    ck("Constituent selector exists",cg is not None)
    ck("Warlord selector exists",wg is not None)
    if cg is not None:
        opts=cg.findall(f"./{C('selectionEntries')}/{C('selectionEntry')}")
        vals={(x.get("type"),x.get("value")) for x in cg.findall(f"./{C('constraints')}/{C('constraint')}")}
        ck("18 constituent Legions",len(opts)==18)
        ck("Constituent min2 max3",("min","2") in vals and ("max","3") in vals)
    if wg is not None:
        opts=wg.findall(f"./{C('selectionEntries')}/{C('selectionEntry')}")
        vals={(x.get("type"),x.get("value")) for x in wg.findall(f"./{C('constraints')}/{C('constraint')}")}
        ck("18 Warlord choices",len(opts)==18)
        ck("Warlord min1 max1",("min","1") in vals and ("max","1") in vals)
        ck("Warlord choices gated by constituent",all("r62-shat-const-" in ET.tostring(x,encoding="unicode") for x in opts))

# Count generic assignment selectors.
assign_groups=[x for x in r.iter(C("selectionEntryGroup")) if (x.get("name") or "")=="Shattered Legions — Assigned Legion"]
ck("Assignment selectors present",len(assign_groups)>=100)
ck("Each assignment has 18 choices",all(len(x.findall(f"./{C('selectionEntries')}/{C('selectionEntry')}"))==18 for x in assign_groups))
for eid in ["hq-praetor","hq-centurion","tactical-unit","veteran-unit","terminator-unit","recon-unit"]:
    e=ids.get(eid)
    gs=[] if e is None else [x for x in e.findall(f"./{C('selectionEntryGroups')}/{C('selectionEntryGroup')}") if (x.get("name") or "")=="Shattered Legions — Assigned Legion"]
    ck(eid+" assignment",len(gs)==1)

# Special-unit protections and primarch block.
special_limits=[x for x in g.iter(G("categoryEntry")) if (x.get("id") or "").startswith("r62-shat-limit-")]
ck("Shattered special-unit 0-1 categories present",len(special_limits)>=50)
hqreq=sum(1 for x in r.iter(C("modifier")) if (x.get("id") or "").startswith("r62-shat-hqreq-"))
ck("Same-Legion HQ requirement modifiers present",hqreq>=50)
prim=[]
for e in r.iter(C("selectionEntry")):
    names=[x.get("name") or "" for x in e.findall(f"./{C('rules')}/{C('rule')}")]+[x.get("name") or "" for x in e.findall(f"./{C('infoLinks')}/{C('infoLink')}")]
    if any(n=="Primarch" for n in names):prim.append(e)
ck("Primarchs detected",len(prim)>0)
ck("All Primarchs blocked in Shattered",all(THEME in ET.tostring(e,encoding="unicode") for e in prim))

# Alpha Legion special shared Mutable Tactic.
if THEME in ids:
    ck("Shattered Alpha Mutable Tactic exists",any((x.get("id") or "")=="r62-shat-alpha-mutable" for x in ids[THEME].iter(C("selectionEntryGroup"))))

# Ensure single-Legion config and Shattered share the same max1 parent.
cfg=ids.get("config-legion")
if cfg is not None:
    vals={(x.get("type"),x.get("value")) for x in cfg.findall(f"./{C('constraints')}/{C('constraint')}")}
    ck("Legion config remains one-of",("max","1") in vals and ("min","1") in vals)
    ck("Shattered Theme is inside Legion Configuration",any(x.get("id")==THEME for x in cfg.findall(f"./{C('selectionEntries')}/{C('selectionEntry')}")))

OUT.write_text("\n".join(lines+["",f"Assignment groups: {len(assign_groups)}",f"Special 0-1 categories: {len(special_limits)}",f"HQ requirement modifiers: {hqreq}",f"Primarchs checked: {len(prim)}"])+"\n",encoding="utf-8")
print(OUT.read_text())
