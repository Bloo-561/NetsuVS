# Draws Cecilia's gold-lightning beam effect for 5B (Narmaya-style horizontal beam).
# beam(x0, x1, cy, half, seed, bolts, fade) -> RGBA image on the 1024 sprite canvas; slash(x0, x1, cy) -> thin draw-slash line.
# x/y are canvas pixels (ground point x=496, floor y=620). Save the result to actors/cecilia/Sprites/fx/<sprite>_fx.png.
import numpy as np
from PIL import Image, ImageDraw, ImageFilter
W=H=1024
WHITE=(255,252,235); PALE=(255,236,150); GOLD=(255,206,60); AMBER=(236,140,24); DARK=(110,62,12)
def beam(x0,x1,cy,half,seed=0,bolts=2,fade=0.0):
    r=np.random.default_rng(seed)
    img=Image.new('RGBA',(W,H),(0,0,0,0))
    L=x1-x0
    # row lengths: centre rows longest -> spear tip; small per-row noise in horizontal runs
    rows=np.arange(int(cy-half*1.3),int(cy+half*1.3)+1)
    layer=np.zeros((H,W,4),float)
    def put(y,xa,xb,col,a):
        xa=int(max(0,xa)); xb=int(min(W,xb))
        if xb<=xa or not(0<=y<H): return
        seg=layer[y,xa:xb]
        na=a*np.ones(xb-xa); # composite over
        seg[:, :3]=seg[:, :3]*(1-na[:,None])+np.array(col)[None,:]/255*na[:,None]
        seg[:,3]=np.maximum(seg[:,3],na)
    noise=np.cumsum(r.normal(0,0.6,len(rows)))
    for i,y in enumerate(rows):
        d=abs(y-cy)/half
        if d>1.3: continue
        reach=L*(1-0.55*d**1.6)+noise[i]*6+r.normal(0,8)
        start=x0+L*0.04*d+r.normal(0,4)
        if d<0.18: col,a=WHITE,1.0
        elif d<0.38: col,a=PALE,0.97
        elif d<0.7: col,a=GOLD,0.92
        elif d<1.0: col,a=AMBER,0.75
        else: col,a=AMBER,0.35
        put(y,start,x0+reach,col,a*(1-fade))
    # inner light streaks
    for k in range(10):
        y=int(cy+r.normal(0,half*0.5)); a0=x0+r.uniform(0,L*0.5); put(y,a0,a0+r.uniform(60,L*0.6),WHITE,0.9*(1-fade))
    # dark speed-line spikes along the top and bottom edges
    for side in (-1,1):
        for k in range(9):
            yb=cy+side*half*r.uniform(0.85,1.25); th=r.uniform(1.5,4.0)
            a0=x0+r.uniform(0.05,0.75)*L; ln=r.uniform(50,260)
            for dy in range(-int(th),int(th)+1):
                taper=1-abs(dy)/(th+0.5)
                put(int(yb+dy),a0+ln*(1-taper)*0.5,a0+ln*(0.5+taper*0.5),DARK,0.85*(1-fade))
    # lightning bolts
    out=Image.fromarray((np.clip(layer,0,1)*255).astype(np.uint8),'RGBA')
    d=ImageDraw.Draw(out)
    for k in range(bolts):
        pts=[]; x=x0+L*0.08
        y=cy+r.normal(0,half*0.3); end=x0+L*r.uniform(0.55,0.85)
        while x<end:
            pts.append((x,y)); x+=r.uniform(6,16); y=float(np.clip(y+r.normal(0,half*0.18),cy-half*0.6,cy+half*0.6))
        if len(pts)>1:
            d.line(pts,fill=GOLD+(int(200*(1-fade)),),width=3); d.line(pts,fill=WHITE+(int(255*(1-fade)),),width=1)
    # soft outer glow
    glow=out.filter(ImageFilter.GaussianBlur(6)); ga=np.asarray(glow).astype(float); ga[...,3]*=0.55
    g=Image.fromarray(ga.astype(np.uint8),'RGBA'); g.alpha_composite(out)
    return g
def slash(x0,x1,cy):
    img=Image.new('RGBA',(W,H),(0,0,0,0)); d=ImageDraw.Draw(img)
    ts=np.linspace(0,1,40)
    top=[(x0+(x1-x0)*t, cy-5*np.sin(np.pi*t)) for t in ts]; bot=[(x0+(x1-x0)*t, cy+5*np.sin(np.pi*t)) for t in ts[::-1]]
    d.polygon(top+bot,fill=GOLD+(235,))
    top=[(x0+(x1-x0)*t, cy-2*np.sin(np.pi*t)) for t in ts]; bot=[(x0+(x1-x0)*t, cy+2*np.sin(np.pi*t)) for t in ts[::-1]]
    d.polygon(top+bot,fill=WHITE+(255,))
    g=img.filter(ImageFilter.GaussianBlur(4)); g.alpha_composite(img); return g
