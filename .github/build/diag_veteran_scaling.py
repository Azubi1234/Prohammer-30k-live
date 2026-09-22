import xml.etree.ElementTree as ET
NS="http://www.battlescribe.net/schema/catalogueSchema"; C=lambda t:f"{{{NS}}}{t}"
r=ET.parse("Legiones Astartes.cat").getroot(); ids={x.get("id"):x for x in r.iter() if x.get("id")}
def cost(e): return [(x.get("typeId"),x.get("value")) for x in e.findall(f"./{C('costs')}/{C('cost')}")]
def con(e): return [(x.get("id"),x.get("type"),x.get("value"),x.get("scope"),x.get("field")) for x in e.findall(f"./{C('constraints')}/{C('constraint')}")]
def mods(e):
 m=e.find(C("modifiers")); return ET.tostring(m,encoding="unicode") if m is not None else ""
def dump(e,d=0,maxd=6):
 ind="  "*d
 print(f"{ind}{e.tag.split('}')[-1]} id={e.get('id')} name={e.get('name')} type={e.get('type')} default={e.get('defaultAmount')} hidden={e.get('hidden')} cost={cost(e)} cons={con(e)}")
 if mods(e): print(ind+" MODS "+mods(e)[:4000])
 if d>=maxd:return
 for tag in ["selectionEntries","selectionEntryGroups","entryLinks"]:
  p=e.find(C(tag))
  if p is not None:
   for x in list(p): dump(x,d+1,maxd)

for eid in ["veteran-unit","r41-unit-xv-0-khenetai-occult-cabal","r41-unit-xv-1-sekhmet-terminator-cabal"]:
 e=ids.get(eid)
 print("\\n====",eid,"====")
 if e: dump(e)
 else: print("MISSING")
