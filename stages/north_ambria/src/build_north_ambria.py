# North Ambria - 3D stage build script (Blender 5.x, runs in --background).
# A frozen snowfield in a blizzard: a raised rocky mound with two snow-capped gravestones at the back,
# ice crystal clusters and snowy boulders around the field, broken cliffs and jagged mountains in the mist.
#
#   blender --background --factory-startup --python run_na.py -- STEPS=build,bake,preview,export CAMS=CAM_mid
#
# Layout is written in GODOT coordinates (x right, y up, +z toward the camera) and converted
# to Blender (Z-up) by G():  Godot (x, y, z) -> Blender (x, -z, y).  1 unit = 1 m.
# Baked groups (atlases): NA_Ground, NA_Ice, NA_Far, NA_Floor (light map only)
# Card groups (Godot shaders): NA_Sky (emits in the bake), NA_Mist (not baked)
import bpy, bmesh, math, random
from mathutils import Vector, Matrix

ROOT = r"E:\Netsu Projects\Netsu Fighter\Godot\netsu-vs\stages\north_ambria"
TEXD = ROOT + r"\textures"

# ---------------- layout (Godot space, metres) ----------------
FLOOR_X = 40.0
FLOOR_BACK, FLOOR_FRONT = -58.0, 22.0
MOUND = (0.0, -34.0)               # the raised mound with the two gravestones
MOUND_H = 2.6
SKY_R = 300.0
LANE_X, LANE_Z = 12.5, -9.0
MIST = [  # (z, top, half-width): blowing snow / mist banks (Godot shader)
    (-14.0, 2.5, 34.0), (-27.0, 5.5, 40.0), (-46.0, 12.0, 60.0), (-60.0, 20.0, 90.0), (-90.0, 32.0, 140.0), (-135.0, 48.0, 220.0)]

V = dict(world=("#8496b8", 1.2), haze="#b8c6da",
         **{"break": (60000, "#e8f0ff"), "top": (9000, "#c4d2ec"), "fill": (5000, "#d0dcf0")},
         sky=[(0.0, "#c8d4e4"), (0.15, "#a8b6cc"), (0.4, "#6a7690"), (1.0, "#2c3448")], sky_strength=1.0)

def srgb(h):
    h = h.lstrip('#'); c = [int(h[i:i + 2], 16) / 255 for i in (0, 2, 4)]
    return tuple(((v + 0.055) / 1.055) ** 2.4 if v > 0.04045 else v / 12.92 for v in c)

def G(x, y, z):
    return Vector((x, -z, y))

def reset():
    for coll in (bpy.data.objects, bpy.data.meshes, bpy.data.materials, bpy.data.cameras,
                 bpy.data.lights, bpy.data.collections, bpy.data.node_groups, bpy.data.worlds):
        for d in list(coll):
            coll.remove(d)
    for im in list(bpy.data.images):
        if im.name not in ("Render Result", "Viewer Node"):
            bpy.data.images.remove(im)

COLS = {}
def col(name):
    if name not in COLS:
        c = bpy.data.collections.new(name)
        bpy.context.scene.collection.children.link(c)
        COLS[name] = c
    return COLS[name]

# ======================================================================
#  mesh builder: one bmesh per group
# ======================================================================
class Group:
    def __init__(self, name, coll="Stage"):
        self.name, self.coll = name, coll
        self.bm = bmesh.new()
        self.uv = self.bm.loops.layers.uv.new("Tex")
        self.custom = self.bm.faces.layers.int.new("custom_uv")
        self.mats = []

    def mi(self, m):
        if m not in self.mats:
            self.mats.append(m)
        return self.mats.index(m)

    def finish(self):
        bm = self.bm
        bm.normal_update()
        for f in bm.faces:
            if f[self.custom]:
                continue
            n = f.normal; ax = max(range(3), key=lambda i: abs(n[i]))
            for l in f.loops:
                p = l.vert.co
                if ax == 0:   l[self.uv].uv = (p.y * (1 if n.x > 0 else -1), p.z)
                elif ax == 1: l[self.uv].uv = (p.x * (-1 if n.y > 0 else 1), p.z)
                else:         l[self.uv].uv = (p.x, p.y)
        me = bpy.data.meshes.new(self.name)
        bm.to_mesh(me); bm.free()
        for m in self.mats:
            me.materials.append(MATS[m])
        o = bpy.data.objects.new(self.name, me)
        col(self.coll).objects.link(o)
        return o

GR = {}
def grp(name, coll="Stage"):
    if name not in GR:
        GR[name] = Group(name, coll)
    return GR[name]

def _tag(g, faces, m):
    idx = g.mi(m)
    for f in faces:
        f.material_index = idx
    return faces

def obox(g, center, size, rot_y=0.0, m="Stone", bevel=0.0):
    """Box at Godot `center` with Godot `size` (x, y, z), turned rot_y degrees about the vertical."""
    g = grp(g) if isinstance(g, str) else g
    M = Matrix.Translation(G(*center)) @ Matrix.Rotation(math.radians(rot_y), 4, 'Z') @ \
        Matrix.Diagonal((size[0], size[2], size[1], 1.0))
    r = bmesh.ops.create_cube(g.bm, size=1.0, matrix=M)
    verts = r["verts"]
    _tag(g, list({f for v in verts for f in v.link_faces}), m)
    if bevel > 0:
        edges = list({e for v in verts for e in v.link_edges})
        b = min(bevel, 0.45 * min(size))
        res = bmesh.ops.bevel(g.bm, geom=verts + edges, offset=b, segments=1, affect='EDGES',
                              profile=0.5, clamp_overlap=True)
        _tag(g, res["faces"], m)

def box(g, x, y0, y1, z, wx, wz, m="Stone", bevel=0.0, rot_y=0.0):
    """Box standing from y0 to y1, centred on (x, z), wx by wz wide."""
    obox(g, (x, (y0 + y1) / 2, z), (wx, y1 - y0, wz), rot_y, m, bevel)

def cyl(g, x, y0, z, r1, r2, h, m="Stone", seg=8, rot=0.0):
    """Vertical cone / cylinder from y0 up by h (seg = 4 -> pyramid)."""
    g = grp(g) if isinstance(g, str) else g
    M = Matrix.Translation(G(x, y0 + h / 2, z)) @ Matrix.Rotation(math.radians(rot), 4, 'Z')
    r = bmesh.ops.create_cone(g.bm, cap_ends=True, cap_tris=False, segments=seg,
                              radius1=r1, radius2=r2, depth=h, matrix=M)
    _tag(g, list({f for v in r["verts"] for f in v.link_faces}), m)

def cone_dir(g, base, d, r, L, m="Metal", seg=6):
    """Cone from Godot point `base` pointing along Godot direction d (spike)."""
    g = grp(g) if isinstance(g, str) else g
    dv = Vector((d[0], -d[2], d[1])).normalized()
    q = dv.to_track_quat('Z', 'Y')
    M = Matrix.Translation(G(*base) + dv * (L / 2)) @ q.to_matrix().to_4x4()
    r = bmesh.ops.create_cone(g.bm, cap_ends=True, cap_tris=False, segments=seg,
                              radius1=r, radius2=0.0, depth=L, matrix=M)
    _tag(g, list({f for v in r["verts"] for f in v.link_faces}), m)

def quad(g, pts, uvs, m):
    g = grp(g) if isinstance(g, str) else g
    vs = [g.bm.verts.new(G(*p)) for p in pts]
    f = g.bm.faces.new(vs)
    f.material_index = g.mi(m); f[g.custom] = 1
    for l, uv in zip(f.loops, uvs):
        l[g.uv].uv = uv
    return f

def octa_prism(g, cx, cz, r, y0, y1, m="Stone", seg=8, rot=22.5):
    cyl(g, cx, y0, cz, r / math.cos(math.pi / seg), r / math.cos(math.pi / seg), y1 - y0, m, seg, rot)

def polar(r, th, y=0.0):
    """Godot point at radius r / angle th (0 = straight ahead of the camera) around the platform centre."""
    return (r * math.sin(th), y, CENTER_Z - r * math.cos(th))

# ======================================================================
#  materials
# ======================================================================
MATS = {}

class NB:
    def __init__(self, name):
        self.m = bpy.data.materials.new(name); self.m.use_nodes = True
        self.nt = self.m.node_tree; self.nt.nodes.clear()
        self.out = self.n("ShaderNodeOutputMaterial", (1100, 0))
        self.bsdf = self.n("ShaderNodeBsdfPrincipled", (700, 0))
        self.nt.links.new(self.bsdf.outputs[0], self.out.inputs[0])
        uvn = self.n("ShaderNodeUVMap", (-1400, 0)); uvn.uv_map = "Tex"
        self.uv = uvn.outputs[0]
        geo = self.n("ShaderNodeNewGeometry", (-1400, -300))
        self.pos = geo.outputs["Position"]; self.normal = geo.outputs["Normal"]
        MATS[name] = self.m

    def n(self, t, loc=(0, 0), **kw):
        nd = self.nt.nodes.new(t); nd.location = loc
        for k, v in kw.items():
            setattr(nd, k, v)
        return nd

    def link(self, a, b):
        self.nt.links.new(a, b)

    def math(self, op, a, b=None):
        nd = self.n("ShaderNodeMath", operation=op)
        for i, v in enumerate((a, b)):
            if v is None:
                continue
            if isinstance(v, (int, float)):
                nd.inputs[i].default_value = v
            else:
                self.link(v, nd.inputs[i])
        return nd.outputs[0]

    def noise(self, vec, scale, detail=4, rough=0.55):
        nd = self.n("ShaderNodeTexNoise"); nd.inputs["Scale"].default_value = scale
        nd.inputs["Detail"].default_value = detail; nd.inputs["Roughness"].default_value = rough
        self.link(vec, nd.inputs["Vector"])
        return nd

    def ramp(self, fac, stops):
        nd = self.n("ShaderNodeValToRGB"); cr = nd.color_ramp
        while len(cr.elements) < len(stops):
            cr.elements.new(0.5)
        for e, (p, c) in zip(cr.elements, stops):
            e.position = p; e.color = (*srgb(c), 1)
        self.link(fac, nd.inputs[0])
        return nd.outputs[0]

    def mixc(self, a, b, fac, blend='MIX'):
        nd = self.n("ShaderNodeMix"); nd.data_type = 'RGBA'; nd.blend_type = blend
        for sock, v in ((0, fac), (6, a), (7, b)):
            if isinstance(v, (int, float)):
                nd.inputs[sock].default_value = v
            elif isinstance(v, str):
                nd.inputs[sock].default_value = (*srgb(v), 1)
            else:
                self.link(v, nd.inputs[sock])
        return nd.outputs[2]

    def image(self, fn, vec, extension='REPEAT', non_color=False):
        im = self.n("ShaderNodeTexImage"); im.image = bpy.data.images.load(TEXD + "\\" + fn, check_existing=True)
        im.extension = extension
        if non_color:
            im.image.colorspace_settings.name = 'Non-Color'
        self.link(vec, im.inputs[0])
        return im


# ======================================================================
#  North Ambria: shapes
# ======================================================================
def spire(g, x, z, h, r, seed, m="Rock", lean=(0.0, 0.0), sink=1.0, segs=None, rings=5, base_y=0.0):
    """Jagged faceted spike (ice crystal / rock spire). Base sunk below base_y by `sink`."""
    g = grp(g) if isinstance(g, str) else g
    rnd = random.Random(seed)
    segs = segs or rnd.choice([5, 6, 7])
    bm = g.bm; ring_v = []
    y0 = base_y - sink
    for k in range(rings):
        t = k / rings
        y = y0 + (h + sink) * t
        rad = r * (1 - t) ** 0.75 * rnd.uniform(0.85, 1.12)
        ox, oz = lean[0] * t * t * h, lean[1] * t * t * h
        a0 = rnd.random() * 6.283; ring = []
        for i in range(segs):
            a = a0 + 6.283 * i / segs + rnd.uniform(-0.2, 0.2)
            rr = rad * rnd.uniform(0.75, 1.12)
            ring.append(bm.verts.new(G(x + ox + rr * math.cos(a), y, z + oz + rr * math.sin(a))))
        ring_v.append(ring)
    tip = bm.verts.new(G(x + lean[0] * h, base_y + h, z + lean[1] * h))
    new = []
    for k in range(rings - 1):
        A, B = ring_v[k], ring_v[k + 1]
        for i in range(segs):
            j = (i + 1) % segs
            new.append(bm.faces.new((A[i], A[j], B[j]))); new.append(bm.faces.new((A[i], B[j], B[i])))
    T = ring_v[-1]
    for i in range(segs):
        new.append(bm.faces.new((T[i], T[(i + 1) % segs], tip)))
    bmesh.ops.recalc_face_normals(bm, faces=new)
    _tag(g, new, m)

def crystal_cluster(x, z, s, seed, base_y=0.0):
    """A cluster of leaning ice crystals (big one in the middle) with snowy rocks at its foot."""
    rnd = random.Random(seed)
    spire("NA_Ice", x, z, 3.2 * s, 1.1 * s, seed, "Ice", (rnd.uniform(-0.08, 0.08), rnd.uniform(-0.05, 0.05)), 0.5, rnd.choice([4, 5]), 3, base_y)
    for k in range(rnd.randint(2, 4)):
        a = rnd.uniform(0, 6.28); d = s * rnd.uniform(0.9, 1.6)
        spire("NA_Ice", x + d * math.cos(a), z + d * math.sin(a), rnd.uniform(1.0, 2.0) * s, rnd.uniform(0.4, 0.7) * s, seed + k + 1,
              "Ice", (math.cos(a) * 0.25, math.sin(a) * 0.25), 0.4, rnd.choice([4, 5]), 3, base_y)
    for k in range(rnd.randint(2, 4)):
        a = rnd.uniform(0, 6.28); d = s * rnd.uniform(1.2, 2.2)
        rock("NA_Ground", x + d * math.cos(a), base_y, z + d * math.sin(a), s * rnd.uniform(0.5, 1.0), s * rnd.uniform(0.35, 0.7),
             s * rnd.uniform(0.5, 0.9), seed * 7 + k, "SnowRock")

def rock(g, x, y, z, sx, sy, sz, seed, m="SnowRock", sub=1, jag=0.28):
    gg = grp(g) if isinstance(g, str) else g
    rnd = random.Random(seed)
    M = Matrix.Translation(G(x, y, z)) @ Matrix.Rotation(rnd.uniform(0, 6.28), 4, 'Z') @ Matrix.Diagonal((sx, sz, sy, 1.0))
    r = bmesh.ops.create_icosphere(gg.bm, subdivisions=sub, radius=1.0, matrix=M)
    c = G(x, y, z)
    for v in r["verts"]:
        v.co = c + (v.co - c) * rnd.uniform(1 - jag, 1 + jag * 0.5)
        if v.co.z < y - 0.25 * sy:
            v.co.z = y - 0.25 * sy
    _tag(gg, list({f for v in r["verts"] for f in v.link_faces}), m)

def drift(g, x, z, rx, rz, h, seed, m="Snow", n=14, y0=0.0):
    """A smooth snow drift / mound: a squashed dome with a noisy ring."""
    gg = grp(g) if isinstance(g, str) else g
    rnd = random.Random(seed); bm = gg.bm
    rings = 5; ring_v = []
    for k in range(rings):
        t = k / rings
        ring = []
        for i in range(n):
            a = 2 * math.pi * i / n
            rr = (1 - t ** 2) ** 0.5 * rnd.uniform(0.92, 1.08) if k else rnd.uniform(0.95, 1.1)
            y = y0 + h * math.sin(t * math.pi / 2) - (0.2 if k == 0 else 0)
            ring.append(bm.verts.new(G(x + rx * rr * math.cos(a), y, z + rz * rr * math.sin(a))))
        ring_v.append(ring)
    top = bm.verts.new(G(x, y0 + h, z))
    new = []
    for k in range(rings - 1):
        A, B = ring_v[k], ring_v[k + 1]
        for i in range(n):
            j = (i + 1) % n
            new.append(bm.faces.new((A[i], A[j], B[j], B[i])))
    for i in range(n):
        new.append(bm.faces.new((ring_v[-1][i], ring_v[-1][(i + 1) % n], top)))
    bmesh.ops.recalc_face_normals(bm, faces=new)
    _tag(gg, new, m)

def ridge(g, z, x0, x1, base, peaks, seed, m="Mountain", n=90, jag=4.0):
    """A jagged mountain range sheet facing the camera. peaks = [(x, height, half_width), ...]."""
    g = grp(g) if isinstance(g, str) else g
    rnd = random.Random(seed); bm = g.bm
    def prof(x):
        h = 4.0
        for (px, ph, pw) in peaks:
            d = abs(x - px) / pw
            if d < 1:
                h = max(h, ph * (1 - d) ** 1.1)
        return h
    cols = []
    for i in range(n + 1):
        x = x0 + (x1 - x0) * i / n + rnd.uniform(-0.3, 0.3) * (x1 - x0) / n
        top = base + prof(x) + rnd.uniform(-1, 1) * jag * (1.0 if i % 2 else 0.4)
        mid = base + (top - base) * rnd.uniform(0.45, 0.65)
        cols.append((bm.verts.new(G(x, base - 4, z + 4)), bm.verts.new(G(x + rnd.uniform(-1, 1), mid, z + rnd.uniform(-2, 2))),
                     bm.verts.new(G(x, top, z - rnd.uniform(0, 3)))))
    new = []
    for i in range(n):
        a, b = cols[i], cols[i + 1]
        for r in range(2):
            new.append(bm.faces.new((a[r], b[r], b[r + 1]))); new.append(bm.faces.new((a[r], b[r + 1], a[r + 1])))
    for f in new:
        f.normal_update()
        if f.normal.y > 0:
            f.normal_flip()
    _tag(g, new, m)

# ======================================================================
#  materials
# ======================================================================
def snow_rock_material(name, dark, light, snow_amount=0.55, haze=None, near=40.0, far=160.0, hmin=0.0, hmax=0.6):
    """Dark granite with snow piled on every upward-facing surface (+ haze into the distance)."""
    b = NB(name)
    n = b.noise(b.pos, 0.9, 5, 0.6)
    c = b.ramp(n.outputs["Fac"], [(0.3, dark), (0.7, light)])
    sep = b.n("ShaderNodeSeparateXYZ"); b.link(b.normal, sep.inputs[0])
    sn = b.noise(b.pos, 2.5, 3, 0.5)
    up = b.math('ADD', sep.outputs[2], b.math('MULTIPLY', b.math('SUBTRACT', sn.outputs["Fac"], 0.5), 0.6))
    snow = b.n("ShaderNodeMapRange"); snow.inputs["From Min"].default_value = 1.0 - snow_amount - 0.05
    snow.inputs["From Max"].default_value = 1.0 - snow_amount + 0.08
    b.link(up, snow.inputs[0])
    c = b.mixc(c, "#e8eef8", snow.outputs[0])
    b.link(c, b.bsdf.inputs["Base Color"]); b.bsdf.inputs["Roughness"].default_value = 0.75
    if haze:
        sp = b.n("ShaderNodeSeparateXYZ"); b.link(b.pos, sp.inputs[0])
        dist = b.math('ABSOLUTE', sp.outputs[1])
        mr = b.n("ShaderNodeMapRange"); mr.inputs["From Min"].default_value = near; mr.inputs["From Max"].default_value = far
        mr.inputs["To Min"].default_value = hmin; mr.inputs["To Max"].default_value = hmax
        b.link(dist, mr.inputs[0])
        em = b.n("ShaderNodeEmission"); em.inputs["Color"].default_value = (*srgb(haze), 1); em.inputs["Strength"].default_value = 1.0
        mix = b.n("ShaderNodeMixShader"); b.link(mr.outputs[0], mix.inputs[0])
        b.link(b.bsdf.outputs[0], mix.inputs[1]); b.link(em.outputs[0], mix.inputs[2]); b.link(mix.outputs[0], b.out.inputs[0])
    return b

def ice_material(name):
    """Pale blue ice: bright faceted surfaces, deep blue inside the cracks, a faint glow (baked as emission)."""
    b = NB(name)
    n = b.noise(b.pos, 1.8, 4, 0.5)
    c = b.ramp(n.outputs["Fac"], [(0.25, "#4a86c0"), (0.6, "#a8d4f4"), (0.85, "#e4f4ff")])
    v = b.n("ShaderNodeTexVoronoi"); v.feature = 'DISTANCE_TO_EDGE'; v.inputs["Scale"].default_value = 1.4
    b.link(b.pos, v.inputs["Vector"])
    crack = b.math('LESS_THAN', v.outputs["Distance"], 0.03)
    c = b.mixc(c, "#2a5a96", b.math('MULTIPLY', crack, 0.8))
    b.link(c, b.bsdf.inputs["Base Color"]); b.bsdf.inputs["Roughness"].default_value = 0.15
    b.bsdf.inputs["Emission Color"].default_value = (*srgb("#7ab8f0"), 1)
    b.bsdf.inputs["Emission Strength"].default_value = 0.25
    return b

def stone_material(name, dark, light):
    """Weathered gravestone: grey stone, carved border, lichen, snow on the top."""
    b = NB(name)
    n = b.noise(b.pos, 3.0, 5, 0.6)
    c = b.ramp(n.outputs["Fac"], [(0.3, dark), (0.7, light)])
    l = b.noise(b.pos, 1.2, 3, 0.5)
    c = b.mixc(c, "#5a6450", b.math('MULTIPLY', b.math('GREATER_THAN', l.outputs["Fac"], 0.62), 0.4))
    sep = b.n("ShaderNodeSeparateXYZ"); b.link(b.normal, sep.inputs[0])
    c = b.mixc(c, "#eef2f8", b.math('GREATER_THAN', sep.outputs[2], 0.55))
    b.link(c, b.bsdf.inputs["Base Color"]); b.bsdf.inputs["Roughness"].default_value = 0.8
    bump = b.n("ShaderNodeBump"); bump.inputs["Strength"].default_value = 0.35
    b.link(n.outputs["Fac"], bump.inputs["Height"]); b.link(bump.outputs[0], b.bsdf.inputs["Normal"])
    return b

def build_materials():
    snow_rock_material("SnowRock", "#2e323a", "#4e5460", 0.62)
    snow_rock_material("Cliff", "#2e323a", "#4e5460", 0.55)
    snow_rock_material("Mountain", "#30343e", "#545a68", 0.45, haze=V["haze"], near=60, far=200, hmin=0.25, hmax=0.75)
    snow_rock_material("MountainFar", "#383c48", "#5a6070", 0.5, haze=V["haze"], near=100, far=260, hmin=0.5, hmax=0.88)
    ice_material("Ice")
    stone_material("Grave", "#7a7f86", "#a4a9b0")
    stone_material("GraveDark", "#3c4048", "#50555e")
    stone_material("Ruin", "#5c6068", "#80858e")
    snow_rock_material("Pine", "#16221f", "#2c3c36", 0.5)
    snow_rock_material("Bark", "#2a2622", "#48423a", 0.35)
    snow_rock_material("Wood", "#3a3028", "#5a4c3e", 0.5)
    b = NB("Metal"); b.bsdf.inputs["Base Color"].default_value = (*srgb("#8a9098"), 1)
    b.bsdf.inputs["Metallic"].default_value = 0.8; b.bsdf.inputs["Roughness"].default_value = 0.35
    b = NB("Cloth"); n = b.noise(b.pos, 6.0, 3, 0.5)
    b.link(b.ramp(n.outputs["Fac"], [(0.3, "#4a1214"), (0.7, "#7a2024")]), b.bsdf.inputs["Base Color"])
    b.bsdf.inputs["Roughness"].default_value = 0.9
    b = NB("Snow")
    n = b.noise(b.pos, 4.0, 3, 0.5)
    b.link(b.ramp(n.outputs["Fac"], [(0.3, "#dfe6f2"), (0.7, "#f4f7fc")]), b.bsdf.inputs["Base Color"])
    b.bsdf.inputs["Roughness"].default_value = 0.85
    b = NB("FloorSnow"); b.bsdf.inputs["Base Color"].default_value = (*srgb("#eaf0f8"), 1); b.bsdf.inputs["Roughness"].default_value = 0.9
    b = NB("SkyCard")
    sep = b.n("ShaderNodeSeparateXYZ"); b.link(b.uv, sep.inputs[0])
    r = b.ramp(sep.outputs[1], V["sky"])
    em = b.n("ShaderNodeEmission"); em.inputs["Strength"].default_value = V["sky_strength"]
    b.link(r, em.inputs["Color"]); b.link(em.outputs[0], b.out.inputs[0])
    b = NB("MistCard")
    em = b.n("ShaderNodeEmission"); em.inputs["Color"].default_value = (*srgb("#c8d4e4"), 1); em.inputs["Strength"].default_value = 0.0
    b.link(em.outputs[0], b.out.inputs[0])
    b = NB("Stand_P1"); b.bsdf.inputs["Base Color"].default_value = (*srgb("#2d6cdf"), 1)
    b = NB("Stand_P2"); b.bsdf.inputs["Base Color"].default_value = (*srgb("#e0463a"), 1)

# ======================================================================
#  the snowfield
# ======================================================================
def in_lane(x, z, pad=0.0):
    return abs(x) < LANE_X + pad and z > LANE_Z - pad

def build_floor():
    g = grp("NA_Floor")
    quad(g, [(-FLOOR_X, 0, FLOOR_FRONT), (FLOOR_X, 0, FLOOR_FRONT), (FLOOR_X, 0, FLOOR_BACK), (-FLOOR_X, 0, FLOOR_BACK)],
         [(-FLOOR_X, -FLOOR_FRONT), (FLOOR_X, -FLOOR_FRONT), (FLOOR_X, -FLOOR_BACK), (-FLOOR_X, -FLOOR_BACK)], "FloorSnow")

def _xf(x, y0, z, yaw=0.0, tilt=0.0):
    return Matrix.Translation(G(x, y0, z)) @ Matrix.Rotation(math.radians(yaw), 4, 'Z') @ Matrix.Rotation(math.radians(tilt), 4, 'X')

def _L(M, px, py, pz):
    """Local Godot point -> world Blender point through matrix M."""
    return M @ Vector((px, -pz, py))

def arch_pts(w, h, n=16, y0=0.0):
    """Round-topped slab outline in the x-y plane: up the left side, over the arch, down the right."""
    r = w / 2; pts = [(-r, y0)]
    for i in range(n + 1):
        a = math.pi - math.pi * i / n
        pts.append((r * math.cos(a), y0 + h - r + r * math.sin(a)))
    pts.append((r, y0))
    return pts

def extrude(g, M, pts, z0, z1, m):
    """Convex outline extruded from z0 (back) to z1 (front), in the local frame M."""
    gg = grp(g) if isinstance(g, str) else g; bm = gg.bm
    F = [bm.verts.new(_L(M, px, py, z1)) for px, py in pts]
    B = [bm.verts.new(_L(M, px, py, z0)) for px, py in pts]
    new = [bm.faces.new(F), bm.faces.new(B[::-1])]
    n = len(pts)
    for i in range(n):
        j = (i + 1) % n
        new.append(bm.faces.new((F[i], B[i], B[j], F[j])))
    bmesh.ops.recalc_face_normals(bm, faces=new)
    _tag(gg, new, m); return new

def band(g, M, inner, outer, z0, z1, m, closed=False):
    """A strip between two matching polylines (frame / snow cap), extruded from z0 to z1."""
    gg = grp(g) if isinstance(g, str) else g; bm = gg.bm
    IF = [bm.verts.new(_L(M, px, py, z1)) for px, py in inner]; OF = [bm.verts.new(_L(M, px, py, z1)) for px, py in outer]
    IB = [bm.verts.new(_L(M, px, py, z0)) for px, py in inner]; OB = [bm.verts.new(_L(M, px, py, z0)) for px, py in outer]
    n = len(inner); new = []
    for i in range(n if closed else n - 1):
        j = (i + 1) % n
        new += [bm.faces.new((IF[i], OF[i], OF[j], IF[j])), bm.faces.new((IB[j], OB[j], OB[i], IB[i])),
                bm.faces.new((OF[i], OB[i], OB[j], OF[j])), bm.faces.new((IF[j], IB[j], IB[i], IF[i]))]
    if not closed:
        for k in (0, n - 1):
            new.append(bm.faces.new((IF[k], IB[k], OB[k], OF[k])))
    bmesh.ops.recalc_face_normals(bm, faces=new)
    _tag(gg, new, m); return new

def gravestone(x, z, w, h, d, base_y, seed, yaw=0.0, tilt=0.0, emblem="cross"):
    """A clean round-topped headstone: two-step plinth, slab with a raised carved border, an emblem and
    inscription lines, and a thick snow cap that follows the arch (heaviest on top)."""
    g = "NA_Ground"; rnd = random.Random(seed)
    obox(g, (x, base_y + 0.18, z), (w + 1.0, 0.42, d + 0.9), yaw * 0.4, "Grave", 0.06)        # plinth
    obox(g, (x, base_y + 0.48, z), (w + 0.5, 0.2, d + 0.45), yaw * 0.4, "Grave", 0.04)
    obox(g, (x, base_y + 0.4, z + 0.05), (w + 0.85, 0.05, d + 0.6), yaw * 0.4, "Snow", 0.02)  # snow on the lower step
    obox(g, (x, base_y + 0.6, z), (w + 0.38, 0.05, d + 0.3), yaw * 0.4, "Snow", 0.02)         # snow on the upper step
    y0 = base_y + 0.56
    M = _xf(x, y0, z, yaw, tilt)
    extrude(g, M, arch_pts(w, h), -d / 2, d / 2, "Grave")                                     # slab
    o = arch_pts(w - 0.16, h - 0.16, 16, 0.12); i = arch_pts(w - 0.34, h - 0.34, 16, 0.24)     # raised border
    band(g, M, i, o, d / 2 - 0.01, d / 2 + 0.035, "Grave")                                  # front frame
    band(g, M, i, o, -d / 2 - 0.035, -d / 2 + 0.01, "Grave")                                # back frame
    extrude(g, M, [(-w / 2 + 0.08, 0.12), (w / 2 - 0.08, 0.12), (w / 2 - 0.08, 0.24), (-w / 2 + 0.08, 0.24)], d / 2 - 0.01, d / 2 + 0.035, "Grave")
    zf = d / 2 + 0.02
    if emblem == "cross":                                                                      # emblem high in the arch
        for (ex, ey, ew, eh) in ((0, h - w / 2 - 0.05, 0.1, 0.62), (0, h - w / 2 + 0.08, 0.4, 0.1)):
            extrude(g, M, [(ex - ew / 2, ey - eh / 2), (ex + ew / 2, ey - eh / 2), (ex + ew / 2, ey + eh / 2), (ex - ew / 2, ey + eh / 2)],
                    zf - 0.02, zf + 0.03, "GraveDark")
    else:                                                                                      # crossed swords (a jaeger's grave)
        for sgn in (-1, 1):
            a = math.radians(35 * sgn); L = 0.72; cx, cy = 0, h - w / 2 - 0.02
            dx, dy = math.sin(a) * L / 2, math.cos(a) * L / 2; nx, ny = math.cos(a) * 0.035, -math.sin(a) * 0.035
            extrude(g, M, [(cx - dx - nx, cy - dy - ny), (cx - dx + nx, cy - dy + ny), (cx + dx + nx, cy + dy + ny), (cx + dx - nx, cy + dy - ny)],
                    zf - 0.02, zf + 0.03, "GraveDark")
    for k, (ly, lw) in enumerate(((h - w / 2 - 0.62, 0.62), (h - w / 2 - 0.86, 0.7), (h - w / 2 - 1.06, 0.5), (h - w / 2 - 1.26, 0.58))):
        if ly < 0.45:
            break
        extrude(g, M, [(-lw / 2, ly - 0.025), (lw / 2, ly - 0.025), (lw / 2, ly + 0.025), (-lw / 2, ly + 0.025)], zf - 0.02, zf + 0.012, "GraveDark")
    # snow cap following the arch, thicker on top, lumpy, overhanging front and back
    r = w / 2; n = 18; inner, outer = [], []
    for k in range(n + 1):
        a = math.radians(170 - 160 * k / n)
        t = 0.03 + 0.2 * math.sin(a) ** 2 + rnd.uniform(-0.02, 0.025) * math.sin(a)
        inner.append(((r - 0.02) * math.cos(a), h - r + (r - 0.02) * math.sin(a)))
        outer.append(((r + t) * math.cos(a), h - r + (r + t) * math.sin(a)))
    band(g, M, inner, outer, -d / 2 - 0.07, d / 2 + 0.08, "Snow")
    # drift banked against the front of the plinth + a little at the back
    drift("NA_Ground", x + rnd.uniform(-0.2, 0.2), z + d / 2 + 0.55, w * 0.75, 0.5, 0.42, seed + 40, "Snow", 12, y0=base_y - 0.05)
    drift("NA_Ground", x, z - d / 2 - 0.5, w * 0.6, 0.4, 0.3, seed + 41, "Snow", 10, y0=base_y - 0.05)

def mound_y(dx, dz):
    """Height of the mound's snow dome at (dx, dz) from its centre (0 outside)."""
    rr = math.sqrt((dx / 12.0) ** 2 + (dz / 6.5) ** 2)
    if rr >= 1.0:
        return 0.0
    return max(0.0, MOUND_H * math.sin(math.pi / 2 * math.sqrt(1 - rr * rr)) - 0.15)

def build_mound():
    """The raised rocky mound with the two gravestones (back centre)."""
    mx, mz = MOUND
    # rocky sides: a ring of big snowy boulders + cliff faces
    rnd = random.Random(21)
    drift("NA_Ground", mx, mz, 12.0, 6.5, MOUND_H, 5, "Snow", 20)
    for k in range(22):
        a = rnd.uniform(-math.pi, math.pi)
        rx, rz = 11.5 * math.cos(a), 6.0 * math.sin(a)
        if rz > 3.0 and abs(rx) < 5.0 and rnd.random() < 0.5:
            continue
        s = rnd.uniform(0.9, 2.2)
        rock("NA_Ground", mx + rx, MOUND_H * 0.1, mz + rz, s * 1.3, s * 1.5, s, 300 + k, "Cliff", 2, 0.3)
    for k in range(10):                                                   # rocks poking through the top
        rock("NA_Ground", mx + rnd.uniform(-8, 8), MOUND_H - 0.2, mz + rnd.uniform(-3.5, 3.0), rnd.uniform(0.4, 1.0),
             rnd.uniform(0.3, 0.6), rnd.uniform(0.4, 0.9), 400 + k, "SnowRock")
    gravestone(mx - 2.6, mz - 0.5, 1.6, 3.1, 0.5, MOUND_H - 0.25, 7, yaw=4.0, tilt=-1.5, emblem="cross")
    gravestone(mx + 2.6, mz - 0.5, 1.5, 2.85, 0.5, MOUND_H - 0.25, 9, yaw=-5.0, tilt=2.0, emblem="swords")
    build_grave_props(mx, mz, MOUND_H - 0.25)

def build_field():
    """Snowy rocks, drifts and ice crystals around the field (outside the fight lane)."""
    rnd = random.Random(5)
    for k, (x, z, s) in enumerate(((-21.0, -18.0, 1.6), (-16.5, -26.0, 1.2), (-26.0, -30.0, 2.0), (22.0, -19.5, 1.7),
                                   (17.0, -28.0, 1.1), (27.0, -33.0, 2.1), (-15.2, 3.5, 1.1), (15.5, 2.5, 1.2),
                                   (-19.5, -8.0, 1.0), (20.0, -9.0, 0.9), (-9.0, -40.0, 1.3), (11.0, -42.0, 1.4))):
        crystal_cluster(x, z, s * 1.5, 50 + k * 3)
    for k in range(60):                                                   # scattered snowy rocks
        x = rnd.uniform(-34, 34); z = rnd.uniform(-48, 10)
        if in_lane(x, z, 1.5) or (abs(x - MOUND[0]) < 13 and abs(z - MOUND[1]) < 7.5):
            continue
        s = rnd.uniform(0.4, 1.4) * (1.0 + max(0, -z - 20) / 30)
        rock("NA_Ground", x, 0, z, s * rnd.uniform(1.0, 1.5), s * rnd.uniform(0.8, 1.2), s, 600 + k, "SnowRock", 2)
        if rnd.random() < 0.6:
            drift("NA_Ground", x + rnd.uniform(-0.5, 0.5), z + s * 0.6, s * 1.5, s * 0.9, s * 0.35, 700 + k, "Snow", 10)
    for k in range(40):                                                   # low snow drifts across the field (never in the lane)
        x = rnd.uniform(-36, 36); z = rnd.uniform(-50, 14)
        if in_lane(x, z, 2.0):
            continue
        drift("NA_Ground", x, z, rnd.uniform(1.5, 4.5), rnd.uniform(0.8, 2.0), rnd.uniform(0.2, 0.7), 800 + k, "Snow", 12)
    # foreground framing: big snowy boulders + crystals at the screen-edge corners
    for sx in (-1, 1):
        for k, (x, z, s) in enumerate(((14.5, 6.5, 1.8), (17.5, 4.0, 2.4), (13.0, 9.5, 1.3))):
            rock("NA_Ground", sx * x, 0, z, s * 1.4, s * 0.85, s, 900 + k + (sx > 0) * 10, "SnowRock", 2)
            drift("NA_Ground", sx * x, z + 0.4, s * 1.6, s * 1.1, s * 0.55, 950 + k + (sx > 0) * 10, "Snow", 12)

def build_grave_props(mx, mz, top):
    """A jaeger's sword planted in the snow between the graves, a tattered banner on a pole behind them,
    and a few small stone markers and cairns."""
    g = "NA_Props"
    # sword: blade, guard, grip, pommel, leaning a little in the wind
    sx, sz, lean = mx + 0.1, mz + 0.9, (0.08, 0.0, 0.03)
    top = mound_y(sx - mx, sz - mz)
    L = 1.5; hy = top + 1.05
    cone_dir(g, (sx + lean[0] * 1.6, hy, sz), (-lean[0], -1.0, -lean[2]), 0.07, L, "Metal", 4)   # blade, point buried
    obox(g, (sx + lean[0] * 1.6, hy, sz), (0.5, 0.07, 0.08), 0, "Metal")                     # guard
    cyl(g, sx + lean[0] * 1.7, hy + 0.03, sz, 0.035, 0.035, 0.32, "Wood", 6)                  # grip
    cyl(g, sx + lean[0] * 1.9, hy + 0.35, sz, 0.06, 0.05, 0.08, "Metal", 6)                   # pommel
    # banner pole + tattered cloth streaming with the wind (+x)
    px, pz = mx + 5.6, mz - 1.6
    top = mound_y(5.6, -1.6)
    cyl(g, px, top - 0.6, pz, 0.07, 0.05, 5.4, "Wood", 6)
    obox(g, (px + 0.55, top + 4.55, pz), (1.2, 0.06, 0.06), 0, "Wood")
    gg = grp(g); bm = gg.bm; rnd = random.Random(77)
    cols, rows, W, H = 9, 6, 1.5, 1.7
    def cp(i, j, off):
        u, v = i / cols, j / rows
        bx = px + 0.1 + u * W; by = top + 4.5 - v * H * (1 - 0.25 * u)
        bz = pz + 0.18 * math.sin(u * 5.0 + v * 1.3) * u + off
        return G(bx, by - 0.25 * u * u, bz)
    for off, flip in ((0.012, False), (-0.012, True)):
        V2 = [[bm.verts.new(cp(i, j, off)) for i in range(cols + 1)] for j in range(rows + 1)]
        fs = []
        for j in range(rows):
            for i in range(cols):
                if j >= rows - 2 and (i * 7 + j * 3) % 5 < 2 and i > 1:
                    continue                                        # tattered holes along the bottom and the fly
                q = (V2[j][i], V2[j][i + 1], V2[j + 1][i + 1], V2[j + 1][i])
                fs.append(bm.faces.new(q[::-1] if flip else q))
        for f in fs:
            f.normal_update()
        if not flip:
            if sum(f.normal.y for f in fs) > 0:
                for f in fs: f.normal_flip()
        else:
            if sum(f.normal.y for f in fs) < 0:
                for f in fs: f.normal_flip()
        _tag(gg, fs, "Cloth")
    # small stone markers + cairns on the mound
    for k, (dx, dz, s) in enumerate(((-6.2, 1.2, 0.8), (6.8, 0.6, 0.7), (-4.4, 2.6, 0.55), (4.6, 2.8, 0.6))):
        if k < 2:
            ty = mound_y(dx, dz)
            obox(g, (mx + dx, ty + 0.35 * s, mz + dz), (0.5 * s, 0.9 * s, 0.22 * s), rnd.uniform(-12, 12), "Ruin", 0.04)
            obox(g, (mx + dx, ty + 0.8 * s + 0.03, mz + dz), (0.5 * s + 0.06, 0.07, 0.3 * s), 0, "Snow", 0.02)
        else:
            for j in range(3):
                rock(g, mx + dx + rnd.uniform(-0.1, 0.1), mound_y(dx, dz) - 0.1 + j * 0.28 * s, mz + dz, 0.4 * s * (1 - j * 0.25),
                     0.22 * s, 0.35 * s * (1 - j * 0.25), 1500 + k * 5 + j, "SnowRock", 1, 0.2)

def broken_pillar(x, z, r, h, seed, base_y=0.0, fallen=False):
    g = "NA_Props"; rnd = random.Random(seed)
    if fallen:
        a = rnd.uniform(0, 360)
        for j in range(3):                                          # three drum sections lying in the snow
            dx, dz = math.cos(math.radians(a)) * j * r * 2.3, math.sin(math.radians(a)) * j * r * 2.3
            gg = grp(g)
            M = Matrix.Translation(G(x + dx, base_y + r * 0.8, z + dz)) @ Matrix.Rotation(math.radians(-a), 4, 'Z') @ \
                Matrix.Rotation(math.radians(90 + rnd.uniform(-8, 8)), 4, 'Y')
            rr = bmesh.ops.create_cone(gg.bm, cap_ends=True, cap_tris=False, segments=10, radius1=r, radius2=r * 0.95, depth=r * 2.0, matrix=M)
            _tag(gg, list({f for v in rr["verts"] for f in v.link_faces}), "Ruin")
        drift("NA_Ground", x, z, r * 4, r * 2.5, r * 0.7, seed + 3, "Snow", 12, y0=base_y - 0.05)
        return
    cyl(g, x, base_y - 0.3, z, r * 1.35, r * 1.35, 0.6, "Ruin", 8)                            # base
    cyl(g, x, base_y + 0.3, z, r, r * 0.95, h, "Ruin", 10, rnd.uniform(0, 30))               # shaft
    # broken top: a jagged cap, snow on it
    spire(g, x, z, rnd.uniform(0.3, 0.7), r * 0.95, seed + 1, "Ruin", (rnd.uniform(-0.3, 0.3), 0), 0.05, 10, 2, base_y + 0.3 + h)
    drift("NA_Ground", x, z, r * 0.9, r * 0.9, 0.18, seed + 2, "Snow", 10, y0=base_y + 0.3 + h + 0.15)
    drift("NA_Ground", x, z, r * 2.4, r * 2.0, 0.45, seed + 4, "Snow", 12, y0=base_y - 0.05)

def ruins():
    """What is left of an old stone ring around the mound and a broken wall to the left."""
    mx, mz = MOUND
    for k, (dx, dz, r, h, fallen) in enumerate(((-10.5, 2.0, 0.55, 3.6, False), (10.8, 1.5, 0.55, 2.2, False),
                                                (-12.8, -2.5, 0.5, 1.4, False), (13.2, -3.0, 0.5, 4.4, False),
                                                (-7.5, -5.0, 0.5, 5.2, False), (7.8, -5.2, 0.5, 1.0, False),
                                                (15.5, 3.5, 0.42, 0, True))):
        broken_pillar(mx + dx, mz + dz, r, h, 2000 + k * 11, mound_y(dx, dz), fallen)
    # a broken wall on the left, mid-field
    rnd = random.Random(31)
    x0, z0 = -33.0, -22.5
    for k in range(9):
        hh = 2.4 - abs(k - 2.5) * 0.45 + rnd.uniform(-0.3, 0.3)
        if hh < 0.4:
            continue
        for j in range(int(hh / 0.45) + 1):
            obox("NA_Props", (x0 + k * 1.05 + rnd.uniform(-0.05, 0.05), 0.22 + j * 0.45, z0 + k * 0.35 + rnd.uniform(-0.05, 0.05)),
                 (1.0, 0.43, 0.7), -18 + rnd.uniform(-3, 3), "Ruin", 0.04)
        obox("NA_Props", (x0 + k * 1.05, 0.22 + (int(hh / 0.45) + 1) * 0.45 - 0.18, z0 + k * 0.35), (1.06, 0.1, 0.76), -18, "Snow", 0.03)
    drift("NA_Ground", x0 + 4.5, z0 + 2.2, 6.0, 1.6, 0.9, 33, "Snow", 14)
    for k in range(6):                                              # fallen blocks
        rock("NA_Props", x0 + rnd.uniform(0, 10), 0.1, z0 + rnd.uniform(1.5, 4.0), 0.45, 0.3, 0.35, 3100 + k, "Ruin", 1, 0.12)

def fence():
    """Leaning old fence posts and a sagging rope marking a path up to the graves."""
    mx, mz = MOUND; rnd = random.Random(41)
    for sx in (-1, 1):
        pts = []
        for k in range(7):
            z = -12.0 - k * 2.6
            x = sx * (3.6 + k * 0.08 + rnd.uniform(-0.15, 0.15))
            if k == 4 and sx > 0:                                   # one post fallen over
                rock("NA_Props", x, 0.05, z, 0.12, 0.1, 0.8, 4000 + k, "Wood", 1, 0.1)
                continue
            h = rnd.uniform(1.0, 1.35)
            lx, lz = rnd.uniform(-0.12, 0.12), rnd.uniform(-0.1, 0.1)
            cone_dir("NA_Props", (x, -0.3, z), (lx, 1, lz), 0.09, h + 0.3, "Wood", 5)
            cyl("NA_Props", x + lx * h, h - 0.08, z + lz * h, 0.1, 0.06, 0.1, "Snow", 6)
            drift("NA_Ground", x, z, 0.5, 0.4, 0.22, 4100 + k * 2 + (sx > 0), "Snow", 8)
            pts.append((x + lx * (h - 0.15), h - 0.15, z + lz * (h - 0.15)))
        for a, b in zip(pts, pts[1:]):                              # sagging rope (thin boxes)
            for t0 in (0.0, 0.5):
                t1 = t0 + 0.5
                def at(t):
                    return (a[0] + (b[0] - a[0]) * t, a[1] + (b[1] - a[1]) * t - 0.35 * math.sin(math.pi * t), a[2] + (b[2] - a[2]) * t)
                p0, p1 = at(t0), at(t1)
                _rope(p0, p1)

def _rope(p0, p1, r=0.022):
    g = grp("NA_Props")
    d = Vector((p1[0] - p0[0], -(p1[2] - p0[2]), p1[1] - p0[1])); L = d.length
    M = Matrix.Translation((G(*p0) + G(*p1)) / 2) @ d.normalized().to_track_quat('Z', 'Y').to_matrix().to_4x4()
    rr = bmesh.ops.create_cone(g.bm, cap_ends=False, cap_tris=False, segments=4, radius1=r, radius2=r, depth=L, matrix=M)
    _tag(g, list({f for v in rr["verts"] for f in v.link_faces}), "Wood")

def pine(x, z, h, seed, base_y=0.0):
    g = "NA_Trees"; rnd = random.Random(seed)
    cyl(g, x, base_y - 0.2, z, h * 0.04, h * 0.025, h * 0.35, "Bark", 5)
    tiers = rnd.randint(4, 5)
    for k in range(tiers):
        t = k / tiers
        r = h * 0.28 * (1 - t * 0.75) * rnd.uniform(0.9, 1.1)
        y = base_y + h * (0.18 + 0.68 * t)
        cyl(g, x + rnd.uniform(-0.05, 0.05) * h, y, z, r, 0.0, h * 0.32, "Pine", rnd.choice([6, 7]), rnd.uniform(0, 60))
    drift("NA_Ground", x, z, h * 0.22, h * 0.2, h * 0.05, seed + 1, "Snow", 8)

def dead_tree(x, z, h, seed, base_y=0.0):
    g = "NA_Props"; rnd = random.Random(seed)
    lx = rnd.uniform(-0.12, 0.12)
    cone_dir(g, (x, base_y - 0.4, z), (lx, 1, 0), h * 0.05, h + 0.4, "Bark", 6)
    def branch(p, d, L, r, depth):
        cone_dir(g, p, d, r, L, "Bark", 4)
        if depth == 0:
            return
        for k in range(rnd.randint(1, 3)):
            t = rnd.uniform(0.45, 0.85)
            q = (p[0] + d[0] * L * t, p[1] + d[1] * L * t, p[2] + d[2] * L * t)
            a = rnd.uniform(-1.0, 1.0)
            nd = (d[0] * 0.6 + a, d[1] * 0.7 + rnd.uniform(0.2, 0.6), d[2] * 0.6 + rnd.uniform(-0.5, 0.5))
            nl = math.sqrt(sum(c * c for c in nd)); nd = tuple(c / nl for c in nd)
            branch(q, nd, L * rnd.uniform(0.45, 0.65), r * 0.55, depth - 1)
    for k in range(rnd.randint(3, 5)):
        t = rnd.uniform(0.35, 0.9)
        p = (x + lx * h * t, base_y + h * t, z)
        s = rnd.choice([-1, 1]); dd = (s * rnd.uniform(0.6, 1.0), rnd.uniform(0.3, 0.9), rnd.uniform(-0.4, 0.4))
        nl = math.sqrt(sum(c * c for c in dd)); dd = tuple(c / nl for c in dd)
        branch(p, dd, h * rnd.uniform(0.25, 0.4), h * 0.025, 2)
    drift("NA_Ground", x, z, h * 0.2, h * 0.16, h * 0.06, seed + 1, "Snow", 10)

def build_env():
    """Extra life around the field: forest bands on both sides, dead trees, ruins, the fence path, big ice."""
    ruins(); fence()
    rnd = random.Random(61)
    for k in range(70):                                             # snowy pine forest at the sides and behind
        sx = rnd.choice([-1, 1])
        x = sx * rnd.uniform(20, 38); z = rnd.uniform(-56, -30)
        if k < 22:
            x = rnd.uniform(-38, 38); z = rnd.uniform(-56, -47)
            if abs(x) < 16:
                continue
        pine(x, z, rnd.uniform(5, 10) * (1 + max(0, -z - 40) / 40), 5000 + k)
    for k in range(10):                                             # a few pines a bit closer at the edges
        sx = 1 if k % 2 else -1
        pine(sx * rnd.uniform(24, 32), rnd.uniform(-22, -12), rnd.uniform(4, 6.5), 5200 + k)
    for k, (x, z, h) in enumerate(((-18.5, -14.0, 4.6), (19.5, -15.5, 5.2), (-24.0, -6.0, 3.8), (25.0, -24.0, 5.8),
                                   (-13.5, -31.0, 4.0), (14.5, -36.0, 4.4))):
        dead_tree(x, z, h, 6000 + k * 7)
    for sx, z, s in ((-1, -30.0, 2.6), (1, -26.0, 2.4)):            # big ice formations in the mid-field
        crystal_cluster(sx * 33.0, z, s, 6100 + int(z))
        crystal_cluster(sx * 29.5, z - 5, s * 0.7, 6150 + int(z))

def build_far():
    g = "NA_Far"; rnd = random.Random(4)
    # broken hills and cliffs right behind the field (seen through the mist)
    for k in range(18):
        x = rnd.uniform(-80, 80); z = rnd.uniform(-85, -62)
        if abs(x) < 14 and z > -70:
            continue
        for j in range(3):                                       # each crag is a few overlapping rough spikes
            spire(g, x + rnd.uniform(-5, 5), z + rnd.uniform(-3, 3), rnd.uniform(7, 18) * (1 - 0.25 * j), rnd.uniform(4, 8),
                  1000 + k * 5 + j, "Mountain", (rnd.uniform(-0.12, 0.12), rnd.uniform(-0.05, 0.05)), 3, rnd.choice([7, 8, 9]), 3)
    ridge(g, -110, -260, 260, -4, [(-180, 38, 70), (-110, 30, 50), (-50, 26, 40), (40, 30, 45), (110, 40, 60), (190, 34, 60)], 3, "Mountain")
    ridge(g, -170, -320, 320, -6, [(-240, 60, 90), (-120, 50, 80), (0, 44, 70), (130, 58, 90), (250, 50, 80)], 5, "MountainFar")

def build_cards():
    # sky cylinder
    g = grp("NA_Sky", "Cards"); n = 96; y0, y1 = -40.0, 300.0
    for i in range(n):
        t0, t1 = i / n, (i + 1) / n
        A0, A1 = 2 * math.pi * t0 - math.pi, 2 * math.pi * t1 - math.pi
        p0 = (SKY_R * math.sin(A0), 0, -10 - SKY_R * math.cos(A0)); p1 = (SKY_R * math.sin(A1), 0, -10 - SKY_R * math.cos(A1))
        quad(g, [(p0[0], y0, p0[2]), (p1[0], y0, p1[2]), (p1[0], y1, p1[2]), (p0[0], y1, p0[2])], [(t0, 0), (t1, 0), (t1, 1), (t0, 1)], "SkyCard")
    # mist banks between the layers + a low drift layer blowing across the field behind the fighters
    for i, (z, top, hw) in enumerate(MIST):
        quad("NA_Mist", [(-hw, -0.5, z), (hw, -0.5, z), (hw, top, z), (-hw, top, z)],
             [(0, i + 0.001), (2 * hw / 20.0, i + 0.001), (2 * hw / 20.0, i + 0.999), (0, i + 0.999)], "MistCard")

def build_preview():
    g = grp("Preview_Standins", "Preview")
    for x, m in ((-1.8, "Stand_P1"), (1.8, "Stand_P2")):
        obox(g, (x, 0.875, 0), (0.6, 1.75, 0.3), 0, m)

# ======================================================================
#  lights, render, cameras
# ======================================================================
def build_lights():
    w = bpy.data.worlds.new("World"); bpy.context.scene.world = w; w.use_nodes = True
    bg = w.node_tree.nodes["Background"]
    bg.inputs["Color"].default_value = (*srgb(V["world"][0]), 1); bg.inputs["Strength"].default_value = V["world"][1]
    bpy.context.scene["ce_variant"] = "day"
    bpy.context.scene["ce_world_strength"] = V["world"][1]
    for name, pos, aim, size, (power, colr) in (
            ("Break_Back", (0, 60, -120), (0, 0, -20), (120, 60), V["break"]),       # the bright gap in the clouds
            ("Sky_Top", (0, 50, -15), (0, 0, -15), (100, 100), V["top"]),
            ("Fill_Front", (0, 14, 28), (0, 1, -10), (60, 20), V["fill"])):
        ld = bpy.data.lights.new(name, 'AREA'); ld.shape = 'RECTANGLE'
        ld.size, ld.size_y = size; ld.energy = power; ld.color = srgb(colr)
        o = bpy.data.objects.new(name, ld); col("Lights").objects.link(o); o.location = G(*pos)
        o.rotation_mode = 'QUATERNION'; o.rotation_quaternion = (G(*aim) - G(*pos)).normalized().to_track_quat('-Z', 'Y')
        o.visible_camera = False

def setup_render():
    sc = bpy.context.scene
    sc.render.engine = 'CYCLES'
    prefs = bpy.context.preferences.addons["cycles"].preferences
    try:
        prefs.compute_device_type = 'HIP'; prefs.get_devices()
        for dv in prefs.devices:
            dv.use = (dv.type == 'HIP' and "9070" in dv.name)
        sc.cycles.device = 'GPU'
    except Exception:
        sc.cycles.device = 'CPU'
    sc.cycles.samples = 64; sc.cycles.use_denoising = True
    sc.cycles.max_bounces = 6; sc.cycles.diffuse_bounces = 3; sc.cycles.transparent_max_bounces = 16
    sc.render.resolution_x, sc.render.resolution_y = 1920, 1080
    sc.render.resolution_percentage = 50
    sc.view_settings.view_transform = 'Standard'; sc.view_settings.look = 'None'

CAMS = (("CAM_near", (0, 1.4, 6.5)), ("CAM_mid", (0, 1.9, 9.5)), ("CAM_far", (0, 3.35, 16.0)),
        ("CAM_near_right", (9.3, 1.4, 6.5)), ("CAM_near_left", (-9.3, 1.4, 6.5)),
        ("CAM_far_right", (4.75, 3.35, 16.0)), ("CAM_far_left", (-4.75, 3.35, 16.0)),
        ("CAM_jump_far", (0, 7.5, 16.0)))

def build_cameras():
    for name, pos in CAMS:
        cd = bpy.data.cameras.new(name); cd.sensor_fit = 'VERTICAL'; cd.angle_y = math.radians(30)
        cd.clip_start = 0.1; cd.clip_end = 900
        o = bpy.data.objects.new(name, cd); col("Cameras").objects.link(o)
        o.location = G(*pos); o.rotation_euler = (math.radians(90), 0, 0)
    bpy.context.scene.camera = bpy.data.objects["CAM_mid"]

def build_all():
    reset(); COLS.clear(); MATS.clear(); GR.clear()
    build_materials()
    build_floor(); build_mound(); build_field(); build_env(); build_far(); build_cards(); build_preview()
    objs = {name: g.finish() for name, g in list(GR.items())}
    for n in ("NA_Sky", "NA_Mist"):
        objs[n].visible_shadow = False
    objs["NA_Mist"].hide_render = True
    build_lights(); build_cameras(); setup_render()
    tris = {o.name: sum(len(p.vertices) - 2 for p in o.data.polygons) for o in objs.values()}
    return {"objects": list(objs), "tris": tris, "total_tris": sum(tris.values())}

if __name__ == "__main__":
    BUILD_INFO = build_all()
