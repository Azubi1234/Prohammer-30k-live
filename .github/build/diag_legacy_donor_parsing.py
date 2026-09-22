import xml.etree.ElementTree as ET,re
NS="http://www.battlescribe.net/schema/catalogueSchema"; C=lambda t:f"{{{NS}}}{t}"
r=ET.parse("Legiones Astartes.cat").getroot()
def source(e):
 for x in e.findall(f"./{C('rules')}/{C('rule')}"):
  if (x.get("name") or "")=="Source Entry":return x.findtext(C("description")) or ""
 return ""
def special_list(t):
 ls=t.splitlines();out=[];active=False
 for line in ls:
  s=line.strip()
  if s.lower().startswith("special rules:"):active=True;continue
  if active:
   if s.startswith("•"):out.append(s[1:].strip());continue
   if out:break
 return out
def bullet_section(t,title):
 ls=t.splitlines();out=[];active=False
 for line in ls:
  s=line.strip()
  if s.lower().startswith(title.lower()+":"):active=True;continue
  if active:
   if s.startswith("•"):out.append(s[1:].strip());continue
   if out:break
 return out
def find_desc(t,name):
 ls=t.splitlines();key=re.sub(r"[^a-z0-9]+"," ",name.lower()).strip()
 def nk(s):return re.sub(r"[^a-z0-9]+"," ",s.lower()).strip()
 starts=[]
 for i,line in enumerate(ls):
  if nk(line.strip())==key:starts.append(i)
 if not starts:return None
 # use last occurrence, usually definition heading after the list
 i=starts[-1];buf=[]
 for line in ls[i+1:]:
  s=line.strip()
  if not s:continue
  # likely a new all-caps heading/section
  if (s.upper()==s and any(ch.isalpha() for ch in s) and len(s)<90) or s.startswith("•") or re.match(r"^(OPTIONS|DEDICATED TRANSPORT|WEAPONS|WARGEAR|SPECIAL RULES|Unit |Force Organisation)",s,re.I):
   if buf:break
  buf.append(s)
  if len(" ".join(buf))>1200:break
 return " ".join(buf) if buf else None
shared={}
for x in r.findall(f"./{C('sharedRules')}/{C('rule')}"):shared[(x.get("name") or "").casefold()]=x.get("id")
for e in r.findall(f"./{C('selectionEntries')}/{C('selectionEntry')}"):
 t=source(e)
 if not t:continue
 if not ((e.get("id") or "").startswith(("r41-unit-xiii-","r41-unit-xiv-","r41-unit-xv-","r41-unit-xvi-"))):continue
 sp=special_list(t);wg=bullet_section(t,"Wargear")
 print("\\nUNIT",e.get("id"),e.get("name"))
 print("WARGEAR",wg)
 print("SPECIALS",sp)
 direct={(x.get("name") or "").casefold() for x in list(e.findall(f"./{C('rules')}/{C('rule')}"))+list(e.findall(f"./{C('infoLinks')}/{C('infoLink')}"))}
 for n in sp:
  print(" RULE",n,"direct",n.casefold() in direct,"shared",shared.get(n.casefold()),"desc",repr(find_desc(t,n)))
