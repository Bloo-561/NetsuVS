import json, os, sys, numpy as np
from PIL import Image, ImageDraw, ImageFont
HERE=os.path.dirname(os.path.abspath(__file__))
char=sys.argv[1]; c=json.load(open(os.path.join(HERE,'manifests',char+'.json')))
an=json.load(open(os.path.join(HERE,'analysis',char+'.json')))
sys.path.insert(0,HERE)
from analyze import source_root
root=source_root(c); ref=an['ref']
BASE=250/ref['h']          # preview at 1x-old size (250 px standing) to keep sheets small
from analyze import font as _font
font=_font(11)
refimg=Image.open(os.path.join(root,c['reference'])).convert('RGBa')
rs=BASE; refs=refimg.resize((int(refimg.width*rs),int(refimg.height*rs)),Image.LANCZOS).convert('RGBA')
ra=np.array(refs); ghost=np.zeros_like(ra); ghost[...,:3]=(90,200,255); ghost[...,3]=(ra[...,3]>128)*70
ghost=Image.fromarray(ghost)
def norm(rel,m):
    s=m['scale'] or 1.0; k=BASE/s
    im=Image.open(os.path.join(root,rel)).convert('RGBa')
    im=im.resize((max(1,int(im.width*k)),max(1,int(im.height*k))),Image.LANCZOS).convert('RGBA')
    return im,k
cells=[]
for rel,m in an['frames'].items():
    if m.get('empty'): continue
    im,k=norm(rel,m)
    cells.append((rel,m,im,k))
CW,CH=300,330; cols=6
rows=(len(cells)+cols-1)//cols
sh=Image.new('RGB',(cols*CW,rows*CH),(105,105,112)); d=ImageDraw.Draw(sh)
for i,(rel,m,im,k) in enumerate(cells):
    x0=(i%cols)*CW; y0=(i//cols)*CH; floor=y0+CH-40
    # ghost reference: feet on floor, rear foot at x0+40
    gx=x0+40-int(ref['rear_x']*BASE); gy=floor-int(ref['bot']*BASE)
    sh.paste(ghost,(gx,gy),ghost)
    px=x0+40-int(m['rear_x']*k); py=floor-int(m['bot']*k)
    # crop to cell
    tmp=Image.new('RGBA',(CW,CH),(0,0,0,0)); tmp.paste(im,(px-x0,py-y0),im)
    sh.paste(tmp,(x0,y0),tmp)
    d.line([(x0,floor),(x0+CW,floor)],fill=(0,220,220))
    d.text((x0+3,y0+CH-36),rel.split('/')[-2][:22]+'/'+rel.split('/')[-1][:24],fill=(255,255,0),font=font)
    sc=m['scale']; d.text((x0+3,y0+CH-22),f"s={sc if sc is None else round(sc,3)} {m.get('scale_how')}",fill=(255,255,255),font=font)
out=os.path.join(HERE,'checks'); os.makedirs(out,exist_ok=True)
# split into pages of 4 rows
for p in range(0,rows,4):
    sh.crop((0,p*CH,cols*CW,min(rows,p+4)*CH)).save(os.path.join(out,f'{char}_scale_{p//4}.png'))
print(rows, 'rows')
