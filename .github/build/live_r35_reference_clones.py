from pathlib import Path
import ast, re, xml.etree.ElementTree as ET

CAT=Path("Legiones Astartes.cat")
IDX=Path("index.xml")
OUT=Path("inspection-live-r35-reference-clones.txt")
SRC=Path(".github/build/live_r34_rules_soh_names.py")

NS="http://www.battlescribe.net/schema/catalogueSchema"
ET.register_namespace("",NS)
C=lambda t:f"{{{NS}}}{t}"
tree=ET.parse(CAT); root=tree.getroot()
if root.get("revision")!="34":
    raise RuntimeError(f"R35 expected CAT 34, got {root.get('revision')}")

# Reuse canonical text constants from the audited R34 source without executing it.
mod=ast.parse(SRC.read_text(encoding="utf-8"))
vals={}
for node in mod.body:
    if isinstance(node,ast.Assign) and len(node.targets)==1 and isinstance(node.targets[0],ast.Name):
        nm=node.targets[0].id
        if nm in {"USR","DEEP_STRIKE","LEGIONES"}:
            vals[nm]=ast.literal_eval(node.value)
USR=vals["USR"]; DEEP_STRIKE=vals["DEEP_STRIKE"]; LEGIONES=vals["LEGIONES"]

# Every rule row whose name itself is a ProHammer rule must contain the effect,
# even when the row also explains availability/context.
context_expanded=0
for r in root.iter(C("rule")):
    n=(r.get("name") or "").strip()
    dnode=r.find(C("description"))
    if dnode is None:
        dnode=ET.SubElement(r,C("description")); dnode.text=""
    d=(dnode.text or "").strip()
    key="Scouts" if n=="Scout" else n
    canonical=None
    if key in USR: canonical=USR[key]
    elif n=="Deep Strike": canonical=DEEP_STRIKE
    elif n.startswith("Feel No Pain"):
        v="4+" if "4+" in n else "5+"
        canonical=f"After a model fails its normal saving throw, roll a D6; on {v} the Wound is ignored, subject to the normal ProHammer Feel No Pain restrictions."
    elif n.startswith("Preferred Enemy ("):
        target=n[n.find("(")+1:n.rfind(")")]
        canonical=f"The unit may re-roll failed hits in close combat against {target}."
    if canonical and canonical[:45].lower() not in d.lower():
        if d:
            dnode.text=d+"\n\n"+n+": "+canonical
        else:
            dnode.text=canonical
        context_expanded+=1

# Helpers for clone patch.
def ensure_container(p,tag):
    x=p.find(C(tag))
    if x is None: x=ET.SubElement(p,C(tag))
    return x
def ensure_rule(e,name,text,id_):
    rs=ensure_container(e,"rules")
    rr=next((x for x in rs.findall(C("rule")) if (x.get("name") or "").lower()==name.lower()),None)
    if rr is None:
        rr=ET.SubElement(rs,C("rule"),{"id":id_,"name":name,"hidden":"false"})
    rr.set("hidden","false")
    dd=rr.find(C("description"))
    if dd is None: dd=ET.SubElement(rr,C("description"))
    dd.text=text
def parent_map(rt): return {c:p for p in rt.iter() for c in p}
pm=parent_map(root)
def ancestors(e):
    out=[]; p=pm.get(e)
    while p is not None:
        out.append(p); p=pm.get(p)
    return out
def soh_context(e):
    anc=ancestors(e)
    allnodes=[e]+anc
    names=" | ".join((x.get("name") or "") for x in allnodes).lower()
    ids=" | ".join((x.get("id") or "") for x in allnodes).lower()
    if "rewards of treachery" in names or "r46-al-reward" in ids:
        return False
    if "r41-unit-xvi" in ids or "r32-soh" in ids:
        return True
    for x in allnodes:
        for c in x.iter(C("condition")):
            if c.get("childId")=="legion-xvi": return True
    return any(k in names for k in ["ezekyle abaddon","horus aximand","garviel loken","tybalt marr","vheren ashurhaddon","horus lupercal","horus ascended"])

ATSKNF=USR["And They Shall Know No Fear"]
soh_leg=LEGIONES+"\n\nAnd They Shall Know No Fear: "+ATSKNF
clone_counts={"Justaerin":0,"Reaver":0,"Chieftain":0,"Luperci":0}
for e in root.iter(C("selectionEntry")):
    if not soh_context(e): continue
    n=(e.get("name") or "").lower()
    eid=e.get("id") or "r35-clone"
    if "justaerin terminator squad" in n:
        ensure_rule(e,"Legiones Astartes (Sons of Horus)",soh_leg,eid+"-r35-legiones")
        ensure_rule(e,"Chosen of the Warmaster","A Sons of Horus Praetor, Ezekyle Abaddon or Horus Lupercal may select one Justaerin Terminator Squad as a retinue. If selected as a retinue, the squad does not occupy a separate Elites choice.",eid+"-r35-chosen")
        clone_counts["Justaerin"]+=1
    elif "reaver attack squad" in n:
        ensure_rule(e,"Legiones Astartes (Sons of Horus)",soh_leg,eid+"-r35-legiones")
        ensure_rule(e,"Furious Charge",USR["Furious Charge"],eid+"-r35-furious")
        clone_counts["Reaver"]+=1
    elif "chieftain squad" in n:
        ensure_rule(e,"Legiones Astartes (Sons of Horus)",soh_leg,eid+"-r35-legiones")
        ensure_rule(e,"Stubborn",USR["Stubborn"],eid+"-r35-stubborn")
        ensure_rule(e,"Cthonian Retinue","One Chieftain Squad may be selected as the retinue of a Sons of Horus Praetor or appropriate named Sons of Horus Independent Character. The squad does not occupy a separate Elites choice. The Character and Chieftain Squad count as a single HQ selection.",eid+"-r35-retinue")
        clone_counts["Chieftain"]+=1
    elif "luperci pack" in n:
        for suf,rn,txt in [
          ("legiones","Legiones Astartes (Sons of Horus)",soh_leg),
          ("daemon","Daemon",USR["Daemon"]),("fearless","Fearless",USR["Fearless"]),
          ("bulky","Bulky",USR["Bulky"]),("furious","Furious Charge",USR["Furious Charge"]),
          ("damned","Damned","A Luperci Pack may never count as a Scoring Unit. No Independent Character may join a Luperci Pack unless that Character has the Daemon special rule."),
          ("talons","Daemonic Talons","Daemonic Talons are Rending Weapons.\n\nRending: "+USR["Rending"])
        ]: ensure_rule(e,rn,txt,eid+"-r35-"+suf)
        clone_counts["Luperci"]+=1

# Character-name clones: derive canonical names from already-normalised R34 roots.
canonical={}
for e in root.iter(C("selectionEntry")):
    n=e.get("name") or ""
    if any(k in (e.get("id") or "") for k in ["r41-unit-xvi-4-","r41-unit-xvi-5-","r41-unit-xvi-6-","r41-unit-xvi-7-","r41-unit-xvi-8-","r41-unit-xvi-9-","r41-unit-xvi-10-","r41-unit-xvi-11-","r41-unit-xvi-12-","r41-unit-xvi-13-"]):
        canonical[re.sub(r"[^a-z0-9]","",n.lower())]=n
clone_name_changes=0
for e in root.iter(C("selectionEntry")):
    n=e.get("name") or ""
    key=re.sub(r"[^a-z0-9]","",n.lower())
    if key in canonical and n!=canonical[key]:
        e.set("name",canonical[key]); clone_name_changes+=1

# Revision/index.
root.set("revision","35")
tree.write(CAT,encoding="utf-8",xml_declaration=True)
IDX_NS="http://www.battlescribe.net/schema/dataIndexSchema"; ET.register_namespace("",IDX_NS)
it=ET.parse(IDX); ir=it.getroot()
for x in ir.iter(f"{{{IDX_NS}}}dataIndexEntry"):
    if x.get("filePath")=="Legiones Astartes.cat": x.set("dataRevision","35")
it.write(IDX,encoding="utf-8",xml_declaration=True)

# Validation.
rr=ET.parse(CAT).getroot(); checks=[]
def ck(lbl,ok):
    checks.append((lbl,bool(ok)))
    if not ok: raise RuntimeError("R35 validation failed: "+lbl)
ck("CAT revision 35",rr.get("revision")=="35")
idx=IDX.read_text(encoding="utf-8")
ck("Index revision 35",'dataRevision="35"' in idx)
ck("Canonical index","ns0:" not in idx)
# Contextual same-name rows now all carry effects.
bad=[]
for r in rr.iter(C("rule")):
    n=(r.get("name") or "").strip()
    d=(r.findtext(C("description")) or "")
    key="Scouts" if n=="Scout" else n
    if key in USR and USR[key][:45].lower() not in d.lower():
        bad.append((n,d[:80]))
ck("All ProHammer-named rule rows include their effect",not bad)

lines=["Live R35 — rule-reference completeness and Sons of Horus clone audit","Input CAT=34 -> target CAT=35","",
"CHANGES:",
f"- Expanded {context_expanded} remaining same-name ProHammer rule rows so availability/context rows also contain the actual rule effect.",
f"- Audited and patched Sons of Horus copies outside Rewards of Treachery: {clone_counts}.",
f"- Normalised {clone_name_changes} additional Sons of Horus character-name clones.",
"- Bumped catalogue/index to revision 35.","","VALIDATION:"]
lines += [f'- {"PASS" if ok else "FAIL"}: {lbl}' for lbl,ok in checks]
OUT.write_text("\n".join(lines)+"\n",encoding="utf-8")
print(OUT.read_text())
