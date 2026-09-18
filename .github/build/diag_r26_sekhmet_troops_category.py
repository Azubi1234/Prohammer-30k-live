from pathlib import Path
import xml.etree.ElementTree as ET
CAT='Legiones Astartes.cat'
r=ET.parse(CAT).getroot(); ns=r.tag.split('}')[0].strip('{'); C=lambda x:f'{{{ns}}}{x}'
def f(i): return next((e for e in r.iter() if e.get('id')==i),None)
def line(e):
    if e is None:return 'MISSING'
    return e.tag.rsplit('}',1)[-1]+' | '+' | '.join(f'{k}={e.get(k)}' for k in ('id','name','type','hidden','targetId','field','value','scope','childId','primary') if e.get(k)!=None)
out=[f'CAT={r.get("revision")}']
sek=f('r41-unit-xv-0-sekhmet-terminator-cabal')
out+=['=== SEKHMET CATEGORY LINKS ===']
for x in sek.findall('.//'+C('categoryLink')):
    out.append(line(x))
    for m in x.findall('.//'+C('modifier')):
        out.append('  '+line(m))
        for c in m.findall('.//'+C('condition')):
            out.append('    '+line(c))
out+=['=== OTHER RITE CATEGORY SWITCH EXAMPLES ===']
for e in r.iter(C('selectionEntry')):
    # look for units with two primary category links where one is hidden by rite
    cls=e.findall('./'+C('categoryLinks')+'/'+C('categoryLink'))
    if len(cls)>=2:
        ids=[x.get('targetId') for x in cls]
        if 'cat-troops' in ids and ('cat-elites' in ids or 'cat-heavy' in ids or 'cat-fast' in ids):
            interesting=False
            for x in cls:
                if x.find(C('modifiers')) is not None:
                    interesting=True
            if interesting:
                out.append('UNIT '+line(e))
                for x in cls:
                    out.append('  '+line(x))
                    for m in x.findall('.//'+C('modifier')):
                        out.append('    '+line(m))
                        for c in m.findall('.//'+C('condition')):
                            out.append('      '+line(c))
                if len(out)>250: break
Path('inspection-r26-sekhmet-troops-category.txt').write_text('\n'.join(out),encoding='utf-8')
print('\n'.join(out[:250]))
