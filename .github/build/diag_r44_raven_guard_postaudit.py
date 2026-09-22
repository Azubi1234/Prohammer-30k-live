from pathlib import Path
import xml.etree.ElementTree as ET, collections, re
CAT=Path("Legiones Astartes.cat"); OUT=Path("inspection-r44-raven-guard-postaudit.txt")
NS="http://www.battlescribe.net/schema/catalogueSchema"; C=lambda t:f"{{{NS}}}{t}"
r=ET.parse(CAT).getroot(); ids={e.get("id"):e for e in r.iter() if e.get("id")}; pm={c:p for p in r.iter() for c in p}
lines=[f"CAT={r.get('revision')}"]
def cons(e):return [(x.get("id"),x.get("type"),x.get("value"),x.get("scope"),x.get("field")) for x in e.findall(f"./{C('constraints')}/{C('constraint')}")]
def costs(e):return [(x.get("typeId"),x.get("value")) for x in e.findall(f"./{C('costs')}/{C('cost')}")]
def cats(e):return [(x.get("targetId"),x.get("primary"),x.get("name")) for x in e.findall(f"./{C('categoryLinks')}/{C('categoryLink')}")]
def mods(e):
    m=e.find(C("modifiers")); return ET.tostring(m,encoding="unicode") if m is not None else ""
def profiles(e):
    out=[]
    for p in e.findall(f"./{C('profiles')}/{C('profile')}"):
        cs=[(x.get("name"),x.text) for x in p.findall(f"./{C('characteristics')}/{C('characteristic')}")]
        out.append((p.get("id"),p.get("name"),p.get("typeId"),cs))
    return out
def chain(e,lim=8):
    out=[];p=e
    while p is not None and len(out)<lim:
        if p.get("id") or p.get("name"):out.append(f"{p.tag.split('}')[-1]}:{p.get('id')}:{p.get('name')}")
        p=pm.get(p)
    return " > ".join(out)

# XIX roots + nested key entries
for eid in [x for x in ids if x.startswith("r41-unit-xix-")]:
    e=ids[eid]; lines += ["",f"==== {eid} {e.get('name')} ====",f"hidden={e.get('hidden')} cost={costs(e)} cons={cons(e)} cats={cats(e)}",f"profiles={profiles(e)}",f"child_profiles={[(x.get('id'),x.get('name'),profiles(x)) for x in e.findall(f'./{C("selectionEntries")}/{C("selectionEntry")}')]}"]

for eid in ["r43-rg-kaedes-replacement","r43-rg-agapito-replacement","r43-rg-sharrowkyn-recon","r43-rg-sharrowkyn-seeker","r43-branne-raptor-squad","r43-pra-dark-retinue"]:
    e=ids.get(eid); lines += ["",f"==== NESTED {eid} ====", "MISSING" if e is None else f"name={e.get('name')} hidden={e.get('hidden')} cost={costs(e)} cons={cons(e)} cats={cats(e)} profiles={profiles(e)} mods={mods(e)}"]

# Check all R43 target refs resolve.
allids=set(ids)
# include shared rules/profiles ids already in ids because generic r.iter catches
bad=[]
for e in r.iter():
    for a in ("targetId","childId"):
        v=e.get(a)
        if v and v not in allids and a=="targetId":
            # targetId may point to GST category IDs, ignore categories we can recognize r4x/generic cat
            if v.startswith(("cat-","r40-sal-","r41-iron-","r42-sal-","r43-rg-")):
                continue
            bad.append((e.tag.split('}')[-1],e.get("id"),a,v,chain(e)))
newbad=[x for x in bad if (x[1] or "").startswith("r43")]
lines += ["","==== R43 UNRESOLVED TARGET IDS ====",*map(str,newbad)]

# All R43 info/entry links targets explicitly.
for e in r.iter():
    if (e.get("id") or "").startswith("r43") and e.tag in (C("entryLink"),C("infoLink")):
        lines.append(f"REF {e.get('id')} -> {e.get('targetId')} exists={e.get('targetId') in allids} chain={chain(e)}")

# Rite enforcement exact key structures
for eid in ["r25-rite-xix-0-decapitation-strike","r25-rite-xix-1-liberation-force","hs-heavy-support-squad","hq-centurion","recon-unit"]:
    e=ids[eid];lines+=["",f"==== KEY {eid} ====",f"mods={mods(e)}",f"cats={cats(e)}"]
    for g in e.findall(f"./{C('selectionEntryGroups')}/{C('selectionEntryGroup')}"):
        if "r43" in (g.get("id") or ""):
            lines.append(f"GROUP {g.get('id')} {g.get('name')} hidden={g.get('hidden')} cons={cons(g)} mods={mods(g)}")
            for l in g.findall(f"./{C('entryLinks')}/{C('entryLink')}"):lines.append(f" LINK {l.get('id')} {l.get('name')} -> {l.get('targetId')} cost={costs(l)} hidden={l.get('hidden')}")

# Profile type definitions / examples useful for stat profile creation
for eid in ["hq-centurion","veteran-unit","r41-unit-xviii-5-artellus-numeon","r41-unit-xviii-0-firedrake-terminator-squad"]:
    e=ids.get(eid)
    if e is not None:lines+=["",f"==== PROFILE EXAMPLE {eid} ====",f"root_profiles={profiles(e)}",f"all_profiles={[(p.get('id'),p.get('name'),p.get('typeId'),[(x.get('name'),x.text,x.get('typeId')) for x in p.findall(f'./{C('characteristics')}/{C('characteristic')}')]) for p in e.iter(C('profile'))][:20]}"]

OUT.write_text("\n".join(lines)+"\n",encoding="utf-8");print(OUT.read_text()[:65000])
