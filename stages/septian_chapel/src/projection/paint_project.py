# Septian Chapel - PAINTED variant (camera projection pilot). Background Blender only:
#   blender --background stages/septian_chapel/src/septian_chapel.blend --python paint_project.py -- [PLATE=<painted.png>]
# 1. renders each atlas group (Chapel / Village / Land) alone from the PROJ camera, unlit = exactly the baked atlas look,
#    plus a view-depth pass;  the colour pass goes through Kuwahara (stand-in for a hand / AI painting).
#    PLATE=<file> (optional): use a real painting of chapel_plate.png's view instead of the Kuwahara stand-in.
# 2. bakes every atlas texel's world position + normal, projects it into the plate, depth-tests it, and blends the
#    painted colour into the atlas where the PROJ camera sees that texel face-on.  -> src/baked_painted/
# 3. exports septian_chapel_painted.glb and A/B renders from the fight cameras -> src/projection/ab_*.png
import bpy, math, os, sys, json, time, traceback
import numpy as np
NEW = r"E:\Netsu Projects\NetsuVS"; OLD = r"E:\Netsu Projects\Netsu Fighter\Godot\netsu-vs"
ROOT = NEW + r"\stages\septian_chapel"; S = ROOT + r"\src"; P = S + r"\projection"; PAINTED = P + r"\baked_painted"
args = dict(a.split("=", 1) for a in (sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []) if "=" in a)
W, H = 3840, 2160
KSIZE = float(args.get("KSIZE", 7))
GROUPS = ("CH_Chapel", "CH_Village", "CH_Land")
os.makedirs(PAINTED, exist_ok=True)
info = {}; t0 = time.time()
def log(*a):
    print("PP:", *a, flush=True)

for im in bpy.data.images:
    if im.filepath.startswith(OLD):
        im.filepath = NEW + im.filepath[len(OLD):]
bk = {"__name__": "lib", "VARIANT": "afternoon"}
exec(open(S + r"\bake_septian_chapel.py", encoding="utf-8").read(), bk)
sc = bpy.context.scene; dg = bpy.context.evaluated_depsgraph_get()

def img_np(path_or_img, colorspace=None):
    im = bpy.data.images.load(path_or_img, check_existing=False) if isinstance(path_or_img, str) else path_or_img
    if colorspace: im.colorspace_settings.name = colorspace
    a = np.empty(im.size[0] * im.size[1] * 4, np.float32); im.pixels.foreach_get(a)
    a = a.reshape(im.size[1], im.size[0], 4)
    if isinstance(path_or_img, str): bpy.data.images.remove(im)
    return a

def save_np(a, path):          # a: HxWx4, values as stored (sRGB-encoded), bottom row first
    h, w = a.shape[:2]
    im = bpy.data.images.new("tmp_save", w, h, alpha=True)
    im.pixels.foreach_set(np.ascontiguousarray(a, np.float32).ravel())
    im.filepath_raw = path; im.file_format = 'PNG'; im.save(); bpy.data.images.remove(im)

# ---- floor preview (its cache was cleared; rebuild it from the shipped light map) ----
os.makedirs(bk["CACHE"], exist_ok=True)
fp = bk["CACHE"] + r"\_floor_preview.png"
if not os.path.exists(fp):
    raw = img_np(ROOT + r"\textures\floor_light.png", "Non-Color")[..., :3]
    L = (raw ** 2.2) * bk["LIGHT_MAX"]
    pv = np.clip(bk["grade"](L * np.array([0.14, 0.24, 0.07], np.float32)), 0, 1)
    bk["save_png"](pv.astype(np.float32), fp, "floor_preview_png")

# ---- unlit preview objects with the ORIGINAL atlases ----
bk["make_preview"]()
vs = sc.view_settings; vs.view_transform = 'Standard'; vs.look = 'None'; vs.exposure = 0; vs.gamma = 1
sc.render.engine = 'CYCLES'; sc.cycles.use_denoising = False
try: sc.cycles.device = 'GPU'
except Exception: pass
sc.render.film_transparent = True
PV = {o.name: o for o in bpy.data.objects if o.name.startswith("PV_")}
log("preview objects", sorted(PV))

cd = bpy.data.cameras.new("PROJ"); cd.sensor_fit = 'HORIZONTAL'; cd.angle_x = math.radians(64)
cd.clip_start = 0.1; cd.clip_end = 1500; cd.shift_y = 0.08
cam = bpy.data.objects.new("PROJ", cd); sc.collection.objects.link(cam)
cam.location = (0, -16.0, 3.35); cam.rotation_euler = (math.radians(90), 0, 0)
bpy.context.view_layer.update()

# compositor: Render Layers -> Kuwahara -> output
ng = bpy.data.node_groups.new("PaintFX", "CompositorNodeTree")
ng.interface.new_socket("Image", in_out='OUTPUT', socket_type='NodeSocketColor')
rl = ng.nodes.new("CompositorNodeRLayers"); kw = ng.nodes.new("CompositorNodeKuwahara"); go = ng.nodes.new("NodeGroupOutput")
kw.inputs["Size"].default_value = KSIZE
try: kw.inputs["Type"].default_value = 'Anisotropic'
except Exception as e: log("type", e)
kw.inputs["High Precision"].default_value = True
ng.links.new(rl.outputs["Image"], kw.inputs["Image"]); ng.links.new(kw.outputs[0], go.inputs[0])

# depth override material
dm = bpy.data.materials.new("PP_depth"); dm.use_nodes = True; nt = dm.node_tree; nt.nodes.clear()
o_ = nt.nodes.new("ShaderNodeOutputMaterial"); cdn = nt.nodes.new("ShaderNodeCameraData"); em = nt.nodes.new("ShaderNodeEmission")
nt.links.new(cdn.outputs["View Z Depth"], em.inputs["Color"]); nt.links.new(em.outputs[0], o_.inputs[0])

def render(path, cam_obj, w, h, samples, comp=False, fmt='PNG'):
    sc.camera = cam_obj; sc.render.resolution_x = w; sc.render.resolution_y = h; sc.render.resolution_percentage = 100
    sc.cycles.samples = samples
    sc.compositing_node_group = ng if comp else None; sc.render.use_compositing = comp
    s = sc.render.image_settings; s.file_format = fmt
    if fmt == 'OPEN_EXR': s.color_depth = '32'; s.color_mode = 'RGB'
    else: s.color_mode = 'RGBA'; s.color_depth = '8'
    sc.render.filepath = path; bpy.ops.render.render(write_still=True)

def only(names):
    for n, o in PV.items(): o.hide_render = n not in names

plate_in = args.get("PLATE")
for g in GROUPS:
    only({"PV_" + g})
    if not plate_in:
        render(P + r"\plate_%s.png" % g, cam, W, H, 16, comp=True)
    bpy.context.view_layer.material_override = dm
    sc.cycles.filter_width = 0.01
    render(P + r"\depth_%s.exr" % g, cam, W, H, 1, fmt='OPEN_EXR')
    bpy.context.view_layer.material_override = None; sc.cycles.filter_width = 1.5
    log("rendered", g)

# ---- bake texel world position / normal on the Bake UVs ----
def bake_attr(obj, res, socket):
    me = obj.data.copy(); tmp = bpy.data.objects.new("PP_tmp", me); sc.collection.objects.link(tmp)
    tmp.matrix_world = obj.matrix_world.copy(); me.uv_layers.active = me.uv_layers["Bake"]
    m = bpy.data.materials.new("PP_attr"); m.use_nodes = True; t = m.node_tree; t.nodes.clear()
    out = t.nodes.new("ShaderNodeOutputMaterial"); geo = t.nodes.new("ShaderNodeNewGeometry"); e = t.nodes.new("ShaderNodeEmission")
    t.links.new(geo.outputs[socket], e.inputs["Color"]); t.links.new(e.outputs[0], out.inputs[0])
    img = bpy.data.images.new("PP_bake", res, res, alpha=True, float_buffer=True); img.colorspace_settings.name = "Non-Color"
    img.generated_color = (0, 0, 0, 0)
    tn = t.nodes.new("ShaderNodeTexImage"); tn.image = img; t.nodes.active = tn
    me.materials.clear(); me.materials.append(m)
    for o in bpy.context.view_layer.objects: o.select_set(False)
    tmp.select_set(True); bpy.context.view_layer.objects.active = tmp
    sc.render.bake.margin = 6; sc.render.bake.use_clear = True; sc.cycles.samples = 1
    bpy.ops.object.bake(type='EMIT', margin=6, use_clear=True)
    a = img_np(img); bpy.data.images.remove(img); bpy.data.objects.remove(tmp); bpy.data.meshes.remove(me); bpy.data.materials.remove(m)
    return a

def bilinear(img, x, y):
    h, w = img.shape[:2]
    x = np.clip(x - 0.5, 0, w - 1.001); y = np.clip(y - 0.5, 0, h - 1.001)
    x0 = x.astype(np.int32); y0 = y.astype(np.int32); fx = (x - x0)[:, None]; fy = (y - y0)[:, None]
    a = img[y0, x0]; b = img[y0, x0 + 1]; c = img[y0 + 1, x0]; d = img[y0 + 1, x0 + 1]
    return (a * (1 - fx) + b * fx) * (1 - fy) + (c * (1 - fx) + d * fx) * fy

sc.camera = cam; sc.render.resolution_x = W; sc.render.resolution_y = H
Mp = np.array(cam.calc_matrix_camera(dg, x=W, y=H, scale_x=1, scale_y=1)); Mv = np.array(cam.matrix_world.inverted())
campos = np.array(cam.matrix_world.translation)
plate_all = img_np(plate_in) if plate_in else None
stats = {}
for g in GROUPS:
    res = bk["ATLAS"][g]
    pos = bake_attr(bpy.data.objects[g], res, "Position"); nrm = bake_attr(bpy.data.objects[g], res, "Normal")
    atlas = img_np(bk["ATLAS_DIR"] + "\\" + g.lower() + ".png")
    plate = plate_all if plate_all is not None else img_np(P + r"\plate_%s.png" % g)
    depth = img_np(P + r"\depth_%s.exr" % g)[..., 0]
    cov = (np.abs(pos[..., :3]).sum(-1) > 1e-6) & (pos[..., 3] > 0.5)
    idx = np.nonzero(cov.ravel())[0]
    Pw = pos[..., :3].reshape(-1, 3)[idx]; Nw = nrm[..., :3].reshape(-1, 3)[idx]
    Nw /= np.linalg.norm(Nw, axis=1, keepdims=True) + 1e-8
    hp = np.c_[Pw, np.ones(len(Pw), np.float32)]
    vp = hp @ Mv.T; vz = -vp[:, 2]
    cp = vp @ Mp.T; ndc = cp[:, :2] / cp[:, 3:4]
    px = (ndc[:, 0] * 0.5 + 0.5) * W; py = (ndc[:, 1] * 0.5 + 0.5) * H
    inb = (vz > 0.1) & (px >= 1) & (px < W - 1) & (py >= 1) & (py < H - 1)
    pxi = np.clip(px.astype(np.int32), 0, W - 1); pyi = np.clip(py.astype(np.int32), 0, H - 1)
    D = depth[pyi, pxi]
    vis = inb & (D > 0.05) & (np.abs(vz - D) < 0.02 * D + 0.06)
    tocam = campos[None, :] - Pw; tocam /= np.linalg.norm(tocam, axis=1, keepdims=True) + 1e-8
    facing = (Nw * tocam).sum(1)
    wgt = np.clip((facing - 0.08) / 0.27, 0, 1) * vis
    col = bilinear(plate, px, py)[:, :3]
    if plate_all is None:       # stand-in plate has no background: ignore pixels the group didn't cover
        wgt *= np.clip(bilinear(plate, px, py)[:, 3] * 1.5 - 0.5, 0, 1)
    flat = atlas.reshape(-1, 4).copy()
    flat[idx, :3] = flat[idx, :3] * (1 - wgt[:, None]) + col * wgt[:, None]
    save_np(flat.reshape(atlas.shape), PAINTED + "\\" + g.lower() + ".png")
    stats[g] = {"texels": int(len(idx)), "painted_frac": round(float((wgt > 0.5).mean()), 3)}
    log(g, stats[g])
    del pos, nrm, atlas, depth, flat
info["stats"] = stats

# ---- A/B renders from the fight cameras + export ----
sc.render.film_transparent = False
for o in PV.values(): o.hide_render = False
if "PV_CH_Sky" in PV: PV["PV_CH_Sky"].hide_render = False
CAMS = ("CAM_far", "CAM_mid", "CAM_near_right", "CAM_jump_far")
def ab(tag):
    for c in CAMS:
        if c in bpy.data.objects:
            render(P + r"\ab_%s_%s.png" % (tag, c), bpy.data.objects[c], 1920, 1080, 16)
ab("orig")
bk["ATLAS_DIR"] = PAINTED
bk["make_preview"](); PV = {o.name: o for o in bpy.data.objects if o.name.startswith("PV_")}
sc.render.film_transparent = False; sc.render.engine = 'CYCLES'; sc.cycles.use_denoising = False
vs.view_transform = 'Standard'
ab("painted")
info["export"] = bk["export_glb"](P + r"\septian_chapel_painted.glb")
info["seconds"] = round(time.time() - t0)
open(P + r"\_status.json", "w").write(json.dumps(info, indent=1))
log("DONE", json.dumps(info))
