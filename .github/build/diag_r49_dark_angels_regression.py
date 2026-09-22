from pathlib import Path
import xml.etree.ElementTree as ET, collections
CAT=Path("Legiones Astartes.cat"); OUT=Path("inspection-r49-dark-angels-regression.txt")
NS="http://www.battlescribe.net/schema/catalogueSchema"; C=lambda t:f"{{{NS}}}{t}"
r=ET.parse(CAT).getroot(); ids={x.get("id"):x for x in r.iter() if x.get("id")}; pm={c:p for p in r.iter() for c in p}
def cons(e):return [(x.get("id"),x.get("type"),x.get("value"),x.get("scope"),x.get("field")) for x in e.findall(f"./{C('constraints')}/{C('constraint')}")]
def path(e):
 out=[];p=e
 while p is not None and len(out)<9:
  out.append(f"{p.tag.split('}')[-1]}:{p.get('id')}:{p.get('name')}");p=pm.get(p)
 return " > ".join(out)
def direct_children(g):
 out=[]
 for boxname in ["selectionEntries","entryLinks","selectionEntryGroups"]:
  box=g.find(C(boxname))
  if box is not None:
   for x in list(box):out.append((boxname,x.tag.split("}")[-1],x.get("id"),x.get("name"),x.get("targetId"),x.get("hidden")))
 return out
checks=[];lines=[f"CAT={r.get('revision')} GSTDEP={r.get('gameSystemRevision')}"]
def ck(name,ok):
 checks.append((name,bool(ok)));lines.append(f'{"PASS" if ok else "FAIL"}: {name}')
 if not ok:raise RuntimeError("DA regression failed: "+name)

ck("CAT49 baseline",r.get("revision")=="49")
# Schema containers globally clean after R49.
bad=[]
for box in r.iter(C("selectionEntries")):
 for x in list(box):
  if x.tag!=C("selectionEntry"):bad.append((x.get("id"),x.get("name"),path(x)))
ck("selectionEntries schema clean",not bad)

# Representative generic units that should expose Hexagrammaton Wing under Dark Angels.
expected=["hq-praetor","hq-centurion","tactical-unit","veteran-unit","terminator-unit","assault-unit","recon-unit","fa-seeker","hs-heavy-support-squad"]
wing_groups=[]
for eid in expected:
 e=ids.get(eid);ck(eid+" exists",e is not None)
 gs=[g for g in e.iter(C("selectionEntryGroup")) if (g.get("name") or "")=="Hexagrammaton Wing"]
 ck(eid+" has Hexagrammaton Wing",len(gs)>=1)
 for g in gs:
  wing_groups.append(g)
  txt=ET.tostring(g,encoding="unicode")
  ck(g.get("id")+" DA gated","legion-i" in txt)
  # Should be 6 direct wing choices.
  ch=direct_children(g)
  names=[n for _,_,_,n,_,_ in ch if n]
  ck(g.get("id")+" has six wing choices",sum(1 for n in names if any(k in n.lower() for k in ["stormwing","deathwing","dreadwing","ironwing","firewing","ravenwing"]))==6)
  # When DA selected, group becomes mandatory.
  mins=[x for x in g.findall(f"./{C('constraints')}/{C('constraint')}") if x.get("type")=="min"]
  ck(g.get("id")+" has min constraint",bool(mins))
  ck(g.get("id")+" DA makes mandatory","field=\""+mins[0].get("id")+"\"" in txt and "value=\"1\"" in txt)

# Dark Angels armoury options across representative units must be schema-correct links and resolve.
da_links=[]
for e in r.iter(C("entryLink")):
 txt=ET.tostring(e,encoding="unicode")
 nm=(e.get("name") or "").lower()
 if "legion-i" in txt or any(k in nm for k in ["calibanite","terranic","plasma repeater","plasma burner","stasis shell","molecular acid"]):
  da_links.append(e)
ck("Dark Angels conditional armoury links exist",len(da_links)>20)
for l in da_links:
 ck(l.get("id")+" target resolves",not l.get("targetId") or l.get("targetId") in ids)

# First Legion-specific roots: must have a fixed DA identity and no Source Entry dump.
da_fixed=[]
for e in r.findall(f"./{C('selectionEntries')}/{C('selectionEntry')}"):
 names=[x.get("name") or "" for x in e.findall(f"./{C('rules')}/{C('rule')}")]+[x.get("name") or "" for x in e.findall(f"./{C('infoLinks')}/{C('infoLink')}")]
 if "Legiones Astartes (Dark Angels)" in names:
  da_fixed.append(e)
ck("Dark Angels fixed roots exist",len(da_fixed)>0)
for e in da_fixed:
 names=[x.get("name") or "" for x in e.findall(f"./{C('rules')}/{C('rule')}")]+[x.get("name") or "" for x in e.findall(f"./{C('infoLinks')}/{C('infoLink')}")]
 ck(e.get("id")+" no Source Entry","Source Entry" not in names)

# Print concise inventory for R50 compatibility.
lines+=["",f"Hexagrammaton groups checked: {len(wing_groups)}",f"DA conditional armoury links checked: {len(da_links)}",f"Fixed DA top-level entries: {len(da_fixed)}",""]
for e in da_fixed:
 lines.append(f"DA_FIXED {e.get('id')} | {e.get('name')} | hidden={e.get('hidden')}")
OUT.write_text("\n".join(lines)+"\n",encoding="utf-8")
print(OUT.read_text())
