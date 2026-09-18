from pathlib import Path
import xml.etree.ElementTree as ET
CAT='Legiones Astartes.cat'; GST='Prohammer 30k.gst'
ct=ET.parse(CAT); r=ct.getroot(); ns=r.tag.split('}')[0].strip('{'); C=lambda x:f'{{{ns}}}{x}'
gt=ET.parse(GST); gr=gt.getroot(); gns=gr.tag.split('}')[0].strip('{'); G=lambda x:f'{{{gns}}}{x}'
def f(root,i): return next((e for e in root.iter() if e.get('id')==i),None)
def line(e):
    if e is None:return 'MISSING'
    tag=e.tag.rsplit('}',1)[-1]
    return tag+' | '+' | '.join(f'{k}={e.get(k)}' for k in ('id','name','type','hidden','targetId','field','value','scope','childId') if e.get(k)!=None)
def dump(e,maxd=8):
    out=[]
    def rec(x,d):
        tag=x.tag.rsplit('}',1)[-1]
        if tag in ('selectionEntry','selectionEntryGroup','entryLink','constraint','modifier','condition','conditionGroup','rule','categoryLink','cost'):
            out.append('  '*d+line(x))
            if tag=='rule':
                de=x.find(C('description'))
                if de is not None and de.text: out.append('  '*(d+1)+'DESC='+de.text[:900].replace('\\n',' '))
        if d<maxd:
            for ch in list(x): rec(ch,d+1)
    if e is not None: rec(e,0)
    else: out.append('MISSING')
    return out

out=[f'CAT={r.get("revision")} GST={gr.get("revision")}']
for i in ['tactical-unit','tactical-squad-weapons','tactical-unit-weapons','tactical-marine-bolter','tactical-marine-bolt-pistol',
          'r45-ts-tactical-brotherhood','r19-ts-tactical-brotherhood-disciplines','r19-ts-tactical-brotherhood-powers']:
    out += ['\\n=== '+i+' ==='] + dump(f(r,i),10)

out.append('\\n=== TACTICAL DIRECT GROUPS ===')
t=f(r,'tactical-unit')
if t:
    for g in list(t.find(C('selectionEntryGroups')) or []):
        out.append(line(g))
        for m in g.iter(C('modifier')):
            out.append('  '+line(m))
            for c in m.iter(C('condition')):out.append('    '+line(c))

out.append('\\n=== TACTICAL ENTRIES NAMED BOLTER/BOLT PISTOL ===')
if t:
    for e in t.iter():
        nm=(e.get('name') or '').lower()
        if nm in ('bolter','bolt pistol') or 'bolters + bolt pistols' in nm or 'chainsword' in nm:
            out.append(line(e))
            for c in e.iter(C('constraint')): out.append('  '+line(c))
            for m in e.iter(C('modifier')):
                out.append('  '+line(m))
                for cc in m.iter(C('condition')): out.append('    '+line(cc))

for i in ['r25-rite-xv-0-the-axis-of-dissolution','r25-rite-xv-1-the-guard-of-the-crimson-king','r25-rite-xv-2-the-fellowships-of-prospero']:
    out += ['\\n=== RITE '+i+' ==='] + dump(f(r,i),8)

out.append('\\n=== FORCE FAST/HQ/ELITES LINKS ===')
force=f(gr,'force-standard')
if force:
    for x in list(force.find(G('categoryLinks')) or []):
        if x.get('targetId') in ('cat-hq','cat-elites','cat-fast','cat-troops','cat-fortification') or 'ts' in (x.get('id') or ''):
            out.append(line(x))
            for c in x.iter(G('constraint')): out.append('  '+line(c))
            for m in x.iter(G('modifier')):
                out.append('  '+line(m))
                for cc in m.iter(G('condition')): out.append('    '+line(cc))

out.append('\\n=== R18/R19 TS FORCE MODIFIERS ANYWHERE GST ===')
for e in gr.iter():
    eid=e.get('id') or ''
    if 'r18-ts' in eid or 'r19-ts' in eid:
        out.append(line(e))

Path('inspection-r20-ts-rite-tactical-errors.txt').write_text('\\n'.join(out),encoding='utf-8')
print('\\n'.join(out[:2500]))
