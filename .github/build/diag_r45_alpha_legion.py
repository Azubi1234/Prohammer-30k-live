from pathlib import Path
import xml.etree.ElementTree as ET, re, collections
CAT=Path("Legiones Astartes.cat"); GST=Path("Prohammer 30k.gst"); OUT=Path("inspection-r45-alpha-legion-baseline.txt")
CNS="http://www.battlescribe.net/schema/catalogueSchema"; GNS="http://www.battlescribe.net/schema/gameSystemSchema"
C=lambda t:f"{{{CNS}}}{t}"; G=lambda t:f"{{{GNS}}}{t}"
r=ET.parse(CAT).getroot(); g=ET.parse(GST).getroot(); pm={c:p for p in r.iter() for c in p}
def cons(e):return [(x.get("id"),x.get("type"),x.get("value"),x.get("scope"),x.get("field")) for x in e.findall(f"./{C('constraints')}/{C('constraint')}")]
def cats(e):return [(x.get("id"),x.get("name"),x.get("targetId"),x.get("primary")) for x in e.findall(f"./{C('categoryLinks')}/{C('categoryLink')}")]
def costs(e):return [(x.get("typeId"),x.get("value")) for x in e.findall(f"./{C('costs')}/{C('cost')}")]
def mods(e):
    m=e.find(C("modifiers"));return ET.tostring(m,encoding="unicode") if m is not None else ""
def anc(e,lim=7):
    out=[];p=e
    while p is not None and len(out)<lim:
        if p.get("id") or p.get("name"):out.append(f"{p.tag.split('}')[-1]}:{p.get('id')}:{p.get('name')}")
        p=pm.get(p)
    return " > ".join(out)
def profiles(e):
    out=[]
    for p in e.findall(f"./{C('profiles')}/{C('profile')}"):
        out.append((p.get("id"),p.get("name"),p.get("typeId"),[(x.get("name"),x.text) for x in p.findall(f"./{C('characteristics')}/{C('characteristic')}")]))
    return out
def dump(e):
    out=[f"{e.tag.split('}')[-1]} id={e.get('id')} name={e.get('name')} type={e.get('type')} hidden={e.get('hidden')} cost={costs(e)} cons={cons(e)} cats={cats(e)} profiles={profiles(e)}"]
    for rr in e.findall(f"./{C('rules')}/{C('rule')}"):out.append(f" RULE {rr.get('name')}: {(rr.findtext(C('description')) or '')[:1400].replace(chr(10),' | ')}")
    for il in e.findall(f"./{C('infoLinks')}/{C('infoLink')}"):out.append(f" INFO {il.get('name')} -> {il.get('targetId')} {il.get('type')}")
    for sg in e.findall(f"./{C('selectionEntryGroups')}/{C('selectionEntryGroup')}"):
        out.append(f" GROUP {sg.get('id')} {sg.get('name')} hidden={sg.get('hidden')} cons={cons(sg)} mods={mods(sg)[:3000]}")
        for z in sg.findall(f"./{C('entryLinks')}/{C('entryLink')}"):out.append(f"  LINK {z.get('id')} {z.get('name')} -> {z.get('targetId')} hidden={z.get('hidden')} cost={costs(z)} cons={cons(z)} mods={mods(z)[:1800]}")
        for z in sg.findall(f"./{C('selectionEntries')}/{C('selectionEntry')}"):out.append(f"  OPT {z.get('id')} {z.get('name')} hidden={z.get('hidden')} cost={costs(z)} cons={cons(z)} cats={cats(z)} mods={mods(z)[:1800]}")
    for z in e.findall(f"./{C('selectionEntries')}/{C('selectionEntry')}"):out.append(f" CHILD {z.get('id')} {z.get('name')} type={z.get('type')} hidden={z.get('hidden')} cost={costs(z)} cons={cons(z)} cats={cats(z)} profiles={profiles(z)}")
    out.append(" MODS "+mods(e)[:6500]);return out

lines=[f"CAT={r.get('revision')} GST={g.get('revision')}"]
# Top-level XX entries
arr=[]
for e in r.findall(f"./{C('selectionEntries')}/{C('selectionEntry')}"):
    n=(e.get("name") or "").lower();eid=e.get("id") or ""
    if eid.startswith("r41-unit-xx-") or "alpha legion" in n or "alpharius" in n or "lernaean" in n or "headhunter" in n or "effrit" in n or "legion operative" in n or any(k in n for k in ["armillus dynat","exodus","autilon skorr","ingo pech","mathias herzog","sheed ranko"]):
        arr.append(e)
lines+=["",f"==== TOP-LEVEL XX ({len(arr)}) ===="]
for e in arr:lines+=dump(e)+[""]

# XX rites
lines+=["","==== XX RITES ===="]
for e in r.iter(C("selectionEntry")):
    n=(e.get("name") or "").lower();eid=e.get("id") or ""
    if "coils of the hydra" in n or "headhunter leviath" in n or ("rite" in n and "xx" in eid):
        lines+=dump(e)+[""]

# Alpha legion shared armoury / selector-ish content
lines+=["","==== ALPHA ARMOURY / TACTICS ===="]
for e in r.iter():
    n=(e.get("name") or "").lower();eid=e.get("id") or ""
    if any(k in n for k in ["mutable tactics","banestrike","power dagger","venom spheres","legion saboteur","pre-emptive strike","teleportation transponders","siege specialists","rewards of treachery"]):
        lines.append(f"{e.tag.split('}')[-1]} {eid} | {e.get('name')} | target={e.get('targetId')} hidden={e.get('hidden')} cost={costs(e) if e.tag in (C('selectionEntry'),C('entryLink')) else []} cons={cons(e) if e.tag in (C('selectionEntry'),C('entryLink'),C('selectionEntryGroup')) else []} anc={anc(e)} mods={mods(e)[:2200]}")

# Relevant core units/characters
for eid in ["fa-seeker","veteran-unit","terminator-unit","hq-praetor","hq-centurion","tactical-unit","recon-unit"]:
    lines+=["",f"==== CORE {eid} ===="]
    e=next((x for x in r.iter(C("selectionEntry")) if x.get("id")==eid),None)
    lines+=dump(e) if e is not None else ["MISSING"]

# Rewards clones
lines+=["","==== REWARDS CLONES ===="]
for e in r.iter(C("selectionEntry")):
    eid=e.get("id") or "";n=e.get("name") or ""
    if "reward" in eid.lower() or "treachery" in eid.lower():
        lines.append(f"{eid} | {n} | hidden={e.get('hidden')} cost={costs(e)} cats={cats(e)} profiles={profiles(e)} anc={anc(e)}")

OUT.write_text("\n".join(lines)+"\n",encoding="utf-8");print("\n".join(lines[:1800]))
