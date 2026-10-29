# Old Schoolhouse -Entrance- - bake, grade, preview and export (Blender 5.x, works in --background).
# Lighting is baked with Cycles, graded here with grade(), and shown UNSHADED in Godot.
# The floor bakes a light map only (moonlight patches, lantern pools); Godot's floor shader draws the slate tiles.
#   night: src/baked/, src/cache/, textures/floor_light.png, schoolhouse_entrance.glb
import bpy, bmesh, math, os, json, struct
import numpy as np

ROOT = r"E:\Netsu Projects\Netsu Fighter\Godot\netsu-vs\stages\schoolhouse_entrance"
VARIANT = globals().get("VARIANT") or bpy.context.scene.get("ce_variant", "night")
SUFFIX = "" if VARIANT == "night" else "_" + VARIANT
OUT = ROOT + r"\textures"
ATLAS_DIR = ROOT + r"\src\baked" + SUFFIX
CACHE = ROOT + r"\src\cache" + ("" if VARIANT == "night" else "\\" + VARIANT)
ATLAS = {"SE_Walls": 4096, "SE_Detail": 4096, "SE_Ceiling": 2048}
CARDS = [g for g in ("SE_Window", "SE_Glow", "SE_Beam") if g in bpy.data.objects]
HIDDEN_CARDS = ("SE_Beam",)       # moonbeams are drawn in Godot only
FLOOR_X, FLOOR_BACK, FLOOR_FRONT = 18.0, -24.5, 16.0
FLOOR_LIGHT = (2048, 2048)
LIGHT_MAX = 4.0              # floor light map encoding: stored = (light / LIGHT_MAX) ** (1/2.2)
D_SPP, I_SPP, I_DIV = 48, 256, 4
MARGIN_PX = 16

# ---- look (keep in sync with the floor material's "look" group in the variant's .tscn) ----
LOOKS = {   # keep in sync with the floor material's "look" group in schoolhouse_entrance.tscn
    "night": dict(EXPOSURE=0.45, SHOULDER=0.8, SATURATION=1.0, SHADOW_TINT=(0.86, 0.92, 1.2),
                  HIGHLIGHT_TINT=(1.08, 1.0, 0.9), TINT_AMOUNT=0.55),
}
globals().update(LOOKS[VARIANT])

def grade(lin):
    c = np.maximum(lin, 0.0) * (2.0 ** EXPOSURE)
    over = np.maximum(c - SHOULDER, 0.0)
    c = np.where(c > SHOULDER, SHOULDER + (1 - SHOULDER) * (1 - np.exp(-over / (1 - SHOULDER))), c)
    lum = (c * np.array([0.2126, 0.7152, 0.0722], np.float32)).sum(-1, keepdims=True)
    c = lum + (c - lum) * SATURATION
    sh = np.clip(1.0 - lum / 0.45, 0, 1) ** 1.5 * TINT_AMOUNT
    hi = np.clip((lum - 0.5) / 0.5, 0, 1) * TINT_AMOUNT
    c = c * (1 - sh + sh * np.array(SHADOW_TINT, np.float32))
    c = c * (1 - hi + hi * np.array(HIGHLIGHT_TINT, np.float32))
    return to_srgb(c)

def to_srgb(c):
    c = np.clip(c, 0, 1)
    return np.where(c <= 0.0031308, c * 12.92, 1.055 * np.power(c, 1 / 2.4) - 0.055)

def from_srgb(c):
    return np.where(c <= 0.04045, c / 12.92, ((c + 0.055) / 1.055) ** 2.4)

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
    rgba = np.concatenate([rgb, np.ones((h, w, 1), np.float32)], -1).astype(np.float32)
    im.pixels.foreach_set(rgba.ravel())
    im.filepath_raw = path; im.file_format = 'PNG'; im.save()
    return im

def load_png(path):
    im = bpy.data.images.load(path, check_existing=False)
    a = _px(im)[..., :3].copy()
    bpy.data.images.remove(im)
    return a

def _select_only(obj):
    for o in bpy.context.view_layer.objects:
        o.select_set(False)
    obj.select_set(True)
    bpy.context.view_layer.objects.active = obj

def bake_uv(obj, margin=0.0015):
    me = obj.data
    if "Bake" in me.uv_layers:
        me.uv_layers.remove(me.uv_layers["Bake"])
    me.uv_layers.active = me.uv_layers.new(name="Bake")
    _select_only(obj)
    bpy.ops.object.mode_set(mode='EDIT')
    bpy.ops.mesh.select_all(action='SELECT')
    bpy.ops.uv.smart_project(angle_limit=math.radians(66), island_margin=margin,
                             area_weight=0.0, correct_aspect=True, scale_to_bounds=False)
    bpy.ops.uv.pack_islands(rotate=True, margin=margin)
    bpy.ops.object.mode_set(mode='OBJECT')

def _bake_target(obj, img):
    for slot in obj.material_slots:
        nt = slot.material.node_tree
        nd = nt.nodes.get("BAKE_TARGET") or nt.nodes.new("ShaderNodeTexImage")
        nd.name = "BAKE_TARGET"; nd.image = img; nd.location = (1400, 400)
        nt.nodes.active = nd

def _bake_pass(obj, res, kind, passes, samples, name):
    w, h = (res, res) if isinstance(res, int) else res
    img = bpy.data.images.new(name, w, h, alpha=False, float_buffer=True)
    _bake_target(obj, img); _select_only(obj)
    sc = bpy.context.scene
    sc.render.engine = 'CYCLES'; sc.cycles.samples = samples
    b = sc.render.bake
    b.use_pass_direct = 'DIRECT' in passes; b.use_pass_indirect = 'INDIRECT' in passes
    b.use_pass_color = 'COLOR' in passes
    b.margin = max(4, MARGIN_PX * w // 4096); b.margin_type = 'EXTEND'
    b.use_clear = True; b.target = 'IMAGE_TEXTURES'
    bpy.ops.object.bake(type=kind)
    a = _px(img)[..., :3].copy()
    bpy.data.images.remove(img)
    return a

def _blur(a, r=1.5):
    if r <= 0:
        return a
    k = int(math.ceil(r * 3)); x = np.arange(-k, k + 1, dtype=np.float32)
    wts = np.exp(-x * x / (2 * r * r)); wts /= wts.sum()
    for ax in (0, 1):
        a = sum(np.roll(a, int(i), ax) * wi for i, wi in zip(x, wts))
    return a

def _upsample(a, f):
    h, w = a.shape[:2]
    y = (np.arange(h * f) + 0.5) / f - 0.5
    y0 = np.floor(y).astype(int); wy = (y - y0).astype(np.float32)[:, None, None]
    a = a[np.clip(y0, 0, h - 1)] * (1 - wy) + a[np.clip(y0 + 1, 0, h - 1)] * wy
    x = (np.arange(w * f) + 0.5) / f - 0.5
    x0 = np.floor(x).astype(int); wx = (x - x0).astype(np.float32)[None, :, None]
    return a[:, np.clip(x0, 0, w - 1)] * (1 - wx) + a[:, np.clip(x0 + 1, 0, w - 1)] * wx

_MET = {}
def _metals_off(off=True):
    for m in bpy.data.materials:
        if not m.use_nodes:
            continue
        for nd in m.node_tree.nodes:
            if nd.type == 'BSDF_PRINCIPLED':
                k = (m.name, nd.name)
                if off:
                    _MET[k] = nd.inputs["Metallic"].default_value; nd.inputs["Metallic"].default_value = 0.0
                elif k in _MET:
                    nd.inputs["Metallic"].default_value = _MET[k]

def lit_scene():
    for o in bpy.data.objects:
        if o.name.startswith("PV_") or o.name.startswith("Preview"):
            o.hide_render = True
        elif o.name.startswith("SE_"):
            o.hide_render = o.name in HIDDEN_CARDS      # windows and lanterns emit in the bake
        elif o.type == 'LIGHT':
            o.hide_render = False
    w = bpy.context.scene.world.node_tree.nodes["Background"].inputs["Strength"]
    if w.default_value == 0.0:
        w.default_value = bpy.context.scene.get("ce_world_strength", 1.0)

def bake_lighting(obj, res, name, d_blur=0.6):
    w, h = (res, res) if isinstance(res, int) else res
    lo = (max(128, w // I_DIV), max(128, h // I_DIV))
    D = _bake_pass(obj, (w, h), 'DIFFUSE', {'DIRECT'}, D_SPP, name + "_D")
    I = _bake_pass(obj, lo, 'DIFFUSE', {'INDIRECT'}, I_SPP, name + "_I")
    return _blur(D, d_blur) + _upsample(_blur(I, 1.0), w // lo[0])

def bake_group(name, res):
    obj = bpy.data.objects[name]
    bake_uv(obj)
    _metals_off(True)
    try:
        A = _bake_pass(obj, res, 'DIFFUSE', {'COLOR'}, 4, name + "_A")
        E = _bake_pass(obj, res, 'EMIT', set(), 4, name + "_E")
        L = bake_lighting(obj, res, name)
    finally:
        _metals_off(False)
    lin = A * L + E
    np.save(CACHE + "\\_" + name.lower() + "_lin.npy", lin.astype(np.float16))
    out = grade(lin).astype(np.float32)
    save_png(out, ATLAS_DIR + "\\" + name.lower() + ".png", name + "_png")
    return {"group": name, "mean": float(out.mean())}

def bake_floor():
    obj = bpy.data.objects["SE_Floor"]
    me = obj.data
    if "Bake" in me.uv_layers:
        me.uv_layers.remove(me.uv_layers["Bake"])
    uvl = me.uv_layers.new(name="Bake"); me.uv_layers.active = uvl
    for poly in me.polygons:
        for li in poly.loop_indices:
            v = me.vertices[me.loops[li].vertex_index].co
            uvl.data[li].uv = ((v.x + FLOOR_X) / (2 * FLOOR_X), ((-v.y) - FLOOR_BACK) / (FLOOR_FRONT - FLOOR_BACK))
    L = bake_lighting(obj, FLOOR_LIGHT, "floor", d_blur=1.0)
    np.save(CACHE + "\\_floor_light.npy", L.astype(np.float16))
    enc = np.clip(L / LIGHT_MAX, 0, 1) ** (1 / 2.2)
    save_png(enc.astype(np.float32), OUT + "\\floor_light" + SUFFIX + ".png", "floor_light_png")
    return {"floor_light_mean": float(L.mean())}

FLOOR_TILE_M = 4.0

def floor_preview_image(res=(1024, 1024)):
    """Blender preview of the floor: a flat slate colour x light (Godot draws the real tiles)."""
    L = np.load(CACHE + "\\_floor_light.npy").astype(np.float32)
    return grade(L * np.array([0.12, 0.14, 0.18], np.float32))

def bake_all(groups=None):
    os.makedirs(CACHE, exist_ok=True); os.makedirs(ATLAS_DIR, exist_ok=True)
    lit_scene()
    res = [bake_group(g, ATLAS[g]) for g in (groups or ATLAS)]
    res.append(bake_floor())
    save_png(floor_preview_image().astype(np.float32), CACHE + "\\_floor_preview.png", "floor_preview_png")
    return res

def regrade(groups=None):
    for name in (groups or ATLAS):
        lin = np.load(CACHE + "\\_" + name.lower() + "_lin.npy").astype(np.float32)
        out = grade(lin).astype(np.float32)
        save_png(out, ATLAS_DIR + "\\" + name.lower() + ".png", name + "_png")
    save_png(floor_preview_image().astype(np.float32), CACHE + "\\_floor_preview.png", "floor_preview_png")

# ----------------------------------------------------------------------
#  preview: what Godot draws (unlit atlases + mirrored world under a see-through floor)
# ----------------------------------------------------------------------
FLOOR_ALPHA_NEAR, FLOOR_ALPHA_FAR = 0.78, 0.45

def _unlit_mat(name, image_path, uv="Bake", strength=1.0, alpha=False, tint=None):
    if name in bpy.data.materials:
        bpy.data.materials.remove(bpy.data.materials[name])
    m = bpy.data.materials.new(name); m.use_nodes = True
    m.use_backface_culling = True
    nt = m.node_tree; nt.nodes.clear()
    out = nt.nodes.new("ShaderNodeOutputMaterial")
    uvn = nt.nodes.new("ShaderNodeUVMap"); uvn.uv_map = uv
    tex = nt.nodes.new("ShaderNodeTexImage")
    tex.image = bpy.data.images.load(image_path, check_existing=True); tex.image.reload()
    em = nt.nodes.new("ShaderNodeEmission"); em.inputs["Strength"].default_value = strength
    nt.links.new(uvn.outputs[0], tex.inputs[0])
    if tint:
        mul = nt.nodes.new("ShaderNodeMix"); mul.data_type = 'RGBA'; mul.blend_type = 'MULTIPLY'
        mul.inputs[0].default_value = 1.0; nt.links.new(tex.outputs[0], mul.inputs[6])
        mul.inputs[7].default_value = (*tint, 1); nt.links.new(mul.outputs[2], em.inputs[0])
    else:
        nt.links.new(tex.outputs[0], em.inputs[0])
    tr = nt.nodes.new("ShaderNodeBsdfTransparent")
    lp = nt.nodes.new("ShaderNodeLightPath")
    mix = nt.nodes.new("ShaderNodeMixShader")
    if alpha:
        mm = nt.nodes.new("ShaderNodeMath"); mm.operation = 'MULTIPLY'
        nt.links.new(lp.outputs["Is Camera Ray"], mm.inputs[0]); nt.links.new(tex.outputs["Alpha"], mm.inputs[1])
        nt.links.new(mm.outputs[0], mix.inputs[0])
    else:
        nt.links.new(lp.outputs["Is Camera Ray"], mix.inputs[0])
    nt.links.new(tr.outputs[0], mix.inputs[1]); nt.links.new(em.outputs[0], mix.inputs[2])
    nt.links.new(mix.outputs[0], out.inputs[0])
    return m

def _pv_copy(src, mat, name, mirror, coll):
    o = bpy.data.objects.new(name, src.data); coll.objects.link(o)
    o.matrix_world = src.matrix_world.copy()
    if mirror:
        o.scale.z = -1
    for slot in o.material_slots:
        slot.link = 'OBJECT'; slot.material = mat
    return o

CARD_LOOK = {   # Blender preview stand-ins for the Godot card shaders (their own emissive materials)
    "SE_Window": "WindowCard", "SE_Glow": "GlowLantern"}

def make_preview():
    pv = bpy.data.collections.get("BakedPreview") or bpy.data.collections.new("BakedPreview")
    if pv.name not in bpy.context.scene.collection.children:
        bpy.context.scene.collection.children.link(pv)
    for o in list(pv.objects):
        bpy.data.objects.remove(o)
    for g in ATLAS:
        m = _unlit_mat("PVM_" + g, ATLAS_DIR + "\\" + g.lower() + ".png")
        _pv_copy(bpy.data.objects[g], m, "PV_" + g, False, pv)
        _pv_copy(bpy.data.objects[g], m, "PV_" + g + "_m", True, pv)
    for g, mname in CARD_LOOK.items():
        m = bpy.data.materials[mname]
        _pv_copy(bpy.data.objects[g], m, "PV_" + g, False, pv)
    # floor
    fl = bpy.data.objects["SE_Floor"]
    m = bpy.data.materials.get("PVM_Floor") or bpy.data.materials.new("PVM_Floor")
    m.use_nodes = True; nt = m.node_tree; nt.nodes.clear()
    out = nt.nodes.new("ShaderNodeOutputMaterial")
    uvn = nt.nodes.new("ShaderNodeUVMap"); uvn.uv_map = "Bake"
    tex = nt.nodes.new("ShaderNodeTexImage")
    tex.image = bpy.data.images.load(CACHE + "\\_floor_preview.png", check_existing=True); tex.image.reload()
    nt.links.new(uvn.outputs[0], tex.inputs[0])
    em = nt.nodes.new("ShaderNodeEmission"); nt.links.new(tex.outputs[0], em.inputs[0])
    tr = nt.nodes.new("ShaderNodeBsdfTransparent")
    lw = nt.nodes.new("ShaderNodeLayerWeight"); lw.inputs["Blend"].default_value = 0.5
    pw = nt.nodes.new("ShaderNodeMath"); pw.operation = 'POWER'; pw.inputs[1].default_value = 3.0
    nt.links.new(lw.outputs["Facing"], pw.inputs[0])
    mr = nt.nodes.new("ShaderNodeMapRange")
    mr.inputs["To Min"].default_value = FLOOR_ALPHA_NEAR; mr.inputs["To Max"].default_value = FLOOR_ALPHA_FAR
    nt.links.new(pw.outputs[0], mr.inputs[0])
    mix = nt.nodes.new("ShaderNodeMixShader")
    nt.links.new(mr.outputs[0], mix.inputs[0]); nt.links.new(tr.outputs[0], mix.inputs[1])
    nt.links.new(em.outputs[0], mix.inputs[2]); nt.links.new(mix.outputs[0], out.inputs[0])
    _pv_copy(fl, m, "PV_Floor", False, pv)
    for o in bpy.data.objects:
        if o.name.startswith("SE_") or o.type == 'LIGHT' or o.name.startswith("Preview"):
            o.hide_render = True
    sc = bpy.context.scene
    sc.cycles.samples = 24; sc.cycles.use_denoising = False; sc.cycles.transparent_max_bounces = 24
    sc.world.node_tree.nodes["Background"].inputs["Strength"].default_value = 0.0
    return {"preview_objects": len(pv.objects)}

# ----------------------------------------------------------------------
#  export
# ----------------------------------------------------------------------
NAMES = {"SE_Walls": "Walls", "SE_Detail": "Detail", "SE_Ceiling": "Ceiling", "SE_Window": "Window", "SE_Glow": "Glow",
         "SE_Beam": "Beam"}

def export_glb(path=None):
    path = path or ROOT + r"\schoolhouse_entrance" + SUFFIX + ".glb"
    ex = bpy.data.collections.get("Export") or bpy.data.collections.new("Export")
    if ex.name not in bpy.context.scene.collection.children:
        bpy.context.scene.collection.children.link(ex)
    for o in list(ex.objects):
        bpy.data.objects.remove(o)
    keep = []
    for g in list(ATLAS) + CARDS:
        src = bpy.data.objects[g]
        me = src.data.copy(); me.name = g + "_export"
        uv_keep = "Bake" if g in ATLAS else "Tex"
        for uvl in list(me.uv_layers):
            if uvl.name != uv_keep:
                me.uv_layers.remove(uvl)
        _cut_below_floor(me)
        me.materials.clear()
        mat = bpy.data.materials.get("PVM_" + g) if g in ATLAS else None
        if mat is None:
            mat = bpy.data.materials.get("EXP_card") or bpy.data.materials.new("EXP_card")
        me.materials.append(mat)
        for p in me.polygons:
            p.material_index = 0
        o = bpy.data.objects.new(NAMES[g], me); ex.objects.link(o); keep.append(o)
    for o in bpy.context.view_layer.objects:
        o.select_set(o in keep)
    bpy.ops.export_scene.gltf(filepath=path, export_format='GLB', use_selection=True, export_yup=True,
                              export_apply=True, export_materials='EXPORT', export_image_format='AUTO',
                              export_texcoords=True, export_normals=True, export_cameras=False,
                              export_lights=False, export_extras=False)
    for o in keep:
        me = o.data; bpy.data.objects.remove(o)
        if me is not None and me.users == 0:
            bpy.data.meshes.remove(me)
    _force_unlit(path)
    return {"glb": path, "bytes": os.path.getsize(path)}

def _cut_below_floor(me):
    """Remove everything under y = 0. The Reflection node mirrors the whole model through the floor,
    so anything below the floor would pop up above it (e.g. sunk spire/mountain bases)."""
    bm = bmesh.new(); bm.from_mesh(me)
    geom = list(bm.verts) + list(bm.edges) + list(bm.faces)
    bmesh.ops.bisect_plane(bm, geom=geom, dist=1e-5, plane_co=(0, 0, 0), plane_no=(0, 0, 1), clear_inner=True)
    bm.to_mesh(me); bm.free()
    _uv_active(me)

def _uv_active(me):
    if len(me.uv_layers):
        me.uv_layers.active = me.uv_layers[0]
        me.uv_layers[0].active_render = True

def _force_unlit(path):
    data = open(path, "rb").read()
    magic, ver, total = struct.unpack_from("<III", data, 0)
    jlen, jtype = struct.unpack_from("<II", data, 12)
    js = json.loads(data[20:20 + jlen].decode("utf-8"))
    for m in js.get("materials", []):
        m.setdefault("extensions", {})["KHR_materials_unlit"] = {}
        em = m.pop("emissiveTexture", None); m.pop("emissiveFactor", None)
        m["extensions"].pop("KHR_materials_emissive_strength", None)
        pbr = m.setdefault("pbrMetallicRoughness", {})
        if "baseColorTexture" not in pbr and em:
            pbr["baseColorTexture"] = em
        pbr["metallicFactor"] = 0.0; pbr["roughnessFactor"] = 1.0
        m["doubleSided"] = m.get("name") == "EXP_card"      # baked rock = single-sided (no z-fighting)
    used = set(js.get("extensionsUsed", [])); used.add("KHR_materials_unlit")
    js["extensionsUsed"] = sorted(used)
    nj = json.dumps(js, separators=(",", ":")).encode("utf-8"); nj += b" " * ((4 - len(nj) % 4) % 4)
    rest = data[20 + jlen:]
    out = struct.pack("<III", magic, ver, 20 + len(nj) + len(rest)) + struct.pack("<II", len(nj), jtype) + nj + rest
    open(path, "wb").write(out)
