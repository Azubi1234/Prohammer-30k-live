from pathlib import Path
import xml.etree.ElementTree as ET, re
CAT='Legiones Astartes.cat'; GST='Prohammer 30k.gst'
raw=Path(CAT).read_text(encoding='utf-8')
ct=ET.parse(CAT); r=ct.getroot(); ns=r.tag.split('}')[0].strip('{'); C=lambda x:f'{{{ns}}}{x}'
gt=ET.parse(GST); gr=gt.getroot(); gns=gr.tag.split('}')[0].strip('{'); G=lambda x:f'{{{gns}}}{x}'
def f(root,i): return next((e for e in root.iter() if e.get('id')==i),None)
def line(e):
    if e is None:return 'MISSING'
    tag=e.tag.rsplit('}',1)[-1]
    attrs=' | '.join(f'{k}={e.get(k)}' for k in ('id','name','type','hidden','targetId','field','value','scope','childId','primary') if e.get(k)!=None)
    return tag+' | '+attrs
def desc(e,nsf=C):
    d=e.find(nsf('description'));return (d.text or '') if d is not None else ''
def snippet(token, radius=1800):
    i=raw.find(token)
    if i<0:return 'NOT FOUND'
    return raw[max(0,i-radius):min(len(raw),i+radius)].replace('><','>\n<')

out=[f'CAT={r.get("revision")} GST={gr.get("revision")}']

for rid in ['r25-rite-xv-0-the-axis-of-dissolution','r25-rite-xv-1-the-guard-of-the-crimson-king','r25-rite-xv-2-the-fellowships-of-prospero']:
    e=f(r,rid); out+=['\n=== '+rid+' STRUCTURE ===',line(e)]
    if e is not None:
        for x in e.iter():
            tag=x.tag.rsplit('}',1)[-1]
            if tag in ('rule','constraint','modifier','condition','categoryLink','entryLink','selectionEntry','selectionEntryGroup'):
                out.append('  '+line(x)+((' DESC='+desc(x)[:1000]) if tag=='rule' else ''))

for rid in [
    'r45-tactical-ts-brother','r45-ts-tactical-brotherhood',
    'r45-veteran-unit-ts-brother','r45-veteran-unit-ts-brother-fellow',
    'r45-terminator-unit-ts-brother','r45-terminator-unit-ts-brother-fellow',
    'r41-unit-xv-0-sekhmet-terminator-cabal','r41-unit-xv-11-xv-magnus-the-red-the-crimson-king',
    'r18-ts-guard-praetor-ml3','r45-ts-trans-unit'
]:
    e=f(r,rid); out+=['\n=== '+rid+' ===',line(e)]
    if e is not None:
        for x in e.iter():
            tag=x.tag.rsplit('}',1)[-1]
            if tag in ('rule','constraint','modifier','condition','categoryLink','entryLink','selectionEntry','cost'):
                nm=(x.get('name') or '').lower()
                if tag in ('rule','constraint','modifier','condition','categoryLink','cost') or 'brother' in nm or 'transponder' in nm or 'mastery' in nm:
                    out.append('  '+line(x)+((' DESC='+desc(x)[:900]) if tag=='rule' else ''))

out.append('\n=== GST XV RITE RELATED ===')
for e in gr.iter():
    eid=e.get('id') or ''
    if any(s in eid for s in ('r18-ts','r19-ts','r20-ts','r21-ts')) or e.get('targetId') in ('cat-hq','cat-elites','cat-troops','cat-fast','cat-fortification'):
        tag=e.tag.rsplit('}',1)[-1]
        if tag in ('categoryLink','constraint','modifier','condition','categoryEntry'):
            out.append(line(e))

out.append('\n=== RAW SNIPPETS ===')
for token in ['id="r45-tactical-ts-brother"','id="r45-veteran-unit-ts-brother-fellow"','id="r45-terminator-unit-ts-brother-fellow"',
              'id="r41-unit-xv-0-sekhmet-terminator-cabal"','id="r41-unit-xv-11-xv-magnus-the-red-the-crimson-king"',
              'id="r18-ts-guard-praetor-ml3"','id="r45-ts-trans-unit"']:
    out += ['\n--- '+token+' ---', snippet(token)]

Path('inspection-r24-ts-rites-raw.txt').write_text('\n'.join(out),encoding='utf-8')
print('\n'.join(out[:4000]))
