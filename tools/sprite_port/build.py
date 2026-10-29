"""SPRITE PORT: turns the source drawings into game sprites + AnimationData.

    python build.py <character> [animation ...] [--preview] [--dry]

Reads   manifests/<character>.json   (which drawing goes where, timing, nudges)
        analysis/<character>.json    (scale of every drawing; made by analyze.py)
Writes  actors/<character>/Sprites/v2/<frame>.png  (+ .import with mipmaps on)
        actors/<character>/AnimationData/<name>_AnimData.tres  (sprite timeline only; hitboxes kept)
        tools/sprite_port/checks/<character>/<name>.gif   with --preview
Key options: [frame, at, {dx, dy, rot, flipx, fx, fx_dx, fx_dy, fx_always, fx_sx, fx_reach}]: fx = an effect drawing shown
on top (only when the hit connects, unless fx_always), fx_dx/fx_dy move the effect alone, fx_sx stretches it along x from its
left edge (SpriteModifier.Scale), fx_reach stretches it so it ends that many world px in front of the character origin
(fx_strip: only two columns from the middle of the piece are stretched, from where the piece starts: no gap)
(Leticia's beams run across the whole screen from a short piece of the drawn beam: derive_leticia.py).
Every frame is trimmed to its picture and placed with its own Offset, so drawings of any canvas
size line up: feet on the floor, rear foot (or body centre in the air) on a fixed point.
Frame options (manifest "frames"): src, anchor (ground = rear foot, front, hips, body_ground, air,
lying, center + at, ref = placed like the reference drawing, like + "like": <frame> = placed like that
frame, pin + "pin": [x, y] = that canvas point on the character origin, the air point ("pin_at": "air") or "at",
attach + "attach": [frame, [x, y] on that frame's drawing, [x, y] on this one] = an effect held at that point),
scale / scale_like / scale_mul,
dx, dy, flip, rotate, erase [[x0,y0,x1,y1]...], breath, blink.
A src starting with derived/ is read from tools/sprite_port/derived/ (pictures made by a script).
"""
import json, os, sys, math, re, hashlib
import numpy as np, cv2
from PIL import Image, ImageDraw
from PIL import ImageFile; ImageFile.LOAD_TRUNCATED_IMAGES = True   # a damaged drawing loads what is there
HERE=os.path.dirname(os.path.abspath(__file__)); PROJ=os.path.abspath(os.path.join(HERE,'..','..'))
sys.path.insert(0,HERE)
from tres import Tres
from analyze import measure, source_root

# ---------------------------------------------------------------- image helpers
def rotated_layer(im, ox, oy, rot, px=0.0, py=0.0):
    """a sprite whose bottom-left is at world (ox, oy), turned by rot degrees about the world point (px, py)
    the way the engine turns a SpriteModifier about the character origin (previews only).
    Returns (image, left, top): its new bottom-left x and top y in world px (y up)."""
    w, h = im.size; t = math.radians(rot); c, s = math.cos(t), math.sin(t)
    dx, dy = ox + w / 2.0 - px, oy + h / 2.0 - py
    ncx, ncy = px + c * dx - s * dy, py + s * dx + c * dy
    r = im.rotate(rot, resample=Image.BICUBIC, expand=True)
    return r, ncx - r.width / 2.0, ncy + r.height / 2.0
def to_f(a):   # uint8 RGBA -> float premultiplied
    f=a.astype(np.float32)/255.0; f[...,:3]*=f[...,3:4]; return f
def to_u8(f):
    al=f[...,3:4]; rgb=np.where(al>1e-5,f[...,:3]/np.maximum(al,1e-5),0)
    return (np.clip(np.dstack([rgb,al]),0,1)*255+0.5).astype(np.uint8)
def resize_pm(f, k):
    h,w=f.shape[:2]; nw,nh=max(1,int(round(w*k))),max(1,int(round(h*k)))
    chans=[np.array(Image.fromarray(f[...,c]).resize((nw,nh),Image.LANCZOS)) for c in range(4)]
    out=np.dstack(chans); out=np.clip(out,0,1); out[...,:3]=np.minimum(out[...,:3],out[...,3:4]); return out
def rotate_pm(f, deg, cx, cy):
    """rotate (counter-clockwise on screen) about (cx,cy); grows the canvas so nothing is cut."""
    h,w=f.shape[:2]; M=cv2.getRotationMatrix2D((cx,cy),deg,1.0)
    c=np.array([[0,0,1],[w,0,1],[0,h,1],[w,h,1]],np.float32)@M.T
    x0,y0=np.floor(c.min(0)); x1,y1=np.ceil(c.max(0))
    M[0,2]-=x0; M[1,2]-=y0
    out=cv2.warpAffine(f,M,(int(x1-x0),int(y1-y0)),flags=cv2.INTER_CUBIC,borderMode=cv2.BORDER_CONSTANT,borderValue=0)
    out=np.clip(out,0,1); out[...,:3]=np.minimum(out[...,:3],out[...,3:4]); return out, M
def warp_rows(f, dy_rows):
    """vertical per-row displacement (rows move by -dy_rows[y] -> sample y+dy)."""
    h,w=f.shape[:2]
    mapy=(np.arange(h,dtype=np.float32)[:,None]+dy_rows[:,None]).repeat(w,1)
    mapx=np.arange(w,dtype=np.float32)[None,:].repeat(h,0)
    out=cv2.remap(f,mapx,mapy,cv2.INTER_LINEAR,borderMode=cv2.BORDER_CONSTANT,borderValue=0)
    return out

class Port:
    def __init__(self, char):
        self.char=char
        self.m=json.load(open(os.path.join(HERE,'manifests',char+'.json'),encoding='utf-8'))
        self.an=json.load(open(os.path.join(HERE,'analysis',char+'.json'),encoding='utf-8'))['frames']
        self.root=source_root(self.m); self.cache={}
        g=self.m['game']; self.fx=self.m.get('fx','none')
        ref_full=self.an[self.m['reference']]
        # output px per reference px: height_px / the reference's measured height, or "base" given directly
        # (drawings whose dark-pixel measurement doesn't cover the whole figure, e.g. a swimsuit)
        self.BASE=float(g['base']) if g.get('base') else g['height_px']/ref_full['h']
        ref=measure(to_u8(self.src(self.m['reference'])),self.fx)   # anchors measured like every other frame
        self.sprite_dir=os.path.join(PROJ,'actors',char,'Sprites',g.get('sprites_subdir','v2'))
        self.res_dir='res://actors/%s/Sprites/%s'%(char,g.get('sprites_subdir','v2'))
        # world anchor points (output px, y up) taken from the reference drawing
        r=ref; B=self.BASE
        ox=r['rear_x']+g.get('origin_from_rear',0.47)*(r['front_x']-r['rear_x'])
        self.ORIGIN_SRC=(ox,r['bot'])
        self.REAR_X=(r['rear_x']-ox)*B; self.FRONT_X=(r['front_x']-ox)*B
        self.AIR=((r['cx']-ox)*B,(r['bot']-r['cy'])*B)
        self.frames_done={}
        self.strips={}     # fx_strip layers: id -> the stretched columns (written with the frames)
    # ------------------------------------------------------------ source + transforms
    def src(self, rel):
        if rel not in self.cache:
            # 'derived/...' = a picture made from the drawings by a script (kept in tools/sprite_port/derived)
            path=os.path.join(HERE,rel) if rel.startswith('derived/') else os.path.join(self.root,rel)
            self.cache[rel]=to_f(np.array(Image.open(path).convert('RGBA')))
        return self.cache[rel]
    def scale_of(self, spec):
        if 'scale' in spec: return float(spec['scale'])
        if spec.get('anchor')=='like' and 'scale_like' not in spec: return self.scale_of(self.m['frames'][spec['like']])
        s=self.an.get(spec['src'],{}).get('scale')
        if spec.get('scale_like'): s=self.an[spec['scale_like']]['scale']
        if s is None: raise SystemExit('No scale for %s: set "scale" or "scale_like" in the manifest'%spec['src'])
        return s*spec.get('scale_mul',1.0)
    def frame(self, fid):
        """returns (u8 image trimmed, offset(x,y) for SpriteModifier, info)"""
        if fid in self.frames_done: return self.frames_done[fid]
        spec=self.m['frames'][fid]
        f=self.src(spec['src']).copy()
        if spec.get('blink'):                       # eye patch from another drawing (idle blink)
            b=spec['blink']; other=self.src(b['src'])
            dx,dy=b.get('shift',[0,0]); x0,y0,x1,y1=b['box']
            sh=cv2.warpAffine(other,np.float32([[1,0,dx],[0,1,dy]]),(f.shape[1],f.shape[0]))
            mk=np.zeros(f.shape[:2],np.float32); mk[y0:y1,x0:x1]=1
            mk=cv2.GaussianBlur(mk,(0,0),b.get('feather',6))[...,None]
            f=f*(1-mk)+sh*mk
        if spec.get('erase'):                        # list of [x0,y0,x1,y1] source rectangles to clear
            for x0,y0,x1,y1 in spec['erase']: f[y0:y1,x0:x1]=0
        if spec.get('breath') is not None:           # idle breathing: rows above the thighs move
            amp=float(spec['breath']); pts=spec.get('breath_rows')
            ys=np.arange(f.shape[0],dtype=np.float32)
            dyr=np.interp(ys,[p[0] for p in pts],[-amp*p[1] for p in pts]).astype(np.float32)
            f=warp_rows(f,dyr)
        if spec.get('flip'): f=f[:,::-1].copy()
        pin=None
        if spec.get('pin'):   # a registration point on the drawing's canvas (the pack's grounded anchor)
            pin=[float(spec['pin'][0]),float(spec['pin'][1])]
            if spec.get('flip'): pin[0]=f.shape[1]-pin[0]
        meas=measure(to_u8(f),self.fx)
        if spec.get('rotate'):
            cx,cy=meas['cx'],meas['cy']; f,M=rotate_pm(f,spec['rotate'],cx,cy); meas=measure(to_u8(f),self.fx)
            if pin: pin=list(np.array([pin[0],pin[1],1.0])@M.T)
        k=self.BASE/self.scale_of(spec)
        o=resize_pm(f,k)
        # anchor -> world
        mode=spec.get('anchor','ground'); A=None; W=None
        if mode=='ground':   A=(meas['rear_x']*k, meas['bot']*k); W=(self.REAR_X,0.0)
        elif mode=='front':  A=(meas['front_x']*k, meas['bot']*k); W=(self.FRONT_X,0.0)
        elif mode=='hips':   A=(meas['hip_x']*k, meas['bot']*k); W=(0.0,0.0)
        elif mode=='body_ground': A=(meas['cx']*k, meas['bot']*k); W=(self.AIR[0],0.0)   # walks/runs: body centre fixed, feet on floor
        elif mode=='air':    A=(meas['cx']*k, meas['cy']*k); W=self.AIR
        elif mode=='lying':  A=(meas['cx']*k, meas['bot']*k); W=(0.0,spec.get('sink',-4.0))
        elif mode=='center': A=(o.shape[1]/2, o.shape[0]/2); W=(0.0,0.0)
        elif mode=='ref':    # same mapping as the reference drawing (for pictures drawn on the reference canvas)
            A=(self.ORIGIN_SRC[0]*k, self.ORIGIN_SRC[1]*k); W=(0.0,0.0)
        elif mode=='pin':    # "pin": [x, y] on the drawing goes to the character origin (or "at"); packs with a shared anchor
            if not pin: raise SystemExit('anchor pin needs "pin": [x, y] for '+fid)
            A=(pin[0]*k, pin[1]*k); W=self.AIR if spec.get('pin_at')=='air' else (0.0,0.0)   # "pin_at": "air" = the air anchor
        elif mode=='like':   # same mapping as another frame: a picture on that frame's canvas (same top-left), e.g. an effect cut from it
            oi=self.frame(spec['like'])[2]; A=oi['A']; W=oi['W']
        elif mode=='attach': # "attach": [frame, [x, y] on that frame's drawing, [x, y] on this drawing]: an effect held at a fist
            ofid,opt,mpt=spec['attach']; ospec=self.m['frames'][ofid]; oi=self.frame(ofid)[2]
            ox_,oy_=float(opt[0]),float(opt[1])
            if ospec.get('flip'): ox_=self.src(ospec['src']).shape[1]-ox_
            ok=oi['k']; oA=oi['A']; oW=oi['W']
            W=(oW[0]+ox_*ok-oA[0], oW[1]-(oy_*ok-oA[1]))     # that drawing point, in world px
            px_,py_=float(mpt[0]),float(mpt[1])
            if spec.get('flip'): px_=f.shape[1]-px_
            A=(px_*k, py_*k)
        else: raise SystemExit('unknown anchor '+mode)
        if mode!='like':
            W=(W[0]+spec.get('dx',0), W[1]+spec.get('dy',0))
            if 'at' in spec: W=tuple(spec['at'])
        u=to_u8(o)
        al=u[...,3]; ys,xs=np.where(al>2)
        if len(ys)==0: raise SystemExit('empty frame '+fid)
        pad=2; x0=max(0,xs.min()-pad); x1=min(u.shape[1],xs.max()+1+pad); y0=max(0,ys.min()-pad); y1=min(u.shape[0],ys.max()+1+pad)
        crop=u[y0:y1,x0:x1]
        off=(round(W[0]+x0-A[0]), round(W[1]-(y1-A[1])))   # bottom-left of the picture, y up
        info={'meas':meas,'k':k,'size':crop.shape[1::-1],'body':self._body_box(crop,off),'A':A,'W':W}
        self.frames_done[fid]=(crop,off,info)
        return self.frames_done[fid]
    def _body_box(self, crop, off):
        m=measure(crop,self.fx)
        if m.get('empty'): return None
        h=crop.shape[0]
        return {'x0':off[0]+m['left'],'x1':off[0]+m['right'],'y0':off[1]+h-m['bot'],'y1':off[1]+h-m['top'],
                'cx':off[0]+m['cx'],'cy':off[1]+h-m['cy']}
    def write_strip(self, sid, arr):
        """an fx_strip layer's picture (a couple of columns of a beam, stretched by the engine)"""
        os.makedirs(self.sprite_dir,exist_ok=True)
        p=os.path.join(self.sprite_dir,sid+'.png'); imp=p+'.import'
        if not os.path.exists(imp): open(imp,'w').write(IMPORT%(self.res_dir+'/'+sid+'.png'))
        Image.fromarray(arr,'RGBA').save(p,optimize=False,compress_level=6)
    def write_frame(self, fid):
        crop,off,info=self.frame(fid)
        os.makedirs(self.sprite_dir,exist_ok=True)
        p=os.path.join(self.sprite_dir,fid+'.png')
        imp=p+'.import'
        if not os.path.exists(imp):   # import settings first (mipmaps for smooth zoom-out), Godot fills in the rest
            open(imp,'w').write(IMPORT%(self.res_dir+'/'+fid+'.png'))
        Image.fromarray(crop,'RGBA').save(p,optimize=False,compress_level=6)
        return off
    # ------------------------------------------------------------ AnimationData
    def keys_of(self, anim):
        keys=[]
        for k in anim['keys']:
            if isinstance(k,list): k={'f':k[0],'at':k[1],**(k[2] if len(k)>2 else {})}
            keys.append(k)
        return keys
    def modifier(self, fid, k, layer_fx=False):
        crop,off,info=self.frame(fid)
        ox,oy=off; rot=k.get('rot',0)
        ox+=k.get('dx',0); oy+=k.get('dy',0)
        if rot:
            # SpriteModifier.Rotation turns the sprite about the character origin; shift the offset so it
            # turns about the body centre instead (pivot in world px)
            b=info['body']; px,py=(b['cx'],b['cy']) if k.get('pivot','body')=='body' else (0,0)
            px+=k.get('dx',0); py+=k.get('dy',0)
            t=math.radians(rot); c,s=math.cos(t),math.sin(t)
            # want R*(offset' + (P-offset_orig)) = P  ->  offset' = R^-1 P - (P - off)
            rx= c*px + s*py; ry=-s*px + c*py
            ox,oy=rx-(px-ox), ry-(py-oy)
        sx=float(k.get('sx',1.0) or 1.0)
        if k.get('reach') and k.get('strip'):
            # Oct 24 late: a short piece of a drawn beam stretched across the screen (fx_strip). The picture's
            # transparent edge columns got stretched with it (x130 for the Photon Line: a gap in the middle of the
            # laser), so only two columns from the middle of the piece are stretched, from where the piece starts.
            a=crop[...,3].astype(np.float32); colmax=a.max(axis=0)
            vis=np.where(colmax>=0.6*colmax.max())[0]; c0,c1=int(vis.min()),int(vis.max())
            mid=(c0+c1)//2; strip=np.ascontiguousarray(crop[:,mid:mid+2])
            sid=fid+'_strip'; self.strips[sid]=strip
            X0=ox+c0                                   # world px where the piece's beam starts
            sx=max(1.0,(float(k['reach'])-X0)/strip.shape[1])
            return {'sprite':sid,'off':(round(X0/sx,4),round(oy)),'rot':0,'flipx':k.get('flipx',False),
                    'contact':layer_fx and not k.get('fx_always'),'sx':round(sx,4)}
        if k.get('reach'):   # stretch along x so the picture ends `reach` world px in front of the origin
            sx=max(1.0,(float(k['reach'])-ox)/max(1,crop.shape[1]))
        if abs(sx-1.0)>1e-6:
            # the engine scales the layer about the character origin, offset included: keep its left edge in place
            return {'sprite':fid,'off':(round(ox/sx,3),round(oy)),'rot':0,'flipx':k.get('flipx',False),
                    'contact':layer_fx and not k.get('fx_always'),'sx':round(sx,4)}
        return {'sprite':fid,'off':(round(ox),round(oy)),'rot':int(round(rot))%360,'flipx':k.get('flipx',False),'contact':layer_fx and not k.get('fx_always')}
    def fx_key(self, k):
        """an effect layer only moves with its own nudges (fx_dx / fx_dy), not the body's"""
        return {'dx': k.get('fx_dx', 0), 'dy': k.get('fx_dy', 0), 'fx_always': k.get('fx_always', False),
                'sx': k.get('fx_sx', 1.0), 'reach': k.get('fx_reach'), 'strip': k.get('fx_strip')}
    def build_anim(self, name, write=True):
        anim=self.m['animations'][name]
        path=os.path.join(PROJ,'actors',self.char,'AnimationData',name+'_AnimData.tres')
        t=Tres(open(path,encoding='utf-8').read())
        # script ids
        def script(pth, uid):
            i=t.ext_id_for_path(pth)
            return i or t.add_ext('Script',pth,uid,prefer_id=os.path.basename(pth)[:2].lower())
        SM=script('res://engine/sakuga/Resources/SpriteModifier.cs','uid://cai1mj5geilcj')
        AS=script('res://engine/sakuga/Resources/AnimationSettings.cs','uid://b8vqwkv52qq3e')
        # drop old sprite timeline (AnimationSettings + SpriteModifier subs, sprite textures)
        sm_path='res://engine/sakuga/Resources/SpriteModifier.cs'; as_path='res://engine/sakuga/Resources/AnimationSettings.cs'
        t.sub=[s for s in t.sub if t.script_of(s[2]) not in (sm_path,as_path)]
        t.ext=[e for e in t.ext if not (e['type']=='Texture2D' and '/Sprites/' in e.get('path',''))]
        keys=self.keys_of(anim); anim_ids=[]
        for n,k in enumerate(keys):
            mods=[self.modifier(k['f'],k)]
            if k.get('fx'): mods.append(self.modifier(k['fx'],self.fx_key(k),layer_fx=True))
            mod_ids=[]
            for j,md in enumerate(mods):
                tid=t.add_ext('Texture2D',self.res_dir+'/'+md['sprite']+'.png',prefer_id='t_'+re.sub(r'\W','_',md['sprite']))
                mid='M%d_%d'%(n,j); body=['script = ExtResource("%s")'%SM,'Sprite = ExtResource("%s")'%tid]
                if md.get('sx'): body.append('Offset = Vector2(%s, %d)'%(('%.4f'%md['off'][0]).rstrip('0').rstrip('.'),md['off'][1]))
                else: body.append('Offset = Vector2(%d, %d)'%md['off'])
                if md['rot']: body.append('Rotation = %d'%md['rot'])
                if md.get('sx'): body.append('Scale = Vector2(%s, 1)'%md['sx'])
                if md['flipx']: body.append('FlipX = true')
                if md['contact']: body.append('OnlyOnContact = true')
                t.sub.append([mid,'Resource',body]); mod_ids.append(mid)
            aid='A%d'%n; body=['script = ExtResource("%s")'%AS]
            if k['at']: body.append('AtFrame = %d'%k['at'])
            body.append('Modifiers = [%s]'%', '.join('SubResource("%s")'%x for x in mod_ids))
            t.sub.append([aid,'Resource',body]); anim_ids.append(aid)
        t.res_set('Animations','[%s]'%', '.join('SubResource("%s")'%a for a in anim_ids),after='Duration')
        if 'duration' in anim: t.res_set('Duration',str(anim['duration']))
        if 'afterimages' in anim: t.res_set('Afterimages','true' if anim['afterimages'] else None)
        if 'hitboxes' in anim: self._set_hitboxes(t,anim['hitboxes'])
        t.prune()
        if write:
            for k in keys:
                self.write_frame(k['f'])
                if k.get('fx'): self.write_frame(k['fx'])
            for sid,arr in self.strips.items(): self.write_strip(sid,arr)
            txt=t.text()
            bak=path+'.bak_sprite_port'
            if not os.path.exists(bak): open(bak,'w',encoding='utf-8').write(open(path,encoding='utf-8').read())
            open(path,'w',encoding='utf-8').write(txt)
        return t
    def _set_hitboxes(self, t, hbs):
        """the box timeline: [[at, stage, hitbox file name], ...]; left as it is when it already says that"""
        hs_path='res://engine/sakuga/Resources/HitboxState.cs'
        cur=[]
        for sid in re.findall(r'SubResource\("([^"]+)"\)',t.res_get('Hitboxes') or ''):
            s=t.sub_get(sid); body='\n'.join(s[2]) if s else ''
            hd=re.search(r'^HitboxData = ExtResource\("([^"]+)"\)',body,re.M)
            e=t.ext_by_id(hd.group(1)) if hd else None
            if not s or t.script_of(s[2])!=hs_path or not e: cur=None; break
            a_=re.search(r'^AtFrame = (\d+)',body,re.M); st_=re.search(r'^animationStage = (\d+)',body,re.M)
            cur.append((int(a_.group(1)) if a_ else 0,int(st_.group(1)) if st_ else 0,e.get('path')))
        if cur==[(at or 0,stage or 0,'res://actors/%s/Hitboxes/%s.tres'%(self.char,hb)) for at,stage,hb in hbs]: return
        HS=t.ext_id_for_path(hs_path) or t.add_ext('Script',hs_path,'uid://5qrsoteskjym',prefer_id='hs')
        t.sub=[s for s in t.sub if t.script_of(s[2])!=hs_path]
        ids=[]
        for n,(at,stage,hb) in enumerate(hbs):
            hp='res://actors/%s/Hitboxes/%s.tres'%(self.char,hb)
            uid=None
            fp=os.path.join(PROJ,'actors',self.char,'Hitboxes',hb+'.tres')
            if os.path.exists(fp):
                m=re.search(r'uid="([^"]+)"',open(fp,encoding='utf-8').readline()); uid=m.group(1) if m else None
            hid=t.add_ext('Resource',hp,uid,prefer_id='hb_'+re.sub(r'\W','_',hb))
            sid='H%d'%n; body=['script = ExtResource("%s")'%HS]
            if at: body.append('AtFrame = %d'%at)
            if stage: body.append('animationStage = %d'%stage)
            body.append('HitboxData = ExtResource("%s")'%hid)
            t.sub.append([sid,'Resource',body]); ids.append(sid)
        t.res_set('Hitboxes','[%s]'%', '.join('SubResource("%s")'%i for i in ids))
    # ------------------------------------------------------------ preview
    def preview(self, name, scale=0.5, out_dir=None):
        anim=self.m['animations'][name]; keys=self.keys_of(anim)
        path=os.path.join(PROJ,'actors',self.char,'AnimationData',name+'_AnimData.tres')
        dur=anim.get('duration') or int(Tres(open(path,encoding='utf-8').read()).res_get('Duration') or 60)
        mods=[]
        for k in keys:
            ms=[self.modifier(k['f'],k)]
            if k.get('fx'): ms.append(self.modifier(k['fx'],self.fx_key(k),True))
            mods.append((k['at'],ms))
        # canvas in world px
        boxes=[]
        for _,ms in mods:
            for md in ms:
                c,o,_=self.frame(md['sprite']); boxes.append((o[0],o[1],o[0]+c.shape[1],o[1]+c.shape[0]))
        X0=min(b[0] for b in boxes+[(self.REAR_X-20,0,0,0)])-30; X1=max(b[2] for b in boxes+[(0,0,self.FRONT_X+20,0)])+30
        Y0=min(b[1] for b in boxes+[(0,-10,0,0)])-20; Y1=max(b[3] for b in boxes)+20
        Wd,Ht=int((X1-X0)*scale),int((Y1-Y0)*scale)
        frames=[]; last=None
        for tick in range(dur):
            cur=[ms for at,ms in mods if at<=tick][-1]
            if last is not None and cur is last: frames[-1][1]+=1; continue
            img=Image.new('RGBA',(Wd,Ht),(78,78,86,255)); d=ImageDraw.Draw(img)
            fy=int((Y1-0)*scale); d.line([(0,fy),(Wd,fy)],fill=(0,200,200,255))
            oxp=int((0-X0)*scale); d.line([(oxp,fy-8),(oxp,fy+8)],fill=(255,80,80,255))
            for md in cur:
                c,o,_=self.frame(md['sprite']); off=md['off']
                im=Image.fromarray(c,'RGBA')
                if md['rot']:
                    # turned about the character origin like the engine does (the sprite itself is turned,
                    # so a part that starts outside the picture isn't cut off first)
                    big=Image.new('RGBA',(int((X1-X0)),int((Y1-Y0))),(0,0,0,0))
                    r,left,top=rotated_layer(im,off[0],off[1],md['rot'])
                    big.paste(r,(int(round(left-X0)),int(round(Y1-top))),r)
                    big=big.resize((Wd,Ht),Image.LANCZOS); img.alpha_composite(big)
                else:
                    im=im.resize((max(1,int(c.shape[1]*scale)),max(1,int(c.shape[0]*scale))),Image.LANCZOS)
                    img.alpha_composite(im,(int((off[0]-X0)*scale),int((Y1-(off[1]+c.shape[0]))*scale)))
            frames.append([img,1]); last=cur
        out_dir=out_dir or os.path.join(HERE,'checks',self.char); os.makedirs(out_dir,exist_ok=True)
        pal=[f[0].convert('RGB') for f in frames]
        durs=[max(20,int(round(f[1]*1000/60/10))*10) for f in frames]
        q=[p.quantize(colors=255,method=Image.MEDIANCUT,dither=Image.Dither.NONE) for p in pal]
        q[0].save(os.path.join(out_dir,name+'.gif'),save_all=True,append_images=q[1:],duration=durs,loop=0,disposal=1)
        return os.path.join(out_dir,name+'.gif')

IMPORT='''[remap]

importer="texture"
type="CompressedTexture2D"

[deps]

source_file="%s"

[params]

compress/mode=0
compress/high_quality=false
compress/lossy_quality=0.7
compress/uastc_level=0
compress/rdo_quality_loss=0.0
compress/hdr_compression=1
compress/normal_map=0
compress/channel_pack=0
mipmaps/generate=true
mipmaps/limit=-1
roughness/mode=0
roughness/src_normal=""
process/channel_remap/red=0
process/channel_remap/green=1
process/channel_remap/blue=2
process/channel_remap/alpha=3
process/fix_alpha_border=true
process/premult_alpha=false
process/normal_map_invert_y=false
process/hdr_as_srgb=false
process/hdr_clamp_exposure=false
process/size_limit=0
detect_3d/compress_to=0
'''

if __name__=='__main__':
    args=[a for a in sys.argv[1:] if not a.startswith('--')]; flags=[a for a in sys.argv[1:] if a.startswith('--')]
    p=Port(args[0]); names=args[1:] or list(p.m['animations'])
    for n in names:
        if '--preview' in flags or '--preview-only' in flags: print('preview',p.preview(n))
        if '--preview-only' not in flags:
            p.build_anim(n, write='--dry' not in flags); print('built',n)
