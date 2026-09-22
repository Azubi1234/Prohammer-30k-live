from pathlib import Path
import xml.etree.ElementTree as ET, collections, re
CAT=Path("Legiones Astartes.cat"); GST=Path("Prohammer 30k.gst"); OUT=Path("inspection-r43-raven-guard-baseline.txt")
CNS="http://www.battlescribe.net/schema/catalogueSchema"; GNS="http://www.battlescribe.net/schema/gameSystemSchema"
C=lambda t:f"{{{CNS}}}{t}"; G=lambda t:f"{{{GNS}}}{t}"
r=ET.parse(CAT).getroot(); g=ET.parse(GST).getroot(); pm={c:p for p in r.iter() for c in p}
def anc(e,lim=8):
    out=[];p=e
    while p is not None and len(out)<lim:
        if p.get("name") or p.get("id"):out.append(f"{p.tag.split('}')[-1]}:{p.get('id')}:{p.get('name')}")
        p=pm.get(p)
    return " > ".join(out)
def cons(e):return [(x.get("id"),x.get("type"),x.get("value"),x.get("scope"),x.get("field")) for x in e.findall(f"./{C('constraints')}/{C('constraint')}")]
def cats(e):return [(x.get("id"),x.get("name"),x.get("targetId"),x.get("primary")) for x in e.findall(f"./{C('categoryLinks')}/{C('categoryLink')}")]
def costs(e):return [(x.get("typeId"),x.get("value")) for x in e.findall(f"./{C('costs')}/{C('cost')}")]
def mods(e):
    m=e.find(C("modifiers"));return ET.tostring(m,encoding="unicode") if m is not None else ""
def dump(e):
    out=[f"{e.tag.split('}')[-1]} id={e.get('id')} name={e.get('name')} type={e.get('type')} hidden={e.get('hidden')} cost={costs(e)} cons={cons(e)} cats={cats(e)}"]
    for rr in e.findall(f"./{C('rules')}/{C('rule')}"):out.append(f"  RULE {rr.get('name')}: {(rr.findtext(C('description')) or '')[:900].replace(chr(10),' | ')}")
    for il in e.findall(f"./{C('infoLinks')}/{C('infoLink')}"):out.append(f"  INFO {il.get('name')} -> {il.get('targetId')} {il.get('type')}")
    for sg in e.findall(f"./{C('selectionEntryGroups')}/{C('selectionEntryGroup')}"):
        out.append(f"  GROUP {sg.get('id')} {sg.get('name')} hidden={sg.get('hidden')} cons={cons(sg)} mods={mods(sg)[:4000]}")
        for z in sg.findall(f"./{C('entryLinks')}/{C('entryLink')}"):out.append(f"    LINK {z.get('id')} {z.get('name')} -> {z.get('targetId')} hidden={z.get('hidden')} cost={costs(z)} cons={cons(z)} mods={mods(z)[:2500]}")
        for z in sg.findall(f"./{C('selectionEntries')}/{C('selectionEntry')}"):out.append(f"    OPT {z.get('id')} {z.get('name')} type={z.get('type')} hidden={z.get('hidden')} cost={costs(z)} cons={cons(z)} cats={cats(z)}")
    for z in e.findall(f"./{C('selectionEntries')}/{C('selectionEntry')}"):out.append(f"  CHILD {z.get('id')} {z.get('name')} type={z.get('type')} hidden={z.get('hidden')} cost={costs(z)} cons={cons(z)} cats={cats(z)}")
    out.append("  MODS "+mods(e)[:8000]);return out

lines=[f"CAT={r.get('revision')} GST={g.get('revision')}"]
ids={e.get("id"):e for e in r.iter() if e.get("id")}
# Raven Guard related roots / IDs/names.
matches=[]
for e in r.findall(f"./{C('selectionEntries')}/{C('selectionEntry')}"):
    n=(e.get("name") or "").lower();eid=e.get("id") or ""
    if ("raven guard" in n or "corax" in n or "mor deythan" in n or "dark fury" in n or "deliverer" in n or "raptor squad" in n or "kaedes nex" in n or "alvarex maun" in n or "agapito nev" in n or "branne nev" in n or "sharrowkyn" in n or "legion-xix" in eid or "r41-unit-xix" in eid):
        matches.append(e)
lines+=["",f"==== TOP-LEVEL RG MATCHES ({len(matches)}) ===="]
for e in matches:
    lines+=dump(e)+[""]

# Rite roots.
lines+=["","==== XIX RITES ===="]
for e in r.iter(C("selectionEntry")):
    n=(e.get("name") or "").lower(); eid=e.get("id") or ""
    if ("raven guard rite" in n or "decapitation strike" in n or "liberation force" in n) and ("xix" in eid or "raven" in n):
        lines+=dump(e)+[""]

# Existing RG armoury shared items & links.
lines+=["","==== RG SHARED / ARMOURY ENTRIES ===="]
for e in r.iter(C("selectionEntry")):
    eid=e.get("id") or "";n=(e.get("name") or "").lower()
    if eid.startswith("r46-rg-") or eid.startswith("r40-rg-") or any(k in n for k in ["raven's talons","raven’s talons","fulcrum hand cannon","infravisor","shroud bombs","cameleoline","teleportation transponders"]):
        if eid.startswith(("r46-rg-","r40-rg-")):
            lines+=dump(e)+[""]

for tid in [e.get("id") for e in r.iter(C("selectionEntry")) if (e.get("id") or "").startswith("r46-rg-")]:
    arr=[l for l in r.iter(C("entryLink")) if l.get("targetId")==tid]
    lines+=["",f"==== LINKS TO {tid} ({len(arr)}) ===="]
    for l in arr[:200]:lines.append(f"{l.get('id')} {l.get('name')} hidden={l.get('hidden')} cost={costs(l)} cons={cons(l)} anc={anc(l)} mods={mods(l)[:1500]}")

# Recon/HS/FA relevant current categories and support handling.
for eid in ["recon-unit","veteran-unit","fa-seeker","destroyer-unit","hs-heavy-support-squad","hq-praetor","hq-centurion"]:
    lines+=["",f"==== CORE {eid} ===="]
    e=ids.get(eid);lines+=dump(e) if e is not None else ["MISSING"]

# All Dark Fury/Raptor/Deliverer copies
for key in ["dark fury","deliverer terminator","raptor squad","mor deythan"]:
    arr=[e for e in r.iter(C("selectionEntry")) if key in (e.get("name") or "").lower()]
    lines+=["",f"==== COPIES {key} ({len(arr)}) ===="]
    for e in arr:lines.append(f"{e.get('id')} | {e.get('name')} | hidden={e.get('hidden')} cons={cons(e)} cats={cats(e)} anc={anc(e)}")

OUT.write_text("\n".join(lines)+"\n",encoding="utf-8")
print("\n".join(lines[:1600]))
