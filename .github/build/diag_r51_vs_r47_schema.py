from lxml import etree
from pathlib import Path
import collections,re,json,subprocess

schema=etree.XMLSchema(etree.parse("Catalogue.xsd"))

def validate(path):
    doc=etree.parse(path)
    schema.validate(doc)
    rows=[]
    for e in schema.error_log:
        msg=e.message
        # normalize dynamic ids / numbers lightly, keep structural wording
        rows.append((e.line,e.type_name,msg))
    return rows

r47=validate("r47.cat")
r51=validate("Legiones Astartes.cat")

def norm(msg):
    # remove concrete element attribute values only where useful
    return re.sub(r"line \d+","line #",msg)

c47=collections.Counter((t,norm(m)) for _,t,m in r47)
c51=collections.Counter((t,norm(m)) for _,t,m in r51)

new=[]
for k,v in c51.items():
    extra=v-c47.get(k,0)
    if extra>0:new.append((extra,k[0],k[1]))

gone=[]
for k,v in c47.items():
    extra=v-c51.get(k,0)
    if extra>0:gone.append((extra,k[0],k[1]))

print("R47 errors",len(r47),"unique",len(c47))
print("R51 errors",len(r51),"unique",len(c51))
print("\nNEW/INCREASED IN R51:")
for x in sorted(new,reverse=True)[:300]:print(x)
print("\nREMOVED/DECREASED SINCE R47:")
for x in sorted(gone,reverse=True)[:100]:print(x)

# Show exact R51 occurrences for new message types.
newkeys={(t,m) for _,t,m in new}
print("\nEXACT R51 NEW OCCURRENCES:")
for line,t,m in r51:
    if (t,norm(m)) in newkeys:
        print(f"line={line} {t}: {m}")
