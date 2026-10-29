# Roer - 3D stage build script (Blender 5.x, runs in --background).
# Roer, the industrial metropolis of Erebonia (capital of Nortia), at dusk. The fight is on the Upper Level plaza
# at the top of the two giant escalators that run down to the Lower Level; the avenue below leads to the Reinford
# Group headquarters. Around it: the cathedral and the Institute of Technology's green dome on the upper level,
# a railway viaduct with trains crossing, the factory district with smoking chimneys and orbal turbines, airships.
#
#   blender --background --factory-startup --python run_rr.py -- STEPS=build,bake,preview,export CAMS=CAM_mid
#
# Layout is written in GODOT coordinates (x right, y up, +z toward the camera) and converted
# to Blender (Z-up) by G():  Godot (x, y, z) -> Blender (x, -z, y).  1 unit = 1 m.
# Baked groups (atlases): RR_Near (plaza props, escalators, gate), RR_City (plaza buildings, the canyon, viaduct),
#                         RR_Upper (upper-level blocks, cathedral, institute), RR_Far (tower, factories, turbines),
#                         RR_Land (ground slabs, mountains), RR_Floor (light map only)
# Card groups (Godot shaders): RR_Sky, RR_Win, RR_Glow (emit in the bake), RR_Steps, RR_Smoke, RR_Rotor, RR_Train,
#                              RR_Ship, RR_Flag, RR_Haze (not baked)
import bpy, bmesh, math, random
from mathutils import Vector, Matrix

ROOT = r"E:\Netsu Projects\Netsu Fighter\Godot\netsu-vs\stages\roer"
TEXD = ROOT + r"\src\tex"
VARIANT = globals().get("VARIANT") or "dusk"

# ---------------- layout (Godot space, metres) ----------------
FLOOR_X = 40.0                     # the plaza floor quad: x +-40, z -12.5..+22
FLOOR_BACK, FLOOR_FRONT = -12.5, 22.0
LANE_X, LANE_Z = 12.5, -9.0        # keep |x| < 12.5 and z > -9 clear (fight lane)
CENTER_Z = -6.0
EDGE_Z = -12.5                     # the plaza ends at a railing over the drop to the Lower Level
LOW_Y = -7.0                       # the Lower Level street
VAL = 15.0                         # the Lower Level avenue runs between x = -15 and +15
ESC_X, ESC_W = 2.05, 1.75          # the two escalators (centres at x = -2.05 / +2.05)
ESC_Z1 = -25.0                     # where the escalators reach the Lower Level
VIA_Z, VIA_Y = -58.0, 6.6          # the railway viaduct
TOWER = (0.0, -125.0)              # the Reinford Group headquarters
SKY_R = 460.0
SUN_DIR = (-0.06, -0.14, 0.99)     # where the low dusk sun shines TO: it sets just right of the Reinford tower
GATE_Z = EDGE_Z + 0.3              # the gateway arch over the escalator heads

V = dict(world=("#4a4a6e", 0.8), sun=(3.6, "#ffb070"), fill=(3600, "#ffc8a8"), top=(2200, "#8a94c4"),
         lamp_w=150, street_w=110, window_emit=0.8, glow_emit=5.0,
         sky=[(0.0, "#6a5a6a"), (0.06, "#ffb070"), (0.14, "#f08a6a"), (0.32, "#7a6a9a"), (1.0, "#2a3060")], sky_strength=1.1)
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
def plain(name, dark, light, scale=3.0, rough=0.6, emit=0.0, haze=None):
    b = NB(name)
    n = b.noise(b.pos, scale, 4, 0.55)
    c = b.ramp(n.outputs["Fac"], [(0.3, dark), (0.7, light)])
    b.link(c, b.bsdf.inputs["Base Color"]); b.bsdf.inputs["Roughness"].default_value = rough
    if emit > 0:
        b.link(c, b.bsdf.inputs["Emission Color"]); b.bsdf.inputs["Emission Strength"].default_value = emit
    if haze:
        add_haze(b, *haze)
    return b

def add_haze(b, colour, near, far, hmax):
    """Fade into the dusk haze with distance from the plaza (baked in as emission)."""
    dist = b.n("ShaderNodeVectorMath", operation='LENGTH'); b.link(b.pos, dist.inputs[0])
    mr = b.n("ShaderNodeMapRange"); mr.inputs["From Min"].default_value = near; mr.inputs["From Max"].default_value = far
    mr.inputs["To Min"].default_value = 0.0; mr.inputs["To Max"].default_value = hmax
    b.link(dist.outputs["Value"], mr.inputs[0])
    em = b.n("ShaderNodeEmission"); em.inputs["Color"].default_value = (*srgb(colour), 1); em.inputs["Strength"].default_value = 1.0
    mix = b.n("ShaderNodeMixShader"); b.link(mr.outputs[0], mix.inputs[0])
    b.link(b.bsdf.outputs[0], mix.inputs[1]); b.link(em.outputs[0], mix.inputs[2]); b.link(mix.outputs[0], b.out.inputs[0])

def blocks(name, c1, c2, mortar, bw, bh, ms=0.02, rough=0.7, haze=None):
    b = NB(name)
    br = b.n("ShaderNodeTexBrick"); br.offset = 0.5
    for k, v in (("Scale", 1.0), ("Mortar Size", ms), ("Brick Width", bw), ("Row Height", bh)):
        br.inputs[k].default_value = v
    br.inputs["Color1"].default_value = (*srgb(c1), 1); br.inputs["Color2"].default_value = (*srgb(c2), 1)
    br.inputs["Mortar"].default_value = (*srgb(mortar), 1)
    b.link(b.uv, br.inputs["Vector"])
    n = b.noise(b.pos, 1.2, 4, 0.6)
    c = b.mixc(br.outputs["Color"], b.ramp(n.outputs["Fac"], [(0.3, "#c4c4c4"), (0.7, "#ffffff")]), 1.0, 'MULTIPLY')
    b.link(c, b.bsdf.inputs["Base Color"]); b.bsdf.inputs["Roughness"].default_value = rough
    if haze:
        add_haze(b, *haze)
    return b

def bands(name, c1, c2, scale, rough=0.5, haze=None):
    """Horizontal bands (chimney stripes)."""
    b = NB(name)
    sep = b.n("ShaderNodeSeparateXYZ"); b.link(b.pos, sep.inputs[0])
    s = b.math('GREATER_THAN', b.math('FRACT', b.math('MULTIPLY', sep.outputs[2], scale)), 0.5)
    c = b.mixc(c1, c2, s)
    b.link(c, b.bsdf.inputs["Base Color"]); b.bsdf.inputs["Roughness"].default_value = rough
    if haze:
        add_haze(b, *haze)
    return b

def emit_solid(name, color, strength):
    b = NB(name)
    em = b.n("ShaderNodeEmission"); em.inputs["Color"].default_value = (*srgb(color), 1); em.inputs["Strength"].default_value = strength
    b.link(em.outputs[0], b.out.inputs[0])
    return b

def street(name):
    """The Lower Level road: small dark setts with painted lines (centre double line, lane dashes, a crossing
    at the foot of the escalators). Works in Blender space: x across, -y = Godot z."""
    b = NB(name)
    br = b.n("ShaderNodeTexBrick"); br.offset = 0.5
    for k, v in (("Scale", 1.0), ("Mortar Size", 0.02), ("Brick Width", 0.36), ("Row Height", 0.2)):
        br.inputs[k].default_value = v
    br.inputs["Color1"].default_value = (*srgb("#3c3a3a"), 1); br.inputs["Color2"].default_value = (*srgb("#4a4644"), 1)
    br.inputs["Mortar"].default_value = (*srgb("#2a2828"), 1)
    b.link(b.pos, br.inputs["Vector"])
    sep = b.n("ShaderNodeSeparateXYZ"); b.link(b.pos, sep.inputs[0])
    ax = b.math('ABSOLUTE', sep.outputs[0]); zz = b.math('MULTIPLY', sep.outputs[1], -1.0)     # Godot z
    m1 = b.math('LESS_THAN', b.math('ABSOLUTE', b.math('SUBTRACT', ax, 0.22)), 0.07)
    m2 = b.math('MULTIPLY', b.math('LESS_THAN', b.math('ABSOLUTE', b.math('SUBTRACT', ax, 5.6)), 0.08),
                b.math('LESS_THAN', b.math('FRACT', b.math('DIVIDE', zz, 6.0)), 0.5))
    band = b.math('MULTIPLY', b.math('GREATER_THAN', zz, -31.5), b.math('LESS_THAN', zz, -28.0))
    m3 = b.math('MULTIPLY', b.math('MULTIPLY', band, b.math('LESS_THAN', b.math('FRACT', b.math('DIVIDE', ax, 1.1)), 0.5)),
                b.math('LESS_THAN', ax, 11.0))
    m = b.math('MAXIMUM', b.math('MAXIMUM', m1, m2), m3)
    c = b.mixc(br.outputs["Color"], "#c8b880", m)
    b.link(c, b.bsdf.inputs["Base Color"]); b.bsdf.inputs["Roughness"].default_value = 0.8
    return b

HZ = "#b08a8a"
def build_materials():
    plain("Granite", "#8a8680", "#a8a49c", 3.0, 0.5)
    plain("Concrete", "#6a6866", "#868480", 2.0, 0.8)
    plain("Steel", "#2c323c", "#424a56", 6.0, 0.4)
    plain("SteelLight", "#6a7480", "#9aa4b0", 6.0, 0.3)
    plain("Rubber", "#0e0f12", "#1c1e22", 8.0, 0.7)
    plain("Gold", "#8a6a2a", "#c89a48", 8.0, 0.3, emit=0.08)
    blocks("FacadeA", "#b4a088", "#c4b096", "#7a6a5a", 1.2, 0.6, 0.012)
    blocks("FacadeB", "#7a8290", "#8a92a0", "#4a5058", 1.4, 0.7, 0.012)
    blocks("FacadeC", "#7a3e2e", "#8a4a36", "#3a2a24", 0.26, 0.085, 0.015)
    blocks("FacadeD", "#c8baa0", "#d6c8ae", "#8a7c6a", 1.0, 0.5, 0.012)
    blocks("FacadeAF", "#a8967e", "#b8a48a", "#6a5c4e", 1.2, 0.6, 0.012, haze=(HZ, 60, 220, 0.6))
    blocks("FacadeBF", "#6e7684", "#7e8694", "#44484e", 1.4, 0.7, 0.012, haze=(HZ, 60, 220, 0.6))
    blocks("FacadeCF", "#6e382a", "#7e4432", "#342620", 0.26, 0.085, 0.015, haze=(HZ, 60, 220, 0.6))
    blocks("FacadeDF", "#bcae94", "#cabca2", "#7e705e", 1.0, 0.5, 0.012, haze=(HZ, 60, 220, 0.6))
    plain("Trim", "#b8b0a2", "#d0c8ba", 4.0, 0.5)
    plain("Roof", "#2a2e36", "#3a404a", 3.0, 0.6)
    plain("Copper", "#4a8a78", "#6aa894", 3.0, 0.5)
    plain("Awning", "#6a1e1e", "#8a2a26", 6.0, 0.8)
    plain("AwningB", "#1e3a5a", "#2a4e72", 6.0, 0.8)
    plain("Pavement", "#5a5856", "#76726c", 4.0, 0.8)
    blocks("PlazaPaving", "#9c988f", "#85817a", "#5c5a55", 1.6, 1.6, 0.006, 0.5)
    for nm, c in (("CarRed", "#7a1c1c"), ("CarCream", "#c8bc9c"), ("CarBlue", "#22406a"), ("CarBlack", "#1a1c20"), ("CarGreen", "#2a4a3a")):
        plain(nm, c, c, 2.0, 0.3)
    plain("Ground", "#2e2a2c", "#403a3a", 1.0, 0.9, haze=(HZ, 80, 300, 0.85))
    plain("Foliage", "#2a4a2a", "#3e6a36", 5.0, 0.8)
    plain("Bark", "#2e2218", "#463424", 5.0, 0.8)
    plain("Glass", "#1a2434", "#2a3a50", 2.0, 0.2, haze=(HZ, 80, 260, 0.5))
    plain("TowerStone", "#4a4e58", "#5c606a", 2.0, 0.5, haze=(HZ, 80, 260, 0.5))
    plain("Iron", "#24262a", "#34363a", 4.0, 0.5, haze=(HZ, 100, 300, 0.75))
    plain("Rust", "#5a3424", "#74442e", 4.0, 0.7, haze=(HZ, 100, 300, 0.75))
    blocks("Factory", "#5a3a2e", "#664436", "#2a201c", 0.4, 0.12, 0.02, haze=(HZ, 100, 300, 0.75))
    bands("Chimney", "#8a2a22", "#c8c0b4", 0.18, 0.6, haze=(HZ, 100, 300, 0.7))
    plain("Turbine", "#3a4450", "#56606c", 3.0, 0.4, haze=(HZ, 100, 300, 0.7))
    plain("Mountain", "#4a3e4e", "#5a4c5c", 0.5, 0.9, haze=(HZ, 200, 500, 0.9))
    b = NB("FloorPlaza"); b.bsdf.inputs["Base Color"].default_value = (*srgb("#9a968e"), 1); b.bsdf.inputs["Roughness"].default_value = 0.5
    b = NB("SkyCard")
    sep = b.n("ShaderNodeSeparateXYZ"); b.link(b.uv, sep.inputs[0])
    em = b.n("ShaderNodeEmission"); em.inputs["Strength"].default_value = V["sky_strength"]
    b.link(b.ramp(sep.outputs[1], V["sky"]), em.inputs["Color"]); b.link(em.outputs[0], b.out.inputs[0])
    emit_solid("WindowCard", "#ffc890", V["window_emit"])
    emit_solid("GlowWarm", "#ffd8a0", V["glow_emit"])
    emit_solid("GlowSign", "#9ae0ff", V["glow_emit"])
    emit_solid("GlowGreen", "#60ffb0", V["glow_emit"])
    emit_solid("GlowRed", "#ff3a2a", V["glow_emit"])
    for nm in ("StepsCard", "SmokeCard", "RotorCard", "TrainCard", "ShipCard", "FlagCard", "HazeCard"):
        emit_solid(nm, "#808080", 0.0)
    b = NB("Stand_P1"); b.bsdf.inputs["Base Color"].default_value = (*srgb("#2d6cdf"), 1)
    b = NB("Stand_P2"); b.bsdf.inputs["Base Color"].default_value = (*srgb("#e0463a"), 1)

# ======================================================================
#  the plaza (Upper Level)
# ======================================================================
POINTS = []        # (x, y, z, watts, hex) point lights for the bake

def build_floor():
    g = grp("RR_Floor")
    quad(g, [(-FLOOR_X, 0, FLOOR_FRONT), (FLOOR_X, 0, FLOOR_FRONT), (FLOOR_X, 0, FLOOR_BACK), (-FLOOR_X, 0, FLOOR_BACK)],
         [(-FLOOR_X, -FLOOR_FRONT), (FLOOR_X, -FLOOR_FRONT), (FLOOR_X, -FLOOR_BACK), (-FLOOR_X, -FLOOR_BACK)], "FloorPlaza")

def orbal_lamp(x, z, h=6.4, arms=2, g="RR_Near"):
    """A modern Erebonian street lamp: dark pole, curved arms, glowing orbal globes."""
    lathe(g, x, 0.0, z, [(0, 0), (0.28, 0.0), (0.28, 0.25), (0.14, 0.4), (0.09, 0.8), (0.07, h), (0.12, h + 0.12), (0, h + 0.2)], 10, "Steel")
    for k in range(arms):
        s = (-1) ** k
        tube(g, [(x, h - 0.4, z), (x + s * 0.5, h - 0.1, z), (x + s * 0.95, h - 0.3, z)], 0.05, "Steel", 6)
        glow_lathe("RR_Glow", x + s * 0.95, h - 0.75, z, [(0, 0), (0.18, 0.06), (0.22, 0.24), (0.14, 0.42), (0, 0.45)], 0)
        POINTS.append((x + s * 0.95, h - 0.6, z, V["lamp_w"], "#ffd2a0"))
    glow_box("RR_Glow", (x, 2.4, z), (0.2, 1.2, 0.2), 1, "GlowSign")      # a lit orbal band on the pole

def bench(x, z, along_z=True, g="RR_Near"):
    sx, sz = (0.5, 1.8) if along_z else (1.8, 0.5)
    box(g, x, 0.0, 0.42, z, sx, sz, "Steel")
    box(g, x, 0.42, 0.5, z, sx + 0.06, sz + 0.06, "Granite")
    if along_z:
        box(g, x + (0.22 if x > 0 else -0.22), 0.5, 1.0, z, 0.08, sz, "Steel")
    else:
        box(g, x, 0.5, 1.0, z - 0.22, sx, 0.08, "Steel")

def planter_tree(x, z, seed, g="RR_Near", s=1.0, y0=0.0):
    rnd = random.Random(seed)
    box(g, x, y0, y0 + 0.7, z, 1.5 * s, 1.5 * s, "Granite", 0.04)
    box(g, x, y0 + 0.6, y0 + 0.72, z, 1.3 * s, 1.3 * s, "Bark")
    cyl(g, x, y0 + 0.7, z, 0.12 * s, 0.09 * s, 2.4 * s, "Bark", 7)
    for k in range(7):
        a = rnd.uniform(0, 6.28); r = rnd.uniform(0.2, 0.7) * s
        ico(g, (x + r * math.cos(a), y0 + (3.0 + rnd.uniform(-0.3, 0.8)) * s, z + r * math.sin(a)), rnd.uniform(0.7, 1.1) * s, "Foliage", seed * 13 + k)

def orbal_car(x, z, heading, m, g="RR_City", y0=LOW_Y):
    """A boxy orbal car of the 1200s: body, cabin, dark wheels, lit head- and tail-lamps."""
    ca, sa = math.cos(math.radians(heading)), math.sin(math.radians(heading))
    def P(lx, lz):
        return (x + lx * ca + lz * sa, z - lx * sa + lz * ca)
    obox(g, (x, y0 + 0.62, z), (1.8, 0.62, 4.3), heading, m)
    cx, cz = P(0.0, -0.25)
    obox(g, (cx, y0 + 1.22, cz), (1.62, 0.6, 2.1), heading, m)
    obox(g, (cx, y0 + 1.22, cz), (1.66, 0.42, 1.9), heading, "Glass")
    for lx in (-0.86, 0.86):
        for lz in (-1.35, 1.35):
            wx, wz = P(lx, lz)
            obox(g, (wx, y0 + 0.33, wz), (0.24, 0.66, 0.66), heading, "Rubber")
    for lx in (-0.6, 0.6):
        hx, hz = P(lx, 2.16); tx, tz = P(lx, -2.16)
        gg = grp("RR_Glow", "Cards")
        n0 = len(gg.bm.faces); obox(gg, (hx, y0 + 0.75, hz), (0.3, 0.16, 0.04), heading, "GlowWarm"); card_uv(gg, list(gg.bm.faces)[n0:], 0)
        n0 = len(gg.bm.faces); obox(gg, (tx, y0 + 0.75, tz), (0.3, 0.12, 0.04), heading, "GlowRed"); card_uv(gg, list(gg.bm.faces)[n0:], 5)

def kiosk(x, z, g="RR_City", y0=LOW_Y, m="AwningB"):
    box(g, x, y0, y0 + 2.4, z, 1.6, 2.2, "CarGreen")
    box(g, x, y0 + 2.4, y0 + 2.7, z, 2.2, 2.8, m)
    glow_box("RR_Glow", (x, y0 + 1.5, z + 1.11), (1.2, 0.8, 0.02), 0, "GlowWarm")

def ico(g, c, r, m, seed, sy=0.85):
    gg = grp(g) if isinstance(g, str) else g
    rnd = random.Random(seed)
    M = Matrix.Translation(G(*c)) @ Matrix.Diagonal((r, r, r * sy, 1.0))
    res = bmesh.ops.create_icosphere(gg.bm, subdivisions=1, radius=1.0, matrix=M)
    cc = G(*c)
    for v in res["verts"]:
        v.co = cc + (v.co - cc) * rnd.uniform(0.85, 1.12)
    _tag(gg, list({f for v in res["verts"] for f in v.link_faces}), m)

def railing(x0, x1, z, h=1.1, g="RR_Near"):
    box(g, (x0 + x1) / 2, 0.0, 0.25, z, x1 - x0, 0.4, "Granite")
    n = max(1, int((x1 - x0) / 1.6))
    for k in range(n + 1):
        box(g, x0 + (x1 - x0) * k / n, 0.25, h, z, 0.08, 0.08, "Steel")
    box(g, (x0 + x1) / 2, h - 0.04, h + 0.04, z, x1 - x0 + 0.1, 0.12, "SteelLight")
    for y in (0.5, 0.75):
        box(g, (x0 + x1) / 2, y - 0.015, y + 0.015, z, x1 - x0, 0.03, "Steel")

def escalator(xc, up, sid):
    """One giant escalator from the plaza (z EDGE_Z, y 0) down to the Lower Level (ESC_Z1, LOW_Y):
    balustrades with rubber handrails and glowing skirt lines, a truss underneath, and the moving steps card."""
    g = "RR_Near"; hw = ESC_W / 2
    zt, zb = EDGE_Z + 1.2, ESC_Z1 - 1.6          # flat landings at both ends
    def line(z):
        if z >= EDGE_Z:
            return 0.0
        if z <= ESC_Z1:
            return LOW_Y
        return LOW_Y * (EDGE_Z - z) / (EDGE_Z - ESC_Z1)
    pts_z = [zt, EDGE_Z, ESC_Z1, zb]
    for s in (-1, 1):
        x0, x1 = sorted((xc + s * hw, xc + s * (hw + 0.22)))
        for za, zb_ in zip(pts_z[:-1], pts_z[1:]):
            ya, yb = line(za), line(zb_)
            hexa(g, [(x0, ya - 0.9, za), (x1, ya - 0.9, za), (x1, yb - 0.9, zb_), (x0, yb - 0.9, zb_),
                     (x0, ya + 1.0, za), (x1, ya + 1.0, za), (x1, yb + 1.0, zb_), (x0, yb + 1.0, zb_)], "SteelLight")
            tube(g, [((x0 + x1) / 2, ya + 1.05, za), ((x0 + x1) / 2, yb + 1.05, zb_)], 0.06, "Rubber", 6)
            xi = x1 if s < 0 else x0
            gg = grp("RR_Glow", "Cards")
            quad(gg, [(xi, ya + 0.12, za), (xi, yb + 0.12, zb_), (xi, yb + 0.2, zb_), (xi, ya + 0.2, za)],
                 [(0, 4.1), (1, 4.1), (1, 4.9), (0, 4.9)], "GlowSign")
    # truss underneath (the incline only) and the floor plates at the landings
    hexa(g, [(xc - hw, -1.1, EDGE_Z), (xc + hw, -1.1, EDGE_Z), (xc + hw, LOW_Y - 1.1, ESC_Z1), (xc - hw, LOW_Y - 1.1, ESC_Z1),
             (xc - hw, -0.05, EDGE_Z), (xc + hw, -0.05, EDGE_Z), (xc + hw, LOW_Y - 0.05, ESC_Z1), (xc - hw, LOW_Y - 0.05, ESC_Z1)], "Steel")
    # the steps card: one strip from the top landing to the bottom one (UV.y 0 -> 1 along it, id: 0 down, 1 up)
    L = [0.0]
    for a, b in zip(pts_z[:-1], pts_z[1:]):
        L.append(L[-1] + math.hypot(b - a, line(b) - line(a)))
    gg = grp("RR_Steps", "Cards")
    for i, (a, b) in enumerate(zip(pts_z[:-1], pts_z[1:])):
        t0, t1 = L[i] / L[-1], L[i + 1] / L[-1]
        ya, yb = line(a) + 0.02, line(b) + 0.02
        quad(gg, [(xc - hw, ya, a), (xc + hw, ya, a), (xc + hw, yb, b), (xc - hw, yb, b)],
             [(0, sid + 0.001 + 0.998 * t0), (1, sid + 0.001 + 0.998 * t0), (1, sid + 0.001 + 0.998 * t1), (0, sid + 0.001 + 0.998 * t1)], "StepsCard")
    # comb plates
    box(g, xc, 0.0, 0.03, zt + 0.25, ESC_W + 0.44, 0.5, "SteelLight")

def build_plaza():
    g = "RR_Near"
    railing(-VAL, -ESC_X - ESC_W / 2 - 0.45, EDGE_Z + 0.15)
    railing(ESC_X + ESC_W / 2 + 0.45, VAL, EDGE_Z + 0.15)
    box(g, 0.0, LOW_Y - 0.2, 0.0, EDGE_Z - 0.2, 2 * VAL, 0.4, "Concrete")          # the drop's retaining wall
    # the two escalators and the deck between them (stainless, following the incline)
    escalator(-ESC_X, False, 0); escalator(ESC_X, True, 1)
    xi = ESC_X - ESC_W / 2 - 0.22
    box(g, 0.0, 0.0, 1.0, EDGE_Z + 0.6, 2 * xi, 1.2, "Granite", 0.03)
    hexa(g, [(-xi, -0.9, EDGE_Z), (xi, -0.9, EDGE_Z), (xi, LOW_Y - 0.9, ESC_Z1), (-xi, LOW_Y - 0.9, ESC_Z1),
             (-xi, 1.0, EDGE_Z), (xi, 1.0, EDGE_Z), (xi, LOW_Y + 1.0, ESC_Z1), (-xi, LOW_Y + 1.0, ESC_Z1)], "SteelLight")
    # the gateway arch with the city's name, standing on the plaza edge over the escalator heads
    gz = GATE_Z
    for s in (-1, 1):
        x = s * 4.45
        box(g, x, 0.0, 0.6, gz, 1.3, 1.3, "Granite", 0.03)
        box(g, x, 0.6, 5.4, gz, 0.9, 0.9, "Steel")
        glow_box("RR_Glow", (x - s * 0.46, 3.0, gz), (0.04, 4.4, 0.18), 1, "GlowSign")
    box(g, 0.0, 5.4, 6.9, gz, 10.2, 1.0, "Steel", 0.03)
    box(g, 0.0, 6.9, 7.1, gz, 10.6, 1.2, "SteelLight")
    box(g, 0.0, 5.32, 5.42, gz + 0.5, 10.0, 0.06, "SteelLight")
    box(g, 0.0, 5.4, 6.4, gz - 1.6, 10.2, 0.4, "Steel")                               # back beam
    for k in range(5):                                                                  # roof ribs between the beams
        box(g, -4.0 + k * 2.0, 6.4, 6.6, gz - 0.8, 0.2, 1.8, "SteelLight")
    # flags with the Reinford emblem either side of the arch
    for s in (-1, 1):
        x = s * 6.9
        lathe(g, x, 0.0, gz, [(0, 0), (0.22, 0.0), (0.2, 0.3), (0.07, 0.4), (0.06, 8.4), (0.12, 8.5), (0, 8.65)], 8, "Steel")
        box(g, x, 7.95, 8.02, gz, 1.5, 0.06, "Steel")
        card("RR_Flag", [(x - 0.7, 4.6, gz + 0.08), (x + 0.7, 4.6, gz + 0.08), (x + 0.7, 7.9, gz + 0.08), (x - 0.7, 7.9, gz + 0.08)],
             0 if s < 0 else 1, "FlagCard")
    # lamps, trees, benches, bollards - in the strip x 13..16.5, outside the fight lane, or behind it
    for s in (-1, 1):
        for z in (-10.6, 1.0, 12.0):
            orbal_lamp(s * 13.3, z)
        for z in (-1.8, 9.0):
            bench(s * 15.3, z)
        for z in (-6.0, 5.5, 16.5):
            planter_tree(s * 14.4, z, 40 + int(z) + (s > 0) * 7, s=0.9)
        for k in range(4):
            cyl(g, s * (6.0 + k * 1.3), 0.0, EDGE_Z + 0.9, 0.14, 0.12, 0.8, "Steel", 8)
            glow_lathe("RR_Glow", s * (6.0 + k * 1.3), 0.8, EDGE_Z + 0.9, [(0, 0), (0.13, 0.0), (0.13, 0.12), (0, 0.14)], 0, 8)

# ======================================================================
#  buildings
# ======================================================================
def building(x0, x1, z0, z1, y0, y1, m="FacadeA", faces=("+z",), g="RR_City", shop=False, roof="flat", seed=0,
             trim="Trim", bands=True, wcol=2.6, wrow=3.4, ww=1.3, wh=1.8):
    rnd = random.Random(seed)
    box(g, (x0 + x1) / 2, y0, y1, (z0 + z1) / 2, x1 - x0, z1 - z0, m)
    box(g, (x0 + x1) / 2, y1 - 0.5, y1, (z0 + z1) / 2, x1 - x0 + 0.5, z1 - z0 + 0.5, trim)           # cornice
    if bands:
        for y in (y0 + 4.0,):
            box(g, (x0 + x1) / 2, y - 0.15, y + 0.15, (z0 + z1) / 2, x1 - x0 + 0.24, z1 - z0 + 0.24, trim)
    if roof == "flat":
        box(g, (x0 + x1) / 2, y1, y1 + 0.6, (z0 + z1) / 2, x1 - x0 - 0.2, z1 - z0 - 0.2, "Roof")
        if rnd.random() < 0.6:                                                      # a water tank / machine room
            cx, cz = rnd.uniform(x0 + 1.5, x1 - 1.5), rnd.uniform(z0 + 1.5, z1 - 1.5)
            box(g, cx, y1 + 0.6, y1 + 2.6, cz, 2.2, 2.2, "Steel")
        if rnd.random() < 0.4:
            cyl(g, rnd.uniform(x0 + 1, x1 - 1), y1 + 0.6, rnd.uniform(z0 + 1, z1 - 1), 0.05, 0.03, 4.0, "Steel", 4)
    elif roof == "mansard":
        hexa(g, [(x0, y1, z0), (x1, y1, z0), (x1, y1, z1), (x0, y1, z1),
                 (x0 + 1.2, y1 + 3.0, z0 + 1.2), (x1 - 1.2, y1 + 3.0, z0 + 1.2), (x1 - 1.2, y1 + 3.0, z1 - 1.2), (x0 + 1.2, y1 + 3.0, z1 - 1.2)], "Roof")
    for f in faces:
        if f[1] == 'z':
            a0, a1, plane = x0 + 0.6, x1 - 0.6, (z1 if f[0] == '+' else z0)
        else:
            a0, a1, plane = z0 + 0.6, z1 - 0.6, (x1 if f[0] == '+' else x0)
        if shop:
            window_grid("RR_Win", f, a0, a1, y0 + 0.4, y0 + 3.4, plane, 3.2, shop=True)
            window_grid("RR_Win", f, a0, a1, y0 + 4.6, y1 - 0.9, plane, wcol, wrow, ww, wh)
        else:
            window_grid("RR_Win", f, a0, a1, y0 + 1.0, y1 - 0.9, plane, wcol, wrow, ww, wh)

def awning(x, z, w, face, y=3.4, m="Awning", g="RR_Near", d=1.0):
    """A sloped shop awning on a facade facing +-x."""
    s = 1 if face == '+x' else -1
    hexa(g, [(x, y, z - w / 2), (x + s * d, y - 0.5, z - w / 2), (x + s * d, y - 0.5, z + w / 2), (x, y, z + w / 2),
             (x, y + 0.08, z - w / 2), (x + s * d, y - 0.42, z - w / 2), (x + s * d, y - 0.42, z + w / 2), (x, y + 0.08, z + w / 2)], m)

def build_plaza_buildings():
    """The buildings around the plaza: shops on the left (a dining bar), RF Arms and Hotel Lagrange on the right."""
    for s in (-1, 1):
        xf = s * 16.5; xb = s * 34.0
        a, b = sorted((xf, xb))
        building(a, b, 2.0, 22.0, 0.0, 14.0, "FacadeA" if s < 0 else "FacadeD", (("+x",) if s < 0 else ("-x",)), "RR_City", True, "mansard", 11 + s)
        building(a, b, -11.5, 1.6, 0.0, 16.0 if s < 0 else 12.5, "FacadeD" if s < 0 else "FacadeB", (("+x",) if s < 0 else ("-x",)), "RR_City", True, "flat", 21 + s)
        for z in (5.0, 9.5, 14.0, 18.5):
            awning(xf, z, 3.6, "+x" if s < 0 else "-x", 3.6, "Awning" if s < 0 else "AwningB")
        for z in (-9.0, -4.5, -0.5):
            awning(xf, z, 3.4, "+x" if s < 0 else "-x", 3.6, "AwningB" if s < 0 else "Awning")
    # signs: the dining bar on the left, the arms store's red sign on the right
    glow_box("RR_Glow", (-16.42, 5.0, -5.0), (0.1, 1.0, 4.2), 1, "GlowSign")
    glow_box("RR_Glow", (16.42, 5.0, -5.0), (0.1, 1.0, 4.2), 5, "GlowRed")
    # Hotel Lagrange: tall, with balconies, on the right corner over the drop
    building(15.0, 34.0, -40.0, -13.0, LOW_Y, 24.0, "FacadeD", ("-x", "+z"), "RR_City", False, "mansard", 31)
    for y in range(-1, 23, 4):
        box("RR_City", 14.8, y - 0.1, y + 0.12, -26.5, 0.8, 25.0, "Trim")
    glow_box("RR_Glow", (14.95, 14.0, -18.0), (0.1, 5.0, 1.0), 1, "GlowSign")
    # the left corner building over the drop
    building(-34.0, -15.0, -40.0, -13.0, LOW_Y, 20.0, "FacadeB", ("+x", "+z"), "RR_City", False, "flat", 33)

def build_lower_level():
    """The Lower Level avenue: paving, lamps, shops along the canyon of buildings that leads to the Khemia Corp tower."""
    g = "RR_City"
    # a pedestrian promenade paved like the plaza above: no road, no kerbs
    box(g, 0.0, LOW_Y - 0.5, LOW_Y, (EDGE_Z + TOWER[1]) / 2, 2 * VAL + 1, EDGE_Z - TOWER[1] + 10, "PlazaPaving")
    for z in (-44.0, -72.0, -97.0):                                                     # a row of trees down the middle
        planter_tree(0.0, z, 700 + int(-z), "RR_City", 1.0, LOW_Y)
        for s in (-1, 1):
            box(g, s * 1.6, LOW_Y, LOW_Y + 0.45, z, 0.5, 1.8, "Granite")                    # stone benches beside them
    for z in (-58.0, -84.0):
        kiosk(0.0, z, m="Awning" if z < -70 else "AwningB")
    for s in (-1, 1):
        for z in range(-30, -115, -14):
            lathe("RR_City", s * 11.6, LOW_Y, z, [(0, 0), (0.18, 0.0), (0.08, 0.4), (0.06, 5.0), (0, 5.1)], 8, "Steel")
            glow_lathe("RR_Glow", s * 11.2, LOW_Y + 4.5, z, [(0, 0), (0.16, 0.0), (0.2, 0.2), (0, 0.4)], 0, 8)
            POINTS.append((s * 11.2, LOW_Y + 4.6, z, V["street_w"], "#ffd2a0"))
            if z < -40:
                planter_tree(s * 12.9, z - 7.0, 300 + z + (s > 0), "RR_City", 0.85, LOW_Y)
        kiosk(s * 12.6, -33.0, m="Awning" if s < 0 else "AwningB")
        # the canyon: buildings along the avenue, a gap where the viaduct crosses
        z = -41.0; k = 0
        while z > TOWER[1] + 14:
            d = random.Random(k * 7 + (s > 0)).uniform(8.0, 13.0)
            z1 = z; z0 = z - d
            if z0 < VIA_Z + 5 and z1 > VIA_Z - 5:
                z = VIA_Z - 6; k += 1; continue
            h = random.Random(k * 11 + (s > 0) * 3).uniform(10.0, 24.0) if z0 > -95 else random.Random(k).uniform(6.0, 11.0)
            m = ["FacadeA", "FacadeB", "FacadeC", "FacadeD"][(k + (s > 0)) % 4]
            a, b = sorted((s * VAL, s * (VAL + 12.0)))
            building(a, b, z0, z1, LOW_Y, h, m, (("-x",) if s > 0 else ("+x",)), g, True, "flat" if k % 3 else "mansard", 50 + k * 2 + (s > 0))
            for zz in (z0 + d * 0.3, z0 + d * 0.72):
                awning(s * VAL, zz, d * 0.35, "-x" if s > 0 else "+x", LOW_Y + 3.6, "Awning" if (k + s) % 2 else "AwningB", g, 1.3)
            z = z0 - 0.4; k += 1

def build_upper_ground():
    """The Upper Level beyond the canyon: ground slabs on both sides (their inner faces are the canyon's walls
    where the viaduct gap opens), dropping to the factory district at z -140."""
    for s in (-1, 1):
        a, b = sorted((s * VAL, s * 240.0))
        box("RR_Land", (a + b) / 2, -9.0, 0.0, -76.25, b - a, 127.5, "Ground")

def build_viaduct():
    """The railway viaduct crossing over the avenue: steel truss, stone piers, the train card."""
    g = "RR_City"; z = VIA_Z
    box(g, 0.0, VIA_Y - 0.9, VIA_Y, z, 180.0, 6.0, "Steel")
    for s in (-1, 1):                                                         # side trusses
        zz = z + s * 2.9
        box(g, 0.0, VIA_Y, VIA_Y + 0.3, zz, 180.0, 0.25, "Steel")
        box(g, 0.0, VIA_Y + 2.7, VIA_Y + 3.0, zz, 180.0, 0.25, "Steel")
        for k in range(-30, 31):
            x = k * 3.0
            box(g, x, VIA_Y + 0.3, VIA_Y + 2.7, zz, 0.2, 0.2, "Steel")
            beam(g, (x, VIA_Y + 0.3, zz), (x + 3.0, VIA_Y + 2.7, zz), 0.14, 0.14, "Steel")
    for x in (-36.0, -12.0, 12.0, 36.0):                                      # piers
        y0 = LOW_Y if abs(x) < VAL else -2.0
        box(g, x, y0, VIA_Y - 0.9, z, 3.2, 5.0, "FacadeC")
        box(g, x, VIA_Y - 1.6, VIA_Y - 0.9, z, 3.8, 5.6, "Trim")
    card("RR_Train", [(-90.0, VIA_Y + 0.1, z + 0.05), (90.0, VIA_Y + 0.1, z + 0.05), (90.0, VIA_Y + 2.6, z + 0.05), (-90.0, VIA_Y + 2.6, z + 0.05)], 0, "TrainCard", 0.0, 180.0 / 20.0)
    POINTS.append((0.0, VIA_Y - 1.5, z + 4.0, 200, "#ffc890"))

def build_tower():
    """The Reinford Group headquarters at the end of the avenue."""
    g = "RR_Far"; x, z = TOWER
    box(g, x, LOW_Y, -3.5, z, 34.0, 24.0, "TowerStone", 0.1)
    box(g, x, -3.5, -2.8, z, 35.0, 25.0, "Trim")
    box(g, x, -2.8, 46.0, z, 20.0, 14.0, "Glass")
    for k in range(-4, 5):                                                    # vertical fins
        box(g, x + k * 2.4, -2.8, 47.0, z + 7.1, 0.35, 0.4, "TowerStone")
    for y in (14.0, 24.0, 36.0):
        box(g, x, y - 0.3, y + 0.3, z, 20.6, 14.6, "Trim")
    box(g, x, 46.0, 54.0, z, 15.0, 10.0, "TowerStone")
    box(g, x, 54.0, 55.0, z, 16.0, 11.0, "Trim")
    cyl(g, x, 55.0, z, 0.4, 0.1, 14.0, "SteelLight", 6)
    window_grid("RR_Win", "+z", x - 9.5, x + 9.5, 5.0, 45.0, z + 7.0, 1.6, 2.6, 1.1, 1.6,
                skip=lambda i, j: 8 <= j <= 10 and 3 <= i <= 7)
    window_grid("RR_Win", "+x", z - 6.5, z + 6.5, 5.0, 45.0, x + 10.0, 1.6, 2.6, 1.1, 1.6)
    window_grid("RR_Win", "+z", x - 9.5, x + 9.5, -2.4, 3.8, z + 7.0, 3.2, shop=True)              # the lit lobby
    window_grid("RR_Win", "-x", z - 6.5, z + 6.5, 5.0, 45.0, x - 10.0, 1.6, 2.6, 1.1, 1.6)
    box(g, x, 27.8, 33.2, z + 7.15, 6.6, 0.3, "Steel")
    letters("RR_Glow", "KC", x - 2.57, 28.5, z + 7.3, 4.0, 5, "GlowRed")
    glow_box("RR_Glow", (x, 50.0, z + 5.1), (15.2, 0.6, 0.1), 1, "GlowSign")
    glow_box("RR_Glow", (x, 69.0, z), (0.5, 0.5, 0.5), 6, "GlowRed")
    POINTS.append((x, 30.0, z + 14.0, 1200, "#ff6a50"))
    # the tower plaza at its foot: steps and a fountain
    box(g, x, LOW_Y, LOW_Y + 0.4, z + 18.0, 30.0, 6.0, "Granite")
    lathe(g, x, LOW_Y, z + 22.0, [(0, 0), (4.0, 0.0), (4.0, 0.8), (3.6, 0.8), (3.6, 0.4), (0.6, 0.4), (0.5, 2.6), (1.4, 2.8), (0, 3.0)], 24, "Granite")

def build_cathedral():
    """Roer Cathedral on the upper level, to the left of the avenue: twin spires, rose window."""
    g = "RR_Upper"; cx, zf = -38.0, -66.0
    gable(g, cx - 7.0, cx + 7.0, zf - 30.0, zf, 0.0, 18.0, 27.0, "FacadeAF", "Roof", 'z', 0.5)
    for s in (-1, 1):
        tx = cx + s * 8.5
        box(g, tx, 0.0, 32.0, zf - 2.5, 5.5, 5.5, "FacadeAF")
        box(g, tx, 32.0, 33.0, zf - 2.5, 6.2, 6.2, "Trim")
        lathe(g, tx, 33.0, zf - 2.5, [(0, 0), (3.0, 0.0), (0.2, 15.0), (0, 15.5)], 8, "Roof", math.pi / 8)
        for y in (10.0, 20.0, 27.0):
            box(g, tx, y, y + 0.5, zf - 2.5, 6.0, 6.0, "Trim")
    box(g, cx, 0.0, 7.0, zf + 0.3, 4.0, 0.6, "Trim")
    box(g, cx, 0.0, 5.4, zf + 0.62, 2.6, 0.1, "Bark")
    for s in (-1, 1):                                                         # buttresses along the nave
        for k in range(4):
            box(g, cx + s * 7.6, 0.0, 14.0, zf - 8.0 - k * 6.0, 1.2, 1.4, "FacadeAF")
    card("RR_Glow", [(cx - 3.0, 12.0, zf + 0.08), (cx + 3.0, 12.0, zf + 0.08), (cx + 3.0, 18.0, zf + 0.08), (cx - 3.0, 18.0, zf + 0.08)], 7, "GlowWarm")
    lathe(g, cx, 26.0, zf - 0.2, [(0, 0), (0.5, 0.0), (0.3, 3.0), (0, 3.2)], 6, "Gold")

def build_institute():
    """The Roer Institute of Technology on the right: a long block under a green copper dome."""
    g = "RR_Upper"; cx, cz = 42.0, -78.0
    building(cx - 14.0, cx + 14.0, cz - 10.0, cz + 10.0, 0.0, 16.0, "FacadeDF", ("+z", "-x"), g, False, "flat", 77)
    lathe(g, cx, 16.0, cz, [(0, 0), (7.0, 0.0), (7.0, 4.0), (7.6, 4.2), (7.0, 4.6), (6.4, 6.8), (5.0, 9.0), (3.0, 10.6), (1.2, 11.3), (1.2, 12.6), (0, 13.6)], 24, "Copper")
    box(g, cx, 16.0, 20.4, cz, 1.0, 1.0, "Trim")

def build_upper_city():
    """Rows of buildings on both upper plateaus, behind the plaza buildings and on toward the factories."""
    rnd = random.Random(3)
    for s in (-1, 1):
        for row in range(4):
            xa = s * (36.0 + row * 16.0)
            for k in range(7):
                z1 = -16.0 - k * 15.0 + rnd.uniform(-2, 2); z0 = z1 - rnd.uniform(9, 13)
                if s < 0 and row == 0 and -96 < z0 < -40:
                    continue                                                   # leave room for the cathedral
                if s > 0 and row <= 1 and -92 < z0 < -60:
                    continue                                                   # and the institute
                h = rnd.uniform(9.0, 26.0) * (1.0 - row * 0.12)
                a, b = sorted((xa, xa + s * rnd.uniform(10, 14)))
                m = ["FacadeAF", "FacadeBF", "FacadeCF"][(row + k) % 3]
                building(a, b, z0, z1, -0.5, h, m, ("+z", "-x" if s > 0 else "+x"), "RR_Upper", False,
                         "flat" if rnd.random() < 0.6 else "mansard", 200 + row * 20 + k + (s > 0) * 100, bands=row < 2)

# ======================================================================
#  the factory district, turbines, sky
# ======================================================================
CHIMNEYS = []

def build_factories():
    g = "RR_Far"; rnd = random.Random(9)
    box("RR_Land", 0.0, -9.0, LOW_Y, -275.0, 900.0, 270.0, "Ground")
    for k in range(18):                                                        # halls with sawtooth roofs
        x = -210.0 + k * 25.0 + rnd.uniform(-4, 4); z = rnd.uniform(-200.0, -160.0)
        w, d, h = rnd.uniform(18, 24), rnd.uniform(20, 34), rnd.uniform(10, 18)
        box(g, x, LOW_Y, LOW_Y + h, z, w, d, "Factory")
        n = int(w / 4); tw = w / n
        for j in range(n):
            xs = x - w / 2 + j * tw
            prism(g, [(xs, LOW_Y + h), (xs + tw, LOW_Y + h), (xs + tw, LOW_Y + h + 3.0)], 'z', z - d / 2, z + d / 2, "Iron")
        if k % 2 == 0:
            ch_h = rnd.uniform(48, 68); cx = x + rnd.uniform(-w / 3, w / 3); cz = z + rnd.uniform(-d / 3, d / 3)
            lathe(g, cx, LOW_Y, cz, [(0, 0), (3.2, 0.0), (2.6, 3.0), (2.0, ch_h), (2.3, ch_h + 0.6), (1.8, ch_h + 0.6), (0, ch_h + 0.6)], 12, "Chimney")
            CHIMNEYS.append((cx, LOW_Y + ch_h + 0.6, cz))
            glow_box("RR_Glow", (cx, LOW_Y + ch_h - 1.0, cz + 2.1), (0.6, 0.6, 0.3), 6, "GlowRed")
    for k in range(6):                                                         # gantry cranes
        x = rnd.uniform(-180, 180); z = rnd.uniform(-150, -140)
        for s in (-1, 1):
            box(g, x + s * 6, LOW_Y, LOW_Y + 24, z, 0.8, 0.8, "Rust")
        box(g, x, LOW_Y + 24, LOW_Y + 26, z, 22.0, 1.6, "Rust")
        box(g, x + 5, LOW_Y + 18, LOW_Y + 24, z, 0.3, 0.3, "Iron")
    # distant ridge behind everything
    for k in range(40):
        x = -420 + k * 22 + rnd.uniform(-6, 6)
        R = rnd.uniform(55, 90); H = rnd.uniform(24, 48)
        lathe("RR_Land", x, -10.0, -430.0 + rnd.uniform(-25, 25), [(0, 0), (R, 0.0), (R * 0.62, H * 0.5), (R * 0.28, H * 0.88), (R * 0.08, H), (0, H + 1.0)],
              9, "Mountain", rnd.uniform(0, 1.0))

TURBINES = [(-96.0, -182.0, 46.0), (70.0, -205.0, 52.0), (140.0, -168.0, 42.0)]

def build_turbines():
    """The orbal turbines: tall generator towers with glowing rings and a great rotor on top (rotor = card)."""
    g = "RR_Far"
    for k, (x, z, h) in enumerate(TURBINES):
        lathe(g, x, LOW_Y, z, [(0, 0), (8.0, 0.0), (8.0, 4.0), (6.0, 6.0), (5.0, h), (6.5, h + 1.0), (6.5, h + 5.0), (3.0, h + 6.0), (0, h + 6.5)], 16, "Turbine")
        for j in range(4):
            y = LOW_Y + 10 + j * (h - 14) / 3
            ring = grp("RR_Glow", "Cards")
            for i in range(16):
                a0, a1 = 2 * math.pi * i / 16, 2 * math.pi * (i + 1) / 16
                r = 6.0 - (y - LOW_Y - 6.0) / max(1.0, h - 6.0) + 0.08
                quad(ring, [(x + r * math.cos(a0), y - 0.4, z + r * math.sin(a0)), (x + r * math.cos(a1), y - 0.4, z + r * math.sin(a1)),
                            (x + r * math.cos(a1), y + 0.4, z + r * math.sin(a1)), (x + r * math.cos(a0), y + 0.4, z + r * math.sin(a0))],
                     [(i / 16, 3.2), ((i + 1) / 16, 3.2), ((i + 1) / 16, 3.8), (i / 16, 3.8)], "GlowGreen")
        R = 17.0; yc = LOW_Y + h + 3.0; zc = z + 7.0
        card("RR_Rotor", [(x - R, yc - R, zc), (x + R, yc - R, zc), (x + R, yc + R, zc), (x - R, yc + R, zc)], k, "RotorCard")
        box(g, x, yc - 1.2, yc + 1.2, z + 5.5, 2.4, 3.0, "Steel")

def build_cards():
    # sky cylinder
    g = grp("RR_Sky", "Cards"); n = 96; y0, y1 = -40.0, 320.0
    for i in range(n):
        t0, t1 = i / n, (i + 1) / n
        A0, A1 = 2 * math.pi * t0 - math.pi, 2 * math.pi * t1 - math.pi
        p0 = (SKY_R * math.sin(A0), 0, -60 - SKY_R * math.cos(A0)); p1 = (SKY_R * math.sin(A1), 0, -60 - SKY_R * math.cos(A1))
        quad(g, [(p0[0], y0, p0[2]), (p1[0], y0, p1[2]), (p1[0], y1, p1[2]), (p0[0], y1, p0[2])], [(t0, 0), (t1, 0), (t1, 1), (t0, 1)], "SkyCard")
    # smoke plumes from the chimneys (crossed quads, leaning with the wind)
    for i, (x, y, z) in enumerate(CHIMNEYS):
        for a in (0.2, 0.2 + math.pi / 2):
            dx, dz = math.cos(a) * 6.0, math.sin(a) * 6.0
            card("RR_Smoke", [(x - dx, y - 1.0, z - dz), (x + dx, y - 1.0, z + dz), (x + dx * 3.2 + 34, y + 56, z + dz * 3.2), (x - dx * 3.2 + 34, y + 56, z - dz * 3.2)], i, "SmokeCard")
    # airships far off
    for i, (y, z, w) in enumerate(((78.0, -360.0, 46.0), (104.0, -420.0, 34.0))):
        card("RR_Ship", [(-w / 2, y - w * 0.22, z), (w / 2, y - w * 0.22, z), (w / 2, y + w * 0.22, z), (-w / 2, y + w * 0.22, z)], i, "ShipCard")
    # smog layers between the city and the factories, and over the far district
    for i, (z, top, hw) in enumerate(((-140.0, 22.0, 160.0), (-210.0, 40.0, 240.0), (-300.0, 60.0, 340.0))):
        card("RR_Haze", [(-hw, LOW_Y - 2, z), (hw, LOW_Y - 2, z), (hw, top, z), (-hw, top, z)], i, "HazeCard", 0.0, 2 * hw / 20.0)

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
    sd = bpy.data.lights.new("Sun", 'SUN'); sd.energy = V["sun"][0]; sd.color = srgb(V["sun"][1]); sd.angle = math.radians(2.0)
    s = bpy.data.objects.new("Sun", sd); col("Lights").objects.link(s)
    d = Vector(SUN_DIR).normalized()
    s.rotation_mode = 'QUATERNION'; s.rotation_quaternion = Vector((d.x, -d.z, d.y)).to_track_quat('-Z', 'Y')
    def area(name, pos, aim, size, power, colr):
        ld = bpy.data.lights.new(name, 'AREA'); ld.shape = 'RECTANGLE'
        ld.size, ld.size_y = size; ld.energy = power; ld.color = srgb(colr)
        o = bpy.data.objects.new(name, ld); col("Lights").objects.link(o); o.location = G(*pos)
        o.rotation_mode = 'QUATERNION'; o.rotation_quaternion = (G(*aim) - G(*pos)).normalized().to_track_quat('-Z', 'Y')
        o.visible_camera = False
    area("Fill_Front", (0, 10.0, 26.0), (0, 1.0, -12.0), (40, 12), V["fill"][0], V["fill"][1])
    area("Fill_Top", (0, 26.0, -6.0), (0, 0.0, -6.0), (44, 44), V["top"][0], V["top"][1])
    for k, (x, y, z, wts, c) in enumerate(POINTS):
        ld = bpy.data.lights.new("Lamp_%d" % k, 'POINT'); ld.energy = wts; ld.color = srgb(c); ld.shadow_soft_size = 0.25
        o = bpy.data.objects.new("Lamp_%d" % k, ld); col("Lights").objects.link(o); o.location = G(x, y, z); o.visible_camera = False

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
        cd.clip_start = 0.1; cd.clip_end = 1200
        o = bpy.data.objects.new(name, cd); col("Cameras").objects.link(o)
        o.location = G(*pos); o.rotation_euler = (math.radians(90), 0, 0)
    bpy.context.scene.camera = bpy.data.objects["CAM_mid"]

CARD_GROUPS = ("RR_Sky", "RR_Win", "RR_Glow", "RR_Steps", "RR_Smoke", "RR_Rotor", "RR_Train", "RR_Ship", "RR_Flag", "RR_Haze")
HIDDEN = ("RR_Steps", "RR_Smoke", "RR_Rotor", "RR_Train", "RR_Ship", "RR_Flag", "RR_Haze")

def build_all():
    reset(); COLS.clear(); MATS.clear(); GR.clear()
    for L in (POINTS, CHIMNEYS):
        L.clear()
    WIN[0] = 0
    build_materials()
    build_floor(); build_plaza(); build_plaza_buildings(); build_lower_level(); build_upper_ground(); build_viaduct()
    build_tower(); build_cathedral(); build_institute(); build_upper_city(); build_factories(); build_turbines()
    build_cards(); build_preview()
    objs = {name: g.finish() for name, g in list(GR.items())}
    for n in CARD_GROUPS:
        if n in objs:
            objs[n].visible_shadow = False
    for n in HIDDEN:
        if n in objs:
            objs[n].hide_render = True
    build_lights(); build_cameras(); setup_render()
    tris = {o.name: sum(len(p.vertices) - 2 for p in o.data.polygons) for o in objs.values()}
    return {"variant": VARIANT, "objects": list(objs), "tris": tris, "total_tris": sum(tris.values()),
            "windows": WIN[0], "points": len(POINTS), "chimneys": len(CHIMNEYS)}

if __name__ == "__main__":
    BUILD_INFO = build_all()
