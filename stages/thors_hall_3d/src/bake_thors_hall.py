# Thors Training Hall - bake, grade, preview and export (Blender 5.x), Morning ("day") or "dusk"
# The variant comes from the scene built by build_thors_hall.py (or VARIANT in the exec globals).
# Outputs per variant:
#   day : src/baked/, src/cache/,      textures/floor_light.png,      thors_hall_3d.glb
#   dusk: src/baked_dusk/, src/cache/dusk/, textures/floor_light_dusk.png, thors_hall_3d_dusk.glb
# Run AFTER build_thors_hall.py in the same Blender session:
#   ns = {"__name__": "lib"}; exec(open(r"...\src\bake_thors_hall.py", encoding="utf-8").read(), ns)
#   ns["bake_all"](); ns["make_preview"](); ns["export_glb"]()
#
# Lighting is baked with Cycles (direct + bounce) into texture atlases, then tone-mapped and
# colour-graded here (grade()) so the game can show them UNSHADED: what you see in the preview
# renders is what Godot draws. The floor is special: it keeps a tiling marble texture plus a
# separate light map so it stays sharp under the fighters, and Godot's floor shader blends it
# over a mirrored copy of the room for the polished reflection.
import bpy, bmesh, math, os, json, struct
import numpy as np

ROOT = r"E:\Netsu Projects\Netsu Fighter\Godot\netsu-vs\stages\thors_hall_3d"
VARIANT = globals().get("VARIANT") or bpy.context.scene.get("th_variant", "day")
SUFFIX = "" if VARIANT == "day" else "_" + VARIANT
OUT = ROOT + r"\textures"           # floor textures (used directly by Godot)
ATLAS_DIR = ROOT + r"\src\baked" + SUFFIX     # room atlases (embedded in the .glb, so kept out of Godot's import)
CACHE = ROOT + r"\src\cache" + ("" if VARIANT == "day" else "\\" + VARIANT)
GLB = ROOT + r"\thors_hall_3d" + SUFFIX + ".glb"
ATLAS = {"TH_Back": 4096, "TH_Sides": 4096, "TH_Ceiling": 2048, "TH_Props": 4096}
FLOOR_LIGHT_RES = 2048
FLOOR_TILE_RES = 2048
FLOOR_TILE_M = 6.0           # metres covered by one repeat of floor_albedo.png
LIGHT_MAX = 6.0              # floor light map encoding: stored = (light / LIGHT_MAX) ** (1/2.2)
SAMPLES = 384
MARGIN_PX = 16

# ---- look (shared with the Godot floor shader's "look" group - keep both in sync) ----
LOOKS = {
    "day": dict(EXPOSURE=0.55, SHOULDER=0.78, SATURATION=1.12,
                SHADOW_TINT=(0.86, 0.88, 1.10),       # cool violet shadows (BlazBlue / Xrd style)
                HIGHLIGHT_TINT=(1.07, 1.0, 0.90),     # warm sunlit highlights
                TINT_AMOUNT=0.55),
    "dusk": dict(EXPOSURE=0.30, SHOULDER=0.78, SATURATION=1.0,
                 SHADOW_TINT=(0.82, 0.80, 1.22),      # deep violet shadows
                 HIGHLIGHT_TINT=(1.10, 0.94, 0.80),   # orange sunset highlights
                 TINT_AMOUNT=0.7),
}
globals().update(LOOKS[VARIANT])

def grade(lin):
    """linear radiance (...,3) -> display sRGB 0..1"""
    c = np.maximum(lin, 0.0) * (2.0 ** EXPOSURE)
    over = np.maximum(c - SHOULDER, 0.0)
    c = np.where(c > SHOULDER, SHOULDER + (1 - SHOULDER) * (1 - np.exp(-over / (1 - SHOULDER))), c)
    lum = (c * np.array([0.2126, 0.7152, 0.0722], np.float32)).sum(-1, keepdims=True)
    c = lum + (c - lum) * SATURATION
    sh = np.clip(1.0 - lum / 0.45, 0, 1) ** 1.5 * TINT_AMOUNT
    hi = np.clip((lum - 0.5) / 0.5, 0, 1) * TINT_AMOUNT
    c = c * (1 - sh + sh * np.array(SHADOW_TINT, np.float32))
    c = c * (1 - hi + hi * np.array(HIGHLIGHT_TINT, np.float32))
    c = np.clip(c, 0, 1)
    return np.where(c <= 0.0031308, c * 12.92, 1.055 * np.power(c, 1 / 2.4) - 0.055)

def to_srgb(c):
    c = np.clip(c, 0, 1)
    return np.where(c <= 0.0031308, c * 12.92, 1.055 * np.power(c, 1 / 2.4) - 0.055)

# ----------------------------------------------------------------------
def _px(img):
    a = np.empty(img.size[0] * img.size[1] * 4, np.float32)
    img.pixels.foreach_get(a)
    return a.reshape(img.size[1], img.size[0], 4)

def save_png(rgb, path, name):
    h, w = rgb.shape[:2]
    if name in bpy.data.images:
        bpy.data.images.remove(bpy.data.images[name])
    im = bpy.data.images.new(name, w, h, alpha=False, float_buffer=False)
    im.colorspace_settings.name = 'sRGB'
    rgba = np.concatenate([rgb, np.ones((h, w, 1), np.float32)], -1).astype(np.float32)
    im.pixels.foreach_set(rgba.ravel())
    im.filepath_raw = path; im.file_format = 'PNG'
    im.save()
    return im

def _select_only(obj):
    for o in bpy.context.view_layer.objects:
        o.select_set(False)
    obj.select_set(True)
    bpy.context.view_layer.objects.active = obj

def bake_uv(obj, margin=0.0015):
    me = obj.data
    if "Bake" in me.uv_layers:
        me.uv_layers.remove(me.uv_layers["Bake"])
    uv = me.uv_layers.new(name="Bake")
    me.uv_layers.active = uv
    _select_only(obj)
    bpy.ops.object.mode_set(mode='EDIT')
    bpy.ops.mesh.select_all(action='SELECT')
    bpy.ops.uv.smart_project(angle_limit=math.radians(66), island_margin=margin,
                             area_weight=0.0, correct_aspect=True, scale_to_bounds=False)
    bpy.ops.uv.pack_islands(rotate=True, margin=margin)
    bpy.ops.object.mode_set(mode='OBJECT')

def _bake_target(obj, img):
    nodes = []
    for slot in obj.material_slots:
        m = slot.material
        nt = m.node_tree
        nd = nt.nodes.get("BAKE_TARGET") or nt.nodes.new("ShaderNodeTexImage")
        nd.name = "BAKE_TARGET"; nd.image = img; nd.location = (1200, 400)
        nt.nodes.active = nd
        nodes.append(nd)
    return nodes

def _cycles_bake(kind, passes):
    sc = bpy.context.scene
    sc.render.engine = 'CYCLES'
    sc.cycles.samples = SAMPLES
    b = sc.render.bake
    b.use_pass_direct = 'DIRECT' in passes
    b.use_pass_indirect = 'INDIRECT' in passes
    b.use_pass_color = 'COLOR' in passes
    if kind == 'COMBINED':
        b.use_pass_diffuse = b.use_pass_glossy = b.use_pass_transmission = b.use_pass_emit = True
    b.margin = MARGIN_PX; b.margin_type = 'EXTEND'
    b.use_clear = True; b.target = 'IMAGE_TEXTURES'
    bpy.ops.object.bake(type=kind)

def _hide_preview(hide=True):
    for o in bpy.data.objects:
        if o.name.startswith("Preview") or o.name.startswith("PV_"):
            o.hide_render = hide

def _bake_pass(obj, res, kind, passes, samples, name):
    img = bpy.data.images.new(name, res, res, alpha=False, float_buffer=True)
    _bake_target(obj, img); _select_only(obj)
    bpy.context.scene.cycles.samples = samples
    b = bpy.context.scene.render.bake
    b.use_pass_direct = 'DIRECT' in passes
    b.use_pass_indirect = 'INDIRECT' in passes
    b.use_pass_color = 'COLOR' in passes
    b.margin = max(4, MARGIN_PX * res // 4096); b.margin_type = 'EXTEND'
    b.use_clear = True; b.target = 'IMAGE_TEXTURES'
    bpy.context.scene.render.engine = 'CYCLES'
    bpy.ops.object.bake(type=kind)
    a = _px(img)[..., :3].copy()
    bpy.data.images.remove(img)
    return a

def _blur(a, r=1.5):
    k = int(math.ceil(r * 3)); x = np.arange(-k, k + 1, dtype=np.float32)
    w = np.exp(-x * x / (2 * r * r)); w /= w.sum()
    for ax in (0, 1):
        a = sum(np.roll(a, int(i), ax) * wi for i, wi in zip(x, w))
    return a

def _upsample(a, f):
    """bilinear upsample by integer factor f"""
    h, w = a.shape[:2]
    y = (np.arange(h * f) + 0.5) / f - 0.5
    y0 = np.floor(y).astype(int); wy = (y - y0).astype(np.float32)[:, None, None]
    a = a[np.clip(y0, 0, h - 1)] * (1 - wy) + a[np.clip(y0 + 1, 0, h - 1)] * wy
    x = (np.arange(w * f) + 0.5) / f - 0.5
    x0 = np.floor(x).astype(int); wx = (x - x0).astype(np.float32)[None, :, None]
    return a[:, np.clip(x0, 0, w - 1)] * (1 - wx) + a[:, np.clip(x0 + 1, 0, w - 1)] * wx

_METALS = {}
def _metals_off(off=True):
    for m in bpy.data.materials:
        if not m.use_nodes:
            continue
        for nd in m.node_tree.nodes:
            if nd.type == 'BSDF_PRINCIPLED':
                key = (m.name, nd.name)
                if off:
                    _METALS[key] = nd.inputs["Metallic"].default_value
                    nd.inputs["Metallic"].default_value = 0.0
                elif key in _METALS:
                    nd.inputs["Metallic"].default_value = _METALS[key]

GLOSSY_GROUPS = {"TH_Props": 0.55}
INDIRECT_BLUR = {"TH_Ceiling": 2.0}     # baked sheen for gold / steel / lacquer (stylised)
INDIRECT_DIV = 4

def _lights(sun=True, soft=True):
    """sun = the Sun lamp; soft = fill area lights + sky (world)."""
    for o in bpy.data.objects:
        if o.type == 'LIGHT':
            o.hide_render = not (sun if o.name == "Sun" else soft)
    w = bpy.context.scene.world.node_tree.nodes["Background"].inputs["Strength"]
    if not hasattr(_lights, "world"):
        _lights.world = w.default_value
    w.default_value = _lights.world if soft else 0.0

SOFT_DIV = 4
SUN_SPP = 16
SOFT_SPP = 512

def bake_lighting(obj, res, name):
    """Sharp sun at full res + everything soft (fills, sky, all bounce) at 1/SOFT_DIV res."""
    lo = max(256, res // SOFT_DIV)
    try:
        _lights(sun=True, soft=False)
        Dsun = _bake_pass(obj, res, 'DIFFUSE', {'DIRECT'}, SUN_SPP, name + "_Ds")
        _lights(sun=False, soft=True)
        Dsoft = _bake_pass(obj, lo, 'DIFFUSE', {'DIRECT'}, SOFT_SPP, name + "_Df")
        _lights(sun=True, soft=True)
        I = _bake_pass(obj, lo, 'DIFFUSE', {'INDIRECT'}, SOFT_SPP, name + "_I")
    finally:
        _lights(sun=True, soft=True)
    soft = _blur(Dsoft + I, INDIRECT_BLUR.get(name, 1.0))
    return Dsun + _upsample(soft, res // lo)

def bake_group(name, res):
    """albedo x (sun + soft light) + emission (+ sheen), then graded to the final PNG."""
    obj = bpy.data.objects[name]
    bake_uv(obj)
    _metals_off(True)
    try:
        A = _bake_pass(obj, res, 'DIFFUSE', {'COLOR'}, 4, name + "_A")
        E = _bake_pass(obj, res, 'EMIT', set(), 1, name + "_E")
        L = bake_lighting(obj, res, name)
    finally:
        _metals_off(False)
    lin = A * L + E
    if name in GLOSSY_GROUPS:
        Gl = _bake_pass(obj, res, 'GLOSSY', {'DIRECT', 'COLOR'}, 16, name + "_G")
        lin = lin + Gl * GLOSSY_GROUPS[name]
    np.save(CACHE + "\\_" + name.lower() + "_lin.npy", lin.astype(np.float16))
    out = grade(lin).astype(np.float32)
    save_png(out, ATLAS_DIR + "\\" + name.lower() + ".png", name + "_png")
    return {"group": name, "res": res, "mean": float(out.mean())}

def regrade(groups=None):
    """Re-apply grade() to the saved linear bakes (tweak EXPOSURE etc. without re-baking)."""
    for name in (groups or ATLAS):
        lin = np.load(CACHE + "\\_" + name.lower() + "_lin.npy").astype(np.float32)
        save_png(grade(lin).astype(np.float32), ATLAS_DIR + "\\" + name.lower() + ".png", name + "_png")
    save_png(floor_preview_image().astype(np.float32), CACHE + "\\_floor_preview.png", "floor_preview_png")

def bake_floor():
    obj = bpy.data.objects["TH_Floor"]
    me = obj.data
    if "Bake" in me.uv_layers:
        me.uv_layers.remove(me.uv_layers["Bake"])
    uvl = me.uv_layers.new(name="Bake"); me.uv_layers.active = uvl
    HW, BACK, FV = 15.5, -27.1, 6.0
    for poly in me.polygons:
        for li in poly.loop_indices:
            v = me.vertices[me.loops[li].vertex_index].co          # Blender coords
            uvl.data[li].uv = ((v.x + HW) / (2 * HW), ((-v.y) - BACK) / (FV - BACK))
    # 1) light map (irradiance, no albedo): sharp direct + smooth low-res bounce
    L = bake_lighting(obj, FLOOR_LIGHT_RES, "floor")
    np.save(CACHE + "\\_floor_light.npy", L.astype(np.float16))
    enc = np.clip(L / LIGHT_MAX, 0, 1) ** (1 / 2.2)
    save_png(enc.astype(np.float32), OUT + "\\floor_light" + SUFFIX + ".png", "floor_light_png")
    # 2) tiling albedo: bake the marble onto a temporary 6x6 m plane
    me2 = bpy.data.meshes.new("_tile")
    s = FLOOR_TILE_M
    me2.from_pydata([(0, 0, 0), (s, 0, 0), (s, s, 0), (0, s, 0)], [], [(0, 1, 2, 3)])
    t_uv = me2.uv_layers.new(name="Tex"); b_uv = me2.uv_layers.new(name="Bake")
    for i, (u, v) in enumerate(((0, 0), (s, 0), (s, s), (0, s))):
        t_uv.data[i].uv = (u, v)                  # Tex = metres (lines never fall in 0..6)
        b_uv.data[i].uv = (u / s, v / s)
    me2.uv_layers.active = b_uv
    me2.materials.append(bpy.data.materials["Floor"])
    tile = bpy.data.objects.new("_tile", me2); bpy.context.scene.collection.objects.link(tile)
    tile.location = (200, 200, 0)
    A = _bake_pass(tile, FLOOR_TILE_RES, 'DIFFUSE', {'COLOR'}, 4, "floor_tile")
    # make it tile seamlessly: blend with a half-offset copy (slab seams sit every 3 m so they stay put)
    h, w = A.shape[:2]
    yy, xx = np.mgrid[0:h, 0:w].astype(np.float32)
    m = (1 - np.abs(2 * xx / (w - 1) - 1)) * (1 - np.abs(2 * yy / (h - 1) - 1))
    m = np.clip(m * 3.0, 0, 1)[..., None]
    A = A * m + np.roll(np.roll(A, h // 2, 0), w // 2, 1) * (1 - m)
    np.save(CACHE + "\\_floor_albedo.npy", A.astype(np.float16))
    if VARIANT == "day":       # the marble is the same for every variant: written once
        save_png(to_srgb(A).astype(np.float32), OUT + "\\floor_albedo.png", "floor_albedo_png")
    bpy.data.objects.remove(tile); bpy.data.meshes.remove(me2)
    return {"light_mean": float(L.mean()), "albedo_mean": float(A.mean())}

def floor_preview_image(res=2048):
    """What the Godot floor shader shows (without the reflection): grade(albedo * light) + court lines."""
    L = np.load(CACHE + "\\_floor_light.npy").astype(np.float32)
    A = np.load(CACHE + "\\_floor_albedo.npy").astype(np.float32)
    HW, BACK, FV = 15.5, -27.1, 6.0
    ys, xs = np.mgrid[0:res, 0:res].astype(np.float32)
    X = -HW + (xs + 0.5) / res * 2 * HW
    Z = BACK + (ys + 0.5) / res * (FV - BACK)         # row 0 = back of the hall (v = 0)
    lr = L.shape[0]
    li = np.clip(((Z - BACK) / (FV - BACK) * lr).astype(int), 0, lr - 1)
    lj = np.clip(((X + HW) / (2 * HW) * lr).astype(int), 0, lr - 1)
    light = L[li, lj]
    ar = A.shape[0]
    ai = (np.mod(-Z, FLOOR_TILE_M) / FLOOR_TILE_M * ar).astype(int) % ar
    aj = (np.mod(X, FLOOR_TILE_M) / FLOOR_TILE_M * ar).astype(int) % ar
    alb = A[ai, aj]
    lines = court_mask(X, Z)[..., None]
    line_col = np.array([0.80, 0.25, 0.035], np.float32)
    alb = alb * (1 - lines) + line_col * lines
    return grade(alb * light)

COURT_X, COURT_Z, COURT_W = 8.0, -17.5, 0.26
def court_mask(X, Z):
    side = (np.abs(np.abs(X) - COURT_X) < COURT_W / 2) & (Z > COURT_Z - COURT_W / 2)
    back = np.abs(Z - COURT_Z) < COURT_W / 2
    return (side | back).astype(np.float32)

def bake_all(groups=None):
    os.makedirs(CACHE, exist_ok=True); os.makedirs(ATLAS_DIR, exist_ok=True)
    show_lit_scene()
    w = bpy.context.scene.world.node_tree.nodes["Background"].inputs["Strength"]
    if w.default_value == 0.0:       # make_preview() switches the sky off
        w.default_value = bpy.context.scene.get("th_world_strength", 1.5)
    _hide_preview(True)
    res = [bake_group(g, ATLAS[g]) for g in (groups or ATLAS)]
    res.append(bake_floor())
    img = floor_preview_image()
    save_png(img.astype(np.float32), CACHE + "\\_floor_preview.png", "floor_preview_png")
    return res

# ----------------------------------------------------------------------
#  preview: rebuild the scene the way Godot will draw it (unlit textures + mirrored room)
# ----------------------------------------------------------------------
FLOOR_ALPHA_NEAR = 0.80      # opacity of the floor looking down (less reflection)
FLOOR_ALPHA_FAR = 0.45       # opacity at grazing angles (more reflection)

def _unlit_mat(name, image_path, uv="Bake", strength=1.0):
    if name in bpy.data.materials:
        bpy.data.materials.remove(bpy.data.materials[name])
    m = bpy.data.materials.new(name); m.use_nodes = True
    nt = m.node_tree; nt.nodes.clear()
    out = nt.nodes.new("ShaderNodeOutputMaterial")
    uvn = nt.nodes.new("ShaderNodeUVMap"); uvn.uv_map = uv
    tex = nt.nodes.new("ShaderNodeTexImage")
    tex.image = bpy.data.images.load(image_path, check_existing=True); tex.image.reload()
    tex.extension = 'EXTEND'
    em = nt.nodes.new("ShaderNodeEmission"); em.inputs["Strength"].default_value = strength
    tr = nt.nodes.new("ShaderNodeBsdfTransparent")
    lp = nt.nodes.new("ShaderNodeLightPath")
    mix = nt.nodes.new("ShaderNodeMixShader")
    nt.links.new(uvn.outputs[0], tex.inputs[0]); nt.links.new(tex.outputs[0], em.inputs[0])
    nt.links.new(lp.outputs["Is Camera Ray"], mix.inputs[0])
    nt.links.new(tr.outputs[0], mix.inputs[1]); nt.links.new(em.outputs[0], mix.inputs[2])
    nt.links.new(mix.outputs[0], out.inputs[0])
    return m

def _pv_copy(src, mat, name, mirror=False, coll=None):
    o = bpy.data.objects.new(name, src.data)
    (coll or bpy.context.scene.collection).objects.link(o)
    o.matrix_world = src.matrix_world.copy()
    if mirror:
        o.scale.z = -1
    for i, slot in enumerate(o.material_slots):
        slot.link = 'OBJECT'; slot.material = mat
    return o

def make_preview():
    pv = bpy.data.collections.get("BakedPreview") or bpy.data.collections.new("BakedPreview")
    if pv.name not in bpy.context.scene.collection.children:
        bpy.context.scene.collection.children.link(pv)
    for o in list(pv.objects):
        bpy.data.objects.remove(o)
    for g in ATLAS:
        m = _unlit_mat("PVM_" + g, ATLAS_DIR + "\\" + g.lower() + ".png")
        src = bpy.data.objects[g]
        _pv_copy(src, m, "PV_" + g, False, pv)
        _pv_copy(src, m, "PV_" + g + "_mirror", True, pv)
    outm = bpy.data.materials["Outside"]     # emission-only sky gradient (Godot draws the animated sky)
    src = bpy.data.objects["TH_Outside"]
    _pv_copy(src, outm, "PV_Outside", False, pv); _pv_copy(src, outm, "PV_Outside_mirror", True, pv)
    # floor: graded preview image over the mirrored room, fresnel-weighted
    fl = bpy.data.objects["TH_Floor"]
    m = bpy.data.materials.get("PVM_Floor") or bpy.data.materials.new("PVM_Floor")
    m.use_nodes = True; nt = m.node_tree; nt.nodes.clear()
    out = nt.nodes.new("ShaderNodeOutputMaterial")
    uvn = nt.nodes.new("ShaderNodeUVMap"); uvn.uv_map = "Bake"
    tex = nt.nodes.new("ShaderNodeTexImage")
    tex.image = bpy.data.images.load(CACHE + "\\_floor_preview.png", check_existing=True); tex.image.reload()
    nt.links.new(uvn.outputs[0], tex.inputs[0])     # pixel row 0 = v 0 = back of the hall
    em = nt.nodes.new("ShaderNodeEmission"); nt.links.new(tex.outputs[0], em.inputs[0])
    tr = nt.nodes.new("ShaderNodeBsdfTransparent")
    lw = nt.nodes.new("ShaderNodeLayerWeight"); lw.inputs["Blend"].default_value = 0.5
    pw = nt.nodes.new("ShaderNodeMath"); pw.operation = 'POWER'; pw.inputs[1].default_value = 3.0
    nt.links.new(lw.outputs["Facing"], pw.inputs[0])
    mr = nt.nodes.new("ShaderNodeMapRange")
    mr.inputs["To Min"].default_value = FLOOR_ALPHA_NEAR; mr.inputs["To Max"].default_value = FLOOR_ALPHA_FAR
    nt.links.new(pw.outputs[0], mr.inputs[0])
    mix = nt.nodes.new("ShaderNodeMixShader")
    nt.links.new(mr.outputs[0], mix.inputs[0])
    nt.links.new(tr.outputs[0], mix.inputs[1]); nt.links.new(em.outputs[0], mix.inputs[2])
    nt.links.new(mix.outputs[0], out.inputs[0])
    _pv_copy(fl, m, "PV_Floor", False, pv)
    # hide the lit scene while previewing
    for o in bpy.data.objects:
        if o.name.startswith("TH_") or o.name.startswith("Fill_") or o.name == "Sun":
            o.hide_render = True
    sc = bpy.context.scene
    sc.cycles.samples = 24; sc.cycles.use_denoising = False
    sc.cycles.transparent_max_bounces = 8
    w = sc.world.node_tree.nodes["Background"]; w.inputs["Strength"].default_value = 0.0
    return {"preview_objects": len(pv.objects)}

def show_lit_scene():
    for o in bpy.data.objects:
        if o.name.startswith("TH_") or o.name.startswith("Fill_") or o.name == "Sun":
            o.hide_render = (o.name == "TH_Glass")      # glass never takes part in the bake
        if o.name.startswith("PV_"):
            o.hide_render = True
    sc = bpy.context.scene
    sc.cycles.samples = 96; sc.cycles.use_denoising = True

# ----------------------------------------------------------------------
#  export: one .glb with the baked atlases (unlit materials) - the floor is built in Godot
# ----------------------------------------------------------------------
def make_shafts():
    """Crossed ribbons from each right-hand window along the sun direction (Godot shader fades them)."""
    from mathutils import Vector
    def G(x, y, z):
        return Vector((x, -z, y))
    b = bpy.data.objects["Sun"].matrix_world.to_quaternion() @ Vector((0, 0, -1))   # Blender-space travel dir
    d = Vector((b.x, b.z, -b.y)).normalized(); L = 14.0                              # -> Godot space
    HW, BACK, BAY, PIER = 15.5, -27.1, 4.2, 0.7
    zs = [BACK + 2.6 + i * BAY for i in range(12)]
    edges = [BACK + 1.0] + zs
    me = bpy.data.meshes.new("Shafts")
    bm = bmesh.new(); uv = bm.loops.layers.uv.new("UVMap")
    def ribbon(p0, p1):
        a, b = Vector(p0), Vector(p1)
        vs = [bm.verts.new(G(*a)), bm.verts.new(G(*b)), bm.verts.new(G(*(b + d * L))), bm.verts.new(G(*(a + d * L)))]
        f = bm.faces.new(vs)
        for l, t in zip(f.loops, ((0, 0), (0, 1), (1, 1), (1, 0))):
            l[uv].uv = t
    for a, b in zip(edges[:-1], edges[1:]):
        z0, z1 = a + PIER / 2, b - PIER / 2
        zc = (z0 + z1) / 2
        if not (-25.5 < zc < 4.0):
            continue
        ribbon((HW - 0.1, 1.2, zc), (HW - 0.1, 6.7, zc))
        ribbon((HW - 0.1, 3.9, z0 + 0.2), (HW - 0.1, 3.9, z1 - 0.2))
    bm.to_mesh(me); bm.free()
    m = bpy.data.materials.get("PVM_Shaft") or bpy.data.materials.new("PVM_Shaft")
    me.materials.append(m)
    o = bpy.data.objects.new("Shafts", me)
    return o

def export_glb(path=None):
    path = path or GLB
    ex = bpy.data.collections.get("Export") or bpy.data.collections.new("Export")
    if ex.name not in bpy.context.scene.collection.children:
        bpy.context.scene.collection.children.link(ex)
    for o in list(ex.objects):
        bpy.data.objects.remove(o)
    keep = []
    for g in list(ATLAS) + ["TH_Outside"]:
        src = bpy.data.objects[g]
        me = src.data.copy(); me.name = g + "_export"
        # only the Bake UV goes to the game (Outside keeps its Tex UV as UV0)
        uv_keep = "Tex" if g == "TH_Outside" else "Bake"
        for uvl in list(me.uv_layers):
            if uvl.name != uv_keep:
                me.uv_layers.remove(uvl)
        me.materials.clear()
        mname = "Outside" if g == "TH_Outside" else "PVM_" + g
        me.materials.append(bpy.data.materials[mname])
        for p in me.polygons:
            p.material_index = 0
        o = bpy.data.objects.new(g.replace("TH_", ""), me)
        ex.objects.link(o); keep.append(o)
    sh = make_shafts(); ex.objects.link(sh); keep.append(sh)
    gl = bpy.data.objects.get("TH_Glass")
    if gl:      # window panes: the Godot scene gives them a transparent material
        me = gl.data.copy(); me.name = "Glass_export"
        for uvl in list(me.uv_layers)[1:]:
            me.uv_layers.remove(uvl)
        me.materials.clear()
        me.materials.append(bpy.data.materials.get("PVM_Shaft") or bpy.data.materials.new("PVM_Shaft"))
        go = bpy.data.objects.new("Glass", me); ex.objects.link(go); keep.append(go)
    for o in bpy.context.view_layer.objects:
        o.select_set(o in keep)
    bpy.ops.export_scene.gltf(filepath=path, export_format='GLB', use_selection=True,
                              export_yup=True, export_apply=True, export_materials='EXPORT',
                              export_image_format='AUTO', export_texcoords=True, export_normals=False,
                              export_cameras=False, export_lights=False, export_extras=False)
    for o in keep:
        me = o.data
        bpy.data.objects.remove(o)
        if me.users == 0:
            bpy.data.meshes.remove(me)
    _force_unlit(path)
    return {"glb": path, "bytes": os.path.getsize(path)}

def _force_unlit(path):
    """Mark every material KHR_materials_unlit in the glb JSON chunk (belt and braces)."""
    data = open(path, "rb").read()
    magic, ver, total = struct.unpack_from("<III", data, 0)
    jlen, jtype = struct.unpack_from("<II", data, 12)
    js = json.loads(data[20:20 + jlen].decode("utf-8"))
    for m in js.get("materials", []):
        m.setdefault("extensions", {})["KHR_materials_unlit"] = {}
        # single-sided: double-sided faces that touch other faces z-fight (flicker) when the camera moves.
        # The mirrored Reflection copy still works: Godot flips culling for negative scale.
        m["doubleSided"] = m.get("name") == "PVM_Shaft"
        em = m.pop("emissiveTexture", None); m.pop("emissiveFactor", None)
        m.get("extensions", {}).pop("KHR_materials_emissive_strength", None)
        pbr = m.setdefault("pbrMetallicRoughness", {})
        if "baseColorTexture" not in pbr and em:
            pbr["baseColorTexture"] = em
        pbr["metallicFactor"] = 0.0; pbr["roughnessFactor"] = 1.0
    used = set(js.get("extensionsUsed", [])); used.add("KHR_materials_unlit")
    js["extensionsUsed"] = sorted(used)
    nj = json.dumps(js, separators=(",", ":")).encode("utf-8")
    nj += b" " * ((4 - len(nj) % 4) % 4)
    rest = data[20 + jlen:]
    out = struct.pack("<III", magic, ver, 12 + 8 + len(nj) + len(rest)) + struct.pack("<II", len(nj), jtype) + nj + rest
    open(path, "wb").write(out)
