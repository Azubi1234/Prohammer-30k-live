from pathlib import Path
import re, xml.etree.ElementTree as ET

CAT=Path("Legiones Astartes.cat")
IDX=Path("index.xml")
OUT=Path("inspection-live-r34-rules-soh-names.txt")
APPLY=True

NS="http://www.battlescribe.net/schema/catalogueSchema"
ET.register_namespace("",NS)
C=lambda t:f"{{{NS}}}{t}"
tree=ET.parse(CAT); root=tree.getroot()
if root.get("revision")!="33":
    raise RuntimeError(f"R34 expected catalogue revision 33, got {root.get('revision')}")

# ------------------------------------------------------------------
# Canonical ProHammer v2.4 rule text.
# Sourced from the Universal Special Rules on pp.63-65 and the
# Deepstrike / Independent Character sections of the uploaded rules.
# ------------------------------------------------------------------
USR={
"Acute Senses":"Unit can re-roll which random table edge it arrives on from reserves.",
"Assault Vehicle":"Passengers disembarking from an Assault Vehicle do not lose their extra Attack charge bonuses when disembarking and charging from an Assault Vehicle. All Open-topped Vehicles count as Assault Vehicles.",
"Crusader":"Roll extra dice when advancing and use the highest. Adds D3\" to pursuit rolls.",
"Fleet":"Unit may still charge into melee combat even if it advanced this turn.",
"Hit & Run":"Unit may choose to leave combat at the end of the Assault phase after taking break tests. Take an Initiative test. If passed, the unit moves 3D6\" in a chosen direction. The unit does not count as having broken or fallen back, and any now unengaged enemy units it moved away from may only consolidate 3\".",
"Infiltrate":"During deployment, may be set up after normal deployment. The unit must be set up 12\" or more away from enemy units that do not have line of sight and 18\" or more away from enemy units with line of sight. The unit also gains Outflank.",
"Jink":"Units that moved in the prior turn can activate Jink as a reaction to being shot and gain a 5+ Cover Save until the start of their next turn. If a model with this rule used Turbo-boosters or moved at Flat Out speed, it gains a 4+ Cover Save instead. Models that use Jink only shoot with Snap Fire on their next turn.",
"Move Through Cover":"Roll 3D6 for Difficult Terrain tests instead of 2D6 and choose the highest.",
"Outflank":"When units with this ability enter from Reserve, roll a D6: on 1-2 enter from the player's left table edge; on 3-4 enter from the player's right; on 5-6 the player chooses the side edge. The unit may alternatively enter from Reserve normally from the player's normal table edge(s).",
"Power of the Machine Spirit":"A Vehicle moving less than Flat Out speed and not using Smoke Launchers can fire one additional main weapon at full Ballistic Skill.",
"Relentless":"Model may move and fire Heavy, Ordnance, Salvo or Rapid Fire weapons as if it remained stationary. It may still charge even after firing such weapons.",
"Scouts":"May always be deployed. Before rolling to see who goes first, may take a bonus normal move. Confers Scout ability to a Dedicated Transport it is mounted in. If both players have Scouts, roll-off and alternate moving Scouts starting with the winner. The unit also gains Outflank.",
"Skilled Rider":"Re-roll failed Dangerous Terrain tests. Gains +1 to any Jink saves.",
"Slow and Purposeful":"Relentless and always moves as if in Difficult Terrain.",
"Swift":"Units composed entirely of Swift models fall back 3D6\" instead of 2D6\". During pursuit and retreat moves, they move their Initiative value + 2D6\".",
"Turbo-Boosters":"Instead of a normal move, the unit may Turbo-boost up to 24\". Turbo-boosting units may not shoot in the Shooting phase or charge in the Assault phase. Units that also have Jink gain a 4+ Cover Save if they used a Turbo-boost move in their last Movement phase.",
"Adamantium Will":"+1 bonus to Deny the Witch, and the unit may attempt to Deny the Witch even if it is not a Psyker.",
"And They Shall Know No Fear":"Automatically passes Regroup tests at the start of the turn and may be used normally for the rest of the turn. If caught by a pursuit, the unit automatically regroups and is re-engaged in close combat, and does not suffer extra wounds from being caught in a pursuit. Immune to Fear.",
"Brotherhood of Psykers":"Unit counts as a Mastery Level 1 Psyker. Uses the unit's highest Leadership value for Psychic Power tests.",
"Bulky":"Counts as two models for Transport Capacity. Very Bulky counts as three models. Extremely Bulky counts as five.",
"Counter-Attack":"If this unit is not engaged with any enemy models and an enemy unit successfully completes a charge move against it, the unit may take a Leadership test. If passed, this unit gains +1 Attack during the Assault phase.",
"Daemon":"Model gains a 5+ Invulnerable Save and causes Fear.",
"Eternal Warrior":"Immune to Instant Death / Massive Wounds. The model suffers 1 Wound instead of D3 Wounds.",
"Fear":"Enemy units in base contact must pass a Leadership test before resolving their close combat attacks. If the test fails, those units attack with WS1 in the melee engagement.",
"Fearless":"Automatically passes all Morale and Pinning tests. May not Take Cover! or choose to voluntarily fail a break test.",
"Furious Charge":"Models gain +1 Strength and +1 Initiative in assault on the turn they charged.",
"Hammer of Wrath":"On the turn this unit charges, models may perform one of their normally allowed Attacks at Initiative 10 instead of during their normal Initiative step.",
"Hatred":"If a unit with Hatred is engaged in melee combat against a hated enemy type, and was not engaged in melee combat with that enemy type during the prior turn, the unit may re-roll all failed close combat To Hit rolls against the hated target.",
"It Will Not Die":"Roll a D6 at the start of its turn for each model with fewer than its starting Wounds but which is not destroyed. On a 5+ it regains one lost Wound. A Vehicle with It Will Not Die may, on a 5+, repair an Engine Damaged, Weapon Destroyed or Immobilized damage result.",
"Night Vision":"Units containing at least one model with this effect ignore Night Fighting restrictions.",
"Preferred Enemy":"The unit can re-roll failed hits in close combat against the indicated Preferred Enemy.",
"Shrouded":"Adds +2 to the value of Cover Saves conferred by terrain, to a maximum of 2+. If in the open, receives a 5+ Cover Save. Does not stack with Stealth.",
"Stealth":"Adds +1 to the value of Cover Saves conferred by terrain, to a maximum of 2+. If in the open, receives a 6+ Cover Save. Does not stack with Shrouded.",
"Stubborn":"Ignore negative Leadership modifiers on Morale and Pinning tests.",
"Swarms":"Have Stealth and Vulnerable to Blasts/Templates.",
"Tank Hunters":"+1 to Armour Penetration rolls. Automatically passes Tank Shock Morale tests.",
"Vulnerable to Blasts/Templates":"Each hit counts as two hits from Blast/Template weapons.",
"Zealot":"A unit with at least one model with this effect gains Fearless and Hatred.",
"Armourbane":"Attack rolls 2D6 for Armour Penetration.",
"Blind":"A unit hit by a weapon with Blind must take an Initiative test. If failed, all models are reduced to BS1 and WS1 until the end of their next turn.",
"Concussive":"A model suffering an unsaved Wound is reduced to Initiative 1 until the end of the following Assault phase. Against units with no Initiative, such as Vehicles, it inflicts Crew Shaken if hit.",
"Fleshbane":"Always wounds on a 2+. No effect versus Vehicles.",
"Gets Hot":"If a model shooting this weapon rolls a 1 To Hit, it causes an automatic Wound on that model and it must take an Armour or Invulnerable Save. If the save fails, the shooting model suffers a Wound. Vehicles are not affected by Gets Hot.",
"Haywire":"Instead of normal Armour Penetration, roll a D6: 1 = no effect; 2-5 = Glancing Hit; 6 = Penetrating Hit.",
"Ignores Cover":"Weapon negates any Cover Saves.",
"Interceptor":"A weapon with this rule may be fired at an enemy unit immediately after that enemy unit enters from Reserves and ends the Movement phase within line of sight and range of the weapon. If used this way, the firing model may not shoot in the Shooting phase of its following turn.",
"Lance":"Treat Vehicle Armour Values greater than 12 as 12.",
"Master-Crafted":"Re-roll one failed To Hit roll per turn.",
"Melta":"When making Armour Penetration rolls, roll 2D6 instead of D6 if the target is at half range or less.",
"Monster Hunter":"Units containing at least one model with this effect re-roll failed To Wound rolls against Monstrous Creatures.",
"Pinning":"Unsaved Wounds caused by this weapon force the unit to take a Pinning Test.",
"Poison":"Wounds on a fixed number regardless of Strength. If the attacker's Strength is higher than the defender's Toughness, re-roll failed Wounds. Poison weapons have no effect against Vehicles. Default value is 4+.",
"Rampage":"Models gain +D3 Attacks if the enemy units contain more models than friendly models that are locked in close combat.",
"Rending":"On a To Wound roll of 6, causes an automatic Wound and the weapon is treated as AP2 for ranged attacks and a Power Weapon attack for melee attacks. Against Vehicles, an Armour Penetration roll of 6 adds an additional D3 to the penetration result.",
"Shred":"Re-roll failed To Wound rolls.",
"Soul Blaze":"Units wounded by this attack are set ablaze. Roll a D6 at the end of each turn. On a 4+, the unit takes D3 Strength 4 AP5 hits with no Cover Saves. On less than 4, the blaze goes out and the effect is removed.",
"Split Fire":"A unit with this rule automatically passes any Split Fire test and may split its fire between up to three different targets instead of two.",
"Sniper":"Hits on a 2+, wounds on a 4+, and gains Rending and Pinning.",
"Strikedown":"Models suffering one or more Wounds from this weapon, even if saved, move as if in Difficult Terrain on their next turn.",
"Torrent":"Place the Flame Template in any orientation so long as the Template is entirely within 12\" range and the tip of the narrower end is closer to the firing model than the tip of the wider end.",
"Twin-Linked":"Re-roll failed To Hit rolls with this weapon. Does not count as two weapons. Twin-linked Template weapons automatically hit all models fully or partially under the Template.",
"Two-Handed":"A model attacking with this weapon does not receive a bonus Attack for having additional close combat weapons.",
"Unwieldy":"A model attacking with this weapon is Initiative 1 unless it is a Monstrous Creature or Vehicle Walker.",
}

DEEP_STRIKE="""Units that enter play from Reserves by Deepstriking are placed directly on the board and do not have to move onto the table from a table edge.

1. Determine Target Location: when the unit is available to enter play, place one model (the centre model) anywhere on the table more than 2\" from enemy models.
2. Roll for Deepstrike Scattering: roll 2D6 and a Scatter die. On a Hit, proceed to placement. On an arrow, determine an adjusted location 2D6\" in that direction. If that location would be on a friendly model, stop 2\" short. If it falls in impassable terrain, off the table, or on top of or within 2\" of an enemy model, a Deepstrike Mishap occurs.
Deepstrike Mishap: the opposing player instead places the centre model within 12\" of the target location. The chosen location may not be in impassable terrain, off the table, within 2\" of an enemy model, or within 2\" of its original position. If no viable position exists, the unit returns to Reserves to redeploy next turn. The unit must also pass a Pinning Test or become Pinned for the remainder of the turn.
3. Place Remaining Models: place all other models within 2\" of the centre model. Models may not be placed in impassable terrain or within 2\" of enemy models. Models that cannot fit within 2\" may be placed in base contact with another model and as close to the centre as possible; any model that still cannot be placed is destroyed.

Using Deepstriking Units: models arriving by Deepstrike or disembarking from Deepstriking Vehicles may not make a normal move after arriving, but may shoot, Advance D6\", or assault. Units charging in the turn they arrived by Deepstrike gain no bonus Attacks for charging and no benefit from assault grenades. Deepstriking Vehicles count as having moved at Cruising Speed on the turn they arrive."""

INDEPENDENT_CHARACTER="""Models with the Independent Character type may join other units.
• Joining Units: an Independent Character functions as part of the joined unit for movement, coherency, shooting, Leadership, assaulting and other purposes. It may not join units that include Vehicle models or Monstrous Creatures.
• Joining During Deployment: an Independent Character may join a unit before deployment. If the joined units are in Reserve, they count as one unit when rolling to enter play. If either has a special deployment rule such as Infiltrate or Deep Strike, both must have the same ability to use it.
• Joining and Leaving: during the Movement phase an Independent Character may join a unit by moving within coherency and declaring the join after its move, or leave by declaring this before moving. It may not join and leave, or leave and join, in the same turn, and may not leave a unit that is engaged in melee, Broken or Pinned.
• Shooting: an Independent Character joined to a unit may declare and resolve shooting against a different target from the joined unit.
• Assault: if joined, it must charge with the unit and enter base contact if possible. In melee it is treated as part of the unit. It may make pile-in moves first to remain engaged.
• Allocating Wounds: unsaved Wounds suffered by a joined unit do not have to be allocated to an already wounded Independent Character.
• Shooting Independent Characters: an unjoined Independent Character may only be selected as a shooting target if it is within 18\" and the closest figurine model; or more than 18\" away and more than 6\" from a friendly figurine unit; or is a Monstrous Creature/Flying Monstrous Creature."""

LEGIONES="""All models with this special rule also have And They Shall Know No Fear as presented in ProHammer Classic. They are not Fearless unless another rule specifically grants Fearless. In addition, each model possesses one named version of Legiones Astartes corresponding to its Legion. A model may only ever possess one named version. Models with a named Legiones Astartes special rule gain any additional rules and abilities associated with that Legion. Unless specifically stated otherwise, Vehicles belonging to a Legiones Astartes army do not themselves possess the Legiones Astartes special rule."""

MASTER_OF_LEGION="""A model with Master of the Legion permits its Detachment to use one Rite of War for which it qualifies. A Detachment may never benefit from more than one Rite of War unless specifically stated otherwise. A Legiones Astartes army may include no more than one model with Master of the Legion for every full 1,000 points in the army. Where permitted by its army list entry, a Master of the Legion may select a Legion Command Squad as a retinue; if equipped with Terminator Armour, an appropriate Terminator Command Squad may be selected instead. The Master of the Legion and its Command Squad occupy a single HQ selection."""

PRIMARCH="""A model with this special rule has Independent Character, Eternal Warrior, Fear, Fearless, Adamantium Will, Fleet, It Will Not Die and Master of the Legion. A Primarch automatically passes Fear tests caused by another Primarch. A Primarch also possesses the named Legiones Astartes special rule corresponding to his own Legion."""

def ensure_container(p,tag):
    x=p.find(C(tag))
    if x is None: x=ET.SubElement(p,C(tag))
    return x

def ensure_rule(e,name,text,id_hint):
    rs=ensure_container(e,"rules")
    r=next((x for x in rs.findall(C("rule")) if (x.get("name") or "").lower()==name.lower()),None)
    if r is None:
        r=ET.SubElement(rs,C("rule"),{"id":id_hint,"name":name,"hidden":"false"})
    else:
        r.set("hidden","false")
    d=r.find(C("description"))
    if d is None: d=ET.SubElement(r,C("description"))
    d.text=text
    return r

def simple_generic(d):
    dl=d.strip().lower()
    return bool(re.match(r"^(?:this|the)\s+(?:unit|model|vehicle|squad)\s+(?:has|gains|possesses)\b",dl)
                or "uses the normal prohammer" in dl
                or re.match(r"^the squad gains the .+ special rule\.?$",dl))

# Standalone ProHammer reference rules: replace the placeholder with the actual rule.
replaced=0
expanded=0
for r in root.iter(C("rule")):
    n=(r.get("name") or "").strip()
    d=(r.findtext(C("description")) or "").strip()
    key=n
    if key=="Scout": key="Scouts"
    if key.lower()=="slow and purposeful": key="Slow and Purposeful"
    if key in USR and simple_generic(d):
        r.find(C("description")).text=USR[key]
        replaced+=1
        continue
    if n=="Deep Strike" and simple_generic(d):
        r.find(C("description")).text=DEEP_STRIKE
        replaced+=1
        continue
    if n.startswith("Feel No Pain") and simple_generic(d):
        val="4+" if "4+" in n else "5+"
        r.find(C("description")).text=f"Feel No Pain ({val}): after a model fails its normal saving throw, roll a D6; on {val} the Wound is ignored. Feel No Pain may not be used where the applicable ProHammer edition restriction prevents it."
        replaced+=1
        continue
    if n.startswith("Preferred Enemy (") and simple_generic(d):
        target=n[n.find("(")+1:n.rfind(")")]
        r.find(C("description")).text=f"Preferred Enemy ({target}): the unit may re-roll failed hits in close combat against {target}."
        replaced+=1
        continue

# Custom short rules that grant a ProHammer rule should explain the referenced rule too.
# This covers Veteran Tactics / Cult Arcana style entries without overwriting their own rule.
grant_aliases={**USR,"Scout":USR["Scouts"]}
for r in root.iter(C("rule")):
    dnode=r.find(C("description"))
    if dnode is None or not (dnode.text or "").strip(): continue
    d=dnode.text.strip()
    if len(d)>420: continue
    additions=[]
    low=d.lower()
    for nm,txt in grant_aliases.items():
        if nm.lower() in low and txt[:35].lower() not in low:
            # only expand when text clearly grants/has/refers to the named rule
            if re.search(rf"\b(has|gains?|possesses|with)\b[^.\n]*\b{re.escape(nm.lower())}\b",low) or "as defined in prohammer" in low or "normal prohammer" in low:
                additions.append(f"{nm}: {txt}")
    if "deep strike" in low and ("gains" in low or "has deep strike" in low) and "determine target location" not in low:
        additions.append("Deep Strike: "+DEEP_STRIKE)
    if additions:
        # de-duplicate preserving order
        seen=[]; uniq=[]
        for a in additions:
            if a not in seen: seen.append(a); uniq.append(a)
        dnode.text=d+"\n\n"+"\n".join(uniq)
        expanded+=1

# ------------------------------------------------------------------
# Sons of Horus source-accurate special rules.
# ------------------------------------------------------------------
byid={e.get("id"):e for e in root.iter() if e.get("id")}
soh_base=LEGIONES+"\n\nAnd They Shall Know No Fear: "+USR["And They Shall Know No Fear"]

def patch_id(id_,rules):
    e=byid.get(id_)
    if e is None: raise RuntimeError("Missing expected Sons of Horus entry "+id_)
    for j,(name,text) in enumerate(rules):
        ensure_rule(e,name,text,f"r34-{id_}-{j}")
    return e

patch_id("r41-unit-xvi-0-justaerin-terminator-squad",[
 ("Legiones Astartes (Sons of Horus)",soh_base),
 ("Chosen of the Warmaster","A Sons of Horus Praetor, Ezekyle Abaddon or Horus Lupercal may select one Justaerin Terminator Squad as a retinue. If selected as a retinue, the squad does not occupy a separate Elites choice.")
])
patch_id("r41-unit-xvi-1-reaver-attack-squad",[
 ("Legiones Astartes (Sons of Horus)",soh_base),
 ("Furious Charge",USR["Furious Charge"])
])
patch_id("r41-unit-xvi-2-chieftain-squad",[
 ("Legiones Astartes (Sons of Horus)",soh_base),
 ("Stubborn",USR["Stubborn"]),
 ("Cthonian Retinue","One Chieftain Squad may be selected as the retinue of a Sons of Horus Praetor or appropriate named Sons of Horus Independent Character. The squad does not occupy a separate Elites choice. The Character and Chieftain Squad count as a single HQ selection.")
])
patch_id("r41-unit-xvi-3-luperci-pack",[
 ("Legiones Astartes (Sons of Horus)",soh_base),
 ("Daemon",USR["Daemon"]),
 ("Fearless",USR["Fearless"]),
 ("Bulky",USR["Bulky"]),
 ("Furious Charge",USR["Furious Charge"]),
 ("Damned","A Luperci Pack may never count as a Scoring Unit. No Independent Character may join a Luperci Pack unless that Character has the Daemon special rule."),
 ("Daemonic Talons","Daemonic Talons are Rending Weapons.\n\nRending: "+USR["Rending"])
])

# Named characters and Primarchs.
patch_id("r41-unit-xvi-4-ezekyle-abaddon-first-captain",[
 ("Legiones Astartes (Sons of Horus)",soh_base),("Independent Character",INDEPENDENT_CHARACTER),
 ("Master of the Legion",MASTER_OF_LEGION),("First Captain","Ezekyle Abaddon is First Captain of the Sons of Horus and may use the retinue and Justaerin rules in his entry.")
])
patch_id("r41-unit-xvi-5-horus-aximand-little-horus",[
 ("Legiones Astartes (Sons of Horus)",soh_base),("Independent Character",INDEPENDENT_CHARACTER),("Master of the Legion",MASTER_OF_LEGION)
])
patch_id("r41-unit-xvi-6-garviel-loken",[
 ("Legiones Astartes (Sons of Horus)",soh_base),("Independent Character",INDEPENDENT_CHARACTER)
])
patch_id("r41-unit-xvi-8-tybalt-marr-the-either",[
 ("Legiones Astartes (Sons of Horus)",soh_base),("Independent Character",INDEPENDENT_CHARACTER),("Master of the Legion",MASTER_OF_LEGION)
])
patch_id("r41-unit-xvi-9-vheren-ashurhaddon",[
 ("Legiones Astartes (Sons of Horus)",soh_base),("Independent Character",INDEPENDENT_CHARACTER),("Master of the Legion",MASTER_OF_LEGION),("Furious Charge",USR["Furious Charge"])
])

for pid in ["r41-unit-xvi-12-xvi-horus-lupercal-the-warmaster","r41-unit-xvi-13-xvi-horus-ascended-the-warmaster"]:
    patch_id(pid,[
      ("Primarch",PRIMARCH),
      ("Legiones Astartes (Sons of Horus)",soh_base),
      ("Independent Character",INDEPENDENT_CHARACTER),
      ("Eternal Warrior",USR["Eternal Warrior"]),("Fear",USR["Fear"]),("Fearless",USR["Fearless"]),
      ("Adamantium Will",USR["Adamantium Will"]),("Fleet",USR["Fleet"]),("It Will Not Die",USR["It Will Not Die"]),
      ("Master of the Legion",MASTER_OF_LEGION)
    ])

# Maloghurst, Kibre and Torgaddon are selected as squad replacements/upgrades.
# Apply their source rules to every actual selectable character instance, not just the hidden source root.
selected_character_instances=0
for e in root.iter(C("selectionEntry")):
    n=(e.get("name") or "").lower()
    if "maloghurst" in n:
        ensure_rule(e,"Legiones Astartes (Sons of Horus)",soh_base,f"r34-{e.get('id')}-legiones")
        ensure_rule(e,"Broken Body",'Reduce the following movement made by Maloghurst\'s unit by 1\", to a minimum of 1\": Normal Movement, Advance movement, Charge movement, Fall Back movement and Consolidation movement. In addition, Maloghurst\'s unit may not Pursue a retreating enemy.',f"r34-{e.get('id')}-broken")
        selected_character_instances+=1
    if "falkus kibre" in n:
        ensure_rule(e,"Legiones Astartes (Sons of Horus)",soh_base,f"r34-{e.get('id')}-legiones")
        ensure_rule(e,"Justaerin Primus","While Falkus Kibre remains alive, his Justaerin Terminator Squad has Fearless. In addition, the squad may purchase the Furious Charge Veteran Skill for +4 points per model.\n\nFearless: "+USR["Fearless"]+"\nFurious Charge: "+USR["Furious Charge"],f"r34-{e.get('id')}-primus")
        selected_character_instances+=1
    if "tarik torgaddon" in n:
        ensure_rule(e,"Legiones Astartes (Sons of Horus)",soh_base,f"r34-{e.get('id')}-legiones")
        ensure_rule(e,"Stubborn",USR["Stubborn"],f"r34-{e.get('id')}-stubborn")
        selected_character_instances+=1

# ------------------------------------------------------------------
# Display-name cleanup.
# 1) Primarch entries never show Legion numerals.
# 2) Character names use normal title-style capitalization.
# ------------------------------------------------------------------
roman_prefix=re.compile(r"^(?:I|II|III|IV|V|VI|VII|VIII|IX|X|XI|XII|XIII|XIV|XV|XVI|XVII|XVIII|XIX|XX)\s*[—-]\s*",re.I)
small={"The","Of","And","The","First","Second"} # titles remain title case except 'the/of/and' handled below

def normal_case(s):
    s=roman_prefix.sub("",s.strip())
    # Python title handles apostrophes acceptably for these names; restore known abbreviations.
    t=s.lower().title()
    t=re.sub(r"\bThe\b","the",t)
    t=re.sub(r"\bOf\b","of",t)
    t=re.sub(r"\bAnd\b","and",t)
    # First word should be capitalised if it was 'the'.
    if t.startswith("the "): t="The "+t[4:]
    # preserve common project spellings
    fixes={
      "T'Kar":"T'Kar","T'Kell":"T'Kell","Rhy'Tan":"Rhy'tan","Khârn":"Khârn",
      "Qin Xa":"Qin Xa","Aximand, “Little Horus”":"Aximand, “Little Horus”",
    }
    for a,b in fixes.items(): t=t.replace(a,b)
    return t

character_keywords=("squad","pack","cohort","cabal","guard","terminator","veteran","seekers","raptor","brethren","destroyer","company","battery","squadron")
name_changes=[]
for e in root.iter(C("selectionEntry")):
    n=(e.get("name") or "").strip()
    if not n: continue
    letters="".join(ch for ch in n if ch.isalpha())
    if len(letters)<4: continue
    upperish=letters.upper()==letters
    pref=bool(roman_prefix.match(n))
    cats=[c.get("targetId") for c in e.findall(f"./{C('categoryLinks')}/{C('categoryLink')}")]
    is_hq_low=any(c in ("cat-hq","cat-low") for c in cats)
    explicit_soh=e.get("id") in {
      "r41-unit-xvi-4-ezekyle-abaddon-first-captain","r41-unit-xvi-5-horus-aximand-little-horus",
      "r41-unit-xvi-6-garviel-loken","r41-unit-xvi-7-maloghurst-the-twisted","r41-unit-xvi-8-tybalt-marr-the-either",
      "r41-unit-xvi-9-vheren-ashurhaddon","r41-unit-xvi-10-falkus-kibre","r41-unit-xvi-11-tarik-torgaddon",
      "r41-unit-xvi-12-xvi-horus-lupercal-the-warmaster","r41-unit-xvi-13-xvi-horus-ascended-the-warmaster"
    }
    named_style=("," in n or " THE " in n or " PRIMARCH " in n or "FIRST CAPTAIN" in n or "WARMASTER" in n)
    if pref or explicit_soh or (upperish and is_hq_low and not any(k in n.lower() for k in character_keywords)) or (upperish and named_style and not any(k in n.lower() for k in character_keywords)):
        nn=normal_case(n)
        if nn!=n:
            e.set("name",nn); name_changes.append((n,nn))

# Ensure all Primarch display entries/clones have no numeral prefix even if not all-uppercase.
primarch_prefix_removed=0
for e in root.iter(C("selectionEntry")):
    n=e.get("name") or ""
    if roman_prefix.match(n):
        nn=roman_prefix.sub("",n)
        e.set("name",nn)
        primarch_prefix_removed+=1

# R34 revision and canonical index.
root.set("revision","34")
tree.write(CAT,encoding="utf-8",xml_declaration=True)

IDX_NS="http://www.battlescribe.net/schema/dataIndexSchema"
ET.register_namespace("",IDX_NS)
it=ET.parse(IDX); ir=it.getroot()
for x in ir.iter(f"{{{IDX_NS}}}dataIndexEntry"):
    if x.get("filePath")=="Legiones Astartes.cat": x.set("dataRevision","34")
it.write(IDX,encoding="utf-8",xml_declaration=True)

# ------------------------------------------------------------------
# Validation
# ------------------------------------------------------------------
checkroot=ET.parse(CAT).getroot()
checks=[]
def ck(label,ok):
    checks.append((label,bool(ok)))
    if not ok: raise RuntimeError("R34 validation failed: "+label)

ck("Catalogue revision 34",checkroot.get("revision")=="34")
idx=IDX.read_text(encoding="utf-8")
ck("Index revision 34",'filePath="Legiones Astartes.cat"' in idx and 'dataRevision="34"' in idx)
ck("Index remains canonical","ns0:" not in idx and "xmlns:ns0" not in idx)

# Known generic placeholders must be gone.
bad=[]
for r in checkroot.iter(C("rule")):
    n=(r.get("name") or "").strip()
    d=(r.findtext(C("description")) or "").strip().lower()
    if n in {"Furious Charge","Counter-Attack","Fleet","Infiltrate","Stubborn","Scout","Move Through Cover","Acute Senses","Adamantium Will","Eternal Warrior","Fear","Stealth","Crusader"}:
        if simple_generic(d): bad.append((n,d))
ck("Known ProHammer reference placeholders removed",not bad)

# SoH special-rule presence.
ids={x.get("id"):x for x in checkroot.iter() if x.get("id")}
expected={
"r41-unit-xvi-0-justaerin-terminator-squad":["Legiones Astartes (Sons of Horus)","Chosen of the Warmaster"],
"r41-unit-xvi-1-reaver-attack-squad":["Legiones Astartes (Sons of Horus)","Furious Charge"],
"r41-unit-xvi-2-chieftain-squad":["Legiones Astartes (Sons of Horus)","Stubborn","Cthonian Retinue"],
"r41-unit-xvi-3-luperci-pack":["Legiones Astartes (Sons of Horus)","Daemon","Fearless","Bulky","Furious Charge","Damned"],
"r41-unit-xvi-9-vheren-ashurhaddon":["Legiones Astartes (Sons of Horus)","Independent Character","Master of the Legion","Furious Charge"],
"r41-unit-xvi-12-xvi-horus-lupercal-the-warmaster":["Primarch","Legiones Astartes (Sons of Horus)"],
"r41-unit-xvi-13-xvi-horus-ascended-the-warmaster":["Primarch","Legiones Astartes (Sons of Horus)"],
}
for i,names in expected.items():
    e=ids[i]
    rnames={r.get("name") for r in e.findall(f"./{C('rules')}/{C('rule')}") if r.get("hidden")!="true"}
    ck(i+" source special rules",all(n in rnames for n in names))

# No Primarch selection name starts with a Legion numeral.
primarch_bad=[]
for e in checkroot.iter(C("selectionEntry")):
    n=e.get("name") or ""
    if roman_prefix.match(n) and any(x in n.lower() for x in ["horus","magnus","angron","mortarion","fulgrim","perturabo","jaghatai","sanguinius","ferrus","guilliman","lorgar","vulkan","corax","alpharius"]):
        primarch_bad.append(n)
ck("Primarch Legion numerals removed",not primarch_bad)

lines=[
"Live R34 — ProHammer rule text, Sons of Horus rules and display names",
"Input CAT=33 -> target CAT=34",
"",
"CHANGES:",
f"- Replaced {replaced} generic standalone rule-reference descriptions with actual ProHammer rule text.",
f"- Expanded {expanded} short custom rules that grant/reference a ProHammer universal rule.",
"- Restored source-listed Sons of Horus special rules to Justaerin, Reavers, Chieftains, Luperci, named characters and both Horus profiles.",
f"- Patched {selected_character_instances} selectable Maloghurst/Kibre/Torgaddon character instances with their source rules.",
f"- Normalised {len(name_changes)} character/Primarch display names from all-caps presentation.",
f"- Removed Legion numeral prefixes from {primarch_prefix_removed} additional Primarch display entries/clones.",
"- Bumped catalogue/index to revision 34.",
"",
"VALIDATION:"
]
lines += [f'- {"PASS" if ok else "FAIL"}: {label}' for label,ok in checks]
lines += ["","NAME CHANGES:"]+[f"- {a} -> {b}" for a,b in name_changes]
OUT.write_text("\n".join(lines)+"\n",encoding="utf-8")
print(OUT.read_text())
