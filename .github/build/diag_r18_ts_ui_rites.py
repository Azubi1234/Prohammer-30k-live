from pathlib import Path
import xml.etree.ElementTree as ET
CAT=Path('Legiones Astartes.cat'); GST=Path('Prohammer 30k.gst')
ct=ET.parse(CAT); root=ct.getroot()
NS=root.tag.split('}')[0].strip('{'); C=lambda t:f'{{{NS}}}{t}'
gt=ET.parse(GST); groot=gt.getroot(); GNS=groot.tag.split('}')[0].strip('{'); G=lambda t:f'{{{GNS}}}{t}'
def findid(r,i):
    return next((e for e in r.iter() if e.get('id')==i),None)
def pts(e):
    out=[]
    if e is None:return ''
    for c in e.iter(C('cost')):
        out.append(f"{c.get('name')}={c.get('value')}")
    return ','.join(out)
def dump(e,depth=0,maxdepth=5):
    if e is None:return ['MISSING']
    lines=[]
    def rec(x,d):
        tag=x.tag.rsplit('}',1)[-1]
        if d<=maxdepth and (tag in ('selectionEntry','selectionEntryGroup','entryLink','rule','modifier','condition','conditionGroup','constraint','categoryLink','profile')):
            attrs=[]
            for k in ('id','name','type','hidden','targetId','field','value','scope','childId','typeId'):
                if x.get(k) is not None: attrs.append(f'{k}={x.get(k)}')
            p=pts(x) if tag in ('selectionEntry','entryLink') else ''
            if p: attrs.append('pts='+p)
            lines.append('  '*d+tag+' | '+' | '.join(attrs))
            if tag=='rule':
                de=x.find(C('description'))
                if de is not None and de.text: lines.append('  '*(d+1)+'DESC='+de.text[:500].replace('\n',' '))
        if d>=maxdepth:return
        for ch in list(x): rec(ch,d+1)
    rec(e,0); return lines

out=[f'CAT={root.get("revision")} GST={groot.get("revision")}']
for i in ['r61-librarian-power1','r61-librarian-power2','hq-librarian','r18-ts-praetor-power1','r18-ts-praetor-power2','r18-ts-centurion-power1','r18-ts-tactical-brotherhood-power','r18-ts-sekhmet-power','r18-final-sekhmet-power2']:
    out+=['\n=== '+i+' ===']+dump(findid(root,i),0,4)

out.append('\n=== XV POWER GROUPS / CULT GROUPS / RITES ===')
for e in root.iter():
    eid=e.get('id') or ''; nm=e.get('name') or ''
    if ('r18' in eid or 'r45-cult' in eid or 'r25-rite-xv' in eid) and (
        'power' in eid.lower() or 'cult' in eid.lower() or 'rite-xv' in eid.lower() or 'brother' in eid.lower()):
        tag=e.tag.rsplit('}',1)[-1]
        if tag in ('selectionEntry','selectionEntryGroup'):
            out.append(f'{tag} | id={eid} | name={nm} | type={e.get("type")} | hidden={e.get("hidden")}')

for i in ['r25-rite-xv-0-the-axis-of-dissolution','r25-rite-xv-1-the-guard-of-the-crimson-king','r25-rite-xv-2-the-fellowships-of-prospero']:
    out+=['\n=== RITE '+i+' ===']+dump(findid(root,i),0,5)

out.append('\n=== SANAKHT ===')
out += dump(findid(root,'r41-unit-xv-10-sanakht'),0,6)
if out[-1]=='MISSING':
    # find by name
    s=next((e for e in root.iter(C('selectionEntry')) if (e.get('name') or '').upper()=='SANAKHT'),None)
    out=out[:-1]+dump(s,0,6)

out.append('\n=== XV CULT SELECTIONS ON INFANTRY ROOTS ===')
for u in root.iter(C('selectionEntry')):
    if u.get('type')!='unit': continue
    nm=u.get('name') or ''
    # identify roots that contain XV cult entries or legion xv gate
    cults=[e for e in u.iter(C('selectionEntry')) if 'cult' in (e.get('id') or '').lower() or (e.get('name') or '') in ('Pavoni','Raptora','Corvidae','Athanaeans','Pyrae')]
    if cults:
        out.append(f'UNIT {u.get("id")} | {nm}')
        for c in cults[:12]: out.append(f'  {c.tag.rsplit("}",1)[-1]} {c.get("id")} | {c.get("name")} | hidden={c.get("hidden")}')

Path('inspection-r18-ts-ui-rites-diag.txt').write_text('\n'.join(out),encoding='utf-8')
print('\n'.join(out[:1200]))
