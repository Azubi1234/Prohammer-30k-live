import xml.etree.ElementTree as ET, collections
CNS="http://www.battlescribe.net/schema/catalogueSchema"; GNS="http://www.battlescribe.net/schema/gameSystemSchema"
C=lambda t:f"{{{CNS}}}{t}"; G=lambda t:f"{{{GNS}}}{t}"
cr=ET.parse("Legiones Astartes.cat").getroot(); gr=ET.parse("Prohammer 30k.gst").getroot()
cids={e.get("id") for e in cr.iter() if e.get("id")}
gids={e.get("id") for e in gr.iter() if e.get("id")}
allids=cids|gids
pm={c:p for p in cr.iter() for c in p}
def chain(e,lim=8):
 out=[];p=e
 while p is not None and len(out)<lim:
  out.append(f"{p.tag.split('}')[-1]}:{p.get('id')}:{p.get('name')}")
  p=pm.get(p)
 return " > ".join(out)

print("CAT REV",cr.get("revision"),"GST DEP",cr.get("gameSystemRevision"),"GST REV",gr.get("revision"))
checks=[
 ("entryLink",C("entryLink"),"targetId"),
 ("infoLink",C("infoLink"),"targetId"),
 ("categoryLink",C("categoryLink"),"targetId"),
 ("catalogueLink",C("catalogueLink"),"targetId"),
 ("condition",C("condition"),"childId"),
 ("repeat",C("repeat"),"childId"),
]
for label,tag,attr in checks:
 bad=[]
 total=0
 for e in cr.iter(tag):
  v=e.get(attr)
  if not v:continue
  total+=1
  if v not in allids:
   bad.append((e.get("id"),e.get("name"),v,chain(e)))
 print("\\n",label,"TOTAL",total,"UNRESOLVED",len(bad))
 for x in bad[:500]:print("BAD",x)

baddefs=[]
for e in cr.iter(C("selectionEntryGroup")):
 d=e.get("defaultSelectionEntryId")
 if d:
  kids={x.get("id") for x in e.findall(f"./{C('selectionEntries')}/{C('selectionEntry')}")}
  links={x.get("id") for x in e.findall(f"./{C('entryLinks')}/{C('entryLink')}")}
  if d not in kids|links:baddefs.append((e.get("id"),e.get("name"),d,chain(e)))
print("\\nDEFAULTS BAD",len(baddefs))
for x in baddefs[:500]:print("BADDEFAULT",x)

# Structural child-container audit.
allowed={
 "selectionEntries":C("selectionEntry"),
 "selectionEntryGroups":C("selectionEntryGroup"),
 "entryLinks":C("entryLink"),
 "infoLinks":C("infoLink"),
 "categoryLinks":C("categoryLink"),
 "profiles":C("profile"),
 "rules":C("rule"),
 "constraints":C("constraint"),
 "costs":C("cost"),
 "modifiers":C("modifier"),
}
for boxname,childtag in allowed.items():
 bad=[]
 for box in cr.iter(C(boxname)):
  for x in list(box):
   if x.tag!=childtag:bad.append((boxname,x.tag.split('}')[-1],x.get("id"),x.get("name"),chain(box)))
 print("\\nSTRUCT",boxname,"BAD",len(bad))
 for x in bad[:200]:print("BADSTRUCT",x)

# Duplicates
cnt=collections.Counter(e.get("id") for e in cr.iter() if e.get("id"))
dups=[(k,v) for k,v in cnt.items() if v>1]
print("\\nDUP IDS",len(dups))
for x in dups[:500]:print("DUP",x)
