from pathlib import Path
import copy,re,xml.etree.ElementTree as ET

GEN=Path("Legiones-Astartes-Generic.cat")
IDX=Path("index.xml")
NS="http://www.battlescribe.net/schema/catalogueSchema"
INS="http://www.battlescribe.net/schema/dataIndexSchema"
ET.register_namespace("",NS)
C=lambda t:f"{{{NS}}}{t}"
I=lambda t:f"{{{INS}}}{t}"

LEGIONS=[
("Dark-Angels.cat","legion-i"),("Emperor-s-Children.cat","legion-iii"),
("Iron-Warriors.cat","legion-iv"),("White-Scars.cat","legion-v"),
("Space-Wolves.cat","legion-vi"),("Imperial-Fists.cat","legion-vii"),
("Night-Lords.cat","legion-viii"),("Blood-Angels.cat","legion-ix"),
("Iron-Hands.cat","legion-x"),("World-Eaters.cat","legion-xii"),
("Ultramarines.cat","legion-xiii"),("Death-Guard.cat","legion-xiv"),
("Thousand-Sons.cat","legion-xv"),("Sons-of-Horus.cat","legion-xvi"),
("Word-Bearers.cat","legion-xvii"),("Salamanders.cat","legion-xviii"),
("Raven-Guard.cat","legion-xix"),("Alpha-Legion.cat","legion-xx")]

def parent_of(root,target):
    for p in root.iter():
        if target in list(p): return p
    return None

def sanitize(path):
    raw=path.read_text(encoding="utf-8")
    clean=re.sub(r'(\simportRootEntries="true")\s+importRootEntries="true"',r'\1',raw)
    clean=re.sub(r'(\simportRootEntries="false")\s+importRootEntries="false"',r'\1',clean)
    if clean!=raw:path.write_text(clean,encoding="utf-8")

# On the first structural run, Generic still contains the full Army Configuration
# and is the authoritative template. On later runs Generic is intentionally clean,
# so reuse each Legion catalogue's already-local configuration instead.
gt=ET.parse(GEN); gr=gt.getroot()
config=next((e for e in gr.findall(f"./{C('selectionEntries')}/{C('selectionEntry')}") if e.get("id")=="config-army"),None)
full_template=copy.deepcopy(config) if config is not None else None

if config is not None:
    gparent=parent_of(gr,config)
    gparent.remove(config)
    gr.set("revision",str(int(gr.get("revision","0"))+1))
    gt.write(GEN,encoding="utf-8",xml_declaration=True)

revisions={GEN.name:int(gr.get("revision","0"))}
for fn,lid in LEGIONS:
    p=Path(fn); sanitize(p)
    t=ET.parse(p); r=t.getroot()
    ses=r.find(C("selectionEntries"))
    if ses is None: ses=ET.SubElement(r,C("selectionEntries"))

    existing=next((e for e in ses.findall(C("selectionEntry")) if e.get("id")=="config-army"),None)
    if full_template is not None:
        local=copy.deepcopy(full_template)
    elif existing is not None:
        local=copy.deepcopy(existing)
    else:
        raise RuntimeError(fn+": no Army Configuration available for idempotent rebuild")

    # Remove obsolete hidden identity marker and any previous local config.
    for e in list(ses):
        if e.get("id")=="config-army" or (e.get("id") or "").startswith("auto-legion-marker-"):
            ses.remove(e)
    group=next((g for g in local.iter(C("selectionEntryGroup")) if g.get("id")=="config-legion"),None)
    if group is None: raise RuntimeError(fn+": config-legion missing in template")
    ec=group.find(C("selectionEntries"))
    if ec is None: raise RuntimeError(fn+": config-legion choices missing")

    chosen=None
    for e in list(ec):
        if e.get("id")==lid:
            chosen=e
        else:
            ec.remove(e)
    if chosen is None: raise RuntimeError(fn+": chosen Legion "+lid+" missing")

    # One structural Legion choice; selected by default and impossible to swap.
    group.set("hidden","false")
    group.set("defaultSelectionEntryId",lid)
    chosen.set("hidden","false")
    chosen.set("defaultAmount","1")

    # Strip old auto-marker visibility logic from the retained choice.
    mods=chosen.find(C("modifiers"))
    if mods is not None:
        for m in list(mods):
            if (m.get("id") or "").startswith(lid+"-auto-"):
                mods.remove(m)
    cons=chosen.find(C("constraints"))
    if cons is None: cons=ET.SubElement(chosen,C("constraints"))
    for c in list(cons):
        if (c.get("id") or "").startswith(lid+"-auto-"):
            cons.remove(c)
    if not any(c.get("type")=="min" for c in cons):
        ET.SubElement(cons,C("constraint"),{
            "id":lid+"-fixed-min","type":"min","value":"1","field":"selections",
            "scope":"parent","shared":"true","includeChildSelections":"false","automatic":"true"})
    else:
        for c in cons:
            if c.get("type")=="min":
                c.set("value","1");c.set("automatic","true")
    for c in cons:
        if c.get("type")=="max":c.set("value","1")

    # The group itself is compulsory and has exactly one entry.
    gcons=group.find(C("constraints"))
    if gcons is None:gcons=ET.SubElement(group,C("constraints"))
    for c in gcons:
        if c.get("type")=="min":
            c.set("value","1");c.set("automatic","true")
        elif c.get("type")=="max":
            c.set("value","1")

    # Keep Army Configuration as the first local root entry for predictable UI.
    ses.insert(0,local)
    r.set("revision",str(int(r.get("revision","0"))+1))
    t.write(p,encoding="utf-8",xml_declaration=True)
    revisions[fn]=int(r.get("revision","0"))

# Index revisions.
ET.register_namespace("",INS)
it=ET.parse(IDX); ir=it.getroot()
for x in ir.iter(I("dataIndexEntry")):
    fp=x.get("filePath")
    if fp in revisions:x.set("dataRevision",str(revisions[fp]))
it.write(IDX,encoding="utf-8",xml_declaration=True)

# Validation.
rg=ET.parse(GEN).getroot()
assert not any(e.get("id")=="config-army" for e in rg.findall(f"./{C('selectionEntries')}/{C('selectionEntry')}")), "Generic still contains Army Configuration"
for fn,lid in LEGIONS:
    r=ET.parse(fn).getroot()
    configs=[e for e in r.findall(f"./{C('selectionEntries')}/{C('selectionEntry')}") if e.get("id")=="config-army"]
    assert len(configs)==1,(fn,len(configs))
    cfg=configs[0]
    g=next(x for x in cfg.iter(C("selectionEntryGroup")) if x.get("id")=="config-legion")
    choices=g.findall(f"./{C('selectionEntries')}/{C('selectionEntry')}")
    assert len(choices)==1,(fn,[x.get("id") for x in choices])
    assert choices[0].get("id")==lid,(fn,choices[0].get("id"),lid)
    assert choices[0].get("defaultAmount")=="1",fn
    assert g.get("defaultSelectionEntryId")==lid,fn
    names=[x.get("name") or "" for x in cfg.iter()]
    assert "Loyalist" in names and "Traitor" in names,fn+" allegiance missing"
    assert any("Rite" in n for n in names),fn+" rites missing"
print("PASS: Generic has no Legion chooser; all 18 Legion catalogues carry one fixed default Legion + Allegiance + Rites")
