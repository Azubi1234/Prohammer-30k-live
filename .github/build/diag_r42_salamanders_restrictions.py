from pathlib import Path
import xml.etree.ElementTree as ET, collections, re
CAT=Path("Legiones Astartes.cat"); GST=Path("Prohammer 30k.gst"); OUT=Path("inspection-r42-salamanders-restriction-audit.txt")
CNS="http://www.battlescribe.net/schema/catalogueSchema"; GNS="http://www.battlescribe.net/schema/gameSystemSchema"
C=lambda t:f"{{{CNS}}}{t}"; G=lambda t:f"{{{GNS}}}{t}"
r=ET.parse(CAT).getroot(); g=ET.parse(GST).getroot(); pm={c:p for p in r.iter() for c in p}
def anc(e,lim=7):
    out=[];p=pm.get(e)
    while p is not None and len(out)<lim:
        if p.get("name") or p.get("id"):out.append(f"{p.tag.split('}')[-1]}:{p.get('id')}:{p.get('name')}")
        p=pm.get(p)
    return " > ".join(out)
def cs(e):return [(x.get("id"),x.get("type"),x.get("value"),x.get("scope"),x.get("field")) for x in e.findall(f"./{C('constraints')}/{C('constraint')}")]
def cats(e):return [(x.get("id"),x.get("name"),x.get("targetId"),x.get("primary")) for x in e.findall(f"./{C('categoryLinks')}/{C('categoryLink')}")]
def costs(e):return [(x.get("typeId"),x.get("value")) for x in e.findall(f"./{C('costs')}/{C('cost')}")]
def mods(e):
    m=e.find(C("modifiers"));return ET.tostring(m,encoding="unicode")[:10000] if m is not None else ""
def dump(e):
    lines=[f"{e.tag.split('}')[-1]} id={e.get('id')} name={e.get('name')} type={e.get('type')} hidden={e.get('hidden')} default={e.get('defaultAmount')} cost={costs(e)} constraints={cs(e)} cats={cats(e)}"]
    for rr in e.findall(f"./{C('rules')}/{C('rule')}"):lines.append(f"  RULE {rr.get('name')}: {(rr.findtext(C('description')) or '')[:600].replace(chr(10),' | ')}")
    for il in e.findall(f"./{C('infoLinks')}/{C('infoLink')}"):lines.append(f"  INFO {il.get('name')} -> {il.get('targetId')} type={il.get('type')}")
    for sg in e.findall(f"./{C('selectionEntryGroups')}/{C('selectionEntryGroup')}"):
        lines.append(f"  GROUP {sg.get('id')} {sg.get('name')} hidden={sg.get('hidden')} cons={cs(sg)} mods={mods(sg)}")
        for z in sg.findall(f"./{C('entryLinks')}/{C('entryLink')}"):lines.append(f"    LINK {z.get('id')} {z.get('name')} -> {z.get('targetId')} hidden={z.get('hidden')} cost={costs(z)} cons={cs(z)} mods={mods(z)}")
        for z in sg.findall(f"./{C('selectionEntries')}/{C('selectionEntry')}"):lines.append(f"    OPT {z.get('id')} {z.get('name')} hidden={z.get('hidden')} cost={costs(z)} cons={cs(z)} cats={cats(z)}")
    for z in e.findall(f"./{C('selectionEntries')}/{C('selectionEntry')}"):lines.append(f"  CHILD {z.get('id')} {z.get('name')} type={z.get('type')} hidden={z.get('hidden')} cost={costs(z)} cons={cs(z)} cats={cats(z)}")
    lines.append("  MODS "+mods(e))
    return lines

lines=[f"CAT={r.get('revision')} GST={g.get('revision')}"]
ids={e.get("id"):e for e in r.iter() if e.get("id")}
targets=[
"legion-xviii","r46-sal-mantle","r46-sal-mastercrafted","r46-sal-artificer-armour","r46-sal-inferno-pistol","r46-sal-heavy-flamer","r46-sal-ceramite",
"r25-rite-xviii-0-the-covenant-of-fire","r25-rite-xviii-1-the-awakening-fire",
"r41-unit-xviii-0-firedrake-terminator-squad","r41-unit-xviii-1-pyroclast-squad","r41-unit-xviii-2-salamanders-infernus-destroyer-squad","r41-unit-xviii-3-adherent-squad","r41-unit-xviii-4-sanctifier-squad",
"r41-unit-xviii-5-artellus-numeon","r41-unit-xviii-6-lord-chaplain-nomus-rhy-tan","r41-unit-xviii-7-xiaphas-jurr-prophet-of-fire","r41-unit-xviii-8-cassian-dracos","r41-unit-xviii-9-forgefather-t-kell","r41-unit-xviii-10-xviii-vulkan-the-forgefather",
"r40-sal-cov-pyro","r40-sal-cov-infernus","r40-sal-nomus-dread-hq","r40-sal-nomus-contemptor-hq",
"hq-praetor","hq-centurion","hq-consul-chaplain",
]
for id_ in targets:
    lines+=["",f"==== {id_} ===="]
    e=ids.get(id_)
    lines+=dump(e) if e is not None else ["MISSING"]

# links/usages of Salamanders armoury packages
for tid in ["r46-sal-mantle","r46-sal-mastercrafted","r46-sal-artificer-armour","r46-sal-inferno-pistol","r46-sal-heavy-flamer","r46-sal-ceramite"]:
    arr=[l for l in r.iter(C("entryLink")) if l.get("targetId")==tid]
    lines+=["",f"==== LINKS TO {tid} count={len(arr)} ===="]
    for l in arr[:250]:lines.append(f"{l.get('id')} {l.get('name')} hidden={l.get('hidden')} cost={costs(l)} cons={cs(l)} anc={anc(l)} mods={mods(l)}")

# Awakening hidden type tag consumers
for cat in ["r40-sal-awakening-jump","r40-sal-awakening-jetbike","r40-sal-awakening-skimmer","r40-sal-awakening-flyer","r40-sal-awakening-chaplain"]:
    arr=[]
    for e in r.iter():
        for cl in e.findall(f"./{C('categoryLinks')}/{C('categoryLink')}"):
            if cl.get("targetId")==cat:arr.append(e)
    lines+=["",f"==== CATEGORY USERS {cat} count={len(arr)} ===="]
    for e in arr[:250]:lines.append(f"{e.tag.split('}')[-1]} {e.get('id')} {e.get('name')} anc={anc(e)}")

# Iron Halo/Mantle hidden counter users
for cat in ["r41-iron-halo-army-limit","r40-sal-mantle-limit","r40-sal-covenant-compulsory","r40-sal-covenant-support"]:
    arr=[]
    for e in r.iter():
        for cl in e.findall(f"./{C('categoryLinks')}/{C('categoryLink')}"):
            if cl.get("targetId")==cat:arr.append(e)
    lines+=["",f"==== CATEGORY USERS {cat} count={len(arr)} ===="]
    for e in arr[:250]:lines.append(f"{e.tag.split('}')[-1]} {e.get('id')} {e.get('name')} anc={anc(e)}")

# Drop-pod-ish selectable roots and Fortification/Allied force/category definitions.
lines+=["","==== DROP/DEEP STRIKE SELECTABLES ===="]
for e in r.iter(C("selectionEntry")):
    n=(e.get("name") or "").lower()
    if any(k in n for k in ["drop pod","dreadclaw"]) and (e.get("type") in ("model","unit")):
        lines.append(f"{e.get('id')} | {e.get('name')} hidden={e.get('hidden')} cats={cats(e)} anc={anc(e)} mods={mods(e)}")
lines+=["","==== GST FORCE/CATEGORY FORTIFICATION ALLIED ===="]
for e in g.iter():
    n=(e.get("name") or "").lower()
    if any(k in n for k in ["fortification","allied"]):
        lines.append(f"{e.tag.split('}')[-1]} id={e.get('id')} name={e.get('name')} hidden={e.get('hidden')} constraints={[(x.get('type'),x.get('value'),x.get('scope')) for x in e.findall(f'./{G('constraints')}/{G('constraint')}')]}")

OUT.write_text("\n".join(lines)+"\n",encoding="utf-8")
print("\n".join(lines[:1400]))
