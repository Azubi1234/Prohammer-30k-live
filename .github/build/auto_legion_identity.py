from pathlib import Path
import re
import xml.etree.ElementTree as ET

LEGIONS = [
("Dark-Angels.cat","legion-i","auto-legion-marker-i"),("Emperor-s-Children.cat","legion-iii","auto-legion-marker-iii"),
("Iron-Warriors.cat","legion-iv","auto-legion-marker-iv"),("White-Scars.cat","legion-v","auto-legion-marker-v"),
("Space-Wolves.cat","legion-vi","auto-legion-marker-vi"),("Imperial-Fists.cat","legion-vii","auto-legion-marker-vii"),
("Night-Lords.cat","legion-viii","auto-legion-marker-viii"),("Blood-Angels.cat","legion-ix","auto-legion-marker-ix"),
("Iron-Hands.cat","legion-x","auto-legion-marker-x"),("World-Eaters.cat","legion-xii","auto-legion-marker-xii"),
("Ultramarines.cat","legion-xiii","auto-legion-marker-xiii"),("Death-Guard.cat","legion-xiv","auto-legion-marker-xiv"),
("Thousand-Sons.cat","legion-xv","auto-legion-marker-xv"),("Sons-of-Horus.cat","legion-xvi","auto-legion-marker-xvi"),
("Word-Bearers.cat","legion-xvii","auto-legion-marker-xvii"),("Salamanders.cat","legion-xviii","auto-legion-marker-xviii"),
("Raven-Guard.cat","legion-xix","auto-legion-marker-xix"),("Alpha-Legion.cat","legion-xx","auto-legion-marker-xx")]
NS="http://www.battlescribe.net/schema/catalogueSchema"
ET.register_namespace("",NS)
q=lambda x:f"{{{NS}}}{x}"

def cont(parent, tag):
    x=parent.find(q(tag))
    if x is None:
        x=ET.SubElement(parent,q(tag))
    return x

def patch_generic(path):
    tree=ET.parse(path); root=tree.getroot()
    before=ET.tostring(root,encoding="utf-8")
    group=root.find(".//"+q("selectionEntryGroup")+"[@id='config-legion']")
    if group is None:
        raise RuntimeError(f"{path}: config-legion missing")
    all_entries=group.findall("./"+q("selectionEntries")+"/"+q("selectionEntry"))
    entries={e.get("id"):e for e in all_entries}
    # A normal Legion catalogue must not expose Shattered Legions Theme or any
    # other alternate identity selector. Hide everything first; the matching
    # Legion is selectively revealed by its automatic catalogue marker below.
    for e in all_entries:
        e.set("hidden","true")
    missing=[lid for _,lid,_ in LEGIONS if lid not in entries]
    if missing:
        raise RuntimeError(f"{path}: missing Legion selectors {missing}")

    # Shattered Legions is a separate army-building mode, not an alternative
    # Legion choice inside every normal modular Legion roster. Preserve all of
    # its rules/data but hide the theme selector in standard Legion catalogues.
    shattered=entries.get("r62-shattered-theme")
    if shattered is not None:
        shattered.set("hidden","true")
        sms=shattered.find(q("modifiers"))
        if sms is not None:
            for m in list(sms):
                if m.get("field")=="hidden" and m.get("value")=="false":
                    sms.remove(m)

    for _,lid,marker in LEGIONS:
        e=entries[lid]
        e.set("hidden","true")
        cons=cont(e,"constraints")
        for c in list(cons):
            if c.get("id")==lid+"-auto-min":
                cons.remove(c)
        cid=lid+"-auto-min"
        ET.SubElement(cons,q("constraint"),{
            "id":cid,"type":"min","value":"0","field":"selections","scope":"parent",
            "shared":"true","includeChildSelections":"false","automatic":"true"
        })
        mods=cont(e,"modifiers")
        for m in list(mods):
            if (m.get("id") or "").startswith(lid+"-auto-"):
                mods.remove(m)
        m=ET.SubElement(mods,q("modifier"),{"id":lid+"-auto-hide","type":"set","field":"hidden","value":"false"})
        cs=ET.SubElement(m,q("conditions"))
        ET.SubElement(cs,q("condition"),{
            "type":"atLeast","value":"1","field":"selections","scope":"roster","childId":marker,
            "shared":"true","includeChildSelections":"true","includeChildForces":"false"
        })
        m=ET.SubElement(mods,q("modifier"),{"id":lid+"-auto-min-on","type":"set","field":cid,"value":"1"})
        cs=ET.SubElement(m,q("conditions"))
        ET.SubElement(cs,q("condition"),{
            "type":"atLeast","value":"1","field":"selections","scope":"roster","childId":marker,
            "shared":"true","includeChildSelections":"true","includeChildForces":"false"
        })
    changed=ET.tostring(root,encoding="utf-8")!=before
    if changed:
        root.set("revision",str(int(root.get("revision","0"))+1))
        tree.write(path,encoding="utf-8",xml_declaration=True)
    return int(root.get("revision","0")),changed

def patch_legion(path, marker):
    # Older string-based modular patches left a duplicate importRootEntries
    # attribute in at least one Legion catalogue. Repair only the exact duplicate
    # attribute form before XML parsing; no rules/options are otherwise touched.
    raw=path.read_text(encoding="utf-8")
    clean=re.sub(r'(\simportRootEntries="true")\s+importRootEntries="true"',r'\1',raw)
    clean=re.sub(r'(\simportRootEntries="false")\s+importRootEntries="false"',r'\1',clean)
    precleaned=clean!=raw
    if precleaned:
        path.write_text(clean,encoding="utf-8")
    tree=ET.parse(path); root=tree.getroot()
    before=ET.tostring(root,encoding="utf-8")
    ses=cont(root,"selectionEntries")
    e=next((x for x in ses.findall(q("selectionEntry")) if x.get("id")==marker),None)
    if e is None:
        e=ET.SubElement(ses,q("selectionEntry"),{
            "type":"upgrade","name":"Automatic Legion Identity","id":marker,
            "hidden":"true","import":"true"
        })
    e.set("hidden","true"); e.set("import","true")
    cons=cont(e,"constraints")
    for c in list(cons):
        if c.get("id") in (marker+"-min",marker+"-max"):
            cons.remove(c)
    ET.SubElement(cons,q("constraint"),{
        "id":marker+"-min","type":"min","value":"1","field":"selections","scope":"parent",
        "shared":"true","includeChildSelections":"false","automatic":"true"
    })
    ET.SubElement(cons,q("constraint"),{
        "id":marker+"-max","type":"max","value":"1","field":"selections","scope":"parent",
        "shared":"true","includeChildSelections":"false"
    })
    costs=cont(e,"costs")
    if not any(c.get("typeId")=="51b2-306e-1021-d207" for c in costs.findall(q("cost"))):
        ET.SubElement(costs,q("cost"),{"name":"Points","typeId":"51b2-306e-1021-d207","value":"0"})
    changed=precleaned or ET.tostring(root,encoding="utf-8")!=before
    if changed:
        root.set("revision",str(int(root.get("revision","0"))+1))
        tree.write(path,encoding="utf-8",xml_declaration=True)
    return int(root.get("revision","0")),changed

generic_rev,generic_changed=patch_generic(Path("Legiones-Astartes-Generic.cat"))
revs={"Legiones-Astartes-Generic.cat":generic_rev}
changed_legions=[]
for fn,_,marker in LEGIONS:
    rev,changed=patch_legion(Path(fn),marker)
    revs[fn]=rev
    if changed: changed_legions.append(fn)

# Keep the staged Generic library in sync when present. Legion staging files are
# not rewritten here; this avoids unrelated Legion churn during shared-list fixes.
staged=Path("modular-catalogues-generated/Legiones-Astartes-Generic.cat")
if staged.exists():
    patch_generic(staged)

ip=Path("index.xml")
it=ET.parse(ip); ir=it.getroot()
for e in ir.iter():
    if not e.tag.endswith("dataIndexEntry"): continue
    fp=e.get("filePath")
    if fp in revs:
        e.set("dataRevision",str(revs[fp]))
it.write(ip,encoding="utf-8",xml_declaration=True)

print("Generic auto-Legion wiring:", "updated" if generic_changed else "already current", "revision", generic_rev)
print("Legion identity markers changed:", changed_legions if changed_legions else "none")
