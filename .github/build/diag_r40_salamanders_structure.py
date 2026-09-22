from pathlib import Path
import xml.etree.ElementTree as ET
CAT=Path("Legiones Astartes.cat"); OUT=Path("inspection-r40-salamanders-structure.txt")
NS="http://www.battlescribe.net/schema/catalogueSchema"; C=lambda t:f"{{{NS}}}{t}"
r=ET.parse(CAT).getroot()
def costs(e): return [(x.get("typeId"),x.get("value")) for x in e.findall(f"./{C('costs')}/{C('cost')}")]
def cons(e): return [(x.get("id"),x.get("type"),x.get("value"),x.get("scope"),x.get("field")) for x in e.findall(f"./{C('constraints')}/{C('constraint')}")]
def profs(e):
    out=[]
    for p in e.findall(f"./{C('profiles')}/{C('profile')}"):
        chars=[(c.get("name"),c.text) for c in p.findall(f"./{C('characteristics')}/{C('characteristic')}")]
        out.append((p.get("id"),p.get("name"),p.get("typeId"),chars))
    return out
def row(e,p=""):
    return f"{p}{e.tag.split('}')[-1]} id={e.get('id')} name={e.get('name')} type={e.get('type')} default={e.get('defaultAmount')} hidden={e.get('hidden')} costs={costs(e)} cons={cons(e)} profiles={profs(e)}"
lines=[f"CAT={r.get('revision')}"]
for root in r.findall(f"./{C('selectionEntries')}/{C('selectionEntry')}"):
    if (root.get("id") or "").startswith("r41-unit-xviii-") or (root.get("id") or "").startswith("r25-rite-xviii"):
        lines += ["","==== "+root.get("id")+" / "+root.get("name")+" ====",row(root)]
        for e in root.findall(f"./{C('selectionEntries')}/{C('selectionEntry')}"):
            lines.append(row(e,"  CHILD "))
        for g in root.findall(f"./{C('selectionEntryGroups')}/{C('selectionEntryGroup')}"):
            lines.append(f"  GROUP id={g.get('id')} name={g.get('name')} hidden={g.get('hidden')} cons={cons(g)}")
            for e in g.findall(f"./{C('selectionEntries')}/{C('selectionEntry')}"):
                lines.append(row(e,"    OPT "))
            for e in g.findall(f"./{C('entryLinks')}/{C('entryLink')}"):
                lines.append(row(e,"    LINK "))
        for c in root.findall(f"./{C('categoryLinks')}/{C('categoryLink')}"):
            lines.append(f"  CAT id={c.get('id')} name={c.get('name')} target={c.get('targetId')} primary={c.get('primary')}")
OUT.write_text("\n".join(lines)+"\n",encoding="utf-8")
print(OUT.read_text())
