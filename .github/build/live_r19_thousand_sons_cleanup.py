from pathlib import Path
from copy import deepcopy
import os, re
import xml.etree.ElementTree as ET

CAT=Path('Legiones Astartes.cat')
GST=Path('Prohammer 30k.gst')
IDX=Path('index.xml')
OUT=Path('inspection-r19-thousand-sons-cleanup.txt')
APPLY=os.environ.get('R19_APPLY','0')=='1'

CNS='http://www.battlescribe.net/schema/catalogueSchema'
GNS='http://www.battlescribe.net/schema/gameSystemSchema'
ET.register_namespace('',CNS); ET.register_namespace('',GNS)
C=lambda t:f'{{{CNS}}}{t}'
G=lambda t:f'{{{GNS}}}{t}'
ct=ET.parse(CAT); root=ct.getroot()
gt=ET.parse(GST); groot=gt.getroot()
if root.get('revision')!='18':
    raise RuntimeError(f'R19 expects live catalogue revision 18, got {root.get("revision")}')

def findid(r,i):
    return next((x for x in r.iter() if x.get('id')==i),None)

def ensure(p,tag,ns=C):
    x=p.find(ns(tag))
    if x is None: x=ET.SubElement(p,ns(tag))
    return x

def cond(typ,val,child,scope='root-entry',field='selections'):
    return {'type':typ,'value':str(val),'field':field,'scope':scope,'childId':child,
            'shared':'true','includeChildSelections':'true','includeChildForces':'false'}

def add_constraint(e,i,typ,val,scope='parent',field='selections',ns=C):
    cs=ensure(e,'constraints',ns)
    for x in list(cs):
        if x.get('id')==i: cs.remove(x)
    return ET.SubElement(cs,ns('constraint'),{
        'id':i,'type':typ,'value':str(val),'field':field,'scope':scope,
        'shared':'true','includeChildSelections':'true','includeChildForces':'false'})

def add_modifier(e,i,typ,field,value,conditions=None,groups=None,ns=C):
    ms=ensure(e,'modifiers',ns)
    for x in list(ms):
        if x.get('id')==i: ms.remove(x)
    m=ET.SubElement(ms,ns('modifier'),{'id':i,'type':typ,'field':field,'value':str(value)})
    if conditions:
        cs=ET.SubElement(m,ns('conditions'))
        for q in conditions: ET.SubElement(cs,ns('condition'),q)
    if groups:
        gs=ET.SubElement(m,ns('conditionGroups'))
        for gtyp,gg in groups:
            cg=ET.SubElement(gs,ns('conditionGroup'),{'type':gtyp})
            cs=ET.SubElement(cg,ns('conditions'))
            for q in gg: ET.SubElement(cs,ns('condition'),q)
    return m

def rule(host,i,name,text,hidden='false'):
    rs=ensure(host,'rules')
    for x in list(rs):
        if x.get('id')==i: rs.remove(x)
    r=ET.SubElement(rs,C('rule'),{'id':i,'name':name,'hidden':hidden})
    d=ET.SubElement(r,C('description')); d.text=text
    return r

def direct_groups(host):
    c=host.find(C('selectionEntryGroups'))
    return list(c) if c is not None else []

def direct_entries(host):
    c=host.find(C('selectionEntries'))
    return list(c) if c is not None else []

def prefix_clone(src,prefix):
    cl=deepcopy(src); mp={}
    for x in cl.iter():
        if x.get('id'): mp[x.get('id')]=prefix+x.get('id')
    for x in cl.iter():
        if x.get('id') in mp: x.set('id',mp[x.get('id')])
        if x.get('childId') in mp: x.set('childId',mp[x.get('childId')])
        if x.get('field') in mp: x.set('field',mp[x.get('field')])
    return cl

def strip_categories(e):
    for x in e.iter():
        c=x.find(C('categoryLinks'))
        if c is not None: x.remove(c)

def remove_group(host,gid):
    gs=host.find(C('selectionEntryGroups'))
    if gs is None: return False
    for x in list(gs):
        if x.get('id')==gid:
            gs.remove(x); return True
    return False

def remove_groups(host,gids):
    return sum(1 for g in gids if remove_group(host,g))

def parent_map():
    return {c:p for p in root.iter() for c in p}

def host_of_group(g):
    pm=parent_map()
    p=pm.get(g)
    return pm.get(p) if p is not None else None

def add_category_link(host,i,name,target,primary='false',hidden='false'):
    cs=ensure(host,'categoryLinks')
    for x in list(cs):
        if x.get('id')==i: cs.remove(x)
    return ET.SubElement(cs,C('categoryLink'),{
        'id':i,'name':name,'targetId':target,'primary':primary,'hidden':hidden})

def sanitize(s):
    return re.sub(r'[^A-Za-z0-9_-]+','-',s).strip('-').lower()

DISCIPLINES=['Biomancy','Divination','Pyromancy','Telekinesis','Telepathy']
CULT_TO_DISC={'Pavoni':'Biomancy','Raptora':'Telekinesis','Corvidae':'Divination','Athanaeans':'Telepathy','Pyrae':'Pyromancy'}

# Canonical power templates come from the current ProHammer Librarian pool.
psrc=findid(root,'r61-librarian-power1')
if psrc is None: raise RuntimeError('Missing canonical Librarian power pool')
pses=psrc.find(C('selectionEntries'))
POWER_TEMPLATES={d:[] for d in DISCIPLINES}
for e in list(pses) if pses is not None else []:
    n=e.get('name') or ''
    disc=next((d for d in DISCIPLINES if n.startswith(d+' —') or n.startswith(d+' -')),None)
    if disc:
        spell=n.split('—',1)[1].strip() if '—' in n else n.split('-',1)[1].strip()
        POWER_TEMPLATES[disc].append((spell,e))
if any(len(POWER_TEMPLATES[d])<1 for d in DISCIPLINES):
    raise RuntimeError('Canonical power pool is incomplete')

log=[]
interfaces=[]

def make_psychic_interface(host,prefix,title,allowed,
                           power_min,power_max,disc_min=1,disc_max=1,
                           requirements=None,dynamic=None,cult_gate=None):
    """Librarian-style UI: choose Discipline(s), then only powers from chosen disciplines are visible."""
    if host is None: raise RuntimeError('Missing host for '+prefix)
    requirements=requirements or []
    dynamic=dynamic or []
    allowed=[d for d in DISCIPLINES if d in allowed]
    gs=ensure(host,'selectionEntryGroups')
    # Idempotent.
    for gid in (prefix+'-disciplines',prefix+'-powers'):
        for x in list(gs):
            if x.get('id')==gid: gs.remove(x)

    dg=ET.SubElement(gs,C('selectionEntryGroup'),{'id':prefix+'-disciplines','name':title+' — Psychic Discipline(s)','hidden':'false'})
    dmin=add_constraint(dg,prefix+'-disc-min','min',0 if requirements else disc_min,'parent')
    dmax=add_constraint(dg,prefix+'-disc-max','max',disc_max,'parent')
    des=ET.SubElement(dg,C('selectionEntries'))
    dids={}
    for d in allowed:
        sid=prefix+'-disc-'+sanitize(d)
        s=ET.SubElement(des,C('selectionEntry'),{'id':sid,'name':d,'type':'upgrade','hidden':'false','import':'true'})
        add_constraint(s,sid+'-max','max',1,'parent')
        if cult_gate:
            cid=cult_gate.get(d)
            if cid:
                add_modifier(s,sid+'-cult','set','hidden','true',
                             conditions=[cond('lessThan',1,cid,'root-entry')])
        dids[d]=sid

    pg=ET.SubElement(gs,C('selectionEntryGroup'),{'id':prefix+'-powers','name':title+' — Psychic Powers','hidden':'false'})
    pmin=add_constraint(pg,prefix+'-power-min','min',0 if requirements else power_min,'parent')
    pmax=add_constraint(pg,prefix+'-power-max','max',power_max,'parent')
    pes=ET.SubElement(pg,C('selectionEntries'))
    spell_ids={}
    for d in allowed:
        for spell,templ in POWER_TEMPLATES[d]:
            cl=prefix_clone(templ,prefix+'-'+sanitize(d)+'-'+sanitize(spell)+'-')
            cl.set('id',prefix+'-power-'+sanitize(d)+'-'+sanitize(spell))
            cl.set('name',spell)
            cl.set('hidden','false')
            strip_categories(cl)
            # Source spell modifiers are not part of this UI; visibility depends only on chosen discipline.
            old=cl.find(C('modifiers'))
            if old is not None: cl.remove(old)
            # Ensure exactly one copy of each spell can be selected.
            cs=ensure(cl,'constraints')
            for q in list(cs):
                if q.get('type')=='max' and q.get('field')=='selections': q.set('value','1')
            if not any(q.get('type')=='max' and q.get('field')=='selections' for q in cs):
                add_constraint(cl,cl.get('id')+'-max','max',1,'parent')
            add_modifier(cl,cl.get('id')+'-discipline','set','hidden','true',
                         conditions=[cond('lessThan',1,dids[d],'root-entry')])
            pes.append(cl)
            spell_ids[(d,spell)]=cl.get('id')

    # Hide/disable until all requirements are met.
    if requirements:
        for i,req in enumerate(requirements):
            inv=dict(req)
            if req['type']=='atLeast': inv['type']='lessThan'
            elif req['type']=='greaterThan': inv['type']='lessThan'
            elif req['type']=='lessThan': inv['type']='atLeast'
            else: raise RuntimeError('Unsupported requirement inversion')
            add_modifier(dg,f'{prefix}-disc-hide-{i}','set','hidden','true',conditions=[inv])
            add_modifier(pg,f'{prefix}-pow-hide-{i}','set','hidden','true',conditions=[inv])
        add_modifier(dg,prefix+'-disc-min-on','set',dmin.get('id'),disc_min,groups=[('and',requirements)])
        add_modifier(pg,prefix+'-pow-min-on','set',pmin.get('id'),power_min,groups=[('and',requirements)])

    # Dynamic tuple: (condition, new_power_min, new_power_max, new_disc_max)
    for i,(q,npmin,npmax,ndmax) in enumerate(dynamic):
        add_modifier(pg,f'{prefix}-dyn-pmin-{i}','set',pmin.get('id'),npmin,conditions=[q])
        add_modifier(pg,f'{prefix}-dyn-pmax-{i}','set',pmax.get('id'),npmax,conditions=[q])
        add_modifier(dg,f'{prefix}-dyn-dmax-{i}','set',dmax.get('id'),ndmax,conditions=[q])

    interfaces.append((prefix,len(allowed),sum(len(POWER_TEMPLATES[d]) for d in allowed),power_min,power_max))
    return dg,pg,dids,spell_ids

def make_fixed_power_group(host,prefix,title,discipline,count,requirements=None):
    requirements=requirements or []
    gs=ensure(host,'selectionEntryGroups')
    gid=prefix+'-powers'
    for x in list(gs):
        if x.get('id')==gid: gs.remove(x)
    g=ET.SubElement(gs,C('selectionEntryGroup'),{'id':gid,'name':title+' — '+discipline,'hidden':'false'})
    mn=add_constraint(g,gid+'-min','min',0 if requirements else count,'parent')
    add_constraint(g,gid+'-max','max',count,'parent')
    ses=ET.SubElement(g,C('selectionEntries'))
    for spell,templ in POWER_TEMPLATES[discipline]:
        cl=prefix_clone(templ,prefix+'-'+sanitize(spell)+'-')
        cl.set('id',prefix+'-power-'+sanitize(spell)); cl.set('name',spell); cl.set('hidden','false')
        strip_categories(cl)
        old=cl.find(C('modifiers'))
        if old is not None: cl.remove(old)
        ses.append(cl)
    if requirements:
        for i,req in enumerate(requirements):
            inv=dict(req); inv['type']='lessThan' if req['type']=='atLeast' else 'atLeast'
            add_modifier(g,f'{gid}-hide-{i}','set','hidden','true',conditions=[inv])
        add_modifier(g,gid+'-min-on','set',mn.get('id'),count,groups=[('and',requirements)])
    interfaces.append((prefix,1,len(POWER_TEMPLATES[discipline]),count,count))
    return g

# ------------------------------------------------------------------
# 1. PSYCHIC UI — LIBRARIAN STYLE
# ------------------------------------------------------------------
xv_req=[cond('atLeast',1,'legion-xv','roster')]

praetor=findid(root,'hq-praetor')
remove_groups(praetor,['r18-ts-praetor-power1','r18-ts-praetor-power2','r18-ts-praetor-power3'])
make_psychic_interface(
    praetor,'r19-ts-praetor','Thousand Sons Praetor',DISCIPLINES,2,2,1,2,
    requirements=xv_req,
    dynamic=[(cond('atLeast',1,'r18-ts-guard-praetor-ml3','root-entry'),3,3,3)]
)

centurion=findid(root,'hq-centurion')
remove_groups(centurion,['r18-ts-centurion-power1','r18-ts-centurion-power2'])
make_psychic_interface(
    centurion,'r19-ts-centurion','Thousand Sons Centurion / Consul',DISCIPLINES,1,1,1,1,
    requirements=xv_req,
    dynamic=[(cond('atLeast',1,'hq-consul-librarian-epistolary','root-entry'),2,2,2)]
)

# Cult-locked Veteran / Terminator Brotherhoods.
for uid in ('veteran-unit','terminator-unit'):
    h=findid(root,uid)
    remove_groups(h,[f'r18-ts-{uid}-brotherhood-power'])
    normal=next((x for x in h.iter(C('entryLink')) if x.get('targetId')=='r45-ts-brotherhood'),None)
    fellow=next((x for x in h.iter(C('entryLink')) if x.get('targetId')=='r45-ts-brotherhood-fellowship'),None)
    cg=findid(root,'r45-cult-'+uid)
    choices={x.get('name'):x.get('id') for x in list(cg.find(C('selectionEntries'))) if cg is not None and cg.find(C('selectionEntries')) is not None}
    cmap={d:choices[c] for c,d in CULT_TO_DISC.items() if c in choices}
    make_psychic_interface(
        h,'r19-ts-'+uid+'-brotherhood','Psychic Brotherhood',
        DISCIPLINES,1,1,1,1,
        requirements=[xv_req[0]],
        cult_gate=cmap
    )
    # The interface is only required when either Brotherhood upgrade is selected.
    dg=findid(root,'r19-ts-'+uid+'-brotherhood-disciplines')
    pg=findid(root,'r19-ts-'+uid+'-brotherhood-powers')
    # overwrite requirement behavior: XV AND (normal OR fellow)
    for g in (dg,pg):
        # min baseline zero
        for c in list(g.find(C('constraints')) or []):
            if c.get('type')=='min': c.set('value','0')
        add_modifier(g,g.get('id')+'-hide-no-brother','set','hidden','true',
                     groups=[('and',[cond('lessThan',1,normal.get('id'),'root-entry'),cond('lessThan',1,fellow.get('id'),'root-entry')])])
        minc=next(c for c in g.find(C('constraints')) if c.get('type')=='min')
        add_modifier(g,g.get('id')+'-min-brother','set',minc.get('id'),1,
                     groups=[('or',[cond('atLeast',1,normal.get('id'),'root-entry'),cond('atLeast',1,fellow.get('id'),'root-entry')])])

# Fellowship Tactical Brotherhood: any normal XV discipline.
tac=findid(root,'tactical-unit')
remove_groups(tac,['r18-ts-tactical-brotherhood-power'])
tlink=next((x for x in tac.iter(C('entryLink')) if x.get('targetId')=='r45-ts-tactical-brotherhood'),None)
make_psychic_interface(
    tac,'r19-ts-tactical-brotherhood','Fellowships Psychic Brotherhood',DISCIPLINES,
    1,1,1,1,requirements=[cond('atLeast',1,tlink.get('id'),'root-entry')]
)

# Sekhmet.
sek=findid(root,'r41-unit-xv-0-sekhmet-terminator-cabal')
remove_groups(sek,['r18-ts-sekhmet-power','r18-final-sekhmet-power2'])
inceptor=findid(root,'r41-unit-xv-0-sekhmet-terminator-cabal-opt-5-sekhmet-inceptor')
make_psychic_interface(
    sek,'r19-ts-sekhmet','Scarab Occult',DISCIPLINES,
    1,1,1,1,
    dynamic=[(cond('atLeast',1,inceptor.get('id'),'root-entry'),2,2,2)]
)

# Ammitara.
amm=findid(root,'r41-unit-xv-2-ammitara-occult-intercession-cabal')
remove_groups(amm,['r18-ts-ammitara-power'])
make_psychic_interface(amm,'r19-ts-ammitara','Ammitara Psychic Brotherhood',
                       ['Divination','Telepathy'],1,1,1,1)

# Osiron.
osi=findid(root,'r41-unit-xv-4-contemptor-osiron-dreadnought')
remove_groups(osi,['r18-ts-osiron-power1','r18-ts-osiron-power2'])
ml2=next((x for x in osi.iter(C('selectionEntry')) if 'Mastery Level 2' in (x.get('name') or '')),None)
if ml2 is None: raise RuntimeError('Osiron ML2 upgrade not found')
make_psychic_interface(
    osi,'r19-ts-osiron','Psychic Dreadnought',DISCIPLINES,1,1,1,1,
    dynamic=[(cond('atLeast',1,ml2.get('id'),'root-entry'),2,2,2)]
)

# Fixed-discipline named characters become one compact list each.
fixed=[
 ('r41-unit-xv-7-phosis-t-kar','r19-ts-phosis','Phosis T’Kar',['r18-ts-r41-unit-xv-7-phosis-t-kar-power1','r18-ts-r41-unit-xv-7-phosis-t-kar-power2'],'Telekinesis',2),
 ('r41-unit-xv-8-magistus-amon-the-hidden','r19-ts-amon','Magistus Amon',['r18-ts-r41-unit-xv-8-magistus-amon-the-hidden-power1','r18-ts-r41-unit-xv-8-magistus-amon-the-hidden-power2'],'Telepathy',2),
 ('r41-unit-xv-9-hathor-maat','r19-ts-hathor','Hathor Maat',['r18-ts-r41-unit-xv-9-hathor-maat-power1','r18-ts-r41-unit-xv-9-hathor-maat-power2'],'Biomancy',2),
]
for uid,prefix,title,olds,disc,n in fixed:
    h=findid(root,uid); remove_groups(h,olds); make_fixed_power_group(h,prefix,title,disc,n)

# Ahriman's Cabal copies — merge each pair into a single two-power Divination list.
for g1 in list(root.iter(C('selectionEntryGroup'))):
    if (g1.get('id') or '')=='r18-final-ahriman-cabal-power1':
        h=host_of_group(g1)
        if h is not None:
            remove_groups(h,['r18-final-ahriman-cabal-power1','r18-final-ahriman-cabal-power2'])
            up=findid(root,'r18-final-ahriman-cabal-upgrade')
            make_fixed_power_group(h,'r19-ts-ahriman-cabal',"Ahriman's Cabal",'Divination',2,
                                   requirements=[cond('atLeast',1,up.get('id'),'root-entry')])
        break

# Crimson King's Guard power groups — one discipline then one power.
for g in list(root.iter(C('selectionEntryGroup'))):
    if 'crimson-guard-power' not in (g.get('id') or ''): continue
    h=host_of_group(g)
    if h is None: continue
    gid=g.get('id')
    # sibling upgrade generated from same prefix
    up=next((e for e in h.iter(C('selectionEntry')) if (e.get('name') or '')=='Brotherhood of Psykers (Mastery Level 1)'),None)
    remove_group(h,gid)
    make_psychic_interface(h,'r19-'+sanitize(gid),'Crimson King’s Guard',DISCIPLINES,1,1,1,1,
                           requirements=[cond('atLeast',1,up.get('id'),'root-entry')])

# Magnus: two or three disciplines, exactly three selected normal powers.
magnus=findid(root,'r41-unit-xv-11-xv-magnus-the-red-the-crimson-king')
remove_groups(magnus,['r18-ts-magnus-primary-disc','r18-ts-magnus-secondary-disc',
                      'r18-ts-magnus-power1','r18-ts-magnus-power2','r18-ts-magnus-power3'])
make_psychic_interface(magnus,'r19-ts-magnus','Magnus — Selected Normal Powers',
                       DISCIPLINES,3,3,2,3)

# Magnus Shard: choose disciplines first, then exactly six unique normal powers.
shard=findid(root,'r41-unit-xv-12-magnus-shard-of-the-crimson-king')
remove_groups(shard,[f'r18-final-shard-power{i}' for i in range(1,7)])
make_psychic_interface(shard,'r19-ts-shard','Magnus Shard — Selected Normal Powers',
                       DISCIPLINES,6,6,1,5)

log.append(f'Psychic UI rebuilt into Librarian-style Discipline(s) -> Powers for {len(interfaces)} interfaces; flat multi-discipline walls removed')

# ------------------------------------------------------------------
# 2. CULT ARCANA + CULT MASTERY — CLEAN, UNIT-FACING RULES
# ------------------------------------------------------------------
CULT_RULES={
 'Pavoni':(
   ('Cult Arcana — Quickblood','This unit gains Fleet.'),
   ('Cult Mastery — Quickblood','If this unit has the Psyker or Brotherhood of Psykers special rule, it also gains Crusader.')
 ),
 'Raptora':(
   ('Cult Arcana — Kine Shields','Models in this unit gain a 6+ Invulnerable Save against shooting attacks. This does not improve an existing Invulnerable Save.'),
   ('Cult Mastery — Kine Shields','If this unit has the Psyker or Brotherhood of Psykers special rule, models instead gain a 5+ Invulnerable Save against shooting; an existing Invulnerable Save improves by 1 against shooting to a maximum of 4+, and Cover Saves against shooting improve by 1 to a maximum of 3+. These benefits do not apply in close combat.')
 ),
 'Corvidae':(
   ('Cult Arcana — Precognitive Strike','When this unit resolves a First Fire shooting attack, it may re-roll To Hit rolls of 1 with all ranged weapons fired as part of that attack.'),
   ('Cult Mastery — Precognitive Strike','If this unit has the Psyker or Brotherhood of Psykers special rule, it may also re-roll To Hit rolls of 1 when making Overwatch, Return Fire and Stand & Shoot attacks.')
 ),
 'Athanaeans':(
   ('Cult Arcana — Discipline of the Mind','This unit gains Stubborn and may re-roll failed Pinning tests.'),
   ('Cult Mastery — Discipline of the Mind','If this unit has the Psyker or Brotherhood of Psykers special rule, it additionally gains Adamantium Will.')
 ),
 'Pyrae':(
   ('Cult Arcana — Ashen Blow','This unit gains Hammer of Wrath.'),
   ('Cult Mastery — Ashen Blow','If this unit has the Psyker or Brotherhood of Psykers special rule, close-combat attacks and Flame weapons used by models in the unit gain Soul Blaze.')
 ),
}
cult_options=0
for g in root.iter(C('selectionEntryGroup')):
    if 'Prosperine Cult' not in (g.get('name') or ''): continue
    ses=g.find(C('selectionEntries'))
    if ses is None: continue
    for e in list(ses):
        cult=e.get('name') or ''
        if cult not in CULT_RULES: continue
        rs=ensure(e,'rules')
        # Remove old generic cult reminder rule and previous R19 versions.
        for r in list(rs):
            if (r.get('name') or '')==cult or (r.get('id') or '').startswith('r19-cult-'):
                rs.remove(r)
        for kind,(rn,txt) in zip(('arcana','mastery'),CULT_RULES[cult]):
            rule(e,f'r19-cult-{sanitize(e.get("id") or cult)}-{kind}',rn,txt)
        cult_options+=1
log.append(f'Prosperine Cult display rebuilt on {cult_options} unit/character Cult options: Arcana and Cult Mastery are now separate unit-facing rules')

# ------------------------------------------------------------------
# 3. REMOVE XV SOURCE WALLS AND REPLACE WITH DISCRETE RULES
# ------------------------------------------------------------------
def hide_source(host):
    if host is None: return 0
    n=0
    rs=host.find(C('rules'))
    if rs is not None:
        for r in list(rs):
            if (r.get('name') or '')=='Source Entry':
                r.set('hidden','true'); n+=1
    return n

source_hidden=0

# Reusable discrete rules for unique units and retinue copies.
for u in root.iter(C('selectionEntry')):
    if u.get('type')!='unit': continue
    name=u.get('name') or ''
    if name=='SEKHMET TERMINATOR CABAL':
        source_hidden+=hide_source(u)
        rule(u,'r19-'+sanitize(u.get('id'))+'-scarab','Scarab Occult',
             'This unit is a Psychic Brotherhood. Assign it to one Prosperine Cult; it receives that Cult’s Arcana and Cult Mastery. It selects one power from the normal Thousand Sons disciplines and takes Psychic Tests on Leadership 9. While the Sekhmet Inceptor is alive, the Cabal is Mastery Level 2, knows one additional power and tests on Leadership 10; if he is slain it returns to Mastery Level 1 and loses the second power.')
        rule(u,'r19-'+sanitize(u.get('id'))+'-force','Prosperine Force Weapons',
             'The Cabal uses the normal Prosperine Force Weapon rules. It may attempt only one Force Weapon activation in each Assault phase, and that activation counts as using one psychic power.')
    elif name=='KHENETAI OCCULT BLADE CABAL':
        source_hidden+=hide_source(u)
        rule(u,'r19-'+sanitize(u.get('id'))+'-brotherhood','Psychic Brotherhood',
             'Assign the Cabal to one Prosperine Cult. It receives both that Cult’s Arcana and Cult Mastery. The Cabal knows only Mindsong of Blades and does not select a normal ProHammer psychic power.')
        rule(u,'r19-'+sanitize(u.get('id'))+'-mindsong','Mindsong of Blades',
             'Blessing, invoked at the beginning of an Assault phase. If successful, until the end of that Assault phase models in the unit gain +1 Initiative and may re-roll close-combat To Hit rolls of 1.')
        rule(u,'r19-'+sanitize(u.get('id'))+'-paired','Paired Prosperine Force Blades',
             'The Khenetai Blades count as a pair of Prosperine Force Weapons. The bonus Attack for two close-combat weapons is already included in their profiles. Force Weapon activation does not count as invoking a psychic power.')
    elif name=='AMMITARA OCCULT INTERCESSION CABAL':
        source_hidden+=hide_source(u)
        rule(u,'r19-'+sanitize(u.get('id'))+'-brotherhood','Psychic Brotherhood',
             'Assign the Cabal to one Prosperine Cult. It receives both that Cult’s Arcana and Cult Mastery. It is Brotherhood of Psykers (Mastery Level 1) and selects one power from Divination or Telepathy.')
    elif name=='CASTELLAX-ACHEA MANIPLE':
        source_hidden+=hide_source(u)
        rule(u,'r19-'+sanitize(u.get('id'))+'-matrix','Aetheric Command Matrix',
             'At the beginning of each Thousand Sons Movement phase, if no model in the Maniple is within 12" of a friendly Thousand Sons Psyker, take a Leadership test. If failed, the Maniple may not Advance or charge and, if it shoots, must target the nearest visible eligible enemy unit.')
        rule(u,'r19-'+sanitize(u.get('id'))+'-conduit','Psychic Conduit',
             'Once in each Thousand Sons Shooting phase, one friendly Thousand Sons Psyker within 12" may channel one psychic shooting power through one Castellax-Achea, measuring range and line of sight from it. The selected Castellax may not fire its Æther-fire Cannon that phase. If the Psyker suffers Perils, the selected Castellax also suffers one Wound; its Invulnerable Save applies normally.')
        rule(u,'r19-'+sanitize(u.get('id'))+'-shield','Aetheric Shielding','The Castellax-Achea has a 5+ Invulnerable Save, already included in its profile.')
        rule(u,'r19-'+sanitize(u.get('id'))+'-construct','Thousand Sons Construct',
             'The Castellax-Achea counts as a Thousand Sons unit for rules which specifically affect friendly Thousand Sons units. It does not possess Legiones Astartes and is not assigned to a Prosperine Cult.')
    elif name=='CONTEMPTOR-OSIRON DREADNOUGHT':
        source_hidden+=hide_source(u)
        rule(u,'r19-'+sanitize(u.get('id'))+'-psy','Psychic Dreadnought',
             'The Osiron is a Psyker (Mastery Level 1), tests on Leadership 9 and selects one power from Biomancy, Divination, Pyromancy, Telekinesis or Telepathy. If upgraded to Mastery Level 2 it selects a second power from the same list. Perils of the Warp causes one automatic Glancing Hit which Automatic Shielding may not prevent. The Osiron is not assigned to a Prosperine Cult.')
        rule(u,'r19-'+sanitize(u.get('id'))+'-battle','Aetheric Battle-Engine',
             'The Osiron may invoke psychic powers in a turn in which it fires weapons. One psychic shooting power may be resolved in addition to its normal shooting attacks; unless another rule permits otherwise, all its shooting that phase must target the same enemy unit.')
        rule(u,'r19-'+sanitize(u.get('id'))+'-blade','Osiron Force Blade',
             'Counts as both a Dreadnought Close Combat Weapon and a Force Weapon. Force Weapon activation does not count as invoking a psychic power.')
    elif name=='NUMEROLOGIST CABAL':
        source_hidden+=hide_source(u)
        rule(u,'r19-'+sanitize(u.get('id'))+'-order','Order of Ruin',
             'Assign the Cabal to one Prosperine Cult. The Cabal receives that Cult’s Arcana; while the Numerologist remains alive it also receives that Cult’s Cult Mastery. The Numerologist knows only Psy-Synchronicity.')
        rule(u,'r19-'+sanitize(u.get('id'))+'-sync','Psy-Synchronicity',
             'Blessing, Thousand Sons Movement phase. If successful, select up to two friendly Thousand Sons units with a model within 6". Until the end of the following Thousand Sons Shooting phase, models in those units may re-roll shooting To Hit rolls of 1. The Numerologist may not fire a weapon in a player turn in which he successfully invokes this power.')
        rule(u,'r19-'+sanitize(u.get('id'))+'-smith','Battlesmith',
             'The Numerologist uses the normal Battlesmith rule. His Servo-Arm grants the normal +1 bonus to repair attempts.')

# Named characters.
phosis=findid(root,'r41-unit-xv-7-phosis-t-kar')
source_hidden+=hide_source(phosis)
rule(phosis,'r19-phosis-cult','Raptora','Phosis always belongs to the Raptora and receives both the Raptora Cult Arcana and Cult Mastery.')
rule(phosis,'r19-phosis-magister','Magister of the Raptora','Phosis selects both of his psychic powers from Telekinesis and otherwise follows the normal rules for a Mastery Level 2 Psyker.')
rule(phosis,'r19-phosis-field','Eldritch Force Field','Phosis has a 4+ Invulnerable Save, improved to 3+ against shooting. While joined to a friendly Thousand Sons Infantry unit, models in that unit receive a 5+ Invulnerable Save against shooting and close combat; existing Invulnerable Saves improve by 1, to a maximum of 3+ against shooting and 4+ in close combat. This may combine with Raptora benefits but may not exceed those limits.')
rule(phosis,'r19-phosis-retinue','Command Retinue','Phosis may select one Legion Command Squad as his retinue without occupying a separate Force Organisation slot.')

amon=findid(root,'r41-unit-xv-8-magistus-amon-the-hidden')
source_hidden+=hide_source(amon)
rule(amon,'r19-amon-cult','Athanaeans','Amon always belongs to the Athanaeans and receives both the Athanaean Cult Arcana and Cult Mastery.')
rule(amon,'r19-amon-powers','Psychic Powers','Amon selects both of his psychic powers from Telepathy.')
rule(amon,'r19-amon-armour','Armour of Shades','Grants a 2+ Armour Save. Amon receives a 5+ Cover Save in open ground; an existing Cover Save improves by two steps, to a maximum of 3+.')
rule(amon,'r19-amon-hidden','The Hidden One','While Amon is joined to a friendly Thousand Sons Infantry unit, that unit receives the same Cover Save protection as the Armour of Shades and gains Infiltrate. This may not be conferred to Terminator Armour models, Bikes, Jetbikes or Jump Infantry.')
rule(amon,'r19-amon-retinue','Master of the Hidden Orders','Instead of a normal Legion Command Squad, Amon may select one Ammitara Occult Intercession Cabal or Legion Seeker Squad as his personal retinue. It occupies no separate Force Organisation slot.')

hathor=findid(root,'r41-unit-xv-9-hathor-maat')
source_hidden+=hide_source(hathor)
rule(hathor,'r19-hathor-cult','Pavoni','Hathor Maat always belongs to the Pavoni and receives both the Pavoni Cult Arcana and Cult Mastery.')
rule(hathor,'r19-hathor-magister','Magister Templi of the Pavoni','Hathor Maat selects both of his psychic powers from Biomancy and otherwise follows the normal rules for a Mastery Level 2 Psyker.')
rule(hathor,'r19-hathor-field','Aetheric Refractor Field','Hathor Maat has a 4+ Invulnerable Save; this is already included in his profile.')
rule(hathor,'r19-hathor-vitalist','Pavoni Vitalist','Hathor Maat has Feel No Pain (5+). While joined to a friendly Thousand Sons Infantry unit, that unit also gains Feel No Pain (5+); an existing Feel No Pain improves by one step to a maximum of 4+. The benefit ends if Hathor leaves or is slain.')
rule(hathor,'r19-hathor-narthecium','Narthecium','Hathor Maat uses the normal Narthecium rules from the Legiones Astartes Army List.')
rule(hathor,'r19-hathor-retinue','Command Retinue','Hathor Maat may select one Legion Command Squad as his retinue without occupying a separate Force Organisation slot.')

san=findid(root,'r41-unit-xv-10-sanakht')
source_hidden+=hide_source(san)
rule(san,'r19-sanakht-cult','Athanaeans','Sanakht always belongs to the Athanaeans and receives both the Athanaean Cult Arcana and Cult Mastery.')
rule(san,'r19-sanakht-psy','Psychic Powers','Sanakht is Mastery Level 1 and knows only Mindsong of Blades. He does not select a power from the normal ProHammer Psychic Disciplines.')
rule(san,'r19-sanakht-mindsong','Mindsong of Blades','Blessing, invoked at the beginning of an Assault phase. If successful, until the end of that Assault phase models in Sanakht’s unit gain +1 Initiative and may re-roll close-combat To Hit rolls of 1.')
rule(san,'r19-sanakht-blades','Paired Prosperine Force Blades','Count as a pair of Prosperine Force Weapons. The bonus Attack for fighting with two close-combat weapons is already included in Sanakht’s profile. Activating them as Force Weapons does not count as invoking a psychic power.')
rule(san,'r19-sanakht-blademaster','Blademaster of Prospero','Sanakht may re-roll one failed To Hit roll and one failed To Wound roll during each Assault phase. A die may never be re-rolled more than once.')
rule(san,'r19-sanakht-retinue','Khenetai Retinue','Sanakht may select one Khenetai Occult Blade Cabal as his personal retinue. It occupies no separate Force Organisation slot; Sanakht and the Cabal count as one HQ selection.')

# Force fixed Cult selectors for named characters to only their source Cult.
for h,cult in [(phosis,'Raptora'),(amon,'Athanaeans'),(hathor,'Pavoni'),(san,'Athanaeans')]:
    cg=next((g for g in direct_groups(h) if 'Prosperine Cult' in (g.get('name') or '')),None)
    if cg is not None:
        cg.set('name','Prosperine Cult — fixed')
        ses=cg.find(C('selectionEntries'))
        for e in list(ses) if ses is not None else []:
            if (e.get('name') or '')!=cult: e.set('hidden','true')
            else:
                e.set('hidden','false')
                # ensure chosen fixed cult is mandatory
                cs=ensure(e,'constraints')
                if not any(q.get('type')=='min' for q in cs):
                    add_constraint(e,e.get('id')+'-r19-fixed-min','min',1,'parent')

log.append(f'XV source-wall cleanup: hid {source_hidden} imported Source Entry blocks and replaced key unit/character rules with discrete entries, including Sanakht')

# ------------------------------------------------------------------
# 4. RITES OF WAR — DISCRETE RULES + FUNCTIONAL RESTRICTIONS
# ------------------------------------------------------------------
AXIS='r25-rite-xv-0-the-axis-of-dissolution'
GUARD='r25-rite-xv-1-the-guard-of-the-crimson-king'
FELLOWS='r25-rite-xv-2-the-fellowships-of-prospero'
axis=findid(root,AXIS); guard=findid(root,GUARD); fellows=findid(root,FELLOWS)
if None in (axis,guard,fellows): raise RuntimeError('Missing one or more XV Rites')

# Global 0-1 Rite selection for the three XV Rites via hidden category.
cats=ensure(groot,'categoryEntries',G)
ritecat='r19-ts-cat-rite-limit'
if findid(groot,ritecat) is None:
    ET.SubElement(cats,G('categoryEntry'),{'id':ritecat,'name':'Thousand Sons Rite of War 0-1','hidden':'true'})
for i,r in enumerate((axis,guard,fellows)):
    add_category_link(r,f'r19-ts-rite-cat-{i}','Thousand Sons Rite of War 0-1',ritecat)
force=findid(groot,'force-standard')
fcls=ensure(force,'categoryLinks',G)
old=next((x for x in fcls if x.get('id')=='r19-ts-rite-limit'),None)
if old is not None: fcls.remove(old)
rl=ET.SubElement(fcls,G('categoryLink'),{'id':'r19-ts-rite-limit','name':'Thousand Sons Rite of War 0-1','hidden':'true','targetId':ritecat})
add_constraint(rl,'r19-ts-rite-limit-max','max',1,'parent',ns=G)

# Replace long rite wall rule with concise named pieces.
def clear_rite_rules(r):
    rs=ensure(r,'rules')
    for x in list(rs): rs.remove(x)

clear_rite_rules(axis)
rule(axis,'r19-axis-intro','The Axis of Dissolution','A prepared Thousand Sons tactical configuration built around selected ground, disciplined resistance and the destruction of an enemy drawn into the pattern.')
rule(axis,'r19-axis-alembic','The Alembic of Adamant','Thousand Sons units automatically pass Morale and Pinning tests while at least one model is within 6" of an Objective. If the mission has no Objectives, nominate one terrain feature outside the enemy deployment zone after deployment zones are determined; its centre counts as an Objective for this rule only.')
rule(axis,'r19-axis-caustic','The Caustic of Grace','Thousand Sons Infantry may enter Overwatch even if they moved in their preceding Movement phase, provided they did not Advance. All other ProHammer Overwatch requirements apply.')
rule(axis,'r19-axis-vitriol','The Transition of Vitriol','Thousand Sons models may re-roll failed To Hit and To Wound rolls against an enemy unit which is Falling Back. Against Vehicles affected by a mission retreat/withdrawal rule, re-roll failed Armour Penetration rolls instead of failed To Wound rolls.')
rule(axis,'r19-axis-limits','Limitations','Every Troops choice must be taken at its maximum permitted unit size. The Detachment may not contain more Tank/Flyer Vehicles than Infantry units and may not include a Fortification. The unit-size restriction is enforced in New Recruit; the cross-unit Vehicle ratio remains stated here because the catalogue cannot safely count every nested/linked unit type.')

clear_rite_rules(guard)
rule(guard,'r19-guard-intro','The Guard of the Crimson King','The XV Legion’s Sekhmet and greatest sorcerers are concentrated into a single psychic spearhead.')
rule(guard,'r19-guard-astral','Astral Warfare','The first two psychic powers successfully invoked by Thousand Sons Psykers during each player turn are ignored when determining Disturbance in the Warp penalties.')
rule(guard,'r19-guard-lightning','Wreathed in Lightning, They Rend the Veil','All Thousand Sons units composed entirely of Terminator Armour gain Teleportation Transponders free. Thousand Sons Independent Characters may purchase them for +10 points regardless of armour. A unit/Character arriving by Deep Strike with them gains Fear and may re-roll Invulnerable Save rolls of 1 until the beginning of the next Thousand Sons player turn.')
rule(guard,'r19-guard-scarab','Initiates of the Scarab','Sekhmet Terminator Cabals are Troops choices and must fulfil the compulsory Troops selections. Note: the Sekhmet entry is also explicitly 0–1; that written source contradiction is preserved rather than silently overridden.')
rule(guard,'r19-guard-bidding','The Bidding of the Crimson King','Magnus the Red may fulfil a compulsory HQ selection and does not occupy a Lord of War selection while using this Rite.')
rule(guard,'r19-guard-limits','Limitations','The Warlord must be Magnus, Ahzek Ahriman or a Thousand Sons Praetor. A Praetor Warlord may upgrade from Mastery Level 2 to 3 for +25 points. Vehicle units may not exceed units with Legiones Astartes (Thousand Sons). No Allied Detachment or Fortification. Warlord and cross-unit ratio requirements remain explicit because the current roster schema has no dependable marker/counter for them.')

clear_rite_rules(fellows)
rule(fellows,'r19-fellows-intro','The Fellowships of Prospero','Great Fellowship formations in which entire companies fight as extensions of their sorcerous commanders.')
rule(fellows,'r19-fellows-circles','Circles of Initiates','A 20-model Legion Tactical Squad may purchase Brotherhood of Psykers (Mastery Level 1) for +25 points. It selects one power from any normal Thousand Sons discipline, gains its chosen Cult Mastery and follows the normal Psychic Brotherhood rules.')
rule(fellows,'r19-fellows-vets','Fellowship Veterans','Legion Veteran and Legion Terminator Squads purchase Brotherhood of Psykers for +15 points per squad instead of +25.')
rule(fellows,'r19-fellows-magister','Magister Templi','At the beginning of each Thousand Sons player turn, the Warlord may nominate one friendly Psychic Brotherhood within 12". Until the next Thousand Sons turn it may use the Warlord’s Leadership for Psychic Tests, overriding the normal attached-Independent-Character restriction.')
rule(fellows,'r19-fellows-order','Order of the Cults','Every Psychic Brotherhood must belong to the same Prosperine Cult as at least one Thousand Sons Independent Character in the army. This remains a roster rule rather than an unsafe cross-root automatic validator.')
rule(fellows,'r19-fellows-limits','Limitations','The Warlord must be a Thousand Sons Psyker. The Detachment must include at least two Psychic Brotherhoods. Tactical Brotherhoods require 20 models. Maximum one Fast Attack choice. No Allied Detachment. The Brotherhood-count and Fast Attack restrictions are enforced in New Recruit.')

# Axis — enforce maximum size on every top-level unit currently categorised as Troops.
axis_forced=[]
for u in root.iter(C('selectionEntry')):
    if u.get('type')!='unit': continue
    cls=u.find(C('categoryLinks'))
    if cls is None or not any(x.get('targetId')=='cat-troops' for x in list(cls)): continue
    for m in direct_entries(u):
        if m.get('type')!='model': continue
        cs=m.find(C('constraints'))
        if cs is None: continue
        mn=next((x for x in cs if x.get('type')=='min' and x.get('field')=='selections'),None)
        mx=next((x for x in cs if x.get('type')=='max' and x.get('field')=='selections'),None)
        if mn is None or mx is None: continue
        try:
            if float(mx.get('value'))<=float(mn.get('value')): continue
        except: continue
        add_modifier(m,'r19-axis-max-'+sanitize(m.get('id')),'set',mn.get('id'),mx.get('value'),
                     conditions=[cond('atLeast',1,AXIS,'roster')])
        axis_forced.append(u.get('name')+': '+(m.get('name') or 'model')+'='+mx.get('value'))

# Guard — make Sekhmet a Troops category while selected.
for u in root.iter(C('selectionEntry')):
    if u.get('type')=='unit' and (u.get('name') or '')=='SEKHMET TERMINATOR CABAL':
        cls=ensure(u,'categoryLinks')
        elite=next((x for x in list(cls) if x.get('targetId')=='cat-elites'),None)
        if elite is not None:
            add_modifier(elite,'r19-guard-sekhmet-hide-elite','set','hidden','true',
                         conditions=[cond('atLeast',1,GUARD,'roster')])
        troop=next((x for x in list(cls) if x.get('id')=='r19-guard-sekhmet-troops'),None)
        if troop is None:
            troop=ET.SubElement(cls,C('categoryLink'),{'id':'r19-guard-sekhmet-troops','name':'Troops — Guard of the Crimson King','targetId':'cat-troops','primary':'true','hidden':'true'})
        add_modifier(troop,'r19-guard-sekhmet-show-troops','set','hidden','false',
                     conditions=[cond('atLeast',1,GUARD,'roster')])

# Guard — free Transponders are mandatory on eligible Terminator units.
forced_trans=0
for e in root.iter(C('entryLink')):
    if e.get('targetId')!='r45-ts-trans-unit': continue
    cs=ensure(e,'constraints')
    mn=next((x for x in cs if x.get('type')=='min' and x.get('field')=='selections'),None)
    if mn is None: mn=add_constraint(e,'r19-'+sanitize(e.get('id'))+'-guard-min','min',0,'parent')
    add_modifier(e,'r19-'+sanitize(e.get('id'))+'-guard-min-on','set',mn.get('id'),1,
                 conditions=[cond('atLeast',1,GUARD,'roster')])
    forced_trans+=1
sektrans=findid(root,'r41-unit-xv-0-sekhmet-terminator-cabal-opt-7-teleportation-transponders')
if sektrans is not None:
    cs=ensure(sektrans,'constraints')
    mn=next((x for x in cs if x.get('type')=='min' and x.get('field')=='selections'),None)
    if mn is None: mn=add_constraint(sektrans,'r19-sekhmet-trans-min','min',0,'parent')
    add_modifier(sektrans,'r19-sekhmet-trans-guard-min','set',mn.get('id'),1,
                 conditions=[cond('atLeast',1,GUARD,'roster')])
    forced_trans+=1

# Axis + Guard Fortification bans, if this GST exposes a Fortification category.
fort_links=[]
cat_by_id={x.get('id'):(x.get('name') or '') for x in groot.iter(G('categoryEntry'))}
for fl in list(force.find(G('categoryLinks')) or []):
    if 'fortification' in cat_by_id.get(fl.get('targetId'),'').lower() or 'fortification' in (fl.get('name') or '').lower():
        fort_links.append(fl)
        cs=ensure(fl,'constraints',G)
        mx=next((x for x in cs if x.get('type')=='max' and x.get('field')=='selections'),None)
        if mx is None: mx=add_constraint(fl,'r19-ts-fort-max','max',99,'parent',ns=G)
        for rite in (AXIS,GUARD):
            add_modifier(fl,'r19-'+sanitize(fl.get('id'))+'-'+sanitize(rite),'set',mx.get('id'),0,
                         conditions=[cond('atLeast',1,rite,'roster')],ns=G)

# Existing Fellowships enforcement is retained and checked below.
log.append(f'Rites rebuilt as discrete rules; Axis maximum-size enforcement applied to {len(axis_forced)} scalable Troops entries; Guard reclassifies Sekhmet as Troops and forces {forced_trans} free Terminator Transponder options')
if fort_links:
    log.append(f'Axis/Guard Fortification bans automated on {len(fort_links)} force-category link(s)')
else:
    log.append('No safe Fortification force-category link exists in the current GST; Fortification bans remain explicit Rite text')

# ------------------------------------------------------------------
# 5. VALIDATION
# ------------------------------------------------------------------
# Old crowded multi-discipline groups must be gone from their direct hosts.
old_groups=[
 'r18-ts-praetor-power1','r18-ts-praetor-power2','r18-ts-praetor-power3',
 'r18-ts-centurion-power1','r18-ts-centurion-power2','r18-ts-tactical-brotherhood-power',
 'r18-ts-veteran-unit-brotherhood-power','r18-ts-terminator-unit-brotherhood-power',
 'r18-ts-sekhmet-power','r18-final-sekhmet-power2','r18-ts-ammitara-power',
 'r18-ts-osiron-power1','r18-ts-osiron-power2',
 'r18-ts-magnus-power1','r18-ts-magnus-power2','r18-ts-magnus-power3',
]+[f'r18-final-shard-power{i}' for i in range(1,7)]
still=[i for i in old_groups if findid(root,i) is not None]
if still: raise RuntimeError('Old crowded psychic groups still present: '+', '.join(still))

# Every new multi-discipline interface must have a Discipline group and a Powers group.
for prefix,nd,np,pmin,pmax in interfaces:
    if findid(root,prefix+'-powers') is None:
        raise RuntimeError('Missing new Powers group '+prefix)
    # fixed groups intentionally have no discipline group.
    if nd>1 and findid(root,prefix+'-disciplines') is None:
        raise RuntimeError('Missing new Discipline group '+prefix)

# Sanakht wall hidden and discrete rules present.
ss=next((r for r in list(san.find(C('rules')) or []) if (r.get('name') or '')=='Source Entry'),None)
if ss is not None and ss.get('hidden')!='true':
    raise RuntimeError('Sanakht Source Entry still visible')
for rid in ('r19-sanakht-mindsong','r19-sanakht-blades','r19-sanakht-blademaster'):
    if findid(root,rid) is None: raise RuntimeError('Sanakht discrete rule missing '+rid)

# Cult options should now have Arcana + Mastery as separate rules.
bad_cults=[]
for g in root.iter(C('selectionEntryGroup')):
    if 'Prosperine Cult' not in (g.get('name') or ''): continue
    ses=g.find(C('selectionEntries'))
    for e in list(ses) if ses is not None else []:
        if (e.get('name') or '') not in CULT_RULES: continue
        names=[r.get('name') or '' for r in list(e.find(C('rules')) or [])]
        if not any(n.startswith('Cult Arcana') for n in names) or not any(n.startswith('Cult Mastery') for n in names):
            bad_cults.append(e.get('id'))
if bad_cults: raise RuntimeError('Cult split incomplete: '+', '.join(bad_cults[:10]))

# Existing Fellowships limits must still be functional in GST.
flfast=findid(groot,'fl-fast')
if flfast is None or not any(m.get('id')=='r18-ts-fellowships-fast-max' for m in flfast.iter(G('modifier'))):
    raise RuntimeError('Fellowships Fast Attack max-1 modifier missing')
bro=findid(groot,'r18-ts-brotherhood-limit')
if bro is None: raise RuntimeError('Fellowships minimum-two Brotherhood validator missing')

# Guard Sekhmet must have dynamic Troops category.
if not any(x.get('id')=='r19-guard-sekhmet-troops' for x in sek.iter(C('categoryLink'))):
    raise RuntimeError('Guard Sekhmet Troops category missing')

lines=[
 'R19 THOUSAND SONS CLEANUP — '+('APPLY' if APPLY else 'DRY RUN'),
 f'Input CAT revision: 18 | Proposed CAT revision: 19 | GST revision remains {groot.get("revision")}',
 f'LIVE FILES WRITTEN: {"YES" if APPLY else "NO"}',
 '',
 'CHANGES:'
]
lines += ['  + '+x for x in log]
lines += [
 '',
 'PSYCHIC INTERFACES:',
]+[f'  - {p}: {d} discipline option(s), {n} power option(s), choose {mn}-{mx} power(s)' for p,d,n,mn,mx in interfaces]
lines += [
 '',
 'RITE LIMITS INTENTIONALLY LEFT AS TEXT:',
 '  - Guard of the Crimson King: Sekhmet remains source 0–1 even though the Rite requires Sekhmet to fill compulsory Troops; no invented override.',
 '  - Axis/Guard cross-unit Vehicle ratios are not automated because nested/linked unit-type counting is not dependable.',
 '  - Warlord identity restrictions are not automated because the current catalogue has no single reliable Warlord marker.',
 '  - Allied Detachment bans and Fellowships Order of the Cults remain explicit text rather than unsafe cross-force/cross-root validation.',
 '',
 'R19 RESULT: PASS'
]
OUT.write_text('\n'.join(lines),encoding='utf-8')

if APPLY:
    root.set('revision','19')
    ct.write(CAT,encoding='utf-8',xml_declaration=True)
    gt.write(GST,encoding='utf-8',xml_declaration=True)
    idx=IDX.read_text(encoding='utf-8')
    idx=re.sub(r'(filePath="Legiones Astartes\.cat"[^>]*dataRevision=")\d+(")',r'\g<1>19\2',idx)
    IDX.write_text(idx,encoding='utf-8')

print('\n'.join(lines))
