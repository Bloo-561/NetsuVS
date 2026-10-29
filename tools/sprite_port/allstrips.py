import sys, os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from build import Port
from strip import strip
from PIL import Image
char=sys.argv[1]; p=Port(char)
names=sys.argv[2:] or list(p.m['animations'])
od=os.path.join(os.path.dirname(os.path.abspath(__file__)),'checks',char)
for n in names: strip(p,n,scale=0.3)
ims=[Image.open(os.path.join(od,'strip_'+n+'.png')) for n in names]
page=[]; h=0; k=0
def flush():
    global page,h,k
    if not page: return
    W=max(i.width for i in page); sh=Image.new('RGB',(min(W,2000),h),(40,40,40)); y=0
    for i in page: sh.paste(i,(0,y)); y+=i.height
    sh.save(os.path.join(od,'page_%02d.png'%k)); print('page',k,sh.size); k+=1; page=[]; h=0
for i in ims:
    if h+i.height>1500: flush()
    page.append(i); h+=i.height
flush()
