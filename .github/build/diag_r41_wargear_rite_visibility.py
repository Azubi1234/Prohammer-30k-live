from pathlib import Path
import collections, re, xml.etree.ElementTree as ET
CAT=Path("Legiones Astartes.cat"); OUT=Path("inspection-r41-wargear-rite-visibility.txt")
NS="http://www.battlescribe.net/schema/catalogueSchema"; C=lambda t:f"{{{NS}}}{t}"
r=ET.parse(CAT).getroot(); pm={c:p for p in r.iter() for c in p}

def anc(e,lim=6):
    out=[]; p=pm.get(e)
    while p is not None and len(out)<lim:
        out.append(f"{p.tag.split('}')[-1]}:{p.get('id')}:{p.get('name')}")
        p=pm.get(p)
    return " > ".join(out)

def costs(e):
    return tuple((x.get("typeId"),x.get("value")) for x in e.findall(f"./{C('costs')}/{C('cost')}"))
def cons(e):
    return tuple((x.get("type"),x.get("value"),x.get("scope"),x.get("field")) for x in e.findall(f"./{C('constraints')}/{C('constraint')}"))

lines=[f"CAT={r.get('revision')}",""]
# Troops roots/copies relevant to rites.
lines.append("==== TROOPS / RITE COPIES ====")
for e in r.findall(f"./{C('selectionEntries')}/{C('selectionEntry')}"):
    n=(e.get("name") or "")
    cats=[(c.get("targetId"),c.get("primary")) for c in e.findall(f"./{C('categoryLinks')}/{C('categoryLink')}")]
    if any(k in n.lower() for k in ["gal vorbak","ashen circle","pyroclast","infernus destroyer"]) or any(k in (e.get("id") or "") for k in ["r40-sal-cov","r37-wb-serrated","r37-wb-zardu","r42-role-xvii","r42-role-xviii"]):
        lines.append(f"id={e.get('id')} name={n} hidden={e.get('hidden')} cats={cats} mods={ET.tostring(e.find(C('modifiers')),encoding='unicode') if e.find(C('modifiers')) is not None else ''}")

# Shared entries and duplicate selectionEntry names.
lines += ["","==== SHARED SELECTION ENTRIES ===="]
sse=r.find(C("sharedSelectionEntries"))
if sse is not None:
    for e in sse.findall(C("selectionEntry")):
        lines.append(f"{e.get('id')} | {e.get('name')} | type={e.get('type')} | costs={costs(e)}")

byname=collections.defaultdict(list)
for e in r.iter(C("selectionEntry")):
    n=(e.get("name") or "").strip()
    if n:
        byname[n].append(e)

lines += ["","==== DUPLICATE SELECTION ENTRY NAMES (>=5) ===="]
for n,arr in sorted(byname.items(), key=lambda kv:(-len(kv[1]),kv[0].lower())):
    if len(arr)<5: continue
    # Focus likely wargear/upgrades rather than model/unit names.
    types=collections.Counter(e.get("type") for e in arr)
    if not any(e.get("type")=="upgrade" for e in arr): continue
    lines.append(f"{n} | count={len(arr)} | types={dict(types)}")
    for e in arr[:12]:
        lines.append(f"  {e.get('id')} | type={e.get('type')} | cost={costs(e)} | cons={cons(e)} | anc={anc(e)}")

# EntryLinks targeting shared/basic gear.
link_targets=collections.Counter(l.get("targetId") for l in r.iter(C("entryLink")) if l.get("targetId"))
lines += ["","==== TOP ENTRYLINK TARGETS ===="]
for tid,c in link_targets.most_common(80):
    t=next((e for e in r.iter(C("selectionEntry")) if e.get("id")==tid),None)
    lines.append(f"{tid} | count={c} | name={(t.get('name') if t is not None else '')}")

OUT.write_text("\n".join(lines)+"\n",encoding="utf-8")
print(OUT.read_text()[:60000])
