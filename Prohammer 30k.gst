<?xml version='1.0' encoding='utf-8'?>
<gameSystem xmlns="http://www.battlescribe.net/schema/gameSystemSchema" id="sys-6f3a-91d2-b47c-5e08" name="Prohammer 30k Live" revision="13" battleScribeVersion="2.03" authorName="Prohammer 30k Project" type="gameSystem">
  <comment>Horus Heresy army lists adapted for use with ProHammer Classic.</comment>
  <readme>Core system skeleton for Prohammer 30k. Contains points, core profile types, battlefield roles, mandatory Army Configuration and the standard Force Organisation Chart.</readme>
  <costTypes>
    <costType id="pts" name="Points" defaultCostLimit="-1" hidden="false" />
  </costTypes>
  <profileTypes>
    <profileType id="prof-model" name="Model">
      <characteristicTypes>
        <characteristicType id="model-ws" name="WS" />
        <characteristicType id="model-bs" name="BS" />
        <characteristicType id="model-s" name="S" />
        <characteristicType id="model-t" name="T" />
        <characteristicType id="model-w" name="W" />
        <characteristicType id="model-i" name="I" />
        <characteristicType id="model-a" name="A" />
        <characteristicType id="model-ld" name="Ld" />
        <characteristicType id="model-sv" name="Sv" />
      </characteristicTypes>
    </profileType>
    <profileType id="prof-ranged" name="Ranged Weapon">
      <characteristicTypes>
        <characteristicType id="ranged-range" name="Range" />
        <characteristicType id="ranged-s" name="S" />
        <characteristicType id="ranged-ap" name="AP" />
        <characteristicType id="ranged-type" name="Type" />
      </characteristicTypes>
    </profileType>
    <profileType id="prof-vehicle" name="Vehicle">
      <characteristicTypes>
        <characteristicType id="vehicle-bs" name="BS" />
        <characteristicType id="vehicle-front" name="Front" />
        <characteristicType id="vehicle-side" name="Side" />
        <characteristicType id="vehicle-rear" name="Rear" />
        <characteristicType id="vehicle-sp" name="SP" />
      </characteristicTypes>
    </profileType>
    <profileType id="prof-walker" name="Walker">
      <characteristicTypes>
        <characteristicType id="walker-ws" name="WS" />
        <characteristicType id="walker-bs" name="BS" />
        <characteristicType id="walker-s" name="S" />
        <characteristicType id="walker-front" name="Front" />
        <characteristicType id="walker-side" name="Side" />
        <characteristicType id="walker-rear" name="Rear" />
        <characteristicType id="walker-i" name="I" />
        <characteristicType id="walker-a" name="A" />
      </characteristicTypes>
    </profileType>
  </profileTypes>
  <categoryEntries>
    <categoryEntry id="cat-hq" name="HQ" hidden="false" />
    <categoryEntry id="cat-troops" name="Troops" hidden="false" />
    <categoryEntry id="cat-elites" name="Elites" hidden="false" />
    <categoryEntry id="cat-fast" name="Fast Attack" hidden="false" />
    <categoryEntry id="cat-heavy" name="Heavy Support" hidden="false" />
    <categoryEntry id="cat-transport" name="Dedicated Transport" hidden="false" />
    <categoryEntry id="cat-low" name="Lords of War" hidden="false" />
    <categoryEntry id="cat-config" name="Configuration" hidden="false" />
    <categoryEntry id="cat-aero" name="Aeronautica Imperialis" hidden="false" />
    <categoryEntry id="cat-retinue" name="Retinue" hidden="false" />
    <categoryEntry id="cat-dg-mobile" name="Death Guard Mobile Support Limit" hidden="true" />
    <categoryEntry id="cat-auxiliary" name="Auxiliary" hidden="false" />
    <categoryEntry id="cat-alpha-reward" name="Rewards of Treachery Limit" hidden="true" />
    <categoryEntry id="r47-cat-wb-favour" name="Word Bearers Favour of the Pantheon Limit" hidden="true" />
    <categoryEntry id="r63-sw-cat-grey-slayer" name="Space Wolves Grey Slayer Requirement" hidden="true" />
    <categoryEntry id="r64-if-cat-stone-comp" name="Stone Gauntlet Compulsory Troops" hidden="true" />
    <categoryEntry id="r64-if-cat-templar-comp" name="Templar Assault Compulsory Troops" hidden="true" />
    <categoryEntry id="r64-if-cat-templar-limit" name="Templar Brethren 0-1" hidden="true" />
    <categoryEntry id="r64-if-cat-tarantula-limit" name="Tarantula Batteries 0-2" hidden="true" />
    <categoryEntry id="r66-if-cat-stone-shield-ic" name="Stone Gauntlet — Shield-bearing Independent Character" hidden="true" />
    <categoryEntry id="r66-if-cat-hammer-warlord" name="Hammerfall — Warlord with Teleportation Transponders" hidden="true" />
    <categoryEntry id="r66-if-cat-templar-warlord" name="Templar Assault — Warlord with qualifying melee weapon" hidden="true" />
    <categoryEntry id="r71-nl-cat-terror-assault-comp" name="Terror Assault compulsory Terror formation" hidden="true" />
    <categoryEntry id="r71-nl-cat-horror-comp" name="Horror Cult compulsory Night Raptor" hidden="true" />
    <categoryEntry id="r74-ba-cat-revelation-comp" name="Day of Revelation — compulsory Assault/Veteran Troops" hidden="true" />
    <categoryEntry id="r74-ba-cat-sorrows-comp" name="Day of Sorrows — compulsory Tactical/Assault/Breacher Troops" hidden="true" />
    <categoryEntry id="r75-ba-cat-rev-warlord-jump" name="Day of Revelation — Warlord with Jump Pack" hidden="true" />
    <categoryEntry id="r79-ih-bitter-comp" name="Company of Bitter Iron — compulsory Medusan Immortal" hidden="true" />
    <categoryEntry id="r80-ih-bitter-comp" name="Company of Bitter Iron — compulsory Medusan Immortal" hidden="true" />
    <categoryEntry id="r80-ih-head-nonforge-consul" name="Head of the Gorgon — non-Forge-Lord Consuls" hidden="true" />
    <categoryEntry id="r81-ih-nonforge-consul" name="Head of the Gorgon — non-Forge Consul" hidden="true" />
    <categoryEntry id="r81-ih-bitter-comp" name="Company of Bitter Iron — compulsory Immortal" hidden="true" />
  <categoryEntry id="r18-ts-cat-brotherhood" name="Thousand Sons Psychic Brotherhood" hidden="true" /><categoryEntry id="r18-ts-cat-sekhmet-limit" name="Thousand Sons Sekhmet 0-1" hidden="true" /><categoryEntry id="r18-final-cat-sekhmet-01" name="Sekhmet Cabal 0-1" hidden="true" /><categoryEntry id="r18-final-cat-khenetai-01" name="Khenetai Cabal 0-1" hidden="true" /><categoryEntry id="r18-final-cat-ammitara-01" name="Ammitara Cabal 0-1" hidden="true" /><categoryEntry id="r18-final-cat-magnus-form" name="Magnus form 0-1" hidden="true" /><categoryEntry id="r19-ts-cat-rite-limit" name="Thousand Sons Rite of War 0-1" hidden="true" /><categoryEntry id="r36-soh-black-master-signals" name="Black Reaving — Master of Signals requirement" hidden="true" /><categoryEntry id="r36-soh-black-reaver-comp" name="Black Reaving — compulsory Reaver requirement" hidden="true" /><categoryEntry id="r36-soh-long-compulsory-troops" name="Long March — compulsory Troops excluding Terminators" hidden="true" /><categoryEntry id="r37-wb-dark-apostle-req" name="Word Bearers — Dark Shepherd" hidden="true" /><categoryEntry id="r37-wb-diabolist-req" name="Word Bearers — Diabolist" hidden="true" /><categoryEntry id="r37-wb-favour-limit" name="Word Bearers — Favour of the Pantheon" hidden="true" /><categoryEntry id="r40-sal-mantle-limit" name="Salamanders Mantle limit" hidden="true" /><categoryEntry id="r40-sal-awakening-chaplain" name="Awakening Fire — Chaplain" hidden="true" /><categoryEntry id="r40-sal-covenant-support" name="Covenant of Fire — Fast/Heavy choices" hidden="true" /><categoryEntry id="r40-sal-awakening-jump" name="Awakening Fire — Jump Infantry" hidden="true" /><categoryEntry id="r40-sal-awakening-jetbike" name="Awakening Fire — Jetbike" hidden="true" /><categoryEntry id="r40-sal-awakening-skimmer" name="Awakening Fire — Skimmer" hidden="true" /><categoryEntry id="r40-sal-awakening-flyer" name="Awakening Fire — Flyer" hidden="true" /><categoryEntry id="r40-sal-nomus-dread-hq" name="Nomus — Keeper of the Keys" hidden="true" /><categoryEntry id="r40-sal-covenant-compulsory" name="Covenant of Fire — compulsory Troops" hidden="true" /><categoryEntry id="r41-iron-halo-army-limit" name="Iron Halo — army-wide limit" hidden="true" /><categoryEntry id="r42-sal-firedrake-limit" name="Salamanders — Firedrake Terminator Squad limit" hidden="true" /><categoryEntry id="r42-sal-compulsory-troops" name="Salamanders — compulsory-capable Troops" hidden="true" /><categoryEntry id="r43-rg-heavy-count" name="Raven Guard — Heavy Support count" hidden="true" /><categoryEntry id="r43-rg-decap-heavy" name="Decapitation Strike — Heavy Support" hidden="true" /><categoryEntry id="r43-rg-decap-consul" name="Decapitation Strike — Consul" hidden="true" /><categoryEntry id="r43-rg-dark-fury-limit" name="Raven Guard — Dark Fury limit" hidden="true" /><categoryEntry id="r43-rg-deliverer-limit" name="Raven Guard — Deliverer limit" hidden="true" /><categoryEntry id="r43-rg-raptor-limit" name="Raven Guard — Raptor limit" hidden="true" /><categoryEntry id="r43-rg-compulsory-troops" name="Raven Guard — compulsory-capable Troops" hidden="true" /><categoryEntry id="r43-rg-sharrowkyn-limit" name="Raven Guard — Sharrowkyn limit" hidden="true" /><categoryEntry id="r45-al-headhunter-limit" name="Alpha Legion — Headhunter limit" hidden="true" /><categoryEntry id="r45-al-lernaean-limit" name="Alpha Legion — Lernaean limit" hidden="true" /><categoryEntry id="r45-al-coils-consul" name="Coils — non-Vigilator Consuls" hidden="true" /><categoryEntry id="r45-al-coils-compulsory" name="Coils — compulsory-capable Troops" hidden="true" /><categoryEntry id="r45-al-headhunter-compulsory" name="Headhunter Leviathal — compulsory Headhunters" hidden="true" /></categoryEntries>
  <forceEntries>
    <forceEntry id="force-standard" name="Standard Age of Darkness Detachment" hidden="false">
      <categoryLinks>
        <categoryLink id="fl-config" name="Configuration" hidden="false" targetId="cat-config">
          <constraints>
            <constraint id="fl-config-min" field="selections" scope="parent" value="1" percentValue="false" shared="true" includeChildSelections="false" includeChildForces="false" type="min" />
            <constraint id="fl-config-max" field="selections" scope="parent" value="1" percentValue="false" shared="true" includeChildSelections="false" includeChildForces="false" type="max" />
          </constraints>
        </categoryLink>
        <categoryLink id="fl-hq" name="HQ" hidden="false" targetId="cat-hq">
          <constraints>
            <constraint id="fl-hq-min" field="selections" scope="parent" value="1" percentValue="false" shared="true" includeChildSelections="false" includeChildForces="false" type="min" />
            <constraint id="fl-hq-max" field="selections" scope="parent" value="2" percentValue="false" shared="true" includeChildSelections="false" includeChildForces="false" type="max" />
          </constraints>
          <modifiers>
            <modifier id="r45-um-hq-max" type="set" value="4" field="fl-hq-max">
              <conditions>
                <condition type="atLeast" value="1" field="selections" scope="roster" childId="legion-xiii" shared="true" includeChildSelections="true" includeChildForces="false" />
              </conditions>
            </modifier>
            <modifier id="r45-um-logos-hq-min" type="set" value="2" field="fl-hq-min">
              <conditions>
                <condition type="atLeast" value="1" field="selections" scope="roster" childId="r25-rite-xiii-0-the-logos-lectora" shared="true" includeChildSelections="true" includeChildForces="false" />
              </conditions>
            </modifier>
            <modifier id="r62-sw-hq-min-reset" type="set" value="0" field="fl-hq-min">
              <conditionGroups>
                <conditionGroup type="and">
                  <conditions>
                    <condition type="atLeast" value="1" field="selections" scope="roster" childId="legion-vi" shared="true" includeChildSelections="true" includeChildForces="false" />
                    <condition type="greaterThan" value="0" field="limit::pts" scope="roster" childId="model" shared="true" includeChildSelections="true" includeChildForces="false" />
                  </conditions>
                </conditionGroup>
              </conditionGroups>
            </modifier>
            <modifier id="r62-sw-hq-max-reset" type="set" value="0" field="fl-hq-max">
              <conditionGroups>
                <conditionGroup type="and">
                  <conditions>
                    <condition type="atLeast" value="1" field="selections" scope="roster" childId="legion-vi" shared="true" includeChildSelections="true" includeChildForces="false" />
                    <condition type="greaterThan" value="0" field="limit::pts" scope="roster" childId="model" shared="true" includeChildSelections="true" includeChildForces="false" />
                  </conditions>
                </conditionGroup>
              </conditionGroups>
            </modifier>
            <modifier id="r62-sw-hq-min-scale" type="increment" value="1" field="fl-hq-min">
              <repeats>
                <repeat field="limit::pts" scope="roster" value="750" shared="true" childId="model" includeChildSelections="true" includeChildForces="false" repeats="1" roundUp="true" />
              </repeats>
              <conditionGroups>
                <conditionGroup type="and">
                  <conditions>
                    <condition type="atLeast" value="1" field="selections" scope="roster" childId="legion-vi" shared="true" includeChildSelections="true" includeChildForces="false" />
                    <condition type="greaterThan" value="0" field="limit::pts" scope="roster" childId="model" shared="true" includeChildSelections="true" includeChildForces="false" />
                  </conditions>
                </conditionGroup>
              </conditionGroups>
            </modifier>
            <modifier id="r62-sw-hq-max-scale" type="increment" value="1" field="fl-hq-max">
              <repeats>
                <repeat field="limit::pts" scope="roster" value="750" shared="true" childId="model" includeChildSelections="true" includeChildForces="false" repeats="1" roundUp="true" />
              </repeats>
              <conditionGroups>
                <conditionGroup type="and">
                  <conditions>
                    <condition type="atLeast" value="1" field="selections" scope="roster" childId="legion-vi" shared="true" includeChildSelections="true" includeChildForces="false" />
                    <condition type="greaterThan" value="0" field="limit::pts" scope="roster" childId="model" shared="true" includeChildSelections="true" includeChildForces="false" />
                  </conditions>
                </conditionGroup>
              </conditionGroups>
            </modifier>
            <modifier id="r62-sw-hq-unlimited-max" type="set" value="4" field="fl-hq-max">
              <conditionGroups>
                <conditionGroup type="and">
                  <conditions>
                    <condition type="atLeast" value="1" field="selections" scope="roster" childId="legion-vi" shared="true" includeChildSelections="true" includeChildForces="false" />
                    <condition type="lessThan" value="0" field="limit::pts" scope="roster" childId="model" shared="true" includeChildSelections="true" includeChildForces="false" />
                  </conditions>
                </conditionGroup>
              </conditionGroups>
            </modifier>
            <modifier id="r71-nl-mawdrym-hq-min" type="set" value="2" field="fl-hq-min">
              <conditionGroups>
                <conditionGroup type="and">
                  <conditions>
                    <condition type="atLeast" value="1" field="selections" scope="roster" childId="r41-unit-viii-8-flaymaster-mawdrym-llansahai" shared="true" includeChildSelections="true" includeChildForces="false" />
                    <condition type="lessThan" value="1" field="selections" scope="roster" childId="da22-rite-primarchs-chosen" shared="true" includeChildSelections="true" includeChildForces="false" />
                  </conditions>
                </conditionGroup>
              </conditionGroups>
            </modifier>
          <modifier id="r18-ts-fl-hq-max" type="set" field="fl-hq-max" value="3"><conditions><condition type="atLeast" value="1" field="selections" scope="roster" childId="legion-xv" shared="true" includeChildSelections="true" includeChildForces="false" /></conditions></modifier></modifiers>
        </categoryLink>
        <categoryLink id="fl-troops" name="Troops" hidden="false" targetId="cat-troops">
          <constraints>
            <constraint id="fl-troops-min" field="selections" scope="parent" value="2" percentValue="false" shared="true" includeChildSelections="false" includeChildForces="false" type="min" />
            <constraint id="fl-troops-max" field="selections" scope="parent" value="6" percentValue="false" shared="true" includeChildSelections="false" includeChildForces="false" type="max" />
          </constraints>
          <modifiers>
            <modifier id="r45-um-logos-troops-min" type="set" value="3" field="fl-troops-min">
              <conditions>
                <condition type="atLeast" value="1" field="selections" scope="roster" childId="r25-rite-xiii-0-the-logos-lectora" shared="true" includeChildSelections="true" includeChildForces="false" />
              </conditions>
            </modifier>
            <modifier id="r46-al-coils-troops-min" type="set" value="3" field="fl-troops-min">
              <conditions>
                <condition type="atLeast" value="1" field="selections" scope="roster" childId="r25-rite-xx-0-the-coils-of-the-hydra" shared="true" includeChildSelections="true" includeChildForces="false" />
              </conditions>
            </modifier>
          </modifiers>
        </categoryLink>
        <categoryLink id="fl-elites" name="Elites" hidden="false" targetId="cat-elites">
          <constraints>
            <constraint id="fl-elites-max" field="selections" scope="parent" value="3" percentValue="false" shared="true" includeChildSelections="false" includeChildForces="false" type="max" />
          </constraints>
        <modifiers><modifier id="r18-ts-fl-elites-max" type="set" field="fl-elites-max" value="4"><conditions><condition type="atLeast" value="1" field="selections" scope="roster" childId="legion-xv" shared="true" includeChildSelections="true" includeChildForces="false" /></conditions></modifier></modifiers></categoryLink>
        <categoryLink id="fl-fast" name="Fast Attack" hidden="false" targetId="cat-fast">
          <constraints>
            <constraint id="fl-fast-max" field="selections" scope="parent" value="3" percentValue="false" shared="true" includeChildSelections="false" includeChildForces="false" type="max" />
          <constraint id="r36-soh-black-fast-min" type="min" value="0" field="selections" scope="parent" shared="true" includeChildSelections="false" includeChildForces="false" /></constraints>
          <modifiers>
            <modifier id="r43-iw-fast-max" type="set" value="1" field="fl-fast-max">
              <conditions>
                <condition type="atLeast" value="1" field="selections" scope="roster" childId="legion-iv" shared="true" includeChildSelections="true" includeChildForces="false" />
              </conditions>
            </modifier>
            <modifier id="r64-if-stone-fast-max" type="set" value="1" field="fl-fast-max">
              <conditions>
                <condition type="atLeast" value="1" field="selections" scope="roster" childId="r25-rite-vii-0-the-stone-gauntlet" shared="true" includeChildSelections="true" includeChildForces="false" />
              </conditions>
            </modifier>
            <modifier id="r64-if-templar-fast-max" type="set" value="1" field="fl-fast-max">
              <conditions>
                <condition type="atLeast" value="1" field="selections" scope="roster" childId="r25-rite-vii-2-templar-assault" shared="true" includeChildSelections="true" includeChildForces="false" />
              </conditions>
            </modifier>
            <modifier id="r73-nl-fl-fast" type="set" value="4" field="fl-fast-max">
              <conditions>
                <condition type="atLeast" value="1" field="selections" scope="roster" childId="legion-viii" shared="true" includeChildSelections="true" includeChildForces="false" />
              </conditions>
            </modifier>
            <modifier id="r80-ih-head-fast-max" type="set" value="1" field="fl-fast-max">
              <conditions>
                <condition type="atLeast" value="1" field="selections" scope="roster" childId="r25-rite-x-0-the-head-of-the-gorgon" shared="true" includeChildSelections="true" includeChildForces="false" />
              </conditions>
            </modifier>
            <modifier id="r81-ih-head-fast-max" type="set" value="1" field="fl-fast-max">
              <conditions>
                <condition type="atLeast" value="1" field="selections" scope="roster" childId="r25-rite-x-0-the-head-of-the-gorgon" shared="true" includeChildSelections="true" includeChildForces="false" />
              </conditions>
            </modifier>
          <modifier id="r18-ts-fl-fast-max" type="set" field="fl-fast-max" value="2"><conditions><condition type="atLeast" value="1" field="selections" scope="roster" childId="legion-xv" shared="true" includeChildSelections="true" includeChildForces="false" /></conditions></modifier><modifier id="r18-ts-fellowships-fast-max" type="set" field="fl-fast-max" value="1"><conditions><condition type="atLeast" value="1" field="selections" scope="roster" childId="r25-rite-xv-2-the-fellowships-of-prospero" shared="true" includeChildSelections="true" includeChildForces="false" /></conditions></modifier><modifier id="r36-soh-black-fast-per-heavy" type="increment" field="r36-soh-black-fast-min" value="1"><repeats><repeat field="selections" scope="force" value="1" shared="true" childId="cat-heavy" includeChildSelections="false" includeChildForces="false" repeats="1" roundUp="false" /></repeats><conditions><condition type="atLeast" value="1" field="selections" scope="roster" childId="r25-rite-xvi-1-the-black-reaving" shared="true" includeChildSelections="true" includeChildForces="false" /></conditions></modifier></modifiers>
        </categoryLink>
        <categoryLink id="fl-heavy" name="Heavy Support" hidden="false" targetId="cat-heavy">
          <constraints>
            <constraint id="fl-heavy-max" field="selections" scope="parent" value="3" percentValue="false" shared="true" includeChildSelections="false" includeChildForces="false" type="max" />
          <constraint id="r37-wb-dark-heavy-max" type="max" value="3" field="selections" scope="parent" shared="true" includeChildSelections="false" includeChildForces="false" /></constraints>
          <modifiers>
            <modifier id="r43-ec-maru-heavy-max" type="set" value="2" field="fl-heavy-max">
              <conditions>
                <condition type="atLeast" value="1" field="selections" scope="roster" childId="r25-rite-iii-0-the-maru-skara" shared="true" includeChildSelections="true" includeChildForces="false" />
              </conditions>
            </modifier>
            <modifier id="r43-iw-heavy-max" type="set" value="4" field="fl-heavy-max">
              <conditions>
                <condition type="atLeast" value="1" field="selections" scope="roster" childId="legion-iv" shared="true" includeChildSelections="true" includeChildForces="false" />
              </conditions>
            </modifier>
            <modifier id="r43-sw-pale-heavy-max" type="set" value="1" field="fl-heavy-max">
              <conditions>
                <condition type="atLeast" value="1" field="selections" scope="roster" childId="r25-rite-vi-0-the-pale-hunters" shared="true" includeChildSelections="true" includeChildForces="false" />
              </conditions>
            </modifier>
            <modifier id="r46-wb-dark-brethren-heavy-max" type="set" value="1" field="fl-heavy-max">
              <conditions>
                <condition type="atLeast" value="1" field="selections" scope="roster" childId="r25-rite-xvii-0-the-dark-brethren" shared="true" includeChildSelections="true" includeChildForces="false" />
              </conditions>
            </modifier>
            <modifier id="r46-rg-decap-heavy-max" type="set" value="1" field="fl-heavy-max">
              <conditions>
                <condition type="atLeast" value="1" field="selections" scope="roster" childId="r25-rite-xix-0-decapitation-strike" shared="true" includeChildSelections="true" includeChildForces="false" />
              </conditions>
            </modifier>
            <modifier id="r52-ec-maru-heavy-max" type="set" value="2" field="fl-heavy-max">
              <conditions>
                <condition type="atLeast" value="1" field="selections" scope="roster" childId="r25-rite-iii-0-the-maru-skara" shared="true" includeChildSelections="true" includeChildForces="false" />
              </conditions>
            </modifier>
            <modifier id="r73-nl-fl-heavy" type="set" value="1" field="fl-heavy-max">
              <conditions>
                <condition type="atLeast" value="1" field="selections" scope="roster" childId="legion-viii" shared="true" includeChildSelections="true" includeChildForces="false" />
              </conditions>
            </modifier>
            <modifier id="r74-ba-rev-heavy-max" type="set" value="1" field="fl-heavy-max">
              <conditions>
                <condition type="atLeast" value="1" field="selections" scope="roster" childId="r25-rite-ix-0-the-day-of-revelation" shared="true" includeChildSelections="true" includeChildForces="false" />
              </conditions>
            </modifier>
            <modifier id="r75-ba-rev-heavy-max" type="set" value="1" field="fl-heavy-max">
              <conditions>
                <condition type="atLeast" value="1" field="selections" scope="roster" childId="r25-rite-ix-0-the-day-of-revelation" shared="true" includeChildSelections="true" includeChildForces="false" />
              </conditions>
            </modifier>
          <modifier id="r86-we-berserker-heavy-max" type="set" value="1" field="fl-heavy-max"><conditions><condition type="atLeast" value="1" field="selections" scope="roster" childId="r25-rite-xii-0-berserker-assault" shared="true" includeChildSelections="true" includeChildForces="false" /></conditions></modifier><modifier id="r37-wb-dark-heavy-set1" type="set" field="r37-wb-dark-heavy-max" value="1"><conditions><condition type="atLeast" value="1" field="selections" scope="roster" childId="r25-rite-xvii-0-the-dark-brethren" shared="true" includeChildSelections="true" includeChildForces="false" /></conditions></modifier></modifiers>
        </categoryLink>
        <categoryLink id="fl-transport" name="Dedicated Transport" hidden="false" targetId="cat-transport" />
        <categoryLink id="fl-low" name="Lords of War" hidden="false" targetId="cat-low">
          <constraints>
            <constraint id="fl-low-max" field="selections" scope="parent" value="1" percentValue="false" shared="true" includeChildSelections="false" includeChildForces="false" type="max" />
          </constraints>
        </categoryLink>
        <categoryLink id="fl-retinue" name="Retinue" hidden="false" targetId="cat-retinue" />
        <categoryLink id="fl-dg-mobile" name="Death Guard Mobile Support Limit" targetId="cat-dg-mobile" hidden="true">
          <constraints>
            <constraint id="r45-dg-mobile-max" field="selections" scope="parent" value="1" type="max" shared="true" includeChildSelections="false" includeChildForces="false" />
          </constraints>
        </categoryLink>
        <categoryLink id="fl-auxiliary" name="Auxiliary" targetId="cat-auxiliary" hidden="false" />
        <categoryLink id="fl-alpha-reward" name="Rewards of Treachery Limit" targetId="cat-alpha-reward" hidden="true">
          <constraints>
            <constraint id="r46-al-reward-max" field="selections" scope="parent" value="1" type="max" shared="true" includeChildSelections="false" includeChildForces="false" />
          </constraints>
        </categoryLink>
        <categoryLink id="r47-fl-wb-favour" name="Word Bearers Favour Limit" targetId="r47-cat-wb-favour" hidden="true">
          <constraints>
            <constraint id="r47-wb-favour-roster-max" field="selections" scope="roster" value="1" type="max" shared="true" includeChildSelections="true" includeChildForces="false" />
          </constraints>
        </categoryLink>
        <categoryLink id="r63-sw-fl-grey-slayer" name="Grey Slayer Requirement" hidden="true" targetId="r63-sw-cat-grey-slayer">
          <constraints>
            <constraint id="r63-sw-grey-slayer-min" type="min" value="0" field="selections" scope="parent" shared="true" includeChildSelections="false" includeChildForces="false" />
          </constraints>
          <modifiers>
            <modifier id="r63-sw-grey-slayer-min-mod" type="set" value="1" field="r63-sw-grey-slayer-min">
              <conditions>
                <condition type="atLeast" value="1" field="selections" scope="roster" childId="r25-rite-vi-1-the-bloodied-claws" shared="true" includeChildSelections="true" includeChildForces="false" />
              </conditions>
            </modifier>
          </modifiers>
        </categoryLink>
        <categoryLink id="r64-if-fl-r64-if-cat-stone-comp" name="Stone Gauntlet Compulsory Troops" hidden="true" targetId="r64-if-cat-stone-comp">
          <constraints>
            <constraint id="r64-if-r64-if-cat-stone-comp-min" type="min" value="0" field="selections" scope="parent" shared="true" includeChildSelections="false" includeChildForces="false" />
          </constraints>
          <modifiers>
            <modifier id="r64-if-r64-if-cat-stone-comp-min-mod" type="set" value="2" field="r64-if-r64-if-cat-stone-comp-min">
              <conditions>
                <condition type="atLeast" value="1" field="selections" scope="roster" childId="r25-rite-vii-0-the-stone-gauntlet" shared="true" includeChildSelections="true" includeChildForces="false" />
              </conditions>
            </modifier>
          </modifiers>
        </categoryLink>
        <categoryLink id="r64-if-fl-r64-if-cat-templar-comp" name="Templar Assault Compulsory Troops" hidden="true" targetId="r64-if-cat-templar-comp">
          <constraints>
            <constraint id="r64-if-r64-if-cat-templar-comp-min" type="min" value="0" field="selections" scope="parent" shared="true" includeChildSelections="false" includeChildForces="false" />
          </constraints>
          <modifiers>
            <modifier id="r64-if-r64-if-cat-templar-comp-min-mod" type="set" value="2" field="r64-if-r64-if-cat-templar-comp-min">
              <conditions>
                <condition type="atLeast" value="1" field="selections" scope="roster" childId="r25-rite-vii-2-templar-assault" shared="true" includeChildSelections="true" includeChildForces="false" />
              </conditions>
            </modifier>
          </modifiers>
        </categoryLink>
        <categoryLink id="r64-if-fl-r64-if-cat-templar-limit" name="Templar Brethren 0-1" hidden="true" targetId="r64-if-cat-templar-limit">
          <constraints>
            <constraint id="r64-if-r64-if-cat-templar-limit-max" type="max" value="99" field="selections" scope="parent" shared="true" includeChildSelections="false" includeChildForces="false" />
          </constraints>
          <modifiers>
            <modifier id="r64-if-r64-if-cat-templar-limit-max-mod" type="set" value="1" field="r64-if-r64-if-cat-templar-limit-max">
              <conditionGroups>
                <conditionGroup type="and">
                  <conditions>
                    <condition type="atLeast" value="1" field="selections" scope="roster" childId="legion-vii" shared="true" includeChildSelections="true" includeChildForces="false" />
                    <condition type="lessThan" value="1" field="selections" scope="roster" childId="r25-rite-vii-2-templar-assault" shared="true" includeChildSelections="true" includeChildForces="false" />
                  </conditions>
                </conditionGroup>
              </conditionGroups>
            </modifier>
          </modifiers>
        </categoryLink>
        <categoryLink id="r64-if-fl-r64-if-cat-tarantula-limit" name="Tarantula Batteries 0-2" hidden="true" targetId="r64-if-cat-tarantula-limit">
          <constraints>
            <constraint id="r64-if-r64-if-cat-tarantula-limit-max" type="max" value="99" field="selections" scope="parent" shared="true" includeChildSelections="false" includeChildForces="false" />
          </constraints>
          <modifiers>
            <modifier id="r64-if-r64-if-cat-tarantula-limit-max-mod" type="set" value="2" field="r64-if-r64-if-cat-tarantula-limit-max">
              <conditions>
                <condition type="atLeast" value="1" field="selections" scope="roster" childId="legion-vii" shared="true" includeChildSelections="true" includeChildForces="false" />
              </conditions>
            </modifier>
          </modifiers>
        </categoryLink>
        <categoryLink id="r66-if-fl-r66-if-cat-stone-shield-ic" name="Stone Gauntlet — Shield-bearing Independent Character" hidden="true" targetId="r66-if-cat-stone-shield-ic">
          <constraints>
            <constraint id="r66-if-fl-r66-if-cat-stone-shield-ic-min" type="min" value="0" field="selections" scope="parent" shared="true" includeChildSelections="true" includeChildForces="false" />
          </constraints>
          <modifiers>
            <modifier id="r66-if-fl-r66-if-cat-stone-shield-ic-min-mod" type="set" value="1" field="r66-if-fl-r66-if-cat-stone-shield-ic-min">
              <conditions>
                <condition type="atLeast" value="1" field="selections" scope="roster" childId="r25-rite-vii-0-the-stone-gauntlet" shared="true" includeChildSelections="true" includeChildForces="false" />
              </conditions>
            </modifier>
          </modifiers>
        </categoryLink>
        <categoryLink id="r66-if-fl-r66-if-cat-hammer-warlord" name="Hammerfall — Warlord with Teleportation Transponders" hidden="true" targetId="r66-if-cat-hammer-warlord">
          <constraints>
            <constraint id="r66-if-fl-r66-if-cat-hammer-warlord-min" type="min" value="0" field="selections" scope="parent" shared="true" includeChildSelections="true" includeChildForces="false" />
            <constraint id="r66-if-fl-r66-if-cat-hammer-warlord-max" type="max" value="99" field="selections" scope="parent" shared="true" includeChildSelections="true" includeChildForces="false" />
          </constraints>
          <modifiers>
            <modifier id="r66-if-fl-r66-if-cat-hammer-warlord-min-mod" type="set" value="1" field="r66-if-fl-r66-if-cat-hammer-warlord-min">
              <conditions>
                <condition type="atLeast" value="1" field="selections" scope="roster" childId="r25-rite-vii-1-hammerfall-strike-force" shared="true" includeChildSelections="true" includeChildForces="false" />
              </conditions>
            </modifier>
            <modifier id="r66-if-fl-r66-if-cat-hammer-warlord-max-mod" type="set" value="1" field="r66-if-fl-r66-if-cat-hammer-warlord-max">
              <conditions>
                <condition type="atLeast" value="1" field="selections" scope="roster" childId="r25-rite-vii-1-hammerfall-strike-force" shared="true" includeChildSelections="true" includeChildForces="false" />
              </conditions>
            </modifier>
          </modifiers>
        </categoryLink>
        <categoryLink id="r66-if-fl-r66-if-cat-templar-warlord" name="Templar Assault — Warlord with qualifying melee weapon" hidden="true" targetId="r66-if-cat-templar-warlord">
          <constraints>
            <constraint id="r66-if-fl-r66-if-cat-templar-warlord-min" type="min" value="0" field="selections" scope="parent" shared="true" includeChildSelections="true" includeChildForces="false" />
            <constraint id="r66-if-fl-r66-if-cat-templar-warlord-max" type="max" value="99" field="selections" scope="parent" shared="true" includeChildSelections="true" includeChildForces="false" />
          </constraints>
          <modifiers>
            <modifier id="r66-if-fl-r66-if-cat-templar-warlord-min-mod" type="set" value="1" field="r66-if-fl-r66-if-cat-templar-warlord-min">
              <conditions>
                <condition type="atLeast" value="1" field="selections" scope="roster" childId="r25-rite-vii-2-templar-assault" shared="true" includeChildSelections="true" includeChildForces="false" />
              </conditions>
            </modifier>
            <modifier id="r66-if-fl-r66-if-cat-templar-warlord-max-mod" type="set" value="1" field="r66-if-fl-r66-if-cat-templar-warlord-max">
              <conditions>
                <condition type="atLeast" value="1" field="selections" scope="roster" childId="r25-rite-vii-2-templar-assault" shared="true" includeChildSelections="true" includeChildForces="false" />
              </conditions>
            </modifier>
          </modifiers>
        </categoryLink>
        <categoryLink id="r71-nl-fl-r71-nl-cat-terror-assault-comp" name="Terror Assault compulsory Terror formation" hidden="true" targetId="r71-nl-cat-terror-assault-comp">
          <constraints>
            <constraint id="r71-nl-r71-nl-cat-terror-assault-comp-min" type="min" value="0" field="selections" scope="parent" shared="true" includeChildSelections="false" includeChildForces="false" />
          </constraints>
          <modifiers>
            <modifier id="r71-nl-r71-nl-cat-terror-assault-comp-min-mod" type="set" value="1" field="r71-nl-r71-nl-cat-terror-assault-comp-min">
              <conditions>
                <condition type="atLeast" value="1" field="selections" scope="roster" childId="r25-rite-viii-0-terror-assault" shared="true" includeChildSelections="true" includeChildForces="false" />
              </conditions>
            </modifier>
          </modifiers>
        </categoryLink>
        <categoryLink id="r71-nl-fl-r71-nl-cat-horror-comp" name="Horror Cult compulsory Night Raptor" hidden="true" targetId="r71-nl-cat-horror-comp">
          <constraints>
            <constraint id="r71-nl-r71-nl-cat-horror-comp-min" type="min" value="0" field="selections" scope="parent" shared="true" includeChildSelections="false" includeChildForces="false" />
          </constraints>
          <modifiers>
            <modifier id="r71-nl-r71-nl-cat-horror-comp-min-mod" type="set" value="1" field="r71-nl-r71-nl-cat-horror-comp-min">
              <conditions>
                <condition type="atLeast" value="1" field="selections" scope="roster" childId="r25-rite-viii-1-horror-cult" shared="true" includeChildSelections="true" includeChildForces="false" />
              </conditions>
            </modifier>
          </modifiers>
        </categoryLink>
        <categoryLink id="r74-ba-fl-r74-ba-cat-revelation-comp" name="Day of Revelation — compulsory Assault/Veteran Troops" hidden="true" targetId="r74-ba-cat-revelation-comp">
          <constraints>
            <constraint id="r74-ba-r74-ba-cat-revelation-comp-min" type="min" value="0" field="selections" scope="parent" shared="true" includeChildSelections="false" includeChildForces="false" />
          </constraints>
          <modifiers>
            <modifier id="r74-ba-r74-ba-cat-revelation-comp-min-set" type="set" value="2" field="r74-ba-r74-ba-cat-revelation-comp-min">
              <conditions>
                <condition type="atLeast" value="1" field="selections" scope="roster" childId="r25-rite-ix-0-the-day-of-revelation" shared="true" includeChildSelections="true" includeChildForces="false" />
              </conditions>
            </modifier>
            <modifier id="r75-ba-r74-ba-cat-revelation-comp-set" type="set" value="2" field="r74-ba-r74-ba-cat-revelation-comp-min">
              <conditions>
                <condition type="atLeast" value="1" field="selections" scope="roster" childId="r25-rite-ix-0-the-day-of-revelation" shared="true" includeChildSelections="true" includeChildForces="false" />
              </conditions>
            </modifier>
          </modifiers>
        </categoryLink>
        <categoryLink id="r74-ba-fl-r74-ba-cat-sorrows-comp" name="Day of Sorrows — compulsory Tactical/Assault/Breacher Troops" hidden="true" targetId="r74-ba-cat-sorrows-comp">
          <constraints>
            <constraint id="r74-ba-r74-ba-cat-sorrows-comp-min" type="min" value="0" field="selections" scope="parent" shared="true" includeChildSelections="false" includeChildForces="false" />
          </constraints>
          <modifiers>
            <modifier id="r74-ba-r74-ba-cat-sorrows-comp-min-set" type="set" value="2" field="r74-ba-r74-ba-cat-sorrows-comp-min">
              <conditions>
                <condition type="atLeast" value="1" field="selections" scope="roster" childId="r25-rite-ix-1-the-day-of-sorrows" shared="true" includeChildSelections="true" includeChildForces="false" />
              </conditions>
            </modifier>
            <modifier id="r75-ba-r74-ba-cat-sorrows-comp-set" type="set" value="2" field="r74-ba-r74-ba-cat-sorrows-comp-min">
              <conditions>
                <condition type="atLeast" value="1" field="selections" scope="roster" childId="r25-rite-ix-1-the-day-of-sorrows" shared="true" includeChildSelections="true" includeChildForces="false" />
              </conditions>
            </modifier>
          </modifiers>
        </categoryLink>
        <categoryLink id="r75-ba-fl-r75-ba-cat-rev-warlord-jump" name="Day of Revelation — Warlord with Jump Pack" hidden="true" targetId="r75-ba-cat-rev-warlord-jump">
          <constraints>
            <constraint id="r75-ba-r75-ba-cat-rev-warlord-jump-min" type="min" value="0" field="selections" scope="parent" shared="true" includeChildSelections="true" includeChildForces="false" />
          </constraints>
          <modifiers>
            <modifier id="r75-ba-r75-ba-cat-rev-warlord-jump-set" type="set" value="1" field="r75-ba-r75-ba-cat-rev-warlord-jump-min">
              <conditions>
                <condition type="atLeast" value="1" field="selections" scope="roster" childId="r25-rite-ix-0-the-day-of-revelation" shared="true" includeChildSelections="true" includeChildForces="false" />
              </conditions>
            </modifier>
          </modifiers>
        </categoryLink>
        <categoryLink id="r79-ih-bitter-comp-link" name="Company of Bitter Iron — compulsory Medusan Immortal" hidden="true" targetId="r79-ih-bitter-comp">
          <constraints>
            <constraint id="r79-ih-bitter-comp-min" type="min" value="0" field="selections" scope="parent" shared="true" includeChildSelections="false" includeChildForces="false" />
          </constraints>
          <modifiers>
            <modifier id="r79-ih-bitter-comp-set" type="set" value="1" field="r79-ih-bitter-comp-min">
              <conditions>
                <condition type="atLeast" value="1" field="selections" scope="roster" childId="r25-rite-x-1-company-of-bitter-iron" shared="true" includeChildSelections="true" includeChildForces="false" />
              </conditions>
            </modifier>
          </modifiers>
        </categoryLink>
        <categoryLink id="r80-ih-bitter-comp-link" name="Company of Bitter Iron — compulsory Medusan Immortal" hidden="true" targetId="r80-ih-bitter-comp">
          <constraints>
            <constraint id="r80-ih-bitter-comp-min" type="min" value="0" field="selections" scope="parent" shared="true" includeChildSelections="true" includeChildForces="false" />
          </constraints>
          <modifiers>
            <modifier id="r80-ih-bitter-comp-set" type="set" value="1" field="r80-ih-bitter-comp-min">
              <conditions>
                <condition type="atLeast" value="1" field="selections" scope="roster" childId="r25-rite-x-1-company-of-bitter-iron" shared="true" includeChildSelections="true" includeChildForces="false" />
              </conditions>
            </modifier>
          </modifiers>
        </categoryLink>
        <categoryLink id="r80-ih-head-consul-link" name="Head of the Gorgon — non-Forge-Lord Consuls" hidden="true" targetId="r80-ih-head-nonforge-consul">
          <constraints>
            <constraint id="r80-ih-head-consul-max" type="max" value="99" field="selections" scope="parent" shared="true" includeChildSelections="true" includeChildForces="false" />
          </constraints>
          <modifiers>
            <modifier id="r80-ih-head-consul-set" type="set" value="1" field="r80-ih-head-consul-max">
              <conditions>
                <condition type="atLeast" value="1" field="selections" scope="roster" childId="r25-rite-x-0-the-head-of-the-gorgon" shared="true" includeChildSelections="true" includeChildForces="false" />
              </conditions>
            </modifier>
          </modifiers>
        </categoryLink>
        <categoryLink id="r81-ih-head-consul-limit" name="Head of the Gorgon — non-Forge Consul" hidden="true" targetId="r81-ih-nonforge-consul">
          <constraints>
            <constraint id="r81-ih-head-consul-max" type="max" value="99" field="selections" scope="parent" shared="true" includeChildSelections="true" includeChildForces="false" />
          </constraints>
          <modifiers>
            <modifier id="r81-ih-head-consul-set" type="set" value="1" field="r81-ih-head-consul-max">
              <conditions>
                <condition type="atLeast" value="1" field="selections" scope="roster" childId="r25-rite-x-0-the-head-of-the-gorgon" shared="true" includeChildSelections="true" includeChildForces="false" />
              </conditions>
            </modifier>
          </modifiers>
        </categoryLink>
        <categoryLink id="r81-ih-bitter-comp-link" name="Company of Bitter Iron — compulsory Immortal" hidden="true" targetId="r81-ih-bitter-comp">
          <constraints>
            <constraint id="r81-ih-bitter-comp-min" type="min" value="0" field="selections" scope="parent" shared="true" includeChildSelections="true" includeChildForces="false" />
          </constraints>
          <modifiers>
            <modifier id="r81-ih-bitter-comp-set" type="set" value="1" field="r81-ih-bitter-comp-min">
              <conditions>
                <condition type="atLeast" value="1" field="selections" scope="roster" childId="r25-rite-x-1-company-of-bitter-iron" shared="true" includeChildSelections="true" includeChildForces="false" />
              </conditions>
            </modifier>
          </modifiers>
        </categoryLink>
      <categoryLink id="r18-ts-brotherhood-limit" name="Fellowships — Psychic Brotherhoods" hidden="true" targetId="r18-ts-cat-brotherhood"><constraints><constraint id="r18-ts-brotherhood-min" type="min" value="0" field="selections" scope="parent" shared="true" includeChildSelections="true" includeChildForces="false" /></constraints><modifiers><modifier id="r18-ts-brotherhood-min-fellowships" type="set" field="r18-ts-brotherhood-min" value="2"><conditions><condition type="atLeast" value="1" field="selections" scope="roster" childId="r25-rite-xv-2-the-fellowships-of-prospero" shared="true" includeChildSelections="true" includeChildForces="false" /></conditions></modifier></modifiers></categoryLink><categoryLink id="r18-ts-sekhmet-limit" name="Sekhmet 0-1" hidden="true" targetId="r18-ts-cat-sekhmet-limit"><constraints><constraint id="r18-ts-sekhmet-limit-max" type="max" value="1" field="selections" scope="parent" shared="true" includeChildSelections="true" includeChildForces="false" /></constraints><modifiers>
        <modifier id="r26-guard-sekhmet-limit-unlimited" type="set" value="99" field="r18-ts-sekhmet-limit-max">
          <conditions>
            <condition type="atLeast" value="1" field="selections" scope="roster" childId="r25-rite-xv-1-the-guard-of-the-crimson-king" shared="true" includeChildSelections="true" includeChildForces="false" />
          </conditions>
        </modifier>
      </modifiers></categoryLink><categoryLink id="r18-final-cat-sekhmet-01-force" name="Sekhmet Cabal 0-1" hidden="true" targetId="r18-final-cat-sekhmet-01"><constraints><constraint id="r18-final-cat-sekhmet-01-max" type="max" value="1" field="selections" scope="parent" shared="true" includeChildSelections="true" includeChildForces="false" /></constraints><modifiers>
        <modifier id="r26-guard-sekhmet-final-unlimited" type="set" value="99" field="r18-final-cat-sekhmet-01-max">
          <conditions>
            <condition type="atLeast" value="1" field="selections" scope="roster" childId="r25-rite-xv-1-the-guard-of-the-crimson-king" shared="true" includeChildSelections="true" includeChildForces="false" />
          </conditions>
        </modifier>
      </modifiers></categoryLink><categoryLink id="r18-final-cat-khenetai-01-force" name="Khenetai Cabal 0-1" hidden="true" targetId="r18-final-cat-khenetai-01"><constraints><constraint id="r18-final-cat-khenetai-01-max" type="max" value="1" field="selections" scope="parent" shared="true" includeChildSelections="true" includeChildForces="false" /></constraints></categoryLink><categoryLink id="r18-final-cat-ammitara-01-force" name="Ammitara Cabal 0-1" hidden="true" targetId="r18-final-cat-ammitara-01"><constraints><constraint id="r18-final-cat-ammitara-01-max" type="max" value="1" field="selections" scope="parent" shared="true" includeChildSelections="true" includeChildForces="false" /></constraints></categoryLink><categoryLink id="r18-final-magnus-form-force" name="Magnus form 0-1" hidden="true" targetId="r18-final-cat-magnus-form"><constraints><constraint id="r18-final-magnus-form-max" type="max" value="1" field="selections" scope="parent" shared="true" includeChildSelections="true" includeChildForces="false" /></constraints></categoryLink><categoryLink id="r19-ts-rite-limit" name="Thousand Sons Rite of War 0-1" hidden="true" targetId="r19-ts-cat-rite-limit"><constraints><constraint id="r19-ts-rite-limit-max" type="max" value="1" field="selections" scope="parent" shared="true" includeChildSelections="true" includeChildForces="false" /></constraints></categoryLink><categoryLink id="r36-soh-black-mos-force" name="Black Reaving — Master of Signals" hidden="true" targetId="r36-soh-black-master-signals"><modifiers><modifier id="r36-soh-black-mos-min-set" type="set" field="r36-soh-black-mos-min" value="1"><conditions><condition type="atLeast" value="1" field="selections" scope="roster" childId="r25-rite-xvi-1-the-black-reaving" shared="true" includeChildSelections="true" includeChildForces="false" /></conditions></modifier></modifiers><constraints><constraint id="r36-soh-black-mos-min" type="min" value="0" field="selections" scope="parent" shared="true" includeChildSelections="true" includeChildForces="false" /></constraints></categoryLink><categoryLink id="r36-soh-black-reaver-force" name="Black Reaving — compulsory Reaver" hidden="true" targetId="r36-soh-black-reaver-comp"><modifiers><modifier id="r36-soh-black-reaver-min-set" type="set" field="r36-soh-black-reaver-min" value="1"><conditions><condition type="atLeast" value="1" field="selections" scope="roster" childId="r25-rite-xvi-1-the-black-reaving" shared="true" includeChildSelections="true" includeChildForces="false" /></conditions></modifier></modifiers><constraints><constraint id="r36-soh-black-reaver-min" type="min" value="0" field="selections" scope="parent" shared="true" includeChildSelections="true" includeChildForces="false" /></constraints></categoryLink><categoryLink id="r36-soh-long-comp-force" name="Long March — compulsory Troops" hidden="true" targetId="r36-soh-long-compulsory-troops"><modifiers><modifier id="r36-soh-long-comp-min-set" type="set" field="r36-soh-long-comp-min" value="2"><conditions><condition type="atLeast" value="1" field="selections" scope="roster" childId="r25-rite-xvi-0-the-long-march" shared="true" includeChildSelections="true" includeChildForces="false" /></conditions></modifier></modifiers><constraints><constraint id="r36-soh-long-comp-min" type="min" value="0" field="selections" scope="parent" shared="true" includeChildSelections="true" includeChildForces="false" /></constraints></categoryLink><categoryLink id="r37-wb-dark-ap-force" name="Word Bearers — Dark Shepherd" targetId="r37-wb-dark-apostle-req" hidden="true"><modifiers><modifier id="r37-wb-dark-ap-min-set" type="set" field="r37-wb-dark-ap-min" value="1"><conditions><condition type="atLeast" value="1" field="selections" scope="roster" childId="legion-xvii" shared="true" includeChildSelections="true" includeChildForces="false" /></conditions></modifier></modifiers><constraints><constraint id="r37-wb-dark-ap-min" type="min" value="0" field="selections" scope="parent" shared="true" includeChildSelections="true" includeChildForces="false" /></constraints></categoryLink><categoryLink id="r37-wb-favour-force" name="Word Bearers — Favour of the Pantheon" targetId="r37-wb-favour-limit" hidden="true"><constraints><constraint id="r37-wb-favour-max" type="max" value="1" field="selections" scope="parent" shared="true" includeChildSelections="true" includeChildForces="false" /></constraints></categoryLink><categoryLink id="r37-wb-diab-force" name="Word Bearers — Diabolist" targetId="r37-wb-diabolist-req" hidden="true"><modifiers><modifier id="r37-wb-diab-min-dark" type="set" field="r37-wb-diab-min" value="1"><conditions><condition type="atLeast" value="1" field="selections" scope="roster" childId="r25-rite-xvii-0-the-dark-brethren" shared="true" includeChildSelections="true" includeChildForces="false" /></conditions></modifier></modifiers><constraints><constraint id="r37-wb-diab-min" type="min" value="0" field="selections" scope="parent" shared="true" includeChildSelections="true" includeChildForces="false" /></constraints></categoryLink><categoryLink id="r40-sal-mantle-force" name="Salamanders Mantle limit" targetId="r40-sal-mantle-limit" hidden="true"><constraints><constraint id="r40-sal-mantle-max" type="max" value="1" field="selections" scope="parent" shared="true" includeChildSelections="true" includeChildForces="false" /></constraints></categoryLink><categoryLink id="r40-sal-chap-force" name="Awakening Fire — Chaplain" targetId="r40-sal-awakening-chaplain" hidden="true"><modifiers><modifier id="r40-sal-chap-set" type="set" field="r40-sal-chap-min" value="1"><conditions><condition type="atLeast" value="1" field="selections" scope="roster" childId="r25-rite-xviii-1-the-awakening-fire" shared="true" includeChildSelections="true" includeChildForces="false" /></conditions></modifier></modifiers><constraints><constraint id="r40-sal-chap-min" type="min" value="0" field="selections" scope="parent" shared="true" includeChildSelections="true" includeChildForces="false" /></constraints></categoryLink><categoryLink id="r40-sal-nomus-dread-force" name="Nomus — Keeper of the Keys" targetId="r40-sal-nomus-dread-hq" hidden="true"><constraints><constraint id="r40-sal-nomus-dread-max" type="max" value="1" field="selections" scope="parent" shared="true" includeChildSelections="true" includeChildForces="false" /></constraints></categoryLink><categoryLink id="r40-sal-cov-sup-force" name="Covenant of Fire — Fast/Heavy choices" targetId="r40-sal-covenant-support" hidden="true"><modifiers><modifier id="r40-sal-cov-sup-zero" type="set" field="r40-sal-cov-sup-max" value="0"><conditions><condition type="atLeast" value="1" field="selections" scope="roster" childId="r25-rite-xviii-0-the-covenant-of-fire" shared="true" includeChildSelections="true" includeChildForces="false" /></conditions></modifier><modifier id="r40-sal-cov-sup-per-troop" type="increment" field="r40-sal-cov-sup-max" value="1"><repeats><repeat field="selections" scope="force" value="1" shared="true" childId="cat-troops" includeChildSelections="false" includeChildForces="false" repeats="1" roundUp="false" /></repeats><conditions><condition type="atLeast" value="1" field="selections" scope="roster" childId="r25-rite-xviii-0-the-covenant-of-fire" shared="true" includeChildSelections="true" includeChildForces="false" /></conditions></modifier></modifiers><constraints><constraint id="r40-sal-cov-sup-max" type="max" value="99" field="selections" scope="parent" shared="true" includeChildSelections="true" includeChildForces="false" /></constraints></categoryLink><categoryLink id="r40-sal-awak-jump-infantry" name="Awakening Fire — Jump Infantry" targetId="r40-sal-awakening-jump" hidden="true"><modifiers><modifier id="r40-sal-awak-jump-infantry-set1" type="set" field="r40-sal-awak-jump-infantry-max" value="1"><conditions><condition type="atLeast" value="1" field="selections" scope="roster" childId="r25-rite-xviii-1-the-awakening-fire" shared="true" includeChildSelections="true" includeChildForces="false" /></conditions></modifier></modifiers><constraints><constraint id="r40-sal-awak-jump-infantry-max" type="max" value="99" field="selections" scope="parent" shared="true" includeChildSelections="true" includeChildForces="false" /></constraints></categoryLink><categoryLink id="r40-sal-awak-jetbike" name="Awakening Fire — Jetbike" targetId="r40-sal-awakening-jetbike" hidden="true"><modifiers><modifier id="r40-sal-awak-jetbike-set1" type="set" field="r40-sal-awak-jetbike-max" value="1"><conditions><condition type="atLeast" value="1" field="selections" scope="roster" childId="r25-rite-xviii-1-the-awakening-fire" shared="true" includeChildSelections="true" includeChildForces="false" /></conditions></modifier></modifiers><constraints><constraint id="r40-sal-awak-jetbike-max" type="max" value="99" field="selections" scope="parent" shared="true" includeChildSelections="true" includeChildForces="false" /></constraints></categoryLink><categoryLink id="r40-sal-awak-skimmer" name="Awakening Fire — Skimmer" targetId="r40-sal-awakening-skimmer" hidden="true"><modifiers><modifier id="r40-sal-awak-skimmer-set1" type="set" field="r40-sal-awak-skimmer-max" value="1"><conditions><condition type="atLeast" value="1" field="selections" scope="roster" childId="r25-rite-xviii-1-the-awakening-fire" shared="true" includeChildSelections="true" includeChildForces="false" /></conditions></modifier></modifiers><constraints><constraint id="r40-sal-awak-skimmer-max" type="max" value="99" field="selections" scope="parent" shared="true" includeChildSelections="true" includeChildForces="false" /></constraints></categoryLink><categoryLink id="r40-sal-awak-flyer" name="Awakening Fire — Flyer" targetId="r40-sal-awakening-flyer" hidden="true"><modifiers><modifier id="r40-sal-awak-flyer-set1" type="set" field="r40-sal-awak-flyer-max" value="1"><conditions><condition type="atLeast" value="1" field="selections" scope="roster" childId="r25-rite-xviii-1-the-awakening-fire" shared="true" includeChildSelections="true" includeChildForces="false" /></conditions></modifier></modifiers><constraints><constraint id="r40-sal-awak-flyer-max" type="max" value="99" field="selections" scope="parent" shared="true" includeChildSelections="true" includeChildForces="false" /></constraints></categoryLink><categoryLink id="r40-sal-covcomp-force" name="Covenant of Fire — compulsory Troops" targetId="r40-sal-covenant-compulsory" hidden="true"><modifiers><modifier id="r40-sal-covcomp-set" type="set" field="r40-sal-covcomp-min" value="2"><conditions><condition type="atLeast" value="1" field="selections" scope="roster" childId="r25-rite-xviii-0-the-covenant-of-fire" shared="true" includeChildSelections="true" includeChildForces="false" /></conditions></modifier></modifiers><constraints><constraint id="r40-sal-covcomp-min" type="min" value="0" field="selections" scope="parent" shared="true" includeChildSelections="true" includeChildForces="false" /></constraints></categoryLink><categoryLink id="r41-iron-halo-force" name="Iron Halo — army-wide limit" targetId="r41-iron-halo-army-limit" hidden="true"><constraints><constraint id="r41-iron-halo-max" type="max" value="1" field="selections" scope="parent" shared="true" includeChildSelections="true" includeChildForces="false" /></constraints></categoryLink><categoryLink id="r42-sal-firedrake-force" name="Salamanders — Firedrake Terminator Squad limit" targetId="r42-sal-firedrake-limit" hidden="true"><constraints><constraint id="r42-sal-firedrake-max" type="max" value="1" field="selections" scope="parent" shared="true" includeChildSelections="true" includeChildForces="false" /></constraints></categoryLink><categoryLink id="r42-sal-comp-force" name="Salamanders — compulsory-capable Troops" targetId="r42-sal-compulsory-troops" hidden="true"><modifiers><modifier id="r42-sal-comp-min2" type="set" field="r42-sal-comp-min" value="2"><conditions><condition type="atLeast" value="1" field="selections" scope="roster" childId="legion-xviii" shared="true" includeChildSelections="true" includeChildForces="false" /></conditions></modifier></modifiers><constraints><constraint id="r42-sal-comp-min" type="min" value="0" field="selections" scope="parent" shared="true" includeChildSelections="true" includeChildForces="false" /></constraints></categoryLink><categoryLink id="r43-rg-heavy-force" name="Raven Guard — Heavy Support count" targetId="r43-rg-heavy-count" hidden="true"><modifiers><modifier id="r43-rg-heavy-zero" type="set" field="r43-rg-heavy-max" value="0"><conditions><condition type="atLeast" value="1" field="selections" scope="roster" childId="legion-xix" shared="true" includeChildSelections="true" includeChildForces="false" /></conditions></modifier><modifier id="r43-rg-heavy-per-fast" type="increment" field="r43-rg-heavy-max" value="1"><repeats><repeat field="selections" scope="force" value="1" shared="true" childId="cat-fast" includeChildSelections="false" includeChildForces="false" repeats="1" roundUp="false" /></repeats><conditions><condition type="atLeast" value="1" field="selections" scope="roster" childId="legion-xix" shared="true" includeChildSelections="true" includeChildForces="false" /></conditions></modifier></modifiers><constraints><constraint id="r43-rg-heavy-max" type="max" value="99" field="selections" scope="parent" shared="true" includeChildSelections="true" includeChildForces="false" /></constraints></categoryLink><categoryLink id="r43-rg-decap-heavy-force" name="Decapitation Strike — Heavy Support" targetId="r43-rg-decap-heavy" hidden="true"><modifiers><modifier id="r43-rg-decap-heavy-one" type="set" field="r43-rg-decap-heavy-max" value="1"><conditions><condition type="atLeast" value="1" field="selections" scope="roster" childId="r25-rite-xix-0-decapitation-strike" shared="true" includeChildSelections="true" includeChildForces="false" /></conditions></modifier></modifiers><constraints><constraint id="r43-rg-decap-heavy-max" type="max" value="99" field="selections" scope="parent" shared="true" includeChildSelections="true" includeChildForces="false" /></constraints></categoryLink><categoryLink id="r43-rg-decap-consul-force" name="Decapitation Strike — Consul" targetId="r43-rg-decap-consul" hidden="true"><modifiers><modifier id="r43-rg-decap-consul-one" type="set" field="r43-rg-decap-consul-max" value="1"><conditions><condition type="atLeast" value="1" field="selections" scope="roster" childId="r25-rite-xix-0-decapitation-strike" shared="true" includeChildSelections="true" includeChildForces="false" /></conditions></modifier></modifiers><constraints><constraint id="r43-rg-decap-consul-max" type="max" value="99" field="selections" scope="parent" shared="true" includeChildSelections="true" includeChildForces="false" /></constraints></categoryLink><categoryLink id="r43-rg-del-force" name="Deliverer limit" targetId="r43-rg-deliverer-limit" hidden="true"><constraints><constraint id="r43-rg-del-force-max" type="max" value="1" field="selections" scope="parent" shared="true" includeChildSelections="true" includeChildForces="false" /></constraints></categoryLink><categoryLink id="r43-rg-rap-force" name="Raptor limit" targetId="r43-rg-raptor-limit" hidden="true"><constraints><constraint id="r43-rg-rap-force-max" type="max" value="1" field="selections" scope="parent" shared="true" includeChildSelections="true" includeChildForces="false" /></constraints></categoryLink><categoryLink id="r43-rg-shar-force" name="Sharrowkyn limit" targetId="r43-rg-sharrowkyn-limit" hidden="true"><constraints><constraint id="r43-rg-shar-force-max" type="max" value="1" field="selections" scope="parent" shared="true" includeChildSelections="true" includeChildForces="false" /></constraints></categoryLink><categoryLink id="r43-rg-df-force" name="Dark Fury limit" targetId="r43-rg-dark-fury-limit" hidden="true"><modifiers><modifier id="r43-rg-df-agapito" type="set" field="r43-rg-df-max" value="2"><conditions><condition type="atLeast" value="1" field="selections" scope="roster" childId="r43-rg-agapito-replacement" shared="true" includeChildSelections="true" includeChildForces="false" /></conditions></modifier></modifiers><constraints><constraint id="r43-rg-df-max" type="max" value="1" field="selections" scope="parent" shared="true" includeChildSelections="true" includeChildForces="false" /></constraints></categoryLink><categoryLink id="r43-rg-comp-force" name="Raven Guard — compulsory-capable Troops" targetId="r43-rg-compulsory-troops" hidden="true"><modifiers><modifier id="r43-rg-comp-two" type="set" field="r43-rg-comp-min" value="2"><conditions><condition type="atLeast" value="1" field="selections" scope="roster" childId="legion-xix" shared="true" includeChildSelections="true" includeChildForces="false" /></conditions></modifier></modifiers><constraints><constraint id="r43-rg-comp-min" type="min" value="0" field="selections" scope="parent" shared="true" includeChildSelections="true" includeChildForces="false" /></constraints></categoryLink><categoryLink id="r45-al-head-limit-force" name="Alpha Legion — Headhunter limit" targetId="r45-al-headhunter-limit" hidden="true"><modifiers><modifier id="r45-al-head-limit-rite" type="set" field="r45-al-head-limit-max" value="99"><conditions><condition type="atLeast" value="1" field="selections" scope="roster" childId="r25-rite-xx-1-headhunter-leviathal" shared="true" includeChildSelections="true" includeChildForces="false" /></conditions></modifier></modifiers><constraints><constraint id="r45-al-head-limit-max" type="max" value="1" field="selections" scope="parent" shared="true" includeChildSelections="true" includeChildForces="false" /></constraints></categoryLink><categoryLink id="r45-al-lern-limit-force" name="Alpha Legion — Lernaean limit" targetId="r45-al-lernaean-limit" hidden="true"><constraints><constraint id="r45-al-lern-limit-max" type="max" value="1" field="selections" scope="parent" shared="true" includeChildSelections="true" includeChildForces="false" /></constraints></categoryLink><categoryLink id="r45-al-reward-force" name="Rewards of Treachery Limit" targetId="cat-alpha-reward" hidden="true"><constraints><constraint id="r45-al-reward-max" type="max" value="1" field="selections" scope="parent" shared="true" includeChildSelections="true" includeChildForces="false" /></constraints></categoryLink><categoryLink id="r45-al-coils-cons-force" name="Coils — non-Vigilator Consuls" targetId="r45-al-coils-consul" hidden="true"><modifiers><modifier id="r45-al-coils-cons-one" type="set" field="r45-al-coils-cons-max" value="1"><conditions><condition type="atLeast" value="1" field="selections" scope="roster" childId="r25-rite-xx-0-the-coils-of-the-hydra" shared="true" includeChildSelections="true" includeChildForces="false" /></conditions></modifier></modifiers><constraints><constraint id="r45-al-coils-cons-max" type="max" value="99" field="selections" scope="parent" shared="true" includeChildSelections="true" includeChildForces="false" /></constraints></categoryLink><categoryLink id="r45-al-coils-troops-force" name="Coils — compulsory-capable Troops" targetId="r45-al-coils-compulsory" hidden="true"><modifiers><modifier id="r45-al-coils-troops-three" type="set" field="r45-al-coils-troops-min" value="3"><conditions><condition type="atLeast" value="1" field="selections" scope="roster" childId="r25-rite-xx-0-the-coils-of-the-hydra" shared="true" includeChildSelections="true" includeChildForces="false" /></conditions></modifier></modifiers><constraints><constraint id="r45-al-coils-troops-min" type="min" value="0" field="selections" scope="parent" shared="true" includeChildSelections="true" includeChildForces="false" /></constraints></categoryLink><categoryLink id="r45-al-head-comp-force" name="Headhunter Leviathal — compulsory Headhunters" targetId="r45-al-headhunter-compulsory" hidden="true"><modifiers><modifier id="r45-al-head-comp-two" type="set" field="r45-al-head-comp-min" value="2"><conditions><condition type="atLeast" value="1" field="selections" scope="roster" childId="r25-rite-xx-1-headhunter-leviathal" shared="true" includeChildSelections="true" includeChildForces="false" /></conditions></modifier></modifiers><constraints><constraint id="r45-al-head-comp-min" type="min" value="0" field="selections" scope="parent" shared="true" includeChildSelections="true" includeChildForces="false" /></constraints></categoryLink></categoryLinks>
    </forceEntry>
  </forceEntries>
</gameSystem>