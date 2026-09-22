from pathlib import Path
import re, xml.etree.ElementTree as ET

CAT=Path("Legiones Astartes.cat")
OUT=Path("inspection-r34-reference-rules-soh-names.txt")
NS="http://www.battlescribe.net/schema/catalogueSchema"
C=lambda t:f"{{{NS}}}{t}"

root=ET.parse(CAT).getroot()
pm={c:p for p in root.iter() for c in p}

def anc_names(e,limit=4):
    out=[]
    p=pm.get(e)
    while p is not None and len(out)<limit:
        if p.get("name"): out.append(p.get("name"))
        p=pm.get(p)
    return " > ".join(out)

placeholder=[]
for r in root.iter(C("rule")):
    d=(r.findtext(C("description")) or "").strip()
    low=d.lower()
    if (re.search(r"\b(this|the) (unit|model|vehicle|squad) (has|gains|possesses)\b",low)
        or re.fullmatch(r"(this )?(unit|model) has [^.]+\.?", low)
        or re.fullmatch(r"(this )?(unit|model) gains [^.]+\.?", low)):
        placeholder.append((r.get("name",""),d,anc_names(r),r.get("id","")))

# Also collect suspicious one-line self-reference descriptions.
selfrefs=[]
for r in root.iter(C("rule")):
    n=(r.get("name") or "").strip()
    d=(r.findtext(C("description")) or "").strip()
    if not n or not d: continue
    dl=d.lower()
    nl=n.lower()
    if len(d)<180 and (dl==nl or dl in {f"this unit has {nl}.",f"this model has {nl}.",f"this unit gains {nl}.",f"this model gains {nl}."}):
        selfrefs.append((n,d,anc_names(r),r.get("id","")))

# Sons of Horus roots / clones.
soh=[]
for e in root.iter(C("selectionEntry")):
    n=e.get("name") or ""
    i=e.get("id") or ""
    if ("xvi" in i.lower() or "soh" in i.lower() or any(k in n.lower() for k in [
        "justaerin","reaver attack","chieftain squad","luperci","abaddon","aximand",
        "loken","maloghurst","tybalt marr","ashurhaddon","falkus kibre","tarik torgaddon",
        "horus lupercal"
    ])):
        rules=[]
        for r in e.iter(C("rule")):
            if r.get("hidden")!="true": rules.append(r.get("name",""))
        links=[x.get("name","") for x in e.iter(C("entryLink")) if x.get("type")=="upgrade"]
        cats=[x.get("name","") for x in e.findall(f".//{C('categoryLink')}")]
        soh.append((i,n,sorted(set(rules)),sorted(set(links)),cats))

# Named-character-ish all-caps roots/profiles, plus Primarch prefixed names.
name_candidates=[]
roman_prefix=re.compile(r"^(?:I|II|III|IV|V|VI|VII|VIII|IX|X|XI|XII|XIII|XIV|XV|XVI|XVII|XVIII|XIX|XX)\s*[—-]\s*",re.I)
for e in root.iter(C("selectionEntry")):
    n=(e.get("name") or "").strip()
    if not n: continue
    # all-caps letters, or legion numeral prefix and a Primarch-ish root
    letters=re.sub(r"[^A-Za-z]","",n)
    allcaps=bool(letters) and letters==letters.upper() and len(letters)>=4
    pref=bool(roman_prefix.match(n))
    # focus root-ish named entries, not generic unit names, by profile model name or common title punctuation.
    model_profiles=[p.get("name","") for p in e.findall(f".//{C('profile')}") if p.get("typeId")=="prof-model"]
    proper_profile=any(mp and mp.lower() not in n.lower()[:0] for mp in model_profiles)
    if pref or (allcaps and any("," in n or "THE " in n or "'" in n or "PRIMARCH" in n for _ in [0])):
        name_candidates.append((e.get("id",""),n,model_profiles,anc_names(e,2)))

lines=[
    "R34 DIAGNOSTIC — REFERENCE RULES / SONS OF HORUS / NAMES",
    f"CAT revision={root.get('revision')}",
    "",
    f"PLACEHOLDER RULES ({len(placeholder)}):"
]
for x in placeholder:
    lines.append(" | ".join(x))
lines += ["",f"SELF-REFERENCE RULES ({len(selfrefs)}):"]
for x in selfrefs:
    lines.append(" | ".join(x))
lines += ["",f"SONS OF HORUS CANDIDATES ({len(soh)}):"]
for i,n,rules,links,cats in soh:
    lines.append(f"{i} | {n} | RULES={'; '.join(rules)} | LINKS={'; '.join(links)} | CATS={'; '.join(cats)}")
lines += ["",f"NAME CANDIDATES ({len(name_candidates)}):"]
for i,n,prof,anc in name_candidates:
    lines.append(f"{i} | {n} | PROFILES={'; '.join(prof)} | ANC={anc}")

OUT.write_text("\n".join(lines)+"\n",encoding="utf-8")
print(OUT.read_text())
