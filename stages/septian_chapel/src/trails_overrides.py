# Septian Chapel - "Trails" variant overrides (VARIANT=trails). exec'd at the end of build_septian_chapel.py,
# in its globals, so it can wrap the builders. Look: Trails in the Sky / Crossbell Cathedral.
#   * grey dressed stone, blue-grey slate, weathered stone walls and planks: CC0 photo textures (src/textures_cc0,
#     Poly Haven) on the "Tex" UVs (metres), tinted to the palette
#   * every big foliage blob (oak, yews, bushes, woods) becomes a cluster of small jagged leaf clumps with a leafy
#     cell material (Celdic's approach), and the poplars become columns of clumps
#   * Crossbell-style lamp posts around the square and flanking the walk to the steps
import bpy, math, random
CC0 = ROOT + r"\src\textures_cc0"

_AVG = {}
def _avg(img):
    """Mean linear luminance of an image (photo textures are normalised by it, so the tint sets the colour)."""
    if img.name not in _AVG:
        import numpy as np
        a = np.empty(img.size[0] * img.size[1] * 4, np.float32); img.pixels.foreach_get(a)
        a = a.reshape(-1, 4)[::97, :3] ** 2.2        # stored sRGB -> linear
        _AVG[img.name] = max(float((a * [0.2126, 0.7152, 0.0722]).sum(1).mean()), 1e-3)
    return _AVG[img.name]

def photo(name, fn, tile, tint, rough=0.75, dirt=True, var=0.18, haze=None, mono=False, level=0.62):
    b = NB(name)
    sc = b.n("ShaderNodeVectorMath", operation='SCALE'); sc.inputs[3].default_value = 1.0 / tile
    b.link(b.uv, sc.inputs[0])
    im = b.n("ShaderNodeTexImage"); im.image = bpy.data.images.load(CC0 + "\\" + fn, check_existing=True)
    b.link(sc.outputs[0], im.inputs[0])
    norm = b.n("ShaderNodeVectorMath", operation='SCALE'); norm.inputs[3].default_value = level / _avg(im.image)
    src = im.outputs["Color"]
    if mono:                                             # keep only the photo's light/dark grain; the tint is the colour
        bw = b.n("ShaderNodeRGBToBW"); b.link(src, bw.inputs[0]); src = bw.outputs[0]
    b.link(src, norm.inputs[0])                          # photo / its own average, then tinted
    c = b.mixc(norm.outputs[0], tint, 1.0, 'MULTIPLY')
    n = b.noise(b.pos, 0.35, 3, 0.5)
    c = b.mixc(c, b.ramp(n.outputs["Fac"], [(0.3, "#%02x%02x%02x" % ((int(255 * (1 - var)),) * 3)), (0.7, "#ffffff")]), 1.0, 'MULTIPLY')
    if dirt:
        sep = b.n("ShaderNodeSeparateXYZ"); b.link(b.pos, sep.inputs[0])
        g = b.math('MINIMUM', b.math('MULTIPLY', sep.outputs[2], 0.8), 1.0)
        c = b.mixc(b.mixc("#7e7a70", "#ffffff", g), c, 1.0, 'MULTIPLY')
    b.link(c, b.bsdf.inputs["Base Color"]); b.bsdf.inputs["Roughness"].default_value = rough
    if haze:
        add_haze(b, *haze)
    return b

def leaves(name, dark, mid, light, haze=None, scale=7.0):
    b = NB(name)
    vo = b.n("ShaderNodeTexVoronoi"); vo.inputs["Scale"].default_value = scale; b.link(b.pos, vo.inputs["Vector"])
    n = b.noise(b.pos, 1.5, 4, 0.6)
    c = b.ramp(vo.outputs["Distance"], [(0.05, light), (0.35, mid), (0.75, dark)])
    c = b.mixc(c, dark, b.math('MULTIPLY', n.outputs["Fac"], 0.45))
    b.link(c, b.bsdf.inputs["Base Color"]); b.bsdf.inputs["Roughness"].default_value = 0.7
    b.bsdf.inputs["Subsurface Weight"].default_value = 0.08
    bump = b.n("ShaderNodeBump"); bump.inputs["Strength"].default_value = 0.6
    b.link(vo.outputs["Distance"], bump.inputs["Height"]); b.link(bump.outputs[0], b.bsdf.inputs["Normal"])
    if haze:
        add_haze(b, *haze)
    return b

_orig_build_materials = build_materials
def build_materials():
    _orig_build_materials()
    for nm in ("Limestone", "StoneTrim", "Slate", "Fieldstone", "Wood", "Timber", "OakLeaf", "Yew", "Foliage", "Forest"):
        bpy.data.materials.remove(MATS.pop(nm))
    photo("Limestone", "stone_brick_wall_001_diff_2k.jpg", 2.4, "#cfcdc8", mono=True)
    plain("StoneTrim", "#b4b0a6", "#cac6bc", 4.0, 0.6)
    photo("Slate", "grey_roof_tiles_diff_2k.jpg", 2.2, "#7e8a9e", 0.5, dirt=False, mono=True)
    photo("Fieldstone", "old_stone_wall_diff_2k.jpg", 2.6, "#bdb9b0", mono=True)
    photo("Wood", "weathered_planks_diff_2k.jpg", 1.6, "#c09070", 0.8, dirt=False)
    photo("Timber", "weathered_planks_diff_2k.jpg", 1.6, "#7a5a44", 0.8, dirt=False)
    for sfx, k in (("", 0), ("2", 1), ("3", 2)):
        leaves("OakLeaf" + sfx, *(("#244a1c", "#3e7228", "#74a83c"), ("#2e5218", "#548228", "#90b844"), ("#1e3e20", "#38662e", "#62944a"))[k])
        leaves("Yew" + sfx, *(("#142e18", "#24482a", "#3e6a36"), ("#18341a", "#2c5228", "#4a7a38"), ("#102814", "#1e4024", "#34603a"))[k])
        leaves("Foliage" + sfx, *(("#2a5420", "#4a7e2e", "#7aac44"), ("#30581c", "#58882a", "#8eb848"), ("#244a24", "#40703a", "#68984a"))[k])
    leaves("Forest", "#1e3a1c", "#2e5226", "#4a7236", haze=(HZ, 90, 480, 0.68), scale=1.2)
    for nm in ("Plaster", "RoofTile", "Headstone", "PaintWhite"):
        bpy.data.materials.remove(MATS.pop(nm))
    photo("Plaster", "plastered_stone_wall_diff_2k.jpg", 3.0, "#ece4d4", 0.85, mono=True, var=0.1)
    photo("RoofTile", "clay_roof_tiles_diff_2k.jpg", 2.0, "#b4583c", 0.6, dirt=False, mono=True)
    photo("Headstone", "old_stone_wall_diff_2k.jpg", 1.4, "#b0aea8", 0.7, mono=True)
    photo("PaintWhite", "white_planks_clean_diff_2k.jpg", 1.2, "#f4f0e8", 0.7, dirt=False, mono=True, var=0.08, level=0.9)
    photo("WellStone", "mossy_cobblestone_diff_2k.jpg", 1.1, "#c4c0b2", 0.8)
    plain("LampStone", "#3a3c40", "#4a4c52", 5.0, 0.6)
    emit_solid("LampGlass", "#ffd890", 3.0)

LEAFY = ("OakLeaf", "Yew", "Foliage", "Forest")
def leaf_clump(gg, x, y, z, s, seed, m, jag=0.38):
    rnd = random.Random(seed)
    M = Matrix.Translation(G(x, y, z)) @ Matrix.Rotation(rnd.uniform(0, 6.28), 4, 'Z') @ Matrix.Diagonal((s * rnd.uniform(0.8, 1.25), s * rnd.uniform(0.8, 1.25), s * rnd.uniform(0.6, 0.95), 1.0))
    r = bmesh.ops.create_icosphere(gg.bm, subdivisions=1, radius=1.0, matrix=M)
    c = G(x, y, z)
    for v in r["verts"]:
        v.co = c + (v.co - c) * rnd.uniform(1 - jag, 1 + jag * 0.45)
    _tag(gg, list({f for v in r["verts"] for f in v.link_faces}), m)

_orig_ico = ico
def ico(g, c, r, m, seed, sy=0.85, sub=1):
    if m not in LEAFY or r < 0.9:
        return _orig_ico(g, c, r, m, seed, sy, sub)
    gg = grp(g) if isinstance(g, str) else g
    rnd = random.Random(seed * 31 + 7)
    far = math.hypot(c[0], c[2] - CENTER_Z) > 70 or m == "Forest"
    n = 6 if far else min(26, int(6 + 4 * r * r))
    _orig_ico(gg, (c[0], c[1] - r * 0.1 * sy, c[2]), r * 0.72, m if far else m + "3", seed, sy, 1)   # a dark core fills the gaps
    for k in range(n):
        a = rnd.uniform(0, 2 * math.pi); e = rnd.uniform(-0.6, 1.0); rr = r * (0.55 + 0.45 * rnd.random() ** 0.5)
        p = (c[0] + rr * math.cos(a) * math.sqrt(1 - e * e * 0.6), c[1] + rr * e * sy * 0.85, c[2] + rr * math.sin(a) * math.sqrt(1 - e * e * 0.6))
        mm = m if far else rnd.choice((m, m, m + "2", m + "3")) if e < 0.3 else rnd.choice((m, m + "2", m + "2"))
        leaf_clump(gg, *p, r * rnd.uniform(0.32, 0.5), seed * 97 + k, mm)

_orig_lathe = lathe
def lathe(g, x, y0, z, prof, seg=12, m="Steel", rot=0.0):
    if m == "Fieldstone" and abs(x + 11.2) < 0.01 and abs(z + 15.6) < 0.01:
        m = "WellStone"                                  # the well: mossy rounded stones, not the wall's slabs
    if m != "Forest" or max(h for _, h in prof) < 10:
        return _orig_lathe(g, x, y0, z, prof, seg, m, rot)
    gg = grp(g) if isinstance(g, str) else g
    _orig_lathe(gg, x, y0, z, [(0, 0), (0.3, 0.0), (0.25, 4.0), (0, 4.2)], 6, "Bark")
    H = max(h for _, h in prof); rnd = random.Random(int(x * 13 + z))
    def rad(h):
        for (r0, h0), (r1, h1) in zip(prof[:-1], prof[1:]):
            if h0 <= h <= h1 and h1 > h0:
                return r0 + (r1 - r0) * (h - h0) / (h1 - h0)
        return 0.3
    _orig_lathe(gg, x, y0, z, [(r * 0.6, min(h, H * 0.66)) for r, h in prof[:-1]] + [(0, H * 0.68)], 8, "Forest")   # a solid core, kept inside the clumps
    for k in range(14):
        h = 2.5 + (H * 0.86 - 2.5) * k / 13; r = max(0.85, rad(h))
        for j in range(3 if k < 11 else 0):
            a = rnd.uniform(0, 2 * math.pi); o = r * (0.45 if k < 12 else 0.2)
            leaf_clump(gg, x + math.cos(a) * o, y0 + h, z + math.sin(a) * o, r * 0.72, int(x * 7) + k * 3 + j, "Forest", 0.25)

def lamp_post(x, z, seed=0):
    g = "CH_Village"
    box(g, x, 0.0, 0.32, z, 0.62, 0.62, "StoneTrim", 0.03)
    box(g, x, 0.32, 0.46, z, 0.5, 0.5, "LampStone", 0.02)
    box(g, x, 0.46, 1.95, z, 0.3, 0.3, "LampStone", 0.02)
    box(g, x, 1.95, 2.08, z, 0.46, 0.46, "StoneTrim", 0.02)
    box(g, x, 2.08, 2.5, z, 0.32, 0.32, "LampGlass")
    for sx in (-1, 1):
        for sz in (-1, 1):
            box(g, x + sx * 0.16, 2.08, 2.5, z + sz * 0.16, 0.05, 0.05, "Iron")
    box(g, x, 2.5, 2.58, z, 0.48, 0.48, "Iron")
    lathe(g, x, 2.58, z, [(0, 0), (0.3, 0.0), (0.06, 0.32), (0, 0.4)], 4, "Iron", 45.0)

ASSETS = ROOT + r"\src\assets_cc0"
def asset(gname, key, pos, rot=0.0, scale=1.0, ratio=0.25):
    """Import a Poly Haven glTF prop, decimate it, and merge it into a bake group (its own UVs -> 'Tex', its
    own materials, base colour + normal map, baked with the rest)."""
    gg = grp(gname)
    before = set(bpy.data.objects)
    bpy.ops.import_scene.gltf(filepath=ASSETS + "\\" + key + "\\" + key + ".gltf")
    new = [o for o in bpy.data.objects if o not in before]
    T = Matrix.Translation(G(*pos)) @ Matrix.Rotation(math.radians(rot), 4, 'Z') @ Matrix.Scale(scale, 4)
    dg = bpy.context.evaluated_depsgraph_get()
    for o in new:
        if o.type != 'MESH':
            continue
        if ratio < 1.0:
            md = o.modifiers.new("dec", 'DECIMATE'); md.ratio = ratio
        dg.update()
        me = bpy.data.meshes.new_from_object(o.evaluated_get(dg))
        me.transform(T @ o.matrix_world)
        if me.uv_layers:
            me.uv_layers[0].name = "Tex"
            for extra in list(me.uv_layers)[1:]:
                me.uv_layers.remove(extra)
        else:
            me.uv_layers.new(name="Tex")
        at = me.attributes.get("custom_uv") or me.attributes.new("custom_uv", 'INT', 'FACE')
        for k in range(len(me.polygons)):
            at.data[k].value = 1
        remap = []
        for m in me.materials:
            nm = "A_" + (m.name if m else key)
            if m and nm not in MATS:
                # rebuild as a plain diffuse material from the prop's colour texture (the glTF metal/rough setup
                # bakes black): base colour on the 'Tex' UVs, a little roughness, no metal
                img = None
                for nd in m.node_tree.nodes:
                    if nd.type == 'BSDF_PRINCIPLED' and nd.inputs["Base Color"].links:
                        src = nd.inputs["Base Color"].links[0].from_node
                        while src.type != 'TEX_IMAGE' and src.inputs and src.inputs[0].links:
                            src = src.inputs[0].links[0].from_node
                        img = src.image if src.type == 'TEX_IMAGE' else None
                b = NB(nm)
                if img:
                    tn = b.n("ShaderNodeTexImage"); tn.image = img; b.link(b.uv, tn.inputs[0])
                    b.link(tn.outputs["Color"], b.bsdf.inputs["Base Color"])
                b.bsdf.inputs["Roughness"].default_value = 0.8; b.bsdf.inputs["Metallic"].default_value = 0.0
            remap.append(gg.mi(nm))
        idx = [remap[p.material_index] if remap else 0 for p in me.polygons]
        n0 = len(gg.bm.faces)
        gg.bm.from_mesh(me)                              # appends; then set the group's material slots
        gg.bm.faces.ensure_lookup_table()
        for k, mi in enumerate(idx):
            gg.bm.faces[n0 + k].material_index = mi
        bpy.data.meshes.remove(me)
    for o in new:
        bpy.data.objects.remove(o, do_unlink=True)

FLOWERS = ("FlowerRed", "FlowerYellow", "FlowerWhite", "FlowerViolet", "FlowerPink")
def bush(x, z, r, seed, g="CH_Village", flowers=10):
    """A leafy shrub (the ico() wrapper turns it into clumps) with a scatter of flowers round its foot."""
    rnd = random.Random(seed)
    ico(g, (x, r * 0.7, z), r, "Foliage", seed, 0.8)
    for k in range(flowers):
        a = rnd.uniform(0, 2 * math.pi); d = r * rnd.uniform(0.9, 1.35)
        fx, fz = x + d * math.cos(a), z + d * math.sin(a) * 0.7
        _orig_ico(g, (fx, 0.16, fz), rnd.uniform(0.14, 0.22), "Foliage", seed * 13 + k, 0.7)
        _orig_ico(g, (fx, 0.34, fz), rnd.uniform(0.07, 0.11), FLOWERS[(seed + k) % 5], seed * 17 + k, 0.8)

def build_trails_props():
    g = "CH_Village"
    # shrubs and flowers along the chapel front, by the tower, and along the churchyard wall
    for (x, z, r) in ((3.95, -27.25, 0.95), (-3.95, -27.25, 0.95), (-6.1, -27.0, 1.05), (9.7, -27.6, 1.0),
                      (19.0, -13.2, 0.85), (23.5, -13.3, 0.95), (28.0, -13.2, 0.85)):
        bush(x, z, r, int(abs(x) * 10 + abs(z)))
    # by the rectory's gable end: barrels and a crate stack
    asset(g, "wine_barrel_01", (-12.7, 0.0, -18.0), 20, 1.15, 0.2)
    asset(g, "wine_barrel_01", (-12.5, 0.0, -19.1), -35, 1.15, 0.2)
    asset(g, "wooden_crate_02", (-13.0, 0.0, -20.4), 82, 1.3, 0.35)
    asset(g, "wooden_crate_01", (-13.0, 0.62, -20.3), 70, 1.3, 0.35)
    # flower boxes under the rectory's front windows
    for x in (-20.6, -17.6):
        asset(g, "planter_box_02", (x, 0.0, -16.75), 0, 1.0, 0.25)
    # a picnic table on the meadow, front left (Trails farm)
    asset(g, "wooden_picnic_table", (-20.5, 0.0, -1.0), 72, 1.0, 0.25)
    # crates and a bucket by the hand cart
    asset(g, "wooden_crate_02", (12.9, 0.0, -10.0), -12, 1.3, 0.35)
    asset(g, "wooden_bucket_01", (9.3, 0.0, -10.5), 0, 1.2, 0.35)

_orig_build_props = build_props
def build_props():
    _orig_build_props()
    build_trails_props()
    for (x, z) in ((13.8, -7.9), (14.6, -4.6), (-13.8, -7.9), (-14.6, -4.6), (3.4, -21.8), (-3.4, -21.8), (8.6, -15.2), (-8.9, -14.6)):
        lamp_post(x, z)
