import bpy
for m in bpy.data.materials:
    if m.name.startswith("A_"):
        imgs=[(n.image.name if n.image else None) for n in m.node_tree.nodes if n.type=='TEX_IMAGE']
        b=[n for n in m.node_tree.nodes if n.type=='BSDF_PRINCIPLED']
        print("PM", m.name, imgs, round(b[0].inputs["Metallic"].default_value,2) if b else None, m.users)
o=bpy.data.objects["CH_Village"]; me=o.data
import collections
cnt=collections.Counter(me.materials[p.material_index].name for p in me.polygons if me.materials[p.material_index].name.startswith("A_"))
print("PM faces", dict(cnt))
# average normal direction vs outward for crate faces near (12.9,-10) -> blender (12.9, 10)
from mathutils import Vector
c=Vector((12.9,10.0,0.4)); out=0; inn=0
for p in me.polygons:
    if (p.center-c).length<1.0 and me.materials[p.material_index].name.startswith("A_"):
        if p.normal.dot(p.center-c)>0: out+=1
        else: inn+=1
print("PM normals out/in", out, inn)
cnt2=collections.Counter(); 
for p in me.polygons:
    if (p.center-Vector((12.9,10.0,0.5))).length<0.9: cnt2[me.materials[p.material_index].name if me.materials else "-"]+=1
print("PM near crate", dict(cnt2), "slots", [m.name for m in me.materials][:60])
print("PM uv", [u.name for u in me.uv_layers])
