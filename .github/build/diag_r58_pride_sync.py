import xml.etree.ElementTree as ET
NS="http://www.battlescribe.net/schema/catalogueSchema"; C=lambda t:f"{{{NS}}}{t}"
r=ET.parse("Legiones Astartes.cat").getroot(); ids={x.get("id"):x for x in r.iter() if x.get("id")}
def cost(e):return [(x.get("typeId"),x.get("value")) for x in e.findall(f"./{C('costs')}/{C('cost')}")]
def con(e):return [(x.get("id"),x.get("type"),x.get("value"),x.get("scope"),x.get("field")) for x in e.findall(f"./{C('constraints')}/{C('constraint')}")]
def cats(e):return [(x.get("id"),x.get("name"),x.get("targetId"),x.get("primary")) for x in e.findall(f"./{C('categoryLinks')}/{C('categoryLink')}")]
def mods(e):
 m=e.find(C("modifiers"));return ET.tostring(m,encoding="unicode") if m is not None else ""
def dump(e,depth=0,maxdepth=4):
 ind="  "*depth
 print(f"{ind}{e.tag.split('}')[-1]} id={e.get('id')} name={e.get('name')} type={e.get('type')} hidden={e.get('hidden')} default={e.get('defaultAmount')} cost={cost(e)} cons={con(e)} cats={cats(e)}")
 if mods(e):print(ind+" MODS "+mods(e)[:10000])
 if depth>=maxdepth:return
 for tag in ["selectionEntries","selectionEntryGroups","entryLinks"]:
  p=e.find(C(tag))
  if p is not None:
   for x in list(p):dump(x,depth+1,maxdepth)
for eid in ["veteran-unit","r35-pride-veteran-veteran-unit","rite-pride"]:
 print("\\n====",eid,"====");dump(ids[eid],0,5)
