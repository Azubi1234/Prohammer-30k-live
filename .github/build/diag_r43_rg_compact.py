from pathlib import Path
import xml.etree.ElementTree as ET, json, re
NS="http://www.battlescribe.net/schema/catalogueSchema"; C=lambda t:f"{{{NS}}}{t}"
r=ET.parse("Legiones Astartes.cat").getroot()
def cons(e):return [(x.get("id"),x.get("type"),x.get("value"),x.get("scope"),x.get("field")) for x in e.findall(f"./{C('constraints')}/{C('constraint')}")]
def costs(e):return [(x.get("typeId"),x.get("value")) for x in e.findall(f"./{C('costs')}/{C('cost')}")]
def cats(e):return [(x.get("targetId"),x.get("primary"),x.get("name")) for x in e.findall(f"./{C('categoryLinks')}/{C('categoryLink')}")]
for e in r.findall(f"./{C('selectionEntries')}/{C('selectionEntry')}"):
    eid=e.get("id") or ""
    if eid.startswith("r41-unit-xix-"):
        print("\\nUNIT",eid,e.get("name"),"type",e.get("type"),"hidden",e.get("hidden"),"cost",costs(e),"cons",cons(e),"cats",cats(e))
        print("  rules:",[(x.get("name"),(x.findtext(C("description")) or "")[:220]) for x in e.findall(f"./{C('rules')}/{C('rule')}")])
        print("  infos:",[(x.get("name"),x.get("targetId"),x.get("type")) for x in e.findall(f"./{C('infoLinks')}/{C('infoLink')}")])
        for g in e.findall(f"./{C('selectionEntryGroups')}/{C('selectionEntryGroup')}"):
            print("  GROUP",g.get("id"),g.get("name"),"hidden",g.get("hidden"),"cons",cons(g))
            for x in g.findall(f"./{C('entryLinks')}/{C('entryLink')}"):print("   LINK",x.get("id"),x.get("name"),"->",x.get("targetId"),"cost",costs(x),"cons",cons(x))
            for x in g.findall(f"./{C('selectionEntries')}/{C('selectionEntry')}"):print("   OPT",x.get("id"),x.get("name"),"cost",costs(x),"cons",cons(x))
        for x in e.findall(f"./{C('selectionEntries')}/{C('selectionEntry')}"):print("  CHILD",x.get("id"),x.get("name"),"type",x.get("type"),"cost",costs(x),"cons",cons(x))
