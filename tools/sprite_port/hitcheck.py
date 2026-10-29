"""Draw a move's hitboxes over its new sprites (green hurt, red attack, blue proximity, yellow pushbox).
   python hitcheck.py cecilia 48_CEC_5A ...      -> checks/<char>/hit_<anim>.png"""
import sys, os, re
from PIL import Image, ImageDraw, ImageFont
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from build import Port, PROJ
from tres import Tres
from analyze import font as _font
font=_font(12)
UNITS_PER_PX=None
def hitbox_file(char, name):
    return os.path.join(PROJ,'actors',char,'Hitboxes',name+'.tres')
def read_boxes(path):
    t=Tres(open(path,encoding='utf-8').read()); out=[]
    ids=[x for x in re.findall(r'SubResource\("([^"]+)"\)', t.res_get('Hitboxes') or '')]
    for i in ids:
        s=t.sub_get(i); body='\n'.join(s[2])
        c=re.search(r'Center = Vector2i\((-?\d+), (-?\d+)\)',body); z=re.search(r'Size = Vector2i\((-?\d+), (-?\d+)\)',body)
        ty=re.search(r'HitboxType = (\d+)',body)
        if c and z: out.append((int(ty.group(1)) if ty else 0,int(c.group(1)),int(c.group(2)),int(z.group(1)),int(z.group(2))))
    pb=t.res_get('Pushbox')
    if pb:
        e=t.ext_by_id(re.search(r'ExtResource\("([^"]+)"\)',pb).group(1))
        pp=os.path.join(PROJ,e['path'].replace('res://',''))
        if os.path.exists(pp):
            b='\n'.join(open(pp,encoding='utf-8').read().split('\n'))
            c=re.search(r'Center = Vector2i\((-?\d+), (-?\d+)\)',b); z=re.search(r'Size = Vector2i\((-?\d+), (-?\d+)\)',b)
            if c and z: out.append((9,int(c.group(1)),int(c.group(2)),int(z.group(1)),int(z.group(2))))
    return out
COL={0:(0,255,0),1:(255,40,40),2:(80,120,255),9:(255,230,0)}
def hit_states(p, name):
    path=os.path.join(PROJ,'actors',p.char,'AnimationData',name+'_AnimData.tres')
    t=Tres(open(path,encoding='utf-8').read()); hs=[]
    for i in re.findall(r'SubResource\("([^"]+)"\)', t.res_get('Hitboxes') or ''):
        s=t.sub_get(i); body='\n'.join(s[2])
        at=re.search(r'AtFrame = (\d+)',body); st=re.search(r'animationStage = (\d+)',body); hd=re.search(r'HitboxData = ExtResource\("([^"]+)"\)',body)
        e=t.ext_by_id(hd.group(1)); hs.append((int(at.group(1)) if at else 0,int(st.group(1)) if st else 0,e['path'].split('/')[-1].replace('.tres','')))
    return sorted(hs), int(t.res_get('Duration') or 0)
def check(p, name, scale=0.45):
    upx=p.m['game']['pixel_size']*10000
    anim=p.m['animations'][name]; keys=p.keys_of(anim)
    hs,dur=hit_states(p,name)
    # one cell per hitbox state, showing the sprite key active at that frame
    cells=[]
    for at,stage,hb in hs:
        k=[k for k in keys if k['at']<=at][-1]
        md=p.modifier(k['f'],k); c,o,_=p.frame(k['f'])
        boxes=read_boxes(hitbox_file(p.char,hb))
        X0,X1,Y0,Y1=-700,900,-60,800
        Wd,Ht=int((X1-X0)*scale),int((Y1-Y0)*scale)
        img=Image.new('RGBA',(Wd,Ht+30),(70,70,78,255)); d=ImageDraw.Draw(img,'RGBA')
        im=Image.fromarray(c,'RGBA')
        if md['rot']:
            R=1800; big=Image.new('RGBA',(2*R,2*R),(0,0,0,0)); big.paste(im,(md['off'][0]+R,R-(md['off'][1]+c.shape[0])),im)
            big=big.rotate(md['rot'],resample=Image.BICUBIC,center=(R,R)).crop((R+X0,R-Y1,R+X1,R-Y0)).resize((Wd,Ht),Image.LANCZOS)
            img.alpha_composite(big)
        else:
            im=im.resize((max(1,int(c.shape[1]*scale)),max(1,int(c.shape[0]*scale))),Image.LANCZOS)
            img.alpha_composite(im,(int((md['off'][0]-X0)*scale),int((Y1-(md['off'][1]+c.shape[0]))*scale)))
        fy=int(Y1*scale); d.line([(0,fy),(Wd,fy)],fill=(0,210,210,255)); d.line([(int(-X0*scale),fy-10),(int(-X0*scale),fy+10)],fill=(255,70,70,255))
        lay=Image.new('RGBA',img.size,(0,0,0,0)); dl=ImageDraw.Draw(lay)
        for ty,cx,cy,w,h in boxes:
            x0=(cx-w/2)/upx; x1=(cx+w/2)/upx; y0=(cy-h/2)/upx; y1=(cy+h/2)/upx
            col=COL.get(ty,(255,255,255))
            dl.rectangle([int((x0-X0)*scale),int((Y1-y1)*scale),int((x1-X0)*scale),int((Y1-y0)*scale)],outline=col+(230,),fill=col+(45,),width=2)
        img.alpha_composite(lay)
        d.text((3,Ht+3),'@%d st%d %s | %s'%(at,stage,hb,k['f']),fill=(255,255,0,255),font=font)
        cells.append(img)
    W=sum(c.width for c in cells); out=Image.new('RGB',(W,cells[0].height)); x=0
    for c in cells: out.paste(c,(x,0)); x+=c.width
    od=os.path.join(os.path.dirname(os.path.abspath(__file__)),'checks',p.char); os.makedirs(od,exist_ok=True)
    out.save(os.path.join(od,'hit_'+name+'.png')); return out.size
if __name__=='__main__':
    p=Port(sys.argv[1])
    for n in sys.argv[2:]: print(n,check(p,n))
