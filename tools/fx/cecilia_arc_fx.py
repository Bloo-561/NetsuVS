import numpy as np
from PIL import Image, ImageDraw, ImageFilter
from cecilia_slash_fx import *
def arc_fx(cx,cy,R,a0,a1,thick,seed,bolts=3,sparks=10,fade=0.0):
    rng=np.random.default_rng(seed)
    glow=Image.new('RGBA',(W,H)); g=ImageDraw.Draw(glow); sharp=Image.new('RGBA',(W,H)); s=ImageDraw.Draw(sharp)
    n=70; t=np.linspace(0,1,n); ang=np.radians(a0+(a1-a0)*t)
    hw=thick*np.sin(np.pi*t)**0.6*(0.3+0.7*t)
    A=lambda a:int(255*a*(1-fade))
    def lens(sc,col,a,dr):
        outer=[(cx+(R+h*sc)*np.cos(q),cy+(R+h*sc)*np.sin(q)) for q,h in zip(ang,hw)]
        inner=[(cx+(R-h*sc*0.5)*np.cos(q),cy+(R-h*sc*0.5)*np.sin(q)) for q,h in zip(ang,hw)][::-1]
        dr.polygon(outer+inner,fill=col+(A(a),))
    lens(2.4,AMBER,0.5,g); lens(1.5,GOLD,0.8,g); lens(1.0,GOLD,1,s); lens(0.6,PALE,1,s); lens(0.28,WHITE,1,s)
    P=lambda i,dr=0:(cx+(R+dr)*np.cos(ang[i]),cy+(R+dr)*np.sin(ang[i]))
    for k in range(bolts):
        i0=rng.integers(10,n//2); i1=rng.integers(n//2,n-3)
        p0=P(i0,rng.normal(0,thick)); p1=P(i1,rng.choice([-1,1])*rng.uniform(thick,thick*2.2))
        bolt(g,p0,p1,rng,GOLD+(A(0.9),),4); bolt(s,p0,p1,rng,WHITE+(A(1),),1)
    for k in range(sparks):
        i=rng.integers(n//3,n); x,y=P(i,thick*0.8); q=ang[i]+rng.uniform(-0.6,0.6); L=rng.uniform(6,16)
        s.line([(x,y),(x+np.cos(q)*L,y+np.sin(q)*L)],fill=PALE+(A(1),),width=1)
    glow=glow.filter(ImageFilter.GaussianBlur(3)); glow.alpha_composite(sharp); return glow
