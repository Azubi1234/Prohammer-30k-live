from pathlib import Path
import xml.etree.ElementTree as ET,json
NS="http://www.battlescribe.net/schema/catalogueSchema";C=lambda t:f"{{{NS}}}{t}"
D=Path("modular-catalogues-generated");report={};bad=[]
for p in sorted(D.glob("*.cat")):
 if p.name=="Legiones-Astartes-Generic.cat":continue
 r=ET.parse(p).getroot();empty=[]
 for g in r.iter(C("selectionEntryGroup")):
  # Flag groups that became structurally empty after pruning, except explanatory/config groups with rules/info.
  has_choice=any(True for _ in g.findall(f"./{C('selectionEntries')}/{C('selectionEntry')}")) or any(True for _ in g.findall(f"./{C('entryLinks')}/{C('entryLink')}")) or any(True for _ in g.findall(f"./{C('selectionEntryGroups')}/{C('selectionEntryGroup')}"))
  if not has_choice and not list(g.findall(f"./{C('rules')}/{C('rule')}")) and not list(g.findall(f"./{C('infoLinks')}/{C('infoLink')}")):
   empty.append({"id":g.get("id"),"name":g.get("name")})
 report[p.name]=empty
 if empty:bad.append((p.name,len(empty)))
Path("modular-empty-group-audit.json").write_text(json.dumps(report,indent=2))
print("empty groups",bad,"total",sum(n for _,n in bad))
