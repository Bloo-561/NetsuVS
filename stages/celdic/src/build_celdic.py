# Celdic (v3) - 3D stage build script (Blender 5.x, runs in --background). Two variants of the market town:
#   VARIANT=day      a booming market day under a blue sky: the well plaza, shopfronts, the Grand Market behind,
#                    the headframe tower, windmills on the hills, and a crowd of shadow figures cheering the fight
#   VARIANT=burning  the same town at dusk, broken down: the headframe toppled onto the market, stalls crushed,
#                    roofs burnt through, fires, smoke and embers, and a restless, worried crowd at the edges
#
#   blender --background --factory-startup --python run_ce.py -- VARIANT=burning STEPS=build,bake,preview,export
#
# Layout is written in GODOT coordinates (x right, y up, +z toward the camera) and converted
# to Blender (Z-up) by G():  Godot (x, y, z) -> Blender (x, -z, y).  1 unit = 1 m.
# Baked groups (atlases): CE_Buildings (plaza houses, inn, gateway), CE_Props (well, arch, stalls, headframe,
#   props), CE_Far (barns, hills, windmills, woods, mountains), CE_Floor (light map only)
# Card groups (Godot shaders): CE_Sky, CE_Window (emit in the bake); CE_Bunting, CE_Crowd, CE_Sails, CE_Grass,
#   CE_Fire, CE_Smoke, CE_Haze (Godot only)
import bpy, bmesh, math, random
from mathutils import Vector, Matrix

ROOT = r"E:\Netsu Projects\NetsuVS\stages\celdic"
TEXD = ROOT + r"\textures"
VARIANT = globals().get("VARIANT") or "day"

# ---------------- layout (Godot space, metres) ----------------
BURN = VARIANT == "burning"
CENTER_Z = -10.0
FLOOR_X = 50.0                     # floor quad: x +-50, z -30..+22 (the light map covers exactly this)
FLOOR_BACK, FLOOR_FRONT = -30.0, 22.0          # the fighting floor, the round court and the ground round the arch
COURT = (0.0, -9.0)                # centre of the round court; the fighters (z 0) stand on its near side
COURT_R = 12.5                     # its radius (to the outside of the curb band)
COURT_BAND = 1.1                   # the band of dressed curb stones round its rim
ARCH_S = 1.4                       # the arch, 1.4 x the old one, a landmark on the far rim of the court
ARCH_Z = -21.0                     # it stands centred on the far rim, its piers on the curb band
ARCH_HALF, ARCH_SPRING = 1.7 * ARCH_S, 3.1 * ARCH_S  # arch half-width and the height where it starts to curve
WELL = (0.0, ARCH_Z)
GATE_Z = -23.0                     # behind the court the ground turns to the market's trodden earth
SKY_R = 900.0
LANE_X, LANE_Z = 12.5, -9.0        # keep |x| < 12.5 and z > -9 clear (fight lane)

VARIANTS = {
    "day": dict(sun_dir=(0.6, -0.64, -0.48), sun_energy=4.3, sun_color="#ffe2c0", world=("#9cb6d8", 0.95),     # a clear, sunny morning
                fill=(3300, "#f2e8dc"), top=(7600, "#b4c8f0"),
                sky=[(0.0, "#c8d8e0"), (0.12, "#eef4f8"), (0.2, "#a6cbef"), (1.0, "#3e7ad0")], sky_strength=1.0,
                haze="#a8c0d8", lamp_glow=0.6, lamp_w=0, window_color="#2a3036", window_glow=0.2, window_w=0, fire_w=0),
    "burning": dict(sun_dir=(-0.4, -0.22, 0.89), sun_energy=1.8, sun_color="#ffb47a", world=("#4c5478", 0.62),
                    fill=(2000, "#8a94bc"), top=(3000, "#5c6894"),
                    sky=[(0.0, "#3a3644"), (0.08, "#f2a868"), (0.16, "#c88a7a"), (0.32, "#5e6086"), (1.0, "#22284a")],
                    sky_strength=1.15, haze="#7a7896", lamp_glow=6.0, lamp_w=130, window_color="#ffb060", window_glow=4.5,
                    window_w=120, fire_w=260, fire_color="#ffa04c"),
}
V = VARIANTS[VARIANT]

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

def stone_material(name, dark, light, moss=0.15, carved=False, rough=0.6):
    """Weathered blue-grey stone; teal grime in the crevices; carved = knotwork relief."""
    b = NB(name)
    n1 = b.noise(b.pos, 1.1, 6, 0.6)
    c = b.ramp(n1.outputs["Fac"], [(0.32, dark), (0.68, light)])
    grime = b.noise(b.pos, 0.35, 3, 0.5)
    gm = b.math('MULTIPLY', b.math('GREATER_THAN', grime.outputs["Fac"], 0.55), moss)
    c = b.mixc(c, "#3f6b66", gm)
    b.link(c, b.bsdf.inputs["Base Color"])
    b.bsdf.inputs["Roughness"].default_value = rough
    bump = b.n("ShaderNodeBump"); bump.inputs["Strength"].default_value = 0.25
    if carved:
        w = b.n("ShaderNodeTexWave"); w.wave_type = 'RINGS'
        w.inputs["Scale"].default_value = 4.0; w.inputs["Distortion"].default_value = 5.0
        w.inputs["Detail"].default_value = 2.0
        b.link(b.pos, w.inputs["Vector"])
        vor = b.n("ShaderNodeTexVoronoi"); vor.feature = 'DISTANCE_TO_EDGE'; vor.inputs["Scale"].default_value = 7.0
        b.link(b.pos, vor.inputs["Vector"])
        h = b.math('ADD', b.math('MULTIPLY', w.outputs["Fac"], 0.6), b.math('LESS_THAN', vor.outputs["Distance"], 0.03))
        bump.inputs["Strength"].default_value = 0.45
        b.link(h, bump.inputs["Height"])
        # carved grooves catch dirt: darken them
        c2 = b.mixc(c, "#2f3a40", b.math('MULTIPLY', b.math('LESS_THAN', vor.outputs["Distance"], 0.03), 0.35))
        b.link(c2, b.bsdf.inputs["Base Color"])
    else:
        b.link(n1.outputs["Fac"], bump.inputs["Height"])
    b.link(bump.outputs[0], b.bsdf.inputs["Normal"])
    return b

def emissive_card(name, fn, color, strength, floor=0.25):
    b = NB(name)
    im = b.image(fn, b.uv, 'EXTEND', True)
    k = b.math('ADD', b.math('MULTIPLY', im.outputs["Color"], 1.0 - floor), floor)
    em = b.n("ShaderNodeEmission"); em.inputs["Color"].default_value = (*srgb(color), 1)
    b.link(b.math('MULTIPLY', k, strength), em.inputs["Strength"])
    b.link(em.outputs[0], b.out.inputs[0])
    return b


def beam(g, p0, p1, w, h, m="Beam"):
    """Square timber from Godot point p0 to p1 (w across, h tall)."""
    g = grp(g) if isinstance(g, str) else g
    a, b = G(*p0), G(*p1); d = b - a; L = d.length
    q = d.normalized().to_track_quat('Z', 'Y')
    M = Matrix.Translation((a + b) / 2) @ q.to_matrix().to_4x4() @ Matrix.Diagonal((w, h, L, 1.0))
    r = bmesh.ops.create_cube(g.bm, size=1.0, matrix=M)
    _tag(g, list({f for v in r["verts"] for f in v.link_faces}), m)

def gable_house(g, cx, cz, wx, wz, wall_h, rise, m_wall="Planks", m_roof="Roof", over=0.45, ridge_z=True, trim="Beam",
                broken=0.0, seed=0, rafter="Charred"):
    """Box house with a gable roof. ridge_z: ridge runs front-back (gable end faces the camera).
    broken: fraction of the camera-facing roof slope that has collapsed (only charred rafters left)."""
    rnd = random.Random(seed)
    box(g, cx, -0.2, wall_h, cz, wx, wz, m_wall)
    for sx in (-1, 1):                                    # corner posts and a mid band
        for sz in (-1, 1):
            box(g, cx + sx * (wx / 2 - 0.1), -0.2, wall_h, cz + sz * (wz / 2 - 0.1), 0.28, 0.28, trim, 0.02)
    box(g, cx, wall_h * 0.48, wall_h * 0.48 + 0.18, cz, wx + 0.08, wz + 0.08, trim)
    box(g, cx, wall_h - 0.2, wall_h, cz, wx + 0.12, wz + 0.12, trim)
    # gable triangles + roof slabs
    gg = grp(g) if isinstance(g, str) else g
    span = wx if ridge_z else wz
    length = wz if ridge_z else wx
    for s in (-1, 1):
        # gable wall triangle at each end
        if ridge_z:
            zf = cz + s * wz / 2
            if broken > 0 and s > 0:            # front gable burnt away: only charred studs of uneven height remain
                for k in range(7):
                    xk = cx - wx / 2 + 0.4 + k * (wx - 0.8) / 6
                    hk = wall_h + (rise * (1 - abs(xk - cx) / (wx / 2))) * rnd.uniform(0.2, 0.9)
                    box(g, xk, wall_h, hk, zf, 0.14, 0.14, rafter)
            else:
                quad(gg, [(cx - wx / 2, wall_h, zf), (cx + wx / 2, wall_h, zf), (cx, wall_h + rise, zf)][::(1 if s > 0 else -1)],
                     [(0, 0), (1, 0), (0.5, 1)][::(1 if s > 0 else -1)], m_wall)
        else:
            xf = cx + s * wx / 2
            quad(gg, [(xf, wall_h, cz + wz / 2), (xf, wall_h, cz - wz / 2), (xf, wall_h + rise, cz)][::(1 if s > 0 else -1)],
                 [(0, 0), (1, 0), (0.5, 1)][::(1 if s > 0 else -1)], m_wall)
        # roof slab from eave to ridge (with overhang)
        half = span / 2 + over
        ang = math.atan2(rise, span / 2)
        Ls = half / math.cos(ang)
        full = length + 2 * over
        gone = (broken if s > 0 else broken * 0.6) if ridge_z else (broken if s > 0 else 0.0)
        keep = full * (1 - gone)
        if ridge_z:
            e = (cx + s * half, wall_h - over * math.tan(ang), cz); r_ = (cx, wall_h + rise, cz)
            zc = cz - full * gone / 2                # the intact part stays at the back
            mid = ((e[0] + r_[0]) / 2, (e[1] + r_[1]) / 2 + 0.08, zc)
            M = Matrix.Translation(G(*mid)) @ Matrix.Rotation(s * ang, 4, 'Y') @ Matrix.Diagonal((Ls, keep, 0.16, 1.0))
            if gone > 0:
                zz = zc + keep / 2 + 0.35
                while zz < cz + full / 2:
                    t = rnd.uniform(0.35, 1.0) if rnd.random() < 0.6 else 1.0      # snapped rafters
                    p0 = (e[0], e[1], zz); p1 = (e[0] + (r_[0] - e[0]) * t, e[1] + (r_[1] - e[1]) * t, zz)
                    beam(g, p0, p1, 0.14, 0.2, rafter)
                    zz += rnd.uniform(0.6, 0.9)
        else:
            e = (cx, wall_h - over * math.tan(ang), cz + s * half); r_ = (cx, wall_h + rise, cz)
            xc = cx + full * gone / 2
            mid = (xc, (e[1] + r_[1]) / 2 + 0.08, (e[2] + r_[2]) / 2)
            M = Matrix.Translation(G(*mid)) @ Matrix.Rotation(s * ang, 4, 'X') @ Matrix.Diagonal((keep, Ls, 0.16, 1.0))
            if gone > 0:
                xx = xc - keep / 2 - 0.35
                while xx > cx - full / 2:
                    t = rnd.uniform(0.35, 1.0) if rnd.random() < 0.6 else 1.0
                    p0 = (xx, e[1], e[2]); p1 = (xx, e[1] + (r_[1] - e[1]) * t, e[2] + (r_[2] - e[2]) * t)
                    beam(g, p0, p1, 0.14, 0.2, rafter)
                    xx -= rnd.uniform(0.6, 0.9)
        r = bmesh.ops.create_cube(gg.bm, size=1.0, matrix=M)
        _tag(gg, list({f for v in r["verts"] for f in v.link_faces}), m_roof)
    # ridge beam
    if ridge_z:
        box(g, cx, wall_h + rise - 0.05, wall_h + rise + 0.2, cz, 0.3, length + 2 * over, trim)
    else:
        box(g, cx, wall_h + rise - 0.05, wall_h + rise + 0.2, cz, length + 2 * over, 0.3, trim)

def window(g, x, y, z, w, h, face_z=True, s=1):
    """Framed window on a +z (or +x) facing wall; the pane is a glowing card (Godot: CE_Window)."""
    if face_z:
        box(g, x, y - 0.08, y + h + 0.08, z + s * 0.05, w + 0.2, 0.12, "Beam")
        quad("CE_Window", [(x - w / 2, y, z + s * 0.12), (x + w / 2, y, z + s * 0.12), (x + w / 2, y + h, z + s * 0.12), (x - w / 2, y + h, z + s * 0.12)][::s],
             [(0, 0), (1, 0), (1, 1), (0, 1)][::s], "WindowCard")
        box(g, x, y + h / 2 - 0.04, y + h / 2 + 0.04, z + s * 0.14, w, 0.05, "Beam")
        box(g, x, y, y + h, z + s * 0.14, 0.06, 0.05, "Beam")
    else:
        box(g, x + s * 0.05, y - 0.08, y + h + 0.08, z, 0.12, w + 0.2, "Beam")
        quad("CE_Window", [(x + s * 0.12, y, z + w / 2), (x + s * 0.12, y, z - w / 2), (x + s * 0.12, y + h, z - w / 2), (x + s * 0.12, y + h, z + w / 2)][::s],
             [(0, 0), (1, 0), (1, 1), (0, 1)][::s], "WindowCard")
    WINDOWS.append((x, y + h / 2, z, w * h))



# ======================================================================
#  shared shape helpers (lathe, prisms, cards, windows)
# ======================================================================
def lathe(g, x, y0, z, prof, seg=12, m="Steel", rot=0.0):
    """Surface of revolution around the vertical through (x, z). prof = [(radius, height), ...] bottom -> top,
    starting and ending at radius 0 so it is closed."""
    gg = grp(g) if isinstance(g, str) else g; bm = gg.bm
    rings = []
    for (r, y) in prof:
        if r < 1e-4:
            rings.append([bm.verts.new(G(x, y0 + y, z))])
        else:
            rings.append([bm.verts.new(G(x + r * math.cos(2 * math.pi * i / seg + rot), y0 + y, z + r * math.sin(2 * math.pi * i / seg + rot)))
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

def hexa(g, pts, m):
    """A closed six-sided solid from 8 Godot points: bottom ring (4) then the matching top ring (4)."""
    gg = grp(g) if isinstance(g, str) else g; bm = gg.bm
    v = [bm.verts.new(G(*p)) for p in pts]
    b, t = v[:4], v[4:]
    faces = [bm.faces.new((b[3], b[2], b[1], b[0])), bm.faces.new((t[0], t[1], t[2], t[3]))]
    for i in range(4):
        j = (i + 1) % 4
        faces.append(bm.faces.new((b[i], b[j], t[j], t[i])))
    bmesh.ops.recalc_face_normals(bm, faces=faces)
    _tag(gg, faces, m)
    return faces

def prism(g, pts, axis, a0, a1, m):
    """A convex outline pushed along a world axis. axis 'z': pts are (x, y), from z = a0 to a1;
    axis 'x': pts are (z, y), from x = a0 to a1; axis 'y': pts are (x, z), from y = a0 to a1."""
    gg = grp(g) if isinstance(g, str) else g; bm = gg.bm
    def P(p, a):
        if axis == 'z':
            return G(p[0], p[1], a)
        if axis == 'x':
            return G(a, p[1], p[0])
        return G(p[0], a, p[1])
    F = [bm.verts.new(P(p, a1)) for p in pts]
    B = [bm.verts.new(P(p, a0)) for p in pts]
    faces = [bm.faces.new(F), bm.faces.new(B[::-1])]
    n = len(pts)
    for i in range(n):
        j = (i + 1) % n
        faces.append(bm.faces.new((F[i], B[i], B[j], F[j])))
    bmesh.ops.recalc_face_normals(bm, faces=faces)
    _tag(gg, faces, m)
    return faces

def gable(g, x0, x1, z0, z1, y0, y_eave, y_ridge, m_wall, m_roof, ridge_axis='z', over=0.4, thick=0.25):
    """A building with a pitched roof: walls to y_eave, gable ends, two roof slabs (ridge along z or x)."""
    box(g, (x0 + x1) / 2, y0, y_eave, (z0 + z1) / 2, x1 - x0, z1 - z0, m_wall)
    if ridge_axis == 'z':
        xm = (x0 + x1) / 2
        prism(g, [(x0, y_eave), (x1, y_eave), (xm, y_ridge)][::-1], 'z', z0, z1, m_wall)
        for s in (-1, 1):
            xe = x0 - over if s < 0 else x1 + over
            ye = y_eave - over * (y_ridge - y_eave) / ((x1 - x0) / 2)
            p = [(xe, ye), (xm, y_ridge), (xm, y_ridge + thick), (xe, ye + thick)]
            prism(g, p if s > 0 else p[::-1], 'z', z0 - over, z1 + over, m_roof)
    else:
        zm = (z0 + z1) / 2
        prism(g, [(z0, y_eave), (z1, y_eave), (zm, y_ridge)][::-1], 'x', x0, x1, m_wall)
        for s in (-1, 1):
            ze = z0 - over if s < 0 else z1 + over
            ye = y_eave - over * (y_ridge - y_eave) / ((z1 - z0) / 2)
            p = [(ze, ye), (zm, y_ridge), (zm, y_ridge + thick), (ze, ye + thick)]
            prism(g, p if s > 0 else p[::-1], 'x', x0 - over, x1 + over, m_roof)

def card(gname, pts, fid, mat, u0=0.0, u1=1.0):
    """A shader card: Blender UV.x = u0..u1 across, UV.y = id + h (h 0 at pts[0..1], 1 at pts[2..3])."""
    return quad(grp(gname, "Cards"), pts, [(u0, fid + 0.001), (u1, fid + 0.001), (u1, fid + 0.999), (u0, fid + 0.999)], mat)

def card_uv(gg, faces, fid, h=0.5, u=0.5):
    for f in faces:
        f[gg.custom] = 1
        for l in f.loops:
            l[gg.uv].uv = (u, fid + h)

def glow_lathe(gname, x, y0, z, prof, fid, seg=10, mat="GlowWarm"):
    gg = grp(gname, "Cards")
    card_uv(gg, lathe(gg, x, y0, z, prof, seg, mat), fid)

def glow_box(gname, center, size, fid, mat="GlowWarm", rot_y=0.0):
    gg = grp(gname, "Cards")
    before = len(gg.bm.faces)
    obox(gg, center, size, rot_y, mat)
    card_uv(gg, list(gg.bm.faces)[before:], fid)

def letters(gname, text, x0, y0, z, h, fid, mat="GlowSign", face=1, depth=0.12):
    """Block capitals made of glowing boxes (a lit sign). Supported: A..Z subset used here."""
    S = {   # 5x7 grid strokes: (col0, row0, col1, row1) rectangles in grid units
        "R": [(0, 0, 1, 7), (1, 6, 4, 7), (3, 4, 4, 7), (1, 3, 4, 4), (2, 0, 3, 3), (3, 0, 4, 2)],
        "O": [(0, 1, 1, 6), (3, 1, 4, 6), (1, 0, 3, 1), (1, 6, 3, 7)],
        "E": [(0, 0, 1, 7), (0, 0, 4, 1), (0, 3, 3, 4), (0, 6, 4, 7)],
        "F": [(0, 0, 1, 7), (0, 3, 3, 4), (0, 6, 4, 7)],
        "C": [(0, 1, 1, 6), (1, 0, 4, 1), (1, 6, 4, 7)],
        "K": [(0, 0, 1, 7), (1, 3, 2, 4), (2, 4, 3, 5), (3, 5, 4, 7), (2, 2, 3, 3), (3, 0, 4, 2)],
    }
    u = h / 7.0; x = x0
    for ch in text:
        for (c0, r0, c1, r1) in S.get(ch, []):
            glow_box(gname, (x + (c0 + c1) / 2 * u, y0 + (r0 + r1) / 2 * u, z + face * depth / 2),
                     ((c1 - c0) * u, (r1 - r0) * u, depth), fid, mat)
        x += 5 * u

WIN = [0]          # running window id (each window card gets its own, the shader picks lit / dark from it)

def window_grid(gname, face, a0, a1, y0, y1, plane, col_w=2.6, row_h=3.4, ww=1.4, wh=1.8, shop=False, skip=None):
    """Window cards on a facade. face: '+z', '-z', '+x', '-x'; a0..a1 the span along the facade (x for z-faces,
    z for x-faces); plane = the facade's coordinate (+0.06 outward is added). shop=True: one big lit shop window
    per bay (UV.x 2..3 tells the shader)."""
    n = max(1, int((a1 - a0) / col_w)); cw = (a1 - a0) / n
    rows = 1 if shop else max(1, int((y1 - y0) / row_h))
    rh = (y1 - y0) / rows
    sgn = 1 if face[0] == '+' else -1
    for i in range(n):
        for j in range(rows):
            if skip and skip(i, j):
                continue
            ac = a0 + (i + 0.5) * cw; yc = y0 + (j + 0.5) * rh
            hw, hh = (cw * 0.42, rh * 0.38) if shop else (ww / 2, wh / 2)
            wid = WIN[0]; WIN[0] += 1
            if face[1] == 'z':
                zc = plane + sgn * 0.06
                pts = [(ac - hw * sgn, yc - hh, zc), (ac + hw * sgn, yc - hh, zc), (ac + hw * sgn, yc + hh, zc), (ac - hw * sgn, yc + hh, zc)]
            else:
                xc = plane + sgn * 0.06
                pts = [(xc, yc - hh, ac + hw * sgn), (xc, yc - hh, ac - hw * sgn), (xc, yc + hh, ac - hw * sgn), (xc, yc + hh, ac + hw * sgn)]
            card(gname, pts, wid, "WindowCard", 2.0 if shop else 0.0, 3.0 if shop else 1.0)


# ======================================================================
#  materials
# ======================================================================
def wood_material(name, dark, light, scale=2.5, vertical=True, rough=0.8, scorch=None):
    """Weathered planks: grain bands, plank seams; burning variant: big blotches of burnt wood."""
    scorch = (0.55 if BURN else 0.0) if scorch is None else scorch
    b = NB(name)
    w = b.n("ShaderNodeTexWave"); w.wave_type = 'BANDS'; w.bands_direction = 'X' if vertical else 'Y'
    w.inputs["Scale"].default_value = scale; w.inputs["Distortion"].default_value = 5.0; w.inputs["Detail"].default_value = 3.0
    b.link(b.pos, w.inputs["Vector"])
    n = b.noise(b.pos, 6.0, 4, 0.6)
    c = b.ramp(w.outputs["Fac"], [(0.2, dark), (0.8, light)])
    c = b.mixc(c, dark, b.math('MULTIPLY', n.outputs["Fac"], 0.35))
    br = b.n("ShaderNodeTexBrick"); br.offset = 0.5
    for k, v in (("Scale", 1.0), ("Mortar Size", 0.012), ("Brick Width", 0.22 if vertical else 3.0), ("Row Height", 3.0 if vertical else 0.22)):
        br.inputs[k].default_value = v
    br.inputs["Color1"].default_value = (1, 1, 1, 1); br.inputs["Color2"].default_value = (0.9, 0.9, 0.9, 1)
    br.inputs["Mortar"].default_value = (0.3, 0.26, 0.22, 1)
    b.link(b.uv, br.inputs["Vector"])
    c = b.mixc(c, br.outputs["Color"], 1.0, 'MULTIPLY')
    sep = b.n("ShaderNodeSeparateXYZ"); b.link(b.normal, sep.inputs[0])            # sun-faded where it faces the sky
    c = b.mixc(c, "#b8a68a", b.math('MULTIPLY', b.math('MAXIMUM', sep.outputs[2], 0.0), 0.22))
    ao = b.n("ShaderNodeAmbientOcclusion"); ao.inputs["Distance"].default_value = 0.15
    edge = b.math('SUBTRACT', 1.0, ao.outputs["AO"])                                  # worn, lighter edges and corners
    c = b.mixc(c, "#a08a6a", b.math('MULTIPLY', b.math('POWER', b.math('SUBTRACT', 1.0, edge), 6.0), 0.0))
    gb = b.n("ShaderNodeBump"); gb.inputs["Strength"].default_value = 0.35; gb.inputs["Distance"].default_value = 0.02
    b.link(w.outputs["Fac"], gb.inputs["Height"]); b.link(gb.outputs[0], b.bsdf.inputs["Normal"])
    if scorch > 0:
        sn = b.noise(b.pos, 0.35, 4, 0.6)
        burn = b.math('MULTIPLY', b.math('GREATER_THAN', sn.outputs["Fac"], 1.0 - scorch * 0.6), 0.85)
        c = b.mixc(c, "#181210", burn)
    b.link(c, b.bsdf.inputs["Base Color"]); b.bsdf.inputs["Roughness"].default_value = rough
    return b

def add_weathering(mname, amount=0.3, grime="#4a443a"):
    """Grime layered over a material's base colour (both variants): dark streaks running down the walls
    (noise stretched along the vertical) and blotchy dirt."""
    m = MATS[mname]; nt = m.node_tree
    bsdf = next((n for n in nt.nodes if n.type == 'BSDF_PRINCIPLED'), None)
    if bsdf is None:
        return
    sock = bsdf.inputs["Base Color"]
    if not sock.links:
        return
    src = sock.links[0].from_socket
    geo = nt.nodes.new("ShaderNodeNewGeometry")
    mp = nt.nodes.new("ShaderNodeMapping"); mp.inputs["Scale"].default_value = (1.0, 1.0, 0.12)    # Blender z is up
    nt.links.new(geo.outputs["Position"], mp.inputs["Vector"])
    st = nt.nodes.new("ShaderNodeTexNoise"); st.inputs["Scale"].default_value = 2.2; st.inputs["Detail"].default_value = 3.0
    nt.links.new(mp.outputs["Vector"], st.inputs["Vector"])
    r1 = nt.nodes.new("ShaderNodeMapRange"); r1.inputs["From Min"].default_value = 0.5; r1.inputs["From Max"].default_value = 0.7
    r1.inputs["To Max"].default_value = amount
    nt.links.new(st.outputs["Fac"], r1.inputs[0])
    bl = nt.nodes.new("ShaderNodeTexNoise"); bl.inputs["Scale"].default_value = 0.7; bl.inputs["Detail"].default_value = 4.0
    nt.links.new(geo.outputs["Position"], bl.inputs["Vector"])
    r2 = nt.nodes.new("ShaderNodeMapRange"); r2.inputs["From Min"].default_value = 0.52; r2.inputs["From Max"].default_value = 0.72
    r2.inputs["To Max"].default_value = amount * 0.7
    nt.links.new(bl.outputs["Fac"], r2.inputs[0])
    mx = nt.nodes.new("ShaderNodeMath"); mx.operation = 'MAXIMUM'
    nt.links.new(r1.outputs[0], mx.inputs[0]); nt.links.new(r2.outputs[0], mx.inputs[1])
    mix = nt.nodes.new("ShaderNodeMix"); mix.data_type = 'RGBA'; mix.blend_type = 'MIX'
    nt.links.new(mx.outputs[0], mix.inputs[0]); nt.links.new(src, mix.inputs[6])
    mix.inputs[7].default_value = (*srgb(grime), 1)
    nt.links.new(mix.outputs[2], sock)

def plain(name, dark, light, scale=3.0, rough=0.7, metal=0.0):
    b = NB(name)
    n = b.noise(b.pos, scale, 4, 0.55)
    b.link(b.ramp(n.outputs["Fac"], [(0.3, dark), (0.7, light)]), b.bsdf.inputs["Base Color"])
    b.bsdf.inputs["Roughness"].default_value = rough; b.bsdf.inputs["Metallic"].default_value = metal
    return b

def brick_material(name, c1, c2, mortar, w=0.25, h=0.08):
    b = NB(name)
    br = b.n("ShaderNodeTexBrick"); br.offset = 0.5
    for k, v in (("Scale", 1.0), ("Mortar Size", 0.012), ("Brick Width", w), ("Row Height", h)):
        br.inputs[k].default_value = v
    br.inputs["Color1"].default_value = (*srgb(c1), 1); br.inputs["Color2"].default_value = (*srgb(c2), 1)
    br.inputs["Mortar"].default_value = (*srgb(mortar), 1)
    b.link(b.uv, br.inputs["Vector"])
    n = b.noise(b.pos, 2.0, 3, 0.5)
    c = b.mixc(br.outputs["Color"], b.ramp(n.outputs["Fac"], [(0.3, "#b8b0a8"), (0.7, "#ffffff")]), 1.0, 'MULTIPLY')
    b.link(c, b.bsdf.inputs["Base Color"]); b.bsdf.inputs["Roughness"].default_value = 0.85
    return b

def roof_material(name, c1="#b5583a", c2="#9a4630"):
    """Terracotta tiles: rows of tiles with dirt and colour variation."""
    b = NB(name)
    br = b.n("ShaderNodeTexBrick"); br.offset = 0.5
    for k, v in (("Scale", 1.0), ("Mortar Size", 0.012), ("Brick Width", 0.3), ("Row Height", 0.22)):
        br.inputs[k].default_value = v
    br.inputs["Color1"].default_value = (*srgb(c1), 1); br.inputs["Color2"].default_value = (*srgb(c2), 1)
    br.inputs["Mortar"].default_value = (*srgb("#4a2a20"), 1)
    b.link(b.uv, br.inputs["Vector"])
    n = b.noise(b.pos, 1.5, 4, 0.6)
    c = b.mixc(br.outputs["Color"], "#6a4a3a", b.math('MULTIPLY', b.math('GREATER_THAN', n.outputs["Fac"], 0.62), 0.4))
    li = b.noise(b.pos, 3.0, 3, 0.6)
    c = b.mixc(c, "#8a8a5a", b.math('MULTIPLY', b.math('GREATER_THAN', li.outputs["Fac"], 0.66), 0.35))     # lichen
    b.link(c, b.bsdf.inputs["Base Color"]); b.bsdf.inputs["Roughness"].default_value = 0.75
    wv = b.n("ShaderNodeTexWave"); wv.inputs["Scale"].default_value = 1.0; b.link(b.uv, wv.inputs["Vector"])
    bp = b.n("ShaderNodeBump"); bp.inputs["Strength"].default_value = 0.55; bp.inputs["Distance"].default_value = 0.04
    b.link(b.math('ADD', br.outputs["Fac"], b.math('MULTIPLY', wv.outputs["Fac"], 0.3)), bp.inputs["Height"])
    b.link(bp.outputs[0], b.bsdf.inputs["Normal"])
    return b

def stone_material(name, dark, light, moss=0.15, rough=0.7):
    b = NB(name)
    n1 = b.noise(b.pos, 1.1, 6, 0.6)
    c = b.ramp(n1.outputs["Fac"], [(0.32, dark), (0.68, light)])
    grime = b.noise(b.pos, 0.35, 3, 0.5)
    c = b.mixc(c, "#4a6a3a", b.math('MULTIPLY', b.math('GREATER_THAN', grime.outputs["Fac"], 0.55), moss))
    b.link(c, b.bsdf.inputs["Base Color"]); b.bsdf.inputs["Roughness"].default_value = rough
    vo = b.n("ShaderNodeTexVoronoi"); vo.feature = 'DISTANCE_TO_EDGE'; vo.inputs["Scale"].default_value = 3.0
    b.link(b.pos, vo.inputs["Vector"])
    ao = b.n("ShaderNodeAmbientOcclusion"); ao.inputs["Distance"].default_value = 0.25
    crev = b.math('SUBTRACT', 1.0, ao.outputs["AO"])
    c2 = b.mixc(c, "#56703e", b.math('MULTIPLY', b.math('POWER', crev, 0.7), moss * 1.6))         # moss in the seams
    b.link(c2, b.bsdf.inputs["Base Color"])
    bump = b.n("ShaderNodeBump"); bump.inputs["Strength"].default_value = 0.4
    b.link(b.math('ADD', b.math('MULTIPLY', n1.outputs["Fac"], 0.6), b.math('MULTIPLY', b.math('LESS_THAN', vo.outputs["Distance"], 0.04), -0.5)),
           bump.inputs["Height"])
    b.link(bump.outputs[0], b.bsdf.inputs["Normal"])
    return b

def stripes(name, c1, c2, width, axis):
    """Faded canvas stripes (awnings, stall covers). axis 'x': stripes change along Godot x; 'z': along Godot z."""
    b = NB(name)
    sep = b.n("ShaderNodeSeparateXYZ"); b.link(b.pos, sep.inputs[0])
    coord = sep.outputs[0] if axis == 'x' else sep.outputs[1]
    band = b.math('GREATER_THAN', b.math('FRACT', b.math('MULTIPLY', coord, 1.0 / width)), 0.5)
    c = b.mixc(c1, c2, band)
    n = b.noise(b.pos, 1.2, 4, 0.6)
    c = b.mixc(c, b.ramp(n.outputs["Fac"], [(0.3, "#c4bcb0"), (0.7, "#ffffff")]), 1.0, 'MULTIPLY')
    b.link(c, b.bsdf.inputs["Base Color"]); b.bsdf.inputs["Roughness"].default_value = 0.85
    b.bsdf.inputs["Sheen Weight"].default_value = 0.2
    fw = b.n("ShaderNodeTexWave"); fw.inputs["Scale"].default_value = 1.6; fw.inputs["Distortion"].default_value = 4.0
    b.link(b.pos, fw.inputs["Vector"])
    fb = b.n("ShaderNodeBump"); fb.inputs["Strength"].default_value = 0.45; fb.inputs["Distance"].default_value = 0.06
    b.link(fw.outputs["Fac"], fb.inputs["Height"]); b.link(fb.outputs[0], b.bsdf.inputs["Normal"])
    return b

def add_haze(b, colour, near, far, hmax):
    """Fade into the distance with distance from the stage (baked in as emission)."""
    dist = b.n("ShaderNodeVectorMath", operation='LENGTH'); b.link(b.pos, dist.inputs[0])
    mr = b.n("ShaderNodeMapRange"); mr.inputs["From Min"].default_value = near; mr.inputs["From Max"].default_value = far
    mr.inputs["To Min"].default_value = 0.0; mr.inputs["To Max"].default_value = hmax
    b.link(dist.outputs["Value"], mr.inputs[0])
    em = b.n("ShaderNodeEmission"); em.inputs["Color"].default_value = (*srgb(colour), 1); em.inputs["Strength"].default_value = 1.0
    mix = b.n("ShaderNodeMixShader"); b.link(mr.outputs[0], mix.inputs[0])
    b.link(b.bsdf.outputs[0], mix.inputs[1]); b.link(em.outputs[0], mix.inputs[2]); b.link(mix.outputs[0], b.out.inputs[0])

def hazed(name, dark, light, near, far, hmax, scale=0.4, rough=0.9):
    b = plain(name, dark, light, scale, rough)
    add_haze(b, V["haze"], near, far, hmax)
    return b

def land(name):
    """Rolling grassland and fields beyond the town, fading into the blue distance."""
    b = NB(name)
    vo = b.n("ShaderNodeTexVoronoi"); vo.voronoi_dimensions = '2D'; vo.feature = 'F1'
    vo.inputs["Scale"].default_value = 0.02; vo.inputs["Randomness"].default_value = 0.85
    b.link(b.pos, vo.inputs["Vector"])
    sep = b.n("ShaderNodeSeparateColor"); b.link(vo.outputs["Color"], sep.inputs[0])
    fields = b.ramp(sep.outputs[0], [(0.0, "#5a8a38"), (0.25, "#82a646"), (0.4, "#b2a65a"), (0.55, "#66963e"),
                                     (0.75, "#96aa50"), (1.0, "#4c7c32")])
    n = b.noise(b.pos, 0.08, 4, 0.6)
    c = b.mixc(fields, b.ramp(n.outputs["Fac"], [(0.3, "#d0d0d0"), (0.7, "#ffffff")]), 1.0, 'MULTIPLY')
    if BURN:
        c = b.mixc(c, "#3a3226", 0.45)
    b.link(c, b.bsdf.inputs["Base Color"]); b.bsdf.inputs["Roughness"].default_value = 0.9
    add_haze(b, V["haze"], 90, 520, 0.7)
    return b

def market_ground(name):
    """Packed earth of the market terrace with stones and straw showing through."""
    b = NB(name)
    n = b.noise(b.pos, 0.6, 5, 0.6)
    c = b.ramp(n.outputs["Fac"], [(0.3, "#6a5a44"), (0.7, "#8a765a")])
    vo = b.n("ShaderNodeTexVoronoi"); vo.inputs["Scale"].default_value = 3.5; b.link(b.pos, vo.inputs["Vector"])
    st = b.math('LESS_THAN', vo.outputs["Distance"], 0.28)
    c = b.mixc(c, "#9a9284", b.math('MULTIPLY', st, b.math('GREATER_THAN', b.noise(b.pos, 0.25, 2, 0.5).outputs["Fac"], 0.5)))
    b.link(c, b.bsdf.inputs["Base Color"]); b.bsdf.inputs["Roughness"].default_value = 0.95
    return b

def worn_paving(name, c1, c2, joint, dirt):
    """The courtyard's worn paving: irregular flags (Voronoi cells) with dark joints, worn and dirty in patches,
    moss in the cracks."""
    b = NB(name)
    vc = b.n("ShaderNodeTexVoronoi"); vc.voronoi_dimensions = '2D'; vc.feature = 'F1'
    vc.inputs["Scale"].default_value = 1.7; vc.inputs["Randomness"].default_value = 0.9
    b.link(b.pos, vc.inputs["Vector"])
    ve = b.n("ShaderNodeTexVoronoi"); ve.voronoi_dimensions = '2D'; ve.feature = 'DISTANCE_TO_EDGE'
    ve.inputs["Scale"].default_value = 1.7; ve.inputs["Randomness"].default_value = 0.9
    b.link(b.pos, ve.inputs["Vector"])
    sep = b.n("ShaderNodeSeparateColor"); b.link(vc.outputs["Color"], sep.inputs[0])
    c = b.ramp(sep.outputs[0], [(0.0, c1), (0.55, c2), (1.0, c1)])
    c = b.mixc(c, joint, b.math('LESS_THAN', ve.outputs["Distance"], 0.045))
    n = b.noise(b.pos, 0.3, 4, 0.6)
    c = b.mixc(c, dirt, b.math('MULTIPLY', b.math('GREATER_THAN', n.outputs["Fac"], 0.56), 0.55))
    m = b.noise(b.pos, 1.3, 3, 0.5)
    moss = b.math('MULTIPLY', b.math('LESS_THAN', ve.outputs["Distance"], 0.07), b.math('GREATER_THAN', m.outputs["Fac"], 0.6))
    c = b.mixc(c, "#3e4a2a", b.math('MULTIPLY', moss, 0.7))
    b.link(c, b.bsdf.inputs["Base Color"]); b.bsdf.inputs["Roughness"].default_value = 0.92
    return b

def mountain_mat(name, forest, clearing, rock, near, far, hmax, scale):
    """Forested slopes: dark clumps of trees (Voronoi), lighter clearings, rock showing on the steep upper parts."""
    b = NB(name)
    vo = b.n("ShaderNodeTexVoronoi"); vo.inputs["Scale"].default_value = scale * 8.0; vo.inputs["Randomness"].default_value = 1.0
    b.link(b.pos, vo.inputs["Vector"])
    n = b.noise(b.pos, scale, 5, 0.6)
    c = b.mixc(b.ramp(vo.outputs["Distance"], [(0.15, forest), (0.6, clearing)]), forest, b.math('MULTIPLY', n.outputs["Fac"], 0.5))
    sep = b.n("ShaderNodeSeparateXYZ"); b.link(b.normal, sep.inputs[0])
    st = b.n("ShaderNodeMapRange"); st.inputs["From Min"].default_value = 0.9; st.inputs["From Max"].default_value = 0.6
    b.link(sep.outputs[2], st.inputs[0])                     # steepness 0 (flat) .. 1 (steep), a soft blend
    c = b.mixc(c, rock, b.math('MULTIPLY', st.outputs[0], 0.65))
    b.link(c, b.bsdf.inputs["Base Color"]); b.bsdf.inputs["Roughness"].default_value = 0.95
    add_haze(b, V["haze"], near, far, hmax)
    return b

def leaves(name, dark, mid, light):
    """Foliage: small leaf cells in three greens, sunlit tips, a crisp bumpy surface."""
    b = NB(name)
    vo = b.n("ShaderNodeTexVoronoi"); vo.inputs["Scale"].default_value = 7.0; b.link(b.pos, vo.inputs["Vector"])
    n = b.noise(b.pos, 1.5, 4, 0.6)
    c = b.ramp(vo.outputs["Distance"], [(0.05, light), (0.35, mid), (0.75, dark)])
    c = b.mixc(c, dark, b.math('MULTIPLY', n.outputs["Fac"], 0.45))
    b.link(c, b.bsdf.inputs["Base Color"]); b.bsdf.inputs["Roughness"].default_value = 0.7
    b.bsdf.inputs["Subsurface Weight"].default_value = 0.08
    bump = b.n("ShaderNodeBump"); bump.inputs["Strength"].default_value = 0.6
    b.link(vo.outputs["Distance"], bump.inputs["Height"]); b.link(bump.outputs[0], b.bsdf.inputs["Normal"])
    return b

def finish_materials():
    """A detail pass over every surface material: softly rounded edges (Bevel normal, baked into the light),
    fine surface bump, slight roughness variation. Cards and emissive materials are left alone."""
    for name, m in MATS.items():
        nt = m.node_tree
        bsdf = next((n for n in nt.nodes if n.type == 'BSDF_PRINCIPLED'), None)
        if bsdf is None or name.startswith("Stand") or name == "FloorCobble":
            continue
        geo = nt.nodes.new("ShaderNodeNewGeometry")
        bev = nt.nodes.new("ShaderNodeBevel"); bev.samples = 6
        bev.inputs["Radius"].default_value = 0.012 if name in ("Iron", "LampGlass") else 0.035
        fine = nt.nodes.new("ShaderNodeTexNoise"); fine.inputs["Scale"].default_value = 22.0; fine.inputs["Detail"].default_value = 4.0
        nt.links.new(geo.outputs["Position"], fine.inputs["Vector"])
        nrm = bsdf.inputs["Normal"]
        if nrm.links:                                   # an existing bump: feed it the bevelled normal
            bp = nrm.links[0].from_node
            if "Normal" in bp.inputs and not bp.inputs["Normal"].links:
                nt.links.new(bev.outputs["Normal"], bp.inputs["Normal"])
        else:
            bp = nt.nodes.new("ShaderNodeBump"); bp.inputs["Strength"].default_value = 0.12; bp.inputs["Distance"].default_value = 0.02
            nt.links.new(fine.outputs["Fac"], bp.inputs["Height"]); nt.links.new(bev.outputs["Normal"], bp.inputs["Normal"])
            nt.links.new(bp.outputs[0], nrm)
        if not bsdf.inputs["Roughness"].links:          # roughness variation
            r0 = bsdf.inputs["Roughness"].default_value
            mr = nt.nodes.new("ShaderNodeMapRange"); mr.inputs["To Min"].default_value = max(0.0, r0 - 0.12)
            mr.inputs["To Max"].default_value = min(1.0, r0 + 0.08)
            nt.links.new(fine.outputs["Fac"], mr.inputs[0]); nt.links.new(mr.outputs[0], bsdf.inputs["Roughness"])

def emit_solid(name, color, strength):
    b = NB(name)
    em = b.n("ShaderNodeEmission"); em.inputs["Color"].default_value = (*srgb(color), 1); em.inputs["Strength"].default_value = strength
    b.link(em.outputs[0], b.out.inputs[0])
    return b

def add_soot(mname, amount=0.45, scale=0.3):
    """Blotchy soot / burn marks layered over an existing material's base colour (burning variant)."""
    m = MATS[mname]; nt = m.node_tree
    bsdf = next((n for n in nt.nodes if n.type == 'BSDF_PRINCIPLED'), None)
    if bsdf is None:
        return
    sock = bsdf.inputs["Base Color"]
    if not sock.links:
        return
    src = sock.links[0].from_socket
    geo = nt.nodes.new("ShaderNodeNewGeometry")
    nz = nt.nodes.new("ShaderNodeTexNoise"); nz.inputs["Scale"].default_value = scale; nz.inputs["Detail"].default_value = 4.0
    nt.links.new(geo.outputs["Position"], nz.inputs["Vector"])
    gt = nt.nodes.new("ShaderNodeMapRange"); gt.inputs["From Min"].default_value = 1.0 - amount * 0.6
    gt.inputs["From Max"].default_value = 1.0 - amount * 0.6 + 0.08
    nt.links.new(nz.outputs["Fac"], gt.inputs[0])
    mix = nt.nodes.new("ShaderNodeMix"); mix.data_type = 'RGBA'; mix.blend_type = 'MIX'
    nt.links.new(gt.outputs[0], mix.inputs[0]); nt.links.new(src, mix.inputs[6])
    mix.inputs[7].default_value = (*srgb("#1a1614"), 1)
    nt.links.new(mix.outputs[2], sock)

def build_materials():
    wood_material("Planks", "#3a2c24", "#5e4a3a")                       # the dark weathered boards of the shopfronts
    wood_material("PlanksLight", "#5e4b3a", "#88705a")                  # crates, counters, barrels (weathered)
    wood_material("PlanksGrey", "#5c5e54", "#7e7e6e")                   # the barns, old sheds
    wood_material("PlanksTeal", "#3c524e", "#56706a")                   # the inn's painted boards
    wood_material("Beam", "#4a3424", "#74563c", 4.0, vertical=False)
    wood_material("BeamDark", "#2a1e18", "#4a3628", 4.0, vertical=False)
    wood_material("Timber", "#7a5a3a", "#a07a50", 4.0, vertical=False, scorch=0.3 if BURN else 0.0)   # new timber of the frame
    wood_material("Charred", "#141010", "#2e2420", 4.0, vertical=False, rough=0.9, scorch=0.0)
    roof_material("Roof", "#a4563c", "#8c4632")                         # faded tiles
    roof_material("RoofOld", "#8e4a34", "#7a3e2c")
    stone_material("StoneMoss", "#6a6e5a", "#8e9078", 0.35)
    stone_material("StoneLight", "#827c70", "#a09888", 0.16)                   # weathered, mossy
    stone_material("StoneArch", "#7a7a66", "#9c9a82", 0.4)
    brick_material("Brick", "#8a4a36", "#7a3e2e", "#5a4a40")
    brick_material("BrickWell", "#8c8478", "#a59c8c", "#4e463e", 0.22, 0.09)
    plain("RedStone", "#8a2a20", "#b0402c", 4.0, 0.6)
    plain("Iron", "#15161a", "#2a2c32", 6.0, 0.45, 0.4)
    plain("BenchRed", "#8a2a1e", "#b23a26", 8.0, 0.6)
    plain("TrimGreen", "#2e4a3c", "#3e5e4c", 6.0, 0.7)
    plain("TrimCream", "#c8bca0", "#ddd2b8", 6.0, 0.7)
    plain("SignWood", "#6a5038", "#8a6a4a", 3.0, 0.8)
    plain("SignPaint", "#b2aa96", "#c2baa6", 6.0, 0.8)
    plain("Leaf", "#2e4a1e", "#4f7a2e", 9.0, 0.8)
    leaves("TreeLeaf", "#24421c", "#3e6a28", "#6a9a3a")
    leaves("TreeLeaf2", "#2e4c1a", "#507a26", "#86aa40")
    leaves("TreeLeaf3", "#1e3a22", "#365e30", "#5a8a44")
    plain("Bark", "#3a2c20", "#54402c", 5.0, 0.8)
    plain("FlowerRed", "#b0202a", "#e04048", 20.0, 0.7)
    plain("FlowerWhite", "#c8c4b8", "#f2efe6", 20.0, 0.7)
    plain("FlowerPink", "#b04a8a", "#e07ab8", 20.0, 0.7)
    plain("FlowerYellow", "#c8a020", "#f0d050", 20.0, 0.7)
    plain("Dirt", "#4a3e30", "#6a5a46", 3.0, 0.95)
    plain("Water", "#0a0e12", "#1a2228", 2.0, 0.1)
    plain("Rubble", "#4e4640", "#7a7064", 5.0, 0.9)
    plain("Sack", "#b49a68", "#d2b884", 6.0, 0.9)
    plain("Hay", "#b8903e", "#dcbc6a", 8.0, 0.9)
    plain("Apple", "#9a1e1e", "#c8342a", 30.0, 0.5)
    plain("Cabbage", "#4e7a2a", "#7aa242", 30.0, 0.7)
    plain("Orange", "#c86a1e", "#e8962e", 30.0, 0.5)
    plain("Bread", "#9a6228", "#c48a44", 20.0, 0.8)
    plain("Pottery", "#b8b0a0", "#e0d8c8", 10.0, 0.4)
    plain("ClothViolet", "#5a3a6a", "#7a5a8a", 8.0, 0.9)
    plain("ClothTeal", "#2a6a6a", "#3a8a84", 8.0, 0.9)
    stripes("StripeRedX", "#ead8b4", "#b8442e", 0.42, 'x')
    stripes("StripeRedZ", "#ead8b4", "#b8442e", 0.42, 'z')
    stripes("StripeBlueX", "#e6dcc0", "#3a6a96", 0.42, 'x')
    stripes("StripeBlueZ", "#e6dcc0", "#3a6a96", 0.42, 'z')
    stripes("StripeTealX", "#e2dcb8", "#2e7a70", 0.5, 'x')
    stripes("AwningZ", "#2c5a8a", "#e0b040", 0.5, 'z')                 # the general store's blue and yellow awning
    stripes("AwningX", "#2c5a8a", "#e0b040", 0.5, 'x')                 # the inn's
    stripes("CurtainX", "#eae6d4", "#5a86b0", 0.32, 'x')               # the gateway's hanging curtains
    land("Land")
    hazed("Mountain", "#4a6a58", "#6a8a70", 280, 900, 0.75, 0.02)
    mountain_mat("MtnNear", "#24422a", "#44663a", "#6e7a5a", 60, 480, 0.36, 0.06)       # forested green foothills
    mountain_mat("MtnMid", "#2a4a50", "#46685e", "#70868a", 100, 760, 0.5, 0.035)
    mountain_mat("MtnFar", "#3e5a78", "#5a7898", "#9aa8b8", 200, 1100, 0.58, 0.02)      # blue peaks far off
    hazed("FarSlate", "#4a5260", "#5e6674", 60, 420, 0.6, 3.0)
    hazed("FarThatch", "#9a8450", "#b49a60", 60, 420, 0.6, 4.0)
    roof_material("RoofSlate", "#4e5866", "#5c6676")
    plain("Plaster", "#c2b69c", "#d4c9b0", 1.6, 0.85)                  # grimy, weathered plaster
    stone_material("StoneStep", "#8c8676", "#ada595", 0.25)
    stone_material("StoneNose", "#8c8474", "#a69e8c", 0.14)                     # the dressed nosings of the steps: worn, dirty
    worn_paving("CourtPaving", "#6e665a", "#8e8474", "#463f36", "#5a4e3e")      # the courtyard: worn flags, dirt, moss
    brick_material("StepField", "#625d52", "#7a7468", "#45413a", 0.34, 0.24)       # the treads: small setts
    brick_material("Fieldstone", "#7e7a6c", "#9a9484", "#4e4a42", 0.6, 0.32)
    market_ground("MarketGround")
    hazed("FarWall", "#b0a692", "#c2b8a4", 60, 420, 0.65, 2.0)                 # cream plaster
    hazed("FarRoof", "#94503a", "#a45c42", 60, 420, 0.65, 3.0)                 # terracotta
    hazed("FarBarn", "#6a6c60", "#848474", 50, 400, 0.6, 2.0)
    hazed("Forest", "#24421f", "#36582a", 60, 480, 0.68, 0.4)
    hazed("Mill", "#bcb29e", "#ccc2ae", 60, 480, 0.6, 2.0)
    plain("Soot", "#0c0a0a", "#1c1716", 3.0, 0.95)
    for mname, amt in (("StoneLight", 0.26), ("StoneNose", 0.26), ("StoneStep", 0.22), ("StoneArch", 0.22), ("StoneMoss", 0.18),
                       ("Fieldstone", 0.26), ("BrickWell", 0.22), ("Brick", 0.18), ("StepField", 0.2), ("Plaster", 0.3),
                       ("TrimCream", 0.28), ("SignPaint", 0.28), ("PlanksLight", 0.14), ("PlanksGrey", 0.14), ("FarWall", 0.26),
                       ("Mill", 0.3), ("AwningZ", 0.2), ("AwningX", 0.2), ("StripeRedX", 0.2), ("StripeRedZ", 0.2),
                       ("StripeBlueX", 0.2), ("StripeBlueZ", 0.2), ("StripeTealX", 0.2)):
        add_weathering(mname, amt)                      # the town is old and the market has been wrecked: grime on everything
    if BURN:
        for mname, amt in (("StoneMoss", 0.4), ("StoneLight", 0.35), ("StoneArch", 0.35), ("Brick", 0.5), ("BrickWell", 0.3),
                           ("Roof", 0.5), ("RoofOld", 0.55), ("BenchRed", 0.4), ("Rubble", 0.3), ("TrimCream", 0.45),
                           ("TrimGreen", 0.4), ("SignWood", 0.5), ("StripeRedX", 0.55), ("StripeRedZ", 0.55),
                           ("StripeBlueX", 0.55), ("StripeBlueZ", 0.55), ("StripeTealX", 0.55), ("AwningZ", 0.45),
                           ("AwningX", 0.45), ("CurtainX", 0.5), ("FarWall", 0.5), ("FarRoof", 0.5), ("FarBarn", 0.5)):
            add_soot(mname, amt)
    emit_solid("LampGlass", "#ffc27a", V["lamp_glow"])
    emit_solid("WindowCard", V["window_color"], V["window_glow"])
    for nm in ("FireCard", "SmokeCard", "BuntingCard", "CrowdCard", "SailsCard", "GrassCard"):
        emit_solid(nm, "#808080", 0.0)
    b = NB("SkyCard")
    sep = b.n("ShaderNodeSeparateXYZ"); b.link(b.uv, sep.inputs[0])
    em = b.n("ShaderNodeEmission"); em.inputs["Strength"].default_value = V["sky_strength"]
    b.link(b.ramp(sep.outputs[1], V["sky"]), em.inputs["Color"]); b.link(em.outputs[0], b.out.inputs[0])
    b = NB("FloorCobble")                       # light map only: a flat average stone colour
    b.bsdf.inputs["Base Color"].default_value = (*srgb("#8f8476"), 1); b.bsdf.inputs["Roughness"].default_value = 0.8
    b = NB("Stand_P1"); b.bsdf.inputs["Base Color"].default_value = (*srgb("#2d6cdf"), 1)
    b = NB("Stand_P2"); b.bsdf.inputs["Base Color"].default_value = (*srgb("#e0463a"), 1)
    finish_materials()

# ======================================================================
#  small shape helpers
# ======================================================================
WINDOWS = []     # (x, y, z, area) - window lights (burning: fire inside)
LAMPS = []       # (x, z, h) standing lamps
FIRES = []       # (x, y, z, size) flames (burning)
SMOKES = []      # (x, y, z, size) smoke columns (burning; a few thin ones from chimneys by day)
CROWD = []       # (x, y, z, height, pose, seed)

def smoothstep(a, b, x):
    t = min(max((x - a) / (b - a), 0.0), 1.0)
    return t * t * (3 - 2 * t)

def hcyl(g, p0, p1, r, m, seg=10, r2=None):
    """Capped cylinder (or cone, r2) between two Godot points."""
    gg = grp(g) if isinstance(g, str) else g
    A, B = G(*p0), G(*p1); d = B - A
    q = d.normalized().to_track_quat('Z', 'Y')
    M = Matrix.Translation((A + B) / 2) @ q.to_matrix().to_4x4()
    res = bmesh.ops.create_cone(gg.bm, cap_ends=True, cap_tris=False, segments=seg, radius1=r, radius2=r if r2 is None else r2,
                                depth=d.length, matrix=M)
    _tag(gg, list({f for v in res["verts"] for f in v.link_faces}), m)

def ico(g, c, r, m, seed, sy=0.85, sub=1):
    gg = grp(g) if isinstance(g, str) else g
    rnd = random.Random(seed)
    M = Matrix.Translation(G(*c)) @ Matrix.Diagonal((r, r, r * sy, 1.0))
    res = bmesh.ops.create_icosphere(gg.bm, subdivisions=sub, radius=1.0, matrix=M)
    cc = G(*c)
    for v in res["verts"]:
        v.co = cc + (v.co - cc) * rnd.uniform(0.86, 1.12)
    _tag(gg, list({f for v in res["verts"] for f in v.link_faces}), m)

def rock(g, x, y, z, sx, sy, sz, seed, m="Rubble", sub=1, jag=0.25):
    gg = grp(g) if isinstance(g, str) else g
    rnd = random.Random(seed)
    M = Matrix.Translation(G(x, y, z)) @ Matrix.Rotation(rnd.uniform(0, 6.28), 4, 'Z') @ Matrix.Diagonal((sx, sz, sy, 1.0))
    r = bmesh.ops.create_icosphere(gg.bm, subdivisions=sub, radius=1.0, matrix=M)
    c = G(x, y, z)
    for v in r["verts"]:
        v.co = c + (v.co - c) * rnd.uniform(1 - jag, 1 + jag * 0.5)
    _tag(gg, list({f for v in r["verts"] for f in v.link_faces}), m)

def slab(g, p0, p1, p2, p3, t, m):
    """A thin slab through four Godot points (a sloped awning or a roof panel), t thick (pushed up)."""
    hexa(g, [p0, p1, p2, p3] + [(p[0], p[1] + t, p[2]) for p in (p0, p1, p2, p3)], m)

def bench(x, z, rot=0.0, broken=False):
    g = "CE_Props"; ca, sa = math.cos(math.radians(rot)), math.sin(math.radians(rot))
    if broken:      # snapped in the middle: one half on the ground
        obox(g, (x - 0.55 * ca, 0.45, z + 0.55 * sa), (1.1, 0.08, 0.55), rot, "BenchRed", 0.01)
        obox(g, (x + 0.6 * ca, 0.2, z - 0.6 * sa), (1.1, 0.08, 0.55), rot + 14, "BenchRed", 0.01)
        obox(g, (x - 0.55 * ca, 0.85, z + 0.55 * sa - 0.25), (1.1, 0.5, 0.06), rot, "BenchRed", 0.01)
        obox(g, (x - 0.95 * ca, 0.22, z + 0.95 * sa), (0.06, 0.44, 0.5), rot, "Iron")
        return
    obox(g, (x, 0.45, z), (2.2, 0.08, 0.55), rot, "BenchRed", 0.01)
    obox(g, (x + 0.25 * sa, 0.85, z - 0.25 * ca), (2.2, 0.5, 0.06), rot, "BenchRed", 0.01)
    for sx in (-0.95, 0.95):
        obox(g, (x + sx * ca, 0.22, z - sx * sa), (0.06, 0.44, 0.5), rot, "Iron")

def planter(x, z, w=2.0, d=0.8, h=0.6, seed=0, smashed=False):
    g = "CE_Props"; rnd = random.Random(seed)
    box(g, x, -0.1, h, z, w, d, "PlanksLight" if not smashed else "Charred", 0.02)
    box(g, x, h - 0.05, h + 0.06, z, w * 0.94, d * 0.86, "Dirt")
    for k in range(int(w * 9)):
        fx = x + rnd.uniform(-w / 2 + 0.15, w / 2 - 0.15); fz = z + rnd.uniform(-d / 2 + 0.12, d / 2 - 0.12)
        leaf_y = h + rnd.uniform(0.05, 0.25)
        if smashed and rnd.random() < 0.6:
            continue
        rock(g, fx, leaf_y, fz, 0.16, 0.12, 0.16, rnd.randint(0, 9999), "Leaf")
        if rnd.random() < 0.6 and not smashed:
            rock(g, fx + rnd.uniform(-0.05, 0.05), leaf_y + 0.12, fz, 0.07, 0.05, 0.07, rnd.randint(0, 9999),
                 rnd.choice(("FlowerRed", "FlowerRed", "FlowerWhite", "FlowerPink", "FlowerYellow")))

def barrel(x, z, s=1.0, g="CE_Props"):
    cyl(g, x, -0.05, z, 0.36 * s, 0.4 * s, 0.5 * s, "PlanksLight", 12)
    cyl(g, x, 0.45 * s, z, 0.4 * s, 0.36 * s, 0.5 * s, "PlanksLight", 12)
    for y in (0.15, 0.48, 0.82):
        cyl(g, x, y * s, z, 0.415 * s, 0.415 * s, 0.05 * s, "Iron", 12)

def crate(x, y, z, s=0.6, rot=0.0, m="PlanksLight", g="CE_Props"):
    obox(g, (x, y + s / 2, z), (s, s, s), rot, m, 0.02)
    obox(g, (x, y + s / 2, z), (s * 1.02, s * 0.12, s * 1.02), rot, "Beam")

def sack(x, z, seed, g="CE_Props"):
    rnd = random.Random(seed)
    rock(g, x, 0.3, z, 0.32, 0.32, 0.26, seed, "Sack", 2, 0.08)
    rock(g, x + rnd.uniform(-0.05, 0.05), 0.62, z, 0.14, 0.1, 0.12, seed + 1, "Sack", 1, 0.1)

def lamp(x, z, h, fallen=False, fall=1):
    g = "CE_Props"
    if fallen:      # knocked over, lying across the stones toward +x (fall=1) or -x (fall=-1)
        hcyl(g, (x, 0.15, z), (x + fall * (h - 0.6), 0.18, z + 0.3), 0.07, "Iron", 8)
        box(g, x, -0.05, 0.4, z, 0.4, 0.4, "Iron")
        obox(g, (x + fall * (h - 0.35), 0.22, z + 0.32), (0.4, 0.36, 0.36), 14, "Iron")          # its glass broken, unlit
        return
    cyl(g, x, -0.05, z, 0.2, 0.16, 0.5, "Iron", 8)
    cyl(g, x, 0.45, z, 0.08, 0.06, h - 0.9, "Iron", 8)
    box(g, x, h - 0.5, h - 0.42, z, 0.5, 0.5, "Iron")
    box(g, x, h - 0.42, h + 0.15, z, 0.36, 0.36, "LampGlass")
    cyl(g, x, h + 0.15, z, 0.33, 0.05, 0.3, "Iron", 4, 45)
    cyl(g, x, h + 0.45, z, 0.05, 0.05, 0.15, "Iron", 6)
    LAMPS.append((x, z, h))

def fence(x0, z0, x1, z1, h=1.0, posts=None, m="Beam", g="CE_Props", broken=()):
    L = math.hypot(x1 - x0, z1 - z0); n = posts or max(2, int(L / 1.8) + 1)
    for k in range(n):
        t = k / (n - 1); x, z = x0 + (x1 - x0) * t, z0 + (z1 - z0) * t
        box(g, x, -0.1, h + 0.12, z, 0.18, 0.18, m, 0.02)
        cyl(g, x, h + 0.12, z, 0.13, 0.0, 0.16, m, 4, 45)
    for k in range(n - 1):
        if k in broken:
            continue
        t0, t1 = k / (n - 1), (k + 1) / (n - 1)
        a = (x0 + (x1 - x0) * t0, z0 + (z1 - z0) * t0); b = (x0 + (x1 - x0) * t1, z0 + (z1 - z0) * t1)
        for y in (h * 0.42, h * 0.85):
            beam(g, (a[0], y, a[1]), (b[0], y, b[1]), 0.09, 0.16, m)

def rubble_pile(x, z, r, n, seed, mats=("Rubble", "Rubble", "Brick", "Charred", "Roof")):
    """A heap of broken stone, brick, tiles and burnt timber, highest in the middle."""
    g = "CE_Props"; rnd = random.Random(seed)
    for k in range(n):
        a = rnd.uniform(0, 6.283); d = r * math.sqrt(rnd.random())
        px, pz = x + d * math.cos(a), z + d * math.sin(a)
        h = (1 - d / r) * r * 0.45
        m = rnd.choice(mats)
        if m == "Charred" or (m == "Roof" and rnd.random() < 0.5):
            beam(g, (px, h * 0.5, pz), (px + rnd.uniform(-1.2, 1.2), h * 0.5 + rnd.uniform(-0.1, 0.5), pz + rnd.uniform(-1.2, 1.2)),
                 rnd.uniform(0.12, 0.25), rnd.uniform(0.1, 0.2), m)
        else:
            s = rnd.uniform(0.18, 0.45)
            rock(g, px, h * 0.7, pz, s * rnd.uniform(0.8, 1.4), s * rnd.uniform(0.5, 0.9), s, rnd.randint(0, 99999), m)

def burnt_hole(g, x, y0, y1, z, w, seed, face=1, axis='z'):
    """A ragged burnt-through hole in a wall facing +z (axis 'z', face 1) or +-x (axis 'x'): black recess,
    charred plank ends around it. Burning only."""
    rnd = random.Random(seed)
    n = max(2, int(w / 0.22))
    if axis == 'z':
        box(g, x, y0, y1, z + face * 0.04, w, 0.06, "Soot")
    else:
        box(g, x + face * 0.04, y0, y1, z, 0.06, w, "Soot")
    for k in range(n):
        t = -w / 2 + (k + 0.5) * w / n
        top = y1 + rnd.uniform(-0.4, 0.5); bot = y0 + rnd.uniform(-0.4, 0.4)
        for (ya, yb) in ((top - rnd.uniform(0.1, 0.5), top), (bot, bot + rnd.uniform(0.1, 0.4))):
            if axis == 'z':
                box(g, x + t, ya, yb, z + face * 0.08, w / n * 0.9, 0.07, "Charred")
            else:
                box(g, x + face * 0.08, ya, yb, z + t, 0.07, w / n * 0.9, "Charred")

# ======================================================================
#  the plaza floor, the well and the arch
# ======================================================================
def build_floor():
    g = grp("CE_Floor")
    quad(g, [(-FLOOR_X, 0, FLOOR_FRONT), (FLOOR_X, 0, FLOOR_FRONT), (FLOOR_X, 0, FLOOR_BACK), (-FLOOR_X, 0, FLOOR_BACK)],
         [(-FLOOR_X, -FLOOR_FRONT), (FLOOR_X, -FLOOR_FRONT), (FLOOR_X, -FLOOR_BACK), (-FLOOR_X, -FLOOR_BACK)], "FloorCobble")

def voussoir(gg, wx, wz, a0, a1, r_in, r_out, hz, m):
    bm = gg.bm
    pts = []
    for (a, r) in ((a0, r_out), (a1, r_out), (a1, r_in), (a0, r_in)):
        c, s_ = -math.cos(a), math.sin(a)
        pts.append((wx + r * c, ARCH_SPRING + r * s_))
    vs = [bm.verts.new(G(x, y, wz + dz)) for dz in (hz, -hz) for (x, y) in pts]
    f, bk = vs[:4], vs[4:]
    faces = [bm.faces.new(f), bm.faces.new(bk[::-1])]
    for i in range(4):
        j = (i + 1) % 4
        faces.append(bm.faces.new((f[j], f[i], bk[i], bk[j])))
    bmesh.ops.recalc_face_normals(bm, faces=faces)
    _tag(gg, faces, m)

def arch_band(g, wx, wz, a0, a1, segs, m="StoneArch"):
    """The arch ring built of separate wedge-shaped stones (voussoirs) with thin joints, each a little different,
    and a projecting keystone; between angles a0..a1 (0 = left springing, pi = right)."""
    gg = grp(g); rnd = random.Random(17)
    n = 13
    for i in range(n):
        b0, b1 = math.pi * i / n, math.pi * (i + 1) / n
        if b1 < a0 - 1e-6 or b0 > a1 + 1e-6:
            continue
        j = 0.012
        key = i == n // 2
        S = ARCH_S
        r_in = ARCH_HALF - 0.27 * S + rnd.uniform(-0.015, 0.015)
        r_out = ARCH_HALF + 0.25 * S + rnd.uniform(-0.03, 0.04) + (0.12 * S if key else 0.0)
        hz = 0.27 * S + rnd.uniform(-0.012, 0.012) + (0.04 * S if key else 0.0)
        voussoir(gg, wx, wz, b0 + j, b1 - j, r_in, r_out, hz, "StoneArch" if rnd.random() > 0.25 else "StoneMoss")
    # the extrados course: a thin moulding over the ring
    for i in range(n * 2):
        b0, b1 = math.pi * i / (2 * n), math.pi * (i + 1) / (2 * n)
        if b1 > a1 + 1e-6:
            break
        voussoir(gg, wx, wz, b0, b1, ARCH_HALF + 0.27 * ARCH_S, ARCH_HALF + 0.34 * ARCH_S, 0.2 * ARCH_S, "StoneLight")

def pier(g, x, wz, top, broken=False, s=1.0):
    """A pier of dressed stone blocks: a stepped plinth, courses with slightly uneven edges, an impost block."""
    rnd = random.Random(int(x * 100))
    box(g, x, -0.2, 0.22 * s, wz, 0.9 * s, 0.9 * s, "StoneLight", 0.05)
    box(g, x, 0.22 * s, 0.46 * s, wz, 0.74 * s, 0.74 * s, "StoneLight", 0.04)
    y = 0.46 * s; k = 0
    while y < top - 0.05:
        h = min(rnd.uniform(0.34, 0.46) * s, top - y)
        w = (0.58 + rnd.uniform(-0.02, 0.02)) * s
        box(g, x + rnd.uniform(-0.01, 0.01), y + 0.008, y + h - 0.008, wz, w, w, "StoneArch" if k % 3 else "StoneMoss", 0.035)
        y += h; k += 1
    if not broken:
        box(g, x, top - 0.02, top + 0.16 * s, wz, 0.72 * s, 0.72 * s, "StoneLight", 0.04)          # the impost

# ======================================================================
#  the left side: the general store (intact, detailed half-timbering), houses behind it, a big tree in front
# ======================================================================
def half_timber_x(g, x, z0, z1, y0, y1, s=1, bay=1.8, seed=0):
    """A timber frame over a plaster wall facing +x (s=1) or -x (s=-1): posts, rails and braces, slightly proud."""
    rnd = random.Random(seed)
    n = max(1, int(round((z1 - z0) / bay)))
    xo = x + s * 0.06
    for k in range(n + 1):
        z = z0 + (z1 - z0) * k / n
        box(g, xo, y0, y1, z, 0.14, 0.2, "Beam", 0.02)
    for y in (y0, (y0 + y1) / 2 if y1 - y0 > 2.6 else None, y1):
        if y is not None:
            box(g, xo, y - 0.09, y + 0.09, (z0 + z1) / 2, 0.14, z1 - z0 + 0.2, "Beam", 0.02)
    for k in range(n):
        za, zb = z0 + (z1 - z0) * k / n, z0 + (z1 - z0) * (k + 1) / n
        if rnd.random() < 0.6:
            a, b = ((za, y0), (zb, y1)) if k % 2 == 0 else ((zb, y0), (za, y1))
            beam(g, (xo, a[1] + 0.1, a[0]), (xo, b[1] - 0.1, b[0]), 0.12, 0.16, "Beam")

def half_timber_z(g, z, x0, x1, y0, y1, bay=1.8, seed=0):
    """The same on a wall facing +z."""
    rnd = random.Random(seed)
    n = max(1, int(round((x1 - x0) / bay)))
    zo = z + 0.06
    for k in range(n + 1):
        x = x0 + (x1 - x0) * k / n
        box(g, x, y0, y1, zo, 0.2, 0.14, "Beam", 0.02)
    for y in (y0, y1):
        box(g, (x0 + x1) / 2, y - 0.09, y + 0.09, zo, x1 - x0 + 0.2, 0.14, "Beam", 0.02)
    for k in range(n):
        xa, xb = x0 + (x1 - x0) * k / n, x0 + (x1 - x0) * (k + 1) / n
        if rnd.random() < 0.7:
            a, b = ((xa, y0), (xb, y1)) if k % 2 == 0 else ((xb, y0), (xa, y1))
            beam(g, (a[0], a[1] + 0.1, zo), (b[0], b[1] - 0.1, zo), 0.16, 0.12, "Beam")

def shutters_x(g, x, y, z, w, h, s=1):
    for d in (-1, 1):
        box(g, x + s * 0.08, y, y + h, z + d * (w / 2 + 0.28), 0.06, 0.5, "TrimGreen", 0.01)

def flower_box_x(g, x, y, z, w, s=1, seed=0):
    rnd = random.Random(seed)
    box(g, x + s * 0.2, y - 0.3, y - 0.05, z, 0.3, w + 0.1, "PlanksLight", 0.01)
    for k in range(int(w * 5)):
        zz = z - w / 2 + (k + 0.5) * w / int(w * 5)
        ico(g, (x + s * 0.2, y + 0.02, zz), 0.12, "Leaf", seed + k, 0.8)
        ico(g, (x + s * 0.24, y + 0.12, zz + rnd.uniform(-0.05, 0.05)), 0.07, rnd.choice(("FlowerRed", "FlowerRed", "FlowerPink", "FlowerWhite")), seed + 50 + k, 0.9)

def build_left():
    g = "CE_Buildings"
    # --- the general store: stone footing, plank ground floor, half-timbered plaster upper floor, tiled roof ---
    cx, cz, wx, wz = -15.8, -18.0, 8.0, 11.0
    xf = cx + wx / 2                                                  # the front wall, x = -11.8
    H, RISE = 4.6, 2.1
    gable_house(g, cx, cz, wx, wz, H, RISE, "Plaster", "RoofOld", ridge_z=True, broken=0.4 if BURN else 0.28, seed=3,
                rafter="Charred" if BURN else "Beam")                     # the front of the roof has come down
    box(g, cx, -0.2, 0.55, cz, wx + 0.3, wz + 0.3, "StoneLight", 0.05)                             # stone footing
    box(g, xf + 0.05, 0.55, 2.45, cz, 0.1, wz - 0.3, "Planks")                                      # plank ground floor
    box(g, cx, 0.55, 2.45, cz + wz / 2 + 0.05, wx - 0.3, 0.1, "Planks")
    half_timber_x(g, xf, cz - wz / 2 + 0.15, cz + wz / 2 - 0.15, 2.45, H - 0.1, 1, 1.8, 5)
    half_timber_z(g, cz + wz / 2, cx - wx / 2 + 0.15, cx + wx / 2 - 0.15, 2.45, H - 0.1, 1.6, 6)
    box(g, xf + 0.95, -0.1, 0.4, cz, 1.9, wz + 0.6, "PlanksLight")                                  # the porch deck
    for k in range(9):
        box(g, xf + 1.9, 0.38, 0.42, cz - wz / 2 - 0.1 + k * (wz + 0.2) / 8, 0.1, 0.1, "BeamDark")
    box(g, xf + 2.05, -0.1, 0.2, cz, 0.35, 2.0, "PlanksLight")
    for z in (-23.3, -19.8, -12.7):                                    # (the post at z -16.2 has been knocked down)
        box(g, xf + 1.75, 0.4, 3.0, z, 0.18, 0.18, "Beam", 0.02)
        for d in (-1, 1):                                                                               # brackets
            beam(g, (xf + 1.75, 2.5, z), (xf + 1.75, 2.95, z + d * 0.45), 0.08, 0.1, "Beam")
    box(g, xf + 1.75, 2.9, 3.05, cz, 0.16, wz + 0.4, "Beam")
    # the awning is torn: the back half still hangs from the rail, the front half has dropped onto the porch
    slab(g, (xf, 3.45, -23.7), (xf, 3.45, -18.6), (xf + 2.0, 3.0, -18.6), (xf + 2.0, 3.0, -23.7), 0.07, "AwningZ")
    slab(g, (xf, 3.45, -18.4), (xf, 3.45, -12.3), (xf + 1.3, 1.4, -13.0), (xf + 1.3, 1.6, -18.4), 0.07, "AwningZ")
    beam(g, (xf + 1.75, 0.4, -16.2), (xf + 2.6, 0.1, -14.0), 0.18, 0.18, "Charred" if BURN else "Beam")       # a porch post knocked down
    box(g, xf + 0.1, 0.4, 2.3, cz, 0.08, 1.4, "BeamDark")                                               # the door, its frame
    box(g, xf + 0.13, 2.3, 2.45, cz, 0.12, 1.7, "Beam")
    for d in (-1, 1):
        box(g, xf + 0.13, 0.4, 2.3, cz + d * 0.75, 0.12, 0.12, "Beam")
    for z in (-21.4, -14.6):
        window(g, xf + 0.06, 1.0, z, 1.5, 1.2, face_z=False, s=1)
        box(g, xf + 0.25, 0.85, 0.95, z, 0.32, 1.8, "Beam")                                            # sill
        window(g, xf + 0.06, 3.15, z, 1.0, 0.9, face_z=False, s=1)
        shutters_x(g, xf + 0.06, 3.1, z, 1.0, 1.0)
        flower_box_x(g, xf + 0.06, 3.1, z, 1.1, 1, int(-z * 10))
    # hanging sign on an iron bracket at the front corner (Ref 8)
    bz = cz + wz / 2 - 0.2
    box(g, xf + 1.0, 3.55, 3.62, bz, 1.6, 0.06, "Iron")
    for k in range(2):
        box(g, xf + 0.6 + k * 0.8, 3.0, 3.55, bz, 0.03, 0.03, "Iron")
    box(g, xf + 1.0, 2.35, 3.05, bz, 1.1, 0.08, "SignWood", 0.02)
    box(g, xf + 1.0, 2.45, 2.95, bz + 0.05, 0.9, 0.02, "SignPaint")
    window(g, cx - 1.9, 1.1, cz + wz / 2 + 0.06, 1.2, 1.2)
    window(g, cx + 1.9, 1.1, cz + wz / 2 + 0.06, 1.2, 1.2)
    window(g, cx, 3.2, cz + wz / 2 + 0.06, 1.0, 0.9)
    window(g, cx, 5.0, cz + wz / 2, 0.6, 0.6)
    box(g, cx - 2.6, 4.6, 7.6, cz - 2.0, 0.8, 0.8, "Brick")
    box(g, cx - 2.6, 7.6, 7.75, cz - 2.0, 0.95, 0.95, "StoneLight")
    if BURN:
        burnt_hole(g, xf + 0.07, 3.0, 4.4, -16.8, 1.6, 31, face=1, axis='x')
        burnt_hole(g, cx + 1.2, 2.6, 4.2, cz + wz / 2 + 0.06, 1.6, 32)
    else:
        SMOKES.append((cx - 2.6, 7.75, cz - 2.0, 0.7))
    # --- the house behind the store, its front facing the camera ---
    hx, hz = -23.2, -36.0
    gable_house(g, hx, hz, 12.0, 8.0, 4.4, 2.2, "Plaster", "RoofSlate", ridge_z=False, broken=0.55 if BURN else 0.35, seed=7,
                rafter="Charred" if BURN else "Beam")
    box(g, hx, -0.2, 0.5, hz, 12.3, 8.3, "StoneLight", 0.04)
    zf = hz + 4.0
    half_timber_z(g, zf, hx - 5.85, hx + 5.85, 0.5, 4.3, 2.0, 9)
    for x in (hx - 4.0, hx + 4.0):
        window(g, x, 1.2, zf + 0.06, 1.2, 1.3)
    window(g, hx, 2.6, zf + 0.06, 1.0, 1.0)
    box(g, hx - 2.0, 0.5, 2.5, zf + 0.12, 1.1, 0.1, "BeamDark")
    slab(g, (hx - 5.5, 2.9, zf + 0.1), (hx + 5.5, 2.9, zf + 0.1), (hx + 5.5, 2.45, zf + 1.5), (hx - 5.5, 2.45, zf + 1.5), 0.07, "StripeRedX")
    if BURN:
        burnt_hole(g, -19.0, 2.6, 4.2, zf + 0.06, 2.0, 33)
    # --- smaller houses far left ---
    gable_house(g, -31.0, -21.0, 8.0, 8.0, 4.0, 2.2, "Planks", "RoofOld", ridge_z=False, seed=8)
    for x in (-33.0, -29.0):
        window(g, x, 1.3, -17.0, 1.2, 1.3)
    gable_house(g, -28.0, -4.0, 7.0, 9.0, 4.0, 2.2, "PlanksGrey", "RoofOld", ridge_z=True, seed=9)
    window(g, -24.5, 1.3, -6.0, 1.2, 1.3, face_z=False, s=1)
    window(g, -24.5, 1.3, -1.6, 1.2, 1.3, face_z=False, s=1)

def tree(x, z, s=1.0, seed=0, g="CE_Props", burnt=False):
    rnd = random.Random(seed)
    hcyl(g, (x, -0.2, z), (x + 0.3 * s, 3.4 * s, z), 0.42 * s, "Bark", 9, 0.3 * s)
    for k in range(5):
        a = 2 * math.pi * k / 5 + rnd.uniform(-0.3, 0.3)
        p1 = (x + math.cos(a) * 2.2 * s, (4.6 + rnd.uniform(0, 1.6)) * s, z + math.sin(a) * 1.6 * s)
        hcyl(g, (x + 0.2 * s, 3.0 * s, z), p1, 0.16 * s, "Bark", 6, 0.08 * s)
    if burnt:
        return
    for k in range(120):                     # many small, jagged leaf clumps: a broken, textured silhouette
        a = rnd.uniform(0, 2 * math.pi); r = (rnd.random() ** 0.55) * 3.1 * s
        c = (x + r * math.cos(a), (rnd.uniform(4.4, 8.2) - r * 0.34) * s, z + r * math.sin(a) * 0.85)
        sz = rnd.uniform(0.32, 0.72) * s
        rock(g, *c, sz * rnd.uniform(0.8, 1.3), sz * rnd.uniform(0.6, 1.0), sz * rnd.uniform(0.8, 1.3), seed * 97 + k,
             rnd.choice(("TreeLeaf", "TreeLeaf", "TreeLeaf2", "TreeLeaf3")), 2, 0.45)

# ======================================================================
#  the right side: a timber house half torn open, under repair - exposed beams, scaffolding (Ref 8)
# ======================================================================
def build_right():
    g = "CE_Buildings"; rnd = random.Random(14)
    cx, cz, wx, wz = 16.0, -20.0, 9.0, 13.0
    xf = cx - wx / 2                                                   # the front wall, x = 11.5, faces -x
    z0, z1 = cz - wz / 2, cz + wz / 2
    FL, TOP, RIDGE = 3.0, 5.4, 7.6
    W = "Planks" if not BURN else "Charred"
    box(g, cx, -0.2, 0.5, cz, wx + 0.3, wz + 0.3, "StoneMoss", 0.05)                                 # stone footing
    # ground floor: plank walls; the front corner is broken open and boarded up with fresh planks
    box(g, cx + wx / 2 - 0.1, 0.5, FL, cz, 0.2, wz, W)                                               # back wall
    box(g, cx, 0.5, FL, z0 + 0.1, wx, 0.2, W)                                                        # far end wall
    box(g, xf + 0.1, 0.5, FL, cz - 2.2, 0.2, wz - 4.4, W)                                            # front wall (back part)
    box(g, cx + 1.0, 0.5, FL, z1 - 0.1, wx - 2.0, 0.2, W)                                            # near end wall, the corner gone
    for k in range(6):                                                                               # the boarded-up gap
        z = z1 - 0.4 - k * 0.42
        beam(g, (xf - 0.05, 0.6 + k * 0.05, z), (xf - 0.05, FL - 0.2 - k * 0.05, z - 0.3), 0.06, 0.38, "Timber")
    beam(g, (xf - 0.08, 0.8, z1 - 2.7), (xf - 0.08, 2.6, z1 - 0.2), 0.08, 0.2, "Timber")
    for zz in (z0 + 0.1, cz - 2.2, cz + 2.2, z1 - 0.1):                                             # posts
        box(g, xf + 0.1, 0.5, TOP, zz, 0.28, 0.28, "Beam", 0.02)
        box(g, cx + wx / 2 - 0.1, 0.5, TOP, zz, 0.28, 0.28, "Beam", 0.02)
    box(g, xf + 0.1, FL - 0.12, FL + 0.12, cz, 0.3, wz, "Beam")                                       # floor beam
    zc = z1 - 3.4                                                                                   # the near end has collapsed
    box(g, cx, FL - 0.08, FL + 0.06, (z0 + zc) / 2, wx - 0.3, zc - z0 - 0.15, "PlanksLight")          # the upper floor
    hexa(g, [(xf + 0.3, FL - 0.1, zc), (xf + 4.4, FL - 0.4, zc), (xf + 4.8, 0.35, z1 + 1.1), (xf + 0.2, 0.25, z1 + 0.9),
             (xf + 0.3, FL + 0.05, zc), (xf + 4.4, FL - 0.25, zc), (xf + 4.8, 0.5, z1 + 1.1), (xf + 0.2, 0.4, z1 + 0.9)], "PlanksLight" if not BURN else "Charred")
    for k in range(5):                                                                               # its joists, snapped
        x = xf + 0.6 + k * 0.9
        beam(g, (x, FL - 0.2, zc + 0.1), (x + rnd.uniform(-0.3, 0.3), rnd.uniform(0.2, 1.4), z1 + rnd.uniform(0.2, 1.4)), 0.14, 0.2, "Beam" if not BURN else "Charred")
    beam(g, (xf + 0.1, FL, z1 - 0.1), (xf - 1.6, 0.15, z1 + 1.8), 0.28, 0.28, "Beam" if not BURN else "Charred")   # the fallen floor beam
    rubble_pile(xf + 2.2, z1 + 1.4, 1.6, 18, 91, ("RoofOld", "RoofOld", "PlanksLight", "Rubble", "Charred"))
    box(g, xf + 0.1, TOP - 0.14, TOP + 0.1, cz, 0.3, wz, "Beam")                                      # top plates
    box(g, cx + wx / 2 - 0.1, TOP - 0.14, TOP + 0.1, cz, 0.3, wz, "Beam")
    for zz in (z0 + 0.1, z1 - 0.1):
        box(g, cx, TOP - 0.14, TOP + 0.1, zz, wx, 0.3, "Beam")
    # upper floor: exposed studs; boards only on the far part of the front and on the back wall
    for k in range(13):
        z = z0 + 0.4 + k * (wz - 0.8) / 12
        box(g, xf + 0.1, FL + 0.1, TOP - 0.1, z, 0.12, 0.12, "Timber" if k > 7 else "Beam")
    box(g, xf + 0.05, FL + 0.1, TOP - 0.1, z0 + 2.2, 0.08, 4.0, W)
    box(g, cx + wx / 2 - 0.15, FL + 0.1, TOP - 0.1, cz - 1.0, 0.08, wz - 2.0, W)
    for k in range(4):                                                                               # loose boards hanging
        z = cz + 0.5 + k * 0.9
        beam(g, (xf, TOP - 0.2, z), (xf - 0.15, TOP - 1.2 - rnd.uniform(0, 0.8), z + rnd.uniform(-0.3, 0.3)), 0.05, 0.3, W)
    beam(g, (xf + 0.1, FL + 0.2, z1 - 0.3), (xf + 0.1, TOP - 0.2, z1 - 3.0), 0.14, 0.16, "Beam")      # a brace
    # roof: rafters along the length; tiles only over the far half, a canvas tarp patch, snapped rafters near us
    n = 12
    for k in range(n + 1):
        z = z0 + k * wz / n
        broken = z > cz + 2.5
        for s in (-1, 1):
            e = (cx + s * (wx / 2 + 0.4), TOP - 0.2, z); r = (cx, RIDGE, z)
            if broken and s < 0 and k % 2:
                t = rnd.uniform(0.35, 0.65); r = (e[0] + (r[0] - e[0]) * t, e[1] + (r[1] - e[1]) * t, z)
            beam(g, e, r, 0.12, 0.18, "Beam" if not BURN else "Charred")
    box(g, cx, RIDGE - 0.05, RIDGE + 0.16, cz - 1.0, 0.22, wz - 2.0, "Beam")
    for s in (-1, 1):
        e = cx + s * (wx / 2 + 0.4)
        slab(g, (e, TOP - 0.1, z0 - 0.3), (cx, RIDGE + 0.12, z0 - 0.3), (cx, RIDGE + 0.12, cz - 1.0), (e, TOP - 0.1, cz - 1.0), 0.16, "RoofOld")
        for k in range(5):                                                                           # battens on the open part
            t = (k + 0.5) / 5
            beam(g, (e + (cx - e) * t, TOP - 0.05 + (RIDGE - TOP) * t + 0.12, cz - 1.0), (e + (cx - e) * t, TOP - 0.05 + (RIDGE - TOP) * t + 0.12, z1 - 0.2),
                 0.05, 0.05, "Timber")
    if not BURN:
        slab(g, (xf - 0.4, TOP + 0.05, cz - 1.0), (cx - 1.5, RIDGE - 0.4, cz - 1.0), (cx - 1.5, RIDGE - 0.4, cz + 1.6), (xf - 0.2, TOP - 0.3, cz + 1.8), 0.03, "CurtainX")
    for z in (cz - 4.2, cz - 1.0):
        window(g, xf, 1.1, z, 1.3, 1.3, face_z=False, s=-1)
    # scaffolding along the front: poles, ledgers, plank decks, braces and a ladder
    sx = xf - 1.1
    zs = (z0 - 0.2, cz - 2.2, cz + 2.2, z1 + 0.2)
    P = "Timber" if not BURN else "Charred"
    for k, z in enumerate(zs):
        if BURN and k == 3:
            beam(g, (sx - 0.1, 0.0, z), (sx - 2.6, 0.2, z + 3.4), 0.12, 0.12, P)
            continue
        for dx in (0.0, 0.9):
            hcyl(g, (sx + dx, -0.1, z), (sx + dx, 6.3, z), 0.06, P, 8)
    zl = z1 + 0.2 if not BURN else cz + 2.2
    for y in (FL, TOP - 0.2):
        for dx in (0.0, 0.9):
            hcyl(g, (sx + dx, y, z0 - 0.3), (sx + dx, y, zl), 0.05, P, 6)
        box(g, sx + 0.45, y + 0.05, y + 0.11, (z0 - 0.2 + zl) / 2, 1.0, zl - z0 + 0.3, "PlanksLight" if not BURN else "Charred")
    for (za, zb) in ((zs[0], zs[1]), (zs[1], zs[2])):
        hcyl(g, (sx, 0.2, za), (sx, TOP - 0.3, zb), 0.04, P, 6)
    for k, z in enumerate(zs[:3]):                                                                   # the third lift (7.2 m)
        for dx in (0.0, 0.9):
            hcyl(g, (sx + dx, 6.3, z), (sx + dx, 8.0, z), 0.06, P, 8)
    for dx in (0.0, 0.9):
        hcyl(g, (sx + dx, 7.2, z0 - 0.3), (sx + dx, 7.2, cz + 2.4), 0.05, P, 6)
    box(g, sx + 0.45, 7.25, 7.31, (z0 + cz + 2.2) / 2, 1.0, cz + 2.2 - z0 + 0.3, "PlanksLight" if not BURN else "Charred")
    for (za, zb) in ((zs[0], zs[1]), (zs[1], zs[2])):
        hcyl(g, (sx + 0.9, 0.2, zb), (sx + 0.9, 7.0, za), 0.04, P, 6)                                 # cross bracing
        hcyl(g, (sx, TOP - 0.1, za), (sx, 7.9, zb), 0.04, P, 6)
    for (x, z) in ((sx, z1 + 2.0), (sx + 1.8, z1 + 2.0), (sx, z1 + 3.6), (sx + 1.8, z1 + 3.6)):          # a corner tower by the collapse
        hcyl(g, (x, -0.1, z), (x, 4.6, z), 0.06, P, 8)
    for y in (2.2, 4.2):
        box(g, sx + 0.9, y, y + 0.06, z1 + 2.8, 2.0, 1.8, "PlanksLight" if not BURN else "Charred")
    hcyl(g, (sx, 0.2, z1 + 2.0), (sx + 1.8, 4.2, z1 + 3.6), 0.04, P, 6)
    hcyl(g, (sx + 0.45, 8.0, zs[1]), (sx - 1.4, 8.0, zs[1]), 0.07, P, 8)                            # the hoist arm, rope and bucket
    hcyl(g, (sx - 1.3, 8.0, zs[1]), (sx - 1.3, 3.4, zs[1]), 0.012, "BeamDark", 4)
    cyl(g, sx - 1.3, 3.0, zs[1], 0.2, 0.17, 0.4, "PlanksLight", 10)
    for s in (-0.22, 0.22):
        beam(g, (sx - 0.9, 0.0, cz + 0.4 + s), (sx - 0.1, FL + 0.9, cz + 0.4 + s), 0.06, 0.06, "Beam")
    for k in range(9):
        t = (k + 0.5) / 9
        beam(g, (sx - 0.9 + 0.8 * t, (FL + 0.9) * t, cz + 0.18), (sx - 0.9 + 0.8 * t, (FL + 0.9) * t, cz + 0.62), 0.04, 0.04, "Beam")
    box(g, sx + 0.45, FL + 0.11, FL + 0.6, z1 - 0.8, 0.5, 0.5, "PlanksLight") if not BURN else None    # a crate of nails up top
    # the raking shores propping the open corner
    for k in range(2):
        z = z1 - 0.6 - k * 1.2
        beam(g, (xf - 2.2, 0.0, z + 0.3), (xf - 0.05, 2.7, z), 0.2, 0.2, "Timber" if not BURN else "Charred")
    # the inn, set back behind the repair (lower, out of the way of the mountains)
    gable_house(g, 27.5, -37.0, 10.0, 9.0, 4.8, 2.3, "PlanksTeal", "Roof", ridge_z=False, broken=0.45 if BURN else 0.0, seed=11)
    box(g, 27.5, -0.2, 0.5, -37.0, 10.3, 9.3, "StoneLight", 0.04)
    for x in (24.5, 27.5, 30.5):
        window(g, x, 1.2, -32.5, 1.2, 1.4)
        window(g, x, 3.2, -32.5, 1.0, 1.0)
    slab(g, (22.2, 2.85, -32.4), (32.8, 2.85, -32.4), (32.8, 2.4, -31.0), (22.2, 2.4, -31.0), 0.07, "AwningX")
    box(g, 27.5, 4.9, 5.5, -32.35, 5.4, 0.1, "SignWood")
    box(g, 30.0, 4.8, 8.0, -38.5, 0.9, 0.9, "Brick")
    if not BURN:
        SMOKES.append((30.0, 8.0, -38.5, 0.7))
    gable_house(g, 31.0, -12.0, 8.0, 9.0, 4.0, 2.1, "PlanksGrey", "RoofOld", ridge_z=True, seed=12)
    window(g, 27.0, 1.3, -14.0, 1.2, 1.3, face_z=False, s=-1)
    # the stacks of repair timber, sawhorses and tools (edges only)
    for k in range(7):
        obox("CE_Props", (12.2 + (k % 3) * 0.02, 0.1 + 0.2 * (k // 3), -28.4 + (k % 3) * 0.28), (3.6, 0.18, 0.26), 90 + rnd.uniform(-3, 3),
             "Timber" if not BURN else "Charred")
    for s in (-1, 1):
        beam("CE_Props", (14.2 + s * 0.6, 0.0, -9.8), (14.2 + s * 0.2, 0.8, -9.8), 0.08, 0.08, "Beam")
        beam("CE_Props", (14.2 + s * 0.6, 0.0, -11.6), (14.2 + s * 0.2, 0.8, -11.6), 0.08, 0.08, "Beam")
    box("CE_Props", 14.2, 0.8, 0.9, -10.7, 0.14, 2.2, "Beam")
    obox("CE_Props", (14.3, 1.0, -10.7), (0.3, 0.12, 3.0), 4, "Timber")
    obox("CE_Props", (13.6, 0.15, -12.8), (0.12, 0.12, 2.6), 30, "Timber")
    obox("CE_Props", (13.4, 0.08, -13.4), (0.2, 0.06, 2.0), -12, "PlanksLight")
    crate(12.6, 0.0, -11.6, 0.55, 8); crate(12.5, 0.55, -11.55, 0.45, 20)
    cyl("CE_Props", 11.8, 0.0, -12.4, 0.24, 0.2, 0.42, "Iron", 10)                                      # a bucket

# ======================================================================
#  the round court, the arch on its far rim, and the wrecked market round it
# ======================================================================
# As in the game's Celdic, all at one level: the fighting floor opens into one broad round court of cobbles, ringed
# by a band of dressed curb stones (painted by the floor shader). The fighters stand on its near side; the old stone
# arch stands centred on its far rim; benches, planters, lamps and low fences stand round the rim, outside the fight
# lane and clear of the way to the arch. Behind and round the arch the market lies wrecked: an old wooden house
# with a crushed stall before it on the left, a big timber building broken to its frame on the right, and behind
# the arch the timber tower among smashed stalls, heaped beams, frames and houses with their roofs fallen in.
LY = 0.0                               # the court, the floor and the market are at the one level
TOWER = (0.6, -44.0)                   # the timber tower, behind the arch and framed by its opening
TOWER_S = 0.6
MARKET_END = -72.0                     # the market ground behind the court; the lower town lies beyond

def lifted(dy, fn, *a, **kw):
    """Run a builder that works at ground level, then move everything it made up (or down) by dy: the geometry
    of every group and its lamp, window, fire, smoke and crowd entries."""
    before = {n: len(g.bm.verts) for n, g in GR.items()}
    n0 = [len(L) for L in (LAMPS, WINDOWS, FIRES, SMOKES, CROWD)]
    r = fn(*a, **kw)
    for n, g in GR.items():
        bm = g.bm; bm.verts.ensure_lookup_table()
        for v in bm.verts[before.get(n, 0):]:
            v.co.z += dy                                             # Blender z = Godot y
    for i in range(n0[0], len(LAMPS)):
        x, z, h = LAMPS[i]; LAMPS[i] = (x, z, h + dy)
    for L, k in ((WINDOWS, n0[1]), (FIRES, n0[2]), (SMOKES, n0[3]), (CROWD, n0[4])):
        for i in range(k, len(L)):
            e = list(L[i]); e[1] += dy; L[i] = tuple(e)
    return r

def shifted(dx, dz, fn, *a, **kw):
    """Run a builder, then move everything it made sideways by (dx, dz) in Godot x / z: the geometry of every
    group and its lamp, window, fire, smoke and crowd entries."""
    before = {n: len(g.bm.verts) for n, g in GR.items()}
    n0 = [len(L) for L in (LAMPS, WINDOWS, FIRES, SMOKES, CROWD)]
    r = fn(*a, **kw)
    for n, g in GR.items():
        bm = g.bm; bm.verts.ensure_lookup_table()
        for v in bm.verts[before.get(n, 0):]:
            v.co.x += dx; v.co.y -= dz                               # Blender y = -Godot z
    for i in range(n0[0], len(LAMPS)):
        x, z, h = LAMPS[i]; LAMPS[i] = (x + dx, z + dz, h)
    for L, k in ((WINDOWS, n0[1]), (FIRES, n0[2]), (SMOKES, n0[3]), (CROWD, n0[4])):
        for i in range(k, len(L)):
            e = list(L[i]); e[0] += dx; e[2] += dz; L[i] = tuple(e)
    return r

LEFT_SHIFT, RIGHT_SHIFT = (-4.0, -3.0), (4.5, -4.0)   # the store and the repair house, moved out round the court

def plate(g, x0, x1, z0, z1, y, m):
    """A flat ground plate seen only from above (one quad: no hidden sides or underside to waste atlas space)."""
    quad(g, [(x0, y, z1), (x1, y, z1), (x1, y, z0), (x0, y, z0)], [(x0, -z1), (x1, -z1), (x1, -z0), (x0, -z0)], m)

def court_xz(th, r):
    """A point on a circle round the court centre: th in degrees from +x, round toward the back (-z)."""
    a = math.radians(th)
    return (COURT[0] + r * math.cos(a), COURT[1] - r * math.sin(a))

def face_centre(x, z):
    """The rotation (as bench() takes it) that turns a seat at (x, z) to face the middle of the court."""
    fx, fz = COURT[0] - x, COURT[1] - z
    return math.degrees(math.atan2(-fx, fz))

def build_arch():
    """The arch, centred on the far rim of the court on its two piers. No basin and no raised base: the court
    floor runs right under it. Burning: its right half has fallen, the stones lying behind the right pier."""
    g = "CE_Props"; wx, az = WELL; S = ARCH_S
    for sx in (-1, 1):
        x = wx + sx * ARCH_HALF
        broken = BURN and sx > 0
        pier(g, x, az, ARCH_SPRING if not broken else 2.4 * S, broken, S)
        if broken:
            for k in range(4):
                rock(g, x + random.Random(k).uniform(-0.25, 0.25), 2.4 * S + 0.05, az + random.Random(k + 9).uniform(-0.25, 0.25),
                     0.3, 0.22, 0.3, 40 + k, "StoneMoss")
    if BURN:
        arch_band(g, wx, az, 0.0, math.pi * 0.62, 20)                                   # the right half has fallen
        rnd = random.Random(8)
        for k in range(9):
            px, pz = wx + rnd.uniform(3.4, 6.4), az + rnd.uniform(-3.4, -0.7)
            rock(g, px, 0.28, pz, rnd.uniform(0.34, 0.56), rnd.uniform(0.22, 0.34), rnd.uniform(0.3, 0.42), 60 + k, "StoneArch")
        obox(g, (wx + 4.8, 0.36, az - 2.0), (1.6, 0.6, 0.64), 32, "StoneArch", 0.05)
        return (wx - 1.0 * S, ARCH_SPRING + ARCH_HALF + 0.1, az)
    arch_band(g, wx, az, 0.0, math.pi, 32)
    top = ARCH_SPRING + ARCH_HALF + 0.34 * S
    box(g, wx, top - 0.04, top + 0.22, az, 0.78, 0.78, "StoneLight", 0.03)                  # the cap
    # the iron finial on the cap (the pennant strings are tied to it, as in the game)
    hcyl(g, (wx, top + 0.2, az), (wx, top + 1.35, az), 0.05, "Iron", 8)
    hcyl(g, (wx - 0.42, top + 0.92, az), (wx + 0.42, top + 0.92, az), 0.035, "Iron", 6)
    for s_ in (-1, 1):
        beam(g, (wx + s_ * 0.42, top + 0.92, az), (wx + s_ * 0.2, top + 0.62, az), 0.03, 0.03, "Iron")
    ico(g, (wx, top + 1.4, az), 0.09, "Iron", 5, 1.0)
    return (wx, top + 1.2, az)

def ruin_frame(cx, cz, wx, wz, h, seed, face=1, g="CE_Buildings"):
    """A timber building wrecked to its frame (as in the game): posts on a stone footing, a few snapped short, the
    upper floor half fallen, the roof frame exposed with rafters missing and a patch of tiles left, beams collapsed
    against it, its boards and tiles in a heap. face: +1 / -1, the side toward the aisle (x)."""
    rnd = random.Random(seed); W = "Charred" if BURN else "Beam"; Wl = "Charred" if BURN else "PlanksGrey"
    x0, x1, z0, z1 = cx - wx / 2, cx + wx / 2, cz - wz / 2, cz + wz / 2
    box(g, cx, -0.25, 0.4, cz, wx + 0.4, wz + 0.4, "StoneMoss", 0.04)
    FL = h * 0.52
    tops = {}
    for i in range(4):
        for j in range(3):
            x = x0 + 0.15 + i * (wx - 0.3) / 3; z = z0 + 0.15 + j * (wz - 0.3) / 2
            snapped = rnd.random() < 0.3 and not (i in (0, 3) and j == 0)
            top = rnd.uniform(1.4, FL + 0.6) if snapped else h
            tops[(i, j)] = top
            box(g, x, 0.4, top, z, 0.26, 0.26, W, 0.02)
    for j in range(3):                                                                       # floor beams, some fallen
        z = z0 + 0.15 + j * (wz - 0.3) / 2
        if rnd.random() < 0.65:
            box(g, cx, FL - 0.14, FL + 0.1, z, wx, 0.24, W)
        else:
            beam(g, (x0 + 0.3, FL, z), (x1 - 0.6, 0.35, z + rnd.uniform(-1.0, 1.0)), 0.24, 0.24, W)
    for k in range(6):                                                                       # joists and a few floor boards
        x = x0 + 0.6 + k * (wx - 1.2) / 5
        if rnd.random() < 0.6:
            box(g, x, FL + 0.1, FL + 0.28, cz, 0.14, wz - 0.3, W)
        else:
            beam(g, (x, FL + 0.2, z0 + 0.3), (x + rnd.uniform(-0.5, 0.5), rnd.uniform(0.2, 1.4), z1 - 0.3), 0.14, 0.18, W)
    box(g, cx - face * wx * 0.2, FL + 0.28, FL + 0.34, cz - wz * 0.15, wx * 0.5, wz * 0.55, Wl)
    box(g, cx, h - 0.12, h + 0.12, z0 + 0.15, wx + 0.2, 0.26, W)                              # the far top plate holds
    box(g, x0 + 0.15, h - 0.12, h + 0.12, cz, 0.26, wz, W)
    # the roof frame (ridge along z): rafters every 0.9 m, some snapped, some gone; tiles only on a far patch
    RISE = 2.3; n = int(wz / 0.9)
    for k in range(n + 1):
        z = z0 + k * wz / n
        for s in (-1, 1):
            if rnd.random() < 0.22:
                continue
            e = (cx + s * (wx / 2 + 0.35), h, z); r_ = (cx, h + RISE, z)
            t = 1.0 if rnd.random() < 0.55 else rnd.uniform(0.3, 0.8)
            beam(g, e, (e[0] + (r_[0] - e[0]) * t, e[1] + (r_[1] - e[1]) * t, z), 0.12, 0.18, W)
    box(g, cx, h + RISE - 0.06, h + RISE + 0.14, z0 + wz * 0.3, 0.22, wz * 0.6, W)              # what is left of the ridge
    ang = math.atan2(RISE, wx / 2 + 0.35)
    for s in (-1, 1):                                                                         # the surviving tile patches
        e = cx + s * (wx / 2 + 0.35); m_ = (e + cx) / 2
        zz0, zz1 = z0 - 0.3, z0 + wz * (0.35 if s == face else 0.55)
        slab(g, (e, h + 0.05, zz0), (cx, h + RISE + 0.12, zz0), (cx, h + RISE + 0.12, zz1), (e, h + 0.05, zz1), 0.14, "RoofOld")
    # the collapsed part: a roof section fallen on the near side, beams leaning down from the floor to the ground
    zn = z1 + 0.6
    slab(g, (x0 - 0.2, 0.3, zn + 0.6), (x1 + 0.2, 0.5, zn + 0.4), (x1 + 0.1, 2.2, z1 - 0.8), (x0 - 0.1, 1.8, z1 - 0.6), 0.14,
         "RoofOld" if not BURN else "Charred")
    for k in range(5):
        x = x0 + rnd.uniform(0.3, wx - 0.3)
        beam(g, (x, rnd.uniform(FL * 0.6, FL + 0.2), z1 - rnd.uniform(0.2, 1.4)), (x + rnd.uniform(-1.2, 1.2), 0.1, zn + rnd.uniform(0.4, 2.2)),
             0.18, 0.22, W)
    beam(g, (cx + face * wx / 2, h * 0.8, cz), (cx + face * (wx / 2 + 2.6), 0.1, cz + rnd.uniform(-1.5, 1.5)), 0.22, 0.24, W)
    for k in range(6):                                                                         # boards hanging off the frame
        z = z0 + rnd.uniform(0.5, wz - 0.5)
        beam(g, (cx + face * wx / 2, FL + rnd.uniform(0.2, 1.4), z), (cx + face * (wx / 2 + 0.1), FL - rnd.uniform(0.5, 1.5), z + rnd.uniform(-0.3, 0.3)), 0.05, 0.3, Wl)
    rubble_pile(cx + face * 0.5, zn + 1.0, 2.0, 26, seed + 5, ("RoofOld", "RoofOld", "PlanksLight", "Rubble", "Beam" if not BURN else "Charred"))
    if BURN:
        FIRES.append((cx - face * 0.8, FL + 0.4, cz + 0.5, 1.3))
        SMOKES.append((cx, h, cz, 4.0))
    elif seed in (63, 65):
        SMOKES.append((cx - face * 0.8, FL + 0.2, cz + 0.5, 1.7))      # by day the wreck still smoulders: a thin wisp

def damaged_house(cx, cz, wx, wz, h, rise, wall, roof, rz, broken, seed, face=1, g="CE_Buildings"):
    """A house of the market with its roof partly fallen in (bare rafters), windows broken or boarded."""
    gable_house(g, cx, cz, wx, wz, h, rise, wall, roof, ridge_z=rz, broken=broken, seed=seed, rafter="Charred" if BURN else "Beam")
    box(g, cx, -0.25, 0.45, cz, wx + 0.3, wz + 0.3, "StoneMoss" if seed % 2 else "StoneLight", 0.04)
    rnd = random.Random(seed)
    xf = cx + face * wx / 2
    for k in range(int(wz / 3.0)):
        z = cz - wz / 2 + 1.5 + k * 3.0
        window(g, xf + face * 0.06, 1.2, z, 1.1, 1.2, face_z=False, s=face)
        if h > 4.6:
            window(g, xf + face * 0.06, h * 0.62, z, 0.9, 0.9, face_z=False, s=face)
        if rnd.random() < 0.45:                                                              # boarded up
            for j in range(3):
                obox(g, (xf + face * 0.2, 1.4 + j * 0.35, z), (0.04, 0.16, 1.4), rnd.uniform(-12, 12), "PlanksGrey")
    zf = cz + wz / 2
    window(g, cx, 1.3, zf + 0.06, 1.0, 1.1)
    if BURN or rnd.random() < 0.5:
        (burnt_hole if BURN else broken_hole)(g, xf + face * 0.07, 1.0 if not BURN else 2.2, 2.6 if not BURN else 3.8,
                                               cz + rnd.uniform(-wz / 4, wz / 4), 1.6, seed, face=face, axis='x')
    rubble_pile(xf + face * 1.4, cz + rnd.uniform(-1.5, 1.5), 1.3, 14, seed + 3, ("Rubble", "RoofOld", "PlanksLight", "Brick"))

def broken_hole(g, x, y0, y1, z, w, seed, face=1, axis='x'):
    """A ragged hole broken through a wall (day: splintered boards round a dark opening)."""
    rnd = random.Random(seed)
    n = max(2, int(w / 0.22))
    box(g, x + face * 0.04, y0, y1, z, 0.06, w, "Soot")
    for k in range(n):
        t = -w / 2 + (k + 0.5) * w / n
        top = y1 + rnd.uniform(-0.4, 0.5); bot = y0 + rnd.uniform(-0.4, 0.4)
        for (ya, yb) in ((top - rnd.uniform(0.1, 0.5), top), (bot, bot + rnd.uniform(0.1, 0.4))):
            box(g, x + face * 0.08, ya, yb, z + t, 0.07, w / n * 0.9, "PlanksGrey")

def wooden_house(cx, cz):
    """The old wooden house facing the court left of the arch (as in the game): dark boards on a stone footing, its
    gable toward us with painted bargeboards, a finial and a gable window, a door and a broad window under a little
    roof. By day it is battered (a wall stove in, a shutter hanging, boards nailed over a window, a beam fallen against
    it); in the evening its roof is burnt through."""
    g = "CE_Buildings"; rnd = random.Random(71)
    wx, wz, H, RISE = 7.0, 8.0, 4.4, 2.8
    gable_house(g, cx, cz, wx, wz, H, RISE, "Planks", "RoofOld", ridge_z=True, broken=0.5 if BURN else 0.0, seed=71,
                rafter="Charred" if BURN else "Beam")
    box(g, cx, -0.2, 0.45, cz, wx + 0.3, wz + 0.3, "StoneMoss", 0.04)
    zf = cz + wz / 2
    tanA = RISE / (wx / 2)
    if not BURN:                                     # the decorated gable
        for s in (-1, 1):
            beam(g, (cx + s * (wx / 2 + 0.45), H - 0.45 * tanA - 0.05, zf + 0.5), (cx, H + RISE + 0.12, zf + 0.5), 0.1, 0.34, "TrimGreen")
        hcyl(g, (cx, H + RISE + 0.05, zf + 0.5), (cx, H + RISE + 0.95, zf + 0.5), 0.06, "TrimGreen", 6)
        box(g, cx, H - 0.12, H + 0.08, zf + 0.08, wx + 0.1, 0.14, "TrimGreen")              # a painted band under the gable
        window(g, cx, H + 0.45, zf + 0.06, 0.9, 0.9)
        for s in (-1, 1):                                                                  # boards of the gable, battened
            for k in range(3):
                x = cx + s * (0.9 + k * 0.85)
                top = H + RISE * (1 - abs(x - cx) / (wx / 2)) - 0.15
                if top > H + 0.25:
                    box(g, x, H + 0.08, top, zf + 0.04, 0.08, 0.05, "BeamDark")
    # the front: a door, a broad window with a sill, shutters (one hanging loose) and a little roof over them
    box(g, cx + 1.7, 0.45, 2.55, zf + 0.06, 1.15, 0.08, "BeamDark")
    box(g, cx + 1.7, 2.55, 2.7, zf + 0.08, 1.45, 0.14, "Beam")
    window(g, cx - 1.3, 1.25, zf + 0.06, 2.0, 1.3)
    box(g, cx - 1.3, 1.1, 1.22, zf + 0.26, 2.3, 0.32, "Beam")
    box(g, cx - 1.3 - 1.25, 1.2, 2.6, zf + 0.12, 0.5, 0.06, "TrimGreen", 0.01)
    obox(g, (cx - 1.3 + 1.3, 1.4, zf + 0.3), (0.5, 1.3, 0.06), 28 if not BURN else 70, "TrimGreen")      # the hanging shutter
    slab(g, (cx - wx / 2 - 0.2, 3.05, zf + 0.05), (cx + wx / 2 + 0.2, 3.05, zf + 0.05), (cx + wx / 2 + 0.2, 2.75, zf + 1.1),
         (cx - wx / 2 - 0.2, 2.75, zf + 1.1), 0.08, "RoofOld" if not BURN else "Charred")
    for s in (-1, 1):
        beam(g, (cx + s * (wx / 2 - 0.1), 2.2, zf + 0.06), (cx + s * (wx / 2 - 0.1), 2.85, zf + 0.95), 0.08, 0.1, "Beam")
    # the side toward the arch: a window boarded over and the wall stove in near the corner
    xs = cx + wx / 2
    window(g, xs + 0.06, 1.3, cz - 1.6, 1.1, 1.2, face_z=False, s=1)
    for j in range(3):
        obox(g, (xs + 0.2, 1.45 + j * 0.38, cz - 1.6), (0.04, 0.16, 1.5), rnd.uniform(-14, 14), "PlanksGrey")
    if BURN:
        burnt_hole(g, xs + 0.07, 1.6, 3.4, cz + 1.4, 1.8, 72, face=1, axis='x')
        FIRES.extend([(cx + 0.6, H + 0.6, cz + 1.0, 1.4), (cx - 1.0, 0.5, zf + 0.6, 0.9)])
        SMOKES.append((cx, H + RISE, cz, 4.5))
    else:
        broken_hole(g, xs + 0.07, 0.5, 2.2, cz + 1.6, 1.7, 72, face=1, axis='x')
    beam(g, (xs + 2.4, 0.05, cz + 2.6), (xs + 0.15, 3.4, cz + 1.9), 0.22, 0.24, "Charred" if BURN else "Beam")   # a beam fallen against it
    rubble_pile(xs + 1.3, cz + 2.2, 1.3, 14, 73, ("Rubble", "RoofOld", "PlanksLight", "Beam" if not BURN else "Charred"))
    for k in range(2):
        barrel(cx - wx / 2 + 0.6 + k * 0.85, zf + 0.7, 0.95)

def build_court():
    """Round the rim of the court, outside the fight lane and clear of the way to the arch: red benches turned to the
    middle, flower planters, lamp posts and low fences behind them (as in the game). Burning: smashed, knocked over."""
    R = COURT_R
    for s in (-1, 1):
        def P(th, r):
            x, z = court_xz(th, r)
            return (COURT[0] + s * (x - COURT[0]), z)
        x, z = P(12, R + 0.9); lamp(x, z, 4.0, fallen=(BURN and s > 0), fall=s)
        x, z = P(25, R + 1.0); bench(x, z, face_centre(x, z), broken=(BURN and s < 0))
        x, z = P(37, R + 1.0); planter(x, z, 1.5, 0.75, 0.6, 800 + s, smashed=BURN)
        x, z = P(49, R + 1.0); bench(x, z, face_centre(x, z), broken=(BURN or s > 0))
        x, z = P(60, R + 1.1); planter(x, z, 1.2, 0.75, 0.6, 810 + s, smashed=(BURN or s < 0))
        pts = [P(th, R + 2.2) for th in (6, 21, 36, 51)]                          # a low fence round the outside
        for k in range(3):
            brk = (1,) if (BURN or (s > 0 and k == 1)) else ()
            fence(pts[k][0], pts[k][1], pts[k + 1][0], pts[k + 1][1], 1.0, broken=brk)
    x, z = court_xz(42, R + 3.0)
    lamp(x, z, 4.2, fallen=BURN, fall=1)                                            # the lamp on the right of the arch (as in the game)

def build_market():
    """The wrecked market behind and round the arch, at the court's level."""
    # left of the arch: the old wooden house, a crushed stall before it, beams heaped where a roof came down
    wooden_house(-10.5, -30.6)
    stall(-4.6, -24.6, '+z', 3.2, "StripeRedX", 41, broken=True)
    rubble_pile(-3.4, -29.2, 1.6, 22, 74, ("Beam", "Beam", "PlanksLight", "RoofOld", "Rubble") if not BURN
                else ("Charred", "Charred", "PlanksLight", "Rubble"))
    # right of the arch: the big timber building broken to its frame, a battered stall before it
    ruin_frame(9.4, -30.5, 9.5, 8.0, 6.4, 65, -1)
    stall(4.7, -23.7, '+z', 3.0, "StripeBlueX", 42, torn=not BURN, broken=BURN)
    # behind the arch, seen through it: a stall stripped to its frame, the timber tower, smashed stalls and heaps
    stall(-2.4, -32.8, '+z', 3.0, "StripeBlueX", 43, frame=True)
    stall(2.3, -35.6, '+z', 3.2, "StripeRedX", 44, broken=True)
    build_headframe()
    ruin_frame(-6.0, -42.0, 6.5, 7.0, 5.0, 63, 1)
    # houses farther back with their roofs fallen in
    damaged_house(10.0, -42.0, 8.0, 8.0, 4.8, 2.4, "Plaster", "RoofOld", True, 0.5, 66, -1)
    damaged_house(-14.5, -47.0, 8.0, 9.0, 5.2, 2.6, "Plaster", "RoofSlate", False, 0.5, 62, 1)
    damaged_house(-4.0, -54.0, 7.0, 7.0, 4.2, 2.3, "PlanksGrey", "RoofOld", True, 0.35, 64, 1)
    damaged_house(7.0, -56.0, 7.0, 8.0, 4.6, 2.3, "PlanksTeal", "RoofOld", False, 0.3, 68, -1)
    stall(-9.6, -37.4, '+z', 3.0, "StripeTealX", 45, torn=not BURN, broken=BURN)
    g = "CE_Props"; rnd = random.Random(2)
    junk = ("PlanksLight", "Beam", "Charred") if BURN else ("PlanksLight", "Beam", "BeamDark")
    for k in range(60):                                                         # debris all over the market ground
        x = rnd.uniform(-15.0, 15.0); z = rnd.uniform(-58.0, -23.4)
        if math.hypot(x - COURT[0], z - COURT[1]) < COURT_R + 0.6 or (abs(x) < ARCH_HALF + 1.2 and abs(z - ARCH_Z) < 1.6):
            continue
        r = rnd.random()
        if r < 0.28:
            crate(x, 0.0, z, rnd.uniform(0.45, 0.7), rnd.uniform(0, 90), rnd.choice(("PlanksLight", "PlanksLight", junk[2])))
        elif r < 0.4:
            obox(g, (x, 0.36, z), (0.75, 0.72, 0.75), rnd.uniform(0, 90), "PlanksLight", 0.03) if rnd.random() < 0.5 else barrel(x, z)
        elif r < 0.78:
            beam(g, (x, 0.06, z), (x + rnd.uniform(-1.8, 1.8), rnd.uniform(0.05, 0.6), z + rnd.uniform(-1.2, 1.2)),
                 rnd.uniform(0.12, 0.24), 0.1, rnd.choice(junk))
        else:
            slab(g, (x - 0.8, 0.03, z - 0.5), (x + 0.7, 0.05, z - 0.6), (x + 0.9, 0.04, z + 0.6), (x - 0.6, 0.06, z + 0.5), 0.02,
                 rnd.choice(("StripeRedX", "StripeBlueX", "CurtainX")))
    for (x, z, r_, n_) in ((0.9, -38.6, 1.2, 14), (-1.8, -46.8, 1.1, 12), (4.4, -48.5, 1.3, 14), (-9.8, -51.6, 1.2, 12),
                           (13.6, -36.0, 1.0, 10)):
        rubble_pile(x, z, r_, n_, int(-z * 10 + x), ("Rubble", "RoofOld", "PlanksLight", "Beam", "Rubble"))
    for k in range(22):                                                         # weeds in the trodden ground
        x, z = rnd.uniform(-14.0, 14.0), rnd.uniform(-58.0, -24.0)
        if math.hypot(x - COURT[0], z - COURT[1]) > COURT_R + 0.8:
            tuft(x, z, 0.8, rnd.choice((0, 1, 2)), 7500 + k)
    if BURN:
        for (x, z, sz) in ((-4.6, -24.4, 1.0), (4.9, -23.4, 1.2), (2.3, -35.4, 1.5), (-9.6, -37.2, 1.1), (-3.2, -29.0, 0.9)):
            FIRES.append((x, 0.3, z, sz))
        SMOKES.extend([(2.3, 1.8, -35.6, 4.6), (-3.4, 1.4, -29.2, 3.4)])

def build_ground():
    """The ground beyond the floor quad: the market's trodden earth and worn flags behind the court, and the plain
    ground either side, all at the floor's level."""
    plate("CE_Buildings", -14.0, 14.0, -50.0, FLOOR_BACK, 0.0, "CourtPaving")
    for s in (-1, 1):
        a, b = sorted((s * 14.0, s * 25.0))
        plate("CE_Far", a, b, -50.0, FLOOR_BACK, 0.0, "MarketGround")
        a, b = sorted((s * 25.0, s * 49.0))
        plate("CE_Far", a, b, MARKET_END, FLOOR_BACK, 0.0, "MarketGround")
    plate("CE_Far", -25.0, 25.0, MARKET_END, -50.0, 0.0, "MarketGround")


def far_shell(g, x, z, w, d, h, r, ax, wall, seed):
    """A gutted house seen from afar: four walls with ragged tops, a dark interior, a few bare rafters."""
    rnd = random.Random(seed); t = 0.3
    for (cx, cz, L, along) in ((x, z + d / 2 - t / 2, w, 'x'), (x, z - d / 2 + t / 2, w, 'x'),
                               (x - w / 2 + t / 2, z, d, 'z'), (x + w / 2 - t / 2, z, d, 'z')):
        n = 4
        for k in range(n):
            o = -L / 2 + (k + 0.5) * L / n
            top = h * rnd.uniform(0.45, 1.0) + (r * rnd.uniform(0.0, 0.7) if along != ax else 0.0)
            if along == 'x':
                box(g, cx + o, -0.3, top, cz, L / n + 0.02, t, wall)
            else:
                box(g, cx, -0.3, top, cz + o, t, L / n + 0.02, wall)
    box(g, x, -0.3, 0.35, z, w - 2 * t, d - 2 * t, "Soot")                    # the burnt-out inside
    m = "Charred" if BURN else "Beam"
    for k in range(4):                                                         # bare rafters, some snapped
        f = rnd.uniform(0.45, 1.0) if rnd.random() < 0.6 else 1.0
        if ax == 'x':
            xx = x - w / 2 + 0.8 + k * (w - 1.6) / 3
            for s in (-1, 1):
                p0 = (xx, h, z + s * d / 2); p1 = (xx, h + r * f, z + s * d / 2 * (1 - f))
                if rnd.random() < 0.75:
                    beam(g, p0, p1, 0.16, 0.2, m)
        else:
            zz = z - d / 2 + 0.8 + k * (d - 1.6) / 3
            for s in (-1, 1):
                p0 = (x + s * w / 2, h, zz); p1 = (x + s * w / 2 * (1 - f), h + r * f, zz)
                if rnd.random() < 0.75:
                    beam(g, p0, p1, 0.16, 0.2, m)

def roof_hole(g, x, z, w, d, h, r, ax, over, thick, seed):
    """A hole broken through the camera-side roof slab of a simple gable house: a ragged dark patch on the slope
    (a fan of triangles round an uneven rim) with rafters across it."""
    rnd = random.Random(seed); gg = grp(g)
    m = "Charred" if BURN else "Beam"
    if ax == 'x':                                    # ridge along x: the +z slope faces the camera
        z1 = z + d / 2 + over; ye = h - over * r / (d / 2)
        def P(a, u):
            return (a, ye + u * (h + r - ye) + thick + 0.03, z1 + u * (z - z1))
        am, hw = x + rnd.uniform(-0.2, 0.1) * w, rnd.uniform(0.15, 0.22) * w
        ccw = True
    else:                                            # ridge along z: the slope facing the middle of the view
        s = -1 if x > 0 else 1
        xe = x + s * (w / 2 + over); ye = h - over * r / (w / 2)
        def P(a, u):
            return (xe + u * (x - xe), ye + u * (h + r - ye) + thick + 0.03, a)
        am, hw = z + rnd.uniform(-0.15, 0.1) * d, rnd.uniform(0.17, 0.25) * d
        ccw = s < 0
    um, hu = rnd.uniform(0.38, 0.5), rnd.uniform(0.24, 0.32)
    n = 9
    rim = []
    for k in range(n):
        t = 2 * math.pi * k / n
        rho = rnd.uniform(0.62, 1.0)
        rim.append(P(am + hw * math.cos(t) * rho, um + hu * math.sin(t) * rho))
    c = P(am, um)
    for k in range(n):
        a_, b_ = rim[k], rim[(k + 1) % n]
        quad(gg, [c, a_, b_] if ccw else [c, b_, a_], [(0.5, 0.5), (0, 0), (1, 0)], "Soot")
    for k in range(3):                                # the rafters left across the hole
        aa = am - hw * 0.7 + k * hw * 0.7
        beam(g, P(aa, um - hu - 0.05), P(aa, min(1.0, um + hu * rnd.uniform(0.3, 1.1))), 0.14, 0.16, m)

def build_lower_town():
    """The lower town beyond the courtyard, at market level: houses either side of the view, lower and hazier
    roofs farther back closing the end of the view."""
    def houses():
        g = "CE_Buildings"
        for (cx, cz, wx, wz, h, rise, wall, roof, rz, seed, brk) in (
                (-8.8, -65.0, 7.0, 7.0, 4.8, 2.4, "Plaster", "RoofOld", True, 51, 0.4),
                (9.6, -66.5, 7.4, 7.0, 4.2, 2.2, "PlanksGrey", "RoofOld", True, 52, 0.32),
                (-18.6, -69.0, 7.0, 8.0, 5.6, 2.6, "Plaster", "RoofSlate", False, 53, 0.45),
                (19.0, -71.0, 7.0, 8.0, 4.6, 2.3, "Plaster", "RoofOld", False, 54, 0.3)):
            gable_house(g, cx, cz, wx, wz, h, rise, wall, roof, ridge_z=rz, broken=brk, seed=seed,
                        rafter="Charred" if BURN else "Beam")
            rubble_pile(cx + (1.2 if cx < 0 else -1.2), cz + wz / 2 + 0.9, 1.4, 14, seed + 300,
                        (roof, roof, "Rubble", "PlanksLight", "Beam" if not BURN else "Charred"))
            box(g, cx, -0.2, 0.4, cz, wx + 0.3, wz + 0.3, "StoneLight", 0.04)
            zf = cz + wz / 2
            for x in (cx - wx / 4, cx + wx / 4):
                window(g, x, 1.2, zf, 1.0, 1.1)
            window(g, cx, 3.0 if h > 4.5 else 2.7, zf, 0.8, 0.8)
        for k, (x, z, w, d, h, r, ax, wall, roof) in enumerate((
                (-2.5, -80.0, 9.0, 6.0, 3.4, 2.1, 'x', "FarWall", "FarRoof"),
                (8.0, -84.0, 8.0, 6.0, 3.8, 2.0, 'z', "FarWall", "FarSlate"),
                (-12.5, -85.0, 8.0, 6.0, 3.0, 2.0, 'x', "FarBarn", "FarThatch"),
                (17.0, -87.0, 7.0, 6.0, 3.4, 2.0, 'x', "FarWall", "FarRoof"),
                (-20.0, -98.0, 9.0, 7.0, 6.0, 2.6, 'x', "FarWall", "FarRoof"),
                (-9.0, -104.0, 8.0, 7.0, 7.2, 2.8, 'z', "FarWall", "FarSlate"),
                (2.5, -100.0, 10.0, 7.0, 6.4, 2.6, 'x', "FarWall", "FarRoof"),
                (13.5, -106.0, 8.0, 7.0, 7.6, 2.8, 'z', "FarWall", "FarRoof"),
                (24.0, -102.0, 9.0, 7.0, 5.6, 2.4, 'x', "FarBarn", "FarSlate"),
                (-31.0, -108.0, 9.0, 7.0, 5.0, 2.4, 'x', "FarWall", "FarRoof"),
                (34.0, -111.0, 9.0, 7.0, 5.2, 2.4, 'z', "FarWall", "FarSlate"))):
            if k in (3, 4, 9):                               # gutted: ragged walls and a few bare rafters, no roof
                far_shell("CE_Far", x, z, w, d, h, r, ax, wall, 900 + k)
            else:
                gable("CE_Far", x - w / 2, x + w / 2, z - d / 2, z + d / 2, -0.3, h, h + r, wall, roof, ax, 0.4, 0.22)
                if k in (0, 1, 6, 7, 10):                    # the roof broken open: a dark hole with the rafters across it
                    roof_hole("CE_Far", x, z, w, d, h, r, ax, 0.4, 0.22, 920 + k)
        plate("CE_Far", -25.0, 25.0, -96.0, MARKET_END, 0.0, "MarketGround")
        if BURN:
            FIRES.extend([(-8.8, 3.6, -61.6, 1.6), (19.0, 3.2, -67.4, 1.4)])
            SMOKES.extend([(-8.8, 5.0, -64.0, 4.5)])
    lifted(LY, houses)

def tatters(g, p0, p1, n, length, m, seed):
    """Frayed strips of torn canvas hanging from the edge p0 -> p1 (Godot points), each its own length and twist."""
    rnd = random.Random(seed)
    for k in range(n):
        t0, t1 = k / n, (k + rnd.uniform(0.55, 0.95)) / n
        a = [p0[i] + (p1[i] - p0[i]) * t0 for i in range(3)]; b_ = [p0[i] + (p1[i] - p0[i]) * t1 for i in range(3)]
        L = length * rnd.uniform(0.3, 1.0); dx, dz = rnd.uniform(-0.12, 0.12), rnd.uniform(-0.12, 0.12)
        tip = ((a[0] + b_[0]) / 2 + dx, (a[1] + b_[1]) / 2 - L, (a[2] + b_[2]) / 2 + dz)
        slab(g, tuple(a), tuple(b_), (tip[0] + 0.05, tip[1], tip[2]), (tip[0] - 0.05, tip[1] + 0.05, tip[2]), 0.04, m)

def stall(cx, cz, face, w, stripe, seed, broken=False, torn=False, frame=False):
    """A market stall: counter with produce, four posts, a sloping striped canopy, crates beside it.
    face: '+z', '+x' or '-x' (the side the customers stand). broken: crushed, the canopy down on the counter;
    torn: standing but battered; frame: stripped to its timber frame, a scrap of canvas left hanging."""
    g = "CE_Props"; rnd = random.Random(seed)
    f = {'+z': (0, 1), '+x': (1, 0), '-x': (-1, 0)}[face]
    r = (f[1], -f[0]) if face != '+z' else (1, 0)
    def P(u, y, v):           # u along the counter, v toward the customer
        return (cx + r[0] * u + f[0] * v, y, cz + r[1] * u + f[1] * v)
    rot = 0.0 if face == '+z' else 90.0
    wood = "Charred" if BURN else "Beam"
    if frame:
        for s in (-1, 1):
            lean = rnd.uniform(-0.18, 0.18)
            beam(g, P(s * w / 2, 0.0, 0.7), P(s * w / 2 + lean, 2.45, 0.7), 0.12, 0.12, wood)
            beam(g, P(s * w / 2, 0.0, -0.6), P(s * w / 2 + lean * 0.5, 2.95, -0.6), 0.12, 0.12, wood)
            beam(g, P(s * w / 2 + lean, 2.42, 0.7), P(s * w / 2 + lean * 0.5, 2.92, -0.6), 0.09, 0.09, wood)
        beam(g, P(-w / 2, 2.92, -0.6), P(w / 2, 2.92, -0.6), 0.1, 0.1, wood)                     # the back rail
        beam(g, P(-w / 2, 2.42, 0.7), P(w / 2 - 0.4, 0.9, 1.1), 0.1, 0.1, wood)                  # the front rail, fallen at one end
        beam(g, P(-w / 2, 1.2, -0.6), P(w / 2, 1.2, -0.6), 0.08, 0.08, wood)
        slab(g, P(-w / 2, 2.9, -0.62), P(0.4, 2.88, -0.62), P(0.2, 1.5, -0.55), P(-w / 2, 1.9, -0.58), 0.03, stripe)
        tatters(g, P(-w / 2, 1.9, -0.58), P(0.2, 1.5, -0.55), 5, 0.5, stripe, seed + 4)
        obox(g, P(0.1, 0.3, 1.1), (w * 0.9, 0.6, 0.7) if face == '+z' else (0.7, 0.6, w * 0.9), rot + rnd.uniform(14, 26),
             "Charred" if BURN else "PlanksLight", 0.02)                                     # the counter, knocked over
        for k in range(7):
            u, v = rnd.uniform(-w / 2, w / 2), rnd.uniform(0.9, 2.2)
            ico(g, P(u, 0.1, v), 0.1, rnd.choice(("Apple", "Orange", "Cabbage", "Bread")), seed * 41 + k, 0.8)
        crate(*P(-w / 2 - 0.5, 0, rnd.uniform(0.0, 1.2)), 0.55, rnd.uniform(10, 50), "Charred" if BURN else "PlanksLight")
        return
    if broken:      # crushed: canopy down on the counter, posts snapped, goods spilled on the ground
        c = P(0, 0.5, 0.2)
        obox(g, c, (w, 0.95, 0.85) if face == '+z' else (0.85, 0.95, w), rot + rnd.uniform(-8, 8), "Charred" if BURN else "PlanksLight", 0.02)
        slab(g, P(-w / 2 - 0.2, 1.4, -1.0), P(w / 2 + 0.2, 0.7, -1.0), P(w / 2 + 0.3, 0.3, 1.0), P(-w / 2 - 0.1, 0.9, 1.0), 0.1, stripe)
        tatters(g, P(-w / 2 - 0.1, 0.88, 1.0), P(w / 2 + 0.3, 0.28, 1.0), 8, 0.35, stripe, seed + 7)
        for s in (-1, 1):
            beam(g, P(s * w / 2, 0.0, -0.9), P(s * w / 2 + rnd.uniform(-0.6, 0.6), 1.2, -0.9 + rnd.uniform(0.3, 1.0)), 0.12, 0.12, wood)
        for k in range(10):
            u, v = rnd.uniform(-w / 2, w / 2), rnd.uniform(0.6, 2.2)
            ico(g, P(u, 0.1, v), 0.1, rnd.choice(("Apple", "Orange", "Cabbage", "Bread")), seed * 31 + k, 0.8)
        for k in range(2):
            crate(*P(rnd.uniform(-w / 2, w / 2), 0, rnd.uniform(1.0, 2.0)), 0.55, rnd.uniform(0, 60), "Charred" if BURN else "PlanksLight")
        return
    if torn:        # still standing, but battered: a leaning post, the canopy ripped and sagging, goods knocked down
        obox(g, P(0, 0.48, 0.25), (w, 0.96, 0.8) if face == '+z' else (0.8, 0.96, w), rot, "PlanksLight", 0.02)
        lean = rnd.choice((-1, 1))
        for s in (-1, 1):
            top = 2.45 if s != lean else 1.7
            beam(g, P(s * w / 2, 0.0, 0.7), P(s * w / 2 + (0.5 * s if s == lean else 0.0), top, 0.7 + (0.4 if s == lean else 0.0)), 0.12, 0.12, "Beam")
            beam(g, P(s * w / 2, 0.0, -0.6), P(s * w / 2, 2.95 if s != lean else 2.3, -0.6), 0.12, 0.12, "Beam")
        hs = -lean
        slab(g, P(hs * (w / 2 + 0.25), 3.0, -0.8), P(0, 2.95 if lean > 0 else 3.0, -0.8), P(0, 1.9, 1.0), P(hs * (w / 2 + 0.25), 2.4, 1.2), 0.1, stripe)
        slab(g, P(-hs * 0.1, 2.9, -0.8), P(-hs * (w / 2 + 0.2), 2.2, -0.7), P(-hs * (w / 2 + 0.4), 0.5, 1.1), P(-hs * 0.2, 1.6, 1.0), 0.1, stripe)
        beam(g, P(hs * (w / 2), 2.4, 0.7), P(-hs * w / 2, 1.0, 1.2), 0.1, 0.1, "Beam")              # a snapped cross-bar
        tatters(g, P(hs * (w / 2 + 0.25), 2.38, 1.2), P(0, 1.88, 1.0), 7, 0.7, stripe, seed + 5)          # frayed hanging edges
        tatters(g, P(-hs * 0.2, 1.58, 1.0), P(-hs * (w / 2 + 0.4), 0.48, 1.1), 5, 0.4, stripe, seed + 6)
        for k in range(8):
            u, v = rnd.uniform(-w / 2, w / 2), rnd.uniform(0.9, 2.0)
            ico(g, P(u, 0.1, v), 0.1, rnd.choice(("Apple", "Orange", "Cabbage", "Bread", "Pottery")), seed * 37 + k, 0.8)
        crate(*P(w / 2 + 0.6, 0, rnd.uniform(0.2, 1.2)), 0.55, rnd.uniform(10, 50))
        obox(g, P(-w / 2 - 0.4, 0.28, 0.9), (0.55, 0.55, 0.55), rot + 35, "PlanksLight", 0.02)
        return
    obox(g, P(0, 0.48, 0.25), (w, 0.96, 0.8) if face == '+z' else (0.8, 0.96, w), rot, "PlanksLight", 0.02)
    obox(g, P(0, 0.99, 0.25), (w + 0.1, 0.06, 0.9) if face == '+z' else (0.9, 0.06, w + 0.1), rot, "Beam")
    for s in (-1, 1):
        box(g, *[P(s * w / 2, 0, 0.7)[i] for i in (0,)], 0.0, 2.45, P(s * w / 2, 0, 0.7)[2], 0.12, 0.12, "Beam")
        box(g, P(s * w / 2, 0, -0.6)[0], 0.0, 2.95, P(s * w / 2, 0, -0.6)[2], 0.12, 0.12, "Beam")
    slab(g, P(-w / 2 - 0.25, 3.0, -0.8), P(w / 2 + 0.25, 3.0, -0.8), P(w / 2 + 0.25, 2.4, 1.2), P(-w / 2 - 0.25, 2.4, 1.2), 0.1, stripe)
    obox(g, P(0, 2.28, 1.22), (w + 0.5, 0.24, 0.03) if face == '+z' else (0.03, 0.24, w + 0.5), rot, stripe)
    obox(g, P(0, 1.7, -0.62), (w, 1.4, 0.04) if face == '+z' else (0.04, 1.4, w), rot, stripe)       # the back cloth
    goods = rnd.choice((("Apple", "Orange"), ("Cabbage", "Apple"), ("Bread", "Bread"), ("Pottery", "Pottery"), ("Orange", "Cabbage")))
    n = int(w / 0.5)
    for k in range(n):                                                         # baskets heaped with goods
        u = -w / 2 + (k + 0.5) * w / n
        obox(g, P(u, 1.1, 0.3), (0.42, 0.16, 0.42), rot, "Hay")
        m = goods[k % 2]
        for j in range(5):
            ico(g, P(u + rnd.uniform(-0.12, 0.12), 1.24 + 0.04 * j, 0.3 + rnd.uniform(-0.12, 0.12)), 0.11 if m != "Pottery" else 0.14,
                m, seed * 97 + k * 7 + j, 0.85 if m != "Bread" else 0.6)
    for k in range(rnd.randint(1, 3)):
        crate(*P(w / 2 + 0.5, 0, rnd.uniform(-0.4, 0.6)), 0.55, rnd.uniform(-10, 10))
    if rnd.random() < 0.5:
        sack(*[P(-w / 2 - 0.5, 0, 0.6)[i] for i in (0, 2)], seed + 3)

HF_SNAP = 6.0
def hf_T(p):
    """The tower's transform, built life-size around its foot and scaled down by TOWER_S. Upright by day;
    burning: snapped at 6 m, the upper part crashed down to the right across the end of the stalls."""
    cx, cz = TOWER
    q = p
    if BURN and p[1] > HF_SNAP + 0.005:
        px = cx + 1.65; a = math.radians(-118.0)
        x, y = p[0] - px, p[1] - HF_SNAP
        q = (px + x * math.cos(a) - y * math.sin(a), HF_SNAP + x * math.sin(a) + y * math.cos(a), p[2] + (p[1] - HF_SNAP) * 0.3)
    return (cx + (q[0] - cx) * TOWER_S, q[1] * TOWER_S, cz + (q[2] - cz) * TOWER_S)

def build_headframe():
    """The market tower (the old headframe, Refs 3, 4) at the far end of the aisle, small in the distance: four
    raked legs, girts and X braces, a railed platform, a ladder, the A-frame and sheave wheel on top.
    Burning: snapped and fallen across the end of the stalls (Ref 7)."""
    g = "CE_Props"; cx, cz = TOWER; S = TOWER_S; T = hf_T
    def corner(sx, sz, y):
        r = 2.3 - (2.3 - 1.0) * y / 12.0
        return (cx + sx * r, y, cz + sz * r)
    C = [(-1, -1), (1, -1), (1, 1), (-1, 1)]
    m = "Beam" if not BURN else "Charred"
    rnd = random.Random(4)
    for (sx, sz) in C:
        if BURN:
            top = HF_SNAP - rnd.uniform(0.2, 1.4)
            beam(g, T(corner(sx, sz, -0.2)), T(corner(sx, sz, top)), 0.36 * S, 0.36 * S, m)
            beam(g, T(corner(sx, sz, HF_SNAP + rnd.uniform(0.3, 1.0))), T(corner(sx, sz, 12.0)), 0.36 * S, 0.36 * S, m)
        else:
            beam(g, T(corner(sx, sz, -0.2)), T(corner(sx, sz, 12.0)), 0.36 * S, 0.36 * S, m)
    levels = (0.4, 3.2, 6.0, 9.0, 12.0)
    for y0, y1 in zip(levels[:-1], levels[1:]):
        if BURN and y0 >= HF_SNAP:
            y0 += 0.01
        for i in range(4):
            a, b = C[i], C[(i + 1) % 4]
            if BURN and abs(y1 - HF_SNAP) < 0.01:
                continue                                          # the girts at the snap are gone
            beam(g, T(corner(*a, y1)), T(corner(*b, y1)), 0.22 * S, 0.22 * S, m)
            if rnd.random() < (0.3 if BURN else 0.2):           # missing braces
                continue
            beam(g, T(corner(*a, y0)), T(corner(*b, y1 - (0.6 if BURN and y1 == HF_SNAP else 0.0))), 0.14 * S, 0.14 * S, m)
            beam(g, T(corner(*b, y0)), T(corner(*a, y1 - (0.6 if BURN and y1 == HF_SNAP else 0.0))), 0.14 * S, 0.14 * S, m)
    P0 = [(cx + sx * 1.9, 12.0, cz + sz * 1.9) for (sx, sz) in C]
    hexa(g, [T(p) for p in P0] + [T((p[0], 12.22, p[2])) for p in P0], "PlanksLight" if not BURN else "Charred")
    for (sx, sz) in C:
        beam(g, T((cx + sx * 1.85, 12.2, cz + sz * 1.85)), T((cx + sx * 1.85, 13.2, cz + sz * 1.85)), 0.1 * S, 0.1 * S, m)
    for i in range(4):
        a, b = C[i], C[(i + 1) % 4]
        for y in (12.65, 13.15):
            beam(g, T((cx + a[0] * 1.85, y, cz + a[1] * 1.85)), T((cx + b[0] * 1.85, y, cz + b[1] * 1.85)), 0.07 * S, 0.07 * S, m)
    zl = cz + 2.45; ytop = 12.1 if not BURN else HF_SNAP - 0.6
    for s in (-0.3, 0.3):
        beam(g, T((cx + s, 0.0, zl)), T((cx + s * (1 - 0.2 * ytop / 12.1), ytop, zl + (cz + 1.95 - zl) * ytop / 12.1)), 0.07 * S, 0.07 * S, m)
    for k in range(int(24 * ytop / 12.1)):
        t = (k + 0.5) / 24
        y = 12.1 * t; zz = zl + (cz + 1.95 - zl) * t
        beam(g, T((cx - 0.3 + 0.06 * t, y, zz)), T((cx + 0.3 - 0.06 * t, y, zz)), 0.04 * S, 0.04 * S, m)
    for s in (-1, 1):
        beam(g, T((cx + s * 1.2, 12.2, cz)), T((cx, 16.0, cz)), 0.2 * S, 0.2 * S, m)
    hcyl(g, T((cx, 15.6, cz - 0.08)), T((cx, 15.6, cz + 0.08)), 0.5 * S, "BeamDark", 16)
    box(g, cx, -0.1, 0.25, cz, 5.4 * S, 5.4 * S, "StoneLight")
    if BURN:
        rubble_pile(cx + 6.0 * S, cz + 1.2, 1.6, 24, 77, ("Charred", "Charred", "PlanksLight", "Rubble"))
        FIRES.extend([(cx + 6.2 * S, 0.3, cz + 1.4, 1.6), (cx + 1.5 * S, (HF_SNAP - 0.5) * S, cz + 0.6, 0.7)])
        SMOKES.append((cx + 5.5 * S, 1.2, cz + 1.0, 5.5))
    return T((cx, 16.2, cz))


# ======================================================================
#  behind the market: arched-roof barns, the rest of the town, the hills and windmills
# ======================================================================
def barn(cx, cz, L, W, h, seed, hole=False):
    """A long barn with a barrel-vaulted roof (Refs 5-7), its long side toward the camera (axis along x)."""
    g = "CE_Far"; rnd = random.Random(seed)
    box(g, cx, -0.2, h, cz, L, W, "PlanksGrey")
    for k in range(int(L / 3.0) + 1):                               # posts between the wall panels
        x = cx - L / 2 + k * L / int(L / 3.0)
        box(g, x, -0.2, h, cz + W / 2 + 0.06, 0.22, 0.12, "Beam")
    box(g, cx, h - 0.25, h, cz + W / 2 + 0.08, L, 0.14, "Beam")
    for k in range(int(L / 3.0)):
        x = cx - L / 2 + (k + 0.5) * L / int(L / 3.0)
        if k % 2 == 0:
            window(g, x, h * 0.45, cz + W / 2, 0.8, 0.8)
    R = W / 2 + 0.5; segs = 14; rise = W * 0.42
    for i in range(segs):
        a0, a1 = math.pi * i / segs, math.pi * (i + 1) / segs
        if hole and 4 <= i <= 8:
            for k in range(5):                                       # burnt through: only the ribs remain
                x = cx + 1.0 + k * 1.6
                beam(g, (x, h + rise * math.sin(a0), cz + R * math.cos(a0)), (x, h + rise * math.sin(a1), cz + R * math.cos(a1)), 0.14, 0.14, "Charred")
            continue
        p = [(cz + R * math.cos(a0), h + rise * math.sin(a0)), (cz + R * math.cos(a1), h + rise * math.sin(a1)),
             (cz + (R - 0.18) * math.cos(a1), h + (rise - 0.18) * math.sin(a1)), (cz + (R - 0.18) * math.cos(a0), h + (rise - 0.18) * math.sin(a0))]
        prism(g, p[::-1], 'x', cx - L / 2 - 0.4, cx + L / 2 + 0.4, "RoofOld")
    for s in (-1, 1):                                                # the end walls under the vault
        pts = [(cz + R * math.cos(math.pi * k / segs) * 0.92, h + rise * 0.92 * math.sin(math.pi * k / segs)) for k in range(segs + 1)]
        for k in range(segs):
            a, b = pts[k], pts[k + 1]
            prism(g, [(a[0], h), (b[0], h), (b[0], b[1]), (a[0], a[1])][::(1 if s > 0 else -1)], 'x',
                  cx + s * L / 2 - 0.1, cx + s * L / 2 + 0.1, "PlanksGrey")
    for k in range(5):                                               # roof ribs
        x = cx - L / 2 + 0.4 + k * (L - 0.8) / 4
        for i in range(segs):
            if hole and 4 <= i <= 8:
                continue
            a0, a1 = math.pi * i / segs, math.pi * (i + 1) / segs
            beam(g, (x, h + (rise + 0.06) * math.sin(a0), cz + (R + 0.06) * math.cos(a0)),
                 (x, h + (rise + 0.06) * math.sin(a1), cz + (R + 0.06) * math.cos(a1)), 0.16, 0.06, "Beam")

def hf(x, z):
    """Terrain height (Godot y) beyond the town: the lower town and the valley straight ahead at the market level,
    the upper town's level either side of it, then the land rolling up to the hills (kept low straight ahead so
    the view down the market street ends in the town and the mountains, not a green hillside)."""
    d = -z; ax = abs(x)
    base = (LY - 0.05) + (-0.06 - (LY - 0.05)) * smoothstep(25.0, 37.5, ax)
    r = smoothstep(135.0, 240.0, d)
    hills = 0.45 * (9.0 * (0.5 + 0.5 * math.sin(x * 0.017 + 1.3)) * (0.5 + 0.5 * math.cos(z * 0.019 + 0.4))
             + 5.0 * math.sin(x * 0.041 - z * 0.013 + 0.7) + 3.5 * math.cos(x * 0.0071 + z * 0.031))
    hills = (hills + 6.0) * (0.3 + 0.7 * smoothstep(25.0, 90.0, ax))
    side = min(max((ax - 70.0) / 120.0, 0.0), 1.0) * 10.0 * min(max((d - 50.0) / 40.0, 0.0), 1.0)
    far = min(max((d - 230.0) / 220.0, 0.0), 1.0) * 6.0
    return base * (1.0 - r) + r * (-0.06 + hills) + side + far

MILLS = []

def mountain_range(g, z0, depth, h0, h1, seed, m, step, gap=None):
    """A range of mountains as one heightfield band: a jagged crest (several peaks, saddles and spurs) rising
    from the valley floor at z0 and falling away behind; gap = (x0, x1, f) lowers the crest between x0..x1."""
    gg = grp(g); bm = gg.bm; rnd = random.Random(seed)
    peaks = [(rnd.uniform(-900, 900), rnd.uniform(h0, h1) * rnd.uniform(0.8, 1.35), rnd.uniform(40, 140)) for _ in range(34)]
    ph = [rnd.uniform(0, 6.28) for _ in range(6)]
    def crest(x):
        c = h0 * 0.55 + h0 * 0.18 * math.sin(x * 0.011 + ph[0]) + h0 * 0.1 * math.sin(x * 0.031 + ph[1])
        for (px, ph_, w) in peaks:
            c = max(c, ph_ * math.exp(-((x - px) / w) ** 2) * (0.85 + 0.15 * abs(math.sin(x * 0.07 + ph[2]))))
        c += 2.5 * abs(math.sin(x * 0.13 + ph[3])) + 1.2 * abs(math.sin(x * 0.37 + ph[4]))      # rocky jags
        if gap and gap[0] < x < gap[1]:
            c *= gap[2] + (1 - gap[2]) * (1 - math.sin(math.pi * (x - gap[0]) / (gap[1] - gap[0])))
        return c
    xs = [-1000 + step * i for i in range(int(2000 / step) + 1)]
    T = [0.0, 0.12, 0.28, 0.45, 0.6, 0.78, 1.0]
    rows = []
    for t in T:
        row = []
        for x in xs:
            c = crest(x)
            prof = (t / 0.45) ** 0.9 if t <= 0.45 else 1.0 - ((t - 0.45) / 0.55) ** 1.4 * 0.7
            y = -6.0 + (c + 6.0) * prof + (rnd.uniform(-1.0, 1.0) if 0 < t < 1 else 0.0)
            row.append(bm.verts.new(G(x, y, z0 - t * depth + 0.15 * depth * math.sin(x * 0.006 + ph[5]))))
        rows.append(row)
    faces = []
    for j in range(len(T) - 1):
        for i in range(len(xs) - 1):
            faces.append(bm.faces.new((rows[j][i], rows[j][i + 1], rows[j + 1][i + 1], rows[j + 1][i])))
    bmesh.ops.recalc_face_normals(bm, faces=faces)
    for f in faces:
        if f.normal.y > 0:          # face the arena (Blender -y = Godot +z)
            f.normal_flip()
    _tag(gg, faces, m)
    for f in faces:
        f.smooth = True

def windmill(mx, mz, s, k):
    g = "CE_Far"; my = hf(mx, mz) - 0.5
    lathe(g, mx, my, mz, [(0, 0), (3.2 * s, 0.0), (2.9 * s, 1.0 * s), (2.1 * s, 11.0 * s), (2.3 * s, 11.3 * s), (0, 11.3 * s)], 12, "Mill")
    lathe(g, mx, my + 11.0 * s, mz, [(0, 0), (2.5 * s, 0.0), (2.2 * s, 1.3 * s), (1.1 * s, 2.8 * s), (0, 3.2 * s)], 10, "FarRoof")
    hcyl(g, (mx, my + 11.9 * s, mz + 1.5 * s), (mx, my + 11.9 * s, mz + 3.2 * s), 0.35 * s, "Iron", 8)
    R = 10.0 * s; c = (mx, my + 11.9 * s, mz + 3.25 * s)
    card("CE_Sails", [(c[0] - R, c[1] - R, c[2]), (c[0] + R, c[1] - R, c[2]), (c[0] + R, c[1] + R, c[2]), (c[0] - R, c[1] + R, c[2])], k, "SailsCard")
    MILLS.append(c)

def build_far():
    g = "CE_Far"; rnd = random.Random(31)
    barn(-36.0, -62.0, 16.0, 9.0, 4.0, 1, hole=False)                         # one long barn on the left
    barn(36.0, -66.0, 14.0, 8.0, 3.8, 2, hole=BURN)                            # a smaller one far right
    # the terrain beyond the town floor
    bm = grp(g).bm
    xs = [-500 + 12.5 * i for i in range(81)]
    zs = [-70 - 12 * j for j in range(45)]
    V2 = [[bm.verts.new(G(x, hf(x, z), z)) for x in xs] for z in zs]
    faces = []
    for j in range(len(zs) - 1):
        for i in range(len(xs) - 1):
            faces.append(bm.faces.new((V2[j][i], V2[j][i + 1], V2[j + 1][i + 1], V2[j + 1][i])))
    bmesh.ops.recalc_face_normals(bm, faces=faces)
    for f in faces:
        if f.normal.z < 0:
            f.normal_flip()
    _tag(grp(g), faces, "Land")
    for s in (-1, 1):
        a, b = sorted((s * 49.0, s * 500.0))
        box(g, (a + b) / 2, -1.0, -0.08, -25.0, b - a, 96.0, "Land")
    # the rest of the town: rows of red roofs behind the barns, thinning out into the fields
    for k in range(22):
        x = rnd.uniform(-95, 95); z = rnd.uniform(-90, -140)
        if abs(x) < 30:                                      # keep the view behind the arch open toward the mountains
            continue
        w, d = rnd.uniform(6, 10), rnd.uniform(5, 8); y = hf(x, z)
        h = rnd.uniform(3.6, 6.0)
        gable(g, x - w / 2, x + w / 2, z - d / 2, z + d / 2, y - 0.5, y + h, y + h + rnd.uniform(2.2, 3.2), "FarWall",
              rnd.choice(("FarRoof", "FarRoof", "FarSlate", "FarThatch")), rnd.choice(('x', 'z')), 0.4, 0.25)
    for k in range(16):                                                 # farmsteads farther out
        x = rnd.uniform(-320, 320); z = rnd.uniform(-160, -380); y = hf(x, z)
        w, d = rnd.uniform(7, 11), rnd.uniform(5, 7)
        gable(g, x - w / 2, x + w / 2, z - d / 2, z + d / 2, y - 0.5, y + 4.0, y + 6.8, "FarWall", "FarRoof", 'x', 0.4, 0.3)
    # windmills on the low hills (Refs 1, 4, 8)
    for k, (x, z, s) in enumerate(((-52.0, -150.0, 1.0), (44.0, -160.0, 0.9))):
        windmill(x, z, s, k)
    # woods and hedgerow trees
    for (cx, cz, n, R) in ((-120, -110, 18, 24), (110, -126, 18, 22), (60, -250, 22, 34), (-90, -280, 26, 40), (210, -240, 20, 34),
                           (-230, -180, 20, 30), (0, -330, 22, 50), (-41, -96, 6, 9), (41, -100, 6, 9)):
        for k in range(n):
            a = rnd.uniform(0, 2 * math.pi); r = R * math.sqrt(rnd.random())
            x, z = cx + r * math.cos(a), cz + r * math.sin(a)
            ico(g, (x, hf(x, z) + rnd.uniform(3.0, 5.0), z), rnd.uniform(3.0, 5.4), "Forest", int(cx * 7 + k), 0.9)
    for k in range(30):
        x = rnd.uniform(-300, 300); z = rnd.uniform(-110, -400)
        ico(g, (x, hf(x, z) + 3.5, z), rnd.uniform(2.5, 4.0), "Forest", 3000 + k, 0.95)
    # layered mountain ranges: forested blue-green foothills, then blue-green peaks, then pale blue peaks far off
    mountain_range(g, -170.0, 60.0, 16.0, 30.0, 11, "MtnNear", 6.0)
    mountain_range(g, -300.0, 110.0, 34.0, 52.0, 23, "MtnMid", 9.0)
    mountain_range(g, -520.0, 180.0, 60.0, 90.0, 37, "MtnFar", 14.0)
    if BURN:
        for (x, y, z, sz) in ((-40, 4, -96, 3.6), (36, 4, -102, 3.8), (-68, 4, -124, 4.0), (70, 5, -132, 4.0)):
            FIRES.append((x, hf(x, z) + y, z, sz))
            SMOKES.append((x, hf(x, z) + y + 2, z, sz * 2.6)) if x < 50 else None

# ======================================================================
#  plaza props
# ======================================================================
def market_cart(x, z, rot, seed, goods=("Cabbage", "Apple", "Orange")):
    g = "CE_Props"; rnd = random.Random(seed); ca, sa = math.cos(math.radians(rot)), math.sin(math.radians(rot))
    def P(u, y, v):
        return (x + u * ca + v * sa, y, z - u * sa + v * ca)
    obox(g, P(0, 0.75, 0), (2.4, 0.12, 1.3), rot, "PlanksLight", 0.02)
    for s in (-1, 1):
        obox(g, P(0, 1.0, s * 0.62), (2.4, 0.4, 0.06), rot, "PlanksLight", 0.01)
        hcyl(g, P(0.2, 0.55, s * 0.72), P(0.2, 0.55, s * 0.8), 0.55, "BeamDark", 14)
        beam(g, P(1.2, 0.7, s * 0.4), P(2.6, 0.3, s * 0.35), 0.08, 0.08, "Beam")
    for k in range(16):
        ico(g, P(rnd.uniform(-1.0, 1.0), 1.02 + rnd.uniform(0, 0.15), rnd.uniform(-0.45, 0.45)), 0.15, rnd.choice(goods), seed * 40 + k, 0.85)

def wrecked_cart(x, z):
    """A toppled hand cart: tilted bed, one wheel on its axle, one wheel fallen flat, spilled crates."""
    g = "CE_Props"
    obox(g, (x, 0.55, z), (2.4, 0.12, 1.3), 18, "Charred", 0.02)
    obox(g, (x - 0.2, 0.95, z - 0.62), (2.3, 0.6, 0.08), 18, "Planks", 0.01)
    beam(g, (x + 1.2, 0.5, z + 0.3), (x + 2.8, 0.05, z + 0.9), 0.1, 0.1, "Beam")
    beam(g, (x + 1.2, 0.5, z - 0.3), (x + 2.7, 0.05, z - 0.2), 0.1, 0.1, "Beam")
    hcyl(g, (x - 0.6, 0.55, z + 0.7), (x - 0.6, 0.55, z + 0.8), 0.55, "BeamDark", 14)
    cyl(g, x + 0.8, 0.0, z - 1.4, 0.55, 0.55, 0.1, "BeamDark", 14)
    for k in range(5):
        crate(x - 1.6 + k * 0.5, 0.0, z - 1.2 + (k % 2) * 0.3, 0.42, k * 17, "PlanksLight" if k % 2 else "Charred")

def build_props():
    g = "CE_Props"; rnd = random.Random(5)
    lx, lz = LEFT_SHIFT; rx, rz = RIGHT_SHIFT
    # low fences along both sides of the front of the floor, turning in to meet the fences round the court
    for s in (-1, 1):
        x6, z6 = court_xz(6, COURT_R + 2.2)
        fence(s * 13.7, 7.0, s * 13.7, 0.5, 1.15, broken=((1, 2) if BURN and s < 0 else ((1,) if BURN else ())))
        fence(s * 13.7, 0.5, s * x6, z6, 1.15, broken=((2,) if BURN else ()))
    # benches, a planter and lamps at the front corners, outside the fight lane
    bench(-13.3, -4.0, -90, broken=BURN)
    bench(13.3, -2.5, 90)
    planter(13.6, -6.6, 0.8, 1.5, 0.6, 905, smashed=BURN)
    planter(-13.5, 1.8, 0.8, 1.5, 0.6, 906)
    lamp(-13.4, -7.4, 4.0)
    tree(-17.6, -5.2, 1.1, 21, burnt=BURN)
    tree(-35.0, -32.0, 1.1, 23)
    tree(-18.5, -31.5, 0.9, 24, burnt=BURN)
    tree(33.0, -24.0, 1.1, 25)
    tree(17.5, -40.5, 0.85, 26, burnt=BURN)
    # goods on the store porch and by its far end
    for k, (z, s_) in enumerate(((-23.0, 0.6), (-22.3, 0.5), (-14.2, 0.6))):
        crate(-10.4 + lx, 0.4, z + lz, s_, k * 23)
    crate(-10.4 + lx, 1.0, -22.95 + lz, 0.5, 40)
    barrel(-15.2, -27.7)
    for k in range(4):
        sack(-16.4 - (k % 2) * 0.5, -28.6 - k * 0.55, 300 + k)
    if not BURN:
        for k in range(5):                                          # hay sacks by the store
            rock(g, -17.7 + rnd.uniform(-0.3, 0.3), 0.25, -27.4 - k * 0.45, 0.42, 0.24, 0.32, 500 + k, "Sack", 2, 0.06)
        return
    # --- the burning town: rubble, wrecks, spilled goods ---
    wrecked_cart(-9.4, -25.0)
    for (x, z, r, n) in ((-16.2, -29.4, 1.5, 20), (18.0, -33.4, 1.6, 22), (-15.2, 1.0, 1.1, 10), (16.0, -8.2, 1.2, 12)):
        rubble_pile(x, z, r, n, int(x * 13 - z * 7))
    for k in range(30):
        x = rnd.uniform(-18, 18); z = rnd.uniform(-30, -6)
        if math.hypot(x - COURT[0], z - COURT[1]) < COURT_R + 0.6 or (abs(x) < LANE_X and z > LANE_Z):
            continue
        if rnd.random() < 0.5:
            ico(g, (x, 0.1, z), 0.11, rnd.choice(("Apple", "Orange", "Cabbage", "Bread")), 900 + k, 0.8)
        else:
            beam(g, (x, 0.08, z), (x + rnd.uniform(-1.2, 1.2), 0.1, z + rnd.uniform(-0.6, 0.6)), 0.12, 0.08, rnd.choice(("Charred", "PlanksLight")))
    for k in range(4):
        crate(rnd.uniform(-17.0, -15.0), 0.0, rnd.uniform(-5.0, -12.0), 0.5, rnd.uniform(0, 90), "Charred")
    for (x, y, z, s_) in ((-13.0 + lx, 5.0, -15.4 + lz, 1.6), (-11.4 + lx, 0.9, -21.4 + lz, 0.8), (12.5 + rx, 3.2, -18.5 + rz, 1.3),
                         (16.0 + rx, 6.2, -16.5 + rz, 1.5), (12.2 + rx, 0.3, -28.4 + rz, 1.4), (27.5 + rx, 5.4, -35.0 + rz, 2.0),
                         (-21.0 + lx, 5.0, -32.5 + lz, 1.8), (36.0, 4.4, -64.0, 2.6), (-36.0, 4.2, -60.5, 2.0),
                         (-16.2, 0.3, -29.4, 1.2), (18.0, 0.3, -33.4, 1.2), (16.0, 0.2, -8.2, 0.7)):
        FIRES.append((x, y, z, s_))
    SMOKES.extend([(-14.0 + lx, 6.0, -16.0 + lz, 4.5), (15.5 + rx, 7.0, -17.0 + rz, 5.0), (27.5 + rx, 6.0, -36.0 + rz, 6.0),
                   (36.0, 6.0, -65.0, 8.5), (-36.0, 6.0, -61.5, 7.0), (-21.0 + lx, 6.5, -33.5 + lz, 6.0)])

# ======================================================================
#  cards: bunting, the crowd, grass, windmill sails, fire, smoke, haze, sky
# ======================================================================
def pennants(A, B, sag, fid0, hang=False, ground=0.0):
    """A string of triangular pennants from A to B. UV.x = 0..1 across a flag, UV.y = flag id + v (0 = top edge).
    hang: snapped and hanging (A is where it is still tied, B where its end lies)."""
    g = grp("CE_Bunting", "Cards"); A, B = Vector(A), Vector(B); L = (B - A).length
    n = max(2, int(L / 0.5)); fid = fid0
    def pt(t):
        p = A.lerp(B, t)
        if hang:
            p.y = A.y + (B.y - A.y) * (t ** 0.5)
        else:
            p.y -= sag * 4 * t * (1 - t)
        return p
    for k in range(n):
        t0, t1 = (k + 0.2) / n, (k + 0.8) / n
        p0, p1 = pt(t0), pt(t1); tip = (p0 + p1) / 2; tip.y -= 0.28
        if hang and p1.y < ground + 0.3:
            continue
        quad(g, [tuple(p0), tuple(tip), tuple(p1)], [(0, fid + 0.001), (0.5, fid + 0.999), (1, fid + 0.001)], "BuntingCard")
        fid += 1
    for k in range(14):
        beam("CE_Props", tuple(pt(k / 14)), tuple(pt((k + 1) / 14)), 0.02, 0.02, "BeamDark")
    return fid

def build_bunting(arch_top):
    fid = 0
    if not BURN:     # two strings of pennants from the finial on the arch: to the wooden house's gable and to the wrecked frame
        fid = pennants(arch_top, (-10.5, 7.05, -26.2), 1.1, fid)
        fid = pennants(arch_top, (4.85, 6.3, -26.6), 0.9, fid)
    else:      # snapped strings hanging down
        fid = pennants(arch_top, (-3.6, 0.05, ARCH_Z - 1.6), 0.0, fid, hang=True)
        fid = pennants((-10.5, 6.6, -26.2), (-7.4, 0.05, -24.4), 0.0, fid, hang=True)
        fid = pennants((4.85, 6.0, -26.6), (6.6, 1.4, -25.6), 0.0, fid, hang=True)

# the crowd of shadow figures. pose: 0 cheer (both arms up) 1 clap 2 watch (hands on hips) 3 wave one arm
#   4 child jumping; burning: 5 hands to the face 6 hugging themselves 7 looking about, restless 8 carrying a bucket
#   9 sitting slumped
def person(x, y, z, h, pose, seed):
    CROWD.append((x, y, z, h, pose, seed))
    w = h * 0.7; hh = h * 1.18
    sd = float(seed % 997)
    card("CE_Crowd", [(x - w / 2, y, z), (x + w / 2, y, z), (x + w / 2, y + hh, z), (x - w / 2, y + hh, z)], pose, "CrowdCard",
         sd + 0.001, sd + 0.999)

def build_crowd():
    rnd = random.Random(99 if not BURN else 98)
    def pick(day_w, burn_w):
        ws = burn_w if BURN else day_w
        r = rnd.random() * sum(ws.values()); acc = 0.0
        for k, v in ws.items():
            acc += v
            if r <= acc:
                return k
        return list(ws)[-1]
    DAY = {0: 3, 1: 3, 2: 2, 3: 2}
    BURNW = {5: 3, 6: 3, 7: 3, 8: 1}
    def group(pts, kids=0.15, day=DAY, burn=BURNW):
        for (x, y, z) in pts:
            kid = rnd.random() < kids
            h = rnd.uniform(1.1, 1.25) if kid else rnd.uniform(1.58, 1.82)
            pose = (4 if not BURN else 6) if kid else pick(day, burn)
            person(x + rnd.uniform(-0.15, 0.15), y, z + rnd.uniform(-0.15, 0.15), h, pose, rnd.randint(1, 9999))
    def line(x0, z0, x1, z1, n, y=0.0):
        return [(x0 + (x1 - x0) * (k + 0.5) / n, y, z0 + (z1 - z0) * (k + 0.5) / n) for k in range(n)]
    if not BURN:
        return            # the day stage is carried by its architecture and set dressing (no crowd)
        group(line(-14.6, -14.0, -14.6, -22.0, 5, 0.35))                       # on the store porch
        group(line(-13.3, -12.6, -13.6, -25.0, 7))                             # along the left side of the plaza
        group(line(13.4, -12.8, 13.6, -26.0, 8))                               # in front of the inn
        group(line(14.7, -14.0, 14.7, -25.0, 5, 4.48), 0.0)                    # on the inn's balcony
        group([(-8.6, 0, -24.6), (-7.2, 0, -26.0), (-4.6, 0, -27.0), (-3.2, 0, -26.4), (3.0, 0, -26.6), (4.8, 0, -27.2),
               (7.6, 0, -25.6), (8.8, 0, -24.2), (-5.8, 0, -25.4), (6.0, 0, -25.0), (-1.4, 0, -27.8), (1.6, 0, -28.0)])
        group(line(-7.6, -31.0, 7.6, -31.2, 11, 0.32), 0.2)                    # on the boardwalk at the gate
        group([(-2.2, 0, -37.0), (2.6, 0, -36.8), (-6.0, 0, -40.5), (6.4, 0, -41.0), (-4.0, 0, -45.0), (4.2, 0, -44.0),
               (-7.2, 0, -50.0), (7.0, 0, -49.0)], 0.1, {2: 3, 3: 2, 0: 1, 1: 1})
        group([(-0.9, 12.22, -50.0), (0.6, 12.22, -50.2), (1.4, 12.22, -49.6)], 0.0, {0: 3, 3: 2})        # up on the headframe
        group([(15.4, 3.56, -30.5), (17.2, 3.56, -30.5), (20.6, 3.56, -30.5)], 0.0, {1: 2, 0: 2})           # on the scaffold
        group(line(-14.6, 5.0, -14.8, -3.0, 4))                                # outside the fences, front corners
        group(line(14.8, 6.0, 15.0, -1.0, 3))
    else:
        lx, lz = LEFT_SHIFT
        group(line(-14.6, -17.0, -14.6, -23.0, 3, 0.4), 0.2)                    # on the store porch
        pts = []
        for (th, r) in ((18, 15.4), (30, 15.4)):                                 # outside the fences round the court
            x, z = court_xz(th, r); pts.append((-x, 0.0, z))
        pts += [(14.87, 0.0, -12.99), (11.87, 0.0, -16.42)]
        group(pts, 0.15)
        x, z = court_xz(25, COURT_R + 1.0)
        person(x - 0.1, 0.0, z + 0.05, 1.7, 9, 4242)                              # slumped on a bench at the rim
        group([(-4.0, 0.0, -27.0), (3.6, 0.0, -27.4), (-0.4, 0.0, -30.4), (3.0, 0.0, -38.4), (-7.0, 0.0, -35.2)],
              0.1, burn={7: 3, 8: 4, 5: 2})                                      # in the market, carrying water
        group([(-14.6, 0, 3.0), (-14.8, 0, -1.6), (14.9, 0, 4.0)], 0.0)

def tuft(x, z, s=1.0, kind=0, seed=0, y=0.0):
    rnd = random.Random(seed)
    w = (0.6 + 0.3 * rnd.random()) * s; h = (0.42 + 0.3 * rnd.random()) * s * (1.6 if kind == 2 else 1.0)
    a = rnd.uniform(0, math.pi)
    for k in range(2):
        aa = a + k * math.pi / 2
        dx, dz = math.cos(aa) * w / 2, math.sin(aa) * w / 2
        sd = float((seed * 7 + k * 13) % 997)
        card("CE_Grass", [(x - dx, y - 0.02, z - dz), (x + dx, y - 0.02, z + dz), (x + dx, y + h, z + dz), (x - dx, y + h, z - dz)], kind, "GrassCard",
             sd + 0.001, sd + 0.999)

def tufts_along(p0, p1, n, s=1.0, seed=0, spread=0.35, kinds=(0, 0, 1, 2)):
    rnd = random.Random(seed)
    for i in range(n):
        t = (i + rnd.random()) / n
        x = p0[0] + (p1[0] - p0[0]) * t + rnd.uniform(-spread, spread)
        z = p0[1] + (p1[1] - p0[1]) * t + rnd.uniform(-spread, spread)
        tuft(x, z, s * rnd.uniform(0.8, 1.2), rnd.choice(kinds), seed * 100 + i)

BUILDINGS = [(-24.2, -13.6, -27.2, -14.8), (-33.6, -20.8, -43.4, -34.6), (-39.2, -30.8, -28.2, -19.8), (-35.7, -28.3, -11.7, -2.3),
             (-14.3, -6.7, -34.9, -24.0), (14.5, 25.5, -31.2, -13.5), (26.7, 37.3, -45.8, -36.2), (31.2, 39.8, -20.8, -11.2),
             (4.2, 14.6, -35.0, -22.8), (5.6, 14.4, -46.4, -37.6), (-18.9, -10.1, -51.9, -42.1), (-9.6, -2.4, -45.9, -34.8)]

def in_building(x, z, m=0.0):
    return any(x0 - m < x < x1 + m and z0 - m < z < z1 + m for (x0, x1, z0, z1) in BUILDINGS)

def build_grass():
    tufts_along((-13.9, 7.0), (-13.9, 0.8), 10, 1.0, 1)                        # along the front fences
    tufts_along((14.1, 7.0), (14.1, 0.8), 8, 1.0, 2)
    x6, z6 = court_xz(6, COURT_R + 2.2)
    tufts_along((-14.0, 0.2), (-x6 - 0.2, z6), 8, 0.9, 5, 0.25)
    tufts_along((14.2, 0.2), (x6 + 0.2, z6), 7, 0.9, 6, 0.25)
    tufts_along((-13.6, -15.8), (-13.6, -26.4), 8, 0.8, 3, 0.2, (0, 1))        # along the store porch
    tufts_along((15.7, -17.4), (15.7, -30.4), 8, 0.8, 4, 0.2, (0, 1))          # under the scaffold
    tufts_along((-30.0, -33.6), (-20.2, -33.6), 10, 0.9, 7)
    rnd = random.Random(8)
    for k in range(60):                                                         # round the court's rim, the corners, the trees
        x = rnd.choice((-1, 1)) * rnd.uniform(9.0, 30.0); z = rnd.uniform(-34.0, 10.0)
        if math.hypot(x - COURT[0], z - COURT[1]) < COURT_R + 0.6 or (abs(x) < LANE_X + 0.5 and z > LANE_Z) or in_building(x, z, 0.3):
            continue
        tuft(x, z, rnd.uniform(0.9, 1.3), rnd.choice((0, 0, 1, 2)), 1200 + k)
    for k in range(26):                                                         # in the joints of the curb band round the court
        th = rnd.uniform(-5.0, 185.0); x, z = court_xz(th, COURT_R - rnd.uniform(0.1, 0.4))
        if (abs(x) < LANE_X + 0.5 and z > LANE_Z) or (abs(x) < ARCH_HALF + 1.4 and z < ARCH_Z + 1.2):
            continue
        tuft(x, z, 0.55, rnd.choice((0, 1)), 1400 + k)

HAZE = [(-46.0, 10.0, 70.0), (-66.0, 16.0, 95.0), (-100.0, 26.0, 150.0), (-160.0, 44.0, 250.0)]

def build_fire_cards():
    """Crossed quads per flame / smoke column; camera-facing haze layers (burning). UV.x across, UV.y = id + height."""
    for i, (x, y, z, s) in enumerate(FIRES):
        for a in (0.0, math.pi / 2):
            dx, dz = math.cos(a) * s * 0.6, math.sin(a) * s * 0.6
            quad("CE_Fire", [(x - dx, y, z - dz), (x + dx, y, z + dz), (x + dx, y + s * 1.9, z + dz), (x - dx, y + s * 1.9, z - dz)],
                 [(0, i + 0.001), (1, i + 0.001), (1, i + 0.999), (0, i + 0.999)], "FireCard")
    for i, (x, y, z, s) in enumerate(SMOKES):
        for a in (0.3, 0.3 + math.pi / 2):
            dx, dz = math.cos(a) * s, math.sin(a) * s
            quad("CE_Smoke", [(x - dx, y, z - dz), (x + dx, y, z + dz), (x + dx * 1.8, y + s * 5.0, z + dz * 1.8), (x - dx * 1.8, y + s * 5.0, z - dz * 1.8)],
                 [(0, i + 0.001), (1, i + 0.001), (1, i + 0.999), (0, i + 0.999)], "SmokeCard")
    if BURN:
        for i, (z, top, hw) in enumerate(HAZE):
            quad("CE_Haze", [(-hw, LY - 0.8, z), (hw, LY - 0.8, z), (hw, top, z), (-hw, top, z)],
                 [(0, i + 0.001), (2 * hw / 20.0, i + 0.001), (2 * hw / 20.0, i + 0.999), (0, i + 0.999)], "SmokeCard")

def build_sky():
    g = grp("CE_Sky", "Cards"); n = 128; y0, y1 = -80.0, 620.0
    for i in range(n):
        t0, t1 = i / n, (i + 1) / n
        A0, A1 = 2 * math.pi * t0 - math.pi, 2 * math.pi * t1 - math.pi
        p0 = (SKY_R * math.sin(A0), 0, -100 - SKY_R * math.cos(A0)); p1 = (SKY_R * math.sin(A1), 0, -100 - SKY_R * math.cos(A1))
        quad(g, [(p0[0], y0, p0[2]), (p1[0], y0, p1[2]), (p1[0], y1, p1[2]), (p0[0], y1, p0[2])], [(t0, 0), (t1, 0), (t1, 1), (t0, 1)], "SkyCard")

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
    if V["sun_energy"] > 0:
        sd = bpy.data.lights.new("Sun", 'SUN'); sd.energy = V["sun_energy"]; sd.color = srgb(V["sun_color"]); sd.angle = math.radians(3.5)
        s = bpy.data.objects.new("Sun", sd); col("Lights").objects.link(s)
        d = Vector(V["sun_dir"]).normalized()
        s.rotation_mode = 'QUATERNION'; s.rotation_quaternion = Vector((d.x, -d.z, d.y)).to_track_quat('-Z', 'Y')
    for name, pos, aim, size, (power, colr) in (("Fill_Front", (0, 18, 30), (0, 2, -15), (70, 25), V["fill"]),
                                                ("Fill_Sky", (0, 60, -20), (0, 0, -20), (90, 90), V["top"])):
        ld = bpy.data.lights.new(name, 'AREA'); ld.shape = 'RECTANGLE'
        ld.size, ld.size_y = size; ld.energy = power; ld.color = srgb(colr)
        o = bpy.data.objects.new(name, ld); col("Lights").objects.link(o); o.location = G(*pos)
        o.rotation_mode = 'QUATERNION'; o.rotation_quaternion = (G(*aim) - G(*pos)).normalized().to_track_quat('-Z', 'Y')
        o.visible_camera = False
    def point(name, p, wts, colr, rad=0.3):
        ld = bpy.data.lights.new(name, 'POINT'); ld.energy = wts; ld.color = srgb(colr); ld.shadow_soft_size = rad
        o = bpy.data.objects.new(name, ld); col("Lights").objects.link(o); o.location = G(*p); o.visible_camera = False
    if V["lamp_w"] > 0:
        for k, (x, z, h) in enumerate(LAMPS):
            point("Fill_Lamp%d" % k, (x, h - 0.15, z + 0.4), V["lamp_w"], "#ffbe78", 0.2)
    if V["window_w"] > 0:
        rnd = random.Random(3)
        for k, (x, y, z, a) in enumerate(WINDOWS):
            if rnd.random() < 0.55:          # not every window has a fire behind it
                point("Fill_Window%d" % k, (x, y, z + 0.6), V["window_w"] * a, V["window_color"], 0.5)
    if V["fire_w"] > 0:
        for k, (x, y, z, s) in enumerate(FIRES):
            if -z > 90:
                continue
            point("Fill_Fire%d" % k, (x, y + s * 0.6, z + 0.3), V["fire_w"] * s * s, V.get("fire_color", "#ff6a24"), s * 0.5)

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
        ("CAM_jump_far", (0, 7.5, 16.0)), ("CAM_court", (0, 1.7, -3.0), 4.0),          # inside the court, looking at the arch
        ("CAM_court_high", (0, 11.0, 8.0), -24.0))                                    # high over the floor, the round court below

def build_cameras():
    for c in CAMS:
        name, pos = c[0], c[1]; pitch = c[2] if len(c) > 2 else 0.0; yaw = c[3] if len(c) > 3 else 0.0
        cd = bpy.data.cameras.new(name); cd.sensor_fit = 'VERTICAL'; cd.angle_y = math.radians(30)
        cd.clip_start = 0.1; cd.clip_end = 1500
        o = bpy.data.objects.new(name, cd); col("Cameras").objects.link(o)
        o.location = G(*pos); o.rotation_euler = (math.radians(90 + pitch), 0, math.radians(yaw))
    bpy.context.scene.camera = bpy.data.objects["CAM_mid"]

CARD_GROUPS = ("CE_Sky", "CE_Window", "CE_Bunting", "CE_Crowd", "CE_Grass", "CE_Sails", "CE_Fire", "CE_Smoke", "CE_Haze")
HIDDEN = ("CE_Bunting", "CE_Crowd", "CE_Grass", "CE_Sails", "CE_Fire", "CE_Smoke", "CE_Haze")

def build_all():
    reset(); COLS.clear(); MATS.clear(); GR.clear()
    for L in (WINDOWS, LAMPS, FIRES, SMOKES, CROWD, MILLS):
        L.clear()
    build_materials()
    build_floor()
    arch_top = build_arch()
    shifted(*LEFT_SHIFT, build_left); shifted(*RIGHT_SHIFT, build_right)
    build_court(); build_market(); build_ground(); build_lower_town()
    build_props(); build_far()
    build_bunting(arch_top); build_crowd(); build_grass(); build_fire_cards(); build_sky(); build_preview()
    objs = {name: g.finish() for name, g in list(GR.items())}
    for n in CARD_GROUPS:
        if n in objs:
            objs[n].visible_shadow = False
    for n in HIDDEN:
        if n in objs:
            objs[n].hide_render = True          # Godot only (fires light the bake through point lights)
    build_lights(); build_cameras(); setup_render()
    tris = {o.name: sum(len(p.vertices) - 2 for p in o.data.polygons) for o in objs.values()}
    return {"variant": VARIANT, "objects": list(objs), "tris": tris, "total_tris": sum(tris.values()),
            "fires": len(FIRES), "smokes": len(SMOKES), "crowd": len(CROWD), "windows": len(WINDOWS)}

if __name__ == "__main__":
    BUILD_INFO = build_all()
