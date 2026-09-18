from pathlib import Path
import xml.etree.ElementTree as ET
CAT='Legiones Astartes.cat'; GST='Prohammer 30k.gst'
ct=ET.parse(CAT); r=ct.getroot(); ns=r.tag.split('}')[0].strip('{'); C=lambda x:f'{{{ns}}}{x}'
gt=ET.parse(GST); gr=gt.getroot(); gns=gr.tag.split('}')[0].strip('{'); G=lambda x:f'{{{gns}}}{x}'
def f(root,i): return next((e for e in root.iter() if e.get('id')==i),None)
def line(e):
    if e is None:return 'MISSING'
    return e.tag.rsplit('}',1)[-1]+' | '+' | '.join(f'{k}={e.get(k)}' for k in ('id','name','type','hidden','targetId','field','value','scope','childId','primary') if e.get(k)!=None)
def dump(e,nsf=C,maxd=7):
    out=[]
    def rec(x,d):
        tag=x.tag.rsplit('}',1)[-1]
        if tag in ('selectionEntry','selectionEntryGroup','entryLink','constraint','modifier','condition','conditionGroup','categoryLink','cost'):
            out.append('  '*d+line(x))
        if d<maxd:
            for ch in list(x): rec(ch,d+1)
    if e is not None: rec(e,0)
    else: out.append('MISSING')
    return out

out=[f'CAT={r.get("revision")} GST={gr.get("revision")}']

for i in ['tactical-unit','r45-tactical-ts-brother','r19-ts-tactical-brotherhood-disciplines','r19-ts-tactical-brotherhood-powers']:
    out+=['\n=== '+i+' ===']+dump(f(r,i),C,8)

sek=f(r,'r41-unit-xv-0-sekhmet-terminator-cabal')
out+=['\n=== SEKHMET ===']+dump(sek,C,8)

mag=f(r,'r41-unit-xv-11-xv-magnus-the-red-the-crimson-king')
out+=['\n=== MAGNUS ===']+dump(mag,C,5)

pra=f(r,'hq-praetor')
out+=['\n=== PRAETOR GUARD ML3 ===']+dump(f(r,'r18-ts-guard-praetor-ml3'),C,5)

trans=f(r,'r45-ts-trans-unit')
out+=['\n=== TRANS UNIT ===']+dump(trans,C,5)

# Force category links
force=f(gr,'force-standard')
out+=['\n=== FORCE LINKS ===']
if force:
    for x in list(force.find(G('categoryLinks')) or []):
        if x.get('targetId') in ('cat-hq','cat-troops','cat-elites','cat-fast') or 'ts' in (x.get('id') or ''):
            out.append(line(x))
            for m in x.iter(G('modifier')):
                out.append('  '+line(m))
                for c in m.iter(G('condition')): out.append('    '+line(c))
            for c in x.iter(G('constraint')): out.append('  '+line(c))

Path('inspection-r25-ts-guard-discipline.txt').write_text('\n'.join(out),encoding='utf-8')
print('\n'.join(out[:3000]))
