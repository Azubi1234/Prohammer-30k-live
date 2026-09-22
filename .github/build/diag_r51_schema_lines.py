from lxml import etree
p="Legiones Astartes.cat"
doc=etree.parse(p)
root=doc.getroot()
for target in [3962,3966]:
    print("\\n==== TARGET",target,"====")
    hits=[]
    for e in root.iter():
        if e.sourceline==target:
            hits.append(e)
    for e in hits:
        print("ELEMENT",e.tag.split("}")[-1],e.attrib)
        p=e
        depth=0
        while p is not None and depth<10:
            print("  "*depth,"PARENT",p.tag.split("}")[-1],dict(p.attrib))
            p=p.getparent();depth+=1
    lines=open("Legiones Astartes.cat",encoding="utf-8").read().splitlines()
    for i in range(target-8,target+10):
        if 1<=i<=len(lines):print(f"{i}: {lines[i-1]}")
