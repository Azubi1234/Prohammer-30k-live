from lxml import etree
import collections
NS="{http://www.battlescribe.net/schema/catalogueSchema}"
def parse(p):
 r=etree.parse(p).getroot()
 return {e.get("id"):e for e in r.iter() if e.get("id")}
a=parse("r47.cat"); b=parse("Legiones Astartes.cat")
changes=[]
for id_,e2 in b.items():
 e1=a.get(id_)
 if e1 is None: continue
 s1=[x.tag.split("}")[-1] for x in e1]
 s2=[x.tag.split("}")[-1] for x in e2]
 if s1!=s2:
  changes.append((id_,e2.tag.split("}")[-1],e2.get("name"),s1,s2))
print("DIRECT_CHILD_ORDER_CHANGES",len(changes))
for x in changes[:500]: print(x)
