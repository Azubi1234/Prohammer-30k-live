from pathlib import Path
import re, xml.etree.ElementTree as ET
CAT=Path("Legiones Astartes.cat"); GST=Path("Prohammer 30k.gst"); OUT=Path("inspection-r37-word-bearers-audit.txt")
NS="http://www.battlescribe.net/schema/catalogueSchema"; GNS="http://www.battlescribe.net/schema/gameSystemSchema"
C=lambda t:f"{{{NS}}}{t}"; G=lambda t:f"{{{GNS}}}{t}"
cr=ET.parse(CAT).getroot(); gr=ET.parse(GST).getroot()
pm={c:p for p in cr.iter() for c in p}
def anc(e,lim=5):
    out=[]; p=pm.get(e)
    while p is not None and len(out)<lim:
        if p.get("name"): out.append(p.get("name"))
        p=pm.get(p)
    return " > ".join(out)
def cats(e):
    return [(c.get("name"),c.get("targetId"),c.get("primary")) for c in e.findall(f"./{C('categoryLinks')}/{C('categoryLink')}")]
def rules(e):
    out=[]
    for r in e.findall(f"./{C('rules')}/{C('rule')}"):
        out.append((r.get("name"),(r.findtext(C("description")) or "")[:350].replace("\n"," | ")))
    for il in e.findall(f"./{C('infoLinks')}/{C('infoLink')}"):
        if il.get("type")=="rule": out.append(("LINK:"+str(il.get("name")),il.get("targetId")))
    return out
def dump_entry(e):
    L=[f"ID={e.get('id')} NAME={e.get('name')} TYPE={e.get('type')} HIDDEN={e.get('hidden')} CATS={cats(e)} ANC={anc(e)}"]
    for n,d in rules(e): L.append(f"  RULE {n}: {d}")
    for g in e.findall(f"./{C('selectionEntryGroups')}/{C('selectionEntryGroup')}"):
        L.append(f"  GROUP {g.get('id')} {g.get('name')} hidden={g.get('hidden')}")
        for x in g.findall(f"./{C('selectionEntries')}/{C('selectionEntry')}"):
            L.append(f"    OPT {x.get('id')} {x.get('name')} hidden={x.get('hidden')}")
        for x in g.findall(f"./{C('entryLinks')}/{C('entryLink')}"):
            L.append(f"    LINK {x.get('id')} {x.get('name')} -> {x.get('targetId')} hidden={x.get('hidden')}")
    return L

lines=[f"CAT={cr.get('revision')} GST={gr.get('revision')}",""]
targets=[]
for e in cr.iter(C("selectionEntry")):
    i=e.get("id") or ""; n=(e.get("name") or "").lower()
    if ("r41-unit-xvii-" in i or "r25-rite-xvii" in i or "r42-role-xvii" in i
        or any(k in n for k in ["word bearers","argel tal","erebus","kor phaeron","zardu layak","hol beloth","lorgar aurelian","anakatis kul","diabolist"])):
        targets.append(e)
for e in targets:
    lines += ["==== ENTRY ===="]+dump_entry(e)+[""]

lines += ["","==== CONSUL / CHAPLAIN / DIABOLIST SEARCH ===="]
for e in cr.iter(C("selectionEntry")):
    n=(e.get("name") or "").lower()
    if any(k in n for k in ["chaplain consul","diabolist","accursed crozius","dark channelling","burning lore"]):
        lines += dump_entry(e)+[""]

lines += ["","==== FORCE LINKS ===="]
for fe in gr.iter(G("forceEntry")):
    if fe.get("id")=="force-standard":
        for cl in fe.findall(f"./{G('categoryLinks')}/{G('categoryLink')}"):
            if cl.get("targetId") in ("cat-heavy","cat-troops","cat-hq") or "word" in (cl.get("name") or "").lower() or "r37" in (cl.get("id") or ""):
                lines.append(ET.tostring(cl,encoding="unicode"))

OUT.write_text("\n".join(lines)+"\n",encoding="utf-8")
print("\n".join(lines[:700]))
