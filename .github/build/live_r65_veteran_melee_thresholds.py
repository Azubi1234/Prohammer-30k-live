from pathlib import Path
import collections, xml.etree.ElementTree as ET

CAT=Path("Legiones Astartes.cat"); IDX=Path("index.xml")
OUT=Path("inspection-live-r65-veteran-melee-thresholds.txt")
NS="http://www.battlescribe.net/schema/catalogueSchema"; INS="http://www.battlescribe.net/schema/dataIndexSchema"
ET.register_namespace("",NS)
C=lambda t:f"{{{NS}}}{t}"; I=lambda t:f"{{{INS}}}{t}"

tree=ET.parse(CAT); root=tree.getroot()
if root.get("revision")!="64": raise RuntimeError(f"R65 expected CAT64, got {root.get('revision')}")
if root.get("gameSystemRevision")!="15": raise RuntimeError(f"R65 expected GST15, got {root.get('gameSystemRevision')}")
baseline=collections.Counter(x.get("id") for x in root.iter() if x.get("id"))

def cont(p,tag,before=("constraints","categoryLinks","entryLinks","infoLinks","profiles","rules","selectionEntries","selectionEntryGroups","costs","modifiers")):
    q=C(tag); x=p.find(q)
    if x is not None:return x
    x=ET.Element(q); kids=list(p); idx=len(kids)
    for j,k in enumerate(kids):
        if k.tag.split("}")[-1] in before: idx=j; break
    p.insert(idx,x); return x

def ensure_max(g,id_,value):
    cs=cont(g,"constraints")
    hits=[x for x in cs.findall(C("constraint")) if x.get("type")=="max"]
    x=hits[0] if hits else ET.SubElement(cs,C("constraint"))
    x.attrib.update({
        "id":id_,"type":"max","value":str(value),"field":"selections","scope":"parent",
        "shared":"true","includeChildSelections":"false","includeChildForces":"false"
    })
    for extra in hits[1:]: cs.remove(extra)
    return x

def clear_field_mods(e,field):
    ms=e.find(C("modifiers"))
    if ms is None:return 0
    n=0
    for m in list(ms):
        if m.get("field")==field:
            ms.remove(m); n+=1
    return n

def add_threshold(g,id_,field,model_id,model_count,total_cap):
    ms=cont(g,"modifiers")
    m=ET.SubElement(ms,C("modifier"),{
        "id":id_,"type":"set","field":field,"value":str(total_cap)
    })
    conds=ET.SubElement(m,C("conditions"))
    ET.SubElement(conds,C("condition"),{
        "type":"atLeast","value":str(model_count),"field":"selections","scope":"root-entry",
        "childId":model_id,"shared":"true","includeChildSelections":"false","includeChildForces":"false"
    })
    return m

patched=[]
for e in root.iter(C("selectionEntry")):
    vm=next((x for x in e.findall(f"./{C('selectionEntries')}/{C('selectionEntry')}")
             if x.get("type")=="model" and (x.get("name") or "")=="Legion Veterans"),None)
    if vm is None: continue

    mg=next((g for g in e.findall(f"./{C('selectionEntryGroups')}/{C('selectionEntryGroup')}")
             if (g.get("name") or "")=="Close Combat Weapon Replacements"),None)
    if mg is None: continue

    # Veteran squad = Sergeant + 4–9 Legion Veterans.
    mx=ensure_max(mg,(mg.get("id") or e.get("id")+"-melee")+"-max",5)
    removed=clear_field_mods(mg,mx.get("id"))

    # New Recruit-safe explicit thresholds.
    # Legion Veterans 4 => total squad 5 (base max 5).
    # Legion Veterans 5..9 => total squad 6..10.
    for veteran_models in range(5,10):
        total=veteran_models+1
        add_threshold(
            mg,
            f"{mg.get('id') or e.get('id')}-r65-total-{total}",
            mx.get("id"),
            vm.get("id"),
            veteran_models,
            total
        )

    # Individual melee option entries must not impose a lower cap.
    for l in mg.findall(f"./{C('entryLinks')}/{C('entryLink')}"):
        cs=l.find(C("constraints"))
        if cs is None: continue
        for c in cs.findall(C("constraint")):
            if c.get("type")=="max":
                try:v=float(c.get("value","0"))
                except: v=0
                if v<10:c.set("value","10")

    patched.append((e.get("id"),e.get("name"),mg.get("id"),vm.get("id"),removed))

if not patched: raise RuntimeError("No Veteran melee groups found")
if not any(x[0]=="veteran-unit" for x in patched): raise RuntimeError("Main Veteran squad was not patched")

# Revision/index.
root.set("revision","65")
tree.write(CAT,encoding="utf-8",xml_declaration=True)

ET.register_namespace("",INS)
it=ET.parse(IDX); ir=it.getroot()
for x in ir.iter(I("dataIndexEntry")):
    if x.get("filePath")=="Legiones Astartes.cat":
        x.set("dataRevision","65")
it.write(IDX,encoding="utf-8",xml_declaration=True)

# Validate.
rr=ET.parse(CAT).getroot(); rids={x.get("id"):x for x in rr.iter() if x.get("id")}; checks=[]
def ck(n,o):
    checks.append((n,bool(o)))
    if not o: raise RuntimeError("R65 validation failed: "+n)

ck("CAT65",rr.get("revision")=="65")
ck("GST dependency remains 15",rr.get("gameSystemRevision")=="15")
ck("Index65",'dataRevision="65"' in IDX.read_text(encoding="utf-8"))

main=rids["veteran-unit"]
vm=next(x for x in main.findall(f"./{C('selectionEntries')}/{C('selectionEntry')}") if x.get("name")=="Legion Veterans")
mg=next(g for g in main.findall(f"./{C('selectionEntryGroups')}/{C('selectionEntryGroup')}") if g.get("name")=="Close Combat Weapon Replacements")
mx=next(x for x in mg.findall(f"./{C('constraints')}/{C('constraint')}") if x.get("type")=="max")
ck("Main Veteran melee base cap 5",mx.get("value")=="5")
txt=ET.tostring(mg,encoding="unicode")
ck("6-model threshold present",f'{vm.get("id")}' in txt and 'value="6"' in txt)
ck("10-model threshold present",'value="10"' in txt and 'value="9"' in txt)
ck("R64 repeat scaler removed","r64-total-models" not in txt)
ck("No repeat arithmetic remains","<ns0:repeats" not in txt and "<repeats" not in txt)
ck("All live Veteran roots patched",len(patched)>=2)

new=collections.Counter(x.get("id") for x in rr.iter() if x.get("id"))
worse={k:v for k,v in new.items() if v>max(1,baseline.get(k,0))}
ck("No new/worsened duplicate IDs",not worse)

OUT.write_text("\n".join([
    "Live R65 — Veteran melee threshold fix",
    "Input CAT64/GST15 -> CAT65/GST15","",
    "FIX:",
    f"- Replaced repeat-based melee scaling on {len(patched)} live Veteran roots with explicit New Recruit-safe thresholds.",
    "- 5 total models -> max 5 melee weapon replacements.",
    "- 6 total models -> max 6.",
    "- 7 total models -> max 7.",
    "- 8 total models -> max 8.",
    "- 9 total models -> max 9.",
    "- 10 total models -> max 10.",
    "- The Veteran Sergeant is included in the allowance.",
    "- Individual melee weapon links are capped high enough not to override the squad-level limit.",
    "- Removed the R64 repeat arithmetic that New Recruit was failing to recalculate after squad-size changes.","",
    "PATCHED ROOTS:"
]+[f"- {eid}: {name} ({gid}; models={mid}; removed {removed} old cap modifier(s))" for eid,name,gid,mid,removed in patched]+[
    "","VALIDATION:"
]+[f'- {"PASS" if ok else "FAIL"}: {n}' for n,ok in checks])+"\n",encoding="utf-8")
print(OUT.read_text())
