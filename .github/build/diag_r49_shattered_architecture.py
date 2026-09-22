import xml.etree.ElementTree as ET, collections, re
CNS="http://www.battlescribe.net/schema/catalogueSchema"; GNS="http://www.battlescribe.net/schema/gameSystemSchema"
C=lambda t:f"{{{CNS}}}{t}"; G=lambda t:f"{{{GNS}}}{t}"
r=ET.parse("Legiones Astartes.cat").getroot(); g=ET.parse("Prohammer 30k.gst").getroot(); pm={c:p for p in r.iter() for c in p}
def cost(e):return [(x.get("typeId"),x.get("value")) for x in e.findall(f"./{C('costs')}/{C('cost')}")]
def cons(e):return [(x.get("id"),x.get("type"),x.get("value"),x.get("scope"),x.get("field")) for x in e.findall(f"./{C('constraints')}/{C('constraint')}")]
def cats(e):return [(x.get("id"),x.get("name"),x.get("targetId"),x.get("primary")) for x in e.findall(f"./{C('categoryLinks')}/{C('categoryLink')}")]
def mods(e):
 m=e.find(C("modifiers"));return ET.tostring(m,encoding="unicode") if m is not None else ""
def dump(e,depth=0,maxdepth=5):
 ind="  "*depth
 print(f"{ind}{e.tag.split('}')[-1]} id={e.get('id')} name={e.get('name')} type={e.get('type')} hidden={e.get('hidden')} default={e.get('defaultAmount')} cost={cost(e)} cons={cons(e)} cats={cats(e)}")
 if mods(e): print(ind+" MODS "+mods(e)[:5000])
 for il in e.findall(f"./{C('infoLinks')}/{C('infoLink')}"):print(ind+" INFO",il.get("id"),il.get("name"),"->",il.get("targetId"),"hidden",il.get("hidden"))
 for rr in e.findall(f"./{C('rules')}/{C('rule')}"):print(ind+" RULE",rr.get("id"),rr.get("name"),":",(rr.findtext(C("description")) or "")[:350].replace("\\n"," | "))
 if depth>=maxdepth:return
 for tag in ["selectionEntries","selectionEntryGroups","entryLinks"]:
  p=e.find(C(tag))
  if p is not None:
   for x in list(p):dump(x,depth+1,maxdepth)

print("REV",r.get("revision"),"GST",r.get("gameSystemRevision"))
# top configuration candidates
for e in r.findall(f"./{C('selectionEntries')}/{C('selectionEntry')}"):
 n=(e.get("name") or "").lower(); eid=e.get("id") or ""
 if any(k in n for k in ["legion","allegiance","rite","theme"]) or eid in ["legion-i","legion-xx","allegiance-loyalist","allegiance-traitor"]:
  print("\\n==== TOP CONFIG ====");dump(e,0,3)
for gr in r.findall(f"./{C('selectionEntryGroups')}/{C('selectionEntryGroup')}"):
 print("\\n==== ROOT GROUP ====");dump(gr,0,4)
# print ancestors of legion-i and legion-xx
ids={x.get("id"):x for x in r.iter() if x.get("id")}
for eid in ["legion-i","legion-xx","allegiance-loyalist","r25-rite-i-0-the-unbroken-vow"]:
 e=ids.get(eid)
 if e:
  print("\\nANCESTOR",eid)
  p=e
  while p is not None:
   print(p.tag.split("}")[-1],p.get("id"),p.get("name"),cons(p),mods(p)[:1000]);p=pm.get(p)
# generic roots + special root examples
for eid in ["hq-praetor","hq-centurion","tactical-unit","recon-unit","r41-unit-xix-0-mor-deythan-squad","transport-rhino","hs-predator"]:
 e=ids.get(eid)
 if e:
  print("\\n==== ROOT EXAMPLE",eid,"====");dump(e,0,3)
# shared selection groups
for g2 in r.findall(C("sharedSelectionEntryGroups")):
 print("shared group container?")
print("shared groups direct",len(r.findall(f"./{C('sharedSelectionEntryGroups')}/{C('selectionEntryGroup')}")))
