from pathlib import Path
import xml.etree.ElementTree as ET, collections, re
CAT=Path("Legiones Astartes.cat"); GST=Path("Prohammer 30k.gst"); OUT=Path("inspection-r42-salamanders-restriction-summary.txt")
CNS="http://www.battlescribe.net/schema/catalogueSchema"; GNS="http://www.battlescribe.net/schema/gameSystemSchema"
C=lambda t:f"{{{CNS}}}{t}"; G=lambda t:f"{{{GNS}}}{t}"
r=ET.parse(CAT).getroot(); g=ET.parse(GST).getroot()
ids={e.get("id"):e for e in r.iter() if e.get("id")}
pm={c:p for p in r.iter() for c in p}
def descendants_names(e):return [(x.get("id"),x.get("name"),x.tag.split('}')[-1],x.get("targetId")) for x in e.iter() if x is not e]
def has_named(e,needle):return any(needle.lower() in (x.get("name") or "").lower() for x in e.iter())
def max_constraints(e):
    return [(x.get("id"),x.get("value"),x.get("scope")) for x in e.findall(f"./{C('constraints')}/{C('constraint')}") if x.get("type")=="max"]
def cond_refs(e):
    return [x.get("childId") for x in e.iter() if x.tag in (C("condition"),G("condition")) and x.get("childId")]
def links_to(tid,under=None):
    base=under if under is not None else r
    return [x for x in base.iter(C("entryLink")) if x.get("targetId")==tid]
def cat_users(tid):
    out=[]
    for e in r.iter():
        if any(c.get("targetId")==tid for c in e.findall(f"./{C('categoryLinks')}/{C('categoryLink')}")):
            out.append((e.get("id"),e.get("name"),e.tag.split('}')[-1]))
    return out

lines=[f"CAT={r.get('revision')} GST={g.get('revision')}"]
issues=[]

# 0-1/unique audit.
expected_unique=[
("r41-unit-xviii-0-firedrake-terminator-squad","Firedrakes source 0-1"),
("r41-unit-xviii-5-artellus-numeon","Numeon unique"),
("r41-unit-xviii-6-lord-chaplain-nomus-rhy-tan","Nomus unique"),
("r41-unit-xviii-7-xiaphas-jurr-prophet-of-fire","Jurr unique"),
("r41-unit-xviii-8-cassian-dracos","Cassian source 0-1"),
("r41-unit-xviii-9-forgefather-t-kell","T'Kell unique"),
("r41-unit-xviii-10-xviii-vulkan-the-forgefather","Vulkan unique"),
]
lines+=["","UNIQUE / 0-1:"]
for eid,label in expected_unique:
    e=ids[eid]; m=max_constraints(e); lines.append(f"{label}: {m}")
    if not any(float(v)<=1 and s in ("roster","parent") for _,v,s in m):
        issues.append(f"{label} lacks an explicit max-1 constraint")

# Named character options and retinues.
lines+=["","NAMED CHARACTER OPTIONS / RETINUES:"]
for eid,name in [
("r41-unit-xviii-5-artellus-numeon","Numeon"),
("r41-unit-xviii-6-lord-chaplain-nomus-rhy-tan","Nomus"),
("r41-unit-xviii-7-xiaphas-jurr-prophet-of-fire","Jurr"),
("r41-unit-xviii-9-forgefather-t-kell","T'Kell"),
]:
    e=ids[eid]; k=has_named(e,"Krak"); mb=has_named(e,"Melta Bomb"); lines.append(f"{name}: krak={k} melta={mb}")
    if not k or not mb:issues.append(f"{name} missing source-listed Krak/Melta Bomb option(s)")
for eid,name in [("r41-unit-xviii-5-artellus-numeon","Numeon"),("r41-unit-xviii-6-lord-chaplain-nomus-rhy-tan","Nomus")]:
    e=ids[eid]; ret=[x for x in e.iter(C("selectionEntryGroup")) if "retinue" in (x.get("name") or "").lower()]
    lines.append(f"{name} selectable retinue groups: {[(x.get('id'),x.get('name')) for x in ret]}")
    if not ret:issues.append(f"{name} has retinue only as text, not selectable")

# Armoury access counts.
lines+=["","SALAMANDERS ARMOURY LINK COUNTS:"]
for tid in ["r46-sal-mantle","r46-sal-mastercrafted","r46-sal-artificer-armour","r46-sal-inferno-pistol","r46-sal-heavy-flamer","r46-sal-ceramite"]:
    arr=links_to(tid);lines.append(f"{tid}: {len(arr)} links")
# Generic HQ discount checks.
for hid in ["hq-praetor","hq-centurion"]:
    h=ids[hid]
    lines.append(f"{hid}: generic mastercraft links={len(links_to('gear-hq-mastercraft',h))}, sal-discount mastercraft links={len(links_to('r46-sal-mastercrafted',h))}, generic artificer links={len(links_to('gear-hq-artificer',h))}, sal-artificer links={len(links_to('r46-sal-artificer-armour',h))}, inferno={len(links_to('r46-sal-inferno-pistol',h))}, mantle={len(links_to('r46-sal-mantle',h))}")
    if len(links_to("r46-sal-mastercrafted",h))==0:issues.append(f"{hid} lacks Salamanders +10 Master-crafted selector")
# Artificer armour should reach non-IC armoury holders; rough current link count.
if len(links_to("r46-sal-artificer-armour"))<5:issues.append("Salamanders +15 Artificer Armour access is not propagated broadly enough")
# Ceramite should appear on eligible vehicles.
if len(links_to("r46-sal-ceramite"))<5:issues.append("Salamanders +10 Reinforced Ceramite is not propagated to eligible Vehicles/Dreadnoughts")

# Covenant deep strike/pod enforcement.
COV="r25-rite-xviii-0-the-covenant-of-fire"
pod_targets={"transport-drop-pod","transport-dreadclaw","transport-dreadnought-pod"}
allpod=[l for l in r.iter(C("entryLink")) if l.get("targetId") in pod_targets]
pod_cov=[l for l in allpod if COV in cond_refs(l)]
lines+=["",f"COVENANT DEEP STRIKE: pod/dreadclaw links={len(allpod)}, links conditioned by Covenant={len(pod_cov)}"]
if len(pod_cov)==0:issues.append("Covenant of Fire does not mechanically block Drop Pod/Dreadclaw selections")

# Fortification/Allied actual structures.
fg=[]
for e in g.iter():
    if any(k in (e.get("name") or "").lower() for k in ["fortification","allied"]):fg.append((e.tag.split('}')[-1],e.get("id"),e.get("name")))
lines+=["","FORTIFICATION / ALLIED STRUCTURES:",str(fg[:100])]
if fg:issues.append("Fortification/Allied structures exist in GST and Rite prohibitions should be mechanically checked")

# Awakening category coverage.
lines+=["","AWAKENING TYPE COVERAGE:"]
for cat in ["r40-sal-awakening-jump","r40-sal-awakening-jetbike","r40-sal-awakening-skimmer","r40-sal-awakening-flyer","r40-sal-awakening-chaplain"]:
    u=cat_users(cat);lines.append(f"{cat}: {len(u)} users -> {u[:80]}")
# Vulkan hide condition.
v=ids["r41-unit-xviii-10-xviii-vulkan-the-forgefather"];refs=cond_refs(v);lines.append(f"Vulkan conditions={refs}")
if "r25-rite-xviii-1-the-awakening-fire" not in refs:issues.append("Awakening Fire does not mechanically hide Vulkan")
# Chaplain counter.
chap=cat_users("r40-sal-awakening-chaplain"); lines.append(f"Chaplain-equivalent users={chap}")
if not chap:issues.append("Awakening Fire Chaplain requirement has no tagged qualifying models")

# Adherent support / compulsory behavior.
ad=ids["r41-unit-xviii-3-adherent-squad"]
lines+=["","ADHERENT SUPPORT / COMPULSORY:",f"Adherent cats={[(x.get('targetId'),x.get('name')) for x in ad.findall(f'./{C('categoryLinks')}/{C('categoryLink')}')]}"]
force=next((x for x in g.iter(G("forceEntry")) if x.get("id")=="force-standard"),None)
trooplinks=[x for x in force.findall(f"./{G('categoryLinks')}/{G('categoryLink')}") if "troop" in (x.get("name") or "").lower()]
lines.append("Force troop links="+str([(x.get("id"),x.get("name"),x.get("targetId"),[(c.get("type"),c.get("value")) for c in x.findall(f'./{G("constraints")}/{G("constraint")}')]) for x in trooplinks]))
# Check Support Squad text but no hidden compulsory tag obvious.
if "Support Squad" in " ".join((x.get("name") or "") for x in ad.iter(C("infoLink"))) and not any("compuls" in (x.get("name") or "").lower() for x in ad.iter(C("categoryLink"))):
    issues.append("Adherent Support Squad may still satisfy generic compulsory Troops unless global support handling exists elsewhere")

# Firedrake roster-wide limit across retinue copies.
firedrakes=[e for e in r.iter(C("selectionEntry")) if "firedrake terminator squad" in (e.get("name") or "").lower()]
lines+=["","FIREDRAKE COPIES:",f"count={len(firedrakes)}"]
for e in firedrakes[:50]:lines.append(f"{e.get('id')} | {e.get('name')} | max={max_constraints(e)} | cats={[(c.get('targetId'),c.get('name')) for c in e.findall(f'./{C('categoryLinks')}/{C('categoryLink')}')]}")
if len(firedrakes)>1 and not any(any(s=="roster" and float(v)<=1 for _,v,s in max_constraints(e)) for e in firedrakes):
    issues.append("Firedrake 0-1 is not shared roster-wide across normal/retinue copies")

lines+=["","ISSUES FOUND:"]
lines += [f"- {x}" for x in issues] if issues else ["- NONE"]
OUT.write_text("\n".join(lines)+"\n",encoding="utf-8")
print(OUT.read_text())
