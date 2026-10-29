import cv2, numpy as np, glob, os, sys
from PIL import Image
SRC=os.path.expanduser('~/mnt/Fighting_Game_All_Sprites')
def load(p):
    a=np.array(Image.open(p).convert('RGBA'))
    al=a[:,:,3:4].astype(np.float32)/255
    rgb=a[:,:,:3].astype(np.float32)*al+128*(1-al)   # composite on grey
    g=cv2.cvtColor(rgb.astype(np.uint8),cv2.COLOR_RGB2GRAY)
    return a,g
sift=cv2.SIFT_create(nfeatures=6000)
ref_a,ref_g=load(os.path.join(SRC,'Cecilia_Original_Idle_Style/01_Idle/01_ready.png'))
ys,xs=np.where(ref_a[:,:,3]>128); top=ys.min()
head=np.zeros(ref_g.shape,np.uint8); head[top:top+330, :]=255
head&=(ref_a[:,:,3]>128).astype(np.uint8)*255
kr,dr=sift.detectAndCompute(ref_g,head)
print('ref head kps',len(kr))
bf=cv2.BFMatcher(cv2.NORM_L2)
def est(p):
    a,g=load(p)
    m=(a[:,:,3]>128).astype(np.uint8)*255
    k,d=sift.detectAndCompute(g,m)
    if d is None or len(k)<10: return None
    mm=bf.knnMatch(dr,d,k=2)
    good=[x[0] for x in mm if len(x)==2 and x[0].distance<0.75*x[1].distance]
    if len(good)<8: return (None,len(good))
    src=np.float32([kr[x.queryIdx].pt for x in good]); dst=np.float32([k[x.trainIdx].pt for x in good])
    M,inl=cv2.estimateAffinePartial2D(src,dst,method=cv2.RANSAC,ransacReprojThreshold=6,maxIters=5000,confidence=0.995)
    if M is None: return (None,len(good))
    s=float(np.hypot(M[0,0],M[1,0])); rot=float(np.degrees(np.arctan2(M[1,0],M[0,0])))
    return (s,int(inl.sum()),len(good),rot)
files=sorted(glob.glob(os.path.join(SRC,sys.argv[1],'**','*.png'),recursive=True))
for f in files:
    r=est(f); ys,xs=np.where(np.array(Image.open(f))[:,:,3]>128)
    print(f'{os.path.relpath(f,SRC):70s} {Image.open(f).size} h{ys.max()-ys.min()+1:5d}', r)
