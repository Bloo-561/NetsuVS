# Septian Chapel - 3D stage build script (Blender 5.x, runs in --background).
# A Septian Church chapel out in the countryside on a golden afternoon. The fight is on the cobbled churchyard
# square in front of the chapel: a stone facade with a rose window, a pointed portal and the Church's emblem,
# a bell tower with a spire, a statue of the Goddess Aidios in a ring of flowers. To the left the sister's
# rectory (smoking chimney, well, laundry line, a big oak with a bench); to the right the churchyard with its
# headstones behind a low wall and a lychgate; hay bales and fences. Behind: rolling patchwork fields, hedgerows,
# poplars, farmhouses, a windmill turning on a hill, woods, blue mountains, a summer sky with drifting clouds.
#
#   blender --background --factory-startup --python run_ch.py -- STEPS=build,bake,preview,export CAMS=CAM_mid
#
# Layout is written in GODOT coordinates (x right, y up, +z toward the camera) and converted
# to Blender (Z-up) by G():  Godot (x, y, z) -> Blender (x, -z, y).  1 unit = 1 m.
# Baked groups (atlases): CH_Chapel (chapel, tower, statue), CH_Village (rectory, churchyard, oak, props),
#                         CH_Land (terrain, farms, windmill, woods, mountains), CH_Floor (light map only)
# Card groups (Godot shaders): CH_Sky, CH_Glass (stained glass), CH_Grass (swaying tufts and flowers), CH_Smoke,
#                              CH_Sails (windmill), CH_Birds, CH_Cloth (laundry)  - only CH_Sky is in the bake
import bpy, bmesh, math, random
from mathutils import Vector, Matrix

ROOT = r"E:\Netsu Projects\Netsu Fighter\Godot\netsu-vs\stages\septian_chapel"
TEXD = ROOT + r"\src\tex"
VARIANT = globals().get("VARIANT") or "afternoon"

# ---------------- layout (Godot space, metres) ----------------
FLOOR_X = 60.0                     # the ground quad (Godot floor shader): x +-60, z -80..+22
FLOOR_BACK, FLOOR_FRONT = -80.0, 22.0
LANE_X, LANE_Z = 12.5, -9.0        # keep |x| < 12.5 and z > -9 clear (fight lane)
CENTER_Z = -6.0
FACADE_Z = -28.0                   # the chapel front
NAVE_W, NAVE_L = 5.0, 20.0         # half width, length
WALL_H, RIDGE_H = 7.0, 12.5
TOWER = (7.1, -30.1, 3.8)          # bell tower centre x, z and width
STATUE = (-6.6, -17.0)
BOARD = (6.4, -17.4)              # the parish notice board
OAK = (-15.5, -6.5)
SKY_R = 1000.0
SUN_DIR = (-0.45, -0.62, -0.64)    # where the afternoon sun shines TO (from behind the camera, on the right)

V = dict(world=("#9ab4d8", 1.0), sun=(4.4, "#ffe4bc"), fill=(1400, "#ffe8d0"), top=(900, "#c8daf0"),
         sky=[(0.0, "#e8eef4"), (0.08, "#bcd2ec"), (0.3, "#7aa2dc"), (1.0, "#3a64b0")], sky_strength=1.0)
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
def add_haze(b, colour, near, far, hmax):
    """Fade into the blue distance with distance from the stage (baked in as emission)."""
    dist = b.n("ShaderNodeVectorMath", operation='LENGTH'); b.link(b.pos, dist.inputs[0])
    mr = b.n("ShaderNodeMapRange"); mr.inputs["From Min"].default_value = near; mr.inputs["From Max"].default_value = far
    mr.inputs["To Min"].default_value = 0.0; mr.inputs["To Max"].default_value = hmax
    b.link(dist.outputs["Value"], mr.inputs[0])
    em = b.n("ShaderNodeEmission"); em.inputs["Color"].default_value = (*srgb(colour), 1); em.inputs["Strength"].default_value = 1.0
    mix = b.n("ShaderNodeMixShader"); b.link(mr.outputs[0], mix.inputs[0])
    b.link(b.bsdf.outputs[0], mix.inputs[1]); b.link(em.outputs[0], mix.inputs[2]); b.link(mix.outputs[0], b.out.inputs[0])

def plain(name, dark, light, scale=3.0, rough=0.6, haze=None):
    b = NB(name)
    n = b.noise(b.pos, scale, 4, 0.55)
    c = b.ramp(n.outputs["Fac"], [(0.3, dark), (0.7, light)])
    b.link(c, b.bsdf.inputs["Base Color"]); b.bsdf.inputs["Roughness"].default_value = rough
    if haze:
        add_haze(b, *haze)
    return b

def blocks(name, c1, c2, mortar, bw, bh, ms=0.02, rough=0.7, haze=None, dirt=True):
    b = NB(name)
    br = b.n("ShaderNodeTexBrick"); br.offset = 0.5
    for k, v in (("Scale", 1.0), ("Mortar Size", ms), ("Brick Width", bw), ("Row Height", bh)):
        br.inputs[k].default_value = v
    br.inputs["Color1"].default_value = (*srgb(c1), 1); br.inputs["Color2"].default_value = (*srgb(c2), 1)
    br.inputs["Mortar"].default_value = (*srgb(mortar), 1)
    b.link(b.uv, br.inputs["Vector"])
    n = b.noise(b.pos, 1.4, 4, 0.6)
    c = b.mixc(br.outputs["Color"], b.ramp(n.outputs["Fac"], [(0.3, "#c8c4bc"), (0.7, "#ffffff")]), 1.0, 'MULTIPLY')
    if dirt:      # weathering: darker near the ground
        sep = b.n("ShaderNodeSeparateXYZ"); b.link(b.pos, sep.inputs[0])
        g = b.math('MINIMUM', b.math('MULTIPLY', sep.outputs[2], 0.9), 1.0)
        c = b.mixc(b.mixc("#8a8478", "#ffffff", g), c, 1.0, 'MULTIPLY')
    b.link(c, b.bsdf.inputs["Base Color"]); b.bsdf.inputs["Roughness"].default_value = rough
    if haze:
        add_haze(b, *haze)
    return b

def streaks(name, c1, c2, scale, rough=0.8):
    """Fibrous streaks (hay, thatch)."""
    b = NB(name)
    w = b.n("ShaderNodeTexWave"); w.wave_type = 'BANDS'
    w.inputs["Scale"].default_value = scale; w.inputs["Distortion"].default_value = 6.0; w.inputs["Detail"].default_value = 3.0
    b.link(b.pos, w.inputs["Vector"])
    c = b.ramp(w.outputs["Fac"], [(0.2, c1), (0.8, c2)])
    b.link(c, b.bsdf.inputs["Base Color"]); b.bsdf.inputs["Roughness"].default_value = rough
    return b

def land(name):
    """Patchwork fields with hedgerows, meadow near the chapel, fading into the blue distance."""
    b = NB(name)
    vo = b.n("ShaderNodeTexVoronoi"); vo.voronoi_dimensions = '2D'; vo.feature = 'F1'
    vo.inputs["Scale"].default_value = 0.022; vo.inputs["Randomness"].default_value = 0.85
    b.link(b.pos, vo.inputs["Vector"])
    sep = b.n("ShaderNodeSeparateColor"); b.link(vo.outputs["Color"], sep.inputs[0])
    fields = b.ramp(sep.outputs[0], [(0.0, "#5e8e36"), (0.2, "#86aa46"), (0.38, "#c8b25e"), (0.5, "#b0904a"),
                                     (0.66, "#6a9a3e"), (0.8, "#a4ac50"), (1.0, "#4e7e32")])
    ve = b.n("ShaderNodeTexVoronoi"); ve.voronoi_dimensions = '2D'; ve.feature = 'DISTANCE_TO_EDGE'
    ve.inputs["Scale"].default_value = 0.022; ve.inputs["Randomness"].default_value = 0.85
    b.link(b.pos, ve.inputs["Vector"])
    hedge = b.math('LESS_THAN', ve.outputs["Distance"], 0.035)
    c = b.mixc(fields, "#2c4a24", hedge)
    n = b.noise(b.pos, 0.08, 4, 0.6)
    c = b.mixc(c, b.ramp(n.outputs["Fac"], [(0.3, "#d0d0d0"), (0.7, "#ffffff")]), 1.0, 'MULTIPLY')
    dist = b.n("ShaderNodeVectorMath", operation='LENGTH'); b.link(b.pos, dist.inputs[0])
    near = b.math('MINIMUM', b.math('MAXIMUM', b.math('MULTIPLY', b.math('SUBTRACT', dist.outputs["Value"], 95.0), 1 / 45.0), 0.0), 1.0)
    c = b.mixc("#5c8c3c", c, near)
    b.link(c, b.bsdf.inputs["Base Color"]); b.bsdf.inputs["Roughness"].default_value = 0.9
    add_haze(b, HZ, 110, 560, 0.7)
    return b

def mountain(name):
    b = NB(name)
    sep = b.n("ShaderNodeSeparateXYZ"); b.link(b.pos, sep.inputs[0])
    n = b.noise(b.pos, 0.02, 5, 0.6)
    hh = b.math('ADD', sep.outputs[2], b.math('MULTIPLY', n.outputs["Fac"], 40.0))
    snow = b.math('GREATER_THAN', hh, 92.0)
    c = b.mixc(b.ramp(n.outputs["Fac"], [(0.3, "#5a6a5a"), (0.7, "#7a8478")]), "#eef2f6", snow)
    b.link(c, b.bsdf.inputs["Base Color"]); b.bsdf.inputs["Roughness"].default_value = 0.9
    add_haze(b, "#a8bcd8", 300, 900, 0.72)
    return b

def emit_solid(name, color, strength):
    b = NB(name)
    em = b.n("ShaderNodeEmission"); em.inputs["Color"].default_value = (*srgb(color), 1); em.inputs["Strength"].default_value = strength
    b.link(em.outputs[0], b.out.inputs[0])
    return b

HZ = "#b4c6dc"
def build_materials():
    blocks("Limestone", "#c4b8a0", "#d2c6ae", "#9a8e7a", 0.9, 0.42, 0.012)
    plain("StoneTrim", "#d0c4ac", "#e0d6c0", 4.0, 0.6)
    blocks("Slate", "#3c4a5e", "#4a586c", "#2a323e", 0.42, 0.24, 0.02, 0.5, dirt=False)
    blocks("Fieldstone", "#8a8476", "#a09a8a", "#5a564e", 0.55, 0.3, 0.035)
    blocks("RoofTile", "#8e3e2a", "#a04a32", "#5a2a1e", 0.3, 0.17, 0.02, 0.6, dirt=False)
    blocks("Brick", "#8a4a36", "#9a563e", "#4a3028", 0.24, 0.08, 0.015)
    plain("Plaster", "#e2d8c6", "#eee6d6", 2.0, 0.8)
    plain("Timber", "#3e2c1e", "#523a28", 6.0, 0.7)
    plain("Wood", "#6a4a30", "#80603e", 5.0, 0.7)
    plain("DoorWood", "#4e3020", "#62402a", 6.0, 0.6)
    plain("Iron", "#202226", "#30333a", 5.0, 0.5)
    plain("Gold", "#a07a30", "#d0a448", 8.0, 0.3)
    plain("Bronze", "#6a5030", "#8a6a3e", 6.0, 0.35)
    plain("Marble", "#d4d0c6", "#e8e4dc", 3.0, 0.4)
    plain("Headstone", "#8a8a84", "#a8a69c", 5.0, 0.7)
    plain("WindowDark", "#1c2430", "#28323e", 3.0, 0.2)
    plain("PaintWhite", "#e6e2d8", "#f2eee6", 4.0, 0.6)
    plain("Foliage", "#3a6a2a", "#5a8a36", 5.0, 0.8)
    plain("OakLeaf", "#335a24", "#4e7c30", 3.0, 0.8)
    plain("Yew", "#1c3620", "#2a4a2a", 4.0, 0.8)
    plain("Bark", "#3a2c20", "#54402c", 5.0, 0.8)
    plain("Soil", "#4a3a2a", "#5a4632", 4.0, 0.9)
    streaks("Hay", "#b8903e", "#dcbc6a", 3.0)
    for nm, c in (("FlowerRed", "#c83a3a"), ("FlowerYellow", "#e8c840"), ("FlowerWhite", "#f0eee6"), ("FlowerViolet", "#8a5ac0"), ("FlowerPink", "#e08aa8")):
        plain(nm, c, c, 2.0, 0.7)
    land("Land")
    mountain("Mountain")
    plain("FarmWall", "#d8d0be", "#e4dccc", 2.0, 0.8, haze=(HZ, 90, 480, 0.68))
    plain("FarmRoof", "#9a4a32", "#aa5638", 3.0, 0.7, haze=(HZ, 90, 480, 0.68))
    plain("Forest", "#24421f", "#36582a", 0.4, 0.9, haze=(HZ, 90, 480, 0.68))
    plain("Mill", "#c8bca6", "#d8ceb8", 2.0, 0.8, haze=(HZ, 90, 480, 0.6))
    b = NB("FloorGround"); b.bsdf.inputs["Base Color"].default_value = (*srgb("#6a8c48"), 1); b.bsdf.inputs["Roughness"].default_value = 0.9
    b = NB("SkyCard")
    sep = b.n("ShaderNodeSeparateXYZ"); b.link(b.uv, sep.inputs[0])
    em = b.n("ShaderNodeEmission"); em.inputs["Strength"].default_value = V["sky_strength"]
    b.link(b.ramp(sep.outputs[1], V["sky"]), em.inputs["Color"]); b.link(em.outputs[0], b.out.inputs[0])
    for nm in ("GlassCard", "GrassCard", "SmokeCard", "SailsCard", "BirdCard", "ClothCard"):
        emit_solid(nm, "#808080", 0.0)
    b = NB("Stand_P1"); b.bsdf.inputs["Base Color"].default_value = (*srgb("#2d6cdf"), 1)
    b = NB("Stand_P2"); b.bsdf.inputs["Base Color"].default_value = (*srgb("#e0463a"), 1)

# ======================================================================
#  shape helpers for this stage
# ======================================================================
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

def parch(cx, ys, w, n=6):
    """Pointed (equilateral) arch over a span cx-w..cx+w springing at ys: points left -> apex -> right (x, y)."""
    L = [(cx + w + 2 * w * math.cos(a), ys + 2 * w * math.sin(a)) for a in [math.pi - (math.pi / 3) * k / n for k in range(n + 1)]]
    R = [(cx - w + 2 * w * math.cos(a), ys + 2 * w * math.sin(a)) for a in [(math.pi / 3) * (n - k) / n for k in range(n + 1)]]
    return L + R[1:]

def arch_leaf(g, cx, y0, ys, w, z0, z1, m, n=6):
    """A solid pointed-arch shape (door leaf, window panel), extruded z0..z1."""
    pts = [(cx - w, y0), (cx + w, y0)] + parch(cx, ys, w, n)[::-1]
    prism(g, pts, 'z', z0, z1, m)

def arch_ring(g, cx, y0, ys, w, t, z0, z1, m, n=6):
    """The moulded frame of a pointed portal: jambs from y0 to ys and the arch ring (inner span w, outer w + t)."""
    for s in (-1, 1):
        box(g, cx + s * (w + t / 2), y0, ys, (z0 + z1) / 2, t, z1 - z0, m)
    inner = parch(cx, ys, w, n); outer = parch(cx, ys, w + t, n)
    for (a, b), (c, d) in zip(zip(inner[:-1], inner[1:]), zip(outer[:-1], outer[1:])):
        hexa(g, [(a[0], a[1], z0), (b[0], b[1], z0), (d[0], d[1], z0), (c[0], c[1], z0),
                 (a[0], a[1], z1), (b[0], b[1], z1), (d[0], d[1], z1), (c[0], c[1], z1)], m)

def ring_z(g, cx, cy, z0, z1, r0, r1, m, n=24):
    """A flat circular ring facing +z (rose window frame, clock bezel)."""
    for i in range(n):
        a, b = 2 * math.pi * i / n, 2 * math.pi * (i + 1) / n
        P = lambda r, t: (cx + r * math.cos(t), cy + r * math.sin(t))
        p0, p1, p2, p3 = P(r0, a), P(r0, b), P(r1, b), P(r1, a)
        hexa(g, [(p0[0], p0[1], z0), (p1[0], p1[1], z0), (p2[0], p2[1], z0), (p3[0], p3[1], z0),
                 (p0[0], p0[1], z1), (p1[0], p1[1], z1), (p2[0], p2[1], z1), (p3[0], p3[1], z1)], m)

def ring_y(g, cx, cz, y0, y1, r0, r1, m, n=24):
    """A flat ring lying on the ground (kerb)."""
    for i in range(n):
        a, b = 2 * math.pi * i / n, 2 * math.pi * (i + 1) / n
        P = lambda r, t: (cx + r * math.cos(t), cz + r * math.sin(t))
        p0, p1, p2, p3 = P(r0, a), P(r0, b), P(r1, b), P(r1, a)
        hexa(g, [(p0[0], y0, p0[1]), (p1[0], y0, p1[1]), (p2[0], y0, p2[1]), (p3[0], y0, p3[1]),
                 (p0[0], y1, p0[1]), (p1[0], y1, p1[1]), (p2[0], y1, p2[1]), (p3[0], y1, p3[1])], m)

def emblem(g, cx, cy, z, s, m="Gold"):
    """The Church's emblem (an original stylised design): a ring crossed by an upright, seven rays above."""
    ring_z(g, cx, cy, z, z + 0.06, 0.32 * s, 0.42 * s, m, 20)
    box(g, cx, cy - 0.62 * s, cy + 0.62 * s, z + 0.03, 0.1 * s, 0.06, m)
    for k in range(7):
        a = math.radians(30 + 20 * k)
        r0, r1 = 0.5 * s, (0.78 if k % 2 == 0 else 0.68) * s
        beam(g, (cx + r0 * math.cos(a), cy + r0 * math.sin(a), z + 0.03), (cx + r1 * math.cos(a), cy + r1 * math.sin(a), z + 0.03), 0.07 * s, 0.06, m)

GRASS = []   # (x, z, size, kind)

def tuft(x, z, s=1.0, kind=0, seed=0):
    """A swaying tuft of grass (kind 0), grass with flowers (1) or tall grass (2): two crossed cards."""
    rnd = random.Random(seed)
    w = (0.6 + 0.3 * rnd.random()) * s; h = (0.42 + 0.3 * rnd.random()) * s * (1.6 if kind == 2 else 1.0)
    a = rnd.uniform(0, math.pi)
    for k in range(2):
        aa = a + k * math.pi / 2
        dx, dz = math.cos(aa) * w / 2, math.sin(aa) * w / 2
        sd = float((seed * 7 + k * 13) % 997)          # the shader's per-tuft seed = floor(UV.x)
        card("CH_Grass", [(x - dx, -0.02, z - dz), (x + dx, -0.02, z + dz), (x + dx, h, z + dz), (x - dx, h, z - dz)], kind, "GrassCard",
             sd + 0.001, sd + 0.999)
    GRASS.append((x, z, s, kind))

def tufts_along(p0, p1, n, s=1.0, seed=0, spread=0.35, kinds=(0, 0, 1, 2)):
    rnd = random.Random(seed)
    for i in range(n):
        t = (i + rnd.random()) / n
        x = p0[0] + (p1[0] - p0[0]) * t + rnd.uniform(-spread, spread)
        z = p0[1] + (p1[1] - p0[1]) * t + rnd.uniform(-spread, spread)
        tuft(x, z, s * rnd.uniform(0.8, 1.2), rnd.choice(kinds), seed * 100 + i)

# ======================================================================
#  the floor and the chapel
# ======================================================================
def build_floor():
    g = grp("CH_Floor")
    quad(g, [(-FLOOR_X, 0, FLOOR_FRONT), (FLOOR_X, 0, FLOOR_FRONT), (FLOOR_X, 0, FLOOR_BACK), (-FLOOR_X, 0, FLOOR_BACK)],
         [(-FLOOR_X, -FLOOR_FRONT), (FLOOR_X, -FLOOR_FRONT), (FLOOR_X, -FLOOR_BACK), (-FLOOR_X, -FLOOR_BACK)], "FloorGround")

def build_chapel():
    g = "CH_Chapel"; zf = FACADE_Z; w = NAVE_W; zb = zf - NAVE_L
    gable(g, -w, w, zb, zf, 0.0, WALL_H, RIDGE_H, "Limestone", "Slate", 'z', 0.45, 0.3)
    box(g, 0.0, -0.3, 0.35, (zf + zb) / 2, 2 * w + 0.5, NAVE_L + 0.5, "StoneTrim")             # plinth
    # facade: string course, corner buttresses, gable coping, the cross-shaped apex stone
    box(g, 0.0, 5.0, 5.25, zf + 0.12, 2 * w, 0.24, "StoneTrim")
    for s in (-1, 1):
        x = s * (w + 0.1)
        box(g, x, 0.0, 4.8, zf - 0.2, 0.9, 1.4, "Limestone")
        prism(g, [(zf + 0.5, 4.8), (zf - 0.9, 4.8), (zf - 0.9, 6.0)], 'x', x - 0.45, x + 0.45, "StoneTrim")
        box(g, x, 4.8, 7.2, zf - 0.6, 0.7, 0.8, "Limestone")
        for k in range(4):                                                             # side buttresses
            box(g, s * (w + 0.3), 0.0, 4.6, zf - 4.0 - k * 4.6, 0.6, 0.8, "Limestone")
    for s in (-1, 1):                                                                  # coping on the gable edges
        beam(g, (s * (w + 0.35), WALL_H - 0.1, zf + 0.1), (0.0, RIDGE_H + 0.12, zf + 0.1), 0.38, 0.3, "StoneTrim")
    lathe(g, 0.0, RIDGE_H + 0.1, zf + 0.1, [(0, 0), (0.25, 0.0), (0.18, 0.5), (0, 0.6)], 6, "StoneTrim")
    emblem(g, 0.0, RIDGE_H + 1.2, zf + 0.1, 0.75, "Gold")
    lathe(g, 0.0, RIDGE_H + 0.5, zf + 0.12, [(0, 0), (0.05, 0.0), (0.05, 1.3), (0, 1.32)], 4, "Gold")
    # the steps
    for k in range(3):
        box(g, 0.0, 0.0, 0.18 * (3 - k), zf + 1.5 - k * 0.5, 5.4 - k * 0.3, 0.5 + k * 0.0 + (0.02 if k else 0), "StoneTrim")
    # the portal: a moulded pointed arch, the door leaves, a tympanum with the emblem
    pz = zf + 0.0
    arch_ring(g, 0.0, 0.54, 2.9, 1.2, 0.45, pz - 0.05, pz + 0.45, "StoneTrim")
    arch_ring(g, 0.0, 0.54, 2.9, 1.65, 0.3, pz - 0.05, pz + 0.25, "Limestone")
    arch_leaf(g, 0.0, 0.54, 2.9, 1.2, pz + 0.01, pz + 0.09, "DoorWood")
    box(g, 0.0, 0.54, 2.9, pz + 0.1, 0.05, 0.04, "Iron")                             # the meeting of the two leaves
    for y in (1.0, 1.9, 2.6):
        box(g, 0.0, y - 0.04, y + 0.04, pz + 0.1, 2.2, 0.03, "Iron")                 # iron straps
    for s in (-1, 1):
        hcyl(g, (s * 0.22, 1.5, pz + 0.09), (s * 0.22, 1.5, pz + 0.16), 0.07, "Iron", 8)
    emblem(g, 0.0, 3.6, pz + 0.1, 0.55, "Gold")
    # rose window: tracery ring and spokes; the glass is a card
    rc, rr = 7.9, 1.45
    ring_z(g, 0.0, rc, zf - 0.05, zf + 0.16, rr, rr + 0.32, "StoneTrim", 28)
    ring_z(g, 0.0, rc, zf - 0.05, zf + 0.1, 0.32, 0.42, "StoneTrim", 16)
    for k in range(8):
        a = 2 * math.pi * k / 8
        beam(g, (0.42 * math.cos(a), rc + 0.42 * math.sin(a), zf + 0.05), (rr * math.cos(a), rc + rr * math.sin(a), zf + 0.05), 0.08, 0.1, "StoneTrim")
    card("CH_Glass", [(-rr, rc - rr, zf + 0.02), (rr, rc - rr, zf + 0.02), (rr, rc + rr, zf + 0.02), (-rr, rc + rr, zf + 0.02)], 0, "GlassCard")
    # lancets either side of the portal (facade) and along the nave
    for s in (-1, 1):
        x = s * 3.3
        arch_ring(g, x, 2.4, 4.6, 0.4, 0.16, zf - 0.02, zf + 0.12, "StoneTrim", 4)
        box(g, x, 2.25, 2.4, zf + 0.05, 1.1, 0.2, "StoneTrim")
        lancet_card(x, 2.4, 4.6, 0.4, zf + 0.01, 1, '+z')
        for k in range(4):
            z = zf - 2.0 - k * 4.6
            lancet_card(z, 2.0, 4.6, 0.45, s * (w + 0.01), 2, '+x' if s > 0 else '-x')
            box(g, s * (w + 0.05), 1.85, 2.0, z, 0.2, 1.2, "StoneTrim")
    build_tower()
    build_statue()
    build_board()

def build_board():
    """The parish notice board by the path, with a little slate roof and notices pinned to it."""
    g = "CH_Chapel"; x, z = BOARD
    for s in (-1, 1):
        box(g, x + s * 0.85, 0.0, 2.3, z, 0.14, 0.14, "Timber")
    box(g, x, 0.95, 2.05, z + 0.02, 1.6, 0.08, "Wood")
    for (dx, dy, w, h) in ((-0.45, 1.45, 0.42, 0.55), (0.1, 1.6, 0.36, 0.4), (0.45, 1.3, 0.4, 0.5), (-0.05, 1.15, 0.3, 0.25)):
        box(g, x + dx, dy - h / 2, dy + h / 2, z + 0.075, w, 0.01, "PaintWhite")
    gable(g, x - 1.05, x + 1.05, z - 0.35, z + 0.35, 2.25, 2.3, 2.75, "Timber", "Slate", 'x', 0.12, 0.08)
    emblem(g, x, 2.42, z + 0.4, 0.18, "Gold")
    tufts_along((x - 1.0, z + 0.3), (x + 1.0, z + 0.3), 4, 0.8, 81)

def lancet_card(a, ys0, ys, w, plane, fid, face):
    """A pointed stained-glass window card. For '+z' a is x; for '+-x' a is z (the window's centre)."""
    top = ys + 1.732 * w
    if face == '+z':
        card("CH_Glass", [(a - w, ys0, plane), (a + w, ys0, plane), (a + w, top, plane), (a - w, top, plane)], fid, "GlassCard")
    else:
        s = 1 if face == '+x' else -1
        card("CH_Glass", [(plane, ys0, a + s * w), (plane, ys0, a - s * w), (plane, top, a - s * w), (plane, top, a + s * w)], fid, "GlassCard")

def build_tower():
    g = "CH_Chapel"; x, z, tw = TOWER; h = tw / 2
    box(g, x, -0.3, 11.0, z, tw, tw, "Limestone")
    box(g, x, -0.3, 0.6, z, tw + 0.4, tw + 0.4, "StoneTrim")
    for y in (5.4, 11.0):
        box(g, x, y - 0.15, y + 0.15, z, tw + 0.2, tw + 0.2, "StoneTrim")
    for sx in (-1, 1):                                                       # corner buttresses
        for sz in (-1, 1):
            box(g, x + sx * (h + 0.15), 0.0, 8.5, z + sz * (h - 0.3), 0.3, 0.6, "Limestone")
    # clock on the front
    ring_z(g, x, 8.2, z + h, z + h + 0.12, 0.62, 0.78, "Gold", 24)
    hcyl(g, (x, 8.2, z + h - 0.02), (x, 8.2, z + h + 0.06), 0.63, "Marble", 24)
    beam(g, (x, 8.2, z + h + 0.08), (x + 0.0, 8.62, z + h + 0.08), 0.05, 0.03, "Iron")
    beam(g, (x, 8.2, z + h + 0.09), (x + 0.33, 8.02, z + h + 0.09), 0.05, 0.03, "Iron")
    # a narrow window low down
    lancet_card(x, 2.6, 3.8, 0.28, z + h + 0.01, 1, '+z')
    # the open belfry: corner piers, pointed hoods, the bell
    box(g, x, 11.0, 11.3, z, tw, tw, "Limestone")
    for sx in (-1, 1):
        for sz in (-1, 1):
            box(g, x + sx * (h - 0.4), 11.3, 14.6, z + sz * (h - 0.4), 0.8, 0.8, "Limestone")
    for s in (-1, 1):
        arch_ring(g, x, 11.3, 13.4, 1.1, 0.25, z + h - 0.5, z + h, "Limestone", 4)          # front + back arches
        arch_ring(g, x, 11.3, 13.4, 1.1, 0.25, z - h, z - h + 0.5, "Limestone", 4)
    for s in (-1, 1):
        box(g, x + s * (h - 0.25), 13.4, 14.6, z, 0.5, tw - 1.6, "Limestone")              # side spandrels
    box(g, x, 14.6, 15.4, z, tw + 0.3, tw + 0.3, "StoneTrim")
    box(g, x, 14.0, 14.25, z, 0.25, tw - 0.6, "Timber")                                      # headstock beam
    lathe(g, x, 12.3, z, [(0, 0), (0.78, 0.0), (0.74, 0.12), (0.52, 0.5), (0.46, 1.15), (0.36, 1.4), (0.12, 1.52), (0, 1.55)], 16, "Bronze")
    box(g, x, 13.85, 14.0, z, 0.3, 0.3, "Iron")
    # the spire with a gold finial and the emblem
    lathe(g, x, 15.4, z, [(0, 0), (2.25, 0.0), (2.25, 0.5), (0.25, 10.0), (0, 10.4)], 8, "Slate", math.pi / 8)
    for sx in (-1, 1):                                                                       # corner pinnacles
        for sz in (-1, 1):
            lathe(g, x + sx * (h - 0.05), 15.4, z + sz * (h - 0.05), [(0, 0), (0.3, 0.0), (0.3, 0.8), (0.0, 2.0)], 4, "StoneTrim", math.pi / 4)
    lathe(g, x, 25.6, z, [(0, 0), (0.12, 0.0), (0.18, 0.3), (0.06, 0.6), (0.05, 1.6), (0, 1.65)], 8, "Gold")
    emblem(g, x, 26.6, z + 0.03, 0.55, "Gold")
    emblem(g, x, 26.6, z - 0.09, 0.55, "Gold")

def build_statue():
    """The Goddess Aidios on a pedestal inside a ring of flowers."""
    g = "CH_Chapel"; x, z = STATUE
    ring_y(g, x, z, 0.0, 0.22, 2.35, 2.6, "StoneTrim", 32)
    box(g, x, 0.0, 0.3, z, 1.5, 1.5, "StoneTrim")
    box(g, x, 0.3, 1.3, z, 1.05, 1.05, "Limestone")
    box(g, x, 1.3, 1.45, z, 1.25, 1.25, "StoneTrim")
    emblem(g, x, 0.85, z + 0.53, 0.32, "Gold")
    y0 = 1.45
    lathe(g, x, y0, z, [(0, 0), (0.44, 0.0), (0.42, 0.1), (0.34, 0.5), (0.27, 1.0), (0.21, 1.3), (0.26, 1.55), (0.22, 1.74), (0.09, 1.84), (0, 1.86)], 14, "Marble")
    ico(g, (x, y0 + 1.99, z + 0.02), 0.13, "Marble", 7, 1.15, 2)
    lathe(g, x, y0 + 1.78, z - 0.02, [(0, 0), (0.19, 0.0), (0.18, 0.2), (0.13, 0.34), (0, 0.38)], 12, "Marble")          # veil
    for s in (-1, 1):
        tube(g, [(x + s * 0.24, y0 + 1.62, z), (x + s * 0.2, y0 + 1.3, z + 0.18), (x + s * 0.05, y0 + 1.5, z + 0.3)], 0.065, "Marble", 8)
    ico(g, (x, y0 + 1.52, z + 0.31), 0.07, "Marble", 9, 1.3)                                                             # joined hands
    pts = [(x + 0.3 * math.cos(2 * math.pi * k / 20), y0 + 2.02 + 0.3 * math.sin(2 * math.pi * k / 20), z - 0.17) for k in range(21)]
    tube(g, pts, 0.02, "Gold", 5)
    # the flowers in the ring
    rnd = random.Random(5); cols = ["FlowerRed", "FlowerYellow", "FlowerWhite", "FlowerViolet", "FlowerPink"]
    for k in range(64):
        a = rnd.uniform(0, 2 * math.pi); r = rnd.uniform(0.95, 2.2)
        fx, fz = x + r * math.cos(a), z + r * math.sin(a)
        ico(g, (fx, 0.22, fz), rnd.uniform(0.16, 0.26), "Foliage", 100 + k, 0.7)
        ico(g, (fx + rnd.uniform(-0.1, 0.1), 0.38 + rnd.uniform(0, 0.12), fz + rnd.uniform(-0.1, 0.1)), rnd.uniform(0.07, 0.11), cols[k % 5], 200 + k, 0.8)

# ======================================================================
#  the village side: rectory, garden, well, laundry, oak; the churchyard; hay and fences
# ======================================================================
def window_box(g, x, y, z, w=0.9, h=1.1, face='+z', flowers=True, seed=0):
    """A cottage window: dark panes, a white frame and glazing bars, a flower box beneath."""
    if face == '+z':
        box(g, x, y, y + h, z + 0.02, w, 0.06, "WindowDark")
        for dx in (-w / 2, w / 2):
            box(g, x + dx, y - 0.05, y + h + 0.05, z + 0.05, 0.08, 0.06, "PaintWhite")
        for yy in (y - 0.05, y + h + 0.05, y + h / 2):
            box(g, x, yy - 0.04, yy + 0.04, z + 0.05, w + 0.08, 0.06, "PaintWhite")
        box(g, x, y, y + h, z + 0.05, 0.05, 0.05, "PaintWhite")
        if flowers:
            box(g, x, y - 0.32, y - 0.08, z + 0.2, w + 0.1, 0.3, "Wood")
            rnd = random.Random(seed)
            for k in range(6):
                ico(g, (x - w / 2 + (k + 0.5) * w / 6, y - 0.02, z + 0.2), 0.1, ["FlowerRed", "FlowerPink", "FlowerRed", "FlowerWhite"][rnd.randrange(4)], seed + k, 0.9)
    else:   # +x face
        box(g, x + 0.02, y, y + h, z, 0.06, w, "WindowDark")
        for dz in (-w / 2, w / 2):
            box(g, x + 0.05, y - 0.05, y + h + 0.05, z + dz, 0.06, 0.08, "PaintWhite")
        for yy in (y - 0.05, y + h + 0.05, y + h / 2):
            box(g, x + 0.05, yy - 0.04, yy + 0.04, z, 0.06, w + 0.08, "PaintWhite")
        if flowers:
            box(g, x + 0.2, y - 0.32, y - 0.08, z, 0.3, w + 0.1, "Wood")
            for k in range(6):
                ico(g, (x + 0.2, y - 0.02, z - w / 2 + (k + 0.5) * w / 6), 0.1, ["FlowerRed", "FlowerYellow"][k % 2], seed + k, 0.9)

def build_rectory():
    g = "CH_Village"
    x0, x1, z0, z1 = -22.5, -13.5, -24.0, -17.0
    gable(g, x0, x1, z0, z1, 0.0, 5.0, 8.4, "Plaster", "RoofTile", 'x', 0.45, 0.25)
    box(g, (x0 + x1) / 2, -0.2, 0.5, (z0 + z1) / 2, x1 - x0 + 0.2, z1 - z0 + 0.2, "Fieldstone")
    # half-timbering on the front (+z) and the gable end facing the square (+x)
    T = "Timber"
    for xx in (x0 + 0.1, x0 + 3.0, x0 + 6.0, x1 - 0.1):
        box(g, xx, 0.5, 5.0, z1 + 0.04, 0.2, 0.1, T)
    for yy in (0.55, 2.55, 4.9):
        box(g, (x0 + x1) / 2, yy - 0.1, yy + 0.1, z1 + 0.04, x1 - x0, 0.1, T)
    for (xa, xb) in ((x0 + 0.1, x0 + 3.0), (x0 + 6.0, x1 - 0.1)):
        beam(g, (xa, 2.65, z1 + 0.05), (xb, 4.8, z1 + 0.05), 0.16, 0.08, T)
    for zz in (z0 + 0.1, (z0 + z1) / 2, z1 - 0.1):
        box(g, x1 + 0.04, 0.5, 5.0, zz, 0.1, 0.2, T)
    for yy in (0.55, 2.55, 4.9):
        box(g, x1 + 0.04, yy - 0.1, yy + 0.1, (z0 + z1) / 2, 0.1, z1 - z0, T)
    beam(g, (x1 + 0.05, 5.0, z0 + 0.2), (x1 + 0.05, 8.2, (z0 + z1) / 2), 0.16, 0.08, T)
    beam(g, (x1 + 0.05, 5.0, z1 - 0.2), (x1 + 0.05, 8.2, (z0 + z1) / 2), 0.16, 0.08, T)
    box(g, x1 + 0.04, 5.0, 8.1, (z0 + z1) / 2, 0.1, 0.2, T)
    # door with a little porch roof, windows with flower boxes
    box(g, -15.2, 0.5, 2.6, z1 + 0.03, 1.15, 0.08, "DoorWood")
    box(g, -15.2, 0.0, 0.5, z1 + 0.45, 1.6, 0.9, "Fieldstone")
    hexa(g, [(-16.3, 2.85, z1), (-14.1, 2.85, z1), (-14.1, 2.45, z1 + 1.1), (-16.3, 2.45, z1 + 1.1),
             (-16.3, 3.0, z1), (-14.1, 3.0, z1), (-14.1, 2.6, z1 + 1.1), (-16.3, 2.6, z1 + 1.1)], "RoofTile")
    for xx in (-21.0, -18.0):
        window_box(g, xx, 1.2, z1, seed=int(-xx * 10))
    for xx in (-21.0, -18.0, -15.2):
        window_box(g, xx, 3.2, z1, 0.8, 1.0, flowers=False, seed=int(-xx * 7))
    window_box(g, x1, 1.2, -20.5, face='+x', seed=31)
    window_box(g, x1, 3.2, -20.5, 0.8, 1.0, face='+x', flowers=False)
    window_box(g, x1, 5.6, -20.5, 0.6, 0.8, face='+x', flowers=False)
    # chimney (smoke card on top)
    box(g, -20.0, 6.0, 9.6, -21.5, 0.9, 0.9, "Brick")
    box(g, -20.0, 9.6, 9.8, -21.5, 1.05, 1.05, "StoneTrim")
    for a in (0.3, 0.3 + math.pi / 2):
        dx, dz = math.cos(a) * 0.6, math.sin(a) * 0.6
        card("CH_Smoke", [(-20.0 - dx, 9.7, -21.5 - dz), (-20.0 + dx, 9.7, -21.5 + dz), (-21.8 + dx * 2.4, 16.5, -21.5 + dz * 2.4), (-21.8 - dx * 2.4, 16.5, -21.5 - dz * 2.4)], 0, "SmokeCard")
    # front garden: picket fence, flower beds, a gravel path to the door
    zf = -13.6
    for (xa, xb) in ((-24.5, -15.9), (-14.5, -12.8)):
        n = int((xb - xa) / 0.22)
        for k in range(n + 1):
            xx = xa + (xb - xa) * k / n
            box(g, xx, 0.0, 0.9, zf, 0.08, 0.04, "PaintWhite")
            prism(g, [(xx - 0.04, 0.9), (xx + 0.04, 0.9), (xx, 1.0)][::-1], 'z', zf - 0.02, zf + 0.02, "PaintWhite")
        for yy in (0.3, 0.72):
            box(g, (xa + xb) / 2, yy - 0.04, yy + 0.04, zf - 0.04, xb - xa, 0.04, "PaintWhite")
    for xx in (-15.9, -14.5):
        box(g, xx, 0.0, 1.15, zf, 0.14, 0.14, "PaintWhite")
    box(g, -12.8, 0.0, 1.15, zf, 0.14, 0.14, "PaintWhite")
    for k in range(int(10.0 / 0.22)):                                      # side fence toward the house
        zz = zf - k * 0.22
        if zz < z1 + 0.1:
            break
        box(g, -12.8, 0.0, 0.9, zz, 0.04, 0.08, "PaintWhite")
    rnd = random.Random(12); cols = ["FlowerRed", "FlowerYellow", "FlowerWhite", "FlowerViolet", "FlowerPink"]
    for k in range(70):
        fx = rnd.uniform(-24.2, -13.2); fz = rnd.uniform(-16.6, -14.0)
        if -16.0 < fx < -14.4:
            continue
        ico(g, (fx, 0.18, fz), rnd.uniform(0.2, 0.32), "Foliage", 300 + k, 0.7)
        ico(g, (fx, 0.4, fz), rnd.uniform(0.07, 0.11), cols[k % 5], 400 + k, 0.8)
    # vegetable rows beside the house
    for r in range(4):
        for k in range(8):
            ico(g, (-25.5 - r * 0.8, 0.2, -23.5 + k * 0.85), 0.26, "Foliage", 600 + r * 10 + k, 0.6)
    # the well
    wx, wz = -11.2, -15.6
    lathe(g, wx, 0.0, wz, [(0, 0.1), (0.85, 0.0), (0.85, 0.85), (0.62, 0.9), (0.62, 0.25), (0, 0.25)], 16, "Fieldstone")
    for s in (-1, 1):
        box(g, wx + s * 0.75, 0.8, 2.6, wz, 0.14, 0.14, "Wood")
    gable(g, wx - 1.05, wx + 1.05, wz - 0.7, wz + 0.7, 2.5, 2.55, 3.2, "Wood", "RoofTile", 'x', 0.1, 0.08)
    hcyl(g, (wx - 0.75, 2.0, wz), (wx + 0.95, 2.0, wz), 0.1, "Wood", 8)
    box(g, wx + 0.97, 1.75, 2.05, wz, 0.05, 0.05, "Iron")
    lathe(g, wx - 0.1, 1.05, wz + 0.2, [(0, 0), (0.17, 0.0), (0.21, 0.32), (0, 0.32)], 10, "Wood")
    tube(g, [(wx - 0.1, 1.37, wz + 0.2), (wx - 0.1, 1.95, wz + 0.1)], 0.012, "Iron", 4)
    # laundry line
    for xx in (-25.8, -20.8):
        box(g, xx, 0.0, 2.3, -11.6, 0.12, 0.12, "Wood")
        box(g, xx, 2.2, 2.28, -11.6, 0.12, 0.6, "Wood")
    tube(g, [(-25.8, 2.15, -11.6), (-23.3, 2.02, -11.6), (-20.8, 2.15, -11.6)], 0.012, "PaintWhite", 4)
    for k, (xa, xb, yb) in enumerate(((-25.4, -24.2, 1.05), (-23.9, -23.2, 1.45), (-22.9, -21.4, 0.95))):
        yt = 2.1 - 0.06 * (1 - abs((xa + xb) / 2 + 23.3) / 2.5)
        card("CH_Cloth", [(xa, yb, -11.6), (xb, yb, -11.6), (xb, yt, -11.6), (xa, yt, -11.6)], k, "ClothCard")
    tufts_along((-24.5, -13.3), (-13.0, -13.3), 22, 0.9, 41)
    tufts_along((x1 + 0.3, z0), (x1 + 0.3, z1), 8, 0.9, 42)

def build_oak():
    g = "CH_Village"; x, z = OAK; rnd = random.Random(77)
    lathe(g, x, -0.1, z, [(0, 0), (1.1, 0.0), (0.72, 0.4), (0.6, 1.2), (0.52, 3.4), (0.62, 3.9), (0, 4.2)], 12, "Bark")
    tips = []
    for k in range(7):
        a = 2 * math.pi * k / 7 + rnd.uniform(-0.3, 0.3)
        L = rnd.uniform(2.6, 4.2); up = rnd.uniform(1.5, 3.0)
        p0 = (x, 3.4, z); p1 = (x + math.cos(a) * L * 0.5, 3.4 + up * 0.6, z + math.sin(a) * L * 0.5)
        p2 = (x + math.cos(a) * L, 3.4 + up, z + math.sin(a) * L)
        tube(g, [p0, p1, p2], 0.22, "Bark", 6)
        tips.append(p2)
    for k in range(30):
        a = rnd.uniform(0, 2 * math.pi); r = rnd.uniform(0.0, 4.6)
        c = (x + r * math.cos(a), rnd.uniform(5.4, 8.6) - r * 0.25, z + r * math.sin(a) * 0.9)
        ico(g, c, rnd.uniform(1.4, 2.3), "OakLeaf", 900 + k, 0.75)
    for k, p in enumerate(tips):
        ico(g, (p[0], p[1] + 0.6, p[2]), rnd.uniform(1.3, 1.8), "OakLeaf", 950 + k, 0.8)
    # a bench beneath it, roots and grass
    bx, bz = x + 1.8, z + 3.0
    for s in (-1, 1):
        box(g, bx + s * 0.8, 0.0, 0.45, bz, 0.1, 0.45, "Iron")
    box(g, bx, 0.45, 0.52, bz, 1.9, 0.45, "Wood")
    box(g, bx, 0.6, 1.0, bz - 0.24, 1.9, 0.06, "Wood")
    for k in range(5):
        a = 2 * math.pi * k / 5 + 0.4
        tube(g, [(x + math.cos(a) * 0.5, 0.4, z + math.sin(a) * 0.5), (x + math.cos(a) * 1.6, 0.0, z + math.sin(a) * 1.6)], 0.16, "Bark", 6)
    for k in range(16):
        a = rnd.uniform(0, 2 * math.pi); r = rnd.uniform(1.2, 3.6)
        tuft(x + r * math.cos(a), z + r * math.sin(a), 1.0, rnd.choice((0, 1, 2)), 1000 + k)

def headstone(g, x, z, kind, rot, seed):
    rnd = random.Random(seed)
    h = rnd.uniform(0.8, 1.25)
    if kind == 0:      # rounded slab
        w = 0.62
        pts = [(x - w / 2, 0.0), (x + w / 2, 0.0)] + [(x + w / 2 * math.cos(a), h - w / 2 + w / 2 * math.sin(a)) for a in [math.pi * k / 6 for k in range(7)]]
        prism(g, pts[::-1], 'z', z - 0.08, z + 0.08, "Headstone")
    elif kind == 1:    # cross
        box(g, x, 0.0, h + 0.3, z, 0.16, 0.14, "Headstone", 0.0, rot)
        box(g, x, h - 0.15, h + 0.0, z, 0.62, 0.14, "Headstone", 0.0, rot)
    elif kind == 2:    # pointed slab
        w = 0.56
        prism(g, [(x - w / 2, 0.0), (x + w / 2, 0.0), (x + w / 2, h - 0.25), (x, h), (x - w / 2, h - 0.25)][::-1], 'z', z - 0.07, z + 0.07, "Headstone")
    else:              # obelisk
        box(g, x, 0.0, 0.35, z, 0.6, 0.6, "Headstone", 0.0, rot)
        lathe(g, x, 0.35, z, [(0, 0), (0.22, 0.0), (0.14, h + 0.6), (0, h + 0.8)], 4, "Headstone", math.pi / 4 + math.radians(rot))
    box(g, x, -0.05, 0.08, z + 0.05, 0.8, 0.34, "Headstone", 0.0, rot)

def build_churchyard():
    g = "CH_Village"
    xa, xb, zf, zb = 12.6, 32.0, -14.0, -38.0
    def wall(x0, z0, x1, z1):
        L = math.hypot(x1 - x0, z1 - z0); rot = math.degrees(math.atan2(-(z1 - z0), x1 - x0))
        obox(g, ((x0 + x1) / 2, 0.5, (z0 + z1) / 2), (L, 1.0, 0.55), rot, "Fieldstone")
        obox(g, ((x0 + x1) / 2, 1.05, (z0 + z1) / 2), (L + 0.1, 0.12, 0.7), rot, "StoneTrim")
    wall(xa, zf, 15.0, zf); wall(17.0, zf, xb, zf); wall(xa, zf, xa, zb); wall(xa, zb, xb, zb)
    # the lychgate over the gap
    for sx in (15.0, 17.0):
        for sz in (zf - 0.5, zf + 0.5):
            box(g, sx, 0.0, 2.2, sz, 0.18, 0.18, "Timber")
    gable(g, 14.6, 17.4, zf - 0.8, zf + 0.8, 2.2, 2.25, 3.4, "Timber", "Slate", 'x', 0.2, 0.12)
    # headstones
    rnd = random.Random(21)
    for r, z in enumerate((-17.0, -20.4, -23.8, -27.2, -30.6, -34.0)):
        for k in range(8):
            x = 14.6 + k * 2.2 + rnd.uniform(-0.3, 0.3)
            if rnd.random() < 0.2:
                continue
            if r == 0 and 14.5 < x < 17.6:
                continue
            headstone(g, x, z + rnd.uniform(-0.3, 0.3), rnd.choice((0, 0, 1, 1, 2, 3)), rnd.uniform(-8, 8), 500 + r * 20 + k)
            tuft(x + rnd.uniform(-0.5, 0.5), z + 0.4, 0.8, rnd.choice((0, 1)), 700 + r * 20 + k)
    # yews
    for (x, z, s) in ((30.0, -36.0, 1.0), (14.4, -35.5, 0.85), (31.0, -16.0, 0.7)):
        cyl(g, x, -0.1, z, 0.3 * s, 0.25 * s, 1.6 * s, "Bark", 7)
        for k in range(5):
            ico(g, (x, (1.6 + k * 1.15) * s, z), (2.0 - k * 0.35) * s, "Yew", int(x * 10) + k, 0.9)
    tufts_along((xa + 0.4, zf + 0.4), (xb, zf + 0.4), 26, 0.9, 51)
    tufts_along((xa - 0.4, zf), (xa - 0.4, zb), 18, 0.9, 52)

def build_props():
    g = "CH_Village"
    # hay bales on the right, in front
    for (x, y, z, a) in ((15.6, 0.75, 3.6, 8.0), (17.6, 0.75, 4.4, -10.0), (16.5, 2.18, 4.0, 2.0), (19.6, 0.75, 7.6, 30.0)):
        ca, sa = math.cos(math.radians(a)), math.sin(math.radians(a))
        hcyl(g, (x - 0.65 * ca, y, z + 0.65 * sa), (x + 0.65 * ca, y, z - 0.65 * sa), 0.75, "Hay", 14)
    # post-and-rail fences along both sides of the square
    for s in (-1, 1):
        x = s * 13.9
        for k in range(7):
            box(g, x, 0.0, 1.2, 1.0 + k * 2.6, 0.16, 0.16, "Wood")
        for y in (0.5, 1.0):
            box(g, x, y - 0.06, y + 0.06, 1.0 + 3 * 2.6, 0.08, 6 * 2.6, "Wood")
        tufts_along((x, 0.5), (x, 17.0), 14, 1.0, 60 + (s > 0))
    # a hand cart by the churchyard wall
    cx, cz = 10.8, -11.6
    box(g, cx, 0.55, 0.62, cz, 2.0, 1.1, "Wood")
    for s in (-1, 1):
        box(g, cx, 0.62, 0.95, cz + s * 0.52, 2.0, 0.06, "Wood")
    box(g, cx - 0.97, 0.62, 0.95, cz, 0.06, 1.1, "Wood")
    for s in (-1, 1):
        hcyl(g, (cx + 0.3, 0.42, cz + s * 0.62), (cx + 0.3, 0.42, cz + s * 0.7), 0.42, "Wood", 14)
    tube(g, [(cx + 1.0, 0.6, cz - 0.4), (cx + 2.1, 0.2, cz - 0.45)], 0.04, "Wood", 5)
    tube(g, [(cx + 1.0, 0.6, cz + 0.4), (cx + 2.1, 0.2, cz + 0.45)], 0.04, "Wood", 5)
    for k in range(6):
        ico(g, (cx + random.Random(k).uniform(-0.7, 0.7), 0.9, cz + random.Random(k + 5).uniform(-0.3, 0.3)), 0.36, "Hay", 800 + k, 0.6)
    # grass along the chapel walls and around the statue and steps
    tufts_along((-NAVE_W - 0.5, FACADE_Z + 0.6), (-2.9, FACADE_Z + 0.6), 8, 0.9, 70)
    tufts_along((2.9, FACADE_Z + 0.6), (TOWER[0] + 2.4, FACADE_Z + 0.6), 10, 0.9, 71)
    tufts_along((-NAVE_W - 0.7, FACADE_Z - 1), (-NAVE_W - 0.7, FACADE_Z - NAVE_L), 14, 0.9, 72)
    rnd = random.Random(73)
    for k in range(18):
        a = rnd.uniform(0, 2 * math.pi)
        tuft(STATUE[0] + 2.85 * math.cos(a), STATUE[1] + 2.85 * math.sin(a), 0.8, rnd.choice((0, 1)), 1100 + k)
    # scattered tufts and flowers in the meadow behind the lane and at the sides
    for k in range(120):
        x = rnd.uniform(-40, 40); z = rnd.uniform(-60, 20)
        if abs(x) < 13.5 and z > -19:
            continue
        if -6 < x < 10.5 and z < -26:
            continue
        if 12.0 < x < 32.5 and -38.5 < z < -13.5:
            continue
        if -27 < x < -12.5 and -25 < z < -11:
            continue
        tuft(x, z, rnd.uniform(0.9, 1.3), rnd.choice((0, 1, 1, 2)), 1200 + k)

# ======================================================================
#  the countryside
# ======================================================================
def hf(x, z):
    """Terrain height (Godot y) beyond the floor."""
    d = -z
    r = min(max((d - 92.0) / 90.0, 0.0), 1.0)
    r = r * r * (3 - 2 * r)
    hills = (9.0 * (0.5 + 0.5 * math.sin(x * 0.017 + 1.3)) * (0.5 + 0.5 * math.cos(z * 0.019 + 0.4))
             + 5.0 * math.sin(x * 0.041 - z * 0.013 + 0.7) + 3.5 * math.cos(x * 0.0071 + z * 0.031))
    side = min(max((abs(x) - 70.0) / 120.0, 0.0), 1.0) * 10.0
    far = min(max((d - 230.0) / 220.0, 0.0), 1.0) * 26.0
    return -0.06 + r * (hills + 6.0) + side * min(max((d - 60.0) / 40.0, 0.0), 1.0) + far

def build_terrain():
    g = grp("CH_Land"); bm = g.bm
    xs = [-480 + 12 * i for i in range(81)]
    zs = [-78 - 12 * j for j in range(43)]
    V2 = [[bm.verts.new(G(x, hf(x, z), z)) for x in xs] for z in zs]
    faces = []
    for j in range(len(zs) - 1):
        for i in range(len(xs) - 1):
            faces.append(bm.faces.new((V2[j][i], V2[j][i + 1], V2[j + 1][i + 1], V2[j + 1][i])))
    bmesh.ops.recalc_face_normals(bm, faces=faces)
    for f in faces:
        if f.normal.z < 0:
            f.normal_flip()
    _tag(g, faces, "Land")
    # side ground beside the floor (beyond x +-60), sloping up gently
    for s in (-1, 1):
        a, b = sorted((s * 59.0, s * 480.0))
        box(g, (a + b) / 2, -1.0, -0.08, -28.0, b - a, 100.0, "Land")

def farmhouse(x, z, rot, seed):
    g = "CH_Land"; y = hf(x, z); rnd = random.Random(seed)
    w, d = rnd.uniform(7, 11), rnd.uniform(5, 7)
    obox(g, (x, y + 2.0, z), (w, 4.4, d), rot, "FarmWall")
    ca, sa = math.cos(math.radians(rot)), math.sin(math.radians(rot))
    # roof as a rotated prism: build in local space via gable on an axis-aligned box, then it is good enough unrotated
    gable(g, x - w / 2, x + w / 2, z - d / 2, z + d / 2, y + 3.6, y + 4.0, y + 6.8, "FarmWall", "FarmRoof", 'x', 0.4, 0.3)
    if rnd.random() < 0.6:   # a barn beside it
        bx = x + w / 2 + 6
        gable(g, bx - 4, bx + 4, z - 5, z + 5, hf(bx, z) - 0.5, hf(bx, z) + 4.2, hf(bx, z) + 8.5, "FarmRoof", "FarmRoof", 'z', 0.4, 0.3)
    for k in range(rnd.randint(2, 5)):
        tx, tz = x + rnd.uniform(-14, 14), z + rnd.uniform(4, 12)
        ico(g, (tx, hf(tx, tz) + 4.0, tz), rnd.uniform(2.6, 4.0), "Forest", seed * 10 + k, 0.9)

def build_country():
    g = "CH_Land"; rnd = random.Random(31)
    build_terrain()
    for k, (x, z, r) in enumerate(((44, -128, 0), (-112, -170, 0), (96, -214, 0), (-34, -248, 0), (152, -156, 0), (-170, -232, 0), (210, -300, 0), (-250, -320, 0))):
        farmhouse(x, z, r, 40 + k)
    # windmill on a hill to the left
    mx, mz = -66.0, -150.0; my = hf(mx, mz)
    lathe(g, mx, my - 0.5, mz, [(0, 0), (3.4, 0.0), (3.1, 1.0), (2.3, 11.5), (2.5, 11.8), (0, 11.8)], 12, "Mill")
    lathe(g, mx, my + 11.5, mz, [(0, 0), (2.7, 0.0), (2.4, 1.4), (1.2, 3.0), (0, 3.4)], 10, "FarmRoof")
    hcyl(g, (mx, my + 12.4, mz + 1.6), (mx, my + 12.4, mz + 3.4), 0.35, "Iron", 8)
    card("CH_Sails", [(mx - 10.5, my + 1.9, mz + 3.45), (mx + 10.5, my + 1.9, mz + 3.45), (mx + 10.5, my + 22.9, mz + 3.45), (mx - 10.5, my + 22.9, mz + 3.45)], 0, "SailsCard")
    MILL[0] = (mx, my + 12.4, mz + 3.45)
    # poplars along a lane to the right
    for k in range(12):
        x = 34.0 + k * 7.5; z = -104.0 - k * 2.0
        y = hf(x, z)
        lathe(g, x, y - 0.3, z, [(0, 0), (0.3, 0.0), (0.3, 2.0), (1.5, 4.0), (1.9, 9.0), (1.3, 14.0), (0, 17.5)], 8, "Forest")
    # woods
    for (cx, cz, n, R) in ((-140, -122, 22, 26), (120, -136, 18, 22), (62, -270, 26, 34), (-96, -305, 30, 40), (220, -250, 24, 36),
                           (-230, -190, 20, 30), (0, -350, 26, 50), (-20, -110, 6, 10)):
        for k in range(n):
            a = rnd.uniform(0, 2 * math.pi); r = R * math.sqrt(rnd.random())
            x, z = cx + r * math.cos(a), cz + r * math.sin(a)
            ico(g, (x, hf(x, z) + rnd.uniform(3.0, 5.5), z), rnd.uniform(3.2, 5.8), "Forest", int(cx * 7 + k), 0.9)
    # hedgerow trees dotted about
    for k in range(40):
        x = rnd.uniform(-300, 300); z = rnd.uniform(-120, -420)
        ico(g, (x, hf(x, z) + 3.5, z), rnd.uniform(2.5, 4.0), "Forest", 3000 + k, 0.95)
    # the mountains
    for k in range(18):
        x = -760 + k * 90 + rnd.uniform(-25, 25)
        R = rnd.uniform(130, 220); H = rnd.uniform(48, 88)
        lathe(g, x, -5.0, -700 + rnd.uniform(-60, 60), [(0, 0), (R, 0.0), (R * 0.58, H * 0.45), (R * 0.25, H * 0.82), (R * 0.06, H), (0, H + 2)],
              9, "Mountain", rnd.uniform(0, 1))

MILL = [None]

def build_cards():
    g = grp("CH_Sky", "Cards"); n = 128; y0, y1 = -80.0, 700.0
    for i in range(n):
        t0, t1 = i / n, (i + 1) / n
        A0, A1 = 2 * math.pi * t0 - math.pi, 2 * math.pi * t1 - math.pi
        p0 = (SKY_R * math.sin(A0), 0, -100 - SKY_R * math.cos(A0)); p1 = (SKY_R * math.sin(A1), 0, -100 - SKY_R * math.cos(A1))
        quad(g, [(p0[0], y0, p0[2]), (p1[0], y0, p1[2]), (p1[0], y1, p1[2]), (p0[0], y1, p0[2])], [(t0, 0), (t1, 0), (t1, 1), (t0, 1)], "SkyCard")
    # birds wheeling around the bell tower (the shader flies them in circles)
    for k in range(7):
        x, z = TOWER[0] + random.Random(k).uniform(-4, 4), TOWER[1] + random.Random(k + 3).uniform(-2, 3)
        y = 19.0 + k * 0.9
        card("CH_Birds", [(x - 0.45, y - 0.2, z), (x + 0.45, y - 0.2, z), (x + 0.45, y + 0.2, z), (x - 0.45, y + 0.2, z)], k, "BirdCard")

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
    sd = bpy.data.lights.new("Sun", 'SUN'); sd.energy = V["sun"][0]; sd.color = srgb(V["sun"][1]); sd.angle = math.radians(1.5)
    s = bpy.data.objects.new("Sun", sd); col("Lights").objects.link(s)
    d = Vector(SUN_DIR).normalized()
    s.rotation_mode = 'QUATERNION'; s.rotation_quaternion = Vector((d.x, -d.z, d.y)).to_track_quat('-Z', 'Y')
    def area(name, pos, aim, size, power, colr):
        ld = bpy.data.lights.new(name, 'AREA'); ld.shape = 'RECTANGLE'
        ld.size, ld.size_y = size; ld.energy = power; ld.color = srgb(colr)
        o = bpy.data.objects.new(name, ld); col("Lights").objects.link(o); o.location = G(*pos)
        o.rotation_mode = 'QUATERNION'; o.rotation_quaternion = (G(*aim) - G(*pos)).normalized().to_track_quat('-Z', 'Y')
        o.visible_camera = False
    area("Fill_Front", (0, 9.0, 26.0), (0, 2.0, -20.0), (44, 12), V["fill"][0], V["fill"][1])
    area("Fill_Top", (0, 30.0, -14.0), (0, 0.0, -14.0), (50, 50), V["top"][0], V["top"][1])

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
        cd.clip_start = 0.1; cd.clip_end = 1500
        o = bpy.data.objects.new(name, cd); col("Cameras").objects.link(o)
        o.location = G(*pos); o.rotation_euler = (math.radians(90), 0, 0)
    bpy.context.scene.camera = bpy.data.objects["CAM_mid"]

CARD_GROUPS = ("CH_Sky", "CH_Glass", "CH_Grass", "CH_Smoke", "CH_Sails", "CH_Birds", "CH_Cloth")
HIDDEN = ("CH_Glass", "CH_Grass", "CH_Smoke", "CH_Sails", "CH_Birds", "CH_Cloth")

def build_all():
    reset(); COLS.clear(); MATS.clear(); GR.clear(); GRASS.clear()
    build_materials()
    build_floor(); build_chapel(); build_rectory(); build_oak(); build_churchyard(); build_props()
    build_country(); build_cards(); build_preview()
    objs = {name: g.finish() for name, g in list(GR.items())}
    for n in CARD_GROUPS:
        if n in objs:
            objs[n].visible_shadow = False
    for n in HIDDEN:
        if n in objs:
            objs[n].hide_render = True
    build_lights(); build_cameras(); setup_render()
    tris = {o.name: sum(len(p.vertices) - 2 for p in o.data.polygons) for o in objs.values()}
    return {"variant": VARIANT, "objects": list(objs), "tris": tris, "total_tris": sum(tris.values()), "tufts": len(GRASS)}

if __name__ == "__main__":
    BUILD_INFO = build_all()
