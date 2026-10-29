"""Filmstrip check: every key of an animation drawn in the same world space (floor = cyan, origin = red tick),
plus an onion-skin of all keys on the right.   python strip.py cecilia 48_CEC_5A 49_CEC_5B ..."""
import sys, os
from PIL import Image, ImageDraw, ImageFont
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from build import Port
from analyze import font as _font
font=_font(12)
def render(p, mods, X0, Y1, Wd, Ht, scale, alpha=1.0):
    img=Image.new('RGBA',(Wd,Ht),(0,0,0,0))
    for md in mods:
        c,o,_=p.frame(md['sprite']); off=md['off']
        im=Image.fromarray(c,'RGBA')
        if md['rot']:
            # draw unrotated on a canvas big enough for the un-rotated rect, rotate about the origin, crop back
            vals=[off[0],off[1],off[0]+c.shape[1],off[1]+c.shape[0],X0,Y1,X0+Wd/scale,Y1-Ht/scale]
            R=int(max(abs(v) for v in vals)*1.5)+8
            big=Image.new('RGBA',(2*R,2*R),(0,0,0,0))
            big.paste(im,(int(off[0]+R),int(R-(off[1]+c.shape[0]))),im)
            big=big.rotate(md['rot'],resample=Image.BICUBIC,center=(R,R))
            big=big.crop((int(R+X0),int(R-Y1),int(R+X0+Wd/scale),int(R-Y1+Ht/scale)))
        else:
            big=Image.new('RGBA',(int(Wd/scale)+2,int(Ht/scale)+2),(0,0,0,0))
            big.paste(im,(int(off[0]-X0),int(Y1-(off[1]+c.shape[0]))),im)
        big=big.resize((Wd,Ht),Image.LANCZOS)
        if alpha<1:
            a=big.split()[3].point(lambda v:int(v*alpha)); big.putalpha(a)
        img.alpha_composite(big)
    return img
def strip(p, name, scale=0.4):
    anim=p.m['animations'][name]; keys=p.keys_of(anim)
    seq=[]
    for k in keys:
        ms=[p.modifier(k['f'],k)]
        if k.get('fx'): ms.append(p.modifier(k['fx'],p.fx_key(k),True))
        seq.append((k,ms))
    boxes=[]
    import math
    for _,ms in seq:
        for md in ms:
            c,o,_=p.frame(md['sprite']); off=md['off']; w,h=c.shape[1],c.shape[0]
            th=math.radians(md['rot']); cs,sn=math.cos(th),math.sin(th)
            pts=[(off[0]+dx,off[1]+dy) for dx in (0,w) for dy in (0,h)]
            pts=[(cs*x-sn*y, sn*x+cs*y) for x,y in pts]
            boxes.append((min(q[0] for q in pts),min(q[1] for q in pts),max(q[0] for q in pts),max(q[1] for q in pts)))
    X0=min(min(b[0] for b in boxes),p.REAR_X)-40; X1=max(max(b[2] for b in boxes),p.FRONT_X)+40
    Y0=min(min(b[1] for b in boxes),0)-30; Y1=max(b[3] for b in boxes)+30
    Wd,Ht=int((X1-X0)*scale),int((Y1-Y0)*scale)
    n=len(seq); out=Image.new('RGBA',(Wd*(n+1),Ht+18),(84,84,92,255)); d=ImageDraw.Draw(out)
    fy=int(Y1*scale); ox=int(-X0*scale)
    for i,(k,ms) in enumerate(seq):
        out.alpha_composite(render(p,ms,X0,Y1,Wd,Ht,scale),(i*Wd,0))
        d.line([(i*Wd,fy),(i*Wd+Wd,fy)],fill=(0,210,210,255)); d.line([(i*Wd+ox,fy-10),(i*Wd+ox,fy+10)],fill=(255,70,70,255))
        d.text((i*Wd+3,Ht+2),'%s @%d%s'%(k['f'],k['at'],(' r%d'%k['rot']) if k.get('rot') else ''),fill=(255,255,0,255),font=font)
    for k,ms in seq: out.alpha_composite(render(p,ms,X0,Y1,Wd,Ht,scale,alpha=0.35),(n*Wd,0))
    d.line([(n*Wd,fy),(n*Wd+Wd,fy)],fill=(0,210,210,255)); d.line([(n*Wd+ox,fy-10),(n*Wd+ox,fy+10)],fill=(255,70,70,255))
    d.text((n*Wd+3,Ht+2),'onion skin',fill=(255,255,255,255),font=font)
    od=os.path.join(os.path.dirname(os.path.abspath(__file__)),'checks',p.char); os.makedirs(od,exist_ok=True)
    out.convert('RGB').save(os.path.join(od,'strip_'+name+'.png')); return out.size
if __name__=='__main__':
    p=Port(sys.argv[1])
    for n in sys.argv[2:]: print(n, strip(p,n))
