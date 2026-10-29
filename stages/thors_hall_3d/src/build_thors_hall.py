# Thors Training Hall - 3D stage build script for Blender 5.x (Morning and Dusk variants)
#
#   exec(open(r"<project>\stages\thors_hall_3d\src\build_thors_hall.py", encoding="utf-8").read(),
#        {"__name__": "__main__", "VARIANT": "dusk"})
#
# VARIANT "day" (Morning, the default) or "dusk": same room and props, different lights, window sky
# and grade (see VARIANTS below and LOOKS in bake_thors_hall.py). run_th.py runs the whole pipeline.
#
# Layout is written in GODOT coordinates (x right, y up, +z toward the camera) and converted
# to Blender (Z-up) by G():  Godot (x, y, z) -> Blender (x, -z, y).  1 unit = 1 m.
# Geometry is accumulated straight into one mesh per texture atlas ("bake group"):
#   TH_Back, TH_Sides, TH_Ceiling, TH_Props  -> baked to textures/<group>.png
#   TH_Outside                               -> sky cards behind the windows: a soft sky gradient that
#                                               lights the room in the bake; Godot draws the animated
#                                               sky (thors_hall_sky.gdshader) on them instead
#   TH_Floor                                 -> baked to textures/floor.png (Godot rebuilds the floor
#                                               as a PlaneMesh with the reflective floor shader)
import bpy, bmesh, math
from mathutils import Vector, Matrix

ROOT = r"E:\Netsu Projects\Netsu Fighter\Godot\netsu-vs\stages\thors_hall_3d"
TEX = ROOT + r"\src\tex"

# ---------------- room dimensions (Godot space, metres) ----------------
HW = 15.5            # side walls at x = +-HW (invisible fight walls are at +-12)
BACK = -27.1         # back wall plane
FRONT = 22.0         # shell continues behind the far camera (z = +16)
CEIL = 9.5
WIN_SILL, WIN_TOP = 0.9, 7.0
CLR_LO, CLR_HI = 7.55, 9.15
BAY = 4.2            # side-wall bay spacing (pilaster to pilaster)
PIER_W = 0.7
COURT_X, COURT_Z = 8.0, -17.5    # orange court lines (painting: corners at x=+-8, z=-17.5)
VARIANT = globals().get("VARIANT") or "day"
# Per-variant lighting. sun_dir = Godot-space direction the sunlight travels.
# sky = (v, colour) stops of the window sky gradient (v 0 = bottom of the cards, 1 = top).
VARIANTS = {
    "day": dict(sun_dir=(-0.62, -0.17, -0.77), sun_energy=6.0, sun_color="#ffcf9a",
                fill_windows=(500, "#dfe8ff"), fill_ceiling=(600, "#fff4e6"), world=("#bcd2f2", 1.5),
                sky=[(0.0, "#94a5ab"), (0.3, "#c6d6e8"), (0.55, "#a9c3e6"), (1.0, "#6a95d9")], sky_strength=0.85,
                flame=12.0, sconce_w=0.0, sconce_color="#ffae5a"),
    # low orange sun, violet sky light, sconces lit (painting: stages/thors_hall/thors_hall_dusk.png)
    "dusk": dict(sun_dir=(-0.70, -0.13, -0.70), sun_energy=5.5, sun_color="#ff9046",
                 fill_windows=(420, "#9d8ce0"), fill_ceiling=(220, "#7a6cb8"), world=("#4a4280", 0.9),
                 sky=[(0.0, "#4a3450"), (0.3, "#ff9a5c"), (0.5, "#d0608a"), (0.75, "#6a3f86"), (1.0, "#3a2a5e")],
                 sky_strength=0.85, flame=22.0, sconce_w=160.0, sconce_color="#ffa04a"),
}
V = VARIANTS[VARIANT]
SUN_DIR = V["sun_dir"]
SUN_ENERGY = V["sun_energy"]
FILL_WINDOWS_W = V["fill_windows"][0]
FILL_CEILING_W = V["fill_ceiling"][0]
WORLD_STRENGTH = V["world"][1]
# Parts of the shell the fight cameras can never see are built into TH_Hidden: they still
# shape the baked light (window shadows, bounce) but are not baked or exported.
VIS_LIMIT = {"TH_Sides": -4.0, "TH_Ceiling": 12.0}
FLOOR_VIS = 6.0

def srgb(h):
    h = h.lstrip('#'); c = [int(h[i:i + 2], 16) / 255 for i in (0, 2, 4)]
    return tuple(((v + 0.055) / 1.055) ** 2.4 if v > 0.04045 else v / 12.92 for v in c)

def G(x, y, z):
    return Vector((x, -z, y))

# ======================================================================
#  scene reset / collections
# ======================================================================
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
#  mesh builder: one bmesh per bake group
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

    def cull(self):
        """Drop faces the fight cameras can never see (outer shell, undersides, faces against walls)."""
        bm = self.bm
        bm.normal_update()
        dead = []
        for f in bm.faces:
            if f[self.custom]:
                continue
            c = f.calc_center_median(); n = f.normal
            gx, gy, gz = c.x, c.z, -c.y          # Godot coords
            nx, ny, nz = n.x, n.z, -n.y
            if (abs(gx) >= HW + 0.45 and gx * nx > 0.5) or (gy >= CEIL + 0.25 and ny > 0.5) \
               or (gz <= BACK - 0.45 and nz < -0.5) or (gy < 0.005 and ny < -0.9) \
               or (gz < BACK + 0.012 and nz < -0.9 and gz > BACK - 0.012) \
               or (abs(gx) > HW - 0.012 and abs(gx) < HW + 0.012 and gx * nx > 0.9):
                dead.append(f)
        bmesh.ops.delete(bm, geom=dead, context='FACES_ONLY')
        return len(dead)

    def finish(self):
        bm = self.bm
        if self.name.startswith("TH_") and self.name not in ("TH_Outside", "TH_Floor", "TH_Hidden"):
            self.cull()
        bm.normal_update()
        # metre-scale box projection for every face without hand-made UVs
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

def box(g, x0, x1, y0, y1, z0, z1, m, bevel=0.0):
    """Axis-aligned box from Godot-space extents into group g."""
    name = g if isinstance(g, str) else g.name
    lim = VIS_LIMIT.get(name)
    if lim is not None:
        zlo, zhi = min(z0, z1), max(z0, z1)
        if zlo >= lim:
            return box("TH_Hidden", x0, x1, y0, y1, zlo, zhi, m, bevel)
        if zhi > lim:
            box(name, x0, x1, y0, y1, zlo, lim, m, bevel)
            return box("TH_Hidden", x0, x1, y0, y1, lim, zhi, m, bevel)
    g = grp(name) if isinstance(g, str) else g
    lo = G(min(x0, x1), min(y0, y1), max(z0, z1)); hi = G(max(x0, x1), max(y0, y1), min(z0, z1))
    c = (lo + hi) / 2; s = hi - lo
    M = Matrix.Translation(c) @ Matrix.Diagonal((abs(s.x), abs(s.y), abs(s.z), 1.0))
    r = bmesh.ops.create_cube(g.bm, size=1.0, matrix=M)
    verts = r["verts"]
    faces = list({f for v in verts for f in v.link_faces})
    _tag(g, faces, m)
    if bevel > 0:
        edges = list({e for v in verts for e in v.link_edges})
        b = min(bevel, 0.45 * min(abs(s.x), abs(s.y), abs(s.z)))
        res = bmesh.ops.bevel(g.bm, geom=verts + edges, offset=b, segments=1, affect='EDGES',
                              profile=0.5, clamp_overlap=True)
        _tag(g, res["faces"], m)

def cyl(g, base, axis, r1, r2, h, m, seg=12):
    """Cone/cylinder starting at Godot point `base`, extending h along Godot axis 'x','y','z'."""
    g = grp(g) if isinstance(g, str) else g
    rot = {"y": Matrix.Identity(4),
           "x": Matrix.Rotation(math.radians(90), 4, 'Y'),
           "z": Matrix.Rotation(math.radians(90), 4, 'X')}[axis]
    d = {"x": (h / 2, 0, 0), "y": (0, h / 2, 0), "z": (0, 0, h / 2)}[axis]
    c = G(base[0] + d[0], base[1] + d[1], base[2] + d[2])
    M = Matrix.Translation(c) @ rot
    r = bmesh.ops.create_cone(g.bm, cap_ends=True, cap_tris=False, segments=seg,
                              radius1=r1, radius2=r2, depth=h, matrix=M)
    faces = list({f for v in r["verts"] for f in v.link_faces})
    _tag(g, faces, m)

def quad(g, pts, uvs, m):
    """Single face from Godot points with explicit UVs (custom mapping)."""
    g = grp(g) if isinstance(g, str) else g
    vs = [g.bm.verts.new(G(*p)) for p in pts]
    f = g.bm.faces.new(vs)
    f.material_index = g.mi(m); f[g.custom] = 1
    for l, uv in zip(f.loops, uvs):
        l[g.uv].uv = uv
    return f

def torus(g, center, axis, R, r, m, seg=12, rseg=6, arc=2 * math.pi, start=0.0):
    """(Partial) torus around Godot axis through center: trophy handles, rings."""
    g = grp(g) if isinstance(g, str) else g
    rings = []
    closed = abs(arc - 2 * math.pi) < 1e-4
    n = seg if closed else seg + 1
    for i in range(n):
        a = start + arc * i / seg
        ring = []
        for j in range(rseg):
            b = 2 * math.pi * j / rseg
            rad = R + r * math.cos(b); off = r * math.sin(b)
            if axis == "z":   p = (center[0] + rad * math.cos(a), center[1] + rad * math.sin(a), center[2] + off)
            elif axis == "x": p = (center[0] + off, center[1] + rad * math.sin(a), center[2] + rad * math.cos(a))
            else:             p = (center[0] + rad * math.cos(a), center[1] + off, center[2] + rad * math.sin(a))
            ring.append(g.bm.verts.new(G(*p)))
        rings.append(ring)
    idx = g.mi(m)
    for i in range(seg):
        A, B = rings[i], rings[(i + 1) % n]
        for j in range(rseg):
            f = g.bm.faces.new((A[j], B[j], B[(j + 1) % rseg], A[(j + 1) % rseg]))
            f.material_index = idx

# ======================================================================
#  materials (procedural Cycles shaders; baked to atlases later)
# ======================================================================
MATS = {}

def _shade(hexcol, k):
    h = hexcol.lstrip('#'); c = [min(255, max(0, int(int(h[i:i + 2], 16) * k))) for i in (0, 2, 4)]
    return "#%02x%02x%02x" % tuple(c)

class NB:
    """Tiny node-tree helper."""
    def __init__(self, name):
        self.m = bpy.data.materials.new(name)
        self.m.use_nodes = True
        self.nt = self.m.node_tree
        self.nt.nodes.clear()
        self.out = self.n("ShaderNodeOutputMaterial", (900, 0))
        self.bsdf = self.n("ShaderNodeBsdfPrincipled", (600, 0))
        self.nt.links.new(self.bsdf.outputs[0], self.out.inputs[0])
        uvn = self.n("ShaderNodeUVMap", (-1200, 0)); uvn.uv_map = "Tex"
        self.uv = uvn.outputs[0]
        MATS[name] = self.m

    def n(self, t, loc=(0, 0), **kw):
        nd = self.nt.nodes.new(t); nd.location = loc
        for k, v in kw.items():
            setattr(nd, k, v)
        return nd

    def l(self, a, ai, b, bi):
        src = a if hasattr(a, "is_linked") else a.outputs[ai]
        self.nt.links.new(src, b.inputs[bi])

    def set(self, **kw):
        names = {"color": "Base Color", "rough": "Roughness", "metal": "Metallic"}
        for k, v in kw.items():
            key = names.get(k, k)
            self.bsdf.inputs[key].default_value = (*srgb(v), 1) if k == "color" else v

    def noise(self, scale, detail=4, rough=0.55, loc=(-900, 0), vec=None):
        nd = self.n("ShaderNodeTexNoise", loc)
        nd.inputs["Scale"].default_value = scale
        nd.inputs["Detail"].default_value = detail
        nd.inputs["Roughness"].default_value = rough
        self.l(vec or self.uv, 0, nd, "Vector")
        return nd

    def ramp(self, fac, stops, loc=(-300, 0)):
        nd = self.n("ShaderNodeValToRGB", loc)
        cr = nd.color_ramp
        while len(cr.elements) < len(stops):
            cr.elements.new(0.5)
        for e, (p, c) in zip(cr.elements, stops):
            e.position = p; e.color = (*srgb(c), 1)
        self.l(fac, 0, nd, 0)
        return nd

    def mix(self, a, b, fac, loc=(0, 0), blend='MIX'):
        nd = self.n("ShaderNodeMix", loc); nd.data_type = 'RGBA'; nd.blend_type = blend
        def feed(val, sock):
            if isinstance(val, (int, float)):
                nd.inputs[sock].default_value = val
            elif isinstance(val, str):
                nd.inputs[sock].default_value = (*srgb(val), 1)
            else:
                self.l(val, 0, nd, sock)
        feed(fac, 0); feed(a, 6); feed(b, 7)
        return nd

    def bump(self, height, strength=0.2, dist=0.02, loc=(300, -300)):
        nd = self.n("ShaderNodeBump", loc)
        nd.inputs["Strength"].default_value = strength
        nd.inputs["Distance"].default_value = dist
        self.l(height, 0, nd, "Height")
        self.nt.links.new(nd.outputs[0], self.bsdf.inputs["Normal"])
        return nd

def m_flat(name, color, rough=0.7, metal=0.0, var=0.08, vscale=3.0):
    b = NB(name)
    n = b.noise(vscale, 3, 0.5)
    r = b.ramp(n, [(0.3, _shade(color, 1 - var)), (0.7, _shade(color, 1 + var))])
    b.l(r, 0, b.bsdf, "Base Color")
    b.set(rough=rough, metal=metal)
    return b

def build_materials():
    # --- brick: warm terracotta with per-brick variation, light mortar, recessed joints
    b = NB("Brick")
    br = b.n("ShaderNodeTexBrick", (-700, 200))
    br.offset = 0.5; br.squash = 1.0
    for k, v in (("Scale", 1.0), ("Mortar Size", 0.014), ("Mortar Smooth", 0.2), ("Bias", 0.0),
                 ("Brick Width", 0.42), ("Row Height", 0.135)):
        br.inputs[k].default_value = v
    br.inputs["Color1"].default_value = (*srgb("#dba086"), 1)
    br.inputs["Color2"].default_value = (*srgb("#c5856b"), 1)
    br.inputs["Mortar"].default_value = (*srgb("#dcc8b6"), 1)
    b.l(b.uv, 0, br, "Vector")
    n = b.noise(0.35, 3, 0.5, (-700, -150))
    big = b.ramp(n, [(0.35, "#c9bdb8"), (0.65, "#ffffff")], (-400, -150))
    c = b.mix(br.outputs["Color"], big.outputs[0], 1.0, (-150, 100), 'MULTIPLY')
    sp = b.noise(28.0, 2, 0.6, (-700, -400))
    spr = b.ramp(sp, [(0.45, "#e9e1dc"), (0.6, "#ffffff")], (-400, -400))
    c2 = b.mix(c.outputs[2], spr.outputs[0], 1.0, (100, 100), 'MULTIPLY')
    b.l(c2.outputs[2], 0, b.bsdf, "Base Color")
    inv = b.n("ShaderNodeMath", (100, -250), operation='SUBTRACT'); inv.inputs[0].default_value = 1.0
    b.nt.links.new(br.outputs["Fac"], inv.inputs[1])
    b.bump(inv, 0.35, 0.01)
    b.set(rough=0.85)

    # --- stone trims (warm grey limestone) and carved stone (frieze / panels)
    for name, base, carved in (("Stone", "#b8b1a5", False), ("StoneCarved", "#b3ab9e", True),
                               ("StoneDark", "#8c8780", False)):
        b = NB(name)
        n = b.noise(2.2, 5, 0.55)
        r = b.ramp(n, [(0.3, _shade(base, 0.9)), (0.7, _shade(base, 1.06))])
        b.l(r, 0, b.bsdf, "Base Color")
        if carved:
            w = b.n("ShaderNodeTexWave", (-900, -300)); w.wave_type = 'RINGS'
            w.inputs["Scale"].default_value = 3.5; w.inputs["Distortion"].default_value = 6.0
            w.inputs["Detail"].default_value = 3.0
            b.l(b.uv, 0, w, "Vector")
            b.bump(w.outputs["Fac"], 0.45, 0.02)
        else:
            b.bump(n.outputs["Fac"], 0.08, 0.01)
        b.set(rough=0.8)

    # --- polished stone floor: lavender-grey marble slabs, dark seams, orange court lines
    b = NB("Floor")
    tile = b.n("ShaderNodeTexBrick", (-700, 300)); tile.offset = 0.0; tile.squash = 1.0
    for k, v in (("Scale", 1.0), ("Brick Width", 3.0), ("Row Height", 3.0), ("Mortar Size", 0.012),
                 ("Mortar Smooth", 0.3), ("Bias", 0.0)):
        tile.inputs[k].default_value = v
    tile.inputs["Color1"].default_value = (*srgb("#b3b8d2"), 1)
    tile.inputs["Color2"].default_value = (*srgb("#a9aecb"), 1)
    tile.inputs["Mortar"].default_value = (*srgb("#666a7d"), 1)
    b.l(b.uv, 0, tile, "Vector")
    marble = b.noise(0.8, 8, 0.62, (-900, -100))
    mr = b.ramp(marble, [(0.38, "#a6abc6"), (0.5, "#ffffff"), (0.62, "#cdd0e2")], (-600, -100))
    c = b.mix(tile.outputs["Color"], mr.outputs[0], 0.55, (-300, 200), 'MULTIPLY')
    sep = b.n("ShaderNodeSeparateXYZ", (-1000, -500)); b.nt.links.new(b.uv, sep.inputs[0])
    def band(src, lo, hi, loc):
        a1 = b.n("ShaderNodeMath", loc, operation='GREATER_THAN'); a1.inputs[1].default_value = lo
        b.nt.links.new(src, a1.inputs[0])
        a2 = b.n("ShaderNodeMath", (loc[0], loc[1] - 120), operation='LESS_THAN'); a2.inputs[1].default_value = hi
        b.nt.links.new(src, a2.inputs[0])
        mm = b.n("ShaderNodeMath", (loc[0] + 160, loc[1] - 60), operation='MULTIPLY')
        b.nt.links.new(a1.outputs[0], mm.inputs[0]); b.nt.links.new(a2.outputs[0], mm.inputs[1])
        return mm
    ax = b.n("ShaderNodeMath", (-850, -700), operation='ABSOLUTE'); b.nt.links.new(sep.outputs[0], ax.inputs[0])
    zz = b.n("ShaderNodeMath", (-850, -950), operation='MULTIPLY'); zz.inputs[1].default_value = -1.0
    b.nt.links.new(sep.outputs[1], zz.inputs[0])                          # Godot z
    side = band(ax.outputs[0], COURT_X - 0.13, COURT_X + 0.13, (-650, -700))   # side lines
    front = band(zz.outputs[0], COURT_Z + 0.13, 99.0, (-650, -950))
    sidem = b.n("ShaderNodeMath", (-300, -800), operation='MULTIPLY')
    b.nt.links.new(side.outputs[0], sidem.inputs[0]); b.nt.links.new(front.outputs[0], sidem.inputs[1])
    backl = band(zz.outputs[0], COURT_Z - 0.13, COURT_Z + 0.13, (-650, -1200))   # back line, wall to wall
    lm = b.n("ShaderNodeMath", (-150, -900), operation='MAXIMUM')
    b.nt.links.new(sidem.outputs[0], lm.inputs[0]); b.nt.links.new(backl.outputs[0], lm.inputs[1])
    wear = b.noise(6.0, 4, 0.6, (-400, -1100))
    wr = b.ramp(wear, [(0.35, "#d9741e"), (0.65, "#f39436")], (-150, -1100))
    c2 = b.mix(c.outputs[2], wr.outputs[0], lm.outputs[0], (150, 0))
    b.l(c2.outputs[2], 0, b.bsdf, "Base Color")
    b.set(rough=0.15)

    # --- ceiling: square acoustic tiles, cool blue-grey
    b = NB("Ceiling")
    t = b.n("ShaderNodeTexBrick", (-700, 200)); t.offset = 0.0
    for k, v in (("Scale", 1.0), ("Brick Width", 1.25), ("Row Height", 1.25), ("Mortar Size", 0.02)):
        t.inputs[k].default_value = v
    t.inputs["Color1"].default_value = (*srgb("#a9afc6"), 1); t.inputs["Color2"].default_value = (*srgb("#a2a8bf"), 1)
    t.inputs["Mortar"].default_value = (*srgb("#5f6476"), 1)
    b.l(b.uv, 0, t, "Vector"); b.nt.links.new(t.outputs["Color"], b.bsdf.inputs["Base Color"]); b.set(rough=0.9)

    m_flat("Beam", "#b2b0b4", 0.8, var=0.06)
    m_flat("Iron", "#33343d", 0.45, metal=0.6, var=0.1)
    m_flat("WindowFrame", "#3b4150", 0.5, metal=0.3, var=0.05)
    m_flat("Glass", "#e4ecf8", 0.1, var=0.0)
    m_flat("RackBoard", "#3a3d4c", 0.6, var=0.05)
    m_flat("Locker", "#22304f", 0.45, var=0.06, vscale=6)
    m_flat("Gold", "#e3ad49", 0.28, metal=1.0, var=0.05)
    m_flat("Steel", "#d6dbe4", 0.2, metal=1.0, var=0.03)
    m_flat("Leather", "#4a2d22", 0.7)
    m_flat("Cork", "#b98552", 0.95, var=0.12, vscale=25)
    m_flat("Can", "#7e8ba0", 0.35, metal=0.7, var=0.06)
    m_flat("Mat", "#34507c", 0.85, var=0.05)
    m_flat("BoxGreen", "#617f40", 0.8); m_flat("BoxTan", "#c9a678", 0.8)
    m_flat("BoxTeal", "#3e7c7a", 0.8); m_flat("BoxOlive", "#99923f", 0.8)
    for name, light, dark in (("Wood", "#b07b48", "#8d5c33"), ("DoorWood", "#7a4c2c", "#5c3820")):
        b = NB(name)
        w = b.n("ShaderNodeTexWave", (-900, 100)); w.wave_type = 'BANDS'; w.bands_direction = 'X'
        w.inputs["Scale"].default_value = 3.0; w.inputs["Distortion"].default_value = 4.0
        w.inputs["Detail"].default_value = 3.0
        b.l(b.uv, 0, w, "Vector")
        r = b.ramp(w.outputs["Fac"], [(0.2, dark), (0.8, light)])
        b.l(r, 0, b.bsdf, "Base Color"); b.set(rough=0.75)

    b = NB("Flame"); b.set(color="#ffcf8a")
    b.bsdf.inputs["Emission Color"].default_value = (*srgb("#ffb860"), 1)
    b.bsdf.inputs["Emission Strength"].default_value = V["flame"]
    for name, fn in (("Banner", "banner.png"), ("Notices", "notices.png")):
        b = NB(name)
        im = b.n("ShaderNodeTexImage", (-600, 0)); im.image = bpy.data.images.load(TEX + "\\" + fn)
        im.interpolation = 'Cubic'; im.extension = 'EXTEND'
        b.l(b.uv, 0, im, "Vector"); b.nt.links.new(im.outputs["Color"], b.bsdf.inputs["Base Color"])
        b.set(rough=0.9 if name == "Banner" else 0.8)
        if name == "Banner":
            b.bsdf.inputs["Sheen Weight"].default_value = 0.3
    b = NB("Outside")   # window sky: emission-only gradient, never lit, never casts
    sep = b.n("ShaderNodeSeparateXYZ", (-900, 0)); b.nt.links.new(b.uv, sep.inputs[0])
    r = b.ramp(sep.outputs[1], V["sky"], (-500, 0))
    em = b.n("ShaderNodeEmission", (300, 0)); em.inputs["Strength"].default_value = V["sky_strength"]
    b.nt.links.new(r.outputs[0], em.inputs["Color"])
    b.nt.links.new(em.outputs[0], b.out.inputs[0])
    m_flat("Stand_P1", "#2d6cdf", 0.6); m_flat("Stand_P2", "#e0463a", 0.6)

# ======================================================================
#  architecture
# ======================================================================
def bay_positions():
    zs = []; z = BACK + 2.6
    while z < FRONT - 1:
        zs.append(z); z += BAY
    return zs

def build_floor():
    g = grp("TH_Floor")
    # Tex UV = (x, -z) in metres; the court-line mask in the floor shader relies on this
    quad(g, [(-HW, 0, FLOOR_VIS), (HW, 0, FLOOR_VIS), (HW, 0, BACK), (-HW, 0, BACK)],
         [(-HW, -FLOOR_VIS), (HW, -FLOOR_VIS), (HW, -BACK), (-HW, -BACK)], "Floor")
    quad("TH_Hidden", [(-HW, 0, FRONT), (HW, 0, FRONT), (HW, 0, FLOOR_VIS), (-HW, 0, FLOOR_VIS)],
         [(-HW, -FRONT), (HW, -FRONT), (HW, -FLOOR_VIS), (-HW, -FLOOR_VIS)], "Floor")

NARROW_PILASTERS = (-9.45, 8.95)    # carry the wall sconces (matches the painting)

def build_back_wall():
    g = "TH_Back"; zb = BACK
    box(g, -HW, HW, 0.7, CLR_LO, zb - 0.5, zb, "Brick")              # brick field
    box(g, -HW, HW, 0.0, 0.72, zb - 0.5, zb + 0.16, "Stone", 0.02)    # skirting
    box(g, -HW, HW, 0.70, 0.86, zb, zb + 0.22, "Stone", 0.03)         # base ledge
    box(g, -HW, HW, 4.50, 4.66, zb, zb + 0.16, "Stone", 0.03)         # string course
    box(g, -HW, HW, 6.50, 6.62, zb, zb + 0.30, "Stone", 0.03)         # frieze bed
    box(g, -HW, HW, 6.62, 7.30, zb, zb + 0.24, "StoneCarved")         # carved frieze
    box(g, -HW, HW, 7.30, 7.55, zb, zb + 0.36, "Stone", 0.04)         # cornice
    # clerestory: piers + mullions + head
    box(g, -HW, HW, CLR_HI, CEIL, zb - 0.5, zb + 0.05, "Stone")
    n = 8; bw = (2 * HW) / n
    for i in range(n + 1):
        x = -HW + i * bw
        box(g, x - 0.32, x + 0.32, CLR_LO, CLR_HI, zb - 0.5, zb + 0.08, "Stone", 0.02)
        if i < n:
            x0, x1 = x + 0.32, x + bw - 0.32
            for k in (1, 2):
                xm = x0 + (x1 - x0) * k / 3
                box(g, xm - 0.04, xm + 0.04, CLR_LO + 0.005, CLR_HI - 0.005, zb - 0.31, zb - 0.19, "WindowFrame")
            ym = (CLR_LO + CLR_HI) / 2
            box(g, x0 + 0.005, x1 - 0.005, ym - 0.04, ym + 0.04, zb - 0.29, zb - 0.21, "WindowFrame")
            quad("TH_Glass", [(x0, CLR_LO, zb - 0.25), (x1, CLR_LO, zb - 0.25), (x1, CLR_HI, zb - 0.25), (x0, CLR_HI, zb - 0.25)],
                 [(0, 0), (1, 0), (1, 1), (0, 1)], "Glass")
    pil = [(-3.6, 0.85), (3.6, 0.85)] + [(x, 0.7) for x in NARROW_PILASTERS]
    for x, w in pil:
        box(g, x - w / 2 - 0.08, x + w / 2 + 0.08, 0.0, 1.0, zb, zb + 0.32, "Stone", 0.03)       # plinth
        box(g, x - w / 2, x + w / 2, 1.0, 6.5, zb, zb + 0.22, "Stone", 0.02)                     # shaft
        box(g, x - w / 2 + 0.1, x + w / 2 - 0.1, 1.5, 6.0, zb + 0.22, zb + 0.25, "StoneCarved")  # carved inset
        box(g, x - w / 2 - 0.06, x + w / 2 + 0.06, 6.2, 6.5, zb, zb + 0.28, "Stone", 0.03)       # capital
    for s in (-1, 1):   # big corner piers (stacked mouldings)
        xc = s * (HW - 0.8)
        box(g, xc - 0.95, xc + 0.95, 0.0, 1.1, zb, zb + 1.05, "Stone", 0.04)
        box(g, xc - 0.8, xc + 0.8, 1.1, 6.4, zb, zb + 0.9, "Stone", 0.03)
        box(g, xc - 0.6, xc + 0.6, 1.6, 5.9, zb + 0.9, zb + 0.95, "StoneCarved")
        box(g, xc - 0.95, xc + 0.95, 6.4, 7.6, zb, zb + 1.05, "StoneCarved", 0.04)
        box(g, xc - 0.8, xc + 0.8, 7.6, CEIL, zb, zb + 0.9, "Stone", 0.03)

def build_side_walls():
    g = "TH_Sides"
    zs = bay_positions()
    for s in (-1, 1):
        xw = s * HW; xo = s * (HW + 0.5)
        x_in, x_out = min(xw, xo), max(xw, xo)
        def inner(off, xw=xw, s=s):     # x just inside the wall face
            return xw - s * off
        box(g, x_in, x_out, 0, 0.72, BACK, FRONT, "Stone")
        box(g, *sorted((xw, inner(0.16))), 0, 0.72, BACK, FRONT, "Stone", 0.02)          # skirting
        if s < 0:   # LEFT: solid brick wall (bulletin board + door)
            box(g, x_in, x_out, 0.72, CEIL, BACK, FRONT, "Brick")
            box(g, *sorted((xw, inner(0.16))), 4.5, 4.66, BACK, FRONT, "Stone", 0.03)
        else:       # RIGHT: wall of windows
            box(g, x_in, x_out, 0.72, WIN_SILL, BACK, FRONT, "Brick")
            box(g, *sorted((xw, inner(0.28))), WIN_SILL - 0.08, WIN_SILL, BACK, FRONT, "Stone", 0.02)   # sill
            box(g, x_in, x_out, WIN_TOP, CEIL, BACK, FRONT, "Brick")
            box(g, *sorted((xw, inner(0.2))), WIN_TOP, WIN_TOP + 0.35, BACK, FRONT, "Stone", 0.03)      # lintel
            edges = [BACK + 1.0] + zs + [FRONT]
            for a, b in zip(edges[:-1], edges[1:]):
                z0, z1 = a + PIER_W / 2, b - PIER_W / 2
                if z1 - z0 < 0.8:
                    continue
                # frame members sit on slightly different depths so no two faces are coplanar
                # (coplanar faces z-fight = flicker when the camera pans)
                xo0, xo1 = sorted((xw + s * 0.17, xw + s * 0.29))     # outer verticals
                xm0, xm1 = sorted((xw + s * 0.18, xw + s * 0.28))     # mullions
                xt0, xt1 = sorted((xw + s * 0.19, xw + s * 0.27))     # transoms
                for zz in (z0 + 0.005, z1 - 0.105):
                    box(g, xo0, xo1, WIN_SILL + 0.005, WIN_TOP - 0.005, zz, zz + 0.1, "WindowFrame")
                for k in (1, 2):
                    zm = z0 + (z1 - z0) * k / 3
                    box(g, xm0, xm1, WIN_SILL + 0.01, WIN_TOP - 0.01, zm - 0.045, zm + 0.045, "WindowFrame")
                for yy in (WIN_SILL + 0.06, 2.6, 4.2, 5.7, WIN_TOP - 0.06):
                    box(g, xt0, xt1, yy - 0.045, yy + 0.045, z0 + 0.11, z1 - 0.11, "WindowFrame")
                if (z0 + z1) / 2 < -3.0:   # glass pane (exported only; softens the view outside)
                    X = xw + s * 0.235
                    quad("TH_Glass", [(X, WIN_SILL, z0), (X, WIN_SILL, z1), (X, WIN_TOP, z1), (X, WIN_TOP, z0)],
                         [(0, 0), (1, 0), (1, 1), (0, 1)], "Glass")
        for z in zs:   # pilasters on both side walls (frame the shot at the screen edges)
            if s < 0 and -18.2 < z < -9.0:
                continue   # leave the bulletin-board bay open
            box(g, *sorted((xw + s * 0.3, inner(0.3))), 0, CEIL, z - PIER_W / 2, z + PIER_W / 2, "Stone", 0.03)
            box(g, *sorted((xw, inner(0.42))), 0, 1.0, z - PIER_W / 2 - 0.08, z + PIER_W / 2 + 0.08, "Stone", 0.03)
            box(g, *sorted((xw, inner(0.4))), 6.9, 7.5, z - PIER_W / 2 - 0.06, z + PIER_W / 2 + 0.06, "StoneCarved", 0.03)
    # left wall: double door near the back corner
    xw = -HW
    box(g, xw, xw + 0.18, 0, 3.25, -23.85, -20.95, "StoneDark", 0.03)     # surround
    box(g, xw, xw + 0.22, 3.25, 3.55, -24.05, -20.75, "Stone", 0.03)      # head
    box("TH_Props", xw, xw + 0.24, 0, 2.95, -23.6, -22.43, "DoorWood", 0.015)
    box("TH_Props", xw, xw + 0.24, 0, 2.95, -22.37, -21.2, "DoorWood", 0.015)
    for z0 in (-23.4, -22.17):
        for y0 in (0.35, 1.7):
            box("TH_Props", xw + 0.24, xw + 0.27, y0, y0 + 1.0, z0, z0 + 0.77, "DoorWood")
    for zz in (-22.62, -22.23):
        box("TH_Props", xw + 0.24, xw + 0.32, 1.35, 1.6, zz, zz + 0.05, "Gold")

def build_ceiling():
    g = "TH_Ceiling"
    box(g, -HW, HW, CEIL, CEIL + 0.3, BACK, FRONT, "Ceiling")
    box(g, -HW, HW, CEIL - 0.95, CEIL, BACK, BACK + 1.1, "Beam", 0.04)
    box(g, -HW, HW, CEIL - 1.15, CEIL - 0.95, BACK, BACK + 1.25, "Beam", 0.03)
    for s in (-1, 1):
        box(g, *sorted((s * HW, s * (HW - 1.0))), CEIL - 0.95, CEIL, BACK, FRONT, "Beam", 0.04)
        box(g, *sorted((s * (HW - 1.0), s * (HW - 1.15))), CEIL - 1.1, CEIL - 0.8, BACK, FRONT, "Beam", 0.02)
        for k in range(4):    # stepped corner brace where the beams meet
            box(g, *sorted((s * (HW - 1.0 - k * 0.35), s * (HW - 1.35 - k * 0.35))),
                CEIL - 1.15 - k * 0.3, CEIL - 0.95, BACK + 1.1, BACK + 1.9, "Beam", 0.02)
    for z in bay_positions():
        box(g, -HW, HW, CEIL - 0.6, CEIL, z - 0.3, z + 0.3, "Beam", 0.03)

# ======================================================================
#  props
# ======================================================================
def build_banner():
    g = grp("TH_Props"); zb = BACK + 0.3
    W, H, top = 3.75, 5.5, 6.25
    nx, ny = 12, 20
    side_end = 0.813            # fraction of the height where the side edges end (painting)
    verts = []
    for j in range(ny + 1):
        row = []
        for i in range(nx + 1):
            u = i / nx
            bot = side_end + (1 - side_end) * (1 - abs(2 * u - 1))
            t = j / ny * bot
            x = -W / 2 + u * W
            y = top - t * H
            z = zb + 0.035 * math.sin(u * math.pi * 5) * (0.3 + t) + 0.06 * t
            row.append((g.bm.verts.new(G(x, y, z)), (u, 1 - t * 1500 / 1536)))
        verts.append(row)
    idx = g.mi("Banner")
    for j in range(ny):
        for i in range(nx):
            q = [verts[j][i], verts[j + 1][i], verts[j + 1][i + 1], verts[j][i + 1]]
            f = g.bm.faces.new([v for v, _ in q])
            f.material_index = idx; f[g.custom] = 1
            for l, (_, uv) in zip(f.loops, q):
                l[g.uv].uv = uv
    cyl(g, (-2.15, top + 0.05, zb), "x", 0.05, 0.05, 4.3, "Iron")              # rod
    cyl(g, (-2.33, top + 0.05, zb), "x", 0.0, 0.09, 0.18, "Gold")              # finials
    cyl(g, (2.15, top + 0.05, zb), "x", 0.09, 0.0, 0.18, "Gold")
    for s in (-1, 1):
        box(g, s * 2.05 - 0.02, s * 2.05 + 0.02, top + 0.05, top + 0.55, zb - 0.02, zb + 0.02, "Iron")

def build_racks():
    zb = BACK + 0.16; g = "TH_Props"
    for s in (-1, 1):
        x0, x1 = (-8.0, -5.5) if s < 0 else (5.2, 7.7)
        for k, y in enumerate((1.6, 2.25, 2.9, 3.55)):
            box(g, x0, x1, y, y + 0.46, zb, zb + 0.08, "RackBoard", 0.01)
            box(g, x0 - 0.03, x1 + 0.03, y - 0.03, y, zb, zb + 0.1, "Gold")
            box(g, x0 - 0.03, x1 + 0.03, y + 0.46, y + 0.49, zb, zb + 0.1, "Gold")
            for hx in (x0 + 0.45, x1 - 0.45):
                box(g, hx - 0.03, hx + 0.03, y + 0.12, y + 0.2, zb + 0.08, zb + 0.18, "Iron")
            yc = y + 0.24; zc = zb + 0.17; gx = x0 + 0.25          # sabre, hilt on the left
            box(g, gx - 0.08, gx, yc - 0.045, yc + 0.045, zc - 0.04, zc + 0.04, "Gold", 0.01)
            cyl(g, (gx, yc, zc), "x", 0.03, 0.03, 0.22, "Leather", 8)
            cyl(g, (gx + 0.22, yc, zc), "x", 0.11, 0.07, 0.07, "Steel", 14)
            box(g, gx + 0.29, x1 - 0.22, yc - 0.03, yc + 0.03, zc - 0.008, zc + 0.008, "Steel")
            box(g, x1 - 0.22, x1 - 0.1, yc - 0.015, yc + 0.015, zc - 0.006, zc + 0.006, "Steel")

def build_sconces():
    zb = BACK + 0.22; g = "TH_Props"
    for x in NARROW_PILASTERS:
        y = 3.75
        box(g, x - 0.12, x + 0.12, y - 0.4, y + 0.08, zb, zb + 0.06, "Iron", 0.01)       # back plate
        box(g, x - 0.04, x + 0.04, y - 0.1, y - 0.02, zb + 0.06, zb + 0.4, "Iron")      # arm
        cyl(g, (x, y - 0.2, zb + 0.45), "y", 0.1, 0.07, 0.12, "Iron", 8)               # cup
        cyl(g, (x, y - 0.08, zb + 0.45), "y", 0.1, 0.1, 0.42, "Flame", 8)              # glass lamp
        cyl(g, (x, y + 0.34, zb + 0.45), "y", 0.13, 0.0, 0.2, "Iron", 8)               # cap

def crate(x, y, z, w, h, d, m="Wood"):
    g = "TH_Props"
    box(g, x - w / 2, x + w / 2, y, y + h, z - d / 2, z + d / 2, m, 0.015)
    f = 0.06; zf = z + d / 2
    for xx in (x - w / 2, x + w / 2 - f):
        box(g, xx, xx + f, y, y + h, zf, zf + 0.02, "DoorWood")
    box(g, x - w / 2, x + w / 2, y, y + f, zf, zf + 0.02, "DoorWood")
    box(g, x - w / 2, x + w / 2, y + h - f, y + h, zf, zf + 0.02, "DoorWood")
    L = math.hypot(w - 2 * f, h - 2 * f); ang = math.atan2(h - 2 * f, w - 2 * f)
    gg = grp(g)
    for sgn in (1, -1):
        M = (Matrix.Translation(G(x, y + h / 2, zf + 0.01)) @
             Matrix.Rotation(sgn * ang, 4, 'Y') @ Matrix.Diagonal((L, 0.02, 0.05, 1)))
        r = bmesh.ops.create_cube(gg.bm, size=1.0, matrix=M)
        _tag(gg, list({f_ for v in r["verts"] for f_ in v.link_faces}), "DoorWood")

def can(x, y, z, r=0.2, h=0.32, m="Can"):
    cyl("TH_Props", (x, y, z), "y", r, r, h, m, 14)
    cyl("TH_Props", (x, y + h, z), "y", r * 1.04, r * 1.04, 0.03, "Iron", 14)
    for yy in (y + h * 0.3, y + h * 0.65):
        cyl("TH_Props", (x, yy, z), "y", r * 1.02, r * 1.02, 0.025, "Iron", 14)

def build_shelf_left():
    g = "TH_Props"; zb = BACK + 0.2
    x0, x1, d = -13.7, -9.95, 0.85
    tiers = (0.25, 1.45, 2.6, 3.55)
    for xx in (x0, (x0 + x1) / 2 - 0.04, x1 - 0.08):
        for zz in (zb, zb + d - 0.08):
            box(g, xx, xx + 0.08, 0, 3.65, zz, zz + 0.08, "Iron")
    for y in tiers:
        box(g, x0 - 0.05, x1 + 0.05, y, y + 0.07, zb, zb + d, "Iron", 0.01)
        box(g, x0 - 0.05, x1 + 0.05, y - 0.1, y, zb + d - 0.05, zb + d, "Iron")
    zc = zb + d / 2
    can(-13.3, 2.67, zc, 0.22, 0.4); crate(-12.3, 2.67, zc, 0.85, 0.72, 0.7)
    can(-11.3, 2.67, zc, 0.16, 0.14); can(-10.9, 2.67, zc, 0.16, 0.14); can(-10.4, 2.67, zc, 0.24, 0.42)
    can(-13.4, 1.52, zc, 0.16, 0.14); can(-13.4, 1.68, zc, 0.15, 0.14); can(-13.0, 1.52, zc, 0.16, 0.2)
    box(g, -12.75, -11.95, 1.52, 2.05, zb + 0.1, zb + 0.75, "BoxGreen", 0.015)
    box(g, -11.9, -11.05, 1.52, 2.03, zb + 0.1, zb + 0.75, "BoxTan", 0.015)
    box(g, -11.0, -10.55, 1.52, 2.03, zb + 0.1, zb + 0.75, "BoxTeal", 0.015)
    box(g, -10.5, -10.05, 1.52, 1.86, zb + 0.15, zb + 0.7, "BoxOlive", 0.015)
    crate(-13.25, 0.0, zb + 1.1, 0.8, 0.62, 0.7)
    crate(-10.5, 0.0, zb + 1.1, 0.8, 0.62, 0.7)
    for k in range(3):
        box(g, -12.25, -11.3, 0.32 + k * 0.1, 0.42 + k * 0.1, zb + 0.15, zb + 0.75, "Mat", 0.03)
    # extra equipment along the left wall (screen-left edge in the far camera)
    crate(-14.6, 0.0, -9.0, 1.0, 0.9, 1.0); crate(-14.55, 0.9, -9.05, 0.85, 0.7, 0.85)
    crate(-14.6, 0.0, -7.7, 0.9, 0.75, 0.9)
    can(-13.6, 0.0, -8.6, 0.3, 0.55); can(-13.55, 0.0, -7.9, 0.24, 0.4, "Iron")
    cyl(g, (-14.7, 0.0, -6.5), "y", 0.36, 0.38, 0.9, "Wood", 14)               # practice-sword barrel
    for yy in (0.15, 0.75):
        cyl(g, (-14.7, yy, -6.5), "y", 0.39, 0.39, 0.05, "Iron", 14)
    for k, (dx, dz) in enumerate(((-0.12, 0.05), (0.1, -0.1), (0.0, 0.14), (0.15, 0.12), (-0.15, -0.12))):
        cyl(g, (-14.7 + dx, 0.5, -6.5 + dz), "y", 0.03, 0.025, 1.25 + 0.05 * k, "Wood", 6)

def trophy(x, y, z, kind, s=1.0):
    g = "TH_Props"
    box(g, x - 0.17 * s, x + 0.17 * s, y, y + 0.12 * s, z - 0.13 * s, z + 0.13 * s, "RackBoard", 0.01)
    box(g, x - 0.12 * s, x + 0.12 * s, y + 0.12 * s, y + 0.18 * s, z - 0.09 * s, z + 0.09 * s, "Gold", 0.01)
    if kind == "cup":
        cyl(g, (x, y + 0.18 * s, z), "y", 0.035 * s, 0.025 * s, 0.12 * s, "Gold", 10)
        cyl(g, (x, y + 0.30 * s, z), "y", 0.04 * s, 0.15 * s, 0.22 * s, "Gold", 14)
        for sg in (-1, 1):
            torus(g, (x + sg * 0.15 * s, y + 0.42 * s, z), "z", 0.06 * s, 0.012 * s, "Gold", 10, 5,
                  arc=math.pi, start=-math.pi / 2 if sg > 0 else math.pi / 2)
    elif kind == "horseshoe":
        torus(g, (x, y + 0.42 * s, z), "z", 0.13 * s, 0.03 * s, "Gold", 12, 6, arc=math.pi * 1.4, start=-math.pi * 0.2)
        cyl(g, (x, y + 0.18 * s, z), "y", 0.05 * s, 0.04 * s, 0.16 * s, "Gold", 10)
    else:
        cyl(g, (x, y + 0.18 * s, z), "y", 0.09 * s, 0.09 * s, 0.24 * s, "Gold", 12)
        cyl(g, (x, y + 0.42 * s, z), "y", 0.02 * s, 0.11 * s, 0.18 * s, "Gold", 10)
        cyl(g, (x, y + 0.60 * s, z), "y", 0.11 * s, 0.02 * s, 0.18 * s, "Gold", 10)

def panel_trim(g, a, b, ya, yb, zf):
    for (p0, p1, q0, q1) in ((a, b, ya, ya + 0.03), (a, b, yb - 0.03, yb), (a, a + 0.03, ya, yb), (b - 0.03, b, ya, yb)):
        box(g, p0, p1, q0, q1, zf, zf + 0.02, "Gold")

def build_cabinets_right():
    g = "TH_Props"; zb = BACK + 0.2; d = 0.7
    x0, x1, h = 9.38, 11.65, 3.35                                      # double locker
    box(g, x0, x1, 0.08, h, zb, zb + d, "Locker", 0.03)
    box(g, x0 - 0.04, x1 + 0.04, 0, 0.1, zb, zb + d + 0.04, "Locker", 0.02)
    box(g, x0 - 0.05, x1 + 0.05, h, h + 0.1, zb, zb + d + 0.05, "Locker", 0.02)
    xm = (x0 + x1) / 2
    for a, b in ((x0 + 0.08, xm - 0.03), (xm + 0.03, x1 - 0.08)):
        for (ya, yb) in ((0.25, 0.95), (1.1, 3.15)):
            panel_trim(g, a + 0.1, b - 0.1, ya, yb, zb + d)
        hx = b - 0.2 if a < xm else a + 0.17
        box(g, hx, hx + 0.04, 1.75, 2.05, zb + d, zb + d + 0.05, "Steel")
    box(g, xm - 0.02, xm + 0.02, 0.1, h, zb + d, zb + d + 0.02, "RackBoard")
    x0, x1, h = 11.8, 13.7, 3.8                                        # trophy cabinet
    box(g, x0, x1, 0.0, 1.25, zb, zb + d, "Locker", 0.03)
    for k in range(3):
        wcell = (x1 - x0 - 0.2) / 3
        a = x0 + 0.1 + k * wcell
        panel_trim(g, a + 0.08, a + wcell - 0.08, 0.2, 1.03, zb + d)
    box(g, x0, x1, 1.25, h, zb, zb + 0.06, "Locker")
    for xx in (x0, x1 - 0.1):
        box(g, xx, xx + 0.1, 1.25, h, zb, zb + d - 0.05, "Locker", 0.02)
    for y in (1.25, 2.45, h - 0.12):
        box(g, x0, x1, y, y + 0.1, zb, zb + d - 0.03, "Locker", 0.02)
        box(g, x0 + 0.02, x1 - 0.02, y + 0.1, y + 0.12, zb + d - 0.06, zb + d - 0.03, "Gold")
    box(g, x0 - 0.06, x1 + 0.06, h, h + 0.14, zb, zb + d + 0.03, "Locker", 0.03)
    zc = zb + 0.38
    for xx in (12.2, 12.75, 13.3):
        trophy(xx, 2.55, zc, "cup", 1.1)
    for xx, kind in ((12.2, "horseshoe"), (12.75, "cup"), (13.3, "column")):
        trophy(xx, 1.35, zc, kind, 1.1)
    bx0, bx1 = 13.9, 15.0                                              # bench under the windows
    box(g, bx0, bx1, 0.42, 0.5, -11.0, -4.5, "Wood", 0.015)
    for zz in (-10.8, -7.8, -4.8):
        box(g, bx0 + 0.1, bx1 - 0.1, 0, 0.42, zz, zz + 0.12, "Iron")

def build_board_left():
    g = grp("TH_Props"); xw = -HW
    z0, z1, y0, y1 = -17.5, -9.5, 1.15, 3.05
    box(g, xw, xw + 0.06, y0, y1, z0, z1, "Cork")
    for (a0, a1, b0, b1) in ((y0 - 0.08, y0, z0 - 0.08, z1 + 0.08), (y1, y1 + 0.08, z0 - 0.08, z1 + 0.08),
                             (y0, y1, z0 - 0.08, z0), (y0, y1, z1, z1 + 0.08)):
        box(g, xw, xw + 0.1, a0, a1, b0, b1, "Wood", 0.01)
    box(g, xw, xw + 0.14, y1 + 0.12, y1 + 0.5, -14.3, -12.7, "Wood", 0.01)       # header plate
    import random
    rnd = random.Random(5)
    spots = [(-17.0, 1.95, 0.75), (-16.1, 1.3, 0.62), (-15.2, 2.05, 0.8), (-14.2, 1.35, 0.7),
             (-13.2, 2.0, 0.78), (-12.1, 1.3, 0.66), (-11.1, 2.1, 0.72), (-10.15, 1.4, 0.7)]
    x = xw + 0.075
    for k, (z, y, s) in enumerate(spots):
        cu, cv = (k % 4) / 4, 1 - (k // 4 + 1) / 2
        hgt = s * 1.0; wid = s * 0.78; ang = rnd.uniform(-0.04, 0.04)
        pts = []
        for (dz, dy) in ((wid / 2, -hgt / 2), (-wid / 2, -hgt / 2), (-wid / 2, hgt / 2), (wid / 2, hgt / 2)):
            rz = dz * math.cos(ang) - dy * math.sin(ang); ry = dz * math.sin(ang) + dy * math.cos(ang)
            pts.append((x, y + hgt / 2 + ry, z + rz))
        quad(g, pts, [(cu, cv), (cu + 0.25, cv), (cu + 0.25, cv + 0.5), (cu, cv + 0.5)], "Notices")

def build_outside():
    g = grp("TH_Outside", "Outside")
    X = 26.0      # right vista card (through the right-hand windows), faces -x
    quad(g, [(X, -8, BACK - 50), (X, -8, FRONT + 30), (X, 24, FRONT + 30), (X, 24, BACK - 50)],
         [(0, 0), (1, 0), (1, 1), (0, 1)], "Outside")
    Z = BACK - 14.0   # back vista card (through the clerestory), faces +z
    quad(g, [(-45, -2, Z), (45, -2, Z), (45, 30, Z), (-45, 30, Z)],
         [(0, 0.35), (0.6, 0.35), (0.6, 1.0), (0, 1.0)], "Outside")

def build_preview():
    g = grp("Preview_Standins", "Preview")
    for x, m in ((-1.8, "Stand_P1"), (1.8, "Stand_P2")):
        box(g, x - 0.3, x + 0.3, 0, 1.75, -0.15, 0.15, m, 0.05)

# ======================================================================
#  lighting, render setup, cameras
# ======================================================================
def build_lights():
    sd = bpy.data.lights.new("Sun", 'SUN')
    sd.energy = SUN_ENERGY; sd.color = srgb(V["sun_color"]); sd.angle = math.radians(1.2)
    s = bpy.data.objects.new("Sun", sd); col("Lights").objects.link(s)
    d = Vector(SUN_DIR).normalized()
    s.rotation_mode = 'QUATERNION'
    s.rotation_quaternion = Vector((d.x, -d.z, d.y)).to_track_quat('-Z', 'Y')
    # soft skylight fill from the window wall + gentle overhead fill (a bright training hall)
    ld = bpy.data.lights.new("Fill_Windows", 'AREA'); ld.shape = 'RECTANGLE'
    ld.size, ld.size_y = 6.0, 48.0; ld.energy = FILL_WINDOWS_W; ld.color = srgb(V["fill_windows"][1])
    o = bpy.data.objects.new("Fill_Windows", ld); col("Lights").objects.link(o)
    o.location = G(HW - 0.4, 4.0, -4.0); o.rotation_euler = (0, math.radians(90), 0)
    o.visible_camera = False
    ld = bpy.data.lights.new("Fill_Ceiling", 'AREA'); ld.shape = 'RECTANGLE'
    ld.size, ld.size_y = 26.0, 34.0; ld.energy = FILL_CEILING_W; ld.color = srgb(V["fill_ceiling"][1])
    o = bpy.data.objects.new("Fill_Ceiling", ld); col("Lights").objects.link(o)
    o.location = G(0.0, CEIL - 1.3, -8.0)
    o.visible_camera = False
    if V["sconce_w"] > 0:   # lit wall sconces (dusk): warm pools on the back wall
        for k, x in enumerate(NARROW_PILASTERS):
            ld = bpy.data.lights.new("Fill_Sconce%d" % k, 'POINT'); ld.energy = V["sconce_w"]
            ld.color = srgb(V["sconce_color"]); ld.shadow_soft_size = 0.25
            o = bpy.data.objects.new("Fill_Sconce%d" % k, ld); col("Lights").objects.link(o)
            o.location = G(x, 3.88, BACK + 0.84)      # just in front of the glass lamp
            o.visible_camera = False
    w = bpy.data.worlds.new("World"); bpy.context.scene.world = w; w.use_nodes = True
    bg = w.node_tree.nodes["Background"]
    bg.inputs["Color"].default_value = (*srgb(V["world"][0]), 1); bg.inputs["Strength"].default_value = WORLD_STRENGTH
    bpy.context.scene["th_variant"] = VARIANT            # read by bake_thors_hall.py
    bpy.context.scene["th_world_strength"] = WORLD_STRENGTH

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
    sc.cycles.samples = 96
    sc.cycles.use_denoising = True
    sc.cycles.max_bounces = 6; sc.cycles.diffuse_bounces = 4; sc.cycles.glossy_bounces = 2
    sc.render.resolution_x, sc.render.resolution_y = 1920, 1080
    sc.render.resolution_percentage = 50
    sc.view_settings.view_transform = 'Standard'
    sc.view_settings.look = 'None'
    sc.view_settings.exposure = 0.0

CAMS = (("CAM_near", (0, 1.4, 6.5)), ("CAM_mid", (0, 1.9, 9.5)), ("CAM_far", (0, 3.35, 16.0)),
        ("CAM_near_right", (9.3, 1.4, 6.5)), ("CAM_near_left", (-9.3, 1.4, 6.5)),
        ("CAM_far_right", (4.75, 3.35, 16.0)), ("CAM_far_left", (-4.75, 3.35, 16.0)),
        ("CAM_jump_far", (0, 7.5, 16.0)))

def build_cameras():
    for name, pos in CAMS:
        cd = bpy.data.cameras.new(name); cd.sensor_fit = 'VERTICAL'; cd.angle_y = math.radians(30)
        cd.clip_start = 0.1; cd.clip_end = 300
        o = bpy.data.objects.new(name, cd); col("Cameras").objects.link(o)
        o.location = G(*pos); o.rotation_euler = (math.radians(90), 0, 0)
    bpy.context.scene.camera = bpy.data.objects["CAM_mid"]

def render(cam, path):
    sc = bpy.context.scene
    sc.camera = bpy.data.objects[cam]
    sc.render.filepath = path
    bpy.ops.render.render(write_still=True)

def build_all():
    reset(); COLS.clear(); MATS.clear(); GR.clear()
    build_materials()
    build_floor(); build_back_wall(); build_side_walls(); build_ceiling()
    build_banner(); build_racks(); build_sconces(); build_shelf_left(); build_cabinets_right()
    build_board_left(); build_outside(); build_preview()
    objs = {name: g.finish() for name, g in list(GR.items())}
    objs["TH_Outside"].visible_shadow = False
    objs["TH_Glass"].hide_render = True          # glass never takes part in the bake
    build_lights(); build_cameras(); setup_render()
    tris = {o.name: sum(len(p.vertices) - 2 for p in o.data.polygons) for o in objs.values()}
    return {"objects": list(objs), "tris": tris, "total_tris": sum(tris.values())}

if __name__ == "__main__":
    BUILD_INFO = build_all()
