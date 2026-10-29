# Review renders: front / 3-4 / side (her right, facing image-right like the game) / back.
import bpy, math, os, importlib
from mathutils import Vector
import lib; importlib.reload(lib)

VIEWS = {  # name: direction from target to camera
    "front": Vector((0, -1, 0)),
    "threequarter": Vector((-0.7071, -0.7071, 0)),
    "side": Vector((-1, 0, 0)),
    "back": Vector((0, 1, 0)),
}

def setup_render(res=(1000, 1100)):
    sc = bpy.context.scene
    for eng in ("BLENDER_EEVEE_NEXT", "BLENDER_EEVEE"):
        try: sc.render.engine = eng; break
        except Exception: pass
    sc.render.resolution_x, sc.render.resolution_y = res
    sc.render.resolution_percentage = 100
    sc.render.film_transparent = True
    sc.render.image_settings.file_format = 'PNG'
    sc.render.image_settings.color_mode = 'RGBA'
    sc.view_settings.view_transform = 'Standard'
    sc.view_settings.look = 'None'
    sc.view_settings.exposure = 0; sc.view_settings.gamma = 1
    if not sc.world: sc.world = bpy.data.worlds.new("World")
    sc.world.use_nodes = True
    bg = sc.world.node_tree.nodes.get("Background")
    if bg: bg.inputs[0].default_value = (0, 0, 0, 1); bg.inputs[1].default_value = 0
    try: sc.eevee.taa_render_samples = 16
    except Exception: pass

def camera(name="ReviewCam"):
    cam = bpy.data.objects.get(name)
    if not cam:
        cd = bpy.data.cameras.new(name); cam = bpy.data.objects.new(name, cd)
        bpy.context.scene.collection.objects.link(cam)
    cam.data.type = 'ORTHO'
    return cam

def render(views=("front", "threequarter", "side", "back"), scale=1.80, target=(0, 0, 0.82), prefix="review", res=(1000, 1100)):
    setup_render(res)
    cam = camera(); sc = bpy.context.scene; sc.camera = cam
    cam.data.ortho_scale = scale
    out = []
    t = Vector(target)
    for v in views:
        d = VIEWS[v]
        cam.location = t + d * 6
        cam.rotation_euler = (-d).to_track_quat('-Z', 'Y').to_euler()
        path = os.path.join(lib.ROOT, "renders", f"{prefix}_{v}.png")
        sc.render.filepath = path
        bpy.ops.render.render(write_still=True)
        out.append(path)
    return out
