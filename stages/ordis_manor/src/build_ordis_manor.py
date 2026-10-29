# Ordis Royal Manor - 3D stage build script (Blender 5.x, runs in --background).
# The grand office of the manor: a polished marble hall with gold inlays, tall windows over the sea,
# bookshelves, the lord's desk and throne-like chair under the crest, purple banners and two chandeliers.
#   VARIANT=day     calm and sunny
#   VARIANT=ruined  after the attack: cracked floor, rubble, fires, smoke, torn banners, soot and cracks
#
#   blender --background --factory-startup --python run_om.py -- VARIANT=ruined STEPS=build,bake,preview,export
#
# Layout is written in GODOT coordinates (x right, y up, +z toward the camera) and converted
# to Blender (Z-up) by G():  Godot (x, y, z) -> Blender (x, -z, y).  1 unit = 1 m.
# Baked groups (atlases): OM_Walls, OM_Furniture, OM_Ceiling, OM_Floor (light map only)
# Card groups (Godot shaders): OM_Window, OM_Glow (emit in the bake), OM_Flame, OM_Fire, OM_Smoke, OM_Haze (not baked)
import bpy, bmesh, math, random
from mathutils import Vector, Matrix

ROOT = r"E:\Netsu Projects\Netsu Fighter\Godot\netsu-vs\stages\ordis_manor"
TEXD = ROOT + r"\src\tex"
VARIANT = globals().get("VARIANT") or "day"
RUIN = VARIANT == "ruined"

# ---------------- layout (Godot space, metres) ----------------
FLOOR_X = 26.0                     # floor quad: x +-26, z -28.5..+18
FLOOR_BACK, FLOOR_FRONT = -28.5, 18.0
LANE_X, LANE_Z = 12.5, -9.0        # keep |x| < 12.5 and z > -9 clear (fight lane)
CENTER_Z = -8.0
WALL_H, WALL_T = 12.4, 0.6         # ceiling height, wall thickness
SILL, WIN_TOP = 1.1, 7.6           # window openings
# the room outline (an elongated octagon), outer corner -> inner corner on each side
P1, P2, P3 = (26.0, -12.0), (14.0, -21.0), (10.0, -27.0)

VARIANTS = {
    "day": dict(world=("#d8c8b0", 0.45), fill=(2600, "#ffe8cc"), top=(1800, "#ffdcb0"),
                window_w=650, window_color="#e6efff", window_emit=2.6,
                candle_w=26, sconce_w=60, lamp_w=45, cove_w=18, fire_w=0),
    "ruined": dict(world=("#c8a888", 0.38), fill=(2000, "#ffd8b4"), top=(1200, "#ffc89a"),
                   window_w=560, window_color="#e8eeff", window_emit=2.3,
                   candle_w=18, sconce_w=40, lamp_w=30, cove_w=10, fire_w=230),
}
V = VARIANTS[VARIANT]

FIRES = [   # (x, y, z, size) - Ruined variant only; also drive the soot on the walls
    (-11.1, 1.0, -23.7, 0.9), (11.3, 0.25, -23.0, 1.2), (-6.6, 2.9, -26.0, 0.8), (5.6, 0.25, -25.2, 1.1),
    (-3.7, 0.2, -22.3, 0.7), (-9.6, 0.3, -25.3, 1.1), (9.4, 0.3, -25.1, 0.9), (-14.6, 0.35, -18.9, 1.3),
    (15.0, 0.35, -19.2, 1.4), (-21.5, 0.3, -13.4, 1.2), (22.0, 0.3, -14.0, 1.0), (-19.6, 1.0, -16.0, 0.8),
    (20.3, 1.0, -15.3, 0.9), (-13.4, 10.6, -20.2, 1.0), (13.5, 10.5, -20.2, 0.9), (-24.6, 9.9, -11.9, 1.1),
    (24.7, 9.7, -12.1, 0.9), (-16.0, 0.3, 4.4, 0.9), (17.0, 0.3, 5.8, 0.7),
    (-6.0, 0.05, -12.8, 0.5), (7.2, 0.05, -11.0, 0.45)]
SOOT_FIRES = [f for f in FIRES if f[3] >= 0.7]
SMOKES = [  # (x, y, z, width, height) - columns rising to the ceiling (Ruined)
    (-11.1, 1.4, -23.9, 2.2, 9.5), (5.6, 1.0, -25.4, 2.6, 10.0), (-9.6, 1.0, -25.5, 2.4, 10.0),
    (-14.6, 1.2, -19.1, 3.0, 10.0), (15.0, 1.2, -19.4, 3.2, 10.0), (-21.5, 1.0, -13.6, 3.0, 10.0),
    (22.0, 1.0, -14.2, 2.6, 10.0), (-6.6, 3.5, -26.1, 1.8, 8.0), (-16.0, 1.0, 4.2, 2.0, 7.0)]
HAZE = [    # (z, y0, y1, half-width) - smoke gathering under the ceiling + a low layer at the back (Ruined).
            # Each card runs on into the walls so its ends never show.
    (-25.6, 7.0, 12.4, 16.0), (-19.0, 7.6, 12.4, 22.0), (-12.0, 8.4, 12.4, 28.0), (-4.0, 9.4, 12.4, 28.0),
    (-24.0, -0.3, 3.2, 16.0)]
RUBBLE = [  # (x, z, radius, height) - Ruined
    (-14.6, -19.0, 2.0, 0.9), (15.0, -19.3, 2.2, 1.0), (-21.5, -13.4, 1.8, 0.7), (22.0, -14.0, 1.6, 0.6),
    (-10.3, -25.0, 1.3, 0.55), (10.8, -23.0, 1.8, 0.8), (-16.4, 4.6, 2.2, 0.9), (17.2, 6.0, 1.6, 0.6),
    (-6.4, -13.2, 0.9, 0.25), (7.6, -11.4, 0.8, 0.2), (1.5, -19.4, 1.0, 0.3), (-2.5, -16.8, 0.7, 0.2)]

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

def beam(g, p0, p1, w, h, m="Metal"):
    """Square bar from Godot point p0 to p1 (w across, h tall)."""
    g = grp(g) if isinstance(g, str) else g
    a, b = G(*p0), G(*p1); d = b - a; L = d.length
    q = d.normalized().to_track_quat('Z', 'Y')
    M = Matrix.Translation((a + b) / 2) @ q.to_matrix().to_4x4() @ Matrix.Diagonal((w, h, L, 1.0))
    r = bmesh.ops.create_cube(g.bm, size=1.0, matrix=M)
    _tag(g, list({f for v in r["verts"] for f in v.link_faces}), m)

def tube(g, pts, r, m="Pipe", seg=10):
    """Round pipe along a polyline of Godot points (smooth joints from overlapping segments + ball joints)."""
    g = grp(g) if isinstance(g, str) else g
    for a, b in zip(pts[:-1], pts[1:]):
        A, B = G(*a), G(*b); d = B - A
        q = d.normalized().to_track_quat('Z', 'Y')
        M = Matrix.Translation((A + B) / 2) @ q.to_matrix().to_4x4()
        rr = bmesh.ops.create_cone(g.bm, cap_ends=False, cap_tris=False, segments=seg, radius1=r, radius2=r, depth=d.length, matrix=M)
        _tag(g, list({f for v in rr["verts"] for f in v.link_faces}), m)
    for p in pts[1:-1]:
        rr = bmesh.ops.create_uvsphere(g.bm, u_segments=seg, v_segments=6, radius=r * 1.0, matrix=Matrix.Translation(G(*p)))
        _tag(g, list({f for v in rr["verts"] for f in v.link_faces}), m)

def arc_pts(c, r, a0, a1, n, plane="xy"):
    """Points on a circular arc around Godot point c (plane xy: bends up/over in x-y)."""
    out = []
    for k in range(n + 1):
        a = a0 + (a1 - a0) * k / n
        if plane == "xy":
            out.append((c[0] + r * math.cos(a), c[1] + r * math.sin(a), c[2]))
        else:
            out.append((c[0], c[1] + r * math.sin(a), c[2] + r * math.cos(a)))
    return out


# ======================================================================
#  Ordis: extra shape helpers
# ======================================================================
def rock(g, x, y, z, sx, sy, sz, seed, m="Rubble", sub=1, jag=0.28, tilt=0.0):
    gg = grp(g) if isinstance(g, str) else g
    rnd = random.Random(seed)
    M = Matrix.Translation(G(x, y, z)) @ Matrix.Rotation(rnd.uniform(0, 6.28), 4, 'Z') @ \
        Matrix.Rotation(tilt, 4, 'X') @ Matrix.Diagonal((sx, sz, sy, 1.0))
    r = bmesh.ops.create_icosphere(gg.bm, subdivisions=sub, radius=1.0, matrix=M)
    c = G(x, y, z)
    for v in r["verts"]:
        v.co = c + (v.co - c) * rnd.uniform(1 - jag, 1 + jag * 0.5)
        if v.co.z < 0.0:
            v.co.z = 0.0
    _tag(gg, list({f for v in r["verts"] for f in v.link_faces}), m)

def mound(g, x, z, rx, rz, h, seed, m="Rubble", n=14):
    """A low rounded pile (dust / debris heap)."""
    gg = grp(g) if isinstance(g, str) else g
    rnd = random.Random(seed); bm = gg.bm
    rings = 4; ring_v = []
    for k in range(rings):
        t = k / rings
        ring = []
        for i in range(n):
            a = 2 * math.pi * i / n
            rr = (1 - t ** 2) ** 0.5 * rnd.uniform(0.85, 1.12)
            ring.append(bm.verts.new(G(x + rx * rr * math.cos(a), h * math.sin(t * math.pi / 2) * rnd.uniform(0.85, 1.1), z + rz * rr * math.sin(a))))
        ring_v.append(ring)
    top = bm.verts.new(G(x, h, z))
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

def lathe(g, x, y0, z, prof, seg=12, m="Gold"):
    """Surface of revolution around the vertical through (x, z). prof = [(radius, height), ...] bottom -> top,
    starting and ending at radius 0 so it is closed."""
    gg = grp(g) if isinstance(g, str) else g; bm = gg.bm
    rings = []
    for (r, y) in prof:
        if r < 1e-4:
            rings.append([bm.verts.new(G(x, y0 + y, z))])
        else:
            rings.append([bm.verts.new(G(x + r * math.cos(2 * math.pi * i / seg), y0 + y, z + r * math.sin(2 * math.pi * i / seg)))
                          for i in range(seg)])
    faces = []
    for A, B in zip(rings[:-1], rings[1:]):
        if len(A) == 1 and len(B) == 1:
            continue
        if len(A) == 1:
            faces += [bm.faces.new((A[0], B[(i + 1) % seg], B[i])) for i in range(seg)]
        elif len(B) == 1:
            faces += [bm.faces.new((A[i], A[(i + 1) % seg], B[0])) for i in range(seg)]
        else:
            faces += [bm.faces.new((A[i], A[(i + 1) % seg], B[(i + 1) % seg], B[i])) for i in range(seg)]
    bmesh.ops.recalc_face_normals(bm, faces=faces)
    _tag(gg, faces, m)
    return faces

def torus(g, center, R, r, rot=None, nR=24, nr=6, m="Gold"):
    gg = grp(g) if isinstance(g, str) else g; bm = gg.bm
    M = Matrix.Translation(G(*center)) @ (rot if rot is not None else Matrix.Identity(4))
    rings = []
    for i in range(nR):
        a = 2 * math.pi * i / nR
        rings.append([bm.verts.new(M @ Vector(((R + r * math.cos(2 * math.pi * j / nr)) * math.cos(a),
                                                (R + r * math.cos(2 * math.pi * j / nr)) * math.sin(a),
                                                r * math.sin(2 * math.pi * j / nr)))) for j in range(nr)])
    faces = []
    for i in range(nR):
        A, B = rings[i], rings[(i + 1) % nR]
        for j in range(nr):
            k = (j + 1) % nr
            faces.append(bm.faces.new((A[j], B[j], B[k], A[k])))
    bmesh.ops.recalc_face_normals(bm, faces=faces)
    _tag(gg, faces, m)

def sphere(g, center, r, m="Gold", seg=10, rings=6, squash=1.0):
    gg = grp(g) if isinstance(g, str) else g
    M = Matrix.Translation(G(*center)) @ Matrix.Diagonal((1.0, 1.0, squash, 1.0))
    res = bmesh.ops.create_uvsphere(gg.bm, u_segments=seg, v_segments=rings, radius=r, matrix=M)
    _tag(gg, list({f for v in res["verts"] for f in v.link_faces}), m)

def _card_uv(gg, faces, fid, h=0.5):
    """Mark faces as custom-UV (kept by Group.finish) with Blender v = id + h (shaders read the id)."""
    for f in faces:
        f[gg.custom] = 1
        for l in f.loops:
            l[gg.uv].uv = (0.5, fid + h)

def glow_lathe(x, y0, z, prof, fid, seg=12, mat="GlowWarm"):
    gg = grp("OM_Glow", "Cards")
    _card_uv(gg, lathe(gg, x, y0, z, prof, seg, mat), fid)

FLAMES = []        # (x, y, z, size): candle flames (crossed quads, OM_Flame)
def flame(x, y, z, s=0.075):
    i = len(FLAMES); FLAMES.append((x, y, z, s))
    for a in (0.0, math.pi / 2):
        dx, dz = math.cos(a) * s * 0.5, math.sin(a) * s * 0.5
        quad("OM_Flame", [(x - dx, y, z - dz), (x + dx, y, z + dz), (x + dx, y + s * 2.2, z + dz), (x - dx, y + s * 2.2, z - dz)],
             [(0, i + 0.001), (1, i + 0.001), (1, i + 0.999), (0, i + 0.999)], "FlameCard")

POINTS = []        # (x, y, z, watts, hex, radius) point lights for the bake

class Seg:
    """One straight wall. t runs along it from A to B, `off` is the distance in front of its inner face."""
    def __init__(self, A, B):
        self.A, self.B = A, B
        dx, dz = B[0] - A[0], B[1] - A[1]
        self.L = math.hypot(dx, dz); self.d = (dx / self.L, dz / self.L)
        n1 = (self.d[1], -self.d[0])
        mx, mz = (A[0] + B[0]) / 2, (A[1] + B[1]) / 2
        self.n = n1 if n1[0] * (0 - mx) + n1[1] * (CENTER_Z - mz) > 0 else (-n1[0], -n1[1])
        self.rot = math.degrees(math.atan2(-self.d[1], self.d[0]))

    def P(self, t, y, off=0.0):
        return (self.A[0] + self.d[0] * t + self.n[0] * off, y, self.A[1] + self.d[1] * t + self.n[1] * off)

    def box(self, g, t0, t1, y0, y1, off0, off1, m, bevel=0.0):
        obox(g, self.P((t0 + t1) / 2, (y0 + y1) / 2, (off0 + off1) / 2), (t1 - t0, y1 - y0, off1 - off0), self.rot, m, bevel)

    def quad(self, g, t0, t1, y0, y1, off, uvs, m):
        return quad(g, [self.P(t0, y0, off), self.P(t1, y0, off), self.P(t1, y1, off), self.P(t0, y1, off)], uvs, m)

def mirror_x(p):
    return (-p[0], p[1])

# ======================================================================
#  materials
# ======================================================================
def soot(b, col, strength=0.9):
    """Ruined: blacken surfaces around (and above) every fire, broken up with noise."""
    if not RUIN:
        return col
    acc = None
    for (x, y, z, s) in SOOT_FIRES:
        c = G(x, y + 1.3 * s, z)
        sub = b.n("ShaderNodeVectorMath", operation='SUBTRACT'); b.link(b.pos, sub.inputs[0]); sub.inputs[1].default_value = (c.x, c.y, c.z)
        mul = b.n("ShaderNodeVectorMath", operation='MULTIPLY'); b.link(sub.outputs[0], mul.inputs[0]); mul.inputs[1].default_value = (1.0, 1.0, 0.42)
        ln = b.n("ShaderNodeVectorMath", operation='LENGTH'); b.link(mul.outputs[0], ln.inputs[0])
        mr = b.n("ShaderNodeMapRange")
        mr.inputs["From Min"].default_value = 0.5 * s; mr.inputs["From Max"].default_value = 2.4 * s + 1.4
        mr.inputs["To Min"].default_value = 1.0; mr.inputs["To Max"].default_value = 0.0
        b.link(ln.outputs["Value"], mr.inputs[0])
        acc = mr.outputs[0] if acc is None else b.math('MAXIMUM', acc, mr.outputs[0])
    n = b.noise(b.pos, 1.3, 4, 0.6)
    acc = b.math('MULTIPLY', acc, b.math('ADD', b.math('MULTIPLY', n.outputs["Fac"], 0.8), 0.35))
    acc = b.math('MINIMUM', acc, strength)
    return b.mixc(col, "#140f0c", acc)

def cracks(b, col, scale=0.32, amount=0.52):
    """Ruined: patches of dark jagged cracks."""
    if not RUIN:
        return col
    w = b.noise(b.pos, 0.9, 3, 0.5)
    add = b.n("ShaderNodeVectorMath", operation='ADD'); b.link(b.pos, add.inputs[0]); b.link(w.outputs["Color"], add.inputs[1])
    v = b.n("ShaderNodeTexVoronoi"); v.feature = 'DISTANCE_TO_EDGE'; v.inputs["Scale"].default_value = scale
    b.link(add.outputs[0], v.inputs["Vector"])
    line = b.math('LESS_THAN', v.outputs["Distance"], 0.016)
    patch = b.noise(b.pos, 0.16, 2, 0.5)
    return b.mixc(col, "#1a120c", b.math('MULTIPLY', line, b.math('GREATER_THAN', patch.outputs["Fac"], amount)))

def mat(name, dark, light, scale=3.0, rough=0.6, ruin=True, crack=False, emit=0.0):
    b = NB(name)
    n = b.noise(b.pos, scale, 4, 0.55)
    c = b.ramp(n.outputs["Fac"], [(0.3, dark), (0.7, light)])
    if ruin:
        if crack:
            c = cracks(b, c)
        c = soot(b, c)
    b.link(c, b.bsdf.inputs["Base Color"]); b.bsdf.inputs["Roughness"].default_value = rough
    if emit > 0:
        b.link(c, b.bsdf.inputs["Emission Color"]); b.bsdf.inputs["Emission Strength"].default_value = emit
    return b

def marble(name, dark, light, vein, scale=0.9, crack=True):
    b = NB(name)
    n = b.noise(b.pos, scale, 5, 0.6)
    c = b.ramp(n.outputs["Fac"], [(0.25, dark), (0.75, light)])
    vn = b.noise(b.pos, 0.45, 6, 0.65); vn.inputs["Distortion"].default_value = 3.0
    d = b.math('ABSOLUTE', b.math('SUBTRACT', vn.outputs["Fac"], 0.5))
    mr = b.n("ShaderNodeMapRange"); mr.inputs["From Min"].default_value = 0.0; mr.inputs["From Max"].default_value = 0.022
    mr.inputs["To Min"].default_value = 0.7; mr.inputs["To Max"].default_value = 0.0; b.link(d, mr.inputs[0])
    c = b.mixc(c, vein, mr.outputs[0])
    if crack:
        c = cracks(b, c)
    c = soot(b, c)
    b.link(c, b.bsdf.inputs["Base Color"]); b.bsdf.inputs["Roughness"].default_value = 0.25
    return b

def crest_mat(name, base_dark, base_light, uscale, vscale, ucen, vcen, border=True, wood=False):
    """Purple (or dark wood) field with the gold crest image (tex/crest_mask.png) and a gold border, from the Tex UV."""
    b = NB(name)
    n = b.noise(b.pos, 6.0 if not wood else 2.0, 4, 0.6)
    c = b.ramp(n.outputs["Fac"], [(0.3, base_dark), (0.7, base_light)])
    sep = b.n("ShaderNodeSeparateXYZ"); b.link(b.uv, sep.inputs[0])
    u, v = sep.outputs[0], sep.outputs[1]
    mp = b.n("ShaderNodeMapping"); mp.vector_type = 'POINT'
    mp.inputs["Scale"].default_value = (1.0 / uscale, 1.0 / vscale, 1.0)
    mp.inputs["Location"].default_value = (0.5 - ucen / uscale, 0.5 - vcen / vscale, 0.0)
    b.link(b.uv, mp.inputs["Vector"])
    im = b.image("crest_mask.png", mp.outputs[0], extension='CLIP', non_color=True)
    gold = b.ramp(im.outputs["Color"], [(0.3, "#6a4a1a"), (0.9, "#e8c060")])
    k = b.math('MINIMUM', b.math('MULTIPLY', im.outputs["Color"], 3.0), 1.0)
    c = b.mixc(c, gold, k)
    if border:
        e = b.math('MAXIMUM', b.math('LESS_THAN', u, 0.06), b.math('GREATER_THAN', u, 0.94))
        e = b.math('MAXIMUM', e, b.math('GREATER_THAN', v, 0.965))
        e = b.math('MAXIMUM', e, b.math('LESS_THAN', v, 0.05))
        inner = b.math('MULTIPLY', b.math('GREATER_THAN', u, 0.085), b.math('LESS_THAN', u, 0.915))
        line = b.math('MULTIPLY', b.math('LESS_THAN', u, 0.1), b.math('GREATER_THAN', u, 0.085))
        line = b.math('MAXIMUM', line, b.math('MULTIPLY', b.math('GREATER_THAN', u, 0.9), b.math('LESS_THAN', u, 0.915)))
        c = b.mixc(c, "#d8ac50", b.math('MAXIMUM', e, b.math('MULTIPLY', line, inner)))
    c = soot(b, c, 0.75)
    b.link(c, b.bsdf.inputs["Base Color"]); b.bsdf.inputs["Roughness"].default_value = 0.7
    return b

def ceiling_mat(name):
    b = NB(name)
    mp = b.n("ShaderNodeMapping"); mp.vector_type = 'POINT'; mp.inputs["Rotation"].default_value = (0.0, 0.0, math.radians(45))
    b.link(b.pos, mp.inputs["Vector"])
    br = b.n("ShaderNodeTexBrick"); br.offset = 0.0
    for k, v in (("Scale", 1.0), ("Mortar Size", 0.03), ("Brick Width", 1.6), ("Row Height", 1.6), ("Mortar Smooth", 0.2)):
        br.inputs[k].default_value = v
    n = b.noise(b.pos, 2.0, 4, 0.55)
    b.link(b.ramp(n.outputs["Fac"], [(0.3, "#2e4844"), (0.7, "#46645c")]), br.inputs["Color1"])
    b.link(b.ramp(n.outputs["Fac"], [(0.3, "#2a423e"), (0.7, "#3e5a54")]), br.inputs["Color2"])
    br.inputs["Mortar"].default_value = (*srgb("#a88440"), 1)
    b.link(mp.outputs[0], br.inputs["Vector"])
    c = cracks(b, br.outputs["Color"], 0.25, 0.45)
    c = soot(b, c)
    b.link(c, b.bsdf.inputs["Base Color"]); b.bsdf.inputs["Roughness"].default_value = 0.7
    return b

def emit_solid(name, color, strength):
    b = NB(name)
    em = b.n("ShaderNodeEmission"); em.inputs["Color"].default_value = (*srgb(color), 1); em.inputs["Strength"].default_value = strength
    b.link(em.outputs[0], b.out.inputs[0])
    return b

BOOKS = ["Book0", "Book1", "Book2", "Book3", "Book4", "Book5"]

def build_materials():
    mat("Plaster", "#b49a74", "#cbb590", 2.0, 0.7, crack=True)
    mat("PlasterLight", "#c8b28c", "#dccaa6", 2.0, 0.7, crack=True)
    marble("Marble", "#c4b8a2", "#e2d8c4", "#8a7c68")
    marble("MarbleDark", "#4a3c34", "#6a5648", "#2a201a")
    mat("Gold", "#8a6626", "#d8ac54", 8.0, 0.3, emit=0.12)
    mat("GoldDark", "#5a4018", "#8a6a2c", 8.0, 0.35, emit=0.05)
    mat("WoodDark", "#241410", "#3e2418", 4.0, 0.5, crack=True)
    mat("Wood", "#3e2414", "#5e3a22", 4.0, 0.5, crack=True)
    mat("WoodPanel", "#30200f", "#4a3018", 3.0, 0.5, crack=True)
    mat("Frame", "#d0c4aa", "#e8dec8", 3.0, 0.5, crack=True)
    mat("Purple", "#2a1636", "#4a2a5a", 6.0, 0.8)
    mat("PurpleBack", "#22122c", "#3a2246", 6.0, 0.85)
    mat("Carpet", "#5a1014", "#7e1e22", 9.0, 0.9)
    mat("Rug", "#34203e", "#4a2e56", 7.0, 0.9)
    mat("Paper", "#d8cba8", "#eee4c8", 6.0, 0.8)
    mat("Candle", "#e8e2d0", "#f6f2e6", 6.0, 0.6, ruin=False)
    mat("Leaf", "#26401e", "#40602a", 6.0, 0.7, ruin=False)
    mat("FlowerW", "#e4e0d2", "#fffcf0", 8.0, 0.6, ruin=False)
    mat("FlowerY", "#d8b440", "#f4d878", 8.0, 0.6, ruin=False)
    mat("Globe", "#2a5a7a", "#7aa08a", 3.0, 0.5, ruin=False)
    mat("Crystal", "#c8d8e4", "#f0f6fa", 9.0, 0.2, ruin=False, emit=0.35)
    mat("Rubble", "#7a6a58", "#b4a48c", 3.0, 0.8, ruin=False)
    mat("RubbleDark", "#3a302a", "#5e5046", 3.0, 0.8, ruin=False)
    mat("BookBurnt", "#140e0c", "#2a1c16", 5.0, 0.9, ruin=False)
    for k, (a, c2) in enumerate((("#5a1416", "#7a2022"), ("#183a26", "#285a3a"), ("#1a2a4a", "#2a426a"),
                                 ("#4a3018", "#6a4826"), ("#3a1a3e", "#5a2e5e"), ("#7a6a4a", "#9a8a62"))):
        mat(BOOKS[k], a, c2, 20.0, 0.6, ruin=False)
    crest_mat("BannerCrest", "#2a1638", "#4a2a5c", 0.8, 0.2, 0.5, 0.62)
    crest_mat("CrestPanel", "#2a1638", "#44285a", 0.78, 0.42, 0.5, 0.55)
    crest_mat("CrestDesk", "#1e100a", "#30180e", 1.0, 1.0, 0.5, 0.5, border=False, wood=True)
    ceiling_mat("Ceiling")
    mat("CeilingBeam", "#b8a07a", "#ccb690", 2.0, 0.7, crack=True)
    b = NB("FloorMarble"); b.bsdf.inputs["Base Color"].default_value = (*srgb("#b4a690"), 1); b.bsdf.inputs["Roughness"].default_value = 0.4
    emit_solid("WindowCard", V["window_color"], V["window_emit"])
    emit_solid("GlowWarm", "#ffc878", 4.0)
    emit_solid("GlowCove", "#ffb860", 3.0)
    emit_solid("GlowSconce", "#ffd8a0", 4.5)
    for nm in ("FlameCard", "FireCard", "SmokeCard"):
        emit_solid(nm, "#ff8a3a", 0.0)
    b = NB("Stand_P1"); b.bsdf.inputs["Base Color"].default_value = (*srgb("#2d6cdf"), 1)
    b = NB("Stand_P2"); b.bsdf.inputs["Base Color"].default_value = (*srgb("#e0463a"), 1)

# ======================================================================
#  the hall
# ======================================================================
WINDOWS = []       # window card ids
WIN_LIGHTS = []    # (Godot centre, Godot aim, w, h)

def window(s, tc, w):
    g = "OM_Walls"
    wid = len(WINDOWS); WINDOWS.append((s.P(tc, 0, 0), w))
    s.quad("OM_Window", tc - w / 2, tc + w / 2, SILL, WIN_TOP, -WALL_T + 0.1,
           [(0, wid + 0.001), (1, wid + 0.001), (1, wid + 0.999), (0, wid + 0.999)], "WindowCard")
    hw = w / 2
    # casing, sill, cap and the gold crest ornament above
    s.box(g, tc - hw - 0.22, tc - hw, SILL - 0.1, WIN_TOP + 0.1, 0.0, 0.12, "Frame")
    s.box(g, tc + hw, tc + hw + 0.22, SILL - 0.1, WIN_TOP + 0.1, 0.0, 0.12, "Frame")
    s.box(g, tc - hw - 0.22, tc + hw + 0.22, WIN_TOP, WIN_TOP + 0.24, 0.0, 0.12, "Frame")
    s.box(g, tc - hw - 0.3, tc + hw + 0.3, SILL - 0.14, SILL + 0.02, -0.2, 0.3, "Marble")
    s.box(g, tc - hw - 0.28, tc + hw + 0.28, WIN_TOP + 0.24, WIN_TOP + 0.32, 0.0, 0.17, "Gold")
    s.box(g, tc - hw - 0.4, tc + hw + 0.4, WIN_TOP + 0.32, WIN_TOP + 0.52, 0.0, 0.3, "PlasterLight")
    s.box(g, tc - 0.22, tc + 0.22, WIN_TOP + 0.52, WIN_TOP + 0.9, 0.08, 0.2, "Gold")
    # the sash inside the reveal: a frame + 2 mullions + 4 transoms (5 rows of panes)
    fo0, fo1 = -0.34, -0.24
    s.box(g, tc - hw, tc - hw + 0.08, SILL, WIN_TOP, fo0, fo1, "Frame")
    s.box(g, tc + hw - 0.08, tc + hw, SILL, WIN_TOP, fo0, fo1, "Frame")
    s.box(g, tc - hw, tc + hw, SILL, SILL + 0.1, fo0, fo1, "Frame")
    s.box(g, tc - hw, tc + hw, WIN_TOP - 0.08, WIN_TOP, fo0, fo1, "Frame")
    for k in (1, 2):
        x = tc - hw + w * k / 3
        s.box(g, x - 0.035, x + 0.035, SILL, WIN_TOP, fo0, fo1, "Frame")
    for k in (1, 2, 3, 4):
        y = SILL + (WIN_TOP - SILL) * (k / 5) + (0.25 if k == 4 else 0.0)
        s.box(g, tc - hw, tc + hw, y - 0.035, y + 0.035, fo0, fo1, "Frame")
    WIN_LIGHTS.append((s.P(tc, (SILL + WIN_TOP) / 2, -0.05), s.P(tc, 1.8, 6.0), w, WIN_TOP - SILL))

def pilaster(s, t, w=0.7):
    g = "OM_Walls"
    s.box(g, t - w / 2 - 0.06, t + w / 2 + 0.06, 0.0, 1.3, 0.0, 0.24, "MarbleDark", 0.02)
    s.box(g, t - w / 2, t + w / 2, 1.3, 9.3, 0.0, 0.16, "Marble")
    s.box(g, t - w / 2 + 0.14, t + w / 2 - 0.14, 1.6, 9.0, 0.16, 0.19, "PlasterLight")     # sunk panel look
    s.box(g, t - w / 2 - 0.08, t + w / 2 + 0.08, 9.3, 9.72, 0.0, 0.3, "Gold", 0.02)

def sconce(s, t, y, off=0.0):
    """Gold wall lamp: back plate, arm, cup and a glowing glass (OM_Glow id 2)."""
    g = "OM_Furniture"
    s.box(g, t - 0.16, t + 0.16, y - 0.55, y + 0.3, off, off + 0.06, "Gold")
    beam(g, s.P(t, y - 0.3, off + 0.05), s.P(t, y + 0.02, off + 0.42), 0.05, 0.05, "Gold")
    x, _, z = s.P(t, 0, off + 0.45)
    lathe(g, x, y, z, [(0, 0), (0.05, 0.0), (0.12, 0.08), (0.12, 0.12), (0, 0.12)], 10, "Gold")
    glow_lathe(x, y + 0.12, z, [(0, 0), (0.08, 0.02), (0.12, 0.17), (0.1, 0.34), (0, 0.38)], 2, 10, "GlowSconce")
    lathe(g, x, y + 0.48, z, [(0, 0), (0.07, 0.0), (0.04, 0.12), (0, 0.16)], 8, "Gold")
    POINTS.append((x, y + 0.3, z, V["sconce_w"], "#ffc884", 0.15))

def build_wall(s, wins, cornice=True):
    g = "OM_Walls"
    edges = [0.0] + [e for (tc, w) in wins for e in (tc - w / 2, tc + w / 2)] + [s.L]
    for k in range(0, len(edges), 2):
        if edges[k + 1] - edges[k] > 0.01:
            s.box(g, edges[k], edges[k + 1], -0.2, WALL_H + 0.2, -WALL_T, 0.0, "Plaster")
    for (tc, w) in wins:
        s.box(g, tc - w / 2, tc + w / 2, -0.2, SILL, -WALL_T, 0.0, "Plaster")
        s.box(g, tc - w / 2, tc + w / 2, WIN_TOP, WALL_H + 0.2, -WALL_T, 0.0, "Plaster")
        window(s, tc, w)
    # wainscot: dark wood band, raised panels, chair rail and skirting
    s.box(g, 0.0, s.L, 0.0, 1.15, 0.0, 0.06, "WoodPanel")
    n = max(1, int(s.L / 1.25))
    for k in range(n):
        t0 = 0.12 + k * (s.L - 0.24) / n
        s.box(g, t0 + 0.08, t0 + (s.L - 0.24) / n - 0.08, 0.3, 0.92, 0.06, 0.09, "WoodDark")
    s.box(g, 0.0, s.L, 1.12, 1.24, 0.0, 0.11, "Gold")
    s.box(g, 0.0, s.L, 0.0, 0.16, 0.0, 0.1, "WoodDark")
    if not cornice:
        return
    # frieze and the stepped cornice with its glowing cove strip (OM_Glow id 1)
    s.box(g, 0.0, s.L, 7.8, 7.92, 0.0, 0.08, "Gold")
    n = max(1, int(s.L / 1.9))
    for k in range(n):
        a = k * s.L / n + 0.18; b = (k + 1) * s.L / n - 0.18
        if any(a < tc + w / 2 + 0.45 and b > tc - w / 2 - 0.45 for (tc, w) in wins):
            continue
        s.box(g, a, b, 8.12, 9.42, 0.0, 0.035, "PlasterLight")
        for (y0, y1) in ((8.12, 8.18), (9.36, 9.42)):
            s.box(g, a, b, y0, y1, 0.035, 0.055, "Gold")
        for t in (a, b - 0.06):
            s.box(g, t, t + 0.06, 8.12, 9.42, 0.035, 0.055, "Gold")
    s.box(g, 0.0, s.L, 9.62, 9.72, 0.0, 0.1, "Gold")
    s.box(g, 0.0, s.L, 9.72, 9.98, 0.0, 0.26, "Plaster")
    s.box(g, 0.0, s.L, 9.98, 10.2, 0.0, 0.42, "Gold")
    s.box(g, 0.0, s.L, 10.2, 10.9, 0.0, 0.55, "PlasterLight")
    s.box(g, 0.0, s.L, 10.9, 11.14, 0.0, 0.78, "Gold")
    s.box(g, 0.0, s.L, 11.14, WALL_H, 0.0, 0.62, "Plaster")
    for k in range(int(s.L / 0.5)):                                           # dentils under the gold band
        t = 0.25 + k * 0.5
        s.box(g, t - 0.1, t + 0.1, 9.82, 9.98, 0.26, 0.36, "PlasterLight")
    gg = grp("OM_Glow", "Cards")
    f = s.quad(gg, 0.2, s.L - 0.2, 10.32, 10.5, 0.57, [(0, 1.3), (1, 1.3), (1, 1.7), (0, 1.7)], "GlowCove")
    for k in range(max(1, int(s.L / 4.5))):
        x, y, z = s.P((k + 0.5) * s.L / max(1, int(s.L / 4.5)), 10.2, 0.9)
        POINTS.append((x, y, z, V["cove_w"], "#ffb868", 0.4))

def corner_pillar(p, a_seg, b_seg, w=1.3):
    """A big square marble pillar standing in the corner where two walls meet, facing the room."""
    g = "OM_Walls"
    nx, nz = a_seg.n[0] + b_seg.n[0], a_seg.n[1] + b_seg.n[1]; L = math.hypot(nx, nz); nx, nz = nx / L, nz / L
    cx, cz = p[0] + nx * 0.55, p[1] + nz * 0.55
    rot = math.degrees(math.atan2(nx, nz))                                    # one face square to the room
    for (y0, y1, ww, m) in ((0.0, 0.25, w + 0.4, "MarbleDark"), (0.25, 1.3, w + 0.22, "MarbleDark"), (1.3, 1.42, w + 0.26, "Gold"),
                            (1.42, 9.3, w, "Marble"), (5.0, 5.12, w + 0.06, "Gold"), (9.3, 9.5, w + 0.16, "Gold"),
                            (9.5, 9.95, w + 0.36, "Gold"), (9.95, WALL_H, w + 0.5, "Plaster")):
        obox(g, (cx, (y0 + y1) / 2, cz), (ww, y1 - y0, ww), rot, m, 0.02 if ww < 2 else 0.0)
    obox(g, (cx + nx * (w / 2), 5.4, cz + nz * (w / 2)), (w - 0.36, 7.0, 0.04), rot, "PlasterLight")
    return (cx, cz, nx, nz, rot)

def build_room():
    """Walls, corner pillars, windows, cornices; returns the wall segments by name."""
    S = {}
    for side, sx in (("L", -1), ("R", 1)):
        p1, p2, p3 = (sx * P1[0], P1[1]), (sx * P2[0], P2[1]), (sx * P3[0], P3[1])
        S["side" + side] = Seg((sx * P1[0], 9.0), p1)
        S["wing" + side] = Seg(p1, p2)
        S["bay" + side] = Seg(p2, p3)
    S["back"] = Seg((-P3[0], P3[1]), (P3[0], P3[1]))
    for side in "LR":
        build_wall(S["side" + side], [], cornice=True)
        build_wall(S["wing" + side], [(5.6, 2.1), (8.9, 2.1), (12.2, 2.1)])
        build_wall(S["bay" + side], [(S["bay" + side].L / 2, 2.4)])
    build_wall(S["back"], [])
    PIL = {}
    for side, sx in (("L", -1), ("R", 1)):
        PIL["P1" + side] = corner_pillar((sx * P1[0], P1[1]), S["side" + side], S["wing" + side])
        PIL["P2" + side] = corner_pillar((sx * P2[0], P2[1]), S["wing" + side], S["bay" + side])
        PIL["P3" + side] = corner_pillar((sx * P3[0], P3[1]), S["bay" + side], S["back"])
        w = S["wing" + side]
        for t in (7.25, 10.55):
            pilaster(w, t, 0.56)
            sconce(w, t, 5.6, 0.16)
    return S, PIL

def build_ceiling():
    g = "OM_Ceiling"
    box(g, 0, WALL_H, WALL_H + 0.4, -9.5, 2 * P1[0] + 2, 40.0, "Ceiling")
    for k in range(9):
        z = -27.0 + k * 4.0
        box(g, 0, WALL_H - 0.45, WALL_H, z, 2 * P1[0], 0.5, "CeilingBeam")
        box(g, 0, WALL_H - 0.5, WALL_H - 0.45, z, 2 * P1[0], 0.58, "Gold")
    for k in range(13):
        x = -24.0 + k * 4.0
        box(g, x, WALL_H - 0.45, WALL_H, -9.5, 0.5, 38.0, "CeilingBeam")
        box(g, x, WALL_H - 0.5, WALL_H - 0.45, -9.5, 0.58, 38.0, "Gold")

# ======================================================================
#  furniture
# ======================================================================
def bookshelf(s, t0, t1, h=6.4, depth=0.7, seed=0):
    g = "OM_Furniture"; rnd = random.Random(seed)
    s.box(g, t0, t1, 0.0, h, 0.0, 0.05, "Wood")                                # back
    s.box(g, t0, t0 + 0.1, 0.0, h, 0.0, depth, "WoodDark", 0.01)               # sides
    s.box(g, t1 - 0.1, t1, 0.0, h, 0.0, depth, "WoodDark", 0.01)
    s.box(g, t0 - 0.06, t1 + 0.06, 0.0, 0.36, 0.0, depth + 0.05, "WoodDark", 0.02)
    s.box(g, t0 - 0.1, t1 + 0.1, h, h + 0.26, 0.0, depth + 0.12, "WoodDark", 0.02)
    s.box(g, t0 - 0.12, t1 + 0.12, h + 0.26, h + 0.34, 0.0, depth + 0.15, "Gold")
    tm = (t0 + t1) / 2
    s.box(g, tm - 0.55, tm + 0.55, h + 0.34, h + 0.74, 0.08, 0.34, "WoodDark", 0.02)
    s.box(g, tm - 0.18, tm + 0.18, h + 0.44, h + 0.7, 0.34, 0.37, "Gold")
    # lower cupboard with two doors
    s.box(g, t0 + 0.1, t1 - 0.1, 0.36, 1.6, depth - 0.05, depth, "WoodDark")
    for k in (0, 1):
        a = t0 + 0.16 + k * (t1 - t0 - 0.32) / 2; b = a + (t1 - t0 - 0.32) / 2 - 0.06
        s.box(g, a, b, 0.46, 1.5, depth, depth + 0.03, "Wood")
        s.box(g, (b if k == 0 else a) - 0.03, (b if k == 0 else a) + 0.03, 0.9, 1.05, depth + 0.03, depth + 0.07, "Gold")
    s.box(g, t0 + 0.1, t1 - 0.1, 1.6, 1.68, 0.05, depth + 0.02, "WoodDark")
    rows = 5; y = 1.68; gap = (h - 0.1 - y) / rows
    for r in range(rows):
        s.box(g, t0 + 0.1, t1 - 0.1, y + gap - 0.05, y + gap, 0.05, depth, "WoodDark")
        s.box(g, t0 + 0.1, t1 - 0.1, y + gap - 0.05, y + gap - 0.01, depth, depth + 0.02, "Gold")
        t = t0 + 0.13
        while t < t1 - 0.2:
            if rnd.random() < 0.09:                                             # a gold ornament instead of books
                x, _, z = s.P(t + 0.14, 0, depth * 0.55)
                if rnd.random() < 0.5:
                    lathe(g, x, y, z, [(0, 0), (0.08, 0.0), (0.05, 0.05), (0.11, 0.2), (0.06, 0.34), (0.08, 0.4), (0, 0.42)], 8, "Gold")
                else:
                    sphere(g, (x, y + 0.14, z), 0.12, "Gold", 8, 5)
                t += 0.32; continue
            bw = rnd.uniform(0.06, 0.13); bh = gap * rnd.uniform(0.62, 0.9); bd = rnd.uniform(0.36, 0.54)
            if t + bw > t1 - 0.12:
                break
            if RUIN and rnd.random() < 0.3:
                t += bw; continue
            m = "BookBurnt" if RUIN and rnd.random() < 0.18 else rnd.choice(BOOKS)
            s.box(g, t, t + bw - 0.005, y, y + bh, 0.08, 0.08 + bd, m)
            t += bw
        y += gap

def cabinet(s, tc, w=2.2, seed=0, item="books"):
    g = "OM_Furniture"; rnd = random.Random(seed)
    s.box(g, tc - w / 2, tc + w / 2, 0.0, 0.95, 0.04, 0.64, "Wood", 0.02)
    s.box(g, tc - w / 2 - 0.05, tc + w / 2 + 0.05, 0.95, 1.02, 0.0, 0.7, "WoodDark", 0.01)
    s.box(g, tc - w / 2 - 0.02, tc + w / 2 + 0.02, 0.0, 0.12, 0.02, 0.66, "WoodDark")
    for k in (0, 1):
        a = tc - w / 2 + 0.1 + k * (w - 0.2) / 2; b = a + (w - 0.2) / 2 - 0.06
        s.box(g, a, b, 0.2, 0.85, 0.64, 0.67, "WoodDark")
        s.box(g, a + 0.08, b - 0.08, 0.3, 0.75, 0.67, 0.68, "Gold")
    for k in range(rnd.randint(2, 4)):                                         # a stack of books
        s.box(g, tc - 0.7 + rnd.uniform(-0.05, 0.05), tc - 0.1, 1.02 + k * 0.08, 1.09 + k * 0.08, 0.2, 0.5, rnd.choice(BOOKS))
    x, _, z = s.P(tc + 0.45, 0, 0.35)
    if item == "globe":
        globe(x, 1.02, z, 0.26)
    else:
        armillary(x, 1.02, z, 0.24)

def globe(x, y0, z, r):
    g = "OM_Furniture"
    lathe(g, x, y0, z, [(0, 0), (0.16, 0.0), (0.12, 0.05), (0.04, 0.12), (0.03, 0.2), (0, 0.22)], 10, "Gold")
    sphere(g, (x, y0 + 0.22 + r, z), r, "Globe", 14, 8)
    torus(g, (x, y0 + 0.22 + r, z), r + 0.03, 0.012, Matrix.Rotation(math.radians(90), 4, 'X') @ Matrix.Rotation(math.radians(23), 4, 'Y'), 20, 4, "Gold")

def armillary(x, y0, z, r, fallen=False):
    g = "OM_Furniture"
    if not fallen:
        lathe(g, x, y0, z, [(0, 0), (0.15, 0.0), (0.1, 0.06), (0.03, 0.12), (0.025, 0.24), (0, 0.25)], 10, "Gold")
        c = (x, y0 + 0.25 + r, z)
    else:
        c = (x, r * 0.8, z)
    tilt = math.radians(60 if fallen else 0)
    for rot in (Matrix.Rotation(math.radians(90), 4, 'X'), Matrix.Rotation(math.radians(90), 4, 'X') @ Matrix.Rotation(math.radians(90), 4, 'Y'),
                Matrix.Rotation(math.radians(23), 4, 'X'), Matrix.Rotation(math.radians(-30), 4, 'Y') @ Matrix.Rotation(math.radians(70), 4, 'X')):
        torus(g, c, r, 0.013, Matrix.Rotation(tilt, 4, 'Y') @ rot, 20, 4, "Gold")
    sphere(g, c, r * 0.22, "Gold", 8, 5)

def floor_lamp(x, z):
    g = "OM_Furniture"
    lathe(g, x, 0.0, z, [(0, 0), (0.24, 0.0), (0.24, 0.05), (0.1, 0.12), (0.045, 0.3), (0.045, 1.6), (0.08, 1.66), (0.04, 1.72), (0, 1.74)], 10, "Gold")
    glow_lathe(x, 1.58, z, [(0, 0), (0.32, 0.0), (0.19, 0.4), (0, 0.42)], 0, 12)
    POINTS.append((x, 1.75, z, V["lamp_w"], "#ffc27a", 0.25))

def vase(x, z, seed):
    g = "OM_Furniture"; rnd = random.Random(seed)
    lathe(g, x, 0.0, z, [(0, 0), (0.34, 0.0), (0.34, 0.12), (0.24, 0.2), (0.19, 0.28), (0.19, 0.98), (0.27, 1.06), (0.32, 1.14), (0.32, 1.2), (0, 1.2)], 12, "Marble")
    cyl(g, x, 0.96, z, 0.22, 0.22, 0.06, "Gold", 12)
    lathe(g, x, 1.2, z, [(0, 0), (0.15, 0.0), (0.1, 0.07), (0.17, 0.25), (0.27, 0.48), (0.24, 0.66), (0.15, 0.76), (0.22, 0.84), (0, 0.84)], 12, "Gold")
    for k in range(10):                                                         # leaves
        a = rnd.uniform(0, 6.28); r = rnd.uniform(0.2, 0.42)
        rock(g, x + r * math.cos(a), 2.05 + rnd.uniform(-0.05, 0.25), z + r * math.sin(a), 0.16, 0.05, 0.08, seed * 31 + k, "Leaf", 1, 0.15)
    for k in range(18):                                                         # white and yellow blooms
        a = rnd.uniform(0, 6.28); r = rnd.uniform(0.0, 0.38); up = (1 - r / 0.4) ** 0.5
        m = "FlowerW" if k % 3 else "FlowerY"
        sphere(g, (x + r * math.cos(a), 2.12 + 0.36 * up + rnd.uniform(-0.04, 0.04), z + r * math.sin(a)), rnd.uniform(0.07, 0.11), m, 7, 4, 0.8)

def desk_and_chair(z=-23.9):
    g = "OM_Furniture"; W, D = 5.6, 1.7
    obox(g, (0, 0.56, z), (W, 0.8, D), 0, "WoodDark", 0.03)
    obox(g, (0, 0.08, z), (W + 0.12, 0.16, D + 0.12), 0, "WoodDark", 0.02)
    obox(g, (0, 0.955, z), (W + 0.24, 0.03, D + 0.2), 0, "Gold")
    obox(g, (0, 1.0, z), (W + 0.2, 0.07, D + 0.16), 0, "Wood", 0.02)
    for k in (-1.9, 0.0, 1.9):
        obox(g, (k, 0.56, z + D / 2 + 0.02), (1.55, 0.6, 0.04), 0, "Wood")
        for dy in (0.27, 0.85):
            obox(g, (k, dy, z + D / 2 + 0.045), (1.55, 0.03, 0.02), 0, "Gold")
    for sx in (-1, 1):
        obox(g, (sx * (W / 2 - 0.04), 0.56, z + D / 2 - 0.02), (0.2, 0.86, 0.14), 0, "Gold", 0.02)
        obox(g, (sx * (W / 2 - 0.04), 0.56, z - D / 2 + 0.02), (0.2, 0.86, 0.14), 0, "GoldDark", 0.02)
    quad(g, [(-0.42, 0.25, z + D / 2 + 0.047), (0.42, 0.25, z + D / 2 + 0.047), (0.42, 0.87, z + D / 2 + 0.047), (-0.42, 0.87, z + D / 2 + 0.047)],
         [(0, 0), (1, 0), (1, 1), (0, 1)], "CrestDesk")
    # on the desk: lamps, books, papers, an inkwell and a small globe
    for sx in (-1, 1):
        x = sx * 2.15
        lathe(g, x, 1.035, z - 0.25, [(0, 0), (0.16, 0.0), (0.12, 0.05), (0.05, 0.12), (0.09, 0.3), (0.04, 0.45), (0.03, 0.5), (0, 0.52)], 10, "Gold")
        glow_lathe(x, 1.5, z - 0.25, [(0, 0), (0.28, 0.0), (0.16, 0.32), (0, 0.34)], 0, 12)
        POINTS.append((x, 1.65, z - 0.1, V["lamp_w"], "#ffc27a", 0.2))
    for k in range(3):
        obox(g, (-1.3, 1.07 + k * 0.07, z - 0.1), (0.55 - k * 0.05, 0.065, 0.4), 6 * k, BOOKS[k])
    obox(g, (0.55, 1.04, z + 0.25), (0.55, 0.01, 0.4), 8, "Paper")
    obox(g, (0.95, 1.045, z + 0.15), (0.4, 0.01, 0.32), -14, "Paper")
    cyl(g, 1.35, 1.035, z - 0.1, 0.06, 0.05, 0.1, "Gold", 8)
    globe(-0.4, 1.035, z - 0.4, 0.16)
    # the chair: tall purple back in a gold frame
    cz = z - 1.35
    obox(g, (0, 0.55, cz), (1.1, 0.18, 1.0), 0, "Purple", 0.05)
    obox(g, (0, 0.42, cz), (1.18, 0.1, 1.06), 0, "Gold")
    for sx in (-1, 1):
        for sz in (-1, 1):
            obox(g, (sx * 0.5, 0.2, cz + sz * 0.42), (0.1, 0.4, 0.1), 0, "Gold")
        obox(g, (sx * 0.6, 0.88, cz + 0.05), (0.12, 0.08, 0.92), 0, "Gold")
        obox(g, (sx * 0.6, 0.72, cz + 0.45), (0.08, 0.3, 0.08), 0, "Gold")
        obox(g, (sx * 0.56, 1.6, cz - 0.46), (0.1, 2.1, 0.18), 0, "Gold")
    obox(g, (0, 1.6, cz - 0.45), (1.02, 1.9, 0.14), 0, "Purple", 0.05)
    obox(g, (0, 2.68, cz - 0.46), (1.26, 0.18, 0.2), 0, "Gold")
    obox(g, (0, 2.9, cz - 0.46), (0.42, 0.3, 0.12), 0, "Gold")
    sphere(g, (0, 3.1, cz - 0.46), 0.09, "Gold", 8, 5)

def chandelier(x, z, y, R, seed=0):
    g = "OM_Furniture"
    cyl(g, x, y + 1.95, z, 0.045, 0.045, WALL_H - 0.5 - (y + 1.95), "Gold", 8)
    lathe("OM_Ceiling", x, WALL_H - 0.75, z, [(0, 0), (0.25, 0.0), (0.7, 0.12), (0.85, 0.25), (0, 0.25)], 16, "Gold")
    lathe(g, x, y - 1.0, z, [(0, 0), (0.06, 0.06), (0.17, 0.3), (0.11, 0.5), (0.2, 0.78), (0.16, 0.98), (0.3, 1.1), (0.15, 1.3),
                             (0.1, 1.8), (0.22, 2.2), (0.12, 2.6), (0.07, 2.9), (0, 2.95)], 12, "Gold")
    for (ry, rr, n, tube_r) in ((0.0, R, 14, 0.06), (0.95, R * 0.62, 9, 0.05), (1.7, R * 0.36, 6, 0.04)):
        torus(g, (x, y + ry, z), rr, tube_r, None, 32 if rr > 1 else 20, 6)
        for k in range(n):
            a = 2 * math.pi * (k + 0.5 * (ry > 0)) / n
            px, pz = x + rr * math.cos(a), z + rr * math.sin(a)
            beam(g, (x + 0.15 * math.cos(a), y + ry + 0.35, z + 0.15 * math.sin(a)), (px, y + ry + 0.02, pz), 0.035, 0.035, "Gold")
            lathe(g, px, y + ry + 0.02, pz, [(0, 0), (0.05, 0.0), (0.09, 0.05), (0.09, 0.07), (0, 0.07)], 8, "Gold")
            cyl(g, px, y + ry + 0.08, pz, 0.028, 0.028, 0.2, "Candle", 6)
            flame(px, y + ry + 0.28, pz)
            if ry == 0.0:                                                        # hanging crystal drops
                b = a + math.pi / n
                cx, cz = x + rr * 0.97 * math.cos(b), z + rr * 0.97 * math.sin(b)
                cyl(g, cx, y - 0.32, cz, 0.006, 0.05, 0.12, "Crystal", 4)
                cyl(g, cx, y - 0.2, cz, 0.05, 0.006, 0.2, "Crystal", 4)
    torus(g, (x, y - 0.25, z), R * 0.82, 0.03, None, 28, 5)
    for k in range(4):                                                           # bake lights for the candles
        a = 2 * math.pi * k / 4
        POINTS.append((x + R * 0.8 * math.cos(a), y + 0.4, z + R * 0.8 * math.sin(a), V["candle_w"] * 4, "#ffc070", 0.4))
    POINTS.append((x, y + 1.3, z, V["candle_w"] * 5, "#ffc070", 0.6))

def banner(px, pz, nx, nz, top=9.2, w=1.5, h=5.8, seed=0):
    """A hanging purple banner with the gold crest (two-sided), on a gold rod with finials."""
    g = "OM_Furniture"; gg = grp(g); bm = gg.bm; rnd = random.Random(seed)
    dx, dz = nz, -nx
    beam(g, (px - dx * (w / 2 + 0.25), top + 0.12, pz - dz * (w / 2 + 0.25)), (px + dx * (w / 2 + 0.25), top + 0.12, pz + dz * (w / 2 + 0.25)), 0.06, 0.06, "Gold")
    for s in (-1, 1):
        sphere(g, (px + s * dx * (w / 2 + 0.3), top + 0.12, pz + s * dz * (w / 2 + 0.3)), 0.09, "Gold", 8, 5)
    cols, rows = (14, 32) if RUIN else (8, 18)
    def P(u, v, side):
        yy = top - v * h * (1.0 - 0.13 * abs(2 * u - 1))
        fold = 0.05 * math.sin(u * math.pi * 3.0 + 0.6) + side * 0.012
        return G(px + dx * (u - 0.5) * w + nx * (0.03 + fold), yy, pz + dz * (u - 0.5) * w + nz * (0.03 + fold))
    nB = Vector((nx, -nz, 0.0))
    for side, m in ((1, "BannerCrest"), (-1, "PurpleBack")):
        V2 = [[bm.verts.new(P(i / cols, j / rows, side)) for i in range(cols + 1)] for j in range(rows + 1)]
        fs = []
        for j in range(rows):
            for i in range(cols):
                if RUIN:                                                         # torn and burnt away at the bottom
                    v = (j + 0.5) / rows; u = (i + 0.5) / cols
                    cut = 0.66 + 0.16 * math.sin(u * 9.0 + seed) * math.cos(u * 4.0 + seed * 1.7) + 0.07 * math.sin(u * 31.0 + seed * 3.0)
                    if v > cut or (v > 0.4 and random.Random(seed * 100 + i * 7 + j).random() < 0.05 + 0.25 * max(0.0, v - cut + 0.12) / 0.12):
                        continue
                f = bm.faces.new((V2[j][i], V2[j][i + 1], V2[j + 1][i + 1], V2[j + 1][i]))
                f[gg.custom] = 1
                for l, uv in zip(f.loops, ((i / cols, 1 - j / rows), ((i + 1) / cols, 1 - j / rows),
                                           ((i + 1) / cols, 1 - (j + 1) / rows), (i / cols, 1 - (j + 1) / rows))):
                    l[gg.uv].uv = uv
                fs.append(f)
        for f in fs:
            f.normal_update()
            if (f.normal.dot(nB) < 0) == (side > 0):
                f.normal_flip()
        _tag(gg, fs, m)

def build_furniture(S, PIL):
    back = S["back"]
    # back wall: crest panel between four bookshelves; desk, chair, vases, rug
    tc = back.L / 2
    back.box("OM_Furniture", tc - 1.95, tc + 1.95, 1.55, 8.45, 0.0, 0.12, "Gold", 0.02)
    back.quad("OM_Furniture", tc - 1.75, tc + 1.75, 1.75, 8.25, 0.13, [(0, 0), (1, 0), (1, 1), (0, 1)], "CrestPanel")
    back.box("OM_Furniture", tc - 0.9, tc + 0.9, 8.45, 8.75, 0.0, 0.2, "Gold", 0.02)
    back.box("OM_Furniture", tc - 0.3, tc + 0.3, 8.75, 9.25, 0.04, 0.18, "Gold")
    for k, (a, b) in enumerate(((tc - 5.7, tc - 3.2), (tc - 8.25, tc - 5.85), (tc + 3.2, tc + 5.7), (tc + 5.85, tc + 8.25))):
        bookshelf(back, a, b, 6.4, 0.7, 11 + k)
    for t in (tc - 2.55, tc + 2.55):
        sconce(back, t, 6.3, 0.0)
    desk_and_chair()
    for sx in (-1, 1):
        vase(sx * 3.75, -23.3, 5 + sx)
    obox("OM_Furniture", (0, 0.012, -23.2), (8.8, 0.024, 6.2), 0, "Rug")
    for (cx, cz, wx, wz) in ((0, -20.2, 8.6, 0.12), (0, -26.2, 8.6, 0.12), (-4.3, -23.2, 0.12, 6.0), (4.3, -23.2, 0.12, 6.0)):
        obox("OM_Furniture", (cx, 0.03, cz), (wx, 0.012, wz), 0, "Gold")
    for side in "LR":
        bay, wing = S["bay" + side], S["wing" + side]
        # carpet runners along the walls
        for s in (bay, wing):
            s.box("OM_Furniture", 0.9, s.L - 0.9, 0.0, 0.022, 0.85, 2.15, "Carpet")
            for o in (0.92, 2.0):
                s.box("OM_Furniture", 0.9, s.L - 0.9, 0.022, 0.03, o, o + 0.08, "Gold")
        cabinet(bay, bay.L / 2, 2.2, 31 if side == "L" else 37, "globe")
        bookshelf(wing, 1.15, 3.75, 6.4, 0.7, 41 if side == "L" else 47)
        for k, t in enumerate((5.6, 8.9, 12.2)):
            cabinet(wing, t, 2.0, 50 + k + (side == "R") * 10, "books" if k != 1 else ("globe" if side == "L" else "armillary"))
        sconce(bay, 1.25, 5.8, 0.0)
        sconce(bay, bay.L - 1.25, 5.8, 0.0)
        # standing armillary sphere and a floor lamp near the middle pillars
        cx, cz, nx, nz, rot = PIL["P2" + side]
        if not RUIN or side == "L":
            armillary(cx + nx * 1.6 + nz * 1.0, 0.0, cz + nz * 1.6 - nx * 1.0, 0.42)
        floor_lamp(cx + nx * 1.5 - nz * 1.2, cz + nz * 1.5 + nx * 1.2)
        # banners on the inner pillars
        cx, cz, nx, nz, rot = PIL["P3" + side]
        banner(cx + nx * 0.85, cz + nz * 0.85, nx, nz, 9.0, 1.4, 5.6, 3 if side == "L" else 8)
    chandelier(0.0, -15.0, 7.4, 2.4, 1)
    chandelier(0.0, -23.0, 8.2, 1.7, 2)

# ======================================================================
#  Ruined: rubble, wreckage, fires, smoke
# ======================================================================
def build_ruin():
    g = "OM_Furniture"; rnd = random.Random(99)
    for k, (x, z, r, h) in enumerate(RUBBLE):
        mound(g, x, z, r, r * 0.75, h * 0.6, 200 + k, "Rubble")
        for j in range(int(6 + r * 7)):
            a = rnd.uniform(0, 6.28); d = rnd.uniform(0, r)
            s = rnd.uniform(0.12, 0.42) * (0.6 + 0.4 * r / 2)
            rock(g, x + d * math.cos(a), max(0.0, h * 0.5 * (1 - d / r)), z + d * math.sin(a) * 0.8, s * 1.3, s * 0.8, s,
                 300 + k * 50 + j, rnd.choice(["Rubble", "Rubble", "RubbleDark", "Marble"]), 1, 0.25)
        for j in range(int(r * 2)):                                              # broken planks and beams
            a = rnd.uniform(0, 180)
            obox(g, (x + rnd.uniform(-r, r) * 0.6, 0.06 + rnd.uniform(0, h * 0.5), z + rnd.uniform(-r, r) * 0.5),
                 (rnd.uniform(0.8, 1.8), 0.08, 0.16), a, rnd.choice(["Wood", "WoodDark", "BookBurnt"]))
        for j in range(int(r * 3)):                                              # scattered books and papers
            obox(g, (x + rnd.uniform(-1.4, 1.4) * r, 0.02, z + rnd.uniform(-1, 1) * r), (0.3, 0.04, 0.22), rnd.uniform(0, 180),
                 rnd.choice(BOOKS + ["Paper", "BookBurnt"]))
    # a fallen ceiling beam with its gold trim, broken in two
    obox(g, (-4.4, 0.25, -17.6), (3.6, 0.45, 0.5), 22, "CeilingBeam")
    obox(g, (-4.4, 0.52, -17.6), (3.6, 0.06, 0.58), 22, "Gold")
    obox(g, (-1.6, 0.25, -18.9), (1.8, 0.45, 0.5), -12, "CeilingBeam")
    # the right armillary lies wrecked on the floor; a chair knocked over on the left
    armillary(14.6, 0.0, -16.6, 0.42, fallen=True)
    obox(g, (-12.8, 0.3, -16.2), (0.9, 0.12, 0.85), 30, "Purple")
    obox(g, (-13.3, 0.55, -16.6), (0.9, 0.12, 1.1), 30, "Purple")
    # loose papers across the back of the hall
    for k in range(40):
        x = rnd.uniform(-20, 20); z = rnd.uniform(-26, -9.5)
        obox(g, (x, 0.006, z), (0.22, 0.006, 0.3), rnd.uniform(0, 180), "Paper")
    # fires, smoke columns and the haze under the ceiling
    for i, (x, y, z, s) in enumerate(FIRES):
        for a in (0.0, math.pi / 2):
            dx, dz = math.cos(a) * s * 0.6, math.sin(a) * s * 0.6
            quad("OM_Fire", [(x - dx, y, z - dz), (x + dx, y, z + dz), (x + dx, y + s * 1.9, z + dz), (x - dx, y + s * 1.9, z - dz)],
                 [(0, i + 0.001), (1, i + 0.001), (1, i + 0.999), (0, i + 0.999)], "FireCard")
    for i, (x, y, z, s, h) in enumerate(SMOKES):
        for a in (0.3, 0.3 + math.pi / 2):
            dx, dz = math.cos(a) * s, math.sin(a) * s
            quad("OM_Smoke", [(x - dx, y, z - dz), (x + dx, y, z + dz), (x + dx * 1.8, y + h, z + dz * 1.8), (x - dx * 1.8, y + h, z - dz * 1.8)],
                 [(0, i + 0.001), (1, i + 0.001), (1, i + 0.999), (0, i + 0.999)], "SmokeCard")
    for i, (z, y0, y1, hw) in enumerate(HAZE):
        quad("OM_Haze", [(-hw, y0, z), (hw, y0, z), (hw, y1, z), (-hw, y1, z)],
             [(0, i + 0.001), (2 * hw / 20.0, i + 0.001), (2 * hw / 20.0, i + 0.999), (0, i + 0.999)], "SmokeCard")

def build_floor():
    g = grp("OM_Floor")
    quad(g, [(-FLOOR_X, 0, FLOOR_FRONT), (FLOOR_X, 0, FLOOR_FRONT), (FLOOR_X, 0, FLOOR_BACK), (-FLOOR_X, 0, FLOOR_BACK)],
         [(-FLOOR_X, -FLOOR_FRONT), (FLOOR_X, -FLOOR_FRONT), (FLOOR_X, -FLOOR_BACK), (-FLOOR_X, -FLOOR_BACK)], "FloorMarble")

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
    bpy.context.scene["ce_variant"] = VARIANT
    bpy.context.scene["ce_world_strength"] = V["world"][1]
    def area(name, pos, aim, size, power, colr):
        ld = bpy.data.lights.new(name, 'AREA'); ld.shape = 'RECTANGLE'
        ld.size, ld.size_y = size; ld.energy = power; ld.color = srgb(colr)
        o = bpy.data.objects.new(name, ld); col("Lights").objects.link(o); o.location = G(*pos)
        o.rotation_mode = 'QUATERNION'; o.rotation_quaternion = (G(*aim) - G(*pos)).normalized().to_track_quat('-Z', 'Y')
        o.visible_camera = False
    area("Fill_Front", (0, 7.0, 14.0), (0, 2.5, -14.0), (32, 10), V["fill"][0], V["fill"][1])
    area("Fill_Top", (0, 12.0, -12.0), (0, 0.0, -12.0), (30, 22), V["top"][0], V["top"][1])
    for k, (p, aim, ww, hh) in enumerate(WIN_LIGHTS):
        area("Window_%d" % k, p, aim, (ww, hh), V["window_w"], V["window_color"])
    def point(name, p, wts, colr, rad=0.3):
        ld = bpy.data.lights.new(name, 'POINT'); ld.energy = wts; ld.color = srgb(colr); ld.shadow_soft_size = rad
        o = bpy.data.objects.new(name, ld); col("Lights").objects.link(o); o.location = G(*p); o.visible_camera = False
    for k, (x, y, z, wts, c, r) in enumerate(POINTS):
        point("Lamp_%d" % k, (x, y, z), wts, c, r)
    if V["fire_w"] > 0:
        for k, (x, y, z, s) in enumerate(FIRES):
            point("Fire_%d" % k, (x, y + s * 0.6, z + 0.3), V["fire_w"] * s * s, "#ff6a24", s * 0.5)

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
        cd.clip_start = 0.1; cd.clip_end = 400
        o = bpy.data.objects.new(name, cd); col("Cameras").objects.link(o)
        o.location = G(*pos); o.rotation_euler = (math.radians(90), 0, 0)
    bpy.context.scene.camera = bpy.data.objects["CAM_mid"]

CARD_GROUPS = ("OM_Window", "OM_Glow", "OM_Flame", "OM_Fire", "OM_Smoke", "OM_Haze")

def build_all():
    reset(); COLS.clear(); MATS.clear(); GR.clear()
    for L in (WINDOWS, WIN_LIGHTS, FLAMES, POINTS):
        L.clear()
    build_materials()
    build_floor()
    S, PIL = build_room()
    build_ceiling(); build_furniture(S, PIL)
    if RUIN:
        build_ruin()
    build_preview()
    objs = {name: g.finish() for name, g in list(GR.items())}
    for n in CARD_GROUPS:
        if n in objs:
            objs[n].visible_shadow = False
    for n in ("OM_Flame", "OM_Fire", "OM_Smoke", "OM_Haze"):
        if n in objs:
            objs[n].hide_render = True            # animated in Godot (they light the bake through point lights)
    build_lights(); build_cameras(); setup_render()
    tris = {o.name: sum(len(p.vertices) - 2 for p in o.data.polygons) for o in objs.values()}
    return {"variant": VARIANT, "objects": list(objs), "tris": tris, "total_tris": sum(tris.values()),
            "windows": len(WINDOWS), "flames": len(FLAMES), "points": len(POINTS)}

if __name__ == "__main__":
    BUILD_INFO = build_all()
