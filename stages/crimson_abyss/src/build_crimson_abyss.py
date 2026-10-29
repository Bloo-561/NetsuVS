# Crimson Abyss - 3D stage build script (Blender 5.x, runs fine in --background)
#
#   blender --background --factory-startup --python build_crimson_abyss.py
#
# Layout is written in GODOT coordinates (x right, y up, +z toward the camera) and converted
# to Blender (Z-up) by G():  Godot (x, y, z) -> Blender (x, -z, y).  1 unit = 1 m.
# Baked groups (atlases):  CA_Ground, CA_Spires, CA_Float, CA_Mountains, CA_Floor (light map only)
# Card groups (Godot shaders, not baked): CA_Sky, CA_Tendrils, CA_Streaks, CA_Mist
import bpy, bmesh, math, random
from mathutils import Vector, Matrix

ROOT = r"E:\Netsu Projects\Netsu Fighter\Godot\netsu-vs\stages\crimson_abyss"
TEXD = ROOT + r"\textures"

# ---------------- layout (Godot space, metres) ----------------
CRATER_Z = -8.0                # crater centre (x = 0)
WALL_R0, WALL_R1, WALL_H = 55.0, 75.0, 5.0    # flat floor radius, wall top radius, wall height
FLOOR_X = 56.0                 # floor quad: x +-56, z -64..+48 (inside the wall)
FLOOR_BACK, FLOOR_FRONT = CRATER_Z - 56.0, CRATER_Z + 56.0
LANE_X, LANE_Z = 12.5, -9.0    # keep |x| < 12.5 and z > -9 clear of props (fight lane)
SKY_R = 185.0                  # sky cylinder radius (around the crater centre)
CRACK_COLOR = "#ff2e8e"
CRACK_STRENGTH = 6.0
# lighting
WORLD_COLOR, WORLD_STRENGTH = "#3a2e48", 1.0
SKY_EMIT = 1.6
RIM_COLOR, RIM_W = "#ff2a66", 30000
FILL_COLOR, FILL_W = "#9a8cc0", 14000
TOP_COLOR, TOP_W = "#b08ad0", 16000
CORE_COLOR, CORE_W = "#a060e0", 60000

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

def obox(g, center, size, rot=(0, 0, 0), m="Rock", bevel=0.0):
    """Oriented box. center/size in Godot space, rot = Godot-space Euler degrees (x, y, z)."""
    g = grp(g) if isinstance(g, str) else g
    # Godot rotation about (x, y, z) == Blender rotation about (x, -z(y-axis), y(z-axis))
    R = (Matrix.Rotation(math.radians(rot[1]), 4, 'Z') @ Matrix.Rotation(math.radians(rot[0]), 4, 'X')
         @ Matrix.Rotation(math.radians(-rot[2]), 4, 'Y'))
    M = Matrix.Translation(G(*center)) @ R @ Matrix.Diagonal((size[0], size[2], size[1], 1.0))
    r = bmesh.ops.create_cube(g.bm, size=1.0, matrix=M)
    verts = r["verts"]
    _tag(g, list({f for v in verts for f in v.link_faces}), m)
    if bevel > 0:
        edges = list({e for v in verts for e in v.link_edges})
        res = bmesh.ops.bevel(g.bm, geom=verts + edges, offset=bevel, segments=1, affect='EDGES',
                              profile=0.5, clamp_overlap=True)
        _tag(g, res["faces"], m)

def quad(g, pts, uvs, m):
    g = grp(g) if isinstance(g, str) else g
    vs = [g.bm.verts.new(G(*p)) for p in pts]
    f = g.bm.faces.new(vs)
    f.material_index = g.mi(m); f[g.custom] = 1
    for l, uv in zip(f.loops, uvs):
        l[g.uv].uv = uv
    return f

def spire(g, x, z, h, r, seed, m="Rock", lean=(0.0, 0.0), sink=1.5, segs=None, rings=5, tip_y=None):
    """Jagged faceted rock spire (crystal-like). Base sunk below y=0 by `sink`."""
    g = grp(g) if isinstance(g, str) else g
    rnd = random.Random(seed)
    segs = segs or rnd.choice([5, 6, 7])
    bm = g.bm
    ring_v = []
    base_y = -sink
    for k in range(rings):
        t = k / rings
        y = base_y + (h + sink) * t
        rad = r * (1 - t) ** 0.85 * rnd.uniform(0.85, 1.12)
        ox, oz = lean[0] * t * t * h, lean[1] * t * t * h
        a0 = rnd.random() * 6.283
        ring = []
        for i in range(segs):
            a = a0 + 6.283 * i / segs + rnd.uniform(-0.22, 0.22)
            rr = rad * rnd.uniform(0.72, 1.15)
            ring.append(bm.verts.new(G(x + ox + rr * math.cos(a), y + rnd.uniform(-0.08, 0.08) * h / rings,
                                       z + oz + rr * math.sin(a))))
        ring_v.append(ring)
    tip = bm.verts.new(G(x + lean[0] * h, base_y + h + sink if tip_y is None else tip_y, z + lean[1] * h))
    new = []
    for k in range(rings - 1):
        A, B = ring_v[k], ring_v[k + 1]
        for i in range(segs):
            j = (i + 1) % segs
            new.append(bm.faces.new((A[i], A[j], B[j])))
            new.append(bm.faces.new((A[i], B[j], B[i])))
    T = ring_v[-1]
    for i in range(segs):
        new.append(bm.faces.new((T[i], T[(i + 1) % segs], tip)))
    bmesh.ops.recalc_face_normals(bm, faces=new)
    _tag(g, new, m)
    return new

def rock(g, x, y, z, sx, sy, sz, seed, m="Rock", sub=1, jag=0.28, flat_bottom=True):
    g = grp(g) if isinstance(g, str) else g
    rnd = random.Random(seed)
    M = Matrix.Translation(G(x, y, z)) @ Matrix.Rotation(rnd.uniform(0, 6.28), 4, 'Z') @ \
        Matrix.Diagonal((sx, sz, sy, 1.0))
    r = bmesh.ops.create_icosphere(g.bm, subdivisions=sub, radius=1.0, matrix=M)
    verts = r["verts"]
    c = G(x, y, z)
    for v in verts:
        d = v.co - c
        v.co = c + d * rnd.uniform(1 - jag, 1 + jag * 0.6)
        if flat_bottom and v.co.z < 0.0:
            v.co.z = rnd.uniform(-0.25, -0.05)
    faces = list({f for v in verts for f in v.link_faces})
    _tag(g, faces, m)

def ridge(g, z, x0, x1, base, peaks, seed, m="Mountain", n=90, depth=8.0, noise=1.0):
    """Mountain range sheet facing +z. peaks = [(x, height, half_width), ...]."""
    g = grp(g) if isinstance(g, str) else g
    rnd = random.Random(seed)
    bm = g.bm
    def prof(x):
        h = 0.0
        for (px, ph, pw) in peaks:
            d = abs(x - px) / pw
            if d < 1:
                h = max(h, ph * (1 - d) ** 1.15)
        return h
    cols = []
    for i in range(n + 1):
        x = x0 + (x1 - x0) * i / n + rnd.uniform(-0.3, 0.3) * (x1 - x0) / n
        top = base + max(2.0, prof(x)) + rnd.uniform(-1, 1) * noise * (2 if i % 2 else 0.6)
        mid = base + (top - base) * rnd.uniform(0.45, 0.65)
        zf = z + rnd.uniform(-1.5, 1.5)
        cols.append((bm.verts.new(G(x, base - 4, zf + 2)), bm.verts.new(G(x + rnd.uniform(-1, 1), mid, zf + rnd.uniform(-1, 2))),
                     bm.verts.new(G(x, top, zf - rnd.uniform(0, 2))), bm.verts.new(G(x, top - 1.5, zf - depth))))
    new = []
    for i in range(n):
        a, b = cols[i], cols[i + 1]
        for r in range(3):
            new.append(bm.faces.new((a[r], b[r], b[r + 1])))
            new.append(bm.faces.new((a[r], b[r + 1], a[r + 1])))
    for f in new:
        f.normal_update()
    # make everything face the camera (+z Godot == -y Blender)
    for f in new:
        if f.normal.y > 0:
            f.normal_flip()
    _tag(g, new, m)

def strip(g, pts, width, m, uv_id=0, segs=28, along_u=True, normal=None):
    """Ribbon along a cubic Bezier (4 Godot points), facing +z. UV.x along, UV.y = id + across."""
    g = grp(g) if isinstance(g, str) else g
    P = [Vector(p) for p in pts]
    def bez(t):
        u = 1 - t
        return P[0] * u ** 3 + P[1] * 3 * u * u * t + P[2] * 3 * u * t * t + P[3] * t ** 3
    rows = []
    for i in range(segs + 1):
        t = i / segs
        p = bez(t); q = bez(min(1, t + 1e-3)) - bez(max(0, t - 1e-3))
        if normal is not None:
            side = q.normalized().cross(Vector(normal)).normalized() * width * 0.5
        else:
            q.z = 0; q.normalize()
            side = Vector((-q.y, q.x, 0)) * width * 0.5
        rows.append((g.bm.verts.new(G(*(p - side))), g.bm.verts.new(G(*(p + side))), t))
    idx = g.mi(m)
    for i in range(segs):
        a, b = rows[i], rows[i + 1]
        f = g.bm.faces.new((a[0], b[0], b[1], a[1]))
        f.material_index = idx; f[g.custom] = 1
        for l, uv in zip(f.loops, ((a[2], uv_id + 0.0), (b[2], uv_id + 0.0), (b[2], uv_id + 1.0), (a[2], uv_id + 1.0))):
            l[g.uv].uv = uv
        f.normal_update()
        if f.normal.y > 0:          # face the camera
            f.normal_flip()

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

    def math(self, op, a, b=None, loc=(0, 0)):
        nd = self.n("ShaderNodeMath", loc, operation=op)
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
            e.position = p; e.color = (*srgb(c), 1) if isinstance(c, str) else c
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

def rock_material(name, base_dark, base_light, top_col, crack_amount, haze=False):
    b = NB(name)
    n1 = b.noise(b.pos, 0.35, 5, 0.6)
    col = b.ramp(n1.outputs["Fac"], [(0.3, base_dark), (0.7, base_light)])
    # dusty / sky-lit tops (Blender Z up)
    sep = b.n("ShaderNodeSeparateXYZ"); b.link(b.normal, sep.inputs[0])
    up = b.math('MAXIMUM', sep.outputs[2], 0.0)
    up = b.math('POWER', up, 2.0)
    col = b.mixc(col, top_col, up)
    # glowing fractures: 3D voronoi edges, only in noisy patches
    warp = b.noise(b.pos, 0.8, 3, 0.5)
    wv = b.n("ShaderNodeMix"); wv.data_type = 'VECTOR'; wv.inputs[0].default_value = 0.18
    b.link(b.pos, wv.inputs[4]); b.link(warp.outputs["Color"], wv.inputs[5])
    vor = b.n("ShaderNodeTexVoronoi"); vor.feature = 'DISTANCE_TO_EDGE'
    vor.inputs["Scale"].default_value = 0.22
    b.link(wv.outputs[1], vor.inputs["Vector"])
    edge = b.math('LESS_THAN', vor.outputs["Distance"], 0.03)
    patch = b.noise(b.pos, 0.12, 2, 0.5)
    pm = b.math('GREATER_THAN', patch.outputs["Fac"], 1.0 - crack_amount)
    crack = b.math('MULTIPLY', edge, pm)
    col = b.mixc(col, "#120a16", crack)
    b.link(col, b.bsdf.inputs["Base Color"])
    b.bsdf.inputs["Roughness"].default_value = 0.65
    b.bsdf.inputs["Emission Color"].default_value = (*srgb(CRACK_COLOR), 1)
    es = b.math('MULTIPLY', crack, CRACK_STRENGTH)
    b.link(es, b.bsdf.inputs["Emission Strength"])
    bump = b.n("ShaderNodeBump"); bump.inputs["Strength"].default_value = 0.25
    b.link(n1.outputs["Fac"], bump.inputs["Height"]); b.link(bump.outputs[0], b.bsdf.inputs["Normal"])
    if haze:
        # atmospheric perspective baked in: blend toward glowing violet haze with distance
        sp = b.n("ShaderNodeSeparateXYZ"); b.link(b.pos, sp.inputs[0])
        cxz = b.n("ShaderNodeCombineXYZ"); b.link(sp.outputs[0], cxz.inputs[0])
        b.link(b.math('SUBTRACT', sp.outputs[1], -CRATER_Z), cxz.inputs[1])
        rad = b.n("ShaderNodeVectorMath"); rad.operation = 'LENGTH'; b.link(cxz.outputs[0], rad.inputs[0])
        mr = b.n("ShaderNodeMapRange"); mr.inputs["From Min"].default_value = 70
        mr.inputs["From Max"].default_value = 160; mr.inputs["To Min"].default_value = 0.08
        mr.inputs["To Max"].default_value = 0.42
        b.link(rad.outputs["Value"], mr.inputs[0])
        # higher = slightly less haze (peaks cut through the mist)
        hz = b.n("ShaderNodeMapRange"); hz.inputs["From Min"].default_value = -15
        hz.inputs["From Max"].default_value = 30; hz.inputs["To Min"].default_value = 1.0
        hz.inputs["To Max"].default_value = 0.6
        b.link(sp.outputs[2], hz.inputs[0])
        f = b.math('MULTIPLY', mr.outputs[0], hz.outputs[0])
        em = b.n("ShaderNodeEmission"); em.inputs["Color"].default_value = (*srgb("#6a2c86"), 1)
        em.inputs["Strength"].default_value = 1.0
        mix = b.n("ShaderNodeMixShader"); b.link(f, mix.inputs[0])
        b.link(b.bsdf.outputs[0], mix.inputs[1]); b.link(em.outputs[0], mix.inputs[2])
        b.link(mix.outputs[0], b.out.inputs[0])
    return b

def image_mat(name, fn, emit=None, alpha=False, uv_scale=None, crack_fn=None):
    b = NB(name)
    vec = b.uv
    if uv_scale:
        mp = b.n("ShaderNodeMapping"); mp.inputs["Scale"].default_value = (uv_scale, uv_scale, 1)
        b.link(b.uv, mp.inputs[0]); vec = mp.outputs[0]
    im = b.n("ShaderNodeTexImage"); im.image = bpy.data.images.load(TEXD + "\\" + fn, check_existing=True)
    b.link(vec, im.inputs[0])
    if emit is not None:
        em = b.n("ShaderNodeEmission"); em.inputs["Strength"].default_value = emit
        b.link(im.outputs["Color"], em.inputs["Color"])
        if alpha:
            tr = b.n("ShaderNodeBsdfTransparent"); mix = b.n("ShaderNodeMixShader")
            b.link(im.outputs["Alpha"], mix.inputs[0]); b.link(tr.outputs[0], mix.inputs[1])
            b.link(em.outputs[0], mix.inputs[2]); b.link(mix.outputs[0], b.out.inputs[0])
        else:
            b.link(em.outputs[0], b.out.inputs[0])
        return b
    b.link(im.outputs["Color"], b.bsdf.inputs["Base Color"])
    b.bsdf.inputs["Roughness"].default_value = 0.35
    if crack_fn:
        cr = b.n("ShaderNodeTexImage"); cr.image = bpy.data.images.load(TEXD + "\\" + crack_fn, check_existing=True)
        cr.image.colorspace_settings.name = 'Non-Color'
        b.link(vec, cr.inputs[0])
        b.bsdf.inputs["Emission Color"].default_value = (*srgb(CRACK_COLOR), 1)
        rg = b.n("ShaderNodeTexImage"); rg.image = bpy.data.images.load(TEXD + "\\floor_region.png", check_existing=True)
        rg.image.colorspace_settings.name = 'Non-Color'
        mp2 = b.n("ShaderNodeMapping"); mp2.inputs["Scale"].default_value = (1 / 64.0, 1 / 64.0, 1)
        b.link(b.uv, mp2.inputs[0]); b.link(mp2.outputs[0], rg.inputs[0])
        reg = b.math('ADD', b.math('MULTIPLY', rg.outputs["Color"], 0.85), 0.15)
        es = b.math('MULTIPLY', b.math('MULTIPLY', cr.outputs["Color"], reg), CRACK_STRENGTH * 0.7)
        b.link(es, b.bsdf.inputs["Emission Strength"])
    return b

def build_materials():
    rock_material("Rock", "#3e3646", "#5c5268", "#857796", 0.18)
    rock_material("Spire", "#433a4e", "#625872", "#8a7a9e", 0.28)
    rock_material("Mountain", "#3a3244", "#564c66", "#7a6c8e", 0.12, haze=True)
    rock_material("Shard", "#3e2c50", "#6a4c86", "#9a78c8", 0.75)
    image_mat("FloorStone", "floor_albedo.png", uv_scale=1 / 8.0, crack_fn="floor_cracks.png")
    image_mat("SkyCard", "sky.png", emit=SKY_EMIT)
    image_mat("TendrilCard", "tendril.png", emit=1.0, alpha=True)
    image_mat("StreakCard", "streak.png", emit=2.0, alpha=True)
    image_mat("MistCard", "mist.png", emit=0.6, alpha=True)
    b = NB("Stand_P1"); b.bsdf.inputs["Base Color"].default_value = (*srgb("#2d6cdf"), 1)
    b = NB("Stand_P2"); b.bsdf.inputs["Base Color"].default_value = (*srgb("#e0463a"), 1)

# ======================================================================
#  geometry
# ======================================================================
def in_lane(x, z, pad=0.0):
    return abs(x) < LANE_X + pad and z > LANE_Z - pad

def polar(r, th, y=0.0):
    """Godot point at radius r / angle th (0 = straight ahead of the camera) around the crater centre."""
    return (r * math.sin(th), y, CRATER_Z - r * math.cos(th))

def build_floor():
    g = grp("CA_Floor")
    quad(g, [(-FLOOR_X, 0, FLOOR_FRONT), (FLOOR_X, 0, FLOOR_FRONT), (FLOOR_X, 0, FLOOR_BACK), (-FLOOR_X, 0, FLOOR_BACK)],
         [(-FLOOR_X, -FLOOR_FRONT), (FLOOR_X, -FLOOR_FRONT), (FLOOR_X, -FLOOR_BACK), (-FLOOR_X, -FLOOR_BACK)], "FloorStone")

def build_crater_wall():
    """Rocky annulus rising from the flat crater floor to the foot of the spike ring."""
    g = grp("CA_Ground"); bm = g.bm; rnd = random.Random(41)
    nr, na = 7, 120
    rows = []
    for i in range(nr + 1):
        t = i / nr
        r = WALL_R0 + (WALL_R1 - WALL_R0) * t
        row = []
        for j in range(na):
            th = 2 * math.pi * j / na + rnd.uniform(-0.01, 0.01)
            y = WALL_H * (t ** 1.4) + (rnd.uniform(-0.5, 0.9) * t if i > 0 else -0.05)
            rr = r + rnd.uniform(-0.8, 0.8) * (t > 0)
            row.append(bm.verts.new(G(*polar(rr, th, y))))
        rows.append(row)
    idx = g.mi("Rock")
    for i in range(nr):
        for j in range(na):
            a, b = rows[i][j], rows[i][(j + 1) % na]
            c, d = rows[i + 1][(j + 1) % na], rows[i + 1][j]
            for tri in ((a, b, c), (a, c, d)):
                f = bm.faces.new(tri); f.material_index = idx; f.normal_update()
                if f.normal.z < 0:
                    f.normal_flip()
    # boulders on the slope and along its foot
    for k in range(150):
        th = rnd.uniform(-math.pi, math.pi); t = rnd.random() ** 0.7
        r = WALL_R0 - 1.5 + (WALL_R1 - WALL_R0) * t
        x, y, z = polar(r, th, WALL_H * (max(t, 0) ** 1.4))
        if in_lane(x, z, 2.0):
            continue
        s = rnd.uniform(0.6, 2.6) * (0.6 + t)
        rock(g, x, y - 0.3, z, s * rnd.uniform(0.9, 1.6), s * rnd.uniform(0.5, 1.0), s, rnd.randint(0, 99999), "Rock", sub=1)

def build_ground():
    g = "CA_Ground"; rnd = random.Random(7)
    build_crater_wall()
    for i in range(170):   # rubble + lifted slabs on the crater floor, never in the fight lane
        th = rnd.uniform(-math.pi, math.pi); r = WALL_R0 * math.sqrt(rnd.uniform(0.05, 1.0))
        x, _, z = polar(r, th)
        if in_lane(x, z, 1.0) or z > FLOOR_FRONT:
            continue
        s = rnd.uniform(0.15, 0.7) * (1.0 + 1.2 * (r / WALL_R0) ** 3)
        rock(g, x, 0, z, s * rnd.uniform(0.8, 1.6), s * rnd.uniform(0.5, 1.0), s, rnd.randint(0, 99999), "Rock", sub=1)
    for i in range(22):
        th = rnd.uniform(-math.pi, math.pi); r = rnd.uniform(16, WALL_R0 - 2)
        x, _, z = polar(r, th)
        if in_lane(x, z, 1.5) or z > FLOOR_FRONT:
            continue
        obox(g, (x, 0.25, z), (rnd.uniform(1.5, 3.5), 0.4, rnd.uniform(1.2, 2.6)),
             (rnd.uniform(-18, 18), rnd.uniform(0, 180), rnd.uniform(-22, 22)), "FloorStone", 0.03)
    # foreground framing shards (screen edges; seen when the camera pans toward a wall)
    for sgn in (-1, 1):
        for k, (xx, zz, h, r) in enumerate(((14.5, 4.0, 5.5, 1.4), (17.0, 1.0, 8.0, 2.0), (15.5, -3.5, 4.0, 1.1),
                                           (20.0, 5.0, 6.5, 1.8), (23.0, -1.0, 10.0, 2.6), (19.0, -7.0, 5.0, 1.5))):
            spire(g, sgn * xx, zz, h, r, 1000 + k * 7 + (sgn > 0) * 50, "Rock",
                  lean=(sgn * rnd.uniform(0.05, 0.18), rnd.uniform(-0.08, 0.08)), sink=1.0)

def build_spires():
    """The ring of spiked mountains all around the crater, leaning inward like claws."""
    g = "CA_Spires"; rnd = random.Random(11)
    for row, (r0, r1, hmul, step) in enumerate(((WALL_R1 - 2, WALL_R1 + 8, 1.0, 3.0), (WALL_R1 + 10, WALL_R1 + 24, 1.25, 4.0))):
        th = -math.pi
        while th < math.pi:
            front = math.cos(th)                       # 1 straight ahead, -1 behind the camera
            h = (5 + 7 * max(front, 0) ** 1.5 + 3 * (1 - abs(front))) * hmul * rnd.uniform(0.55, 1.4)
            r = rnd.uniform(r0, r1)
            x, _, z = polar(r, th)
            rad = rnd.uniform(1.8, 3.4) * (0.6 + h / 20)
            k = rnd.uniform(0.08, 0.22)
            spire(g, x, z, h + WALL_H * 0.6, rad, rnd.randint(0, 99999), "Spire",
                  lean=(-math.sin(th) * k, math.cos(th) * k), sink=2.0, segs=rnd.choice([6, 7, 8]), rings=6)
            if rnd.random() < 0.45:                    # a smaller spike leaning off the big one
                x2, _, z2 = polar(r - rad * 0.8, th + rnd.uniform(-0.03, 0.03))
                spire(g, x2, z2, h * rnd.uniform(0.35, 0.6) + WALL_H * 0.5, rad * 0.5, rnd.randint(0, 99999), "Spire",
                      lean=(-math.sin(th) * k * 1.8, math.cos(th) * k * 1.8), sink=1.0, rings=4)
            th += math.radians(step * rnd.uniform(0.7, 1.3))

FLOATERS = [(-18, 11.0, -28, 1.3), (-30, 18.0, -38, 2.2), (14, 13.0, -30, 1.1), (28, 20.0, -40, 2.4),
            (-6, 22.0, -50, 1.6), (40, 26.0, -34, 2.6), (-42, 15.0, -22, 1.8), (22, 9.0, -22, 0.9)]

def build_floaters_v2():
    """Floating crystal shards: an upward and a downward point joined at a jagged waist."""
    g = grp("CA_Float"); rnd = random.Random(23); bm = g.bm
    for i, (x, y, z, s) in enumerate(FLOATERS):
        segs = rnd.choice([5, 6]); a0 = rnd.random() * 6.28
        waist = []
        for k in range(segs):
            a = a0 + 6.283 * k / segs + rnd.uniform(-0.25, 0.25)
            rr = s * rnd.uniform(0.7, 1.1)
            waist.append(bm.verts.new(G(x + rr * math.cos(a), y + rnd.uniform(-0.2, 0.2) * s, z + rr * math.sin(a))))
        top = bm.verts.new(G(x + rnd.uniform(-0.4, 0.4) * s, y + s * rnd.uniform(1.8, 2.6), z))
        bot = bm.verts.new(G(x + rnd.uniform(-0.4, 0.4) * s, y - s * rnd.uniform(1.3, 2.0), z))
        new = []
        for k in range(segs):
            a, b = waist[k], waist[(k + 1) % segs]
            new.append(bm.faces.new((a, b, top))); new.append(bm.faces.new((b, a, bot)))
        bmesh.ops.recalc_face_normals(bm, faces=new)
        _tag(g, new, "Shard")

def build_mountains():
    """Far ring of peaks in the haze beyond the spike ring."""
    g = "CA_Mountains"; rnd = random.Random(5)
    th = -math.pi
    while th < math.pi:
        front = math.cos(th)
        r = rnd.uniform(135, 165)
        x, _, z = polar(r, th)
        h = (11 + 8 * max(front, 0)) * rnd.uniform(0.7, 1.3)
        spire(g, x, z, h, rnd.uniform(6, 11), rnd.randint(0, 99999), "Mountain",
              lean=(rnd.uniform(-0.06, 0.06), 0), sink=4, segs=rnd.choice([6, 7, 8]), rings=6)
        th += math.radians(rnd.uniform(5, 9))

def build_sky():
    """Full 360 degree storm-sky cylinder around the crater. UV.x runs 0..2 (shader ping-pongs the image)."""
    g = grp("CA_Sky", "Cards")
    n = 96; y0, y1 = -30.0, 150.0
    for i in range(n):
        t0, t1 = i / n, (i + 1) / n
        A0, A1 = 2 * math.pi * t0 - math.pi, 2 * math.pi * t1 - math.pi
        p0 = polar(SKY_R, A0); p1 = polar(SKY_R, A1)
        quad(g, [(p0[0], y0, p0[2]), (p1[0], y0, p1[2]), (p1[0], y1, p1[2]), (p0[0], y1, p0[2])],
             [(2 * t0, 0), (2 * t1, 0), (2 * t1, 1), (2 * t0, 1)], "SkyCard")

TENDRIL_COUNT = 10

def build_tendrils():
    """Shadow tendrils placed around the crater; Godot orbits them around it (energy circling the fight)."""
    rnd = random.Random(77)
    for i in range(TENDRIL_COUNT):
        th = 2 * math.pi * i / TENDRIL_COUNT + rnd.uniform(-0.15, 0.15)
        R = rnd.uniform(115, 140)
        y0 = rnd.uniform(16, 30); span = rnd.uniform(30, 48); sgn = rnd.choice((-1, 1))
        # wide swooping S-curves across the sky (like the painting), not columns
        loc = [(0, y0), (sgn * rnd.uniform(22, 34), y0 + span * 0.25), (-sgn * rnd.uniform(0, 12), y0 + span * 0.7),
               (sgn * rnd.uniform(34, 52), y0 + span)]
        c = Vector(polar(R, th)); tdir = Vector((math.cos(th), 0, math.sin(th)))
        pts = [tuple(c + tdir * s + Vector((0, y, 0))) for (s, y) in loc]
        inward = (-math.sin(th), 0.0, math.cos(th))
        strip(grp("CA_Tendrils", "Cards"), pts, rnd.uniform(3.2, 5.0), "TendrilCard", uv_id=i, normal=inward)

STREAKS = [((-60, 78, -150), (-38, 52, -150)), ((-20, 90, -150), (-8, 62, -150)), ((18, 86, -150), (28, 60, -150)),
           ((50, 80, -150), (64, 56, -150)), ((-90, 70, -150), (-74, 50, -150))]

def build_streaks():
    g = grp("CA_Streaks", "Cards")
    for i, (a, b) in enumerate(STREAKS):
        A, B = Vector(a), Vector(b); d = (B - A); d.z = 0; d.normalize()
        s = Vector((-d.y, d.x, 0)) * 0.9
        quad(g, [tuple(A - s), tuple(B - s), tuple(B + s), tuple(A + s)], [(0, i), (1, i), (1, i + 1), (0, i + 1)], "StreakCard")

MIST_RINGS = [(WALL_R0 + 4, -1.0, 5.0, 48), (WALL_R1 + 6, 0.5, 12.0, 56), (118, 0.0, 22.0, 64)]   # r, y0, y1, segments

def build_mist():
    """Rings of mist cards facing the crater centre: at the wall foot, between the spikes, and far out."""
    g = grp("CA_Mist", "Cards")
    for i, (r, y0, y1, n) in enumerate(MIST_RINGS):
        for k in range(n):
            a0, a1 = 2 * math.pi * k / n - math.pi, 2 * math.pi * (k + 1) / n - math.pi
            p0, p1 = polar(r, a0), polar(r, a1)
            u0, u1 = k / n * (2 * math.pi * r / 40.0), (k + 1) / n * (2 * math.pi * r / 40.0)
            quad(g, [(p0[0], y0, p0[2]), (p1[0], y0, p1[2]), (p1[0], y1, p1[2]), (p0[0], y1, p0[2])],
                 [(u0, i), (u1, i), (u1, i + 1), (u0, i + 1)], "MistCard")

def build_preview():
    g = grp("Preview_Standins", "Preview")
    for x, m in ((-1.8, "Stand_P1"), (1.8, "Stand_P2")):
        obox(g, (x, 0.875, 0), (0.6, 1.75, 0.3), (0, 0, 0), m)

# ======================================================================
#  lights, render, cameras
# ======================================================================
def build_lights():
    # the fight's energy: a big violet glow high above the crater centre lights the inner faces of the ring
    ld = bpy.data.lights.new("Core_Glow", 'POINT'); ld.energy = CORE_W; ld.color = srgb(CORE_COLOR)
    ld.shadow_soft_size = 12.0
    o = bpy.data.objects.new("Core_Glow", ld); col("Lights").objects.link(o); o.location = G(0, 60, CRATER_Z)
    o.visible_camera = False
    w = bpy.data.worlds.new("World"); bpy.context.scene.world = w; w.use_nodes = True
    bg = w.node_tree.nodes["Background"]
    bg.inputs["Color"].default_value = (*srgb(WORLD_COLOR), 1); bg.inputs["Strength"].default_value = WORLD_STRENGTH
    for name, pos, aim, size, power, colr in (
            ("Rim_Back", (0, 55, -100), (0, 0, -8), (140, 50), RIM_W, RIM_COLOR),
            ("Fill_Front", (0, 22, 34), (0, 0, -10), (80, 30), FILL_W, FILL_COLOR),
            ("Key_Top", (-30, 70, -10), (0, 0, -40), (60, 60), TOP_W, TOP_COLOR)):
        ld = bpy.data.lights.new(name, 'AREA'); ld.shape = 'RECTANGLE'
        ld.size, ld.size_y = size; ld.energy = power; ld.color = srgb(colr)
        o = bpy.data.objects.new(name, ld); col("Lights").objects.link(o)
        o.location = G(*pos)
        d = (G(*aim) - G(*pos)).normalized()
        o.rotation_mode = 'QUATERNION'; o.rotation_quaternion = d.to_track_quat('-Z', 'Y')
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
        cd.clip_start = 0.1; cd.clip_end = 600
        o = bpy.data.objects.new(name, cd); col("Cameras").objects.link(o)
        o.location = G(*pos); o.rotation_euler = (math.radians(90), 0, 0)
    bpy.context.scene.camera = bpy.data.objects["CAM_mid"]

def render(cam, path):
    sc = bpy.context.scene
    sc.camera = bpy.data.objects[cam]; sc.render.filepath = path
    bpy.ops.render.render(write_still=True)

def build_all():
    reset(); COLS.clear(); MATS.clear(); GR.clear()
    build_materials()
    build_floor(); build_ground(); build_spires(); build_floaters_v2(); build_mountains()
    build_sky(); build_tendrils(); build_streaks(); build_mist(); build_preview()
    objs = {name: g.finish() for name, g in list(GR.items())}
    for n in ("CA_Sky", "CA_Tendrils", "CA_Streaks", "CA_Mist"):
        objs[n].visible_shadow = False
    for n in ("CA_Tendrils", "CA_Streaks", "CA_Mist"):
        objs[n].hide_render = True            # animated in Godot; not part of the bake
    build_lights(); build_cameras(); setup_render()
    tris = {o.name: sum(len(p.vertices) - 2 for p in o.data.polygons) for o in objs.values()}
    return {"objects": list(objs), "tris": tris, "total_tris": sum(tris.values())}

if __name__ == "__main__":
    BUILD_INFO = build_all()
