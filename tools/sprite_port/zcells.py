"""crop fit_<anim>.png cells to the fighter area: python zcells.py <char> <scale> <anim>..."""
import sys
from PIL import Image
char, sc = sys.argv[1], float(sys.argv[2]); cw=int(1600*sc)
for n in sys.argv[3:]:
    im=Image.open('checks/%s/fit_%s.png'%(char,n)); k=im.width//cw
    cells=[im.crop((i*cw+int(350*sc), int(100*sc), i*cw+int(1450*sc), im.height)) for i in range(k)]
    W=sum(c.width for c in cells); out=Image.new('RGB',(W,cells[0].height)); x=0
    for c in cells: out.paste(c,(x,0)); x+=c.width
    out.save('checks/%s/z_%s.png'%(char,n)); print(n,out.size)
