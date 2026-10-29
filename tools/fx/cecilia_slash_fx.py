import numpy as np
from PIL import Image, ImageDraw, ImageFilter
W=H=1024
WHITE=(255,252,235); PALE=(255,236,150); GOLD=(255,206,60); AMBER=(236,140,24)
def bolt(d,p0,p1,rng,col,w,jit=6,seg=7):
    pts=[p0]
    for i in range(1,seg):
        t=i/seg; pts.append((p0[0]+(p1[0]-p0[0])*t+rng.normal(0,jit*0.4), p0[1]+(p1[1]-p0[1])*t+rng.normal(0,jit)))
    pts.append(p1); d.line(pts,fill=col,width=w,joint='curve'); return pts
def slash_fx(x0,x1,cy,thick,curve,seed,bolts=3,fade=0.0,core=True,sparks=8):
    rng=np.random.default_rng(seed)
    glow=Image.new('RGBA',(W,H)); g=ImageDraw.Draw(glow)
    sharp=Image.new('RGBA',(W,H)); s=ImageDraw.Draw(sharp)
    n=60; xs=np.linspace(x0,x1,n); t=np.linspace(0,1,n)
    ys=cy-curve*np.sin(np.pi*t)            # gentle crescent along blade path
    hw=thick*np.sin(np.pi*t)**0.7*(0.35+0.65*t)  # thin at hand, fat near tip, sharp ends
    A=lambda a:int(255*a*(1-fade))
    def lens(scale,col,a,dr):
        top=[(x,y-h*scale) for x,y,h in zip(xs,ys,hw)]; bot=[(x,y+h*scale*0.6) for x,y,h in zip(xs,ys,hw)][::-1]
        dr.polygon(top+bot,fill=col+(A(a),))
    lens(2.6,AMBER,0.55,g); lens(1.6,GOLD,0.8,g)
    lens(1.0,GOLD,1.0,s); lens(0.6,PALE,1.0,s)
    if core: lens(0.28,WHITE,1.0,s)
    for k in range(bolts):
        i0=rng.integers(5,n//2); i1=rng.integers(n//2,n-3)
        p0=(xs[i0],ys[i0]+rng.normal(0,thick)); p1=(xs[i1]+rng.uniform(5,25),ys[i1]+rng.choice([-1,1])*rng.uniform(thick,thick*2.5))
        bolt(g,p0,p1,rng,GOLD+(A(0.9),),4); bolt(s,p0,p1,rng,WHITE+(A(1),),1)
    for k in range(sparks):
        i=rng.integers(n//3,n); x,y=xs[i],ys[i]; ang=rng.uniform(-0.9,0.9); L=rng.uniform(6,18)
        p1=(x+np.cos(ang)*L*1.5,y+np.sin(ang)*L)
        s.line([(x,y),p1],fill=PALE+(A(1),),width=1)
    glow=glow.filter(ImageFilter.GaussianBlur(3))
    glow.alpha_composite(sharp); return glow
O='/mnt/user-data/outputs/b5v3/'
cy=453
f3=slash_fx(565,765,cy,8,8,11,bolts=3,sparks=8)
f4=slash_fx(560,770,cy-2,12,12,12,bolts=5,sparks=14)
f5=slash_fx(580,765,cy+2,7,11,13,bolts=2,fade=0.55,core=False,sparks=5)
for n,im in [('5b3',f3),('5b4',f4),('5b5',f5)]: im.save(O+f'{n}_fx.png')
tiles=[]
for i in range(1,7):
    bg=Image.new('RGBA',(W,H),(40,44,56,255)); bg.alpha_composite(Image.open(f'n5/5b{i}.png').convert('RGBA'))
    if i in (3,4,5): bg.alpha_composite(Image.open(O+f'5b{i}_fx.png'))
    tiles.append(bg.crop((370,350,840,630)).resize((705,420),Image.NEAREST))
w,h=tiles[0].size; out=Image.new('RGBA',(w*3,h*2))
for i,t in enumerate(tiles): out.paste(t,((i%3)*w,(i//3)*h))
out.save('/home/claude/5b_slash_fx.png')
