"""One-time engine side of the 2x sprite port for Cecilia: her skin scenes draw sprites at half the
pixel size (so the 2x pictures keep her old size) with mipmaps, the palette shaders sample mipmaps.
Backups in _backup_stage_select/pre_sprite_port/."""
import sys, os, re
PROJ=os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)),'..','..'))
sys.path.insert(0,os.path.join(PROJ,'tools','sprite_port'))
from build import Port
os.chdir(PROJ)
p=Port('cecilia'); c,off,_=p.frame('idle_O0'); print('idle_O0 offset',off)
bk='_backup_stage_select/pre_sprite_port'; os.makedirs(bk,exist_ok=True)
for i in range(4):
    f='actors/cecilia/Instances/CEC_Fighter_Skin0%d.tscn'%i
    s=open(f,encoding='utf-8').read()
    b=os.path.join(bk,os.path.basename(f)+'.bak')
    if not os.path.exists(b): open(b,'w',encoding='utf-8').write(s)
    s=re.sub(r'\[ext_resource type="Texture2D"[^\]]*path="res://actors/cecilia/Sprites/[^"]+" id="8"\]',
             '[ext_resource type="Texture2D" path="res://actors/cecilia/Sprites/v2/idle_O0.png" id="8"]',s)
    for name in ('Sprite','FX'):
        m=re.search(r'(\[node name="%s" type="Sprite3D"[^\n]*\n)(.*?)(?=\n\[)'%name,s,re.S)
        body=m.group(2)
        body=re.sub(r'offset = Vector2\([^)]*\)','offset = Vector2(%d, %d)'%off,body)
        body=re.sub(r'pixel_size = [0-9.]+','pixel_size = 0.00275',body)
        body=re.sub(r'texture_filter = \d','texture_filter = 3',body)
        s=s[:m.start(2)]+body+s[m.end(2):]
    open(f,'w',encoding='utf-8').write(s); print(f,'pixel_size x',s.count('pixel_size = 0.00275'))
for sh in ['assets/shaders/sprite_color_swap.gdshader','assets/shaders/sprite_hue_shift.gdshader']:
    s=open(sh,encoding='utf-8').read()
    b=os.path.join(bk,os.path.basename(sh)+'.bak')
    if not os.path.exists(b): open(b,'w',encoding='utf-8').write(s)
    s2=re.sub(r'(uniform sampler2D albedo_texture : source_color, )filter_(nearest|linear)\b(?!_)',r'\1filter_linear_mipmap',s)
    open(sh,'w',encoding='utf-8').write(s2); print(sh,'changed' if s2!=s else 'same')
