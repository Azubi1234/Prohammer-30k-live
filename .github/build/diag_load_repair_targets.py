import xml.etree.ElementTree as ET,re
NS="http://www.battlescribe.net/schema/catalogueSchema"; C=lambda t:f"{{{NS}}}{t}"
r=ET.parse("Legiones Astartes.cat").getroot(); ids={e.get("id"):e for e in r.iter() if e.get("id")}
print("TELEPORT ENTRIES")
for e in r.iter():
 n=(e.get("name") or "").lower()
 if "teleportation transponder" in n:
  print(e.tag.split("}")[-1],e.get("id"),e.get("name"),"target",e.get("targetId"))
print("\nBAD DEFAULT GROUP CHILDREN")
for gid in ["r40-da-storm-tactical-tac-loadout","r57-iw-hammer-tactical-tac-loadout"]:
 g=ids.get(gid);print("GROUP",gid,g.get("name"),"default",g.get("defaultSelectionEntryId"))
 if g is not None:
  for boxn in ["selectionEntries","entryLinks"]:
   box=g.find(C(boxn))
   if box is not None:
    for x in list(box):print(" ",boxn,x.tag.split("}")[-1],x.get("id"),x.get("name"),x.get("targetId"))
print("\nAHRIMAN SIMILAR IDS")
for e in r.iter():
 eid=e.get("id") or "";n=e.get("name") or ""
 if "ahriman" in eid.lower() and ("command" in n.lower() or "power weapon" in n.lower() or "champion" in n.lower()):
  print(e.tag.split("}")[-1],eid,n,e.get("targetId"))
