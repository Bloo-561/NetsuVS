# The GeoFront - 3D stage build script (Blender 5.x, runs in --background). Version 2 ("vault"), from the
# updated painting: a round blue steel chamber with a giant circular vault door at the back - glowing circuit
# lines on its outer ring, a cross lock with hazard-striped arms - tall dark pillars with glowing ribbed
# sections, amber lamps and pipe rails along the arena edge, ramps at the sides, and a diamond-plate floor
# with a hazard-ringed grate in the middle (the floor is drawn by Godot's gf_floor shader).
#
#   blender --background --factory-startup --python run_gf.py -- STEPS=build,bake,preview,export CAMS=CAM_mid
#
# Layout is written in GODOT coordinates (x right, y up, +z toward the camera) and converted
# to Blender (Z-up) by G():  Godot (x, y, z) -> Blender (x, -z, y).  1 unit = 1 m.
# Baked groups (atlases): GF_Walls, GF_Machines, GF_Floor (light map only)
# Card group (Godot shader, it still emits in the bake): GF_Glow - Blender UV.y = 2 * id + t, ids:
#   0 wall light strips   1 vault circuit lines   2 pillar rib glow   3 amber lamps   4 vault slot lines
# Exports geofront_vault.glb / textures/floor_light_vault.png (the first GeoFront's files stay as they were).
import bpy, bmesh, math, random
from mathutils import Vector, Matrix

ROOT = r"E:\Netsu Projects\Netsu Fighter\Godot\netsu-vs\stages\geofront"
TEXD = ROOT + r"\textures"
VARIANT = globals().get("VARIANT") or "vault"

# ---------------- layout (Godot space, metres) ----------------
FLOOR_X = 26.0                     # floor quad: x +-26, z -31.5..+18
FLOOR_BACK, FLOOR_FRONT = -31.5, 18.0
LANE_X, LANE_Z = 12.5, -9.0        # keep |x| < 12.5 and z > -9 clear (fight lane)
CENTER_Z = -6.0
WALL_R, WALL_C, WALL_H = 25.0, -6.0, 17.0      # round chamber wall: radius, centre z, height
# lighting
WORLD_COLOR, WORLD_STRENGTH = "#060a14", 0.35
TOP_COLOR, TOP_W = "#8cb4ff", 4200
FILL_COLOR, FILL_W = "#b4c4e0", 2200

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
#  shape helpers
# ======================================================================
def lathe(g, x, y0, z, prof, seg=12, m="Metal", rot=0.0):
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

def xy_prism(g, pts, z0, z1, m):
    """A convex outline in the x-y plane (Godot), pushed from z0 (back) to z1 (front)."""
    gg = grp(g) if isinstance(g, str) else g; bm = gg.bm
    F = [bm.verts.new(G(x, y, z1)) for x, y in pts]
    B = [bm.verts.new(G(x, y, z0)) for x, y in pts]
    faces = [bm.faces.new(F), bm.faces.new(B[::-1])]
    n = len(pts)
    for i in range(n):
        j = (i + 1) % n
        faces.append(bm.faces.new((F[i], B[i], B[j], F[j])))
    bmesh.ops.recalc_face_normals(bm, faces=faces)
    _tag(gg, faces, m)
    return faces

def annulus(g, cx, cy, r0, r1, z0, z1, m, n=48, a0=0.0, a1=2 * math.pi, gap=0.0):
    """A ring (or ring sector) in the x-y plane, n segments; gap (radians) leaves a slit between segments."""
    for k in range(n):
        A = a0 + (a1 - a0) * k / n + gap / 2; B = a0 + (a1 - a0) * (k + 1) / n - gap / 2
        pts = [(cx + r0 * math.sin(A), cy + r0 * math.cos(A)), (cx + r0 * math.sin(B), cy + r0 * math.cos(B)),
               (cx + r1 * math.sin(B), cy + r1 * math.cos(B)), (cx + r1 * math.sin(A), cy + r1 * math.cos(A))]
        xy_prism(g, pts, z0, z1, m)

def disc(g, cx, cy, r, z0, z1, m, n=48):
    xy_prism(g, [(cx + r * math.sin(2 * math.pi * k / n), cy + r * math.cos(2 * math.pi * k / n)) for k in range(n)][::-1], z0, z1, m)

def rect_xy(g, x0, x1, y0, y1, z0, z1, m, rot=0.0, cx=None, cy=None):
    """Rectangle in the x-y plane, optionally turned by rot (radians) about (cx, cy)."""
    pts = [(x0, y0), (x1, y0), (x1, y1), (x0, y1)]
    if rot:
        cx = (x0 + x1) / 2 if cx is None else cx; cy = (y0 + y1) / 2 if cy is None else cy
        c, s = math.cos(rot), math.sin(rot)
        pts = [(cx + (x - cx) * c - (y - cy) * s, cy + (x - cx) * s + (y - cy) * c) for x, y in pts]
    xy_prism(g, pts, z0, z1, m)

def torus_h(g, cx, y, cz, R, r, m, nR=24, nr=6):
    """Horizontal torus (a rib around a pillar)."""
    gg = grp(g); bm = gg.bm
    rings = [[bm.verts.new(G(cx + (R + r * math.cos(2 * math.pi * j / nr)) * math.cos(2 * math.pi * i / nR), y + r * math.sin(2 * math.pi * j / nr),
                             cz + (R + r * math.cos(2 * math.pi * j / nr)) * math.sin(2 * math.pi * i / nR))) for j in range(nr)] for i in range(nR)]
    faces = []
    for i in range(nR):
        A, B = rings[i], rings[(i + 1) % nR]
        for j in range(nr):
            k = (j + 1) % nr
            faces.append(bm.faces.new((A[j], B[j], B[k], A[k])))
    bmesh.ops.recalc_face_normals(bm, faces=faces)
    _tag(gg, faces, m)

def glow_strip(pts, z, wd, fid, mat="GlowBlue", watts=0.0, colour="blue"):
    """A flat glowing strip along a 2D polyline in the x-y plane at depth z (card group GF_Glow).
    Blender UV.y = 2 * id + t, t = 0..1 along the whole line (pulses run along it)."""
    g = grp("GF_Glow", "Cards")
    L = [0.0]
    for a, b in zip(pts[:-1], pts[1:]):
        L.append(L[-1] + math.hypot(b[0] - a[0], b[1] - a[1]))
    tot = max(L[-1], 1e-6)
    for i, (a, b) in enumerate(zip(pts[:-1], pts[1:])):
        dx, dy = b[0] - a[0], b[1] - a[1]; ln = math.hypot(dx, dy)
        if ln < 1e-6:
            continue
        ux, uy = dx / ln, dy / ln; nx, ny = -uy * wd / 2, ux * wd / 2
        ex, ey = ux * wd / 2, uy * wd / 2                                     # overlap the joints
        p0 = (a[0] - ex, a[1] - ey); p1 = (b[0] + ex, b[1] + ey)
        t0, t1 = L[i] / tot, L[i + 1] / tot
        quad(g, [(p0[0] - nx, p0[1] - ny, z), (p1[0] - nx, p1[1] - ny, z), (p1[0] + nx, p1[1] + ny, z), (p0[0] + nx, p0[1] + ny, z)],
             [(0, 2 * fid + t0), (0, 2 * fid + t1), (1, 2 * fid + t1), (1, 2 * fid + t0)], mat)
    if watts > 0:
        for k in range(0, len(pts), 5):
            GLOWS.append((pts[k][0], pts[k][1], z + 0.4, watts, colour))

def glow_quad(pts, fid, mat="GlowAmber"):
    quad(grp("GF_Glow", "Cards"), pts, [(0, 2 * fid), (1, 2 * fid), (1, 2 * fid + 1), (0, 2 * fid + 1)], mat)

def ring_glow(cx, y, cz, r, fid, n=32, mat="GlowBlue", h=0.22):
    """A glowing band around a vertical axis (between the ribs of a pillar)."""
    g = grp("GF_Glow", "Cards")
    for k in range(n):
        a0, a1 = 2 * math.pi * k / n, 2 * math.pi * (k + 1) / n
        quad(g, [(cx + r * math.cos(a0), y - h / 2, cz + r * math.sin(a0)), (cx + r * math.cos(a1), y - h / 2, cz + r * math.sin(a1)),
                 (cx + r * math.cos(a1), y + h / 2, cz + r * math.sin(a1)), (cx + r * math.cos(a0), y + h / 2, cz + r * math.sin(a0))],
             [(k / n, 2 * fid), ((k + 1) / n, 2 * fid), ((k + 1) / n, 2 * fid + 1), (k / n, 2 * fid + 1)], mat)

GLOWS = []        # (x, y, z, watts, colour) point lights for the bake

# ======================================================================
#  materials
# ======================================================================
def metal_material(name, dark, light, panel=1.0, rough=0.45, seams=True, rivets=False):
    b = NB(name)
    n = b.noise(b.pos, 1.4, 4, 0.55)
    c = b.ramp(n.outputs["Fac"], [(0.3, dark), (0.7, light)])
    w = b.n("ShaderNodeTexWave"); w.wave_type = 'BANDS'; w.bands_direction = 'Z'
    w.inputs["Scale"].default_value = 40.0; w.inputs["Distortion"].default_value = 2.0
    b.link(b.pos, w.inputs["Vector"])
    c = b.mixc(c, b.ramp(w.outputs["Fac"], [(0.0, "#d8d8d8"), (1.0, "#ffffff")]), 1.0, 'MULTIPLY')
    if seams:
        br = b.n("ShaderNodeTexBrick"); br.offset = 0.0
        for k, v in (("Scale", 1.0), ("Mortar Size", 0.012), ("Brick Width", 1.2 * panel), ("Row Height", 0.8 * panel)):
            br.inputs[k].default_value = v
        br.inputs["Color1"].default_value = (1, 1, 1, 1); br.inputs["Color2"].default_value = (0.9, 0.92, 0.95, 1)
        br.inputs["Mortar"].default_value = (0.18, 0.2, 0.24, 1)
        b.link(b.uv, br.inputs["Vector"])
        c = b.mixc(c, br.outputs["Color"], 1.0, 'MULTIPLY')
    if rivets:
        v = b.n("ShaderNodeTexVoronoi"); v.inputs["Scale"].default_value = 6.0
        b.link(b.uv, v.inputs["Vector"])
        dot = b.math('LESS_THAN', v.outputs["Distance"], 0.06)
        c = b.mixc(c, "#c8d4e0", b.math('MULTIPLY', dot, 0.5))
    b.link(c, b.bsdf.inputs["Base Color"]); b.bsdf.inputs["Roughness"].default_value = rough
    return b

def plain(name, dark, light, scale=3.0, rough=0.6):
    b = NB(name)
    n = b.noise(b.pos, scale, 4, 0.55)
    b.link(b.ramp(n.outputs["Fac"], [(0.3, dark), (0.7, light)]), b.bsdf.inputs["Base Color"])
    b.bsdf.inputs["Roughness"].default_value = rough
    return b

def hazard_material(name, scale=3.0):
    b = NB(name)
    w = b.n("ShaderNodeTexWave"); w.wave_type = 'BANDS'; w.bands_direction = 'DIAGONAL'
    w.inputs["Scale"].default_value = scale; w.inputs["Distortion"].default_value = 0.0
    b.link(b.pos, w.inputs["Vector"])
    s = b.math('GREATER_THAN', w.outputs["Fac"], 0.5)
    c = b.mixc("#141414", "#d8a820", s)
    n = b.noise(b.pos, 6.0, 3, 0.6)
    c = b.mixc(c, "#3a3226", b.math('MULTIPLY', b.math('GREATER_THAN', n.outputs["Fac"], 0.64), 0.45))
    b.link(c, b.bsdf.inputs["Base Color"]); b.bsdf.inputs["Roughness"].default_value = 0.55
    return b

def emit_solid(name, color, strength):
    b = NB(name)
    em = b.n("ShaderNodeEmission"); em.inputs["Color"].default_value = (*srgb(color), 1); em.inputs["Strength"].default_value = strength
    b.link(em.outputs[0], b.out.inputs[0])
    return b

GLOW_HEX = {"blue": "#3aa0ff", "amber": "#ffa040"}

def build_materials():
    metal_material("Wall", "#16243a", "#22334c", 1.6, 0.5, rivets=True)
    metal_material("WallDark", "#0e1624", "#18233a", 1.2, 0.55)
    metal_material("Metal", "#4a5462", "#6a7584", 1.0, 0.4)
    metal_material("MetalLight", "#7e8a98", "#a8b4c2", 0.8, 0.3)
    metal_material("MetalDark", "#1a222c", "#2a3440", 1.0, 0.45)
    metal_material("Chrome", "#8a96a4", "#c4ccd6", 4.0, 0.2, seams=False)
    metal_material("Pillar", "#141c26", "#222c38", 3.0, 0.4, seams=False)
    hazard_material("Hazard", 3.0)
    plain("Brass", "#7a6034", "#b08a4c", 5.0, 0.35)
    plain("Rubber", "#0c0e12", "#1a1e24", 8.0, 0.8)
    b = NB("Cable")                                                            # twisted cable: diagonal bands
    w = b.n("ShaderNodeTexWave"); w.wave_type = 'BANDS'; w.bands_direction = 'DIAGONAL'
    w.inputs["Scale"].default_value = 9.0; w.inputs["Distortion"].default_value = 0.0
    b.link(b.pos, w.inputs["Vector"])
    b.link(b.ramp(w.outputs["Fac"], [(0.2, "#0a0c10"), (0.5, "#3a4250"), (0.8, "#0a0c10")]), b.bsdf.inputs["Base Color"])
    b.bsdf.inputs["Roughness"].default_value = 0.5
    emit_solid("GlowBlue", GLOW_HEX["blue"], 6.0)
    emit_solid("GlowAmber", GLOW_HEX["amber"], 6.0)
    b = NB("FloorPlate"); b.bsdf.inputs["Base Color"].default_value = (*srgb("#6a7480"), 1); b.bsdf.inputs["Roughness"].default_value = 0.4
    b = NB("Stand_P1"); b.bsdf.inputs["Base Color"].default_value = (*srgb("#2d6cdf"), 1)
    b = NB("Stand_P2"); b.bsdf.inputs["Base Color"].default_value = (*srgb("#e0463a"), 1)

# ======================================================================
#  the chamber
# ======================================================================
def build_floor():
    g = grp("GF_Floor")
    quad(g, [(-FLOOR_X, 0, FLOOR_FRONT), (FLOOR_X, 0, FLOOR_FRONT), (FLOOR_X, 0, FLOOR_BACK), (-FLOOR_X, 0, FLOOR_BACK)],
         [(-FLOOR_X, -FLOOR_FRONT), (FLOOR_X, -FLOOR_FRONT), (FLOOR_X, -FLOOR_BACK), (-FLOOR_X, -FLOOR_BACK)], "FloorPlate")

def wall_point(a, r=None, y=0.0):
    r = WALL_R if r is None else r
    return (r * math.sin(a), y, WALL_C - r * math.cos(a))

def build_walls():
    """The round steel wall: riveted panels, ribs, ledges with blue light strips, a dark upper band, the ceiling."""
    g = "GF_Walls"; n = 56
    for i in range(n):
        a0, a1 = 2 * math.pi * i / n - math.pi, 2 * math.pi * (i + 1) / n - math.pi
        am = (a0 + a1) / 2
        if abs(am) < math.radians(17):                                       # the vault door sits here
            quad(g, [wall_point(a1, WALL_R, -0.2), wall_point(a0, WALL_R, -0.2), wall_point(a0, WALL_R, WALL_H), wall_point(a1, WALL_R, WALL_H)],
                 [(0, 0), (1, 0), (1, 1), (0, 1)], "WallDark")
            continue
        quad(g, [wall_point(a1, WALL_R, -0.2), wall_point(a0, WALL_R, -0.2), wall_point(a0, WALL_R, 8.2), wall_point(a1, WALL_R, 8.2)],
             [(0, 0), (1, 0), (1, 1), (0, 1)], "Wall")
        quad(g, [wall_point(a1, WALL_R, 8.2), wall_point(a0, WALL_R, 8.2), wall_point(a0, WALL_R, WALL_H), wall_point(a1, WALL_R, WALL_H)],
             [(0, 0), (1, 0), (1, 1), (0, 1)], "WallDark")
        x, _, z = wall_point(a0, WALL_R - 0.2)
        rot = -math.degrees(a0)
        obox(g, (x, 4.1, z), (0.36, 8.4, 0.4), rot, "MetalDark", 0.02)                       # rib
        xm, _, zm = wall_point(am, WALL_R - 0.05)
        obox(g, (xm, 0.6, zm), (2 * math.pi * WALL_R / n - 0.4, 1.2, 0.1), -math.degrees(am), "MetalDark")   # skirting panel
        for (y, d, h) in ((2.75, 0.5, 0.18), (5.2, 0.6, 0.2), (8.2, 0.9, 0.3)):              # ledges
            xl, _, zl = wall_point(am, WALL_R - d / 2)
            obox(g, (xl, y, zl), (2 * math.pi * (WALL_R - d / 2) / n + 0.02, h, d), -math.degrees(am), "Metal")
    for (y, rr) in ((2.6, WALL_R - 0.42), (5.03, WALL_R - 0.52)):                            # blue light strips under the ledges
        g2 = grp("GF_Glow", "Cards")
        for i in range(n):
            a0, a1 = 2 * math.pi * i / n - math.pi, 2 * math.pi * (i + 1) / n - math.pi
            if abs((a0 + a1) / 2) < math.radians(17):
                continue
            p = [wall_point(a1, rr, y - 0.07), wall_point(a0, rr, y - 0.07), wall_point(a0, rr, y + 0.07), wall_point(a1, rr, y + 0.07)]
            quad(g2, p, [(0, 0), (1, 0), (1, 1), (0, 1)], "GlowBlue")
            if i % 4 == 0:
                x, _, z = wall_point(a0, rr - 0.5)
                GLOWS.append((x, y, z, 16, "blue"))
    # ceiling: a dark steel dome-ish lid with ring beams
    box(g, 0, WALL_H, WALL_H + 0.4, WALL_C, 2 * WALL_R + 2, 2 * WALL_R + 2, "WallDark")
    for r in (8.0, 15.0, 21.0):
        for k in range(36):
            a0, a1 = 2 * math.pi * k / 36, 2 * math.pi * (k + 1) / 36
            p0, p1 = wall_point(a0, r, WALL_H - 0.4), wall_point(a1, r, WALL_H - 0.4)
            obox(g, ((p0[0] + p1[0]) / 2, WALL_H - 0.2, (p0[2] + p1[2]) / 2), (2 * math.pi * r / 36 + 0.05, 0.4, 0.5), -math.degrees((a0 + a1) / 2), "MetalDark")

# ---------------------------------------------------------------- the vault door
VX, VY, VZ = 0.0, 5.9, -29.6       # centre of the vault door (its front plane is about VZ)
R_OUT = 7.0

def circuit_traces():
    """The glowing angular circuit lines on the outer ring (the left side mirrors the right): each trace is
    (radius, angle-from-top in degrees) corners joined by straight chords (no arcs), with 45-degree jogs."""
    T = [[(6.62, 2), (6.62, 22), (6.12, 30), (6.12, 52), (6.62, 60), (6.62, 82), (6.2, 90), (6.2, 104)],
         [(6.02, 7), (6.02, 20), (6.45, 27), (6.45, 44)],
         [(5.86, 56), (5.86, 74), (6.38, 82)],
         [(6.74, 92), (6.74, 112), (6.18, 120), (6.18, 138), (6.62, 146), (6.62, 162)],
         [(5.88, 112), (5.88, 132)]]
    out = []
    for tr in T:
        pts = []
        for (r0, a0), (r1, a1) in zip(tr[:-1], tr[1:]):
            n = 1 if abs(r1 - r0) > 1e-6 else max(1, int(math.ceil(abs(a1 - a0) / 20.0)))
            for k in range(n):
                a = math.radians(a0 + (a1 - a0) * k / n); r = r0 + (r1 - r0) * k / n
                pts.append((r * math.sin(a), r * math.cos(a)))
        r, a = tr[-1]; pts.append((r * math.sin(math.radians(a)), r * math.cos(math.radians(a))))
        out.append(pts)
    return out

def build_vault():
    g = "GF_Machines"
    # backing plate and the stepped rings
    rect_xy("GF_Walls", -9.5, 9.5, -0.2, WALL_H, VZ - 1.3, VZ - 1.0, "WallDark")
    annulus(g, VX, VY, R_OUT, R_OUT + 0.45, VZ - 1.05, VZ - 0.55, "Metal", 64)
    annulus(g, VX, VY, 5.6, R_OUT, VZ - 1.0, VZ + 0.2, "MetalLight", 64)
    annulus(g, VX, VY, R_OUT - 0.08, R_OUT + 0.05, VZ + 0.2, VZ + 0.32, "Metal", 64)          # raised outer lip
    for k in range(64):                                                       # bolts around the outer ring
        a = 2 * math.pi * (k + 0.5) / 64
        x, y = VX + 6.82 * math.sin(a), VY + 6.82 * math.cos(a)
        rect_xy(g, x - 0.07, x + 0.07, y - 0.07, y + 0.07, VZ + 0.2, VZ + 0.36, "Chrome")
    annulus(g, VX, VY, 5.25, 5.6, VZ - 0.9, VZ + 0.05, "MetalDark", 48, gap=0.0)
    for k in range(36):                                                       # teeth (the gear-like notches)
        a0 = 2 * math.pi * k / 36; a1 = a0 + 2 * math.pi / 36 * 0.55
        annulus(g, VX, VY, 5.15, 5.6, VZ - 0.9, VZ + 0.12, "Metal", 1, a0, a1)
    annulus(g, VX, VY, 4.25, 5.25, VZ - 1.0, VZ - 0.45, "MetalDark", 48)                     # recess
    for k in range(16):                                                       # radial fins in the recess
        a = 2 * math.pi * (k + 0.5) / 16
        rect_xy(g, VX - 0.09, VX + 0.09, VY + 4.3, VY + 5.2, VZ - 0.45, VZ - 0.2, "Metal", -a, VX, VY)
    annulus(g, VX, VY, 3.85, 4.25, VZ - 0.8, VZ - 0.05, "Metal", 48)                          # door frame
    for k in range(24):
        a = 2 * math.pi * (k + 0.5) / 24
        x, y = VX + 4.05 * math.sin(a), VY + 4.05 * math.cos(a)
        rect_xy(g, x - 0.06, x + 0.06, y - 0.06, y + 0.06, VZ - 0.05, VZ + 0.05, "Chrome")
    # the door itself: disc, cross lock with hazard-striped side arms, octagonal hub, diagonal slots
    disc(g, VX, VY, 3.85, VZ - 0.9, VZ - 0.35, "Metal", 48)
    annulus(g, VX, VY, 3.2, 3.85, VZ - 0.35, VZ - 0.2, "MetalLight", 48)
    rect_xy(g, VX - 0.42, VX + 0.42, VY - 3.75, VY + 3.75, VZ - 0.35, VZ - 0.05, "MetalLight")
    for sx in (-1, 1):
        a, b = sorted((VX + sx * 1.0, VX + sx * 3.7))
        rect_xy(g, a, b, VY - 0.45, VY + 0.45, VZ - 0.35, VZ - 0.1, "Hazard")
        rect_xy(g, a, b, VY + 0.45, VY + 0.6, VZ - 0.35, VZ - 0.04, "MetalLight")
        rect_xy(g, a, b, VY - 0.6, VY - 0.45, VZ - 0.35, VZ - 0.04, "MetalLight")
    cyl_oct = [(VX + 1.05 * math.sin(math.pi / 8 + k * math.pi / 4), VY + 1.05 * math.cos(math.pi / 8 + k * math.pi / 4)) for k in range(8)][::-1]
    xy_prism(g, cyl_oct, VZ - 0.35, VZ + 0.1, "MetalLight")
    cyl_oct2 = [(VX + 0.7 * math.sin(math.pi / 8 + k * math.pi / 4), VY + 0.7 * math.cos(math.pi / 8 + k * math.pi / 4)) for k in range(8)][::-1]
    xy_prism(g, cyl_oct2, VZ + 0.1, VZ + 0.24, "Metal")
    rect_xy(g, VX - 0.42, VX + 0.42, VY - 0.13, VY + 0.13, VZ + 0.24, VZ + 0.28, "MetalDark")
    for (qx, qy) in ((1, 1), (-1, 1), (1, -1), (-1, -1)):                     # diagonal locking slots + glow
        cx, cy = VX + qx * 1.95, VY + qy * 1.95
        rot = math.radians(45) * (1 if qx * qy > 0 else -1)
        rect_xy(g, cx - 1.25, cx + 1.25, cy - 0.32, cy + 0.32, VZ - 0.35, VZ - 0.28, "MetalDark", rot)
        rect_xy(g, cx - 0.9, cx + 0.9, cy - 0.12, cy + 0.12, VZ - 0.28, VZ - 0.18, "Metal", rot)
        c, s = math.cos(rot), math.sin(rot)
        for off in (-0.24, 0.24):
            p0 = (cx + (-1.15) * c - off * s, cy + (-1.15) * s + off * c); p1 = (cx + 1.15 * c - off * s, cy + 1.15 * s + off * c)
            glow_strip([p0, p1], VZ - 0.26, 0.05, 4)
        # the bracket-shaped line around each slot
        glow_strip([(VX + qx * 1.25, VY + qy * 3.15), (VX + qx * 2.1, VY + qy * 3.15), (VX + qx * 3.05, VY + qy * 2.2), (VX + qx * 3.05, VY + qy * 1.2)],
                   VZ - 0.33, 0.06, 4)
    # the glowing circuit on the outer ring
    for pts in circuit_traces():
        for sx in (-1, 1):
            glow_strip([(VX + sx * x, VY + y) for x, y in pts], VZ + 0.21, 0.17, 1, watts=14)
    GLOWS.append((VX, VY + 3.0, VZ + 2.5, 600, "blue"))
    GLOWS.append((VX, VY - 2.0, VZ + 3.0, 300, "blue"))
    # the plinth and steps in front of the door
    box(g, 0.0, 0.0, 0.42, -27.9, 12.4, 4.4, "Metal", 0.03)
    box(g, 0.0, 0.0, 0.06, -25.66, 12.5, 0.12, "Hazard")
    box(g, 0.0, 0.42, 0.84, -28.5, 10.2, 3.2, "Metal", 0.03)
    box(g, 0.0, 0.84, 2.35, -29.1, 7.2, 2.0, "MetalLight", 0.03)
    for (x0, x1) in ((-3.3, -0.9), (0.9, 3.3)):                                # panel slots on the plinth face
        box(g, (x0 + x1) / 2, 1.3, 1.5, -28.08, x1 - x0, 0.06, "MetalDark")
        box(g, (x0 + x1) / 2, 1.8, 1.9, -28.08, x1 - x0 - 0.6, 0.06, "MetalDark")
    box(g, 0.0, 1.45, 1.75, -28.07, 1.4, 0.07, "MetalDark")
    for sx in (-1, 1):                                                        # side posts with brass caps and rails
        x = sx * 6.6
        box(g, x, 0.0, 1.7, -27.2, 0.7, 0.7, "Metal", 0.03)
        box(g, x, 1.7, 1.85, -27.2, 0.8, 0.8, "Brass", 0.02)
        tube(g, [(sx * 6.6, 1.25, -27.2), (sx * 8.3, 1.25, -25.9)], 0.06, "Chrome", 8)
        box(g, sx * 5.4, 0.42, 1.35, -26.4, 0.5, 0.5, "MetalDark", 0.02)
        glow_quad([(sx * 5.4 - 0.18, 0.6, -26.14), (sx * 5.4 + 0.18, 0.6, -26.14), (sx * 5.4 + 0.18, 0.75, -26.14), (sx * 5.4 - 0.18, 0.75, -26.14)], 3)

# ---------------------------------------------------------------- pillars, lamps, rails
PILLARS = [(7.4, -25.0), (9.9, -25.9), (16.6, -20.6), (19.2, -18.9)]

def pillar(x, z, r=0.85, top=WALL_H):
    g = "GF_Machines"
    box(g, x, -0.2, 1.3, z, 2.6, 2.6, "Metal", 0.05)
    box(g, x, 1.3, 1.5, z, 2.7, 2.7, "Brass", 0.03)
    box(g, x, 1.5, 2.1, z, 2.0, 2.0, "MetalDark", 0.04)
    cyl(g, x, 2.1, z, r, r, top - 2.1, "Pillar", 24)
    for (y0, y1) in ((5.6, 9.4), (12.2, 14.8)):                              # ribbed sections with blue light between the ribs
        cyl(g, x, y0 - 0.25, z, r + 0.2, r + 0.2, 0.25, "Chrome", 24)
        cyl(g, x, y1, z, r + 0.2, r + 0.2, 0.25, "Chrome", 24)
        n = int((y1 - y0) / 0.34)
        for k in range(n):
            cyl(g, x, y0 + 0.08 + k * 0.34, z, r + 0.16, r + 0.16, 0.18, "Chrome", 20)
        for k in range(n - 1):
            ring_glow(x, y0 + 0.34 + k * 0.34, z, r + 0.04, 2, 20, h=0.12)
        GLOWS.append((x, (y0 + y1) / 2, z + 1.4, 40, "blue"))
    for k in range(4):                                                        # vertical seams / straps on the shaft
        a = math.pi / 4 + k * math.pi / 2
        obox(g, (x + r * math.cos(a), 3.85, z + r * math.sin(a)), (0.14, 3.4, 0.14), 0, "MetalDark")
    # amber lamp on the base, facing the arena
    dx, dz = -x, (CENTER_Z - z); L = math.hypot(dx, dz); dx, dz = dx / L, dz / L
    px, pz = x + dx * 1.31, z + dz * 1.31; tx, tz = dz, -dx
    glow_quad([(px - tx * 0.7, 0.35, pz - tz * 0.7), (px + tx * 0.7, 0.35, pz + tz * 0.7), (px + tx * 0.7, 0.75, pz + tz * 0.7), (px - tx * 0.7, 0.75, pz - tz * 0.7)], 3)
    GLOWS.append((px + dx * 0.4, 0.55, pz + dz * 0.4, 70, "amber"))

def cable(x, z, y0=1.5, y1=WALL_H):
    """A thick twisted cable running up beside a pillar (the twist is in its material)."""
    g = "GF_Machines"
    cyl(g, x, y0, z, 0.2, 0.2, y1 - y0, "Cable", 12)
    box(g, x, y0 - 0.5, y0 + 0.1, z, 0.6, 0.6, "MetalDark", 0.02)
    for y in (5.0, 10.8):
        cyl(g, x, y, z, 0.27, 0.27, 0.22, "Chrome", 12)

LAMPS = [22, 40, 56]           # amber floor lamps along the arena edge (degrees from straight back)

def lamps_and_rails():
    g = "GF_Machines"
    R = 17.2
    for sx in (-1, 1):
        prev = None
        for th in LAMPS:
            a = math.radians(th) * sx
            x, z = R * math.sin(a), CENTER_Z - R * math.cos(a)
            rot = -math.degrees(a)
            obox(g, (x, 0.24, z), (1.8, 0.48, 0.7), rot, "Metal", 0.03)
            nx, nz = -math.sin(a), math.cos(a)                                  # toward the arena centre
            tx, tz = nz, -nx
            px, pz = x + nx * 0.36, z + nz * 0.36
            glow_quad([(px - tx * 0.7, 0.1, pz - tz * 0.7), (px + tx * 0.7, 0.1, pz + tz * 0.7), (px + tx * 0.7, 0.38, pz + tz * 0.7), (px - tx * 0.7, 0.38, pz - tz * 0.7)], 3)
            GLOWS.append((px + nx * 0.3, 0.3, pz + nz * 0.3, 80, "amber"))
            # a post behind the lamp and the pipe rail running between them
            qx, qz = x - nx * 0.7, z - nz * 0.7
            box(g, qx, 0.0, 1.15, qz, 0.22, 0.22, "MetalDark")
            if prev:
                tube(g, [(prev[0], 1.05, prev[1]), (qx, 1.05, qz)], 0.05, "Chrome", 8)
                tube(g, [(prev[0], 0.6, prev[1]), (qx, 0.6, qz)], 0.04, "Chrome", 8)
            prev = (qx, qz)

def side_ramps():
    """Ramps climbing to upper decks at both screen edges, with railings."""
    g = "GF_Machines"
    for sx in (-1, 1):
        x0, x1 = sorted((sx * 20.6, sx * 23.4))
        z0, z1, y1 = -5.0, -14.5, 3.2
        pts = [(x0, 0.0, z0), (x1, 0.0, z0), (x1, 0.0, z1), (x0, 0.0, z1), (x0, 0.05, z0), (x1, 0.05, z0), (x1, y1, z1), (x0, y1, z1)]
        gg = grp(g); bm = gg.bm
        v = [bm.verts.new(G(*p)) for p in pts]
        b_, t_ = v[:4], v[4:]
        fs = [bm.faces.new((b_[3], b_[2], b_[1], b_[0])), bm.faces.new((t_[0], t_[1], t_[2], t_[3]))]
        for i in range(4):
            j = (i + 1) % 4
            fs.append(bm.faces.new((b_[i], b_[j], t_[j], t_[i])))
        bmesh.ops.recalc_face_normals(bm, faces=fs); _tag(gg, fs, "Metal")
        xi = x0 if sx > 0 else x1                                              # inner edge rail
        for k in range(6):
            t = k / 5; z = z0 + (z1 - z0) * t; y = 0.05 + (y1 - 0.05) * t
            box(g, xi, y, y + 1.05, z, 0.12, 0.12, "MetalDark")
        tube(g, [(xi, 1.1, z0), (xi, y1 + 1.05, z1)], 0.05, "Chrome", 8)
        tube(g, [(xi, 0.6, z0), (xi, y1 + 0.55, z1)], 0.04, "Chrome", 8)
        box(g, (x0 + x1) / 2, 0.0, 0.08, z0 + 0.1, x1 - x0, 0.2, "Hazard")
        box(g, (x0 + x1) / 2, y1 - 0.3, y1, z1 - 2.0, x1 - x0, 4.0, "Metal")   # the upper deck

def build_machines():
    build_vault()
    for (x, z) in PILLARS:
        for sx in (-1, 1):
            pillar(sx * x, z)
    for sx in (-1, 1):
        cable(sx * 8.65, -25.2)
        cable(sx * 17.9, -19.4)
    lamps_and_rails()
    side_ramps()

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
    bg.inputs["Color"].default_value = (*srgb(WORLD_COLOR), 1); bg.inputs["Strength"].default_value = WORLD_STRENGTH
    bpy.context.scene["ce_variant"] = VARIANT
    bpy.context.scene["ce_world_strength"] = WORLD_STRENGTH
    for name, pos, aim, size, power, colr in (
            ("Key_Top", (0, WALL_H - 0.6, -12), (0, 0, -12), (24, 24), TOP_W, TOP_COLOR),
            ("Fill_Front", (0, 8, 18), (0, 2.5, -14), (28, 10), FILL_W, FILL_COLOR)):
        ld = bpy.data.lights.new(name, 'AREA'); ld.shape = 'RECTANGLE'
        ld.size, ld.size_y = size; ld.energy = power; ld.color = srgb(colr)
        o = bpy.data.objects.new(name, ld); col("Lights").objects.link(o); o.location = G(*pos)
        o.rotation_mode = 'QUATERNION'; o.rotation_quaternion = (G(*aim) - G(*pos)).normalized().to_track_quat('-Z', 'Y')
        o.visible_camera = False
    for k, (x, y, z, wts, c) in enumerate(GLOWS):
        ld = bpy.data.lights.new("Glow_%d" % k, 'POINT'); ld.energy = wts; ld.color = srgb(GLOW_HEX[c])
        ld.shadow_soft_size = 0.3
        o = bpy.data.objects.new("Glow_%d" % k, ld); col("Lights").objects.link(o); o.location = G(x, y, z)
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
        cd.clip_start = 0.1; cd.clip_end = 400
        o = bpy.data.objects.new(name, cd); col("Cameras").objects.link(o)
        o.location = G(*pos); o.rotation_euler = (math.radians(90), 0, 0)
    bpy.context.scene.camera = bpy.data.objects["CAM_mid"]

def build_all():
    reset(); COLS.clear(); MATS.clear(); GR.clear(); GLOWS.clear()
    build_materials()
    build_floor(); build_walls(); build_machines(); build_preview()
    objs = {name: g.finish() for name, g in list(GR.items())}
    objs["GF_Glow"].visible_shadow = False
    build_lights(); build_cameras(); setup_render()
    tris = {o.name: sum(len(p.vertices) - 2 for p in o.data.polygons) for o in objs.values()}
    return {"objects": list(objs), "tris": tris, "total_tris": sum(tris.values()), "glows": len(GLOWS)}

if __name__ == "__main__":
    BUILD_INFO = build_all()
