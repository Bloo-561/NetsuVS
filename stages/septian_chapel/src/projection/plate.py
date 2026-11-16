import bpy, math, sys
OUT = r"E:\Netsu Projects\NetsuVS\_tmp_claude\chapel_plate"
sc = bpy.context.scene
OLD=r"E:\Netsu Projects\Netsu Fighter\Godot\netsu-vs"; NEW=r"E:\Netsu Projects\NetsuVS"
for im in bpy.data.images:
    if im.filepath.startswith(OLD): im.filepath = NEW + im.filepath[len(OLD):]; im.reload()
# projection / paint-over camera: far fight camera position, wide enough for every pan and jump
cd = bpy.data.cameras.new("PROJ"); cd.sensor_fit = 'HORIZONTAL'; cd.angle_x = math.radians(64)
cd.clip_start = 0.1; cd.clip_end = 1500; cd.shift_y = 0.08
o = bpy.data.objects.new("PROJ", cd); sc.collection.objects.link(o)
o.location = (0, -16.0, 3.35); o.rotation_euler = (math.radians(90), 0, 0)
sc.camera = o
for im in bpy.data.images:
    if im.filepath.endswith("_floor_preview.png"):
        im.filepath = NEW + r"\stages\septian_chapel\textures\floor_light.png"; im.reload()
for m in bpy.data.materials:
    if m.use_nodes:
        for n in m.node_tree.nodes:
            if n.type=='TEX_IMAGE' and n.image and n.image.filepath.endswith("floor_light.png"):
                nt=m.node_tree; mix=nt.nodes.new('ShaderNodeMix'); mix.data_type='RGBA'; mix.blend_type='MULTIPLY'
                mix.inputs['Factor'].default_value=1.0; mix.inputs[7].default_value=(0.42,0.55,0.30,1)
                links=[l for l in nt.links if l.from_node==n and l.from_socket.name=='Color']
                nt.links.new(n.outputs['Color'], mix.inputs[6])
                for l in links: nt.links.new(mix.outputs[2], l.to_socket)
sc.render.resolution_x = 3840; sc.render.resolution_y = 2160; sc.render.resolution_percentage = 100
sc.render.engine = 'CYCLES'; sc.cycles.samples = 48; sc.cycles.use_denoising = True
try:
    sc.cycles.device = 'GPU'
except Exception: pass
sc.render.image_settings.file_format = 'PNG'
sc.render.filepath = OUT + ".png"
bpy.ops.render.render(write_still=True)
# fight-camera reference renders (far, near-right) for the A/B later
for name, loc in (("far", (0, -16.0, 3.35)), ("near_r", (9.3, -6.5, 1.4))):
    cd.shift_y = 0.0; cd.sensor_fit = 'VERTICAL'; cd.angle_y = math.radians(30); o.location = loc
    sc.render.resolution_x = 1920; sc.render.resolution_y = 1080; sc.cycles.samples = 32
    sc.render.filepath = OUT + "_" + name + ".png"; bpy.ops.render.render(write_still=True)
print("PLATE_DONE")
