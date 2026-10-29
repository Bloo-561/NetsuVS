"""Measure every source drawing of a character: scale vs. the reference drawing (SIFT on the head,
with fallbacks), body/effect masks, feet line, rear/front foot, hip and body centres.
Writes analysis/<char>.json, which build.py uses.  Run:  python analyze.py cecilia"""
import cv2, numpy as np, json, os, sys, glob
from PIL import Image
from PIL import ImageFile; ImageFile.LOAD_TRUNCATED_IMAGES = True   # a damaged drawing loads what is there
HERE=os.path.dirname(os.path.abspath(__file__))
def cfg(char): return json.load(open(os.path.join(HERE,'manifests',char+'.json'),encoding='utf-8'))
def font(size, bold=False):
    """a TrueType font for check pictures: DejaVu (Linux) or Arial (Windows), else PIL's small default"""
    from PIL import ImageFont
    for n in ('/usr/share/fonts/truetype/dejavu/DejaVuSans%s.ttf' % ('-Bold' if bold else ''), 'arialbd.ttf' if bold else 'arial.ttf'):
        try: return ImageFont.truetype(n, size)
        except Exception: pass
    return ImageFont.load_default()
def source_root(c):
    """the drawings folder: 'source_root' (Windows path) or 'source_root_device' (Claude's Linux view of it)"""
    for k in ('source_root','source_root_device'):
        p=os.path.expanduser(c.get(k,'') or '')
        if p and os.path.isdir(p): return p
    raise SystemExit('drawings folder not found: set "source_root" in the manifest')
def load(p):
    a=np.array(Image.open(p).convert('RGBA'))
    al=a[:,:,3:4].astype(np.float32)/255
    rgb=(a[:,:,:3].astype(np.float32)*al+128*(1-al)).astype(np.uint8)
    return a,cv2.cvtColor(rgb,cv2.COLOR_RGB2GRAY)
def fx_mask(a,kind):
    r,g,b,al=[a[:,:,i].astype(np.int16) for i in range(4)]
    if kind=='yellow':   # Cecilia's lightning: bright yellow + its white-hot core where soft
        yel=(r>170)&(g>150)&(b<140)&((r-b)>70)
        soft=(al<235)&(r>200)&(g>200)
        return yel|soft
    if kind=='cyan':     # Leticia's shots/beams
        cy=(b>170)&(g>150)&(r<150)&((b-r)>60)
        soft=(al<235)&(b>200)&(g>200)
        return cy|soft
    if kind=='purple':   # Noah's devil-arm energy: bright violet / magenta glow (his crystal arm is darker)
        pu=(b>150)&(r>110)&(g<150)&((b-g)>70)&((r-g)>30)
        soft=(al<235)&(b>170)&(r>140)
        return pu|soft
    if kind=='gold':
        return (r>170)&(g>130)&(b<120)&((r-b)>80)
    if kind=='radiant':  # Flan's golden energy (her yellow frills are the same colour, so see radiant_mask)
        return radiant_mask(a)
    return np.zeros(a.shape[:2],bool)
def radiant_mask(a, min_area=400, win=21, dens=0.10):
    """Flan's golden energy: bright warm/white pixels where soft (semi-transparent) glow is dense nearby.
    Her yellow frills, trim and skin are opaque and outlined, so they only count right next to the energy."""
    r,g,b,al=[a[...,i].astype(np.int16) for i in range(4)]
    vis=al>40
    v=np.maximum(np.maximum(r,g),b); mn=np.minimum(np.minimum(r,g),b)
    bright=vis&(v>180)&(((r-b)>40)|(mn>215))
    soft=bright&(al<235)
    d=cv2.boxFilter(soft.astype(np.float32),-1,(win,win),normalize=True)
    m=soft|(bright&(d>dens))
    grown=cv2.dilate(m.astype(np.uint8),np.ones((5,5),np.uint8))
    n,lab,st,_=cv2.connectedComponentsWithStats(grown,8)
    cnt=np.bincount(lab[m],minlength=n)
    keep=cnt>=min_area; keep[0]=False
    return keep[lab]&m
def measure(a,fxkind,dark=True):
    """anchor measurements.  dark=True measures on dark pixels only (hair, jacket, socks, shoes, outlines):
    slash trails, lightning and speed lines are bright, so they can't drag the feet or body centre.
    fx 'radiant' (Flan) measures the whole body minus the energy instead (her soles are white)."""
    al=a[:,:,3]; solid=al>128
    if fxkind=='radiant': dark=False   # Flan: white soles and gold trim at the feet -> whole body minus her energy
    if dark:
        v=a[:,:,:3].max(2)
        dk=solid&(v<110)&(al>200)
        if dk.sum()>2000:
            k=np.ones((5,5),np.uint8)
            dk=cv2.morphologyEx(dk.astype(np.uint8),cv2.MORPH_CLOSE,k).astype(bool)
            r=measure_mask(dk)
            if r: r['mask']='dark'; return r
    return measure_body(a,fxkind)
def measure_mask(body, band_frac=0.10):
    n,lab,st,_=cv2.connectedComponentsWithStats(body.astype(np.uint8),8)
    if n>1:
        big=np.argmax(st[1:,cv2.CC_STAT_AREA])+1
        keep=np.zeros(n,bool); keep[big]=True
        for i in range(1,n):
            if st[i,cv2.CC_STAT_AREA]>0.03*st[big,cv2.CC_STAT_AREA]: keep[i]=True
        body=keep[lab]&body
    ys,xs=np.where(body)
    if len(ys)<50: return None
    top,bot,left,right=int(ys.min()),int(ys.max()),int(xs.min()),int(xs.max())
    h=bot-top+1
    band=body[max(top,bot-int(band_frac*h)):bot+1]   # whatever touches (or nearly touches) the floor
    cols=np.where(band.any(0))[0]
    hip_band=body[top+int(0.45*h):top+int(0.65*h)]
    hc=np.where(hip_band.any(0))[0]
    m=cv2.moments(body.astype(np.uint8),True)
    return {'empty':False,'top':top,'bot':bot,'left':left,'right':right,'h':h,
            'rear_x':int(cols.min()),'front_x':int(cols.max()),
            'hip_x':float((hc.min()+hc.max())/2) if len(hc) else float(m['m10']/m['m00']),
            'cx':float(m['m10']/m['m00']),'cy':float(m['m01']/m['m00'])}
def measure_body(a,fxkind):
    al=a[:,:,3]; solid=al>128
    fx=fx_mask(a,fxkind)&solid
    body=solid&~fx
    # remove tiny islands from body (sparks)
    n,lab,st,_=cv2.connectedComponentsWithStats(body.astype(np.uint8),8)
    if n>1:
        big=np.argmax(st[1:,cv2.CC_STAT_AREA])+1
        keep=np.zeros(n,bool); keep[big]=True
        for i in range(1,n):
            if st[i,cv2.CC_STAT_AREA]>0.02*st[big,cv2.CC_STAT_AREA]: keep[i]=True
        body=keep[lab]&body
    ys,xs=np.where(body)
    if len(ys)<50: return {'empty':True}
    top,bot,left,right=int(ys.min()),int(ys.max()),int(xs.min()),int(xs.max())
    h=bot-top+1
    band=body[max(top,bot-int(0.04*h)):bot+1]
    cols=np.where(band.any(0))[0]
    hip_band=body[top+int(0.45*h):top+int(0.65*h)]
    hc=np.where(hip_band.any(0))[0]
    m=cv2.moments(body.astype(np.uint8),True)
    return {'empty':False,'top':top,'bot':bot,'left':left,'right':right,'h':h,
            'rear_x':int(cols.min()),'front_x':int(cols.max()),
            'hip_x':float((hc.min()+hc.max())/2) if len(hc) else float(m['m10']/m['m00']),
            'cx':float(m['m10']/m['m00']),'cy':float(m['m01']/m['m00']),
            'fx_px':int(fx.sum())}
sift=cv2.SIFT_create(nfeatures=8000); bf=cv2.BFMatcher(cv2.NORM_L2)
def feats(g,mask): return sift.detectAndCompute(g,mask)
def similarity(k1,d1,k2,d2,thr=6):
    if d1 is None or d2 is None or len(k1)<8 or len(k2)<8: return None
    mm=bf.knnMatch(d1,d2,k=2)
    good=[x[0] for x in mm if len(x)==2 and x[0].distance<0.75*x[1].distance]
    if len(good)<8: return None
    s=np.float32([k1[x.queryIdx].pt for x in good]); d=np.float32([k2[x.trainIdx].pt for x in good])
    M,inl=cv2.estimateAffinePartial2D(s,d,method=cv2.RANSAC,ransacReprojThreshold=thr,maxIters=8000,confidence=0.997)
    if M is None: return None
    return {'scale':float(np.hypot(M[0,0],M[1,0])),'rot':float(np.degrees(np.arctan2(M[1,0],M[0,0]))),'inliers':int(inl.sum()),'good':len(good)}
def main(char):
    c=cfg(char); root=source_root(c)
    ref_a,ref_g=load(os.path.join(root,c['reference']))
    rm=measure(ref_a,c.get('fx','none'))
    head=np.zeros(ref_g.shape,np.uint8); hh=int(rm['h']*c.get('head_frac',0.23))
    head[rm['top']:rm['top']+hh,:]=255; head&=(ref_a[:,:,3]>128).astype(np.uint8)*255
    kh,dh=feats(ref_g,head); kb,db=feats(ref_g,(ref_a[:,:,3]>128).astype(np.uint8)*255)
    files=[]
    for d in c['source_dirs']: files+=sorted(glob.glob(os.path.join(root,d,'**','*.png'),recursive=True))
    out={}; cache={}
    for f in files:
        rel=os.path.relpath(f,root).replace('\\','/')
        a,g=load(f); m=measure(a,c.get('fx','none')); m['size']=list(a.shape[1::-1])
        k,d=feats(g,(a[:,:,3]>128).astype(np.uint8)*255); cache[rel]=(k,d)
        r=similarity(kh,dh,k,d); how='head'
        if not r or r['inliers']<25 or abs(r['rot'])>40:
            r2=similarity(kb,db,k,d,thr=10); 
            if r2 and r2['inliers']>=20 and (not r or r2['inliers']>r['inliers']): r,how=r2,'body'
        m['sift']=r; m['scale_how']=how if r else None
        m['scale']=r['scale'] if r and r['inliers']>=15 else None
        out[rel]=m
        print(f"{rel:75s} scale {m['scale'] if m['scale'] is None else round(m['scale'],3)} ({how}, {r['inliers'] if r else 0} inl, rot {round(r['rot'],1) if r else '-'})",flush=True)
    # neighbour chain for weak frames: match against frames in the same folder with good scales
    for rel,m in out.items():
        if m.get('empty') or (m['scale'] is not None and (m.get('sift') or {}).get('inliers',0)>=25): continue
        folder=os.path.dirname(rel); best=None
        for o,om in out.items():
            if o==rel or os.path.dirname(o)!=folder or om.get('empty') or om['scale'] is None or (om.get('sift') or {}).get('inliers',0)<25: continue
            r=similarity(*cache[o],*cache[rel],thr=10)
            if r and r['inliers']>=20 and (best is None or r['inliers']>best[1]['inliers']): best=(o,r)
        if best:
            m['scale']=out[best[0]]['scale']*best[1]['scale']; m['scale_how']='via '+os.path.basename(best[0]); m['sift_chain']=best[1]
            print('chain',rel,round(m['scale'],3),m['scale_how'],best[1]['inliers'])
    os.makedirs(os.path.join(HERE,'analysis'),exist_ok=True)
    json.dump({'reference':c['reference'],'ref':rm,'frames':out},open(os.path.join(HERE,'analysis',char+'.json'),'w'),indent=1)
if __name__=='__main__': main(sys.argv[1])
