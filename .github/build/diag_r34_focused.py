from pathlib import Path
import re, collections, xml.etree.ElementTree as ET
CAT=Path("Legiones Astartes.cat")
OUT=Path("inspection-r34-focused.txt")
NS="http://www.battlescribe.net/schema/catalogueSchema"; C=lambda t:f"{{{NS}}}{t}"
root=ET.parse(CAT).getroot()

# Exact generic reference-only rules by name.
hits=collections.Counter()
examples={}
pat=re.compile(r"^(?:this|the)\s+(?:unit|model|vehicle|squad)\s+(?:has|gains|possesses)\s+(.+?)\.?$",re.I)
for r in root.iter(C("rule")):
    n=(r.get("name") or "").strip()
    d=(r.findtext(C("description")) or "").strip()
    m=pat.match(d)
    if m and n:
        hits[n]+=1
        examples.setdefault(n,d)

# Relevant SoH roots and their directly-visible / descendant named rules.
targets={
"r41-unit-xvi-0-justaerin-terminator-squad":"Justaerin",
"r41-unit-xvi-1-reaver-attack-squad":"Reaver",
"r41-unit-xvi-2-chieftain-squad":"Chieftain",
"r41-unit-xvi-3-luperci-pack":"Luperci",
"r41-unit-xvi-4-ezekyle-abaddon-first-captain":"Abaddon",
"r41-unit-xvi-5-horus-aximand-little-horus":"Aximand",
"r41-unit-xvi-6-garviel-loken":"Loken",
"r41-unit-xvi-7-maloghurst-the-twisted":"Maloghurst",
"r41-unit-xvi-8-tybalt-marr-the-either":"Marr",
"r41-unit-xvi-9-vheren-ashurhaddon":"Ashurhaddon",
"r41-unit-xvi-10-falkus-kibre":"Kibre",
"r41-unit-xvi-11-tarik-torgaddon":"Torgaddon",
"r41-unit-xvi-12-xvi-horus-lupercal-the-warmaster":"Horus",
"r41-unit-xvi-13-xvi-horus-ascended-the-warmaster":"Horus Ascended",
}
byid={e.get("id"):e for e in root.iter() if e.get("id")}
lines=["R34 FOCUSED DIAGNOSTIC",f"CAT={root.get('revision')}","","EXACT GENERIC RULE REFERENCES:"]
for n,c in sorted(hits.items(),key=lambda x:(-x[1],x[0].lower())):
    lines.append(f"{n} | count={c} | {examples[n]}")
lines+=["","SONS OF HORUS CORE:"]
for i,label in targets.items():
    e=byid.get(i)
    if e is None:
        lines.append(f"{label} | MISSING ROOT {i}"); continue
    rules=[r.get("name","") for r in e.iter(C("rule")) if r.get("hidden")!="true"]
    links=[l.get("name","") for l in e.iter(C("entryLink"))]
    lines.append(f"{label} | NAME={e.get('name')} | RULES={'; '.join(sorted(set(rules)))} | LINKS={'; '.join(sorted(set(links)))}")

OUT.write_text("\n".join(lines)+"\n",encoding="utf-8")
print(OUT.read_text())
